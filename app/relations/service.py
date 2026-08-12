from __future__ import annotations

from app.db.models import User
from app.relations.models import RelationshipCandidate
from app.relations.repository import RelationshipRepository


class RelationshipService:
    def __init__(self, repository: RelationshipRepository):
        self.repository = repository

    async def store(
        self,
        *,
        guild_id: str | None,
        user_a: User,
        user_b: User,
        source_message_id: str,
        candidate: RelationshipCandidate,
    ):
        if guild_id is None:
            return None
        if not candidate.is_explicit and candidate.confidence >= 0.8:
            return None
        if user_a.id == user_b.id:
            return None
        return await self.repository.add_event(
            guild_id=guild_id,
            user_a=user_a,
            user_b=user_b,
            source_message_id=source_message_id,
            candidate=candidate,
        )
