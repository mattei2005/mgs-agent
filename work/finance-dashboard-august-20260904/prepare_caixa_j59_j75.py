#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
WORK = BASE / 'work/finance-dashboard-august-20260904'
SHEET_ID = '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
HELPER = BASE / 'scripts/mgs_google_workspace_auth.py'

spec = importlib.util.spec_from_file_location('mgs_google_workspace_auth', HELPER)
if not spec or not spec.loader:
    raise RuntimeError('canonical Google helper unavailable')
google = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = google
spec.loader.exec_module(google)

token = google.service_account_access_token([google.DRIVE_SCOPE, google.SHEETS_SCOPE])
project = google.service_account_project_id()
sa = google.load_service_account()
if sa.get('client_email') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com':
    raise RuntimeError('canonical service account mismatch')
if project != 'mgs-core-prod':
    raise RuntimeError('canonical project mismatch')


def api(method: str, url: str, payload=None):
    status, data = google.api_json(method, url, token, payload, quota_project=project)
    if status != 200:
        err = (data.get('error') or {}).get('status') or f'HTTP_{status}'
        raise RuntimeError(f'Google API failure: {err}')
    return data


def values_get(a1: str, render: str):
    encoded = urllib.parse.quote(a1, safe='')
    url = (
        f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}'
        f'?majorDimension=ROWS&valueRenderOption={render}'
    )
    return api('GET', url).get('values') or []


def cell(grid, row: int, col: int):
    if row < 1 or col < 1 or row > len(grid):
        return ''
    values = grid[row - 1]
    return values[col - 1] if col <= len(values) else ''


def write_json(path: Path, obj):
    raw = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    path.write_text(raw, encoding='utf-8')
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

# Exact live target backup in all render modes.
caixa_range = "'CAIXA SINTETICO'!A1:R85"
source_range = "'Agosto 2026'!A1:APE338"
caixa = {
    'formula': values_get(caixa_range, 'FORMULA'),
    'unformatted': values_get(caixa_range, 'UNFORMATTED_VALUE'),
    'formatted': values_get(caixa_range, 'FORMATTED_VALUE'),
}
source = {
    'formula': values_get(source_range, 'FORMULA'),
    'unformatted': values_get(source_range, 'UNFORMATTED_VALUE'),
    'formatted': values_get(source_range, 'FORMATTED_VALUE'),
}
created_at = datetime.now(timezone.utc).isoformat()
backup = {
    'created_at': created_at,
    'spreadsheet_id': SHEET_ID,
    'range': caixa_range,
    **caixa,
}
backup_path = WORK / 'caixa-sintetico-prewrite-j59-j75-backup.json'
backup_sha = write_json(backup_path, backup)

# J is column 10. Preserve correct pre-existing summary formulas and spacer rows;
# only the seven missing August source-link formulas are write targets.
write_rows = [59, 60, 61, 62, 72, 73, 75]
preserved_summary = {
    64: '=SUM(J58:J63)',
    67: '=SUM(J12:J35,J59)*$B$3*-1',
    68: '=SUM(J53:J54,J60)*$B$4*-1',
    69: '=SUM(J9:J10,J61)*$B$3*-1',
    70: '=SUM(J38:J51,J62)*$B$3*-1',
    71: '=SUM(J64:J70)*$B$2*-1',
}
spacer_rows = [63, 65, 66, 74]
not_blank = {r: cell(caixa['formula'], r, 10) for r in write_rows if cell(caixa['formula'], r, 10) not in ('', None)}
summary_mismatches = {
    r: cell(caixa['formula'], r, 10)
    for r, expected in preserved_summary.items()
    if cell(caixa['formula'], r, 10) != expected
}
spacer_not_blank = {r: cell(caixa['formula'], r, 10) for r in spacer_rows if cell(caixa['formula'], r, 10) not in ('', None)}
if not_blank:
    raise RuntimeError(f'write cells are no longer blank: {sorted(not_blank)}')
if summary_mismatches:
    raise RuntimeError(f'pre-existing summary formula mismatch: {summary_mismatches}')
if spacer_not_blank:
    raise RuntimeError(f'spacer rows are no longer blank: {sorted(spacer_not_blank)}')
if cell(caixa['formula'], 58, 10) != '=SUM(J9:J57)':
    raise RuntimeError('J58 prerequisite formula mismatch')

# Validate August semantic source labels and formulas from the live sheet.
source_labels = {
    'Q175': cell(source['formula'], 175, 17),
    'Q176': cell(source['formula'], 176, 17),
    'Q177': cell(source['formula'], 177, 17),
    'Q178': cell(source['formula'], 178, 17),
    'M145': cell(source['formula'], 145, 13),
    'M161': cell(source['formula'], 161, 13),
}
expected_labels = {
    'Q175': 'Invalidos AV',
    'Q176': 'Invalidos M2',
    'Q177': 'Invalidos YM',
    'Q178': 'Invalidos JBF',
    'M145': 'Total de Despesas Adicionais:',
    'M161': 'Salario e comissoes:',
}
if source_labels != expected_labels:
    raise RuntimeError(f'August source label mismatch: {source_labels}')
apb_formula = cell(source['formula'], 36, 1094)  # APB
if '"GASTOS_TOTAL"' not in str(apb_formula) or '$E36:$AMA36' not in str(apb_formula) or '$E136:$AMA136' not in str(apb_formula):
    raise RuntimeError('APB36 is not the expected all-block GASTOS_TOTAL aggregator')

source_cells = {
    'P175': cell(source['unformatted'], 175, 16),
    'P176': cell(source['unformatted'], 176, 16),
    'P177': cell(source['unformatted'], 177, 16),
    'P178': cell(source['unformatted'], 178, 16),
    'O145': cell(source['unformatted'], 145, 15),
    'O161': cell(source['unformatted'], 161, 15),
    'APB36': cell(source['unformatted'], 36, 1094),
}
if not all(isinstance(v, (int, float)) for v in source_cells.values()):
    raise RuntimeError(f'non-numeric August source value: {source_cells}')
source_display = {
    'P175': cell(source['formatted'], 175, 16),
    'P176': cell(source['formatted'], 176, 16),
    'P177': cell(source['formatted'], 177, 16),
    'P178': cell(source['formatted'], 178, 16),
    'O145': cell(source['formatted'], 145, 15),
    'O161': cell(source['formatted'], 161, 15),
    'APB36': cell(source['formatted'], 36, 1094),
}
if any(str(v).startswith('#') for v in source_display.values()):
    raise RuntimeError(f'August source displays an error: {source_display}')

candidate = {
    'J59': "=SUM('Agosto 2026'!P175)",
    'J60': "=SUM('Agosto 2026'!P176)",
    'J61': "=SUM('Agosto 2026'!P177)",
    'J62': "=SUM('Agosto 2026'!P178)",
    'J72': "=SUM('Agosto 2026'!O145)",
    'J73': "=SUM('Agosto 2026'!O161)",
    'J75': "=SUM('Agosto 2026'!APB36)",
}
# Adjacent-month formula family check for all preserved intra-summary formulas.
for row, expected in preserved_summary.items():
    i_formula = str(cell(caixa['formula'], row, 9))
    translated = i_formula.replace('I', 'J')
    if translated != expected:
        raise RuntimeError(f'adjacent formula family mismatch at row {row}: {i_formula!r}')

candidate_obj = {
    'created_at': created_at,
    'spreadsheet_id': SHEET_ID,
    'authorized_range': "'CAIXA SINTETICO'!J59:J75",
    'target_count': len(candidate),
    'preserved_summary_formulas': {f'J{row}': formula for row, formula in preserved_summary.items()},
    'preserved_spacer_rows': spacer_rows,
    'formulas': candidate,
    'source_labels': source_labels,
    'source_values': source_cells,
    'source_display': source_display,
    'source_formula_APB36': apb_formula,
}
candidate_path = WORK / 'caixa-j59-j75-write-candidate.json'
candidate_sha = write_json(candidate_path, candidate_obj)
print(json.dumps({
    'status': 'pass',
    'backup_path': str(backup_path),
    'backup_sha256': backup_sha,
    'candidate_path': str(candidate_path),
    'candidate_sha256': candidate_sha,
    'target_count': len(candidate),
    'spacer_rows_preserved': spacer_rows,
    'source_values': source_cells,
}, ensure_ascii=False, separators=(',', ':')))
