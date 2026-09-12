import os


def test_openai_provider_is_selected_when_key_exists(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    from app.llm.client import LLMClient

    client = LLMClient()
    assert client.active_provider == "openai"


def test_ollama_provider_is_default_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    from app.llm.client import LLMClient

    client = LLMClient()
    assert client.active_provider == "ollama"
