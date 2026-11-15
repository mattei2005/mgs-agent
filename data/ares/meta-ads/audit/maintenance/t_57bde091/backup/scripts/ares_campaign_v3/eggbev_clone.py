from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")
_DUPLICATE_SUFFIX = re.compile(r"^(?P<base>.*?)(?:\s+DUP(?P<number>\d+))$", re.IGNORECASE)
_CANONICAL_CAMPAIGN_NAME = re.compile(
    r"^\s*(?P<page_sequence>\d+)\s*-\s*(?P<page_name>.+?)\s*-\s*ENG\s*-\s*US\s*-\s*"
    r"\((?P<page_token>pg_\d+)\)\s+(?P<campaign_sequence>C\d+)"
    r"(?:\s+DUP(?P<duplicate_number>\d+))?\s*$",
    re.IGNORECASE,
)
_PAGE_TOKEN = re.compile(r"^pg_\d+$", re.IGNORECASE)


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


def page_switch_campaign_name(
    source_name: str,
    *,
    target_page_sequence: int,
    target_page_name: str,
    target_page_token: str,
    duplicate_number: int,
) -> str:
    """Build the exact Eggbev name for a clone that switches Facebook Page.

    The selected target Page owns the visible page sequence, display name and
    pg token. Only the source Cnnn campaign sequence is preserved. The caller
    must supply the next free DUP number after the live collision scan.
    """
    source = str(source_name or "").strip()
    match = _CANONICAL_CAMPAIGN_NAME.fullmatch(source)
    if match is None:
        raise ValueError("source campaign name must match the canonical Eggbev pattern")
    page_sequence = int(target_page_sequence)
    if page_sequence < 1:
        raise ValueError("target page sequence must be positive")
    page_name = " ".join(str(target_page_name or "").split())
    if not page_name:
        raise ValueError("target page name is required")
    page_token = str(target_page_token or "").strip().lower()
    if _PAGE_TOKEN.fullmatch(page_token) is None:
        raise ValueError("target page token must match pg_XXXXX")
    dup = int(duplicate_number)
    if dup < 1:
        raise ValueError("duplicate number must be positive")
    campaign_sequence = match.group("campaign_sequence").upper()
    return (
        f"{page_sequence} - {page_name} - ENG - US - "
        f"({page_token}) {campaign_sequence} DUP{dup:02d}"
    )


def next_midnight_et(now: datetime | None = None) -> datetime:
    """Return 00:00 America/New_York on the next calendar day."""
    current = now or datetime.now(ET)
    if current.tzinfo is None:
        raise ValueError("now must include timezone")
    local = current.astimezone(ET)
    next_date = local.date() + timedelta(days=1)
    return datetime.combine(next_date, time.min, tzinfo=ET)
