from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utcnow
from app.db.models import Memory, MemoryStatus, User
from app.memory.repository import MemoryRepository
from app.memory.schemas import MemoryCandidate, ValidationContext
from app.memory.validator import MemoryRejected, MemoryValidator


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())[:200]


class MemoryService:
    def __init__(self, session: AsyncSession, validator: MemoryValidator | None = None):
        self.session = session
        self.repository = MemoryRepository(session)
        self.validator = validator or MemoryValidator()

    async def store_candidate(
        self,
        *,
        subject: User,
        candidate: MemoryCandidate,
        context: ValidationContext,
        embedding: list[float] | None = None,
    ) -> Memory | None:
        if not subject.memory_enabled:
            return None
        validated = self.validator.validate(candidate, context)
        normalized = normalize_key(candidate.normalized_key)
        current = await self.repository.active_by_key(subject.id, normalized)

        if current and current.content.strip().casefold() == candidate.content.strip().casefold():
            current.updated_at = utcnow()
            current.confidence = max(current.confidence, candidate.confidence)
            current.importance = max(current.importance, candidate.importance)
            return current

        status = MemoryStatus.ACTIVE
        if current:
            confidence_gap = candidate.confidence - current.confidence
            if candidate.is_explicit and (confidence_gap >= -0.1):
                await self.repository.add_revision(
                    current,
                    candidate.content,
                    "newer explicit statement superseded this memory",
                    context.source_message_id,
                )
                current.status = MemoryStatus.SUPERSEDED.value
                current.valid_until = utcnow()
            else:
                current.status = MemoryStatus.DISPUTED.value
                status = MemoryStatus.DISPUTED

        memory = Memory(
            subject_user_id=subject.id,
            memory_type=candidate.memory_type.value,
            content=candidate.content.strip(),
            normalized_key=normalized,
            confidence=candidate.confidence,
            importance=candidate.importance,
            status=status.value,
            visibility=validated.visibility.value,
            is_explicit=candidate.is_explicit,
            guild_id=context.guild_id,
            channel_id=context.channel_id,
            source_message_id=context.source_message_id,
            valid_until=candidate.valid_until,
            embedding=embedding,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def correct_owned(
        self,
        memory_id: str,
        subject_user_id: str,
        new_content: str,
        reason: str = "user correction",
    ) -> Memory | None:
        memory = await self.repository.get_owned(memory_id, subject_user_id)
        if memory is None:
            return None
        await self.repository.add_revision(memory, new_content, reason)
        memory.content = new_content.strip()
        memory.confidence = 1.0
        memory.status = MemoryStatus.ACTIVE.value
        memory.updated_at = utcnow()
        return memory

    async def delete_owned(self, memory_id: str, subject_user_id: str) -> bool:
        memory = await self.repository.get_owned(memory_id, subject_user_id)
        if memory is None:
            return False
        memory.status = MemoryStatus.DELETED.value
        memory.embedding = None
        memory.updated_at = utcnow()
        return True


__all__ = ["MemoryRejected", "MemoryService", "normalize_key"]
