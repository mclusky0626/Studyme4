from __future__ import annotations

from datetime import UTC, datetime

from app.images.intent import is_image_recall_request
from app.images.repository import ImageRepository
from app.images.service import ImageArchiveService
from app.images.storage import LocalImageStorage
from app.llm.fake_provider import FakeProvider
from app.memory.privacy import MemoryScope
from app.memory.repository import MessageRepository, UserRepository


class FakeAttachment:
    id = 987
    filename = "바다 사진.png"
    content_type = "image/png"

    def __init__(self, data: bytes):
        self.data = data
        self.size = len(data)

    async def read(self, *, use_cached: bool = True) -> bytes:
        assert use_cached
        return self.data


async def _source(sessions, *, guild_id: str | None = "guild-1"):
    async with sessions() as session, session.begin():
        user = await UserRepository(session).upsert("100", "건우", guild_id)
        message = await MessageRepository(session).add(
            discord_message_id="message-1",
            guild_id=guild_id,
            channel_id="channel-1",
            author_user_id=user.id,
            reply_to_message_id=None,
            content="여행 사진",
            created_at=datetime.now(UTC),
            is_dm=guild_id is None,
        )
        return user.id, message.id


def test_image_recall_intent() -> None:
    assert is_image_recall_request("그때 바닷가 사진 보여줘")
    assert is_image_recall_request("고양이 짤 다시 찾아줘")
    assert is_image_recall_request("그 사진 다시 보내줘")
    assert not is_image_recall_request("사진 분석해줘")


async def test_archive_analyze_search_and_delete(sessions, tmp_path) -> None:
    user_id, message_id = await _source(sessions)
    storage = LocalImageStorage(tmp_path / "images")
    service = ImageArchiveService(
        sessions=sessions,
        provider=FakeProvider(image_descriptions=["푸른 바닷가에서 찍은 노을 풍경"]),
        storage=storage,
        max_bytes=1024,
        analyze=True,
    )

    archived = await service.archive_attachments(
        [FakeAttachment(b"fake-png")],
        owner_user_id=user_id,
        source_message_id=message_id,
        discord_message_id="message-1",
        guild_id="guild-1",
        channel_id="channel-1",
        message_text="여행 사진",
    )
    assert len(archived) == 1
    assert archived[0].description == "푸른 바닷가에서 찍은 노을 풍경"
    assert archived[0].stored_path.startswith(str(tmp_path))

    async with sessions() as session, session.begin():
        repository = ImageRepository(session)
        found = await repository.search(
            scope=MemoryScope(guild_id="guild-1", channel_id="channel-2", is_dm=False),
            query="그때 바닷가 사진 보여줘",
            owner_user_id=user_id,
        )
        hidden = await repository.search(
            scope=MemoryScope(guild_id="guild-2", channel_id="channel-2", is_dm=False),
            query="바닷가",
            owner_user_id=user_id,
        )
        latest = await repository.search(
            scope=MemoryScope(guild_id="guild-1", channel_id="channel-2", is_dm=False),
            query="저번에 내가 올린 사진 다시 보여줘",
            owner_user_id=user_id,
        )
    assert [item.id for item in found] == [archived[0].id]
    assert hidden == []
    assert [item.id for item in latest] == [archived[0].id]

    assert await storage.delete(archived[0].stored_path)


async def test_non_image_and_oversized_attachments_are_skipped(sessions, tmp_path) -> None:
    user_id, message_id = await _source(sessions)
    attachment = FakeAttachment(b"too-large")
    attachment.content_type = "text/plain"
    service = ImageArchiveService(
        sessions=sessions,
        provider=FakeProvider(),
        storage=LocalImageStorage(tmp_path / "images"),
        max_bytes=2,
        analyze=True,
    )
    archived = await service.archive_attachments(
        [attachment],
        owner_user_id=user_id,
        source_message_id=message_id,
        discord_message_id="message-1",
        guild_id="guild-1",
        channel_id="channel-1",
        message_text="",
    )
    assert archived == []
