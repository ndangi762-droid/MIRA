import httpx
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL

class OllamaClient:
    def __init__(self):
        self.url = OLLAMA_BASE_URL.rstrip("/") + "/api/chat"
        self.model = OLLAMA_MODEL

    async def generate(self, system: str, history: list[dict], message: str) -> str:
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        payload = {"model": self.model, "messages": messages, "stream": False}

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(self.url, json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
