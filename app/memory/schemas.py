from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

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
