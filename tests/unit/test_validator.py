import pytest

from app.db.models import MemoryType, Visibility
from app.memory.schemas import MemoryCandidate, ValidationContext
from app.memory.validator import MemoryRejected, MemoryValidator


def candidate(**overrides):
    values = {
        "memory_type": MemoryType.PREFERENCE,
        "subject_discord_user_id": "123",
        "content": "민수는 해산물을 싫어한다.",
        "normalized_key": "food:seafood",
        "confidence": 0.95,
        "importance": 0.7,
        "visibility": Visibility.GUILD,
        "is_explicit": True,
        "sensitive": False,
    }
    values.update(overrides)
    return MemoryCandidate(**values)


def context(**overrides):
    values = {
        "author_discord_user_id": "123",
        "guild_id": "10",
        "channel_id": "20",
        "is_dm": False,
        "source_message_id": "message-id",
    }
    values.update(overrides)
    return ValidationContext(**values)


def test_dm_forces_private_visibility():
    result = MemoryValidator().validate(
        candidate(visibility=Visibility.GUILD),
        context(guild_id=None, channel_id="dm-123", is_dm=True),
    )
    assert result.visibility == Visibility.DM_PRIVATE


def test_guild_cannot_claim_dm_visibility():
    with pytest.raises(MemoryRejected):
        MemoryValidator().validate(candidate(visibility=Visibility.DM_PRIVATE), context())


def test_secret_like_memory_is_rejected():
    with pytest.raises(MemoryRejected):
        MemoryValidator().validate(candidate(content="내 password=supersecret123이야"), context())


def test_inference_cannot_have_fact_level_confidence():
    with pytest.raises(MemoryRejected):
        MemoryValidator().validate(candidate(is_explicit=False, confidence=0.9), context())
