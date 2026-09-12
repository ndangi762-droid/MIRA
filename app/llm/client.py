from __future__ import annotations

from app.config import LLM_PROVIDER, OPENAI_API_KEY
from app.llm.ollama import OllamaClient
from app.llm.openai_client import OpenAIClient


class LLMClient:
    """Select OpenAI when configured, otherwise keep local Ollama as fallback."""

    def __init__(self):
        self.openai = OpenAIClient()
        self.ollama = OllamaClient()
        self.provider = LLM_PROVIDER

    @property
    def active_provider(self) -> str:
        if self.provider == "openai":
            return "openai"
        if self.provider == "ollama":
            return "ollama"
        return "openai" if OPENAI_API_KEY.strip() else "ollama"

    async def generate(self, system: str, history: list[dict], message: str, web_search: bool = False) -> str:
        if self.active_provider == "openai":
            return await self.openai.generate(system, history, message, web_search=web_search)
        if web_search:
            raise RuntimeError("web search requires the OpenAI provider")
        return await self.ollama.generate(system, history, message)
