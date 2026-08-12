from __future__ import annotations

import logging

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.conversation.context_builder import ContextBuilder
from app.conversation.participation import (
    ParticipationAction,
    ParticipationDecision,
    ParticipationInput,
    ParticipationJudge,
    ParticipationService,
)
from app.conversation.response_generator import ResponseGenerator
from app.conversation.state import ConversationStateRepository
from app.db.models import ServerPolicy
from app.discord.message_normalizer import MessageNormalizer
from app.discord.response_sender import send_response
from app.images.intent import is_image_recall_request
from app.images.repository import ImageRepository
from app.images.service import ImageArchiveService
from app.images.storage import LocalImageStorage
from app.llm.base import LLMProvider
from app.llm.router import build_participation_provider
from app.memory.extractor import MemoryExtractor
from app.memory.privacy import MemoryScope
from app.memory.repository import MemoryRepository, MessageRepository, UserRepository
from app.memory.retrieval import MemoryRetriever
from app.memory.schemas import ValidationContext
from app.memory.service import MemoryService
from app.memory.validator import MemoryRejected
from app.persona.profile import PersonaProfile
from app.relations.extractor import RelationshipExtractor
from app.relations.repository import RelationshipRepository
from app.relations.service import RelationshipService

log = logging.getLogger(__name__)


class DiscordEventHandler:
    def __init__(
        self,
        *,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        provider: LLMProvider,
    ):
        self.sessions = sessions
        self.settings = settings
        self.provider = provider
        self.normalizer = MessageNormalizer(settings.wake_word)
        self.participation = ParticipationService()
        self.participation_judge = ParticipationJudge(
            build_participation_provider(settings, provider),
            reply_threshold=settings.participation_reply_threshold,
            react_threshold=settings.participation_react_threshold,
            spontaneous_cooldown_seconds=settings.spontaneous_cooldown_seconds,
        )
        self.response_generator = ResponseGenerator(provider)
        self.memory_extractor = MemoryExtractor(provider)
        self.relationship_extractor = RelationshipExtractor(provider)
        self.profile = PersonaProfile(
            name=settings.bot_name,
            version=settings.persona_version,
            speaking_style=settings.persona_text(),
        )
        self.image_storage = LocalImageStorage(settings.image_storage_dir)
        self.image_archive = ImageArchiveService(
            sessions=sessions,
            provider=provider,
            storage=self.image_storage,
            max_bytes=settings.image_max_bytes,
            analyze=settings.image_analysis_enabled,
        )

    async def handle(self, message: discord.Message, bot_user: discord.ClientUser) -> None:
        if message.author.bot:
            return
        normalized = self.normalizer.normalize(message, bot_user)
        scope = MemoryScope(
            guild_id=normalized.guild_id,
            channel_id=normalized.channel_id,
            is_dm=normalized.is_dm,
        )

        async with self.sessions() as session, session.begin():
            users = UserRepository(session)
            author = await users.upsert(
                normalized.author_discord_id,
                normalized.author_name,
                normalized.guild_id,
            )
            for mentioned in message.mentions:
                await users.upsert(str(mentioned.id), mentioned.display_name, normalized.guild_id)
            bot_identity = await users.upsert(
                str(bot_user.id), bot_user.display_name, normalized.guild_id
            )
            stored_message = await MessageRepository(session).add(
                discord_message_id=normalized.discord_message_id,
                guild_id=normalized.guild_id,
                channel_id=normalized.channel_id,
                author_user_id=author.id,
                reply_to_message_id=normalized.reply_to_message_id,
                content=normalized.content,
                created_at=normalized.created_at,
                is_dm=normalized.is_dm,
            )
            state_repository = ConversationStateRepository(session)
            state = await state_repository.get(normalized.channel_id)
            server_policy = (
                await session.scalar(
                    select(ServerPolicy).where(ServerPolicy.guild_id == normalized.guild_id)
                )
                if normalized.guild_id
                else None
            )
            auto_enabled = (
                server_policy.auto_participation_enabled
                if server_policy
                else self.settings.auto_participation_enabled
            )
            decision = self.participation.decide(
                ParticipationInput(
                    author_id=normalized.author_discord_id,
                    content=normalized.content,
                    is_dm=normalized.is_dm,
                    bot_mentioned=normalized.bot_mentioned,
                    bot_replied_to=normalized.reply_to_bot,
                    wake_word_used=normalized.wake_word_used,
                    mentioned_user_ids=normalized.mentioned_user_ids,
                    bot_user_id=str(bot_user.id),
                    last_partner_id=state.last_partner_discord_id if state else None,
                    engaged_until=state.engaged_until if state else None,
                    last_spontaneous_at=state.last_spontaneous_at if state else None,
                    auto_participation_enabled=auto_enabled,
                )
            )
            judge_history: list[str] = []
            if decision.requires_judge:
                recent = await MessageRepository(session).recent(scope, 8)
                judge_history = [
                    f"{row_user.current_display_name}: {row_message.content}"
                    for row_message, row_user in recent
                    if row_message.id != stored_message.id
                ]

        archived_images = []
        if self.settings.image_storage_enabled and message.attachments:
            archived_images = await self.image_archive.archive_attachments(
                message.attachments,
                owner_user_id=author.id,
                source_message_id=stored_message.id,
                discord_message_id=normalized.discord_message_id,
                guild_id=normalized.guild_id,
                channel_id=normalized.channel_id,
                message_text=normalized.content,
            )

        recall_request = is_image_recall_request(normalized.content) and not (
            normalized.mentioned_user_ids - {str(bot_user.id)}
        )
        if recall_request:
            decision = ParticipationDecision(
                ParticipationAction.REPLY,
                normalized.author_discord_id,
                1.0,
                "explicit image recall request",
            )

        judged_participation = decision.requires_judge
        if decision.requires_judge and not recall_request:
            decision = await self.participation_judge.judge(
                ParticipationInput(
                    author_id=normalized.author_discord_id,
                    content=normalized.content,
                    is_dm=normalized.is_dm,
                    bot_mentioned=normalized.bot_mentioned,
                    bot_replied_to=normalized.reply_to_bot,
                    wake_word_used=normalized.wake_word_used,
                    mentioned_user_ids=normalized.mentioned_user_ids,
                    bot_user_id=str(bot_user.id),
                    last_partner_id=state.last_partner_discord_id if state else None,
                    engaged_until=state.engaged_until if state else None,
                    last_spontaneous_at=state.last_spontaneous_at if state else None,
                    auto_participation_enabled=auto_enabled,
                ),
                bot_name=bot_user.display_name,
                author_name=normalized.author_name,
                recent_messages=judge_history,
            )

        if decision.action == ParticipationAction.IGNORE:
            return
        if decision.action == ParticipationAction.REACT:
            try:
                await message.add_reaction(decision.emoji or "👍")
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

        recalled_images = []
        if recall_request:
            async with self.sessions() as session, session.begin():
                recalled_images = await ImageRepository(session).search(
                    scope=scope,
                    query=normalized.content,
                    limit=self.settings.image_recall_limit,
                    owner_user_id=author.id,
                )

        image_context = "\n".join(f"- {image.description}" for image in archived_images)
        content_for_model = normalized.content
        if image_context:
            content_for_model += f"\n\n[방금 첨부된 이미지 분석]\n{image_context}"

        async with self.sessions() as session, session.begin():
            context = await ContextBuilder(
                MessageRepository(session),
                MemoryRetriever(MemoryRepository(session)),
                RelationshipRepository(session),
            ).build(
                query=content_for_model,
                scope=scope,
                relevant_user_ids=[author.id, bot_identity.id],
                recent_limit=self.settings.recent_message_limit,
                memory_top_k=self.settings.memory_top_k,
            )

        try:
            if recall_request:
                reply = (
                    f"찾았어. 관련 있어 보이는 사진 {len(recalled_images)}개 가져왔어."
                    if recalled_images
                    else "저장된 사진에서 그 내용과 맞는 걸 못 찾았어."
                )
            else:
                reply = await self.response_generator.generate(
                    author_name=normalized.author_name,
                    content=content_for_model,
                    context=context,
                    profile=self.profile,
                )
            sent_bubbles = await send_response(
                message,
                reply or "ㅇㅇ",
                max_bubbles=self.settings.response_max_bubbles,
                max_chars=self.settings.response_bubble_max_chars,
            )
            for image in recalled_images:
                try:
                    await message.channel.send(
                        file=discord.File(image.stored_path, filename=image.original_filename)
                    )
                except (FileNotFoundError, discord.Forbidden, discord.HTTPException):
                    log.exception("failed to resend archived image %s", image.id)
        except Exception:
            log.exception("response generation failed")
            await message.reply(
                "지금 답 만들다가 오류 났어. 잠깐 뒤에 다시 불러줘.", mention_author=False
            )
            return

        async with self.sessions() as session, session.begin():
            users = UserRepository(session)
            bot_identity = await users.upsert(
                str(bot_user.id), bot_user.display_name, normalized.guild_id
            )
            reply_to_id = normalized.discord_message_id
            for sent_bubble in sent_bubbles:
                await MessageRepository(session).add(
                    discord_message_id=str(sent_bubble.message.id),
                    guild_id=normalized.guild_id,
                    channel_id=normalized.channel_id,
                    author_user_id=bot_identity.id,
                    reply_to_message_id=reply_to_id,
                    content=sent_bubble.text,
                    created_at=sent_bubble.message.created_at,
                    is_dm=normalized.is_dm,
                )
                reply_to_id = str(sent_bubble.message.id)
            last_sent = sent_bubbles[-1].message
            visible_reply = " ".join(bubble.text for bubble in sent_bubbles)
            await ConversationStateRepository(session).mark_replied(
                channel_id=normalized.channel_id,
                guild_id=normalized.guild_id,
                partner_discord_id=normalized.author_discord_id,
                bot_message_id=str(last_sent.id),
                engage_window_seconds=self.settings.engage_window_seconds,
                spontaneous=judged_participation,
            )
            if not self.settings.memory_extraction_enabled:
                return
            if server_policy and not server_policy.memory_enabled:
                return
            allowed_ids = {
                normalized.author_discord_id,
                str(bot_user.id),
                *normalized.mentioned_user_ids,
            }
            try:
                candidates = await self.memory_extractor.extract(
                    author_discord_user_id=normalized.author_discord_id,
                    author_name=normalized.author_name,
                    content=(
                        f"USER {normalized.author_name} ({normalized.author_discord_id}): "
                        f"{normalized.content}\n"
                        f"BOT {bot_user.display_name} ({bot_user.id}): {visible_reply}"
                    ),
                    allowed_subject_ids=allowed_ids,
                    is_dm=normalized.is_dm,
                )
                for candidate in candidates:
                    subject = await users.by_discord_id(candidate.subject_discord_user_id)
                    if subject is None:
                        continue
                    embedding = await self.provider.embed(candidate.content)
                    try:
                        await MemoryService(session).store_candidate(
                            subject=subject,
                            candidate=candidate,
                            context=ValidationContext(
                                author_discord_user_id=normalized.author_discord_id,
                                guild_id=normalized.guild_id,
                                channel_id=normalized.channel_id,
                                is_dm=normalized.is_dm,
                                source_message_id=stored_message.id,
                            ),
                            embedding=embedding,
                        )
                    except MemoryRejected as exc:
                        log.info("memory candidate rejected: %s", exc)

                if normalized.guild_id:
                    relations = await self.relationship_extractor.extract(
                        normalized.content, allowed_ids
                    )
                    for candidate in relations:
                        user_a = await users.by_discord_id(candidate.user_a_discord_id)
                        user_b = await users.by_discord_id(candidate.user_b_discord_id)
                        if user_a and user_b:
                            await RelationshipService(RelationshipRepository(session)).store(
                                guild_id=normalized.guild_id,
                                user_a=user_a,
                                user_b=user_b,
                                source_message_id=stored_message.id,
                                candidate=candidate,
                            )
            except Exception:
                # Memory extraction failure must not break an already-delivered reply.
                log.exception("post-response memory extraction failed")
