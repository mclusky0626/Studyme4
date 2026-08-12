from __future__ import annotations

from functools import lru_cache
from pathlib import Path
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

    bot_name: str = "미유"
    bot_persona: str = "친근하고 간결한 한국어 반말을 쓰되 AI임을 숨기지 않는다."
    bot_persona_file: str = "persona.md"
    persona_version: str = "v1"

    memory_extraction_enabled: bool = True
    auto_participation_enabled: bool = True
    participation_judge_provider: Literal["llm", "ollama", "off"] = "llm"
    participation_reply_threshold: float = Field(default=0.78, ge=0.5, le=1)
    participation_react_threshold: float = Field(default=0.72, ge=0.5, le=1)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_participation_model: str = "qwen2.5:3b"
    recent_message_limit: int = Field(default=16, ge=4, le=50)
    memory_top_k: int = Field(default=6, ge=1, le=20)
    engage_window_seconds: int = Field(default=90, ge=10, le=600)
    spontaneous_cooldown_seconds: int = Field(default=300, ge=30, le=3600)
    response_max_bubbles: int = Field(default=4, ge=1, le=8)
    response_bubble_max_chars: int = Field(default=700, ge=80, le=1900)

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

    @field_validator("discord_application_id", mode="before")
    @classmethod
    def blank_application_id_is_none(cls, value: object) -> object:
        return None if value == "" else value

    def provider_api_key(self) -> str:
        keys = {
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "grok": self.grok_api_key,
            "fake": SecretStr("fake"),
        }
        return keys[self.llm_provider].get_secret_value()

    def persona_text(self) -> str:
        """Load a long persona from a UTF-8 file, falling back to BOT_PERSONA."""
        if self.bot_persona_file:
            path = Path(self.bot_persona_file).expanduser()
            if path.is_file():
                value = path.read_text(encoding="utf-8").strip()
                if value:
                    return value
        return self.bot_persona.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
