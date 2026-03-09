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
ユーザーとの自然な会話を通じて、以下の企業情報を聞き出してください。

【収集する情報】
1. 業種（industry）: it, retail, restaurant, construction, manufacturing, service のいずれか
2. 会社名（name）: ユーザーの会社名
3. 社員数（staff_count）: 数値
4. 月額固定費（fixed_cost_monthly）: 数値（円単位）

【会話ルール】
- 最初の挨拶: 「こんにちは！KATANA AIです。御社の経営を一刀両断します⚔️ まず、どんなお仕事をされていますか？」
- 自然な会話で情報を聞き出す。一度に全部聞かない。
- ユーザーの発言から情報を推測・抽出する
- 「万」は10000倍に変換（例：180万 → 1800000）
- まだ聞いていない情報があれば、自然な流れで質問する
- 全情報が揃ったら、内容を一覧表示して「この内容で登録してよろしいですか？」と確認する
- ユーザーが「はい」等で確認したら <confirmed>true</confirmed> タグを追加する
- 現在利用可能な業種はITと小売のみ。他の業種は「準備中」と伝える

【業種キーワードマッピング】
- IT/ソフトウェア/開発/システム/SaaS/エンジニア/プログラム/Web/アプリ/受託 → it
- 小売/スーパー/食品/ドラッグストア/コンビニ/専門店/物販/店舗/販売 → retail
- 飲食/レストラン/カフェ/居酒屋/食堂/料理 → restaurant
- 建設/工事/建築/土木/リフォーム/施工 → construction
- 製造/工場/加工/組立/部品/生産 → manufacturing
- サービス/人材/派遣/教育/研修/コンサル → service

【重要】必ず回答の最後に以下のタグで抽出した情報を含めてください：
<extracted>{"industry": null, "name": null, "staff_count": null, "fixed_cost_monthly": null}</extracted>

未取得の項目はnullにしてください。判明した項目は値を入れてください。
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
            messages.append({"role": "user", "content": user_msg})

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

    return router
