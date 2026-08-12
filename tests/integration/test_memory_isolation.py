from datetime import UTC, datetime

from app.db.models import MemoryType, Visibility
from app.memory.privacy import MemoryScope
from app.memory.repository import MemoryRepository, MessageRepository, UserRepository
from app.memory.schemas import MemoryCandidate, ValidationContext
from app.memory.service import MemoryService


async def seed_memory(
    session,
    *,
    author_discord_id: str,
    guild_id: str | None,
    channel_id: str,
    discord_message_id: str,
    visibility: Visibility,
    content: str,
    key: str,
):
    users = UserRepository(session)
    user = await users.upsert(author_discord_id, "민수", guild_id)
    message = await MessageRepository(session).add(
        discord_message_id=discord_message_id,
        guild_id=guild_id,
        channel_id=channel_id,
        author_user_id=user.id,
        reply_to_message_id=None,
        content=content,
        created_at=datetime.now(UTC),
        is_dm=guild_id is None,
    )
    memory = await MemoryService(session).store_candidate(
        subject=user,
        candidate=MemoryCandidate(
            memory_type=MemoryType.PREFERENCE,
            subject_discord_user_id=author_discord_id,
            content=content,
            normalized_key=key,
            confidence=0.95,
            importance=0.7,
            visibility=visibility,
        ),
        context=ValidationContext(
            author_discord_user_id=author_discord_id,
            guild_id=guild_id,
            channel_id=channel_id,
            is_dm=guild_id is None,
            source_message_id=message.id,
        ),
    )
    return user, memory


async def test_guild_memories_do_not_cross_servers(sessions):
    async with sessions() as session, session.begin():
        user, _ = await seed_memory(
            session,
            author_discord_id="123",
            guild_id="guild-a",
            channel_id="channel-a",
            discord_message_id="message-a",
            visibility=Visibility.GUILD,
            content="민수는 해산물을 싫어한다.",
            key="food:seafood",
        )
        repository = MemoryRepository(session)
        visible_a = await repository.conversational_candidates(
            scope=MemoryScope(guild_id="guild-a", channel_id="channel-a", is_dm=False),
            subject_user_ids=[user.id],
        )
        visible_b = await repository.conversational_candidates(
            scope=MemoryScope(guild_id="guild-b", channel_id="channel-b", is_dm=False),
            subject_user_ids=[user.id],
        )
    assert len(visible_a) == 1
    assert visible_b == []


async def test_dm_memory_never_appears_in_guild(sessions):
    async with sessions() as session, session.begin():
        user, memory = await seed_memory(
            session,
            author_discord_id="123",
            guild_id=None,
            channel_id="dm-123",
            discord_message_id="message-dm",
            visibility=Visibility.GUILD,
            content="민수는 비공개로 이직을 준비한다.",
            key="work:job-change",
        )
        repository = MemoryRepository(session)
        in_dm = await repository.conversational_candidates(
            scope=MemoryScope(guild_id=None, channel_id="dm-123", is_dm=True),
            subject_user_ids=[user.id],
        )
        in_guild = await repository.conversational_candidates(
            scope=MemoryScope(guild_id="guild-a", channel_id="channel-a", is_dm=False),
            subject_user_ids=[user.id],
        )
    assert memory.visibility == Visibility.DM_PRIVATE.value
    assert len(in_dm) == 1
    assert in_guild == []
