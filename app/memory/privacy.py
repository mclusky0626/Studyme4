from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, or_

from app.db.models import Memory, Visibility


@dataclass(frozen=True, slots=True)
class MemoryScope:
    guild_id: str | None
    channel_id: str
    is_dm: bool

    def __post_init__(self) -> None:
        if self.is_dm and self.guild_id is not None:
            raise ValueError("DM scope cannot contain a guild_id")
        if not self.is_dm and self.guild_id is None:
            raise ValueError("Guild scope requires guild_id")


def visible_memory_clause(scope: MemoryScope):
    """Return the mandatory SQL boundary for conversational memory retrieval."""
    if scope.is_dm:
        return and_(
            Memory.visibility == Visibility.DM_PRIVATE.value,
            Memory.guild_id.is_(None),
            Memory.channel_id == scope.channel_id,
        )
    return or_(
        and_(
            Memory.visibility == Visibility.GUILD.value,
            Memory.guild_id == scope.guild_id,
        ),
        and_(
            Memory.visibility == Visibility.CHANNEL.value,
            Memory.guild_id == scope.guild_id,
            Memory.channel_id == scope.channel_id,
        ),
    )
