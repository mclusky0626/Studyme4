from __future__ import annotations

from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.fake_provider import FakeProvider
from app.llm.openai_provider import OpenAICompatibleProvider


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "fake":
        return FakeProvider()
    api_key = settings.provider_api_key()
    if not api_key:
        raise RuntimeError(f"{settings.llm_provider} API key is not configured")
    if settings.llm_provider == "openai":
        return OpenAICompatibleProvider(
            api_key=api_key,
            chat_model=settings.openai_chat_model,
            embedding_model=settings.openai_embedding_model,
        )
    if settings.llm_provider == "gemini":
        return OpenAICompatibleProvider(
            api_key=api_key,
            chat_model=settings.gemini_chat_model,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return OpenAICompatibleProvider(
        api_key=api_key,
        chat_model=settings.grok_chat_model,
        base_url="https://api.x.ai/v1",
    )


def build_participation_provider(
    settings: Settings, default_provider: LLMProvider
) -> LLMProvider | None:
    if settings.participation_judge_provider == "off":
        return None
    if settings.participation_judge_provider == "llm":
        return default_provider
    base_url = settings.ollama_base_url.rstrip("/") + "/v1"
    return OpenAICompatibleProvider(
        api_key="ollama",
        chat_model=settings.ollama_participation_model,
        base_url=base_url,
    )
