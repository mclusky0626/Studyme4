from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.common.time import utcnow


class ParticipationAction(StrEnum):
    REPLY = "reply"
    REACT = "react"
    IGNORE = "ignore"


@dataclass(slots=True)
class ParticipationDecision:
    action: ParticipationAction
    target_user_id: str | None
    confidence: float
    reason: str
    emoji: str | None = None


@dataclass(slots=True)
class ParticipationInput:
    author_id: str
    content: str
    is_dm: bool
    bot_mentioned: bool
    bot_replied_to: bool
    wake_word_used: bool
    mentioned_user_ids: set[str]
    bot_user_id: str
    last_partner_id: str | None = None
    engaged_until: object | None = None
    auto_participation_enabled: bool = False


_LAUGHTER = re.compile(r"^[ㅋㅎ]{2,}[!~.]*$")


class ParticipationService:
    def decide(self, item: ParticipationInput) -> ParticipationDecision:
        if item.is_dm:
            return ParticipationDecision(
                ParticipationAction.REPLY, item.author_id, 1.0, "direct message"
            )
        if item.bot_mentioned or item.bot_replied_to or item.wake_word_used:
            return ParticipationDecision(
                ParticipationAction.REPLY, item.author_id, 0.99, "explicitly addressed"
            )
        other_mentions = item.mentioned_user_ids - {item.bot_user_id}
        if other_mentions:
            return ParticipationDecision(
                ParticipationAction.IGNORE, None, 0.97, "another user was addressed"
            )
        if _LAUGHTER.fullmatch(item.content.strip()):
            return ParticipationDecision(
                ParticipationAction.REACT, item.author_id, 0.8, "reaction is more natural", "😂"
            )
        if (
            item.last_partner_id == item.author_id
            and item.engaged_until is not None
            and item.engaged_until > utcnow()
        ):
            return ParticipationDecision(
                ParticipationAction.REPLY, item.author_id, 0.78, "ongoing bot conversation"
            )
        if item.auto_participation_enabled:
            return ParticipationDecision(
                ParticipationAction.IGNORE,
                None,
                0.6,
                "spontaneous participation requires a separate high-confidence judge",
            )
        return ParticipationDecision(
            ParticipationAction.IGNORE, None, 0.95, "uncertain, so remain silent"
        )
