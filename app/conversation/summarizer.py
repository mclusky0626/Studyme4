from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationSummary


class ConversationSummarizer:
    """Persists externally produced summaries; generation stays provider-agnostic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self,
        *,
        guild_id: str | None,
        channel_id: str,
        topic: str,
        summary: str,
        participants: list[str],
        started_at: datetime,
        ended_at: datetime,
        embedding: list[float] | None = None,
    ) -> ConversationSummary:
        value = ConversationSummary(
            guild_id=guild_id,
            channel_id=channel_id,
            topic=topic,
            summary=summary,
            participants=participants,
            started_at=started_at,
            ended_at=ended_at,
            embedding=embedding,
        )
        self.session.add(value)
        await self.session.flush()
        return value
