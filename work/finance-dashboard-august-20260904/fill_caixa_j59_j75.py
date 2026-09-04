#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
WORK = BASE / 'work/finance-dashboard-august-20260904'
SHEET_ID = '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
HELPER = BASE / 'scripts/mgs_google_workspace_auth.py'
BACKUP_PATH = WORK / 'caixa-sintetico-prewrite-j59-j75-backup.json'
CANDIDATE_PATH = WORK / 'caixa-j59-j75-write-candidate.json'

spec = importlib.util.spec_from_file_location('mgs_google_workspace_auth', HELPER)
if not spec or not spec.loader:
    raise RuntimeError('canonical Google helper unavailable')
google = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = google
spec.loader.exec_module(google)
token = google.service_account_access_token([google.DRIVE_SCOPE, google.SHEETS_SCOPE])
project = google.service_account_project_id()
sa = google.load_service_account()
if sa.get('client_email') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com' or project != 'mgs-core-prod':
    raise RuntimeError('canonical Google identity mismatch')


def api(method: str, url: str, payload=None):
    status, data = google.api_json(method, url, token, payload, quota_project=project)
    if status != 200:
        err = (data.get('error') or {}).get('status') or f'HTTP_{status}'
        raise RuntimeError(f'Google API failure: {err}')
    return status, data


def values_get(a1: str, render: str):
    encoded = urllib.parse.quote(a1, safe='')
    _, data = api('GET', (
        f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}'
        f'?majorDimension=ROWS&valueRenderOption={render}'
    ))
    return data.get('values') or []


def value_put(a1: str, value, input_option='RAW'):
    encoded = urllib.parse.quote(a1, safe='')
    return api('PUT', (
        f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}'
        f'?valueInputOption={input_option}'
    ), {'range': a1, 'majorDimension': 'ROWS', 'values': [[value]]})


def value_clear(a1: str):
    encoded = urllib.parse.quote(a1, safe='')
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}:clear', {})


def cell(grid, row: int, col: int):
    if row < 1 or col < 1 or row > len(grid):
        return ''
    values = grid[row - 1]
    return values[col - 1] if col <= len(values) else ''


def col_name(n: int):
    out = ''
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def write_json(path: Path, obj):
    raw = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    path.write_text(raw, encoding='utf-8')
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def close(a, b, tol=1e-7):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)

backup = json.loads(BACKUP_PATH.read_text(encoding='utf-8'))
candidate_obj = json.loads(CANDIDATE_PATH.read_text(encoding='utf-8'))
candidate = candidate_obj['formulas']
expected_targets = set(candidate)
if expected_targets != {'J59', 'J60', 'J61', 'J62', 'J72', 'J73', 'J75'}:
    raise RuntimeError('candidate target set mismatch')
pre_formula = backup['formula']

# Re-check exact preconditions immediately before any external write.
live_formula = values_get("'CAIXA SINTETICO'!A1:R85", 'FORMULA')
if live_formula != pre_formula:
    raise RuntimeError('CAIXA formula state changed since preflight backup')
for target in expected_targets:
    row = int(target[1:])
    if cell(live_formula, row, 10) not in ('', None):
        raise RuntimeError(f'target no longer blank: {target}')

# Reversible canary in an authorized blank spacer cell.
canary_cell = "'CAIXA SINTETICO'!J63"
canary_value = f'MGS_CANARY_{int(time.time())}'
canary_ok = False
try:
    value_put(canary_cell, canary_value, 'RAW')
    got = values_get(canary_cell, 'UNFORMATTED_VALUE')
    if cell(got, 1, 1) != canary_value:
        raise RuntimeError('canary readback mismatch')
    canary_ok = True
finally:
    value_clear(canary_cell)
    restored = values_get(canary_cell, 'FORMULA')
    if cell(restored, 1, 1) not in ('', None):
        raise RuntimeError('canary restore failed')
if not canary_ok:
    raise RuntimeError('canary failed')

# Re-check after canary before committing the seven formulas.
live_formula = values_get("'CAIXA SINTETICO'!A1:R85", 'FORMULA')
if live_formula != pre_formula:
    raise RuntimeError('CAIXA formula state changed after canary')

payload = {
    'valueInputOption': 'USER_ENTERED',
    'data': [
        {'range': f"'CAIXA SINTETICO'!{target}", 'majorDimension': 'ROWS', 'values': [[candidate[target]]]}
        for target in sorted(expected_targets, key=lambda x: int(x[1:]))
    ],
    'includeValuesInResponse': True,
    'responseValueRenderOption': 'FORMULA',
}
write_url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate'
write_status = 0
write_data = {}
rolled_back = False
try:
    write_status, write_data = api('POST', write_url, payload)
    if write_data.get('totalUpdatedCells') != 7:
        raise RuntimeError(f"unexpected updated cell count: {write_data.get('totalUpdatedCells')}")

    # Give dependency formulas a bounded opportunity to recalculate.
    post = None
    source_now = None
    direct_expected = {}
    mismatches = []
    for _ in range(5):
        post = {
            'formula': values_get("'CAIXA SINTETICO'!A1:R85", 'FORMULA'),
            'unformatted': values_get("'CAIXA SINTETICO'!A1:R85", 'UNFORMATTED_VALUE'),
            'formatted': values_get("'CAIXA SINTETICO'!A1:R85", 'FORMATTED_VALUE'),
        }
        source_now = {
            'formula': values_get("'Agosto 2026'!A1:APE338", 'FORMULA'),
            'unformatted': values_get("'Agosto 2026'!A1:APE338", 'UNFORMATTED_VALUE'),
            'formatted': values_get("'Agosto 2026'!A1:APE338", 'FORMATTED_VALUE'),
        }
        mismatches = []
        for target, formula in candidate.items():
            row = int(target[1:])
            if cell(post['formula'], row, 10) != formula:
                mismatches.append({'cell': target, 'kind': 'formula'})
        direct_expected = {
            59: cell(source_now['unformatted'], 175, 16),
            60: cell(source_now['unformatted'], 176, 16),
            61: cell(source_now['unformatted'], 177, 16),
            62: cell(source_now['unformatted'], 178, 16),
            72: cell(source_now['unformatted'], 145, 15),
            73: cell(source_now['unformatted'], 161, 15),
            75: cell(source_now['unformatted'], 36, 1094),
        }
        for row, expected in direct_expected.items():
            actual = cell(post['unformatted'], row, 10)
            if not close(actual, expected):
                mismatches.append({'cell': f'J{row}', 'kind': 'value', 'expected': expected, 'actual': actual})
        if not mismatches:
            break
        time.sleep(2)
    if post is None or source_now is None or mismatches:
        raise RuntimeError(f'post-write direct readback mismatch: {mismatches}')

    # Formula scope diff: exactly the seven authorized blank cells changed.
    changed = []
    max_rows = max(len(pre_formula), len(post['formula']))
    for r in range(1, max_rows + 1):
        pre_row = pre_formula[r - 1] if r <= len(pre_formula) else []
        post_row = post['formula'][r - 1] if r <= len(post['formula']) else []
        max_cols = max(len(pre_row), len(post_row))
        for c in range(1, max_cols + 1):
            before = pre_row[c - 1] if c <= len(pre_row) else ''
            after = post_row[c - 1] if c <= len(post_row) else ''
            if before != after:
                changed.append(f'{col_name(c)}{r}')
    if set(changed) != expected_targets or len(changed) != 7:
        raise RuntimeError(f'formula scope diff mismatch: {changed}')

    # Preserve the existing correct formula family and blank spacers.
    preserved_summary = {int(k[1:]): v for k, v in candidate_obj['preserved_summary_formulas'].items()}
    for row, formula in preserved_summary.items():
        if cell(post['formula'], row, 10) != formula:
            raise RuntimeError(f'preserved summary formula changed: J{row}')
    for row in candidate_obj['preserved_spacer_rows']:
        if cell(post['formula'], row, 10) not in ('', None):
            raise RuntimeError(f'spacer row changed: J{row}')

    # Independent arithmetic checks for summaries and downstream KPIs.
    u = post['unformatted']
    def j(row): return cell(u, row, 10)
    def b(row): return cell(u, row, 2)
    checks = {
        'J64': close(j(64), sum(float(j(r) or 0) for r in range(58, 64))),
        'J67': close(j(67), (sum(float(j(r) or 0) for r in range(12, 36)) + float(j(59) or 0)) * float(b(3)) * -1),
        'J68': close(j(68), (sum(float(j(r) or 0) for r in range(53, 55)) + float(j(60) or 0)) * float(b(4)) * -1),
        'J69': close(j(69), (sum(float(j(r) or 0) for r in range(9, 11)) + float(j(61) or 0)) * float(b(3)) * -1),
        'J70': close(j(70), (sum(float(j(r) or 0) for r in range(38, 52)) + float(j(62) or 0)) * float(b(3)) * -1),
        'J71': close(j(71), sum(float(j(r) or 0) for r in range(64, 71)) * float(b(2)) * -1),
        'J77': close(j(77), sum(float(j(r) or 0) for r in range(64, 77))),
        'J79': close(j(79), float(j(77)) / -float(j(75))),
        'J80': close(j(80), float(j(77)) * 0.5),
        'J81': close(j(81), float(j(80)) * float(j(2))),
    }
    failed_checks = [name for name, ok in checks.items() if not ok]
    if failed_checks:
        raise RuntimeError(f'arithmetic checks failed: {failed_checks}')

    displayed_errors = []
    for r, row in enumerate(post['formatted'], 1):
        for c, value in enumerate(row, 1):
            if isinstance(value, str) and value.startswith('#'):
                displayed_errors.append(f'{col_name(c)}{r}:{value}')
    if displayed_errors:
        raise RuntimeError(f'displayed errors found: {displayed_errors[:20]}')

    verification = {
        'status': 'pass',
        'verified_at': datetime.now(timezone.utc).isoformat(),
        'spreadsheet_id': SHEET_ID,
        'authorized_range': "'CAIXA SINTETICO'!J59:J75",
        'write_http': write_status,
        'updated_cells': write_data.get('totalUpdatedCells'),
        'changed_formula_cells': sorted(changed, key=lambda x: int(x[1:])),
        'formula_scope_ok': True,
        'canary_cell': 'J63',
        'canary_restored_blank': True,
        'preserved_summary_formulas': sorted(f'J{r}' for r in preserved_summary),
        'preserved_spacer_rows': [f'J{r}' for r in candidate_obj['preserved_spacer_rows']],
        'formula_mismatches': [],
        'value_mismatches': [],
        'displayed_errors': [],
        'arithmetic_checks': checks,
        'values': {f'J{r}': j(r) for r in [58,59,60,61,62,64,67,68,69,70,71,72,73,75,77,79,80,81]},
        'formatted': {f'J{r}': cell(post['formatted'], r, 10) for r in [58,59,60,61,62,64,67,68,69,70,71,72,73,75,77,79,80,81]},
        'source_values_live': direct_expected,
    }
    out_path = WORK / 'caixa-j59-j75-final-verification.json'
    out_sha = write_json(out_path, verification)
    result_path = WORK / 'caixa-j59-j75-write-result.json'
    result_sha = write_json(result_path, {
        'status': 'pass',
        'write_http': write_status,
        'updated_cells': write_data.get('totalUpdatedCells'),
        'targets': sorted(expected_targets, key=lambda x: int(x[1:])),
        'canary_restored': True,
        'verification_path': str(out_path),
        'verification_sha256': out_sha,
    })
    print(json.dumps({
        'status': 'pass',
        'write_http': write_status,
        'updated_cells': write_data.get('totalUpdatedCells'),
        'changed_cells': sorted(changed, key=lambda x: int(x[1:])),
        'displayed_errors': 0,
        'canary_restored': True,
        'J64_total': j(64),
        'J77_net': j(77),
        'J79_roi': j(79),
        'J80_half_usd': j(80),
        'J81_half_brl': j(81),
        'verification_path': str(out_path),
        'verification_sha256': out_sha,
        'write_result_sha256': result_sha,
    }, ensure_ascii=False, separators=(',', ':')))
except Exception:
    # Roll back only the seven cells that were blank in the immutable backup.
    for target in sorted(expected_targets, key=lambda x: int(x[1:])):
        try:
            value_clear(f"'CAIXA SINTETICO'!{target}")
        except Exception:
            pass
    rolled_back = True
    rollback_grid = values_get("'CAIXA SINTETICO'!J59:J75", 'FORMULA')
    for row in [59,60,61,62,72,73,75]:
        local_row = row - 58
        if cell(rollback_grid, local_row, 1) not in ('', None):
            raise RuntimeError(f'write failed and rollback incomplete at J{row}')
    raise
