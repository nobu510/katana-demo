"""
チャットAPI - SSEストリーミング対応 + 企業登録会話
"""
from __future__ import annotations
import json
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.llm.claude_client import ClaudeClient

router = APIRouter()

# ===== 企業登録用システムプロンプト =====
REGISTRATION_SYSTEM_PROMPT = """あなたはKATANA AIの企業登録アシスタントです。
ユーザーとの自然な会話を通じて、以下の4つの企業情報を聞き出してください。

【収集する情報（4項目）】
1. 業種（industry）: it, retail, restaurant, construction, manufacturing, service のいずれか
2. 会社名（name）: ユーザーの会社名
3. 社員数（staff_count）: 数値
4. 月額固定費（fixed_cost_monthly）: 数値（円単位）

【会話ルール】
- ユーザーの発言から可能な限り多くの情報を一括抽出する
- 1つの発言に複数の情報が含まれる場合は全て抽出する
  例: 「株式会社シャンクスです 社員6名 固定費200万」→ name, staff_count, fixed_cost_monthly を全て抽出
- 「万」は10000倍に変換（例：200万 → 2000000、180万 → 1800000）
- 「名」「人」は数値部分を抽出（例：6名 → 6、10人 → 10）
- ユーザーメッセージに「[システム情報: ...]」がある場合、そこに記載された項目は既に取得済み。絶対に再度聞かない。
- まだ不足している項目だけを自然に質問する
- 全4項目が揃ったら、内容を以下の形式で一覧表示して確認する：
  ・業種: ○○
  ・会社名: ○○
  ・社員数: ○名
  ・月額固定費: ○○万円
  「この内容で登録してよろしいですか？」
- ユーザーが「はい」「OK」「お願い」「大丈夫」等の肯定で返答したら、「登録完了しました！ダッシュボードを準備しています...」と返答し、必ず <confirmed>true</confirmed> タグを付ける
- 現在利用可能な業種はITと小売のみ。他の業種は「現在準備中です。ITまたは小売からお選びください」と伝える

【業種キーワードマッピング】
- IT/ソフトウェア/開発/システム/SaaS/エンジニア/プログラム/Web/アプリ/受託/テック → it
- 小売/スーパー/食品/ドラッグストア/コンビニ/専門店/物販/店舗/販売/EC/通販 → retail
- 飲食/レストラン/カフェ/居酒屋/食堂/料理 → restaurant（準備中）
- 建設/工事/建築/土木/リフォーム/施工 → construction（準備中）
- 製造/工場/加工/組立/部品/生産 → manufacturing（準備中）
- サービス/人材/派遣/教育/研修/コンサル → service（準備中）

【重要】必ず回答の最後に以下のタグで、今回の発言から新たに判明した情報も含めて全ての抽出結果を出力してください：
<extracted>{"industry": "it", "name": "株式会社○○", "staff_count": 6, "fixed_cost_monthly": 2000000}</extracted>

未取得の項目はnullにしてください。判明した項目は値を入れてください。
このタグはシステムが自動処理するため、ユーザーには見えません。必ず毎回出力してください。
"""


def build_rag_context(message: str, rag_docs: list[dict]) -> str:
    """キーワードマッチでRAGコンテキストを構築"""
    msg_lower = message.lower()
    scored = []
    for doc in rag_docs:
        score = sum(1 for kw in doc["keywords"] if kw in msg_lower)
        if score > 0:
            scored.append((score, doc["content"]))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return ""
    hits = [c for _, c in scored[:6]]
    return "\n\n【RAG検索結果 - 以下のデータを優先参照して回答してください】\n" + "\n".join(f"・{h}" for h in hits)


def _parse_registration_response(response: str) -> dict:
    """Claudeの応答から<extracted>と<confirmed>タグをパースする"""
    extracted = None
    confirmed = False
    reply = response

    # Extract <extracted> tag
    ext_match = re.search(r"<extracted>(.*?)</extracted>", response, re.DOTALL)
    if ext_match:
        try:
            extracted = json.loads(ext_match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
        reply = re.sub(r"\s*<extracted>.*?</extracted>\s*", "", reply, flags=re.DOTALL).strip()

    # Check for <confirmed> tag
    conf_match = re.search(r"<confirmed>(.*?)</confirmed>", response)
    if conf_match and conf_match.group(1).strip().lower() == "true":
        confirmed = True
        reply = re.sub(r"\s*<confirmed>.*?</confirmed>\s*", "", reply).strip()

    return {
        "reply": reply,
        "extracted_data": extracted,
        "confirmed": confirmed,
    }


# ===== 業種別データ入力プロンプト =====
_INDUSTRY_PROMPTS: dict[str, str] = {
    "it": """【IT企業のデータ入力ガイド】
ステップ1: 案件の売上データ（案件名、取引先名、受注額）
ステップ2: 案件の原価（外注費、材料費）または原価率
ステップ3: 社員情報（名前、役職、担当案件、時給、月給）

案件データの変換ルール:
- 受注額は円単位。「万」は×10000、「万円」も×10000
- 契約月(cm)=0(4月), 請求月(im)=cm+2, 入金月(pm)=cm+4（最大11）
- 原価(cst): 原価率指定時は受注額×原価率、指定なしは受注額×40%
- 案件名(pj)はユーザーの発言から抽出
- 取引先名(nm)はユーザーの発言から抽出。なければ案件名を使用

例: 「A社のクラウド導入 480万」→ nm:"A社", pj:"クラウド導入", amt:4800000, cst:1920000""",

    "retail": """【小売業のデータ入力ガイド】
ステップ1: 商品カテゴリ別の売上データ（カテゴリ名と月間売上額）
ステップ2: 各カテゴリの原価率
ステップ3: 3視点を自動計算してレポート

小売データの変換ルール:
- 各カテゴリ→1つのclient（ADD_CLIENT）
- nm=カテゴリ名, pj=カテゴリ名+"売上"
- amt=月間売上額
- cst=売上×原価率（原価率未指定時はデフォルト60%）
- 小売は契約=請求=入金が同月: cm=0, im=0, pm=0
- 原価率が伝えられたら、既存clientのcstを更新（UPDATE_COSTアクション）

例: 「和菓子 300万、洋菓子 200万」→
  ADD_CLIENT {nm:"和菓子", pj:"和菓子売上", amt:3000000, cst:1800000, cm:0, im:0, pm:0}
  ADD_CLIENT {nm:"洋菓子", pj:"洋菓子売上", amt:2000000, cst:1200000, cm:0, im:0, pm:0}

原価率更新例: 「和菓子 原価率45%」→
  ADD_CLIENT {nm:"和菓子", amt:3000000, cst:1350000}（cstを再計算して上書き）""",

    "restaurant": """【飲食業のデータ入力ガイド】
ステップ1: メニューカテゴリ別売上（ランチ、ディナー、ドリンク、テイクアウト等）
ステップ2: 食材原価率（FL比率）
ステップ3: スタッフ情報

変換ルール:
- 各メニューカテゴリ→ADD_CLIENT
- nm=カテゴリ名, pj=カテゴリ名+"売上"
- 食材原価率: ランチ35%, ディナー30%, ドリンク20%（デフォルト）
- cm=0, im=0, pm=0（即時売上）""",

    "construction": """【建設業のデータ入力ガイド】
ステップ1: 工事名、発注者、受注額
ステップ2: 外注費・材料費
ステップ3: 現場スタッフ

変換ルール:
- 各工事→ADD_CLIENT
- nm=発注者名, pj=工事名
- 建設は長期: cm=契約月, im=cm+3, pm=cm+6
- 原価率デフォルト70%""",

    "manufacturing": """【製造業のデータ入力ガイド】
ステップ1: 製品名と売上額
ステップ2: 材料費・加工費
ステップ3: 生産スタッフ

変換ルール:
- 各製品→ADD_CLIENT
- nm=製品名, pj=製品名+"製造"
- 原価率デフォルト60%
- cm=0, im=1, pm=2""",

    "service": """【サービス業のデータ入力ガイド】
ステップ1: サービス名と売上額
ステップ2: 人件費・外注費
ステップ3: スタッフ情報

変換ルール:
- 各サービス→ADD_CLIENT
- nm=サービス名, pj=サービス名
- 原価率デフォルト40%
- cm=0, im=0, pm=1""",
}

DATA_INPUT_BASE_PROMPT = """あなたはKATANA AIの経営データアシスタントです。
経営者がチャットで話すだけで、売上・経費・勤怠を全て自動記録します。
経理知識ゼロの経営者が使うことを前提に、専門用語を使わず分かりやすく回答してください。

{industry_guide}

【対応する入力パターン】

■ パターン1: 売上・案件の登録
「今月売上300万」「A社のシステム開発 500万」「和菓子 300万、洋菓子 200万」
→ ADD_CLIENT アクションで登録

■ パターン2: 経費・支払いの記録
「家賃30万払った」「タクシー代2340円」「AWS利用料4万8千円」「交際費3万2千円」
→ UPDATE_FIXED_COSTS アクションで固定費に反映
  - 家賃/賃料 → rent
  - 水道/電気/ガス/光熱 → utilities
  - 電話/ネット/通信/AWS/サーバー → communication
  - リース/レンタル → lease
  - 保険料 → insurance
  - 給与/給料/月給/人件費 → personnel
  - 利息/金利 → interest
  - 減価償却 → depreciation
  - その他（交通費/交際費/消耗品/研修等） → other

■ パターン3: 勤怠・工数の記録
「田中が5時間A案件で働いた」「佐藤 A社 8h」「今日 田中 3時間」
→ LOG_WORK アクション: 指定の社員を指定の案件に工数追加

■ パターン4: 原価率の更新
「和菓子 原価率45%」「A社の原価率は40%」
→ 既存clientのcstを再計算してADD_CLIENTで上書き

■ パターン5: 社員の追加
「田中太郎、エンジニア、月給45万」
→ ADD_STAFF アクション

■ パターン6: 質問・分析
「4月儲かってる？」「利益いくら？」「売上教えて」
→ actionsは空配列、replyで回答。登録済みデータから計算:
  - 売上合計 = 全clientのamt合計
  - 原価合計 = 全clientのcst合計
  - 粗利 = 売上 - 原価
  - 固定費はシステム情報から参照
  - 利益 = 粗利 - 固定費
  - データが無い場合 → 「まだデータがありません。まずは売上データを入力しましょう！」

【金額変換ルール】
- 「万」「万円」→ ×10000（300万→3000000）
- 「千円」→ ×1000
- 「億」→ ×100000000
- 数字のみ → そのまま円単位

【会話ルール】
- 一度に複数のデータが含まれていたら全て抽出する
- データ登録後は必ず登録内容を簡潔に確認し、次に必要なデータを案内する
- 売上入力後 → 「原価率も教えていただけると、利益を計算できます」
- 経費記録後 → 「記録しました。月の固定費に反映しました」
- 質問に回答する際は具体的な数字で回答する
- 「完了」「OK」「以上」等で入力終了 → input_complete: true

【重要】必ず回答の最後に以下のJSONタグを出力してください（ユーザーには見えません）:
<data_actions>
{{
  "reply": "ユーザーに見せるメッセージ",
  "actions": [
    {{"type": "ADD_CLIENT", "data": {{"nm": "名前", "fl": "正式名称", "pj": "案件名", "amt": 金額, "cst": 原価, "cm": 0, "im": 0, "pm": 1, "ct": "", "staff": [], "progress": 0, "inv": []}} }},
    {{"type": "ADD_STAFF", "data": {{"name": "姓", "full": "フルネーム", "role": "役職", "rate": 時給, "salary": 月給}} }},
    {{"type": "UPDATE_FIXED_COSTS", "data": {{"category": "rent", "amount_man": 30}} }},
    {{"type": "LOG_WORK", "data": {{"staff_name": "田中", "client_nm": "A社", "hours": 5}} }}
  ],
  "input_complete": false
}}
</data_actions>

actionsが不要な場合は空配列[]にしてください。
UPDATE_FIXED_COSTSのamount_manは万円単位です。
LOG_WORKはstaff_nameに社員の姓、client_nmに案件/取引先名、hoursに時間を入れます。
"""

def _build_data_input_prompt(industry: str) -> str:
    """業種に応じたデータ入力プロンプトを構築"""
    industry_lower = industry.lower()
    # 業種キーワードマッチ
    guide = _INDUSTRY_PROMPTS.get("it", "")  # default
    for key, prompt in _INDUSTRY_PROMPTS.items():
        if key in industry_lower:
            guide = prompt
            break
    # キーワード部分マッチ
    keyword_map = {
        "it": ["it", "ソフトウェア", "開発", "システム", "saas", "ai", "テック", "受託"],
        "retail": ["小売", "スーパー", "食品", "ドラッグ", "コンビニ", "専門店", "物販", "販売", "ec", "和菓子", "洋菓子", "菓子"],
        "restaurant": ["飲食", "レストラン", "カフェ", "居酒屋", "食堂", "料理"],
        "construction": ["建設", "工事", "建築", "土木", "リフォーム", "施工"],
        "manufacturing": ["製造", "工場", "加工", "組立", "部品", "生産"],
        "service": ["サービス", "人材", "派遣", "教育", "研修", "コンサル"],
    }
    for key, keywords in keyword_map.items():
        if any(kw in industry_lower for kw in keywords):
            guide = _INDUSTRY_PROMPTS[key]
            break
    return DATA_INPUT_BASE_PROMPT.format(industry_guide=guide)


def _parse_data_input_response(response: str) -> dict:
    """データ入力応答から<data_actions>タグをパース"""
    reply = response
    actions = []
    input_complete = False

    match = re.search(r"<data_actions>(.*?)</data_actions>", response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            reply = data.get("reply", reply)
            actions = data.get("actions", [])
            input_complete = data.get("input_complete", False)
        except (json.JSONDecodeError, ValueError):
            pass
        # タグ部分を除去（replyが抽出できなかった場合のフォールバック）
        if reply == response:
            reply = re.sub(r"\s*<data_actions>.*?</data_actions>\s*", "", reply, flags=re.DOTALL).strip()

    return {
        "reply": reply,
        "actions": actions,
        "input_complete": input_complete,
    }


# ===== 固定費更新プロンプト =====
FIXED_COST_SYSTEM_PROMPT = """あなたはKATANA AIの固定費管理アシスタントです。
ユーザーの指示に基づいて固定費の内訳を更新します。

【固定費の9つの勘定科目】
- personnel: 人件費（給与・賞与・法定福利費）
- rent: 地代家賃
- utilities: 水道光熱費
- communication: 通信費
- lease: リース料
- insurance: 保険料
- depreciation: 減価償却費
- interest: 支払利息
- other: その他固定費

【ルール】
- ユーザーの指示を適切な勘定科目に分類
- 金額は万円単位で扱う（「35万」→35）
- 変更した項目のみupdated_costsに含める
- 変更しない項目は含めない

【重要】回答の最後に以下のタグを出力:
<fixed_cost_update>
{
  "reply": "変更内容の確認メッセージ",
  "updated_costs": {"rent": 35, "utilities": 8}
}
</fixed_cost_update>

更新不要の場合はupdated_costsをnullにしてください。
"""


def _parse_fixed_cost_response(response: str) -> dict:
    """固定費応答をパース"""
    reply = response
    updated_costs = None

    match = re.search(r"<fixed_cost_update>(.*?)</fixed_cost_update>", response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            reply = data.get("reply", reply)
            updated_costs = data.get("updated_costs")
        except (json.JSONDecodeError, ValueError):
            pass
        if reply == response:
            reply = re.sub(r"\s*<fixed_cost_update>.*?</fixed_cost_update>\s*", "", reply, flags=re.DOTALL).strip()

    return {
        "reply": reply,
        "updated_costs": updated_costs,
    }


def create_chat_router(
    claude: ClaudeClient,
    system_prompt: str,
    rag_docs: list[dict],
    rate_limiter,
) -> APIRouter:
    """チャットルーターを生成"""

    @router.post("/api/chat")
    async def chat_proxy(request: Request):
        if not claude.api_key:
            return JSONResponse({"error": "API key not configured"}, status_code=500)

        ip = request.client.host if request.client else "unknown"
        if not rate_limiter(ip):
            return JSONResponse(
                {"error": "リクエスト制限中です。1分後にお試しください。"},
                status_code=429,
            )

        body = await request.json()
        messages = []
        for h in body.get("history", [])[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})

        user_msg = body.get("message", "")
        rag_context = build_rag_context(user_msg, rag_docs)
        messages.append({"role": "user", "content": user_msg + rag_context})

        async def event_stream():
            try:
                async for chunk in claude.stream_chat(messages, system_prompt):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.post("/api/chat/register")
    async def chat_register(request: Request):
        """企業登録会話エンドポイント（非ストリーミング）"""
        if not claude.api_key:
            # API未設定時はモック応答
            return JSONResponse({
                "reply": "こんにちは！KATANA AIです。御社の経営を一刀両断します⚔️ まず、どんなお仕事をされていますか？",
                "extracted_data": {"industry": None, "name": None, "staff_count": None, "fixed_cost_monthly": None},
                "confirmed": False,
            })

        ip = request.client.host if request.client else "unknown"
        if not rate_limiter(ip):
            return JSONResponse(
                {"error": "リクエスト制限中です。1分後にお試しください。"},
                status_code=429,
            )

        body = await request.json()
        messages = []
        for h in body.get("history", [])[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})

        user_msg = body.get("message", "")
        if user_msg:
            # 既に取得済みの情報をユーザーメッセージに付与して、Claudeが同じ質問を繰り返さないようにする
            collected = body.get("collected", {})
            collected_info = []
            if collected.get("industry"):
                collected_info.append(f"業種: {collected['industry']}")
            if collected.get("name"):
                collected_info.append(f"会社名: {collected['name']}")
            if collected.get("staff_count") is not None:
                collected_info.append(f"社員数: {collected['staff_count']}名")
            if collected.get("fixed_cost_monthly") is not None:
                collected_info.append(f"固定費: 月{collected['fixed_cost_monthly']}円")

            context_note = ""
            if collected_info:
                context_note = f"\n\n[システム情報: 以下の項目は既に取得済みです。再度聞かないでください。]\n" + "\n".join(collected_info)

            messages.append({"role": "user", "content": user_msg + context_note})

        try:
            response = await claude.single_request(
                messages=messages,
                system_prompt=REGISTRATION_SYSTEM_PROMPT,
                max_tokens=1024,
            )
            result = _parse_registration_response(response)
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ===== データ入力エンドポイント =====
    @router.post("/api/chat/data-input")
    async def chat_data_input(request: Request):
        """業種別データ入力会話（売上→原価→3視点計算）"""
        body = await request.json()
        industry = body.get("industry", "")
        company_name = body.get("company_name", "")
        current_clients = body.get("current_clients", [])
        current_staff = body.get("current_staff", [])

        if not claude.api_key:
            # API未設定時のモック応答
            return JSONResponse({
                "reply": "売上データを入力してください。",
                "actions": [],
                "input_complete": False,
            })

        ip = request.client.host if request.client else "unknown"
        if not rate_limiter(ip):
            return JSONResponse(
                {"error": "リクエスト制限中です。1分後にお試しください。"},
                status_code=429,
            )

        messages = []
        for h in body.get("history", [])[-12:]:
            messages.append({"role": h["role"], "content": h["content"]})

        fixed_costs = body.get("fixed_costs", {})
        user_msg = body.get("message", "")
        # 現在のデータ状態をコンテキストとして追加
        context = f"\n\n[システム情報]\n会社名: {company_name}\n業種: {industry}"
        if current_clients:
            context += f"\n登録済み売上/案件: {json.dumps(current_clients, ensure_ascii=False)}"
        if current_staff:
            context += f"\n登録済み社員: {json.dumps(current_staff, ensure_ascii=False)}"
        if fixed_costs:
            # 万円単位に変換して表示
            fc_display = {k: v / 10000 for k, v in fixed_costs.items() if isinstance(v, (int, float)) and v > 0}
            if fc_display:
                context += f"\n現在の月額固定費(万円): {json.dumps(fc_display, ensure_ascii=False)}"
        messages.append({"role": "user", "content": user_msg + context})

        prompt = _build_data_input_prompt(industry)

        try:
            response = await claude.single_request(
                messages=messages,
                system_prompt=prompt,
                max_tokens=2048,
            )
            result = _parse_data_input_response(response)
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ===== 固定費更新エンドポイント =====
    @router.post("/api/chat/fixed-costs")
    async def chat_fixed_costs(request: Request):
        """固定費の内訳変更"""
        if not claude.api_key:
            return JSONResponse({
                "reply": "固定費を更新しました。",
                "updated_costs": None,
            })

        ip = request.client.host if request.client else "unknown"
        if not rate_limiter(ip):
            return JSONResponse(
                {"error": "リクエスト制限中です。"},
                status_code=429,
            )

        body = await request.json()
        messages = []
        for h in body.get("history", [])[-8:]:
            messages.append({"role": h["role"], "content": h["content"]})

        current_costs = body.get("current_costs", {})
        user_msg = body.get("message", "")
        context = f"\n\n[現在の固定費（万円）]: {json.dumps(current_costs, ensure_ascii=False)}"
        messages.append({"role": "user", "content": user_msg + context})

        try:
            response = await claude.single_request(
                messages=messages,
                system_prompt=FIXED_COST_SYSTEM_PROMPT,
                max_tokens=1024,
            )
            result = _parse_fixed_cost_response(response)
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    return router
