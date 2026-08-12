from __future__ import annotations

import logging
import mimetypes

import discord
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import ImageMemory
from app.images.repository import ImageRepository
from app.images.storage import LocalImageStorage
from app.llm.base import LLMProvider

log = logging.getLogger(__name__)


class ImageArchiveService:
    def __init__(
        self,
        *,
        sessions: async_sessionmaker[AsyncSession],
        provider: LLMProvider,
        storage: LocalImageStorage,
        max_bytes: int,
        analyze: bool,
    ):
        self.sessions = sessions
        self.provider = provider
        self.storage = storage
        self.max_bytes = max_bytes
        self.analyze = analyze

    async def archive_attachments(
        self,
        attachments: list[discord.Attachment],
        *,
        owner_user_id: str,
        source_message_id: str,
        discord_message_id: str,
        guild_id: str | None,
        channel_id: str,
        message_text: str,
    ) -> list[ImageMemory]:
        archived: list[ImageMemory] = []
        for attachment in attachments:
            content_type = attachment.content_type or mimetypes.guess_type(attachment.filename)[0]
            if not content_type or not content_type.casefold().startswith("image/"):
                continue
            if attachment.size > self.max_bytes:
                log.warning("image attachment %s is too large; skipped", attachment.id)
                continue
            try:
                data = await attachment.read(use_cached=True)
                if len(data) > self.max_bytes:
                    log.warning("image attachment %s exceeded limit; skipped", attachment.id)
                    continue
                stored = await self.storage.save(
                    data=data,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    message_id=discord_message_id,
                    attachment_id=str(attachment.id),
                    filename=attachment.filename,
                )
                description = f"파일명: {attachment.filename}"
                if self.analyze:
                    try:
                        analyzed = await self.provider.describe_image(
                            data=data,
                            content_type=content_type,
                            prompt=(
                                "검색용으로 이 이미지를 한국어 3~6문장으로 설명해. "
                                "마지막에는 핵심 사물과 장면의 비슷한 표현을 검색 키워드로 적어. "
                                f"함께 적힌 메시지: {message_text or '(없음)'}"
                            ),
                        )
                        if analyzed:
                            description = analyzed[:4000]
                    except Exception:
                        log.exception("image analysis failed for attachment %s", attachment.id)
                async with self.sessions() as session, session.begin():
                    record = await ImageRepository(session).add(
                        owner_user_id=owner_user_id,
                        source_message_id=source_message_id,
                        discord_attachment_id=str(attachment.id),
                        guild_id=guild_id,
                        channel_id=channel_id,
                        original_filename=attachment.filename,
                        stored_path=str(stored.path),
                        content_type=content_type,
                        byte_size=stored.byte_size,
                        sha256=stored.sha256,
                        description=description,
                    )
                    archived.append(record)
            except Exception:
                log.exception("image archive failed for attachment %s", attachment.id)
        return archived
