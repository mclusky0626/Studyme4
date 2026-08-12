from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    discord_token: SecretStr = SecretStr("")
    discord_application_id: int | None = None
    wake_word: str = "스터디미야"

    database_url: str = "postgresql+asyncpg://studyme:studyme@localhost:5432/studyme"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: Literal["openai", "gemini", "grok", "fake"] = "openai"
    openai_api_key: SecretStr = SecretStr("")
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_chat_model: str = "gemini-2.5-flash-lite"
    grok_api_key: SecretStr = SecretStr("")
    grok_chat_model: str = "grok-3-mini"

    bot_name: str = "스터디미"
    bot_persona: str = "친근하고 간결한 한국어 반말을 쓰되 AI임을 숨기지 않는다."
    persona_version: str = "v1"

    memory_extraction_enabled: bool = True
    auto_participation_enabled: bool = False
    recent_message_limit: int = Field(default=16, ge=4, le=50)
    memory_top_k: int = Field(default=6, ge=1, le=20)
    engage_window_seconds: int = Field(default=90, ge=10, le=600)
    spontaneous_cooldown_seconds: int = Field(default=300, ge=30, le=3600)

    run_bot: bool = True
    health_host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    def provider_api_key(self) -> str:
        keys = {
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "grok": self.grok_api_key,
            "fake": SecretStr("fake"),
        }
        return keys[self.llm_provider].get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
