from __future__ import annotations

import discord
from discord import app_commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models import ServerPolicy, User
from app.memory.repository import MemoryRepository, UserRepository
from app.memory.service import MemoryService


def _short(value: str, limit: int = 80) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def register_commands(
    tree: app_commands.CommandTree,
    sessions: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    async def current_user(session: AsyncSession, interaction: discord.Interaction) -> User:
        return await UserRepository(session).upsert(
            str(interaction.user.id),
            interaction.user.display_name,
            str(interaction.guild_id) if interaction.guild_id else None,
        )

    @tree.command(name="기억보기", description="나에 대해 저장된 기억을 봅니다")
    async def memory_list(interaction: discord.Interaction) -> None:
        async with sessions() as session, session.begin():
            user = await current_user(session, interaction)
            memories = await MemoryRepository(session).list_owned(user.id)
            if not memories:
                text = "저장된 기억이 없어."
            else:
                text = "\n".join(
                    f"`{memory.id[:8]}` [{memory.status}] {_short(memory.content)}"
                    for memory in memories[:20]
                )
        await interaction.response.send_message(text[:1900], ephemeral=True)

    @tree.command(name="기억검색", description="내 기억에서 단어를 검색합니다")
    @app_commands.describe(query="찾을 말")
    async def memory_search(interaction: discord.Interaction, query: str) -> None:
        async with sessions() as session, session.begin():
            user = await current_user(session, interaction)
            memories = await MemoryRepository(session).list_owned(user.id, limit=100)
            found = [m for m in memories if query.casefold() in m.content.casefold()]
            text = (
                "\n".join(f"`{memory.id[:8]}` {_short(memory.content)}" for memory in found[:20])
                or "검색 결과가 없어."
            )
        await interaction.response.send_message(text[:1900], ephemeral=True)

    @tree.command(name="기억수정", description="내 기억 내용을 정정하고 이력을 남깁니다")
    async def memory_correct(
        interaction: discord.Interaction, memory_id: str, new_content: str
    ) -> None:
        async with sessions() as session, session.begin():
            user = await current_user(session, interaction)
            memories = await MemoryRepository(session).list_owned(user.id, limit=100)
            match = next(
                (m for m in memories if m.id == memory_id or m.id.startswith(memory_id)), None
            )
            if match is None:
                text = "그 ID의 내 기억을 찾지 못했어."
            else:
                updated = await MemoryService(session).correct_owned(match.id, user.id, new_content)
                text = "수정했고 이전 내용은 이력으로 남겼어." if updated else "수정하지 못했어."
        await interaction.response.send_message(text, ephemeral=True)

    @tree.command(name="기억삭제", description="내 기억 하나를 비활성 삭제합니다")
    async def memory_delete(interaction: discord.Interaction, memory_id: str) -> None:
        async with sessions() as session, session.begin():
            user = await current_user(session, interaction)
            memories = await MemoryRepository(session).list_owned(user.id, limit=100)
            match = next(
                (m for m in memories if m.id == memory_id or m.id.startswith(memory_id)), None
            )
            deleted = bool(match) and await MemoryService(session).delete_owned(match.id, user.id)
        await interaction.response.send_message(
            "삭제 상태로 바꾸고 임베딩도 제거했어." if deleted else "그 ID의 내 기억을 못 찾았어.",
            ephemeral=True,
        )

    @tree.command(name="나를잊어", description="내 기억·벡터·관계 데이터를 삭제합니다")
    async def forget_me(interaction: discord.Interaction) -> None:
        async with sessions() as session, session.begin():
            user = await current_user(session, interaction)
            memory_count, relation_count = await MemoryRepository(session).forget_user(user.id)
            user.memory_enabled = False
        await interaction.response.send_message(
            f"기억 {memory_count}개와 관계 {relation_count}개를 삭제했어. "
            "Discord 원문 메시지는 Discord와 서버 운영 정책에 따라 남을 수 있어.",
            ephemeral=True,
        )

    @tree.command(name="기억끄기", description="앞으로 나에 대한 기억 저장을 끕니다")
    async def memory_off(interaction: discord.Interaction) -> None:
        async with sessions() as session, session.begin():
            user = await current_user(session, interaction)
            user.memory_enabled = False
        await interaction.response.send_message("앞으로 네 기억을 저장하지 않을게.", ephemeral=True)

    @tree.command(name="기억켜기", description="나에 대한 기억 저장을 다시 켭니다")
    async def memory_on(interaction: discord.Interaction) -> None:
        async with sessions() as session, session.begin():
            user = await current_user(session, interaction)
            user.memory_enabled = True
        await interaction.response.send_message("네 기억 저장을 다시 켰어.", ephemeral=True)

    @tree.command(name="서버기억설정", description="이 서버의 기억 기능을 설정합니다")
    async def server_memory_policy(interaction: discord.Interaction, enabled: bool) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("서버에서만 쓸 수 있어.", ephemeral=True)
            return
        permissions = getattr(interaction.user, "guild_permissions", None)
        if not permissions or not permissions.manage_guild:
            await interaction.response.send_message("서버 관리 권한이 필요해.", ephemeral=True)
            return
        guild_id = str(interaction.guild_id)
        async with sessions() as session, session.begin():
            policy = await session.scalar(
                select(ServerPolicy).where(ServerPolicy.guild_id == guild_id)
            )
            if policy is None:
                policy = ServerPolicy(guild_id=guild_id)
                session.add(policy)
            policy.memory_enabled = enabled
        await interaction.response.send_message(
            f"이 서버의 기억 기능을 {'켰어' if enabled else '껐어'}.", ephemeral=True
        )

    @tree.command(name="서버참여설정", description="접두사 없는 대화 참여 판단을 설정합니다")
    async def server_participation_policy(interaction: discord.Interaction, enabled: bool) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("서버에서만 쓸 수 있어.", ephemeral=True)
            return
        permissions = getattr(interaction.user, "guild_permissions", None)
        if not permissions or not permissions.manage_guild:
            await interaction.response.send_message("서버 관리 권한이 필요해.", ephemeral=True)
            return
        guild_id = str(interaction.guild_id)
        async with sessions() as session, session.begin():
            policy = await session.scalar(
                select(ServerPolicy).where(ServerPolicy.guild_id == guild_id)
            )
            if policy is None:
                policy = ServerPolicy(guild_id=guild_id)
                session.add(policy)
            policy.auto_participation_enabled = enabled
        await interaction.response.send_message(
            f"접두사 없는 대화 참여 판단을 {'켰어' if enabled else '껐어'}.",
            ephemeral=True,
        )

    @tree.command(name="봇정보", description="봇의 기억·개인정보 원칙을 봅니다")
    async def bot_info(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"{settings.bot_name} v0.1.0 · AI 챗봇\n"
            "DM 기억은 서버에서 사용하지 않고, 기억에는 출처·공개 범위·상태를 저장해. "
            "`/기억보기`, `/기억수정`, `/기억삭제`, `/나를잊어`로 직접 관리할 수 있어.",
            ephemeral=True,
        )
