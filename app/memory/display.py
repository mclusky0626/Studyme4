from __future__ import annotations

from app.db.models import Memory


def format_memory_overview(memories: list[Memory], *, memory_enabled: bool, limit: int = 20) -> str:
    state = "켜짐" if memory_enabled else "꺼짐"
    if not memories:
        return f"기억 저장: {state}\n저장된 장기 기억이 없어."
    items = "\n".join(
        f"`{memory.id[:8]}` [{memory.status}] "
        f"{memory.content if len(memory.content) <= 80 else memory.content[:79] + '…'}"
        for memory in memories[:limit]
    )
    return f"기억 저장: {state} · 총 {len(memories)}개\n{items}"
