from datetime import timedelta

from app.common.time import utcnow
from app.conversation.participation import (
    ParticipationAction,
    ParticipationInput,
    ParticipationService,
)


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


def test_uncertain_message_is_silent():
    result = ParticipationService().decide(item(content="오늘 뭐 먹지"))
    assert result.action == ParticipationAction.IGNORE
