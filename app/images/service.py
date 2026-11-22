from __future__ import annotations

import logging
import mimetypes
import re

import discord
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import ImageMemory
from app.images.repository import ImageRepository
from app.images.storage import LocalImageStorage
from app.llm.base import LLMProvider

log = logging.getLogger(__name__)

_DESCRIPTION_MARKUP = re.compile(r"\[\[|\]\]|\*\*|__|`{1,3}")


def image_analysis_prompt(message_text: str) -> str:
    return (
        "나중에 검색하고 사용자에게 다시 자세히 설명할 수 있도록 "
        "이 이미지를 한국어 8~12문장으로 분석해. 보이는 대상의 외형과 "
        "행동, 전경·중경·배경, 구도와 시점, 주요 색상, 조명, 화풍 또는 "
        "사진 스타일, 분위기, 읽을 수 있는 글자를 빠뜨리지 마. "
        "작품명·인물명은 근거가 충분할 때만 쓰고 불확실하면 후보라고 밝혀. "
        "마지막 문장에는 동의어를 포함한 검색 키워드를 쉼표로 적어. "
        "Markdown, 대괄호 제목, 별표 강조는 사용하지 마. "
        f"함께 적힌 메시지: {message_text or '(없음)'}"
    )


def clean_image_description(value: str) -> str:
    lines = [line.strip().lstrip("#-• ").strip() for line in value.splitlines()]
    return "\n".join(_DESCRIPTION_MARKUP.sub("", line).strip() for line in lines if line).strip()


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
                            prompt=image_analysis_prompt(message_text),
                        )
                        if analyzed:
                            description = clean_image_description(analyzed)[:4000]
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
