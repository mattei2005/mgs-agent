"""Read-only health signals for native Hermes jobs and failed system timers.
Completion, scheduler progress, and delivery are deliberately separate predicates.
"""
from __future__ import annotations
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError):
        return None


def native_rows(now, profiles_root=None):
    root = Path(profiles_root or os.environ.get('MGS_MONITOR_PROFILES_ROOT', '/root/.hermes/profiles'))
    rows = []
    for profile in ('zeus', 'atena', 'ares'):
        p = root / profile / 'cron/jobs.json'
        if not p.exists():
            rows.append((f'hermes:{profile}:scheduler', 'ERROR', 'scheduler store unavailable'))
            continue
        try:
            store = json.loads(p.read_text())
            jobs = store if isinstance(store, list) else store.get('jobs', [])
            if not isinstance(jobs, list):
                raise ValueError('invalid jobs contract')
        except (ValueError, OSError, TypeError):
            rows.append((f'hermes:{profile}:scheduler', 'ERROR', 'scheduler store unreadable; not a healthy zero'))
            continue
        for job in jobs:
            if not job.get('enabled') or job.get('state') not in (None, 'scheduled', 'running'):
                continue
            key = f'hermes:{profile}:{job["id"]}'
            label = str(job.get('name') or job['id'])
            status = 'OK'
            detail = f'{label}; scheduler completion and delivery checked'
            last_status = str(job.get('last_status') or '').lower()
            if last_status in ('error', 'failed', 'failure') or job.get('last_error'):
                status, detail = 'ERROR', f'{label}; last execution failed (details retained in scheduler)'
            elif job.get('last_delivery_error'):
                status, detail = 'ERROR', f'{label}; completion recorded, delivery failed'
            else:
                next_due = parse_time(job.get('next_run_at'))
                # Scheduler next_due naturally covers overnight/weekly inactive
                # windows. A dead scheduler leaves an overdue next_due behind.
                if next_due is not None and now - next_due > 30 * 60:
                    status, detail = 'STALE', f'{label}; scheduler next execution overdue >30min'
                elif next_due is None:
                    status, detail = 'UNKNOWN', f'{label}; next due unavailable; no successful execution inferred'
            rows.append((key, status, detail))
    return rows


def timer_rows():
    if os.environ.get('MGS_MONITOR_SKIP_TIMERS') == '1':
        return []
    p = subprocess.run(['systemctl', '--failed', '--type=timer', '--no-legend', '--plain', '--no-pager'], capture_output=True, text=True, timeout=15)
    if p.returncode:
        return [('systemd:timer-observation', 'ERROR', 'timer failed-state query unavailable')]
    return [(f'systemd:{line.split()[0]}', 'ERROR', 'timer unit failed') for line in p.stdout.splitlines() if line.strip()]
