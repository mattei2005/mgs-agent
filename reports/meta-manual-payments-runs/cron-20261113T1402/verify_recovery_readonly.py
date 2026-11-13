"""Read-only exact-target verification for this occurrence, not a business runner."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import json
import re
import sys

BASE = Path('/root/mgs-agent')
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'scripts'))
from mgs_finance_continuity import read_workbook, authored


def load(path):
    return json.loads(Path(path).read_text())


def rows(sheet):
    result = {}
    for grid in sheet.get('data', []):
        for row in grid.get('rowData', []):
            cells = row.get('values', [])
            m = re.search(r'^ID da conta: (\d+)\b', cells[0].get('note', '')) if cells else None
            if m:
                assert m[1] not in result
                result[m[1]] = cells
    return result


def value(cell):
    v = cell.get('userEnteredValue', {})
    return next(iter(v.values()), '')


c = load(BASE / 'data/meta-manual-payments/digital-trust-workbook-contract.json')
p = load(RUN / 'recovery-progress.json')
plan = load(Path(json.loads(p['completed']['api']['stdout'])['run_dir']) / 'plan.json')
inv = load(Path(json.loads(p['completed']['invoices']['stdout'])['run_dir']) / 'invoice-collection.json')
live = read_workbook(c)
(RUN / 'recovery-readback.json').write_text(json.dumps(live, ensure_ascii=False))
old = {s['properties']['sheetId']: s for s in load(RUN / 'workbook-before.json')['sheets']}
new = {s['properties']['sheetId']: s for s in live['sheets']}
assert set(old) == set(new)
assert all(authored(old[k]) == authored(new[k]) for k in old if k != c['sheet_id'])
a = rows(new[c['sheet_id']])
b = rows(old[c['sheet_id']])
assert set(a) == set(b) == set(c['account_ids'])
assert set(a) == {x['id'] for x in plan['planned']}
for item in plan['planned']:
    cells = a[item['id']]
    assert value(cells[2]) == item['default']
    for col, key in [(6, 'average_daily'), (8, 'balance'), (9, 'month_spend')]:
        assert Decimal(str(value(cells[col]))) == Decimal(item[key]), (item['id'], key)
        assert plan['collected_at'] in cells[col]['note']
    for col in (3, 7):
        assert cells[col].get('userEnteredValue') == b[item['id']][col].get('userEnteredValue')
        assert cells[col].get('note') == b[item['id']][col].get('note')
    invoice = inv['by_account'].get(item['id'])
    if invoice:
        assert Decimal(str(value(cells[5]))) == Decimal(invoice['due'])
        expected = invoice['invoice'] if Decimal(invoice['due']) > 0 and invoice['status'] != 'Paid' else ''
        assert str(value(cells[4])) == expected
    else:
        assert value(cells[4]) == ''
        assert value(cells[5]) in ('', 0)
job = next(j for j in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs'] if j['id'] == c['cron_job_id'])
assert job['enabled'] and not job['fire_claim'] and job['schedule']['expr'] == '2 8,14,21 * * *'
assert job['timezone'] == 'America/New_York'
now = datetime.now().astimezone()
assert datetime.fromisoformat(job['next_run_at']) > now
receipt = {
    'continuity_key': p['continuity_key'], 'job_id': job['id'],
    'scheduled_at': p['scheduled_at'], 'status': 'partial_validated_waiting_human_passkey',
    'verified_at': now.isoformat(), 'accounts': len(a), 'fresh_metrics_count': len(a),
    'api_collected_at': plan['collected_at'], 'source_to_live_sheet_cgij_exact': True,
    'invoice_source_to_live_sheet_ef_exact': True, 'other_sheet_data_unchanged': True,
    'h_preserved_exact': True, 'h_fresh_count': 0,
    'pending_h_account_ids': c['pay_now_account_ids'], 'pending_ui': plan['pending_ui'],
    'd_preserved_exact': True, 'business_delivery_validated': False,
    'auth_gate': 'Meta passkey: security/twofactor/reauth; visible instruction in blocked.txt and blocked.png',
    'h_run_dir': p['h_run_dir'], 'next_run_at': job['next_run_at'],
    'payments_executed': 0, 'billing_changes': 0, 'meta_writes': 0, 'cron_changes': 0,
    'next_step': 'Human completes Meta passkey on PC1 Rodolfo Chrome; positive same-target read, then resume H40 and pending D only; final API reconciliation, validation and canonical delivery remain pending.',
}
(RUN / 'recovery-validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
print(json.dumps(receipt, ensure_ascii=False))
