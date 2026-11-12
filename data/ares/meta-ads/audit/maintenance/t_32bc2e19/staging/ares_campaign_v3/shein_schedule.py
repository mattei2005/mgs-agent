"""Approved SHEIN intake policy; no writes and no changes to saved manifests."""
from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def elapsed_start_is_immediate(request, profile, *, now=None):
    policy = profile.get('expired_schedule_policy') or {}
    if (policy.get('enabled') is not True or policy.get('approved_by') != '344196393512075265'
            or policy.get('scope') != 'explicit_start_same_account_day_only'
            or policy.get('when_elapsed') != 'IMMEDIATE_AFTER_QA'):
        return False
    if request.get('start_now') is True or request.get('start_next_midnight') is True or not request.get('start_time'):
        return False
    if not profile.get('timezone'):
        raise ValueError('expired schedule requires verified account timezone')
    start = datetime.fromisoformat(str(request['start_time']).replace('Z','+00:00'))
    instant = now or datetime.now(timezone.utc)
    if start.tzinfo is None or instant.tzinfo is None:
        raise ValueError('expired schedule comparison requires aware timestamps')
    tz = ZoneInfo(profile['timezone'])
    return start <= instant and start.astimezone(tz).date() == instant.astimezone(tz).date()
