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


async def test_extractor_accepts_gemini_compatible_field_names():
    provider = FakeProvider(
        json_responses=[
            {
                "memories": [
                    {
                        "subject_id": "123",
                        "visibility": "guild",
                        "action": "ADD",
                        "normalized_key": "media:anime:youjo_senki",
                        "memory": "유녀전기 애니메이션을 좋아함",
                        "is_explicit": True,
                        "confidence": 1.0,
                    }
                ]
            }
        ]
    )
    values = await MemoryExtractor(provider).extract(
        author_discord_user_id="123",
        author_name="민수",
        content="유녀전기 좋아함",
        allowed_subject_ids={"123"},
        is_dm=False,
    )
    assert len(values) == 1
    assert values[0].subject_discord_user_id == "123"
    assert values[0].content == "유녀전기 애니메이션을 좋아함"
    assert values[0].memory_type.value == "preference"
    assert values[0].importance == 0.55


async def test_extractor_keeps_valid_candidates_when_one_is_invalid():
    provider = FakeProvider(
        json_responses=[
            {
                "memories": [
                    {"subject_id": "not-a-discord-id", "memory": "잘못된 후보"},
                    {
                        "memory_type": "profile",
                        "subject_discord_user_id": "123",
                        "content": "고등학생이다",
                        "normalized_key": "profile:student",
                        "confidence": 1.0,
                        "importance": 0.7,
                        "visibility": "guild",
                    },
                ]
            }
        ]
    )
    values = await MemoryExtractor(provider).extract(
        author_discord_user_id="123",
        author_name="민수",
        content="나는 고등학생이야",
        allowed_subject_ids={"123"},
        is_dm=False,
    )
    assert [value.content for value in values] == ["고등학생이다"]
