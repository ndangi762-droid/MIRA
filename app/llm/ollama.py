import json

import httpx
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaClient:
    def __init__(self):
        self.url = OLLAMA_BASE_URL.rstrip("/") + "/api/chat"
        self.model = OLLAMA_MODEL

    def _messages(self, system: str, history: list[dict], message: str) -> list[dict]:
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        return messages

    async def generate(self, system: str, history: list[dict], message: str) -> str:
        payload = {"model": self.model, "messages": self._messages(system, history, message), "stream": False}

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(self.url, json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]

    async def stream(self, system: str, history: list[dict], message: str):
        payload = {"model": self.model, "messages": self._messages(system, history, message), "stream": True}

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", self.url, json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    delta = data.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                    if data.get("done"):
                        break
