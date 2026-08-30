from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")
_DUPLICATE_SUFFIX = re.compile(r"^(?P<base>.*?)(?:\s+DUP(?P<number>\d+))$", re.IGNORECASE)


def duplicate_names(source_name: str, count: int) -> list[str]:
    """Return stable Eggbev duplicate names while preserving the original base."""
    original = str(source_name or "").strip()
    if not original:
        raise ValueError("source campaign name is required")
    total = int(count)
    if total < 1 or total > 100:
        raise ValueError("duplicate count must be between 1 and 100")
    match = _DUPLICATE_SUFFIX.fullmatch(original)
    if match:
        base = match.group("base").strip()
        start = int(match.group("number")) + 1
    else:
        base = original
        start = 1
    if not base:
        raise ValueError("source campaign base name is empty")
    return [f"{base} DUP{number:02d}" for number in range(start, start + total)]


def next_midnight_et(now: datetime | None = None) -> datetime:
    """Return 00:00 America/New_York on the next calendar day."""
    current = now or datetime.now(ET)
    if current.tzinfo is None:
        raise ValueError("now must include timezone")
    local = current.astimezone(ET)
    next_date = local.date() + timedelta(days=1)
    return datetime.combine(next_date, time.min, tzinfo=ET)
