from __future__ import annotations

import os

from app.llm.gemini_client import GeminiClient
from app.llm.ollama import OllamaClient
from app.llm.openai_client import OpenAIClient


class LLMClient:
    """Select an LLM provider at runtime with Gemini free-tier support."""

    def __init__(self):
        self.gemini = GeminiClient()
        self.openai = OpenAIClient()
        self.ollama = OllamaClient()
        self.ollama_fallback = OllamaClient(os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.2:3b"))

    @property
    def provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "auto").strip().lower()

    @property
    def active_provider(self) -> str:
        provider = self.provider
        if provider in {"gemini", "openai", "ollama"}:
            return provider
        if self.gemini.available:
            return "gemini"
        if self.openai.available:
            return "openai"
        return "ollama"

    async def generate(self, system: str, history: list[dict], message: str, web_search: bool = False) -> str:
        active = self.active_provider

        if active == "gemini":
            try:
                return await self.gemini.generate(system, history, message, web_search=web_search)
            except Exception:
                if self.openai.available and not web_search:
                    return await self.openai.generate(system, history, message)
                raise

        if active == "openai":
            try:
                return await self.openai.generate(system, history, message, web_search=web_search)
            except Exception:
                if web_search:
                    raise
                return await self.ollama.generate(system, history, message)

        if web_search:
            raise RuntimeError("web search requires a web-enabled provider")

        try:
            return await self.ollama.generate(system, history, message)
        except Exception as primary_error:
            if self.ollama_fallback.model == self.ollama.model:
                raise primary_error
            return await self.ollama_fallback.generate(system, history, message)

    async def stream(self, system: str, history: list[dict], message: str, web_search: bool = False):
        """Yield response text incrementally with Gemini/Ollama support."""
        active = self.active_provider

        if active == "gemini":
            try:
                async for delta in self.gemini.stream(system, history, message, web_search=web_search):
                    yield delta
                return
            except Exception:
                if self.openai.available and not web_search:
                    yield await self.openai.generate(system, history, message)
                    return
                raise

        if active == "openai":
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
            raise RuntimeError("web search requires a web-enabled provider")

        try:
            async for delta in self.ollama.stream(system, history, message):
                yield delta
        except Exception as primary_error:
            if self.ollama_fallback.model == self.ollama.model:
                raise primary_error
            async for delta in self.ollama_fallback.stream(system, history, message):
                yield delta
