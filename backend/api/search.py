"""
トレンド検索・市場分析API
OpenAI: トレンド検索、市場動向
Gemini: 横断分析、業界比較
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.llm.openai_client import OpenAIClient
from backend.llm.gemini_client import GeminiClient

router = APIRouter()


def create_search_router(
    openai_client: OpenAIClient | None = None,
    gemini_client: GeminiClient | None = None,
    template=None,
) -> APIRouter:
    oa = openai_client or OpenAIClient()
    gm = gemini_client or GeminiClient()

    @router.get("/api/search/trends")
    async def search_trends(q: str = "", industry: str = "IT", limit: int = 5):
        """トレンド検索（OpenAI）"""
        results = await oa.search_trends(q, industry=industry, limit=limit)
        return JSONResponse({"trends": results, "query": q})

    @router.get("/api/search/market")
    async def market_analysis(industry: str = "IT"):
        """市場動向分析（OpenAI）"""
        company_data = template.summary(current_month=0) if template else {}
        report = await oa.market_analysis(company_data, industry=industry)
        return JSONResponse({"report": report})

    @router.post("/api/search/market-stream")
    async def market_stream(request: Request):
        """ストリーミング市場分析（OpenAI）"""
        body = await request.json()
        question = body.get("question", "市場動向を分析してください")
        company_data = template.summary(current_month=0) if template else {}

        async def generate():
            async for chunk in oa.stream_market_analysis(company_data, question):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @router.get("/api/search/cross-analysis")
    async def cross_analysis(analysis_type: str = "general"):
        """横断分析（Gemini）"""
        data = template.summary(current_month=0) if template else {}
        report = await gm.cross_analyze(data, analysis_type=analysis_type)
        return JSONResponse({"report": report, "type": analysis_type})

    @router.get("/api/search/industry-compare")
    async def industry_compare(industry: str = "IT"):
        """業界比較分析（Gemini）"""
        company_data = template.summary(current_month=0) if template else {}
        report = await gm.compare_industry(company_data, industry=industry)
        return JSONResponse({"report": report})

    @router.post("/api/search/cross-stream")
    async def cross_stream(request: Request):
        """ストリーミング横断分析（Gemini）"""
        body = await request.json()
        question = body.get("question", "横断分析してください")
        data = template.summary(current_month=0) if template else {}

        async def generate():
            async for chunk in gm.stream_analyze(data, question):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    return router
