from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import MemoryType, Visibility


class MemoryCandidate(BaseModel):
    should_store: bool = True
    memory_type: MemoryType
    subject_discord_user_id: str
    content: str = Field(min_length=3, max_length=1000)
    normalized_key: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    importance: float = Field(ge=0, le=1)
    visibility: Visibility
    is_explicit: bool = True
    sensitive: bool = False
    valid_until: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_compatible_extractor_fields(cls, value: Any) -> Any:
        """Normalize common model variations without weakening ID/content validation."""
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.setdefault(
            "subject_discord_user_id",
            normalized.get("subject_id") or normalized.get("user_id"),
        )
        normalized.setdefault(
            "content",
            normalized.get("memory") or normalized.get("fact") or normalized.get("text"),
        )
        if "should_store" not in normalized:
            action = str(normalized.get("action", "add")).casefold()
            normalized["should_store"] = action not in {"skip", "ignore", "none", "delete"}
        normalized.setdefault("importance", 0.55)
        normalized.setdefault("confidence", 0.9 if normalized.get("is_explicit", True) else 0.65)
        normalized.setdefault("visibility", Visibility.GUILD.value)
        if not normalized.get("memory_type"):
            normalized["memory_type"] = cls._infer_memory_type(
                str(normalized.get("normalized_key", "")),
                str(normalized.get("content", "")),
            )
        return normalized

    @staticmethod
    def _infer_memory_type(normalized_key: str, content: str) -> str:
        value = f"{normalized_key} {content}".casefold()
        mappings = (
            (("dislike", "싫어", "싫어함"), MemoryType.DISLIKE),
            (("plan", "schedule", "일정", "예정"), MemoryType.PLAN),
            (("goal", "dream", "꿈", "목표"), MemoryType.GOAL),
            (("promise", "약속"), MemoryType.PROMISE),
            (("event", "했음", "다녀옴"), MemoryType.EVENT),
            (("state", "상태"), MemoryType.STATE),
            (("opinion", "생각"), MemoryType.OPINION),
            (("profile", "age", "gender", "나이", "학생"), MemoryType.PROFILE),
            (
                ("preference", "favorite", "food:", "media:", "hobby:", "좋아"),
                MemoryType.PREFERENCE,
            ),
        )
        for needles, memory_type in mappings:
            if any(needle in value for needle in needles):
                return memory_type.value
        return MemoryType.PROFILE.value

    @field_validator("subject_discord_user_id")
    @classmethod
    def discord_id_must_be_numeric(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("subject_discord_user_id must be a numeric Discord ID")
        return value


class ValidationContext(BaseModel):
    author_discord_user_id: str
    guild_id: str | None
    channel_id: str
    is_dm: bool
    source_message_id: str


class ValidatedMemory(BaseModel):
    candidate: MemoryCandidate
    visibility: Visibility
    status_reason: str = "validated"


class RankedMemory(BaseModel):
    id: str
    content: str
    memory_type: str
    confidence: float
    importance: float
    score: float
    source_message_id: str
    valid_from: datetime
