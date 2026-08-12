from __future__ import annotations

import asyncio

import discord


async def send_response(message: discord.Message, text: str) -> discord.Message:
    chunks = [text[index : index + 1900] for index in range(0, len(text), 1900)] or ["ㅇㅇ"]
    sent: discord.Message | None = None
    for index, chunk in enumerate(chunks):
        try:
            async with message.channel.typing():
                await asyncio.sleep(min(0.25 + len(chunk) * 0.01, 1.2))
        except (discord.Forbidden, discord.HTTPException):
            pass
        if index == 0:
            sent = await message.reply(chunk, mention_author=False)
        else:
            sent = await message.channel.send(chunk)
    assert sent is not None
    return sent
