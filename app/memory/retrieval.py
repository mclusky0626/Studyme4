from __future__ import annotations

from app.common.time import utcnow
from app.memory.privacy import MemoryScope
from app.memory.ranking import rank_memories
from app.memory.repository import MemoryRepository
from app.memory.schemas import RankedMemory


class MemoryRetriever:
    def __init__(self, repository: MemoryRepository):
        self.repository = repository

    async def search(
        self,
        query: str,
        scope: MemoryScope,
        *,
        subject_user_ids: list[str] | None = None,
        top_k: int = 6,
    ) -> list[RankedMemory]:
        candidates = await self.repository.conversational_candidates(
            scope=scope, subject_user_ids=subject_user_ids
        )
        ranked = rank_memories(query, candidates, top_k)
        recalled_ids = {item.id for item in ranked}
        for memory in candidates:
            if memory.id in recalled_ids:
                memory.last_recalled_at = utcnow()
                memory.recall_count += 1
        return ranked
