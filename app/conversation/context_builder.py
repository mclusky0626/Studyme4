from __future__ import annotations

from dataclasses import dataclass

from app.memory.privacy import MemoryScope
from app.memory.repository import MessageRepository
from app.memory.retrieval import MemoryRetriever
from app.relations.repository import RelationshipRepository


@dataclass(slots=True)
class ConversationContext:
    recent_messages: list[str]
    memories: list[str]
    relationships: list[str]


class ContextBuilder:
    def __init__(
        self,
        messages: MessageRepository,
        memories: MemoryRetriever,
        relationships: RelationshipRepository,
    ):
        self.messages = messages
        self.memories = memories
        self.relationships = relationships

    async def build(
        self,
        *,
        query: str,
        scope: MemoryScope,
        relevant_user_ids: list[str],
        recent_limit: int,
        memory_top_k: int,
    ) -> ConversationContext:
        recent_rows = await self.messages.recent(scope, recent_limit)
        ranked = await self.memories.search(
            query,
            scope,
            subject_user_ids=relevant_user_ids,
            top_k=memory_top_k,
        )
        relations = (
            await self.relationships.for_user(scope.guild_id, relevant_user_ids[0])
            if scope.guild_id and relevant_user_ids
            else []
        )
        return ConversationContext(
            recent_messages=[
                f"{user.current_display_name}: {message.content}" for message, user in recent_rows
            ],
            memories=[
                f"{item.content} "
                f"(신뢰도 {item.confidence:.2f}, 근거 메시지 {item.source_message_id})"
                for item in ranked
            ],
            relationships=[
                f"{item.user_a_name} -[{item.relation_type}]-> {item.user_b_name} "
                f"(신뢰도 {item.confidence:.2f})"
                for item in relations
            ],
        )
