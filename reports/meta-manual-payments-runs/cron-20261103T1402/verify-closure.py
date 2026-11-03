#!/usr/bin/env python3
"""Read-only source and full workbook acceptance for the existing financial tick."""
import json,sys,re,subprocess
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from collections import Counter
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B=Path(__file__).parent
H=Path('/root/mgs-agent/data/meta-manual-payments')
R=B.parent/'20261103T142853102717'
P=B.parent/'pay-now-20261103T140536679703'
N=B.parent/'september-20261103T140500934654'
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),None)
def num(c):return Decimal(str(c.get('effectiveValue',{}).get('numberValue',c.get('userEnteredValue',{}).get('numberValue',0))))
def parse(sh):
 accounts={};totals=[]
 for row in sh.get('data',[{}])[0].get('rowData',[]):
  cs=row.get('values',[]);cs=cs+[{}]*max(0,10-len(cs))
  m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))
  if m:assert m[1] not in accounts;accounts[m[1]]=cs
  elif str(val(cs[0])).startswith('TOTAL'):totals.append(cs)
 return accounts,totals
def authored(sh):
 out={'properties':sh['properties'],'data':[]}
 for grid in sh.get('data',[]):
  rows=[]
  for row in grid.get('rowData',[]):
   cells=[{k:v for k,v in x.items()if k in ['userEnteredValue','note','userEnteredFormat']}for x in row.get('values',[])]
   while cells and not cells[-1]:cells.pop()
   rows.append({'values':cells}if cells else {})
  while rows and not rows[-1]:rows.pop()
  out['data'].append({'rowData':rows})
 return out
c=load(H/'digital-trust-workbook-contract.json');plan=load(R/'plan.json');mr=load(R/'receipt.json');baseline=load(B/'baseline.json')
assert mr['status']=='updated_validated' and mr['pending_ui']==[]
assert c['month_since']=='2026-11-01' and c['month_until']=='2026-11-30'
g.load_env();sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod'
t=g.service_account_access_token();s,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert s==200
save(B/'final-workbook-readback.json',book)
old={x['properties']['sheetId']:x for x in baseline['sheets']};new={x['properties']['sheetId']:x for x in book['sheets']};assert set(old)==set(new)
assert all(old[s]['properties']==new[s]['properties']for s in old),'sheet_properties_changed'
other_unchanged=all(authored(old[s])==authored(new[s])for s in old if s!=c['sheet_id'])
accounts,totals=parse(new[c['sheet_id']]);before,_=parse(old[c['sheet_id']]);assert len(accounts)==47 and set(accounts)==set(before)==set(c['account_ids'])
for p in plan['planned']:
 cs=accounts[p['id']];assert [val(cs[i])for i in [0,1,2]]==[p['name'],p['method'],p['default']]
 assert cs[0].get('note')==before[p['id']][0].get('note') and cs[0].get('userEnteredFormat')==before[p['id']][0].get('userEnteredFormat')
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
  assert num(cs[col])==Decimal(p[key]) and plan['collected_at']in cs[col].get('note','')
  assert 'USD'in str(cs[col].get('userEnteredFormat',{}))
 assert cs[3].get('userEnteredValue')==before[p['id']][3].get('userEnteredValue') and cs[3].get('note')==before[p['id']][3].get('note')
ledger=load(H/'pc1-pay-now-ledger.json');checks=load(P/'visual-verification.json');targetids=set(c['pay_now_account_ids']);assert targetids==set(ledger['accounts'])==set(checks['verified_account_ids'])==set(checks['accounts_list_checks'])
for aid,e in ledger['accounts'].items():
 cs=accounts[aid];ck=checks['accounts_list_checks'][aid];source=load(P/(aid+'-receipt.json'))
 assert num(cs[7])==Decimal(e['amount'])==Decimal(ck['balance_usd'])==Decimal(source['amount'])
 assert ck['row_account_id']==aid and ck['name']==val(cs[0]) and ck['valid_billing_list'] and ck['business_id']==c['business_id']
 assert e['read_at']==source['read_at'] and e['read_at']in cs[7]['note'] and e['source']=='accounts_list_current_balance' and e['source']in cs[7]['note'] and e['receipt']in cs[7]['note']
 assert str(P)in e['receipt']
card=load(H/'pc1-card-ledger.json')['accounts'];gaps=[];proved=0
for aid,cs in accounts.items():
 e=card.get(aid)
 if e and e.get('latest_card'):
  proof=e['latest_card'];assert num(cs[3])==Decimal(proof['amount']) and e['read_at']in cs[3].get('note','') and proof['method']in cs[3]['note'];proved+=1
 else:
  assert val(cs[3])is None
  gaps.append({'account_id':aid,'name':val(cs[0]),'method':val(cs[1]),'reason':'no_charge_located_historical'if e else 'no_historical_card_instrument_proof_collected','last_ui_read_at':e.get('read_at')if e else None})
inv=load(N/'receipt.json');invl=load(H/'september-invoice-ledger.json');assert invl==load(N/'invoice-collection.json');visible=0
for aid,cs in accounts.items():
 e=invl['by_account'].get(aid);pending=e and Decimal(e['due'])>0
 if pending:assert str(val(cs[4]))==e['invoice'];visible+=1
 else:assert val(cs[4])is None
 if e:assert num(cs[5])==Decimal(e['due'])
 elif val(cs[1])=='Linha de crédito':assert val(cs[5])==0
 else:assert val(cs[5])is None
assert visible==inv['visible_invoice_numbers'];assert sum((num(x[5])for x in accounts.values()),Decimal(0))==Decimal(inv['tab_due_usd'])
subtotal_checks=[]
assert len(totals)==3
for cs in totals:
 label=val(cs[0]);subset=[x for x in accounts.values()if label.startswith('TOTAL GERAL')or('CARTÃO'in label and val(x[1])=='Cartão de crédito')or('LINHA'in label and val(x[1])=='Linha de crédito')]
 for col in [5,6,7,8,9]:
  expected=sum((num(x[col])for x in subset),Decimal(0))
  if val(cs[col])is None:assert expected==0;continue
  formula=cs[col].get('userEnteredValue',{}).get('formulaValue');assert formula and formula.startswith('=ROUND(SUM(')and num(cs[col])==expected
  subtotal_checks.append({'label':label,'column':chr(65+col),'formula':formula,'value':str(expected)})
lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert lease['locked']is False
periods=[dict(p)for p in {tuple(sorted(x['average_period'].items()))for x in plan['planned']}];times=sorted(e['read_at']for e in ledger['accounts'].values())
out={'status':'updated_validated','verified_at':datetime.now().astimezone().isoformat(),'accounts':len(accounts),'groups':dict(Counter(val(x[1])for x in accounts.values())),'validated_metrics_at':plan['collected_at'],'run_dir':str(R),'pay_now_run_dir':str(P),'invoice_run_dir':str(N),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'d_ledger_to_live_sheet_exact':True,'h_source_to_live_sheet_and_note_exact':True,'fresh_h_account_ids':sorted(targetids),'fresh_h_count':len(targetids),'h_preserved_count':0,'pending_h_account_ids':[],'h_read_at_min':times[0],'h_read_at_max':times[-1],'h_sum_usd':str(sum((Decimal(e['amount'])for e in ledger['accounts'].values()),Decimal(0))),'pending_ui':[],'card_proofs_updated':0,'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':proved,'average_period':periods,'month_periods':[dict(p)for p in {tuple(sorted(x['month_period'].items()))for x in plan['planned']}],'current_day_partial':True,'totals_usd':{key:str(sum((Decimal(x[key])for x in plan['planned']),Decimal(0)))for key in ['average_daily','balance','month_spend']},'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':visible,'invoice_period':inv['invoice_period'],'invoice_outside_scope':inv['outside_accounts'],'totals_validated_columns':['F','G','H','I','J'],'subtotal_checks':subtotal_checks,'lease_free':True,'pc1_blocker':None,'payments_executed':0,'meta_writes':0,'cron_changes':0,'workbook_sheet_count':len(new),'other_sheet_properties_unchanged':True,'other_sheet_data_unchanged':other_unchanged,'closure_receipt':str(B/'closure-current.json'),'report_infra_status':'pending'}
save(B/'closure-current.json',out)
print(json.dumps({k:out[k]for k in ['status','accounts','groups','validated_metrics_at','fresh_h_count','h_read_at_min','h_read_at_max','h_sum_usd','historical_d_blank_count','historical_d_verified_values','average_period','totals_usd','invoice_due_usd','visible_invoice_numbers','invoice_period','lease_free','other_sheet_data_unchanged','closure_receipt']},ensure_ascii=False))
