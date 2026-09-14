from __future__ import annotations

import os

from app.llm.ollama import OllamaClient
from app.llm.openai_client import OpenAIClient


class LLMClient:
    """Select an LLM provider at runtime and fail over safely when possible."""

    def __init__(self):
        self.openai = OpenAIClient()
        self.ollama = OllamaClient()
        self.ollama_fallback = OllamaClient(os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.2:3b"))

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
        return "openai" if self.openai.available else "ollama"

    async def generate(self, system: str, history: list[dict], message: str, web_search: bool = False) -> str:
        if self.active_provider == "openai":
            try:
                return await self.openai.generate(system, history, message, web_search=web_search)
            except Exception:
                if web_search:
                    raise
                return await self.ollama.generate(system, history, message)

        if web_search:
            raise RuntimeError("web search requires the OpenAI provider")

        try:
            return await self.ollama.generate(system, history, message)
        except Exception as primary_error:
            if self.ollama_fallback.model == self.ollama.model:
                raise primary_error
            return await self.ollama_fallback.generate(system, history, message)

    async def stream(self, system: str, history: list[dict], message: str, web_search: bool = False):
        """Yield response text incrementally, with a safe Ollama model fallback."""
        if self.active_provider == "openai":
            try:
                yield await self.openai.generate(system, history, message, web_search=web_search)
                return
            except Exception:
                if web_search:
                    raise
                async for delta in self.ollama.stream(system, history, message):
                    yield delta
                return

        if web_search:
            raise RuntimeError("web search requires the OpenAI provider")

        try:
            async for delta in self.ollama.stream(system, history, message):
                yield delta
        except Exception as primary_error:
            if self.ollama_fallback.model == self.ollama.model:
                raise primary_error
            async for delta in self.ollama_fallback.stream(system, history, message):
                yield delta
