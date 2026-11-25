"""Read-only occurrence verifier for the recovered SB token-monitor alert.

Never refresh authentication, run apply, or publish a business/diagnostic message.
The existing supervisor remains the only queue owner and delivery executor.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import time
from datetime import datetime

BASE = Path('/root/mgs-agent')
KEY = '24c94f890699dee6148cf511'
ALERT = '1572362593874608159'
SOURCE_KEY = 'alert:' + ALERT
RECOVERIES = {
    KEY: ALERT,
    'e853905050082dbd77669386': '1575042753283227769',
}
QUEUE_DB = Path('/root/.hermes/shared/automation-continuity/queue.sqlite3')


def probe(base):
    command = ['flock', '-n', '/var/lock/monitor_sb_messenger_token_invalid.lock',
               'xvfb-run', '-a', '/root/.local/share/mgs/sb-venv/bin/python',
               str(base / 'scripts/monitor-sb-messenger-token-invalid.py'), '--dry-run']
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise ValueError('Exact read-only consumer unavailable')
    lines = [line for line in result.stdout.splitlines() if line.startswith('{')]
    if not lines:
        raise ValueError('Consumer JSON missing')
    return json.loads(lines[-1])


def observation(base=BASE, reader=None, now=None, queue_path=QUEUE_DB, key=KEY, alert=ALERT):
    if RECOVERIES.get(key) != alert:
        return None
    source_key = 'alert:' + alert
    root = base / 'reports/automation-recovery' / key
    path = root / 'checkpoint.json'
    if not path.exists():
        return None
    if queue_path is not None:
        try:
            with sqlite3.connect(f'file:{queue_path}?mode=ro', uri=True, timeout=5) as db:
                row = db.execute('SELECT source_key,state FROM requests WHERE key=?', (key,)).fetchone()
            if row is None or row[0] != source_key or row[1] in ('completed_validated', 'cancelled_owner'):
                return None
        except (OSError, sqlite3.Error):
            return None
    now = time.time() if now is None else now
    result = {'status': 'UNKNOWN', 'verified': False, 'target': source_key,
              'receipt': str(path), 'at': now,
              'source': {'kind': 'alert', 'profile': 'zeus', 'alert_id': alert,
                         'alert_channel': '1498132022634483894'}}
    try:
        receipt = json.loads(path.read_text())
        if receipt.get('operation_key') != key or receipt.get('alert_id') != alert:
            raise ValueError('Occurrence identity mismatch')
        if receipt.get('authority_message_ids') != ['1569193434189668453', '1545180305961386055']:
            raise ValueError('Authority mismatch')
        if receipt.get('status') != 'business_recovered_waiting_supervisor_closure':
            raise ValueError('Recovery receipt not ready')
        if receipt.get('initial_pending') is not None or receipt.get('apply_exit') != 0 or receipt.get('apply_mode') != 'noop':
            raise ValueError('Business effects not certified')
        script = base / 'scripts/monitor-sb-messenger-token-invalid.py'
        if hashlib.sha256(script.read_bytes()).hexdigest() != receipt.get('canonical_script_sha256'):
            raise ValueError('Canonical consumer changed')
        state = json.loads((base / 'data/sb-messenger-token-invalid-monitor.json').read_text())
        stamp = datetime.fromisoformat(state['last_check']).timestamp()
        if stamp < receipt['natural_tick_not_before'] or stamp > now + 30 or now - stamp > 1200:
            raise ValueError('Fresh subsequent producer tick not verified')
        if state.get('consecutive_failures') != 0 or state.get('last_error') is not None or state.get('pending') is not None:
            raise ValueError('Canonical monitor still unhealthy or pending')
        if state.get('last_seen_id') != receipt['preserved_cursor']:
            raise ValueError('New business occurrence needs separate delivery reconciliation')
        live = (reader or probe)(base)
        if live.get('ok') is not True or live.get('mode') != 'noop' or live.get('new_alerts') != 0 or live.get('last_seen_id') != receipt['preserved_cursor']:
            raise ValueError('Live exact-consumer no-op not verified')
        after = json.loads((base / 'data/sb-messenger-token-invalid-monitor.json').read_text())
        if after != state:
            raise ValueError('Concurrent producer state changed')
        result.update(status='OK', verified=True, evidence={
            'exact_consumer_live_read': True, 'natural_tick_last_check': state['last_check'],
            'cursor': state['last_seen_id'], 'alerts_seen': live['alerts_seen'],
            'new_alerts': 0, 'new_business_delivery_required': False,
            'credentials_changed': False})
    except Exception as exc:
        result['receipt'] += '; unverified:' + type(exc).__name__
    return result
