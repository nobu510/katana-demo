"""
OpenAI クライアント（トレンド検索・市場分析用）
"""
from __future__ import annotations
import json
import os
from typing import AsyncGenerator

import httpx


# OpenAI APIが未設定時のモックレスポンス
MOCK_TRENDS = [
    {
        "title": "生成AI市場が急拡大",
        "summary": "2026年国内市場規模1.2兆円突破見込み。企業導入率45%に到達。",
        "tag": "注目",
        "relevance": 0.95,
    },
    {
        "title": "AI Agent活用が本格化",
        "summary": "自律型AIが業務プロセスを自動化。人件費30%削減の事例が続出。",
        "tag": "急上昇",
        "relevance": 0.92,
    },
    {
        "title": "RAG技術で社内DX加速",
        "summary": "社内文書×AIで知識検索が革命的に。導入企業の生産性25%向上。",
        "tag": "トレンド",
        "relevance": 0.88,
    },
    {
        "title": "IT導入補助金2026",
        "summary": "AI・クラウド導入に最大450万円。申請締切は6月30日。",
        "tag": "締切注意",
        "relevance": 0.85,
    },
    {
        "title": "キャッシュフロー予測AI",
        "summary": "入金予測精度90%超。資金繰り不安を解消する中小企業が増加。",
        "tag": "トレンド",
        "relevance": 0.82,
    },
]

MOCK_MARKET_ANALYSIS = """📰 **市場動向レポート（デモ）**

【IT業界 2026年トレンド】
1. 生成AI市場: 国内1.2兆円規模、前年比+40%
2. AI Agent: 自律型業務自動化が本格普及
3. RAG/検索AI: 社内ナレッジ活用の標準技術に

【J.NOVAへの影響】
・G社「AI Agent開発」案件は市場成長の追い風
・AI研修需要の拡大（B社・H社型案件の増加見込み）
・セキュリティ需要の高まり（E社型案件の拡大余地）

【推奨アクション】
・AI Agent分野の営業強化（市場成長率+40%）
・IT導入補助金の活用提案を顧客に展開
・RAG技術を自社サービスに組み込み差別化

⚠️ これはOpenAI API未接続時のデモレスポンスです。"""


class OpenAIClient:
    """
    OpenAI API wrapper
    トレンド検索・市場動向分析・業界ニュース要約
    """

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def search_trends(
        self,
        query: str,
        industry: str = "IT",
        limit: int = 5,
    ) -> list[dict]:
        """
        トレンド検索
        業界関連のトレンド・ニュースを検索して構造化データで返す
        """
        if not self.is_configured:
            # フィルタリング付きモック
            q_lower = query.lower()
            filtered = [
                t for t in MOCK_TRENDS
                if q_lower in t["title"].lower() or q_lower in t["summary"].lower()
            ]
            return filtered[:limit] if filtered else MOCK_TRENDS[:limit]

        prompt = (
            f"「{query}」に関連する{industry}業界の最新トレンドを{limit}件、"
            "以下のJSON配列形式で返してください。JSON以外出力しないでください。\n"
            '[{"title":"タイトル","summary":"要約(50文字以内)","tag":"タグ","relevance":0.0-1.0}]'
        )

        text = await self._request(prompt)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return MOCK_TRENDS[:limit]

    async def market_analysis(
        self,
        company_data: dict,
        industry: str = "IT",
    ) -> str:
        """市場動向分析レポート"""
        if not self.is_configured:
            return MOCK_MARKET_ANALYSIS

        prompt = (
            f"以下の{industry}企業のデータを元に、市場動向レポートを作成してください。\n\n"
            f"企業データ: {json.dumps(company_data, ensure_ascii=False)}\n\n"
            "1. 業界トレンド 2. 自社への影響 3. 推奨アクション の3部構成で。"
        )
        return await self._request(prompt)

    async def stream_market_analysis(
        self,
        company_data: dict,
        question: str,
    ) -> AsyncGenerator[str, None]:
        """ストリーミング市場分析"""
        if not self.is_configured:
            for line in MOCK_MARKET_ANALYSIS.split("\n"):
                yield json.dumps({"text": line + "\n"})
            return

        prompt = (
            f"企業データ:\n{json.dumps(company_data, ensure_ascii=False)}\n\n"
            f"質問: {question}\n\n"
            "市場動向の観点から分析して回答してください。"
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "stream": True,
                },
            ) as resp:
                if resp.status_code != 200:
                    yield json.dumps({"error": f"OpenAI API error: {resp.status_code}"})
                    return
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        evt = json.loads(data_str)
                        delta = evt.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            yield json.dumps({"text": delta["content"]})
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    async def _request(self, prompt: str) -> str:
        """OpenAI API 単発リクエスト"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                },
            )
            if resp.status_code != 200:
                raise Exception(f"OpenAI API error: {resp.status_code}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]
