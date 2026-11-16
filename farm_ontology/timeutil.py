"""Timezone-aware instants. Naive datetimes are rejected."""

from __future__ import annotations

from datetime import datetime, timezone


def ensure_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def parse_time(text: str) -> datetime:
    if not isinstance(text, str) or not text:
        raise ValueError("time must be an ISO-8601 string with a timezone")
    normalised = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalised)
    return ensure_utc(parsed, text)
