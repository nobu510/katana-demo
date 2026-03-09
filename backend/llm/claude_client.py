"""
Claude API クライアント（メイン分析・チャット・仕訳チェック）
- ストリーミングチャット (SSE)
- 単発リクエスト (OCR, 仕訳チェック)
- 経営分析 (専用プロンプト)
"""
from __future__ import annotations
import json
import os
from typing import AsyncGenerator

import httpx


class ClaudeClient:
    """Claude API wrapper with streaming support"""

    def __init__(self):
        self.api_key = os.environ.get("CLAUDE_API_KEY", "")
        self.model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.base_url = "https://api.anthropic.com/v1/messages"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: str,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """SSEストリーミングでチャット応答を返す"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "stream": True,
                    "system": system_prompt,
                    "messages": messages,
                },
            ) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    try:
                        err_msg = json.loads(error_body).get("error", {}).get("message", "API error")
                    except Exception:
                        err_msg = "API error"
                    yield json.dumps({"error": err_msg})
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
                            yield json.dumps({"text": delta["text"]})
                    elif evt_type == "message_stop":
                        break

    async def single_request(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """単発リクエスト（OCR・仕訳チェック等）"""
        body: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            body["system"] = system_prompt
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self.base_url,
                headers=self.headers,
                json=body,
            )
            data = resp.json()
            if resp.status_code != 200:
                raise Exception(data.get("error", {}).get("message", "API error"))
            return "".join(
                b["text"] for b in data.get("content", []) if b.get("type") == "text"
            )

    async def analyze_financials(
        self,
        summary_data: dict,
        question: str,
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        経営分析（ストリーミング）
        summary_dataにダッシュボードデータを渡してClaude分析
        """
        context = json.dumps(summary_data, ensure_ascii=False, indent=2)
        messages = [
            {
                "role": "user",
                "content": f"以下の経営データを分析してください。\n\n【経営データ】\n{context}\n\n【質問】\n{question}",
            }
        ]
        async for chunk in self.stream_chat(messages, system_prompt, max_tokens=2048):
            yield chunk

    async def check_journal_entry(
        self,
        entry: dict,
    ) -> str:
        """
        仕訳チェック
        勘定科目・金額・税区分の妥当性を検証
        """
        prompt = (
            "以下の仕訳データを会計の観点からチェックしてください。\n"
            "問題があれば指摘し、修正案を提示してください。\n"
            "問題なければ「OK」と回答してください。\n\n"
            f"仕訳データ: {json.dumps(entry, ensure_ascii=False)}"
        )
        return await self.single_request(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="あなたは日本の会計基準に精通した経理AIアシスタントです。仕訳の妥当性を簡潔にチェックしてください。",
        )
