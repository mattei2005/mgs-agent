"""Read-only financial source-to-live verification for the same recovery."""
import json, re, sys, subprocess
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from collections import Counter
from zoneinfo import ZoneInfo
sys.path.insert(0, '/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B = Path(__file__).parent
H = Path('/root/mgs-agent/data/meta-manual-payments')
def load(p): return json.loads(p.read_text())
def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2)); p.chmod(0o600)
def val(c): return next(iter(c.get('userEnteredValue', {}).values()), None)
def money(c): return Decimal(str(c.get('effectiveValue', {}).get('numberValue', 0)))
def authored(s):
    out = {k:v for k,v in s.items() if k != 'data'}
    out['data'] = []
    for grid in s.get('data', []):
        rows = []
        for row in grid.get('rowData', []):
            cells = [{k:v for k,v in c.items() if k in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']} for c in row.get('values', [])]
            while cells and not cells[-1]: cells.pop()
            rows.append({'values':cells} if cells else {})
        while rows and not rows[-1]: rows.pop()
        out['data'].append({'rowData':rows})
    return out
c = load(H/'digital-trust-workbook-contract.json')
ph = load(B/'phases.json')
M = Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261109T011431675011')
P = Path(ph['publish_pay_now']['run_dir'])
N = Path(ph['refresh_september_invoices']['run_dir'])
plan = load(M/'plan.json'); metrics_receipt = load(M/'receipt.json')
assert metrics_receipt['status'] == 'updated_validated' and not metrics_receipt['pending_ui']
g.load_env(); token = g.service_account_access_token()
status, book = g.api_json('GET', 'https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true', token, quota_project='mgs-core-prod')
assert status == 200
save(B/'recovery-final-workbook-0114.json', book)
old = {s['properties']['sheetId']:s for s in load(B/'baseline.json')['sheets']}
new = {s['properties']['sheetId']:s for s in book['sheets']}
assert set(old) == set(new)
assert all(old[k]['properties'] == new[k]['properties'] for k in old)
other = all(authored(old[k]) == authored(new[k]) for k in old if k != c['sheet_id'])
acc = {}; totals = []
for row in new[c['sheet_id']]['data'][0]['rowData']:
    cs = row.get('values', []); cs = cs + [{}]*max(0,10-len(cs))
    m = re.search(r'^ID da conta: (\d+)\b', cs[0].get('note',''))
    if m:
        assert m[1] not in acc; acc[m[1]] = cs
    elif str(val(cs[0])).startswith('TOTAL'): totals.append(cs)
assert len(acc) == 47 and set(acc) == set(c['account_ids'])
for p in plan['planned']:
    cs = acc[p['id']]
    assert [val(cs[i]) for i in [0,1,2]] == [p['name'],p['method'],p['default']]
    for col, key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
        assert money(cs[col]) == Decimal(p[key]) and plan['collected_at'] in cs[col]['note']
    from datetime import timedelta
    local = datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(p['timezone'])).date()
    assert p['average_period'] == {'since':str(local-timedelta(days=3)), 'until':str(local-timedelta(days=1))}
    assert p['month_period']['since'] == c['month_since']
    assert p['month_period']['until'] == min(str(local),c['month_until'])
ledger = load(H/'pc1-pay-now-ledger.json')['accounts']
checks = load(P/'visual-verification.json')
targets = {x['account_id'] for x in load(P/'targets.json')}
assert targets == set(ledger) == set(checks['verified_account_ids']) == set(c['pay_now_account_ids'])
for aid in targets:
    e = ledger[aid]; check = checks['accounts_list_checks'][aid]
    assert money(acc[aid][7]) == Decimal(e['amount']) == Decimal(str(check['balance_usd']))
    assert e['source'] == 'accounts_list_current_balance' and e['source'] in acc[aid][7]['note'] and e['read_at'] in acc[aid][7]['note']
    assert check['row_account_id'] == aid and check['business_id'] == c['business_id'] and check['name'] == val(acc[aid][0])
card = load(H/'pc1-card-ledger.json')['accounts']; gaps = []
for aid, cs in acc.items():
    e = card.get(aid)
    if e and e.get('latest_card'):
        event = e['latest_card']
        assert money(cs[3]) == Decimal(event['amount']) and e['read_at'] in cs[3]['note'] and event['method'] in cs[3]['note']
    else:
        assert val(cs[3]) is None
        gaps.append({'account_id':aid,'name':val(cs[0]),'reason':'no_charge_located' if e else 'no_historical_card_instrument_proof_collected'})
inv = load(N/'receipt.json'); il = load(N/'invoice-collection.json')
assert il == load(H/'september-invoice-ledger.json')
visible = 0
for aid,cs in acc.items():
    e = il['by_account'].get(aid)
    if e and Decimal(e['due']) > 0:
        assert str(val(cs[4])) == e['invoice']; visible += 1
    else: assert val(cs[4]) is None
    if e: assert money(cs[5]) == Decimal(e['due'])
    elif val(cs[1]) == 'Linha de crédito': assert val(cs[5]) == 0
    else: assert val(cs[5]) is None
assert visible == inv['visible_invoice_numbers']
assert sum((money(x[5]) for x in acc.values()),Decimal(0)) == Decimal(inv['tab_due_usd'])
assert len(totals) == 3
for cs in totals:
    label = val(cs[0]); subset = [x for x in acc.values() if label.startswith('TOTAL GERAL') or ('CARTÃO' in label and val(x[1]) == 'Cartão de crédito') or ('LINHA' in label and val(x[1]) == 'Linha de crédito')]
    for col in [5,6,7,8,9]:
        expected = sum((money(x[col]) for x in subset),Decimal(0))
        if val(cs[col]) is None: assert expected == 0; continue
        assert cs[col]['userEnteredValue']['formulaValue'].startswith('=ROUND(SUM(') and money(cs[col]) == expected
lease = json.loads(subprocess.check_output([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],text=True))
assert not lease['locked']
out = {'status':'financial_result_validated_delivery_pending','continuity_key':'9f77ed97faf39eb7de4ba1b3','verified_at':datetime.now().astimezone().isoformat(),'accounts':len(acc),'groups':dict(Counter(val(x[1]) for x in acc.values())),'fresh_metrics_count':len(plan['planned']),'validated_metrics_at':plan['collected_at'],'run_dir':str(M),'pending_ui':[],'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'h_source_to_live_sheet_and_note_exact':True,'d_ledger_to_live_sheet_exact':True,'fresh_h_count':len(targets),'h_preserved_count':0,'h_original_collection_times_preserved':True,'pay_now_run_dir':str(P),'h_read_times':{aid:ledger[aid]['read_at'] for aid in targets},'h_sum_usd':str(sum((Decimal(ledger[x]['amount']) for x in targets),Decimal(0))),'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':len(acc)-len(gaps),'average_periods':sorted({tuple(p['average_period'].items()) for p in plan['planned']}),'month_periods':sorted({tuple(p['month_period'].items()) for p in plan['planned']}),'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':visible,'invoice_outside_scope':inv['outside_accounts'],'invoice_run_dir':str(N),'other_sheet_data_unchanged':other,'all_sheet_properties_unchanged':True,'lease_free':True,'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'delivery_verified':False,'delivery_owner':'existing continuity supervisor; no agent copy sent'}
save(B/'recovery-financial-validation.json', out)
print(json.dumps(out,ensure_ascii=False))
