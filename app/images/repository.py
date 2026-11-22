from __future__ import annotations

import re

from sqlalchemy import and_, delete, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utcnow
from app.db.models import ImageMemory, Visibility
from app.memory.privacy import MemoryScope

_SEARCH_FILLERS = (
    "사진",
    "이미지",
    "그림",
    "짤",
    "보여줘",
    "보여 줘",
    "찾아줘",
    "찾아 줘",
    "꺼내줘",
    "꺼내 줘",
    "불러줘",
    "불러 줘",
    "재전송",
    "보내줘",
    "보내 줘",
    "올려줘",
    "올려 줘",
    "다시",
    "그때",
    "저번",
    "저번에",
    "지난번",
    "예전에",
    "올린",
    "올렸던",
    "보낸",
    "보냈던",
    "저장한",
    "저장했던",
    "내가",
    "우리",
)


def visible_image_clause(scope: MemoryScope):
    if scope.is_dm:
        return and_(
            ImageMemory.visibility == Visibility.DM_PRIVATE.value,
            ImageMemory.guild_id.is_(None),
            ImageMemory.channel_id == scope.channel_id,
        )
    return or_(
        and_(
            ImageMemory.visibility == Visibility.GUILD.value,
            ImageMemory.guild_id == scope.guild_id,
        ),
        and_(
            ImageMemory.visibility == Visibility.CHANNEL.value,
            ImageMemory.guild_id == scope.guild_id,
            ImageMemory.channel_id == scope.channel_id,
        ),
    )


def search_terms(query: str) -> list[str]:
    cleaned = query.casefold()
    for filler in _SEARCH_FILLERS:
        cleaned = cleaned.replace(filler, " ")
    return [token for token in re.findall(r"[0-9a-z가-힣]+", cleaned) if len(token) >= 2]


class ImageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        *,
        owner_user_id: str,
        source_message_id: str,
        discord_attachment_id: str,
        guild_id: str | None,
        channel_id: str,
        original_filename: str,
        stored_path: str,
        content_type: str,
        byte_size: int,
        sha256: str,
        description: str,
    ) -> ImageMemory:
        existing = await self.session.scalar(
            select(ImageMemory).where(ImageMemory.discord_attachment_id == discord_attachment_id)
        )
        if existing is not None:
            return existing
        image = ImageMemory(
            owner_user_id=owner_user_id,
            source_message_id=source_message_id,
            discord_attachment_id=discord_attachment_id,
            guild_id=guild_id,
            channel_id=channel_id,
            visibility=(Visibility.GUILD.value if guild_id else Visibility.DM_PRIVATE.value),
            original_filename=original_filename,
            stored_path=stored_path,
            content_type=content_type,
            byte_size=byte_size,
            sha256=sha256,
            description=description,
        )
        self.session.add(image)
        await self.session.flush()
        return image

    async def list_owned(self, owner_user_id: str, limit: int = 50) -> list[ImageMemory]:
        return list(
            (
                await self.session.scalars(
                    select(ImageMemory)
                    .where(
                        ImageMemory.owner_user_id == owner_user_id,
                        ImageMemory.deleted_at.is_(None),
                    )
                    .order_by(desc(ImageMemory.created_at))
                    .limit(limit)
                )
            ).all()
        )

    async def get_owned_by_prefix(self, image_id: str, owner_user_id: str) -> ImageMemory | None:
        candidates = await self.list_owned(owner_user_id, limit=500)
        matches = [
            item for item in candidates if item.id == image_id or item.id.startswith(image_id)
        ]
        return matches[0] if len(matches) == 1 else None

    async def search(
        self,
        *,
        scope: MemoryScope,
        query: str,
        limit: int = 3,
        owner_user_id: str | None = None,
    ) -> list[ImageMemory]:
        stmt = (
            select(ImageMemory)
            .where(ImageMemory.deleted_at.is_(None), visible_image_clause(scope))
            .order_by(desc(ImageMemory.created_at))
            .limit(300)
        )
        if owner_user_id:
            stmt = stmt.where(ImageMemory.owner_user_id == owner_user_id)
        candidates = list((await self.session.scalars(stmt)).all())
        terms = search_terms(query)
        if terms:
            ranked: list[tuple[int, int, ImageMemory]] = []
            for position, image in enumerate(candidates):
                haystack = f"{image.description} {image.original_filename}".casefold()
                score = sum(
                    3 if haystack.startswith(term) else 1 for term in terms if term in haystack
                )
                if score:
                    ranked.append((score, -position, image))
            ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
            found = [row[2] for row in ranked[:limit]]
        else:
            found = candidates[:limit]
        now = utcnow()
        for image in found:
            image.recall_count += 1
            image.last_recalled_at = now
        return found

    async def soft_delete_owned(self, image: ImageMemory, owner_user_id: str) -> bool:
        if image.owner_user_id != owner_user_id or image.deleted_at is not None:
            return False
        image.deleted_at = utcnow()
        return True

    async def hard_delete_all_owned(self, owner_user_id: str) -> tuple[int, list[str]]:
        images = await self.list_owned(owner_user_id, limit=10_000)
        paths = [image.stored_path for image in images]
        result = await self.session.execute(
            delete(ImageMemory).where(ImageMemory.owner_user_id == owner_user_id)
        )
        return result.rowcount or 0, paths
