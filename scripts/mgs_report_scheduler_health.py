"""Read-only receipts for existing SHEIN cron wrappers; no execution or POST."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

SHEIN_ROOT = Path('/root/mgs-agent/data/ares/meta-ads/state')
REPORTS = {
    'ares/shein-daily-cron.py': ('shein-daily-report', 24, 36 * 3600),
    # 23:31 -> 09:32 is a deliberate overnight gap, including DST variation.
    'ares/shein-intraday-cron.py': ('shein-intraday-report', 24, 12 * 3600),
    'ares/shein-campaign-creation-cron.py': ('shein-campaign-creation-daily', 36, 36 * 3600),
}


def report_health(script, now, log_mtime=0, root=None):
    if script not in REPORTS:
        return None
    root = Path(root or SHEIN_ROOT)
    directory, expected, threshold = REPORTS[script]
    home = root / directory
    try:
        if directory == 'shein-campaign-creation-daily':
            candidates = sorted(home.glob('????-??-??/run.json'))
            if not candidates:
                return ('ERROR', 'report receipt absent; delivery not inferred from fresh log')
            path = candidates[-1]
            data = json.loads(path.read_text())
            delivery = json.loads(path.with_name('delivery.json').read_text())
            status = data.get('status') == 'complete' and delivery.get('status') == 'GET_VERIFIED'
            status = status and data.get('complete_accounts') == expected and delivery.get('complete_accounts') == expected
            status = status and bool(delivery.get('message_id'))
            stamp = data.get('completed_at')
        else:
            path = home / 'last-cron-result.json'
            data = json.loads(path.read_text())
            if 'returncode' in data:
                if data.get('returncode') != 0:
                    return ('ERROR', 'report wrapper recorded failed attempt; delivery incomplete')
                stamp = data.get('at')
                payload = json.loads(data.get('stdout', ''))
            else:
                stamp = data.get('completed_at')
                payload = data
            status = payload.get('status') == 'COMPLETE_GET_VERIFIED' and payload.get('accounts') == expected
        parsed = datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('naive receipt time')
        timestamp = parsed.timestamp()
        if timestamp > now + 300:
            raise ValueError('future receipt')
        if not status:
            return ('ERROR', 'report receipt does not prove complete account coverage and verified delivery')
        if path.stat().st_mtime + 5 < log_mtime:
            return None  # Do not hide a genuinely newer wrapper error.
        age = now - timestamp
        if age > threshold:
            return ('STALE', f'verified report receipt age={int(age)//60}min threshold={threshold//60}min')
        return ('OK', f'verified report receipt accounts={expected}; age={int(age)//60}min; cadence unchanged')
    except (OSError, ValueError, TypeError, KeyError):
        return ('ERROR', 'report receipt absent or unreadable; successful delivery not inferred')
