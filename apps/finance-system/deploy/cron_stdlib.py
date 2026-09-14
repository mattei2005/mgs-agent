"""Small fail-closed five-field cron expander for MGS schedule audits."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo


def _field(text: str, minimum: int, maximum: int, *, sunday: bool = False) -> tuple[set[int], bool]:
    if not text or any(ch not in "0123456789*,-/" for ch in text):
        raise ValueError(f"unsupported cron field: {text!r}")
    values: set[int] = set()
    unrestricted = text == "*"
    for part in text.split(","):
        base, slash, step_text = part.partition("/")
        step = int(step_text) if slash else 1
        if step <= 0:
            raise ValueError("cron step must be positive")
        if base == "*":
            start, stop = minimum, maximum
        elif "-" in base:
            left, right = base.split("-", 1)
            start, stop = int(left), int(right)
        else:
            start = stop = int(base)
        if start < minimum or stop > maximum or start > stop:
            raise ValueError(f"cron field outside {minimum}-{maximum}: {text!r}")
        values.update(range(start, stop + 1, step))
    if sunday and 7 in values:
        values.add(0)
        values.discard(7)
    return values, unrestricted


def cron_matches(expression: str, moment: dt.datetime) -> bool:
    parts = expression.split()
    if len(parts) != 5 or moment.tzinfo is None:
        raise ValueError("cron expression must have five fields and an aware datetime")
    minutes, _ = _field(parts[0], 0, 59)
    hours, _ = _field(parts[1], 0, 23)
    month_days, month_day_any = _field(parts[2], 1, 31)
    months, _ = _field(parts[3], 1, 12)
    week_days, week_day_any = _field(parts[4], 0, 7, sunday=True)
    cron_weekday = (moment.weekday() + 1) % 7
    if month_day_any and week_day_any:
        day_matches = True
    elif month_day_any:
        day_matches = cron_weekday in week_days
    elif week_day_any:
        day_matches = moment.day in month_days
    else:
        day_matches = moment.day in month_days or cron_weekday in week_days
    return moment.minute in minutes and moment.hour in hours and moment.month in months and day_matches


def cron_dates_between(expression: str, start: dt.datetime, end: dt.datetime, timezone: ZoneInfo) -> list[dt.datetime]:
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("start/end must be ordered aware datetimes")
    cursor = start.astimezone(dt.timezone.utc).replace(second=0, microsecond=0)
    if cursor < start.astimezone(dt.timezone.utc):
        cursor += dt.timedelta(minutes=1)
    stop = end.astimezone(dt.timezone.utc)
    out: list[dt.datetime] = []
    while cursor < stop:
        local = cursor.astimezone(timezone)
        if cron_matches(expression, local):
            out.append(local)
        cursor += dt.timedelta(minutes=1)
    return out
