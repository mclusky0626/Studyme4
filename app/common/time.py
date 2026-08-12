from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalize DB datetimes to aware UTC values.

    SQLite drops timezone metadata even for DateTime(timezone=True), while PostgreSQL
    preserves it. Treat a naive value read from our database as UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
