"""UTC timestamp helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise TypeError(f"Cannot parse timestamp from {type(value)}")


def to_unix_seconds(value: datetime | str | int | float) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return int(parse_timestamp(value).timestamp())
