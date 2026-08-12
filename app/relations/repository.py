from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Relationship, RelationshipEvent, User
from app.relations.models import RelationshipCandidate, RelationshipView


class RelationshipRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_event(
        self,
        *,
        guild_id: str,
        user_a: User,
        user_b: User,
        source_message_id: str,
        candidate: RelationshipCandidate,
    ) -> Relationship:
        relationship = await self.session.scalar(
            select(Relationship).where(
                Relationship.guild_id == guild_id,
                Relationship.user_a_id == user_a.id,
                Relationship.user_b_id == user_b.id,
                Relationship.relation_type == candidate.relation_type,
            )
        )
        if relationship is None:
            relationship = Relationship(
                guild_id=guild_id,
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                relation_type=candidate.relation_type,
                confidence=candidate.confidence,
            )
            self.session.add(relationship)
            await self.session.flush()
        else:
            # One message changes the current summary slowly; the event remains exact.
            relationship.confidence = max(relationship.confidence, candidate.confidence)
            relationship.closeness = max(
                0.0,
                min(1.0, relationship.closeness + candidate.sentiment * 0.05),
            )
            relationship.tension = max(
                0.0,
                min(1.0, relationship.tension - candidate.sentiment * 0.05),
            )

        self.session.add(
            RelationshipEvent(
                relationship_id=relationship.id,
                event_type=candidate.event_type,
                description=candidate.description,
                sentiment=candidate.sentiment,
                confidence=candidate.confidence,
                is_explicit=candidate.is_explicit,
                source_message_id=source_message_id,
            )
        )
        return relationship

    async def for_user(self, guild_id: str, user_id: str) -> list[RelationshipView]:
        user_a = User.__table__.alias("user_a")
        user_b = User.__table__.alias("user_b")
        stmt = (
            select(
                Relationship.id,
                user_a.c.current_display_name,
                user_b.c.current_display_name,
                Relationship.relation_type,
                Relationship.confidence,
            )
            .join(user_a, Relationship.user_a_id == user_a.c.id)
            .join(user_b, Relationship.user_b_id == user_b.c.id)
            .where(
                Relationship.guild_id == guild_id,
                or_(Relationship.user_a_id == user_id, Relationship.user_b_id == user_id),
            )
        )
        return [
            RelationshipView(
                id=row.id,
                user_a_name=row.current_display_name,
                user_b_name=row.current_display_name_1,
                relation_type=row.relation_type,
                confidence=row.confidence,
            )
            for row in (await self.session.execute(stmt)).all()
        ]
