import json

import httpx

from app.config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiClient:
    """Gemini REST client for Render/cloud deployments."""

    def __init__(self):
        self.api_key = GEMINI_API_KEY.strip()
        self.model = GEMINI_MODEL.strip() or "gemini-3.1-flash-lite"
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

    def _payload(self, system: str, history: list[dict], message: str, web_search: bool = False) -> dict:
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": self._contents(history, message),
        }
        if web_search:
            # Gemini's Google Search grounding lets MIRA answer current questions
            # from live web results while keeping the model/API key on the server.
            payload["tools"] = [{"google_search": {}}]
        return payload

    def _headers(self) -> dict:
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _url(self, method: str) -> str:
        return f"{self.base_url}/{self.model}:{method}"

    @staticmethod
    def _raise_with_context(response: httpx.Response) -> None:
        if response.is_error:
            detail = response.text.strip().replace("\n", " ")
            if len(detail) > 800:
                detail = detail[:800]
            raise RuntimeError(f"Gemini HTTP {response.status_code}: {detail}")

    @staticmethod
    def _extract_text(data: dict) -> str:
        parts = []
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text = part.get("text", "")
                if text:
                    parts.append(text)
        text = "".join(parts).strip()
        if not text:
            raise RuntimeError("Gemini response did not contain text")
        return text

    async def generate(self, system: str, history: list[dict], message: str, web_search: bool = False) -> str:
        if not self.available:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
            response = await client.post(
                self._url("generateContent"),
                headers=self._headers(),
                json=self._payload(system, history, message, web_search=web_search),
            )
            self._raise_with_context(response)
            data = response.json()

        return self._extract_text(data)

    async def stream(self, system: str, history: list[dict], message: str, web_search: bool = False):
        if not self.available:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        url = self._url("streamGenerateContent") + "?alt=sse"
        async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
            async with client.stream(
                "POST",
                url,
                headers=self._headers(),
                json=self._payload(system, history, message, web_search=web_search),
            ) as response:
                self._raise_with_context(response)
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
