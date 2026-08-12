from __future__ import annotations

import base64
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

    async def describe_image(self, *, data: bytes, content_type: str, prompt: str) -> str:
        encoded = base64.b64encode(data).decode("ascii")
        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 정밀한 이미지 기록 분석기다. 검색과 향후 회상을 위해 이미지의 "
                        "시각적 근거를 빠짐없이 한국어 평문으로 기록해. 보이는 사람·사물·장소·색·"
                        "행동·배경·구도·조명·화풍·분위기와 읽을 수 있는 글자를 포함하되, "
                        "확실하지 않은 신원이나 민감한 특성은 추측하지 마. Markdown 서식이나 "
                        "대괄호 제목은 출력하지 마."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{encoded}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()
