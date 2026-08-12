from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.common.ids import new_id
from app.common.time import utcnow


class MemoryType(StrEnum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    DISLIKE = "dislike"
    EVENT = "event"
    PLAN = "plan"
    PROMISE = "promise"
    GOAL = "goal"
    STATE = "state"
    OPINION = "opinion"
    SHARED_EXPERIENCE = "shared_experience"
    INSIDE_JOKE = "inside_joke"
    BOT_PROMISE = "bot_promise"


class MemoryStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    DELETED = "deleted"
    EXPIRED = "expired"


class Visibility(StrEnum):
    DM_PRIVATE = "dm_private"
    CHANNEL = "channel"
    GUILD = "guild"
    USER_PRIVATE = "user_private"


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    discord_user_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    current_display_name: Mapped[str] = mapped_column(String(100))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    aliases: Mapped[list[IdentityAlias]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class IdentityAlias(Base):
    __tablename__ = "identity_aliases"
    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", "alias", name="uq_alias_user_guild_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    guild_id: Mapped[str | None] = mapped_column(String(32), index=True)
    alias: Mapped[str] = mapped_column(String(100), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="aliases")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("discord_message_id", name="uq_message_discord_id"),
        Index("ix_messages_context", "guild_id", "channel_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    discord_message_id: Mapped[str] = mapped_column(String(32))
    guild_id: Mapped[str | None] = mapped_column(String(32), index=True)
    channel_id: Mapped[str] = mapped_column(String(32), index=True)
    author_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reply_to_message_id: Mapped[str | None] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_dm: Mapped[bool] = mapped_column(Boolean, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_memory_confidence"),
        CheckConstraint("importance >= 0 AND importance <= 1", name="ck_memory_importance"),
        Index(
            "ix_memories_scope_subject",
            "subject_user_id",
            "guild_id",
            "channel_id",
            "visibility",
            "status",
        ),
        Index("ix_memories_normalized_key", "subject_user_id", "normalized_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=MemoryStatus.CANDIDATE.value)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False)
    is_explicit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    guild_id: Mapped[str | None] = mapped_column(String(32), index=True)
    channel_id: Mapped[str | None] = mapped_column(String(32), index=True)
    source_message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="RESTRICT"), index=True
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_recalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recall_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536).with_variant(JSON, "sqlite"), nullable=True
    )

    revisions: Mapped[list[MemoryRevision]] = relationship(
        back_populates="memory", cascade="all, delete-orphan"
    )


class MemoryRevision(Base):
    __tablename__ = "memory_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    memory_id: Mapped[str] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"), index=True
    )
    previous_content: Mapped[str] = mapped_column(Text, nullable=False)
    new_content: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    source_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    memory: Mapped[Memory] = relationship(back_populates="revisions")


class Relationship(Base, TimestampMixin):
    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint(
            "guild_id", "user_a_id", "user_b_id", "relation_type", name="uq_relationship"
        ),
        CheckConstraint("closeness >= 0 AND closeness <= 1", name="ck_relation_closeness"),
        CheckConstraint("trust >= 0 AND trust <= 1", name="ck_relation_trust"),
        CheckConstraint("playfulness >= 0 AND playfulness <= 1", name="ck_relation_playfulness"),
        CheckConstraint("tension >= 0 AND tension <= 1", name="ck_relation_tension"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    guild_id: Mapped[str] = mapped_column(String(32), index=True)
    user_a_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_b_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    relation_type: Mapped[str] = mapped_column(String(32), default="unknown")
    closeness: Mapped[float] = mapped_column(Float, default=0.3)
    trust: Mapped[float] = mapped_column(Float, default=0.3)
    playfulness: Mapped[float] = mapped_column(Float, default=0.2)
    tension: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    events: Mapped[list[RelationshipEvent]] = relationship(
        back_populates="relationship", cascade="all, delete-orphan"
    )


class RelationshipEvent(Base):
    __tablename__ = "relationship_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    relationship_id: Mapped[str] = mapped_column(
        ForeignKey("relationships.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    is_explicit: Mapped[bool] = mapped_column(Boolean, default=False)
    source_message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    relationship: Mapped[Relationship] = relationship(back_populates="events")


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    __table_args__ = (Index("ix_summary_scope", "guild_id", "channel_id", "ended_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    guild_id: Mapped[str | None] = mapped_column(String(32))
    channel_id: Mapped[str] = mapped_column(String(32), index=True)
    topic: Mapped[str] = mapped_column(String(200), default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    participants: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536).with_variant(JSON, "sqlite"), nullable=True
    )


class BotState(Base):
    __tablename__ = "bot_states"
    __table_args__ = (UniqueConstraint("bot_id", "guild_id", name="uq_bot_state"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    bot_id: Mapped[str] = mapped_column(String(32))
    guild_id: Mapped[str | None] = mapped_column(String(32))
    persona_version: Mapped[str] = mapped_column(String(40), default="v1")
    current_mood: Mapped[str] = mapped_column(String(40), default="neutral")
    active_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ChannelState(Base):
    __tablename__ = "channel_states"

    channel_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    guild_id: Mapped[str | None] = mapped_column(String(32), index=True)
    last_partner_discord_id: Mapped[str | None] = mapped_column(String(32))
    last_bot_message_id: Mapped[str | None] = mapped_column(String(32))
    engaged_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_spontaneous_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ServerPolicy(Base):
    __tablename__ = "server_policies"

    guild_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_participation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
