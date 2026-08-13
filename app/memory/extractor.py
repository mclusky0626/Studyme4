from __future__ import annotations

import logging
from typing import Protocol

from pydantic import ValidationError

from app.memory.schemas import MemoryCandidate

log = logging.getLogger(__name__)


class JsonCompletionProvider(Protocol):
    async def complete_json(self, *, system: str, user: str) -> dict: ...


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
Return one JSON object with exactly one `memories` array. Every memory object must use
these exact fields:
{
  "should_store": true,
  "memory_type": "one allowed memory type listed below",
  "subject_discord_user_id": "numeric ID copied from allowed_subject_ids",
  "content": "one self-contained Korean fact",
  "normalized_key": "stable category:key",
  "confidence": 0.0,
  "importance": 0.0,
  "visibility": "dm_private|guild|channel|user_private",
  "is_explicit": true,
  "sensitive": false,
  "valid_until": null
}
Do not rename fields to subject_id, memory, fact, action, or type. Store only reusable
profile, preference, dislike, event, plan, promise, goal, state, opinion,
shared_experience, inside_joke, or bot_promise facts. Do not store greetings, questions,
jokes presented as facts, credentials, financial data, exact addresses, authentication
codes, or unnecessary sensitive data. Never invent a subject ID. Inferences must set
is_explicit=false and confidence below 0.8. Use a stable normalized_key such as
`food:seafood` so later corrections can conflict. Visibility must be dm_private in DMs;
otherwise guild, channel, or user_private. Return {"memories": []} when nothing qualifies."""
        user = (
            f"author={author_name} ({author_discord_user_id})\n"
            f"allowed_subject_ids={sorted(allowed_subject_ids)}\n"
            f"is_dm={is_dm}\nmessage={content}"
        )
        payload = await self.provider.complete_json(system=system, user=user)
        candidates: list[MemoryCandidate] = []
        raw_memories = payload.get("memories", [])
        if not isinstance(raw_memories, list):
            log.warning("memory extractor returned a non-list memories field")
            return []
        for raw in raw_memories:
            try:
                candidates.append(MemoryCandidate.model_validate(raw))
            except ValidationError as exc:
                log.warning("memory extractor skipped one invalid candidate: %s", exc)
        return [
            candidate
            for candidate in candidates
            if candidate.subject_discord_user_id in allowed_subject_ids
        ]
