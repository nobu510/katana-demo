"""
KATANA AI - FastAPI エントリポイント
業種共通の経営管理SaaS
"""
from dotenv import load_dotenv
load_dotenv()

import json
import os
import io
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from pathlib import Path

from backend.templates.it_company import ITCompanyTemplate
from backend.templates.retail import RetailTemplate
from backend.llm.claude_client import ClaudeClient
from backend.llm.gemini_client import GeminiClient
from backend.llm.openai_client import OpenAIClient
from backend.api.chat import create_chat_router, build_rag_context
from backend.api.dashboard import create_dashboard_router
from backend.api.search import create_search_router
from backend.api.register import create_register_router

# ===== App =====
app = FastAPI(title="KATANA AI", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Template & LLM =====
templates = {
    "it_company": ITCompanyTemplate(),
    "retail": RetailTemplate(),
}
template = templates["it_company"]  # デフォルト
claude = ClaudeClient()
gemini = GeminiClient()
openai_client = OpenAIClient()

SYSTEM_PROMPT = template.build_system_prompt()
RAG_DOCS = template.build_rag_docs()

# ===== Rate Limiter =====
rate_limits: dict[str, list[float]] = {}
RATE_LIMIT = 10
RATE_WINDOW = 60


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    if ip not in rate_limits:
        rate_limits[ip] = []
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < RATE_WINDOW]
    if len(rate_limits[ip]) >= RATE_LIMIT:
        return False
    rate_limits[ip].append(now)
    return True


# ===== Register API routers =====
app.include_router(
    create_chat_router(claude, SYSTEM_PROMPT, RAG_DOCS, check_rate_limit)
)
app.include_router(create_dashboard_router(templates))
app.include_router(create_search_router(openai_client, gemini, template))
app.include_router(create_register_router())


# ===== OCR (kept inline - uses Claude directly) =====
@app.post("/api/ocr")
async def ocr_process(request: Request):
    if not claude.api_key:
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
        text = await claude.single_request(
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
                {"type": "text", "text": 'このレシートを読み取りJSON形式で返してください。JSON以外出力しないでください。\n{"store":"店舗名","date":"YYYY/MM/DD","items":[{"name":"品目","price":数値}],"total":合計,"tax":税額,"category":"勘定科目"}'},
            ]}],
            system_prompt="",
        )
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            return JSONResponse({"success": True, "data": json.loads(text)})
        except json.JSONDecodeError:
            return JSONResponse({"success": False, "raw": text, "error": "Parse error"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== Quote PDF =====
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
        for fp in [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Regular.otf",
        ]:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("NotoJP", fp, subfontIndex=0))
                    font_name = "NotoJP"
                    break
                except Exception:
                    pass

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        c.setFont(font_name, 24)
        c.drawCentredString(w / 2, h - 50 * mm, "御 見 積 書")
        c.setLineWidth(2)
        c.line(30 * mm, h - 55 * mm, w - 30 * mm, h - 55 * mm)
        c.setFont(font_name, 14)
        c.drawString(30 * mm, h - 70 * mm, f"{body.get('company', '')} 御中")
        c.setFont(font_name, 10)
        c.drawString(30 * mm, h - 76 * mm, f"{body.get('person', '')} 様")
        c.drawRightString(w - 30 * mm, h - 70 * mm, f"見積番号: {body.get('no', '')}")
        c.drawRightString(w - 30 * mm, h - 76 * mm, "発行日: 2026/04/15")
        c.setFont(font_name, 11)
        c.drawRightString(w - 30 * mm, h - 90 * mm, template.config.name)
        total = body.get("total", 0) + body.get("tax", 0)
        c.setFillColor(HexColor("#f5f3ff"))
        c.rect(30 * mm, h - 112 * mm, w - 60 * mm, 18 * mm, fill=1, stroke=0)
        c.setFillColor(HexColor("#1a1a2e"))
        c.setFont(font_name, 10)
        c.drawCentredString(w / 2, h - 100 * mm, "お見積金額（税込）")
        c.setFont(font_name, 18)
        c.drawCentredString(w / 2, h - 108 * mm, f"\u00a5{total:,}-")
        y = h - 125 * mm
        c.setFillColor(HexColor("#f3f4f6"))
        c.rect(30 * mm, y - 6 * mm, w - 60 * mm, 8 * mm, fill=1, stroke=0)
        c.setFillColor(HexColor("#1a1a2e"))
        c.setFont(font_name, 9)
        cols = [30 * mm, 100 * mm, 120 * mm, 145 * mm]
        for i, hdr in enumerate(["品目", "数量", "単価", "金額"]):
            c.drawString(cols[i] + 2 * mm, y - 4 * mm, hdr)
        y -= 8 * mm
        for item in body.get("items", []):
            y -= 7 * mm
            c.drawString(cols[0] + 2 * mm, y, item.get("name", ""))
            c.drawRightString(cols[2] - 2 * mm, y, str(item.get("qty", 1)))
            c.drawRightString(w - 32 * mm, y, f"\u00a5{item.get('qty', 1) * item.get('price', 0):,}")
            c.line(30 * mm, y - 2 * mm, w - 30 * mm, y - 2 * mm)
        y -= 10 * mm
        c.drawRightString(cols[3] - 2 * mm, y, "小計")
        c.drawRightString(w - 32 * mm, y, f"\u00a5{body.get('total', 0):,}")
        y -= 7 * mm
        c.drawRightString(cols[3] - 2 * mm, y, "消費税(10%)")
        c.drawRightString(w - 32 * mm, y, f"\u00a5{body.get('tax', 0):,}")
        y -= 9 * mm
        c.setFont(font_name, 12)
        c.setFillColor(HexColor("#4f46e5"))
        c.drawRightString(cols[3] - 2 * mm, y, "合計（税込）")
        c.drawRightString(w - 32 * mm, y, f"\u00a5{total:,}")
        c.save()
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=quote_{body.get('no', '')}.pdf"},
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== Static files (HTML版フォールバック) =====
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
