from __future__ import annotations

import math
import re
from datetime import UTC, datetime

from app.common.time import as_utc
from app.db.models import Memory
from app.memory.schemas import RankedMemory

_TOKEN = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(text)}


def rank_memories(query: str, memories: list[Memory], top_k: int) -> list[RankedMemory]:
    query_tokens = _tokens(query)
    now = datetime.now(UTC)
    ranked: list[RankedMemory] = []
    for memory in memories:
        memory_tokens = _tokens(memory.content)
        union = query_tokens | memory_tokens
        lexical = len(query_tokens & memory_tokens) / len(union) if union else 0.0
        age_days = max((now - as_utc(memory.updated_at)).total_seconds() / 86400, 0)
        recency = math.exp(-age_days / 90)
        repeated = min(math.log1p(memory.recall_count) / 4, 1.0)
        explicit_bonus = 1.0 if memory.is_explicit else 0.45
        score = (
            lexical * 0.45
            + memory.importance * 0.20
            + recency * 0.12
            + repeated * 0.08
            + memory.confidence * 0.10
            + explicit_bonus * 0.05
        )
        ranked.append(
            RankedMemory(
                id=memory.id,
                content=memory.content,
                memory_type=memory.memory_type,
                confidence=memory.confidence,
                importance=memory.importance,
                score=round(score, 6),
                source_message_id=memory.source_message_id,
                valid_from=memory.valid_from,
            )
        )
    return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]
