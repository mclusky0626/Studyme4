from app.db.models import MemoryType, Visibility


def test_required_memory_enums_exist():
    assert MemoryType.BOT_PROMISE.value == "bot_promise"
    assert Visibility.DM_PRIVATE.value == "dm_private"
