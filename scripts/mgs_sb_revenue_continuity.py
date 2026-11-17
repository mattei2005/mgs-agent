"""Read-only verification of the exact recovered Messenger revenue incident.

This adapter never runs the business sync, changes its schedule or posts a report.
It supplies the existing supervisor with live evidence for the original alert key.
"""
import fcntl
import hashlib
import importlib.util
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sqlite3
import time
import urllib.parse

BASE = Path('/root/mgs-agent')
KEY = '64078873756ff45895aade65'
ALERT = '1572239665250181151'
SOURCE_KEY = 'alert:' + ALERT
SHEET = '1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY'
EXPECTED_SHA = '900bde8902b44b6a50660da377ea48aa2dbba74726984c4565a486b493534453'
CENT = Decimal('0.01')
QUEUE_DB = Path('/root/.hermes/shared/automation-continuity/queue.sqlite3')


def read_column(base, row_count):
    spec = importlib.util.spec_from_file_location('revenue_google_auth', base / 'scripts/mgs_google_workspace_auth.py')
    if spec is None or spec.loader is None:
        raise ValueError('Canonical Google helper unavailable')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    account = helper.load_service_account()
    if account.get('client_email') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com' or account.get('project_id') != 'mgs-core-prod':
        raise ValueError('Canonical Google identity mismatch')
    token = helper.service_account_access_token()
    area = urllib.parse.quote(f"'Migracao 22/06'!C1:C{row_count}", safe='')
    status, data = helper.api_json('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{area}?valueRenderOption=UNFORMATTED_VALUE', token, quota_project='mgs-core-prod')
    if status != 200:
        raise ValueError(f'Independent Sheets read HTTP {status}')
    return data.get('values') or []


def observation(base=BASE, reader=None, now=None, queue_path=QUEUE_DB):
    root = base / 'reports/automation-recovery' / KEY
    if not (root / 'checkpoint.json').exists():
        return None
    # Do not add a recurring credential lookup once the original owner closed it.
    if queue_path is not None:
        try:
            with sqlite3.connect(f'file:{queue_path}?mode=ro', uri=True, timeout=5) as db:
                row = db.execute('SELECT source_key,state FROM requests WHERE key=?', (KEY,)).fetchone()
            if row is None or row[0] != SOURCE_KEY or row[1] in ('completed_validated', 'cancelled_owner'):
                return None
        except (OSError, sqlite3.Error):
            return None
    result = {'status': 'UNKNOWN', 'verified': False, 'target': SOURCE_KEY,
              'receipt': str(root / 'checkpoint.json'), 'at': time.time() if now is None else now,
              'source': {'kind': 'alert', 'profile': 'zeus', 'alert_id': ALERT,
                         'alert_channel': '1498132022634483894'}}
    try:
        receipt = json.loads((root / 'checkpoint.json').read_text())
        if receipt.get('operation_id') != KEY or receipt.get('alert_id') != ALERT or receipt.get('status') != 'business_validated':
            raise ValueError('Wrong or incomplete occurrence receipt')
        if receipt.get('authority_message_id') != '1571311723217035436':
            raise ValueError('Wrong original authority')
        if receipt.get('target') != {'sheet_id': SHEET, 'tab': 'Migracao 22/06', 'gid': 542936436, 'column': 'C'}:
            raise ValueError('Wrong business target')
        state = json.loads((base / 'data/sb-messenger-revenue-sheet-sync-state.json').read_text())
        if state != receipt['canonical_state'] or state.get('status') != 'SYNC_OK' or state.get('readback') != 'exact_cents_ok':
            raise ValueError('Canonical state changed or not verified')
        if state.get('period_start') != '2026-11-15' or state.get('period_end') != '2026-11-17' or state.get('days') != 3 or state.get('includes_current_day') is not True:
            raise ValueError('Wrong recovered report dates')
        raw = (root / 'expected-column.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            raise ValueError('Frozen business write values changed')
        expected = json.loads(raw)
        row_count = expected['row_count']
        if type(row_count) is not int or not 220 <= row_count <= 10000:
            raise ValueError('Unexpected sheet bounds')
        wanted = {int(k): Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP) for k, v in expected['values'].items()}
        if any(not 2 <= k <= row_count for k in wanted) or len(wanted) != state['written_rows']:
            raise ValueError('Expected row identity/count mismatch')
        with Path('/var/lock/sync_sb_messenger_revenue_sheet.lock').open('r') as lock:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            values = (reader or (lambda n: read_column(base, n)))(row_count)
        if not values or values[0] != ['RECEITA 3 DIAS'] or len(values) > row_count:
            raise ValueError('Sheet header/bounds drift')
        actual = {}
        for row, cells in enumerate(values[1:], 2):
            if cells and str(cells[0]).strip():
                value = cells[0]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError('Non-numeric revenue value')
                actual[row] = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
        total = str(sum(actual.values(), Decimal(0)).quantize(CENT))
        if actual != wanted or total != state['written_total']:
            raise ValueError('Live full-column exact-cent mismatch')
        result.update(status='OK', verified=True, evidence={'written_rows': len(actual), 'written_total': total,
                      'period_start': state['period_start'], 'period_end': state['period_end'],
                      'expected_sha256': EXPECTED_SHA, 'live_google_get': True})
    except Exception as exc:
        result['receipt'] += '; unverified:' + type(exc).__name__
    return result
