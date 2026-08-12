from datetime import UTC, datetime, timedelta, timezone

from app.common.time import as_utc


def test_naive_database_datetime_is_interpreted_as_utc():
    value = as_utc(datetime(2026, 8, 12, 12, 0))
    assert value.tzinfo is UTC
    assert value.hour == 12


def test_aware_datetime_is_converted_to_utc():
    value = as_utc(datetime(2026, 8, 12, 21, 0, tzinfo=timezone(timedelta(hours=9))))
    assert value == datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
