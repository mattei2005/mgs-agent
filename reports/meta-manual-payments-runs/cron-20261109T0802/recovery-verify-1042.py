"""Read-only source-to-live verification for the same 08:02 occurrence."""
import sys, shutil, json, re, subprocess
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
R = Path(shutil.which('hermes')).resolve().parents[2]
sys.path.insert(0, str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0, '/root/mgs-agent/scripts')
from mgs_finance_continuity import read_workbook, authored
B = Path(__file__).parent
H = Path('/root/mgs-agent/data/meta-manual-payments')
def load(p): return json.loads(p.read_text())
def save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2)); p.chmod(0o600)
def value(c): return next(iter(c.get('userEnteredValue', {}).values()), None)
def money(c): return Decimal(str(c.get('effectiveValue', {}).get('numberValue', 0)))
c = load(H/'digital-trust-workbook-contract.json')
plan = load(Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261109T104251445625/plan.json'))
P = Path('/root/mgs-agent/reports/meta-manual-payments-runs/pay-now-20261109T080433813808')
N = Path('/root/mgs-agent/reports/meta-manual-payments-runs/september-20261109T080401607897')
assert c['month_since'] == '2026-11-01' and not plan['pending_ui']
book = read_workbook(c)
save(B/'recovery-final-workbook-1042.json', book)
old = {s['properties']['sheetId']: s for s in load(B/'baseline.json')['sheets']}
new = {s['properties']['sheetId']: s for s in book['sheets']}
assert set(old) == set(new)
assert all(old[k]['properties'] == new[k]['properties'] for k in old)
other = all(authored(old[k]) == authored(new[k]) for k in old if k != c['sheet_id'])
assert other
acc = {}; totals = []
for row in new[c['sheet_id']]['data'][0]['rowData']:
    cs = row.get('values', []); cs += [{}] * max(0, 10-len(cs))
    m = re.search(r'^ID da conta: (\d+)\b', cs[0].get('note', ''))
    if m:
        assert m[1] not in acc; acc[m[1]] = cs
    elif str(value(cs[0])).startswith('TOTAL'): totals.append(cs)
assert len(acc) == 47 and set(acc) == set(c['account_ids']) == {p['id'] for p in plan['planned']}
for p in plan['planned']:
    cs = acc[p['id']]
    assert [value(cs[i]) for i in [0,1,2]] == [p['name'],p['method'],p['default']]
    for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
        assert money(cs[col]) == Decimal(p[key]) and plan['collected_at'] in cs[col]['note']
        assert 'USD' in str(cs[col]['userEnteredFormat'])
    local = datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(p['timezone'])).date()
    assert p['month_period'] == {'since':c['month_since'],'until':min(local,date.fromisoformat(c['month_until'])).isoformat()}
    assert p['average_period'] == {'since':(local-timedelta(days=3)).isoformat(),'until':(local-timedelta(days=1)).isoformat()}
    original = next(r['values'] for r in old[c['sheet_id']]['data'][0]['rowData'] if r.get('values') and re.search(r'^ID da conta: '+p['id']+r'\b',r['values'][0].get('note','')))
    assert cs[0].get('note') == original[0].get('note') and cs[0].get('textFormatRuns') == original[0].get('textFormatRuns')
ledger = load(H/'pc1-pay-now-ledger.json')['accounts']
targets = {x['account_id'] for x in load(P/'targets.json')}
v = load(P/'visual-verification.json')
assert targets == set(ledger) == set(c['pay_now_account_ids']) == set(v['verified_account_ids']) and len(targets) == 36
for aid,e in ledger.items():
    rec = load(P/(aid+'-receipt.json')); check = v['accounts_list_checks'][aid]
    assert money(acc[aid][7]) == Decimal(e['amount']) == Decimal(rec['amount']) == Decimal(check['balance_usd'])
    assert e['read_at'] == rec['read_at'] and e['read_at'] in acc[aid][7]['note']
    assert e['source'] == 'accounts_list_current_balance' and e['source'] in acc[aid][7]['note']
    assert check['row_account_id'] == aid and check['business_id'] == c['business_id'] and check['name'] == rec['name'] and check['valid_billing_list']
card = load(H/'pc1-card-ledger.json')['accounts']; gaps=[]
for aid,cs in acc.items():
    e=card.get(aid)
    if e and e.get('latest_card'):
        z=e['latest_card']; assert money(cs[3]) == Decimal(z['amount']) and e['read_at'] in cs[3]['note'] and z['method'] in cs[3]['note']
    else:
        assert value(cs[3]) is None
        gaps.append({'account_id':aid,'name':value(cs[0]),'reason':'no_charge_located_historical' if e else 'no_historical_card_instrument_proof_collected'})
assert len(gaps) == 35
inv=load(N/'receipt.json'); il=load(N/'invoice-collection.json'); assert il == load(H/'september-invoice-ledger.json')
visible=0
for aid,cs in acc.items():
    e=il['by_account'].get(aid)
    if e and Decimal(e['due'])>0: assert str(value(cs[4])) == e['invoice']; visible+=1
    else: assert value(cs[4]) is None
    if e: assert money(cs[5]) == Decimal(e['due'])
    elif value(cs[1]) == 'Linha de crédito': assert value(cs[5]) == 0
    else: assert value(cs[5]) is None
assert visible == inv['visible_invoice_numbers'] and sum((money(x[5]) for x in acc.values()),Decimal(0)) == Decimal(inv['tab_due_usd'])
checks=[]; assert len(totals)==3
for cs in totals:
    label=value(cs[0]); subset=[x for x in acc.values() if label.startswith('TOTAL GERAL') or ('CARTÃO' in label and value(x[1])=='Cartão de crédito') or ('LINHA' in label and value(x[1])=='Linha de crédito')]
    for col in [5,6,7,8,9]:
        expected=sum((money(x[col]) for x in subset),Decimal(0))
        if value(cs[col]) is None: assert expected==0; continue
        assert cs[col]['userEnteredValue']['formulaValue'].startswith('=ROUND(SUM(') and money(cs[col])==expected
        checks.append({'label':label,'column':chr(65+col),'value':str(expected)})
lease=json.loads(subprocess.check_output([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],text=True)); assert not lease['locked']
out={'status':'financial_recovery_validated_delivery_pending','continuity_key':'6a8f887c7ddb0077beeeb05b','scheduled_at':'2026-11-09T08:02:00-05:00','verified_at':datetime.now().astimezone().isoformat(),'accounts':47,'fresh_metrics_count':47,'fresh_h_count':36,'pending_ui':[], 'pending_h_account_ids':[], 'validated_metrics_at':plan['collected_at'],'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'h_source_to_live_sheet_and_note_exact':True,'d_ledger_to_live_sheet_exact':True,'h_original_collection_times_preserved':True,'other_sheet_data_unchanged':other,'h_read_times':{aid:e['read_at'] for aid,e in ledger.items()},'h_sum_usd':str(sum((Decimal(e['amount']) for e in ledger.values()),Decimal(0))),'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'renewed_card_proof_ids':['1150399088163771','1062446663435585'],'subtotal_checks':checks,'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':visible,'invoice_outside_scope':inv['outside_accounts'],'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'lease_free':True,'delivery_verified':False,'snapshot':str(B/'recovery-final-workbook-1042.json'),'metrics_run_dir':'/root/mgs-agent/reports/meta-manual-payments-runs/20261109T104251445625','pay_now_run_dir':str(P),'invoice_run_dir':str(N),'report_infra_status':'pending'}
save(B/'recovery-financial-validation.json',out)
print(json.dumps({k:v for k,v in out.items() if k not in ['h_read_times','historical_d_gaps','subtotal_checks']},ensure_ascii=False))
