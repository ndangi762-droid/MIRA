import json

import httpx

from app.config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiClient:
    """Minimal Gemini REST client with native SSE streaming."""

    def __init__(self):
        self.api_key = GEMINI_API_KEY.strip()
        self.model = GEMINI_MODEL
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _contents(self, history: list[dict], message: str) -> list[dict]:
        contents = []
        for item in history:
            role = item.get("role")
            content = item.get("content", "")
            if role == "assistant":
                role = "model"
            if role in {"user", "model"} and content:
                contents.append({"role": role, "parts": [{"text": content}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        return contents

    def _payload(self, system: str, history: list[dict], message: str) -> dict:
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": self._contents(history, message),
        }

    def _headers(self) -> dict:
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def generate(self, system: str, history: list[dict], message: str, web_search: bool = False) -> str:
        if not self.available:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        if web_search:
            raise RuntimeError("web search is not enabled for the free Gemini provider")

        url = f"{self.base_url}/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                json=self._payload(system, history, message),
            )
            response.raise_for_status()
            data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Gemini response did not contain text")

    async def stream(self, system: str, history: list[dict], message: str, web_search: bool = False):
        if not self.available:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        if web_search:
            raise RuntimeError("web search is not enabled for the free Gemini provider")

        url = f"{self.base_url}/{self.model}:streamGenerateContent?alt=sse"
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                url,
                headers=self._headers(),
                json=self._payload(system, history, message),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw or raw == "[DONE]":
                        continue
                    data = json.loads(raw)
                    for candidate in data.get("candidates", []):
                        for part in candidate.get("content", {}).get("parts", []):
                            text = part.get("text", "")
                            if text:
                                yield text
