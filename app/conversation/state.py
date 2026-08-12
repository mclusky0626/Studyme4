from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utcnow
from app.db.models import ChannelState


class ConversationStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, channel_id: str) -> ChannelState | None:
        return await self.session.scalar(
            select(ChannelState).where(ChannelState.channel_id == channel_id)
        )

    async def mark_replied(
        self,
        *,
        channel_id: str,
        guild_id: str | None,
        partner_discord_id: str,
        bot_message_id: str,
        engage_window_seconds: int,
    ) -> ChannelState:
        state = await self.get(channel_id)
        if state is None:
            state = ChannelState(channel_id=channel_id, guild_id=guild_id)
            self.session.add(state)
        state.last_partner_discord_id = partner_discord_id
        state.last_bot_message_id = bot_message_id
        state.engaged_until = utcnow() + timedelta(seconds=engage_window_seconds)
        return state
