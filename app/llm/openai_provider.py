from __future__ import annotations

import json
import re

from openai import AsyncOpenAI


def _json_from_text(value: str) -> dict:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        api_key: str,
        chat_model: str,
        base_url: str | None = None,
        embedding_model: str | None = None,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    async def complete(self, *, system: str, user: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    async def complete_json(self, *, system: str, user: str) -> dict:
        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
        except Exception:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system + " Return valid JSON only."},
                    {"role": "user", "content": user},
                ],
            )
        return _json_from_text(response.choices[0].message.content or "{}")

    async def embed(self, text: str) -> list[float] | None:
        if not self.embedding_model:
            return None
        response = await self.client.embeddings.create(model=self.embedding_model, input=text)
        return response.data[0].embedding
