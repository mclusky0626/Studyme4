from datetime import datetime, timedelta

from app.common.time import utcnow
from app.conversation.participation import (
    ParticipationAction,
    ParticipationInput,
    ParticipationJudge,
    ParticipationService,
)
from app.llm.fake_provider import FakeProvider


def item(**overrides):
    values = {
        "author_id": "1",
        "content": "안녕",
        "is_dm": False,
        "bot_mentioned": False,
        "bot_replied_to": False,
        "wake_word_used": False,
        "mentioned_user_ids": set(),
        "bot_user_id": "99",
    }
    values.update(overrides)
    return ParticipationInput(**values)


def test_direct_message_always_replies():
    result = ParticipationService().decide(item(is_dm=True))
    assert result.action == ParticipationAction.REPLY


def test_other_user_mention_is_ignored():
    result = ParticipationService().decide(item(mentioned_user_ids={"2"}))
    assert result.action == ParticipationAction.IGNORE


def test_bot_reply_is_answered():
    result = ParticipationService().decide(item(bot_replied_to=True))
    assert result.action == ParticipationAction.REPLY


def test_laughter_prefers_reaction():
    result = ParticipationService().decide(item(content="ㅋㅋㅋㅋ"))
    assert result.action == ParticipationAction.REACT
    assert result.emoji == "😂"


def test_active_partner_can_continue_without_wake_word():
    result = ParticipationService().decide(
        item(last_partner_id="1", engaged_until=utcnow() + timedelta(seconds=30))
    )
    assert result.action == ParticipationAction.REPLY


def test_active_partner_with_sqlite_naive_datetime_can_continue():
    future_without_timezone = datetime.now() + timedelta(seconds=30)
    result = ParticipationService().decide(
        item(last_partner_id="1", engaged_until=future_without_timezone)
    )
    assert result.action == ParticipationAction.REPLY


def test_uncertain_message_is_silent():
    result = ParticipationService().decide(item(content="오늘 뭐 먹지"))
    assert result.action == ParticipationAction.IGNORE


def test_ambiguous_message_requests_judge_when_enabled():
    result = ParticipationService().decide(
        item(content="아까 말한 거 다시 알려줘", auto_participation_enabled=True)
    )
    assert result.action == ParticipationAction.IGNORE
    assert result.requires_judge is True


async def test_contextual_judge_can_detect_implicit_bot_conversation():
    provider = FakeProvider(
        json_responses=[
            {
                "action": "reply",
                "target_user_id": "1",
                "confidence": 0.93,
                "reason": "the author is answering the bot's previous question",
            }
        ]
    )
    result = await ParticipationJudge(provider).judge(
        item(content="응 그걸로 해줘", auto_participation_enabled=True),
        bot_name="스터디미",
        author_name="민수",
        recent_messages=["스터디미: 돼지국밥 쪽으로 찾아볼까?", "민수: 응 그걸로 해줘"],
    )
    assert result.action == ParticipationAction.REPLY
    assert result.confidence == 0.93


async def test_contextual_judge_rejects_low_confidence_reply():
    provider = FakeProvider(
        json_responses=[
            {
                "action": "reply",
                "target_user_id": "1",
                "confidence": 0.55,
                "reason": "possibly directed at the bot",
            }
        ]
    )
    result = await ParticipationJudge(provider).judge(
        item(content="뭐 먹지", auto_participation_enabled=True),
        bot_name="스터디미",
        author_name="민수",
        recent_messages=["철수: 배고프다", "민수: 뭐 먹지"],
    )
    assert result.action == ParticipationAction.IGNORE


async def test_contextual_judge_fails_silent_when_disabled():
    result = await ParticipationJudge(None).judge(
        item(content="그건 어때", auto_participation_enabled=True),
        bot_name="스터디미",
        author_name="민수",
        recent_messages=[],
    )
    assert result.action == ParticipationAction.IGNORE


async def test_spontaneous_cooldown_blocks_merely_probable_interjection():
    provider = FakeProvider(
        json_responses=[
            {
                "action": "reply",
                "target_user_id": "1",
                "confidence": 0.9,
                "reason": "the bot could add something useful",
            }
        ]
    )
    result = await ParticipationJudge(provider).judge(
        item(
            content="여행지 추천 없나",
            last_partner_id="2",
            last_spontaneous_at=utcnow(),
            auto_participation_enabled=True,
        ),
        bot_name="스터디미",
        author_name="민수",
        recent_messages=["민수: 여행지 추천 없나"],
    )
    assert result.action == ParticipationAction.IGNORE


async def test_sqlite_naive_spontaneous_datetime_is_supported():
    provider = FakeProvider(
        json_responses=[
            {
                "action": "ignore",
                "target_user_id": None,
                "confidence": 0.99,
                "reason": "human conversation",
            }
        ]
    )
    result = await ParticipationJudge(provider).judge(
        item(
            content="그건 어때",
            last_spontaneous_at=datetime.now(),
            auto_participation_enabled=True,
        ),
        bot_name="미유",
        author_name="민수",
        recent_messages=[],
    )
    assert result.action == ParticipationAction.IGNORE
