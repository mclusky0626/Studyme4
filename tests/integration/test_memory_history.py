from datetime import UTC, datetime

from sqlalchemy import func, select

from app.db.models import MemoryRevision, MemoryStatus, MemoryType, Visibility
from app.memory.repository import MemoryRepository, MessageRepository, UserRepository
from app.memory.schemas import MemoryCandidate, ValidationContext
from app.memory.service import MemoryService


async def test_duplicate_refreshes_and_correction_preserves_history(sessions):
    async with sessions() as session, session.begin():
        users = UserRepository(session)
        user = await users.upsert("123", "민수", "guild-a")
        messages = MessageRepository(session)
        first_source = await messages.add(
            discord_message_id="one",
            guild_id="guild-a",
            channel_id="channel-a",
            author_user_id=user.id,
            reply_to_message_id=None,
            content="커피 좋아함",
            created_at=datetime.now(UTC),
            is_dm=False,
        )
        second_source = await messages.add(
            discord_message_id="two",
            guild_id="guild-a",
            channel_id="channel-a",
            author_user_id=user.id,
            reply_to_message_id=None,
            content="요즘 커피 끊었음",
            created_at=datetime.now(UTC),
            is_dm=False,
        )
        service = MemoryService(session)

        def candidate(content):
            return MemoryCandidate(
                memory_type=MemoryType.STATE,
                subject_discord_user_id="123",
                content=content,
                normalized_key="drink:coffee:current-state",
                confidence=0.95,
                importance=0.7,
                visibility=Visibility.GUILD,
            )

        first = await service.store_candidate(
            subject=user,
            candidate=candidate("민수는 커피를 즐겨 마신다."),
            context=ValidationContext(
                author_discord_user_id="123",
                guild_id="guild-a",
                channel_id="channel-a",
                is_dm=False,
                source_message_id=first_source.id,
            ),
        )
        duplicate = await service.store_candidate(
            subject=user,
            candidate=candidate("민수는 커피를 즐겨 마신다."),
            context=ValidationContext(
                author_discord_user_id="123",
                guild_id="guild-a",
                channel_id="channel-a",
                is_dm=False,
                source_message_id=first_source.id,
            ),
        )
        replacement = await service.store_candidate(
            subject=user,
            candidate=candidate("민수는 건강 때문에 커피를 끊은 상태다."),
            context=ValidationContext(
                author_discord_user_id="123",
                guild_id="guild-a",
                channel_id="channel-a",
                is_dm=False,
                source_message_id=second_source.id,
            ),
        )
        await session.flush()
        memories = await MemoryRepository(session).list_owned(user.id)
        revision_count = await session.scalar(
            select(func.count(MemoryRevision.id)).where(MemoryRevision.memory_id == first.id)
        )

        assert duplicate.id == first.id
        assert first.status == MemoryStatus.SUPERSEDED.value
        assert revision_count == 1
        assert replacement.status == MemoryStatus.ACTIVE.value
        assert len(memories) == 2
