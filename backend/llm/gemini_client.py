"""
Gemini 2.5 Pro クライアント（横断分析用）
売上×在庫×人件費のクロス分析、大規模データ比較
"""
from __future__ import annotations
import json
import os
from typing import AsyncGenerator

import httpx


# Gemini APIが未設定時のモックレスポンス
MOCK_CROSS_ANALYSIS = """📊 **横断分析レポート（デモ）**

【売上×人件費 効率分析】
・最高効率: B社（AI研修）- 売上320万 / 人件費26.7万 = ROI 12.0倍
・最低効率: G社（AI Agent）- 売上2500万 / 人件費310万 = ROI 8.1倍
・全社平均ROI: 9.2倍

【リソース配分の最適化提案】
・田中太郎(780h): 稼働率が高い。C社・G社の工数分散を検討
・高橋次郎(170h): 余裕あり。新規案件のアサイン候補
・山本五郎(620h): G社完了後にL社へシフト推奨

【キャッシュフロー×売上タイミング分析】
・4-6月: 入金A社480万のみ。運転資金に注意
・10-12月: G社2500万+H社400万の入金。資金に余裕
・年間運転資金ピーク: 8月（累積CF最低値）

⚠️ これはGemini API未接続時のデモレスポンスです。"""

MOCK_COMPARISON = """📈 **業界比較分析（デモ）**

【IT業界平均との比較】
・粗利率: J.NOVA 60.7% vs 業界平均 45% → ✅ 優秀
・人件費率: J.NOVA 32.3% vs 業界平均 40% → ✅ 効率的
・固定費率: J.NOVA 32.3% vs 業界平均 30% → ⚠️ やや高め

【改善ポイント】
・固定費の見直し（家賃・ライセンス費の最適化）
・高利益率案件（B社70%）の比率を増やす営業戦略

⚠️ これはGemini API未接続時のデモレスポンスです。"""


class GeminiClient:
    """
    Gemini 2.5 Pro API wrapper
    横断分析・大規模データ比較・クロス分析用
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def cross_analyze(
        self,
        data: dict,
        analysis_type: str = "general",
    ) -> str:
        """
        横断分析（売上×在庫×人件費のクロス分析）

        analysis_type:
        - "general": 全体横断分析
        - "efficiency": 効率分析（売上/人件費）
        - "cashflow_risk": CFリスク分析
        - "resource": リソース最適化
        """
        if not self.is_configured:
            return MOCK_CROSS_ANALYSIS

        prompt = self._build_cross_prompt(data, analysis_type)
        return await self._request(prompt)

    async def compare_industry(
        self,
        company_data: dict,
        industry: str = "IT",
    ) -> str:
        """業界比較分析"""
        if not self.is_configured:
            return MOCK_COMPARISON

        prompt = (
            f"以下の{industry}企業の経営データを業界平均と比較分析してください。\n\n"
            f"データ: {json.dumps(company_data, ensure_ascii=False)}\n\n"
            "粗利率、人件費率、固定費率を業界平均と比較し、改善点を提案してください。"
        )
        return await self._request(prompt)

    async def stream_analyze(
        self,
        data: dict,
        question: str,
    ) -> AsyncGenerator[str, None]:
        """ストリーミング横断分析"""
        if not self.is_configured:
            # モック: チャンクに分けて返す
            for line in MOCK_CROSS_ANALYSIS.split("\n"):
                yield json.dumps({"text": line + "\n"})
            return

        prompt = (
            f"経営データ:\n{json.dumps(data, ensure_ascii=False)}\n\n"
            f"質問: {question}\n\n"
            "横断的に分析して具体的な数字で回答してください。"
        )

        url = f"{self.base_url}/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2048},
                },
            ) as resp:
                if resp.status_code != 200:
                    yield json.dumps({"error": f"Gemini API error: {resp.status_code}"})
                    return
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        evt = json.loads(line[6:])
                        parts = evt.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if "text" in part:
                                yield json.dumps({"text": part["text"]})
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    def _build_cross_prompt(self, data: dict, analysis_type: str) -> str:
        """横断分析用プロンプトを構築"""
        base = f"以下の経営データを横断的に分析してください。\n\nデータ:\n{json.dumps(data, ensure_ascii=False)}\n\n"
        type_prompts = {
            "general": "売上・原価・人件費・キャッシュフローを横断的に分析し、経営改善のポイントを3つ提案してください。",
            "efficiency": "各案件の売上/人件費比率（ROI）を計算し、最も効率の良い案件と悪い案件を特定してください。",
            "cashflow_risk": "月別キャッシュフローを分析し、資金繰りリスクが高い月と対策を提案してください。",
            "resource": "社員別の稼働率を分析し、リソース配分の最適化案を提案してください。",
        }
        return base + type_prompts.get(analysis_type, type_prompts["general"])

    async def _request(self, prompt: str) -> str:
        """Gemini API 単発リクエスト"""
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2048},
                },
            )
            if resp.status_code != 200:
                raise Exception(f"Gemini API error: {resp.status_code}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise Exception("Gemini: no candidates returned")
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts)
