from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import discord

_BUBBLE_BOUNDARY = re.compile(r"\s*(?:\[\[BUBBLE\]\]|<BUBBLE>|\[BUBBLE\])\s*|\n+", re.IGNORECASE)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+")


@dataclass(slots=True)
class SentBubble:
    message: discord.Message
    text: str


def _hard_wrap(value: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    rest = value.strip()
    while len(rest) > max_chars:
        cut = rest.rfind(" ", 0, max_chars + 1)
        if cut < max_chars // 2:
            cut = max_chars
        chunks.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        chunks.append(rest)
    return chunks


def split_response_bubbles(text: str, *, max_bubbles: int = 4, max_chars: int = 700) -> list[str]:
    """Parse model bubble markers and keep every Discord message comfortably sized."""
    value = text.strip() or "ㅇㅇ"
    parts = [part.strip() for part in _BUBBLE_BOUNDARY.split(value) if part.strip()]

    # If a model ignored the explicit marker, split only an unusually long response.
    if len(parts) == 1 and len(parts[0]) > max_chars:
        sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(parts[0]) if part.strip()]
        if len(sentences) > 1:
            parts = sentences

    wrapped = [chunk for part in parts for chunk in _hard_wrap(part, max_chars)]
    if len(wrapped) <= max_bubbles:
        return wrapped

    # Prefer the configured number of bubbles, unless Discord's hard 2,000-char limit
    # makes additional bubbles necessary.
    head = wrapped[: max_bubbles - 1]
    tail = " ".join(wrapped[max_bubbles - 1 :])
    return head + _hard_wrap(tail, min(1900, max_chars * 2))


async def send_response(
    message: discord.Message,
    text: str,
    *,
    max_bubbles: int = 4,
    max_chars: int = 700,
) -> list[SentBubble]:
    bubbles = split_response_bubbles(text, max_bubbles=max_bubbles, max_chars=max_chars)
    sent: list[SentBubble] = []
    for index, bubble in enumerate(bubbles):
        try:
            async with message.channel.typing():
                await asyncio.sleep(min(0.25 + len(bubble) * 0.012, 1.4))
        except (discord.Forbidden, discord.HTTPException):
            pass
        if index == 0:
            sent_message = await message.reply(bubble, mention_author=False)
        else:
            sent_message = await message.channel.send(bubble)
        sent.append(SentBubble(message=sent_message, text=bubble))
    return sent
