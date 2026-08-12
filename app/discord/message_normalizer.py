from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import discord


@dataclass(slots=True)
class NormalizedMessage:
    discord_message_id: str
    guild_id: str | None
    channel_id: str
    author_discord_id: str
    author_name: str
    reply_to_message_id: str | None
    reply_to_bot: bool
    content: str
    created_at: datetime
    is_dm: bool
    mentioned_user_ids: set[str]
    bot_mentioned: bool
    wake_word_used: bool


class MessageNormalizer:
    def __init__(self, wake_word: str):
        self.wake_word = wake_word

    def normalize(
        self, message: discord.Message, bot_user: discord.ClientUser
    ) -> NormalizedMessage:
        content = message.content
        for mentioned in message.mentions:
            label = f"@{mentioned.display_name}"
            content = content.replace(f"<@{mentioned.id}>", label)
            content = content.replace(f"<@!{mentioned.id}>", label)

        resolved = message.reference.resolved if message.reference else None
        reply_to_bot = isinstance(resolved, discord.Message) and resolved.author.id == bot_user.id
        return NormalizedMessage(
            discord_message_id=str(message.id),
            guild_id=str(message.guild.id) if message.guild else None,
            channel_id=str(message.channel.id),
            author_discord_id=str(message.author.id),
            author_name=message.author.display_name,
            reply_to_message_id=(str(message.reference.message_id) if message.reference else None),
            reply_to_bot=reply_to_bot,
            content=content.strip(),
            created_at=message.created_at,
            is_dm=message.guild is None,
            mentioned_user_ids={str(user.id) for user in message.mentions},
            bot_mentioned=bot_user.id in {user.id for user in message.mentions},
            wake_word_used=content.lstrip().startswith(self.wake_word),
        )
