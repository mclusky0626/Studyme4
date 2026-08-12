from __future__ import annotations

import logging

import discord
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.discord.commands import register_commands
from app.discord.events import DiscordEventHandler
from app.llm.base import LLMProvider

log = logging.getLogger(__name__)


class StudymeBot(commands.Bot):
    def __init__(
        self,
        *,
        settings: Settings,
        sessions: async_sessionmaker[AsyncSession],
        provider: LLMProvider,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
            application_id=settings.discord_application_id,
        )
        self.settings = settings
        self.handler = DiscordEventHandler(sessions=sessions, settings=settings, provider=provider)
        register_commands(self.tree, sessions, settings)

    async def setup_hook(self) -> None:
        synced = await self.tree.sync()
        log.info("synced %d application commands", len(synced))

    async def on_ready(self) -> None:
        log.info("Discord connected as %s (%s)", self.user, self.user.id if self.user else "?")

    async def on_message(self, message: discord.Message) -> None:
        if self.user is None:
            return
        await self.handler.handle(message, self.user)
