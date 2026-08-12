from app.llm.fake_provider import FakeProvider
from app.memory.extractor import MemoryExtractor


async def test_extractor_rejects_invented_subject_id():
    provider = FakeProvider(
        json_responses=[
            {
                "memories": [
                    {
                        "memory_type": "preference",
                        "subject_discord_user_id": "999",
                        "content": "없는 사람은 커피를 좋아한다.",
                        "normalized_key": "drink:coffee",
                        "confidence": 0.9,
                        "importance": 0.5,
                        "visibility": "guild",
                    }
                ]
            }
        ]
    )
    values = await MemoryExtractor(provider).extract(
        author_discord_user_id="123",
        author_name="민수",
        content="커피 좋아함",
        allowed_subject_ids={"123"},
        is_dm=False,
    )
    assert values == []
