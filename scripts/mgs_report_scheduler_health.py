"""Read-only receipts for existing SHEIN cron wrappers; no execution or POST."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SHEIN_ROOT = Path('/root/mgs-agent/data/ares/meta-ads/state')
REPORTS = {
    'ares/shein-daily-cron.py': ('shein-daily-report', 24, 36 * 3600),
    # 23:31 -> 09:32 is a deliberate overnight gap, including DST variation.
    'ares/shein-intraday-cron.py': ('shein-intraday-report', 24, 12 * 3600),
    'ares/shein-campaign-creation-cron.py': ('shein-campaign-creation-daily', 36, 36 * 3600),
}


def daily_recovery_receipt(home, attempt, expected):
    """Reconcile a failed wrapper with its exact D-1 frozen delivery journal.

    Never replace the historical failure or accept another day's green receipt.
    This is local receipt validation only: no collection, execution or POST.
    """
    failed = datetime.fromisoformat(str(attempt).replace('Z', '+00:00'))
    if failed.tzinfo is None:
        raise ValueError('naive wrapper time')
    day = (failed.astimezone(ZoneInfo('America/New_York')).date() - timedelta(days=1)).isoformat()
    directory = home / day
    path = directory / 'completion.json'

    def read(path):
        return json.loads(path.read_text())

    def require(condition):
        if not condition:
            raise ValueError('incomplete or mismatched daily recovery journal')

    completion = read(path)
    request = read(directory / 'request.json')
    require(isinstance(completion, dict) and isinstance(request, dict))
    require(completion.get('date') == request.get('date') == day)
    require(completion.get('status') == 'COMPLETE_GET_VERIFIED' and completion.get('accounts') == expected)
    completed = datetime.fromisoformat(str(completion.get('completed_at')).replace('Z', '+00:00'))
    require(completed.tzinfo is not None and completed >= failed)
    bindings = request.get('bindings')
    deliveries = completion.get('deliveries')
    if not isinstance(bindings, list) or not isinstance(deliveries, list):
        raise ValueError('invalid bindings or deliveries')
    require(len(bindings) == len(deliveries) == expected)
    require(all(isinstance(b, dict) for b in bindings + deliveries))
    pairs = {(b.get('account_id'), b.get('thread_id')) for b in bindings}
    require(len(pairs) == expected)
    require(len({p[0] for p in pairs}) == len({p[1] for p in pairs}) == expected)
    require(all(isinstance(a, str) and a.isdigit() and isinstance(t, str) and t.isdigit() for a, t in pairs))
    require({(d.get('account_id'), d.get('thread_id')) for d in deliveries} == pairs)
    message_ids = []
    for delivery in deliveries:
        account = directory / delivery['account_id']
        require(read(account / 'delivery.json') == delivery)
        require(delivery.get('status') == 'COMPLETE_GET_VERIFIED')
        parts = read(account / 'report.parts.json')
        receipts = delivery.get('parts')
        if not isinstance(parts, list) or not isinstance(receipts, list) or not parts:
            raise ValueError('invalid frozen parts or receipts')
        require(len(parts) == len(receipts) and all(isinstance(p, str) for p in parts))
        require('\n\n'.join(parts) == (account / 'report.md').read_text())
        for index, (text, receipt) in enumerate(zip(parts, receipts)):
            require(isinstance(receipt, dict))
            intent = read(account / f'delivery-intent-{index}.json')
            require(isinstance(intent, dict))
            require(receipt.get('verified') is True and receipt.get('part') == index)
            mid = receipt.get('id')
            require(isinstance(mid, str) and mid.isdigit())
            require(intent.get('message_id') == mid and intent.get('part') == index)
            require(intent.get('thread_id') == delivery['thread_id'] and intent.get('status') == 'GET_VERIFIED')
            require(intent.get('sha256') == hashlib.sha256(text.encode()).hexdigest())
            message_ids.append(mid)
    require(len(message_ids) == len(set(message_ids)) == completion.get('published_parts'))
    return path, completion


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
                    if directory != 'shein-daily-report':
                        return ('ERROR', 'report wrapper recorded failed attempt; delivery incomplete')
                    path, payload = daily_recovery_receipt(home, data.get('at'), expected)
                    stamp = payload.get('completed_at')
                else:
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
