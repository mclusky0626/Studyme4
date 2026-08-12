from __future__ import annotations

from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from app.relations.models import RelationshipCandidate


class JsonCompletionProvider(Protocol):
    async def complete_json(self, *, system: str, user: str) -> dict: ...


_CANDIDATES = TypeAdapter(list[RelationshipCandidate])


class RelationshipExtractor:
    def __init__(self, provider: JsonCompletionProvider):
        self.provider = provider

    async def extract(
        self, content: str, allowed_user_ids: set[str]
    ) -> list[RelationshipCandidate]:
        payload = await self.provider.complete_json(
            system=(
                "Extract only explicit or carefully marked inferred relationships. "
                "Return JSON with a `relationships` array. IDs must come from "
                "allowed_user_ids. Tone alone is not proof."
            ),
            user=f"allowed_user_ids={sorted(allowed_user_ids)}\nmessage={content}",
        )
        try:
            values = _CANDIDATES.validate_python(payload.get("relationships", []))
        except ValidationError:
            return []
        return [
            value
            for value in values
            if value.user_a_discord_id in allowed_user_ids
            and value.user_b_discord_id in allowed_user_ids
        ]
