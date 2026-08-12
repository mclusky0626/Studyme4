from __future__ import annotations

import logging
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from app.memory.schemas import MemoryCandidate

log = logging.getLogger(__name__)


class JsonCompletionProvider(Protocol):
    async def complete_json(self, *, system: str, user: str) -> dict: ...


_CANDIDATES = TypeAdapter(list[MemoryCandidate])


class MemoryExtractor:
    def __init__(self, provider: JsonCompletionProvider):
        self.provider = provider

    async def extract(
        self,
        *,
        author_discord_user_id: str,
        author_name: str,
        content: str,
        allowed_subject_ids: set[str],
        is_dm: bool,
    ) -> list[MemoryCandidate]:
        system = """You extract reusable long-term memories from a Discord message.
Return JSON with a single `memories` array. Store only explicit profile, preference,
dislike, event, plan, promise, goal, state, opinion, shared_experience, inside_joke,
or bot_promise facts. Do not store greetings, jokes presented as facts, credentials,
financial data, exact addresses, authentication codes, or unnecessary sensitive data.
Never invent a subject ID. Inferences must set is_explicit=false and confidence below 0.8.
Use a stable normalized_key such as `food:seafood` so later corrections can conflict.
Visibility must be dm_private in DMs; otherwise guild, channel, or user_private."""
        user = (
            f"author={author_name} ({author_discord_user_id})\n"
            f"allowed_subject_ids={sorted(allowed_subject_ids)}\n"
            f"is_dm={is_dm}\nmessage={content}"
        )
        payload = await self.provider.complete_json(system=system, user=user)
        try:
            candidates = _CANDIDATES.validate_python(payload.get("memories", []))
        except ValidationError as exc:
            log.warning("memory extractor returned invalid candidates: %s", exc)
            return []
        return [
            candidate
            for candidate in candidates
            if candidate.subject_discord_user_id in allowed_subject_ids
        ]
