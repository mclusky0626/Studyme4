from __future__ import annotations

from collections import deque


class FakeProvider:
    def __init__(
        self,
        responses: list[str] | None = None,
        json_responses: list[dict] | None = None,
    ):
        self.responses = deque(responses or ["ㅇㅇ 기억해둘게"])
        self.json_responses = deque(json_responses or [{"memories": []}])

    async def complete(self, *, system: str, user: str) -> str:
        del system, user
        return self.responses.popleft() if self.responses else "ㅇㅇ"

    async def complete_json(self, *, system: str, user: str) -> dict:
        del system, user
        return self.json_responses.popleft() if self.json_responses else {"memories": []}

    async def embed(self, text: str) -> list[float] | None:
        del text
        return None
