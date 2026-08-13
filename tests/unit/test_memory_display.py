from types import SimpleNamespace

from app.memory.display import format_memory_overview


def test_empty_memory_overview_reports_enabled_state():
    assert format_memory_overview([], memory_enabled=True) == (
        "기억 저장: 켜짐\n저장된 장기 기억이 없어."
    )


def test_memory_overview_reports_real_count_and_contents():
    memories = [
        SimpleNamespace(id="abcdefgh-1234", status="active", content="근대역사를 좋아한다."),
        SimpleNamespace(id="ijklmnop-1234", status="active", content="개발자가 꿈이다."),
    ]
    text = format_memory_overview(memories, memory_enabled=True)
    assert "총 2개" in text
    assert "`abcdefgh` [active] 근대역사를 좋아한다." in text
    assert "개발자가 꿈이다." in text
