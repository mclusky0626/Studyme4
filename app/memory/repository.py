from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utcnow
from app.db.models import (
    IdentityAlias,
    Memory,
    MemoryRevision,
    MemoryStatus,
    Message,
    Relationship,
    User,
)
from app.memory.privacy import MemoryScope, visible_memory_clause


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, discord_user_id: str, display_name: str, guild_id: str | None) -> User:
        user = await self.session.scalar(
            select(User).where(User.discord_user_id == discord_user_id)
        )
        now = utcnow()
        if user is None:
            user = User(
                discord_user_id=discord_user_id,
                current_display_name=display_name,
                last_seen_at=now,
            )
            self.session.add(user)
            await self.session.flush()
        else:
            user.current_display_name = display_name
            user.last_seen_at = now

        alias = await self.session.scalar(
            select(IdentityAlias).where(
                IdentityAlias.user_id == user.id,
                IdentityAlias.guild_id == guild_id,
                IdentityAlias.alias == display_name,
            )
        )
        if alias is None:
            self.session.add(IdentityAlias(user_id=user.id, guild_id=guild_id, alias=display_name))
        else:
            alias.last_seen_at = now
        return user

    async def by_discord_id(self, discord_user_id: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.discord_user_id == discord_user_id)
        )


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        *,
        discord_message_id: str,
        guild_id: str | None,
        channel_id: str,
        author_user_id: str,
        reply_to_message_id: str | None,
        content: str,
        created_at: datetime,
        is_dm: bool,
    ) -> Message:
        existing = await self.session.scalar(
            select(Message).where(Message.discord_message_id == discord_message_id)
        )
        if existing:
            return existing
        message = Message(
            discord_message_id=discord_message_id,
            guild_id=guild_id,
            channel_id=channel_id,
            author_user_id=author_user_id,
            reply_to_message_id=reply_to_message_id,
            content=content,
            created_at=created_at,
            is_dm=is_dm,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def recent(self, scope: MemoryScope, limit: int) -> list[tuple[Message, User]]:
        stmt = (
            select(Message, User)
            .join(User, Message.author_user_id == User.id)
            .where(Message.channel_id == scope.channel_id, Message.deleted_at.is_(None))
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        if scope.is_dm:
            stmt = stmt.where(Message.is_dm.is_(True), Message.guild_id.is_(None))
        else:
            stmt = stmt.where(Message.is_dm.is_(False), Message.guild_id == scope.guild_id)
        rows = list((await self.session.execute(stmt)).all())
        rows.reverse()
        return rows


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def active_by_key(self, subject_user_id: str, normalized_key: str) -> Memory | None:
        return await self.session.scalar(
            select(Memory)
            .where(
                Memory.subject_user_id == subject_user_id,
                Memory.normalized_key == normalized_key,
                Memory.status == MemoryStatus.ACTIVE.value,
            )
            .order_by(desc(Memory.valid_from))
            .limit(1)
        )

    async def conversational_candidates(
        self,
        *,
        scope: MemoryScope,
        subject_user_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[Memory]:
        now = utcnow()
        stmt = (
            select(Memory)
            .where(
                Memory.status == MemoryStatus.ACTIVE.value,
                visible_memory_clause(scope),
                (Memory.valid_until.is_(None) | (Memory.valid_until > now)),
            )
            .order_by(desc(Memory.updated_at))
            .limit(limit)
        )
        if subject_user_ids:
            stmt = stmt.where(Memory.subject_user_id.in_(subject_user_ids))
        return list((await self.session.scalars(stmt)).all())

    async def list_owned(self, subject_user_id: str, limit: int = 50) -> list[Memory]:
        return list(
            (
                await self.session.scalars(
                    select(Memory)
                    .where(
                        Memory.subject_user_id == subject_user_id,
                        Memory.status.in_(
                            [
                                MemoryStatus.ACTIVE.value,
                                MemoryStatus.DISPUTED.value,
                                MemoryStatus.SUPERSEDED.value,
                            ]
                        ),
                    )
                    .order_by(desc(Memory.updated_at))
                    .limit(limit)
                )
            ).all()
        )

    async def get_owned(self, memory_id: str, subject_user_id: str) -> Memory | None:
        return await self.session.scalar(
            select(Memory).where(
                Memory.id == memory_id,
                Memory.subject_user_id == subject_user_id,
                Memory.status != MemoryStatus.DELETED.value,
            )
        )

    async def add_revision(
        self,
        memory: Memory,
        new_content: str,
        reason: str,
        source_message_id: str | None = None,
    ) -> None:
        self.session.add(
            MemoryRevision(
                memory_id=memory.id,
                previous_content=memory.content,
                new_content=new_content,
                reason=reason,
                source_message_id=source_message_id,
            )
        )

    async def forget_user(self, subject_user_id: str) -> tuple[int, int]:
        memory_result = await self.session.execute(
            delete(Memory).where(Memory.subject_user_id == subject_user_id)
        )
        relationship_result = await self.session.execute(
            delete(Relationship).where(
                (Relationship.user_a_id == subject_user_id)
                | (Relationship.user_b_id == subject_user_id)
            )
        )
        return memory_result.rowcount or 0, relationship_result.rowcount or 0
