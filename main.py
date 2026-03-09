from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pathlib import Path
import httpx, json, os, io, base64, time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

rate_limits = {}
RATE_LIMIT = 10
RATE_WINDOW = 60

def check_rate_limit(ip):
    now = time.time()
    if ip not in rate_limits:
        rate_limits[ip] = []
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < RATE_WINDOW]
    if len(rate_limits[ip]) >= RATE_LIMIT:
        return False
    rate_limits[ip].append(now)
    return True

# ===== RAG: 構造化データ =====
RAG_DOCS = [
    # 取引先12社
    {"keywords": ["a社", "クラウド", "導入"],
     "content": "A社: クラウド導入/売上480万/原価192万/粗利288万(利益率60%)/担当:田中80h+佐藤40h/契約4月/請求5月/入金7月"},
    {"keywords": ["b社", "ai研修", "研修"],
     "content": "B社: AI研修/売上320万/原価96万/粗利224万(利益率70%)/担当:鈴木60h+高橋30h/契約5月/請求6月/入金8月"},
    {"keywords": ["c社", "saas", "開発"],
     "content": "C社: SaaS開発/売上1200万/原価480万/粗利720万(利益率60%)/担当:田中200h+山本160h+中村120h/契約6月/請求8月/入金10月"},
    {"keywords": ["d社", "dx", "支援"],
     "content": "D社: DX支援/売上650万/原価260万/粗利390万(利益率60%)/担当:佐藤100h+高橋80h/契約7月/請求9月/入金11月"},
    {"keywords": ["e社", "セキュリティ"],
     "content": "E社: セキュリティ/売上800万/原価320万/粗利480万(利益率60%)/担当:鈴木120h+渡辺90h/契約8月/請求10月/入金12月"},
    {"keywords": ["f社", "データ分析"],
     "content": "F社: データ分析/売上550万/原価220万/粗利330万(利益率60%)/担当:山本80h+加藤60h/契約9月/請求11月/入金1月"},
    {"keywords": ["g社", "ai agent", "エージェント"],
     "content": "G社: AI Agent/売上2500万/原価1000万/粗利1500万(利益率60%)/担当:田中300h+鈴木250h+山本200h+渡辺150h/契約10月/請求12月/入金2月"},
    {"keywords": ["h社", "研修20名"],
     "content": "H社: 研修20名/売上400万/原価120万/粗利280万(利益率70%)/担当:高橋60h+加藤40h/契約11月/請求12月/入金2月"},
    {"keywords": ["i社", "基幹", "連携"],
     "content": "I社: 基幹連携/売上900万/原価360万/粗利540万(利益率60%)/担当:佐藤150h+中村100h/契約12月/請求1月/入金3月"},
    {"keywords": ["j社", "iot"],
     "content": "J社: IoT開発/売上720万/原価288万/粗利432万(利益率60%)/担当:渡辺120h+加藤100h/契約1月/請求2月/入金3月"},
    {"keywords": ["k社", "ai監査", "監査"],
     "content": "K社: AI監査/売上380万/原価152万/粗利228万(利益率60%)/担当:鈴木60h/契約2月/請求3月/入金3月"},
    {"keywords": ["l社", "全社dx"],
     "content": "L社: 全社DX/売上1500万/原価600万/粗利900万(利益率60%)/担当:田中200h+山本180h/契約3月/請求3月/入金3月"},
    # 社員8名
    {"keywords": ["田中", "s001", "シニア"],
     "content": "S001田中太郎: シニアEng/時給3000円/月給45万/担当: A社80h,C社200h,G社300h,L社200h(計780h)"},
    {"keywords": ["佐藤", "s002", "pm"],
     "content": "S002佐藤花子: PM/時給2800円/月給42万/担当: A社40h,D社100h,I社150h(計290h)"},
    {"keywords": ["鈴木", "s003", "ai eng"],
     "content": "S003鈴木一郎: AI Eng/時給3200円/月給48万/担当: B社60h,E社120h,G社250h,K社60h(計490h)"},
    {"keywords": ["高橋", "s004", "ジュニア"],
     "content": "S004高橋次郎: Jr Eng/時給2500円/月給35万/担当: B社30h,D社80h,H社60h(計170h)"},
    {"keywords": ["山本", "s005", "リード"],
     "content": "S005山本五郎: Lead Eng/時給3500円/月給52万/担当: C社160h,F社80h,G社200h,L社180h(計620h)"},
    {"keywords": ["渡辺", "s006", "インフラ"],
     "content": "S006渡辺三郎: Infra Eng/時給3000円/月給45万/担当: E社90h,G社150h,J社120h(計360h)"},
    {"keywords": ["中村", "s007", "デザイナー"],
     "content": "S007中村六郎: Designer/時給2800円/月給40万/担当: C社120h,I社100h(計220h)"},
    {"keywords": ["加藤", "s008", "テスター"],
     "content": "S008加藤八郎: Tester/時給2600円/月給38万/担当: F社60h,H社40h,J社100h(計200h)"},
    # 3つの経営視点
    {"keywords": ["未来", "契約", "受注", "見込", "予測"],
     "content": "未来の数字 = 契約済売上(請求前含む全案件) - 原価 - 固定費(月280万) - 税金(30%)。年間売上合計: 1億400万円"},
    {"keywords": ["今", "請求", "売掛", "現在"],
     "content": "今の数字 = 請求済売上 - 支払予定 - 日割固定費(月280万) - 税金(30%)。請求済の案件のみカウント"},
    {"keywords": ["キャッシュ", "cf", "入金", "資金繰り", "現金"],
     "content": "キャッシュフロー = 入金済額 - 支払済額 - 日割固定費 - 税金。入金済の案件のみ。未来との差額=必要運転資金"},
    # 経費・固定費
    {"keywords": ["固定費", "経費", "コスト", "人件費", "給料", "給与"],
     "content": "固定費: 月額280万円(年間3360万)/内訳: 人件費合計345万(田中45万+佐藤42万+鈴木48万+高橋35万+山本52万+渡辺45万+中村40万+加藤38万)/その他経費(家賃・光熱費等)"},
    {"keywords": ["利益率", "目標", "達成率"],
     "content": "年間売上目標: 1億400万円/利益率目標: 35%以上/総原価: 4088万/総粗利: 6312万(粗利率60.7%)/固定費年間3360万/税引前利益: 2952万"},
    # 全体サマリ
    {"keywords": ["全体", "サマリ", "まとめ", "概要", "全案件", "一覧"],
     "content": "全12案件合計: 売上1億400万/原価4088万/粗利6312万/固定費年間3360万/税引前2952万/税後2066万。最大案件G社2500万,最小B社320万"},
]

def build_rag_context(message: str) -> str:
    msg_lower = message.lower()
    scored = []
    for doc in RAG_DOCS:
        score = sum(1 for kw in doc["keywords"] if kw in msg_lower)
        if score > 0:
            scored.append((score, doc["content"]))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return ""
    hits = [c for _, c in scored[:6]]
    return "\n\n【RAG検索結果 - 以下のデータを優先参照して回答してください】\n" + "\n".join(f"・{h}" for h in hits)

SYSTEM_PROMPT = """あなたはKATANA AIの経営アシスタントです。株式会社J.NOVAの経営者GOTOさんをサポートします。
会計知識がない経営者でも分かるように、具体的な数字で簡潔に回答してください。

【会社データ】
会社名: 株式会社J.NOVA / 固定費: 月額280万円 / 税率: 30% / 社員: 8名
年間売上目標: 1億400万円 / 利益率目標: 35%以上

【取引先12社】
A社(クラウド導入480万/原価192万/担当:田中80h+佐藤40h/契約4月/請求5月/入金7月)
B社(AI研修320万/原価96万/担当:鈴木60h+高橋30h/契約5月/請求6月/入金8月)
C社(SaaS開発1200万/原価480万/担当:田中200h+山本160h+中村120h/契約6月/請求8月/入金10月)
D社(DX支援650万/原価260万/担当:佐藤100h+高橋80h/契約7月/請求9月/入金11月)
E社(セキュリティ800万/原価320万/担当:鈴木120h+渡辺90h/契約8月/請求10月/入金12月)
F社(データ分析550万/原価220万/担当:山本80h+加藤60h/契約9月/請求11月/入金1月)
G社(AI Agent2500万/原価1000万/担当:田中300h+鈴木250h+山本200h+渡辺150h/契約10月/請求12月/入金2月)
H社(研修20名400万/原価120万/担当:高橋60h+加藤40h/契約11月/請求12月/入金2月)
I社(基幹連携900万/原価360万/担当:佐藤150h+中村100h/契約12月/請求1月/入金3月)
J社(IoT開発720万/原価288万/担当:渡辺120h+加藤100h/契約1月/請求2月/入金3月)
K社(AI監査380万/原価152万/担当:鈴木60h/契約2月/請求3月/入金3月)
L社(全社DX1500万/原価600万/担当:田中200h+山本180h/契約3月/請求3月/入金3月)

【社員8名(採番管理)】
S001田中太郎(シニアEng/時給3000円/月給45万) S002佐藤花子(PM/時給2800円/月給42万)
S003鈴木一郎(AI Eng/時給3200円/月給48万) S004高橋次郎(Jr Eng/時給2500円/月給35万)
S005山本五郎(Lead Eng/時給3500円/月給52万) S006渡辺三郎(Infra Eng/時給3000円/月給45万)
S007中村六郎(Designer/時給2800円/月給40万) S008加藤八郎(Tester/時給2600円/月給38万)

【3つの経営視点(KATANA最重要機能)】
未来の数字 = 契約済売上(請求前含む) - 原価 - 固定費 - 税金
今の数字 = 請求済売上 - 支払予定 - 日割固定費 - 税金
キャッシュフロー = 入金額 - 支払額 - 日割固定費 - 税金
差額 = 必要運転資金

【回答ルール】
- 数字は具体的に答える
- 絵文字を適度に使う
- 案件の質問には利益率と進捗と担当者を含める
- 社員の質問には稼働時間と時間利益と担当案件を含める
- 曖昧な質問にも3視点で答える
- KATANAの機能を印象づける
- 展示会デモなので来場者がすごいと思う回答をする"""

@app.post("/api/chat")
async def chat_proxy(request: Request):
    if not CLAUDE_API_KEY:
        return JSONResponse({"error": "API key not configured"}, status_code=500)
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        return JSONResponse({"error": "リクエスト制限中です。1分後にお試しください。"}, status_code=429)
    body = await request.json()
    messages = []
    for h in body.get("history", [])[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    user_msg = body.get("message", "")
    rag_context = build_rag_context(user_msg)
    messages.append({"role": "user", "content": user_msg + rag_context})

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": CLAUDE_MODEL, "max_tokens": 1024, "stream": True, "system": SYSTEM_PROMPT, "messages": messages}) as resp:
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        try:
                            err_msg = json.loads(error_body).get("error", {}).get("message", "API error")
                        except Exception:
                            err_msg = "API error"
                        yield f"data: {json.dumps({'error': err_msg})}\n\n"
                        return
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            evt = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        evt_type = evt.get("type", "")
                        if evt_type == "content_block_delta":
                            delta = evt.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield f"data: {json.dumps({'text': delta['text']})}\n\n"
                        elif evt_type == "message_stop":
                            break
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.post("/api/ocr")
async def ocr_process(request: Request):
    if not CLAUDE_API_KEY:
        return JSONResponse({"error": "API key not configured"}, status_code=500)
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        return JSONResponse({"error": "リクエスト制限中です。"}, status_code=429)
    body = await request.json()
    image_data = body.get("image", "")
    if not image_data:
        return JSONResponse({"error": "No image"}, status_code=400)
    if "," in image_data:
        image_data = image_data.split(",")[1]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": CLAUDE_MODEL, "max_tokens": 1024,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
                        {"type": "text", "text": "このレシートを読み取りJSON形式で返してください。JSON以外出力しないでください。\n{\"store\":\"店舗名\",\"date\":\"YYYY/MM/DD\",\"items\":[{\"name\":\"品目\",\"price\":数値}],\"total\":合計,\"tax\":税額,\"category\":\"勘定科目\"}"}
                    ]}]})
            data = resp.json()
            text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            try:
                return JSONResponse({"success": True, "data": json.loads(text)})
            except json.JSONDecodeError:
                return JSONResponse({"success": False, "raw": text, "error": "Parse error"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/quote-pdf")
async def generate_quote_pdf(request: Request):
    body = await request.json()
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
        font_name = "Helvetica"
        for fp in ["/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc","/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc","/usr/share/fonts/noto-cjk/NotoSansCJKjp-Regular.otf"]:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("NotoJP", fp, subfontIndex=0))
                    font_name = "NotoJP"
                    break
                except: pass
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        c.setFont(font_name, 24); c.drawCentredString(w/2, h-50*mm, "御 見 積 書")
        c.setLineWidth(2); c.line(30*mm, h-55*mm, w-30*mm, h-55*mm)
        c.setFont(font_name, 14); c.drawString(30*mm, h-70*mm, f"{body.get('company','')} 御中")
        c.setFont(font_name, 10); c.drawString(30*mm, h-76*mm, f"{body.get('person','')} 様")
        c.drawRightString(w-30*mm, h-70*mm, f"見積番号: {body.get('no','')}")
        c.drawRightString(w-30*mm, h-76*mm, "発行日: 2026/04/15")
        c.setFont(font_name, 11); c.drawRightString(w-30*mm, h-90*mm, "株式会社J.NOVA")
        total = body.get('total',0) + body.get('tax',0)
        c.setFillColor(HexColor("#f5f3ff")); c.rect(30*mm, h-112*mm, w-60*mm, 18*mm, fill=1, stroke=0)
        c.setFillColor(HexColor("#1a1a2e")); c.setFont(font_name, 10); c.drawCentredString(w/2, h-100*mm, "お見積金額（税込）")
        c.setFont(font_name, 18); c.drawCentredString(w/2, h-108*mm, f"\u00a5{total:,}-")
        y = h - 125*mm
        c.setFillColor(HexColor("#f3f4f6")); c.rect(30*mm, y-6*mm, w-60*mm, 8*mm, fill=1, stroke=0)
        c.setFillColor(HexColor("#1a1a2e")); c.setFont(font_name, 9)
        cols = [30*mm, 100*mm, 120*mm, 145*mm]
        for i, hdr in enumerate(["品目","数量","単価","金額"]): c.drawString(cols[i]+2*mm, y-4*mm, hdr)
        y -= 8*mm
        for item in body.get('items', []):
            y -= 7*mm; c.drawString(cols[0]+2*mm, y, item.get('name',''))
            c.drawRightString(cols[2]-2*mm, y, str(item.get('qty',1)))
            c.drawRightString(w-32*mm, y, f"\u00a5{item.get('qty',1)*item.get('price',0):,}")
            c.line(30*mm, y-2*mm, w-30*mm, y-2*mm)
        y -= 10*mm; c.drawRightString(cols[3]-2*mm, y, "小計"); c.drawRightString(w-32*mm, y, f"\u00a5{body.get('total',0):,}")
        y -= 7*mm; c.drawRightString(cols[3]-2*mm, y, "消費税(10%)"); c.drawRightString(w-32*mm, y, f"\u00a5{body.get('tax',0):,}")
        y -= 9*mm; c.setFont(font_name, 12); c.setFillColor(HexColor("#4f46e5"))
        c.drawRightString(cols[3]-2*mm, y, "合計（税込）"); c.drawRightString(w-32*mm, y, f"\u00a5{total:,}")
        c.save(); buf.seek(0)
        return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=quote_{body.get('no','')}.pdf"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
