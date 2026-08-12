from app.conversation.participation import (
    ParticipationAction,
    ParticipationInput,
    ParticipationService,
)
from app.conversation.state import ConversationStateRepository


async def test_sqlite_round_trip_channel_state_can_be_compared(sessions):
    async with sessions() as session, session.begin():
        await ConversationStateRepository(session).mark_replied(
            channel_id="channel-a",
            guild_id="guild-a",
            partner_discord_id="123",
            bot_message_id="message-a",
            engage_window_seconds=90,
            spontaneous=True,
        )

    async with sessions() as session:
        state = await ConversationStateRepository(session).get("channel-a")
        assert state is not None
        # SQLite returns these as naive despite DateTime(timezone=True).
        assert state.engaged_until is not None
        assert state.engaged_until.tzinfo is None
        decision = ParticipationService().decide(
            ParticipationInput(
                author_id="123",
                content="응 그거 해줘",
                is_dm=False,
                bot_mentioned=False,
                bot_replied_to=False,
                wake_word_used=False,
                mentioned_user_ids=set(),
                bot_user_id="999",
                last_partner_id=state.last_partner_discord_id,
                engaged_until=state.engaged_until,
                last_spontaneous_at=state.last_spontaneous_at,
                auto_participation_enabled=True,
            )
        )
    assert decision.action == ParticipationAction.REPLY
