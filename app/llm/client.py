from __future__ import annotations

import os

from app.llm.ollama import OllamaClient
from app.llm.openai_client import OpenAIClient


class LLMClient:
    """Select an LLM provider at runtime.

    ``auto`` prefers OpenAI only when an API key is currently configured;
    otherwise it falls back to local Ollama. Reading environment variables at
    runtime also keeps tests and local configuration changes deterministic.
    """

    def __init__(self):
        self.openai = OpenAIClient()
        self.ollama = OllamaClient()

    @property
    def provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "auto").strip().lower()

    @property
    def active_provider(self) -> str:
        provider = self.provider
        if provider == "openai":
            return "openai"
        if provider == "ollama":
            return "ollama"
        return "openai" if os.getenv("OPENAI_API_KEY", "").strip() else "ollama"

    async def generate(self, system: str, history: list[dict], message: str, web_search: bool = False) -> str:
        if self.active_provider == "openai":
            return await self.openai.generate(system, history, message, web_search=web_search)
        if web_search:
            raise RuntimeError("web search requires the OpenAI provider")
        return await self.ollama.generate(system, history, message)
