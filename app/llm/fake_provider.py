from __future__ import annotations

from collections import deque


class FakeProvider:
    def __init__(
        self,
        responses: list[str] | None = None,
        json_responses: list[dict] | None = None,
        image_descriptions: list[str] | None = None,
    ):
        self.responses = deque(responses or ["ㅇㅇ 기억해둘게"])
        self.json_responses = deque(json_responses or [{"memories": []}])
        self.image_descriptions = deque(image_descriptions or ["테스트 이미지"])

    async def complete(self, *, system: str, user: str) -> str:
        del system, user
        return self.responses.popleft() if self.responses else "ㅇㅇ"

    async def complete_json(self, *, system: str, user: str) -> dict:
        del system, user
        return self.json_responses.popleft() if self.json_responses else {"memories": []}

    async def embed(self, text: str) -> list[float] | None:
        del text
        return None

    async def describe_image(self, *, data: bytes, content_type: str, prompt: str) -> str:
        del data, content_type, prompt
        return self.image_descriptions.popleft() if self.image_descriptions else "테스트 이미지"
