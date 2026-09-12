from __future__ import annotations

import os
import httpx


class OpenAIClient:
    """Small Responses API client with optional built-in web search."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        self.url = "https://api.openai.com/v1/responses"

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, system: str, history: list[dict], message: str, web_search: bool = False) -> str:
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        input_items = []
        for item in history:
            role = item.get("role")
            content = item.get("content", "")
            if role in {"user", "assistant"}:
                input_items.append({"role": role, "content": content})
        input_items.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "instructions": system,
            "input": input_items,
        }
        if web_search:
            payload["tools"] = [{"type": "web_search"}]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        text = data.get("output_text")
        if text:
            return text.strip()
        raise RuntimeError("OpenAI response did not contain output_text")
