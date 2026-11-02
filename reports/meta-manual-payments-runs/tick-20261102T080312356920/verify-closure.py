#!/usr/bin/env python3
"""Read-only final acceptance of the bounded 2026-11-02 08:02 financial tick."""
import json,sys,re,os,subprocess
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from collections import Counter
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B=Path(__file__).parent
H=Path('/root/mgs-agent/data/meta-manual-payments')
R=Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261102T080426237661')
P=Path('/root/mgs-agent/reports/meta-manual-payments-runs/pay-now-20261102T080428537840')
N=Path('/root/mgs-agent/reports/meta-manual-payments-runs/september-20261102T080358500974')
def load(p):return json.loads(p.read_text())
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),None)
def num(c):return Decimal(str(c.get('effectiveValue',{}).get('numberValue',c.get('userEnteredValue',{}).get('numberValue',0))))
def save(p,d):
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def parse(sheet):
 out={};totals=[]
 for row in sheet['data'][0]['rowData']:
  cells=row.get('values',[])
  if not cells:continue
  cells=cells+[{}]*max(0,10-len(cells));m=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))
  if m:
   assert m[1]not in out;out[m[1]]=cells
  elif str(val(cells[0])).startswith('TOTAL'):totals.append(cells)
 return out,totals
c=load(H/'digital-trust-workbook-contract.json');plan=load(R/'plan.json');receipt=load(R/'receipt.json');baseline=load(B/'workbook-before.json')
g.load_env();sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
t=g.service_account_access_token();s,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert s==200
save(B/'final-workbook-readback.json',book)
old={x['properties']['sheetId']:x for x in baseline['sheets']};new={x['properties']['sheetId']:x for x in book['sheets']};assert set(old)==set(new)
for sid in old:
 if sid!=c['sheet_id']:assert old[sid]==new[sid],'other_sheet_changed'
 else:assert old[sid]['properties']==new[sid]['properties'],'target_properties_changed'
accounts,totals=parse(new[c['sheet_id']]);before,_=parse(old[c['sheet_id']]);assert len(accounts)==47 and set(accounts)==set(c['account_ids'])==set(before)
for p in plan['planned']:
 cells=accounts[p['id']];assert val(cells[0])==p['name'] and val(cells[1])==p['method'] and val(cells[2])==p['default']
 assert cells[0].get('note')==before[p['id']][0].get('note') and cells[0].get('textFormatRuns')==before[p['id']][0].get('textFormatRuns')
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
  assert num(cells[col])==Decimal(p[key]) and plan['collected_at'] in cells[col].get('note','')
  assert 'USD' in str(cells[col].get('userEnteredFormat',{}))
for aid,cells in accounts.items():
 for col in [3,7]:
  for key in ['userEnteredValue','userEnteredFormat','note']:assert cells[col].get(key)==before[aid][col].get(key),'historical_DH_not_preserved'
ledger=load(H/'pc1-pay-now-ledger.json');targetids=set(c['pay_now_account_ids']);assert targetids==set(ledger['accounts'])
for aid,e in ledger['accounts'].items():
 cells=accounts[aid];assert num(cells[7])==Decimal(e['amount']) and e['read_at'] in cells[7]['note'] and e['source'] in cells[7]['note'] and e['receipt'] in cells[7]['note']
card=load(H/'pc1-card-ledger.json')['accounts'];gaps=[];proved=0
for aid,cells in accounts.items():
 e=card.get(aid)
 if e and e.get('latest_card'):
  proof=e['latest_card'];assert num(cells[3])==Decimal(proof['amount']) and e['read_at'] in cells[3].get('note','') and proof['method'] in cells[3]['note'];proved+=1
 else:
  assert val(cells[3])is None
  gaps.append({'account_id':aid,'name':val(cells[0]),'method':val(cells[1]),'reason':'no_charge_located_historical' if e else 'no_historical_card_instrument_proof_collected','last_ui_read_at':e.get('read_at')if e else None})
inv=load(N/'receipt.json');invl=load(H/'september-invoice-ledger.json');visible=0
for aid,cells in accounts.items():
 e=invl['by_account'].get(aid);pending=e and Decimal(e['due'])>0
 if pending:assert str(val(cells[4]))==e['invoice'];visible+=1
 else:assert val(cells[4])is None
 if e:assert num(cells[5])==Decimal(e['due'])
assert visible==inv['visible_invoice_numbers'];assert sum((num(x[5])for x in accounts.values()),Decimal(0))==Decimal(inv['tab_due_usd'])
checks=[]
for cells in totals:
 label=val(cells[0]);subset=[x for x in accounts.values()if label.startswith('TOTAL GERAL')or('CARTÃO'in label and val(x[1])=='Cartão de crédito')or('LINHA'in label and val(x[1])=='Linha de crédito')]
 for col in [5,6,7,8,9]:
  expected=sum((num(x[col])for x in subset),Decimal(0))
  if val(cells[col])is None:assert expected==0;continue
  formula=cells[col].get('userEnteredValue',{}).get('formulaValue');assert formula and formula.startswith('=ROUND(SUM(')and num(cells[col])==expected
  checks.append({'label':label,'column':chr(65+col),'formula':formula,'value':str(expected)})
assert len(totals)==3
lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert lease['locked']is False
periods=[dict(p)for p in {tuple(sorted(x['average_period'].items()))for x in plan['planned']}];times=sorted(e['read_at']for e in ledger['accounts'].values())
out={'status':'partial_metrics_validated_pc1_approved_chrome_unavailable','verified_at':datetime.now().astimezone().isoformat(),'accounts':len(accounts),'groups':dict(Counter(val(x[1])for x in accounts.values())),'validated_metrics_at':plan['collected_at'],'run_dir':str(R),'pay_now_run_dir':str(P),'source_to_live_sheet_cgij_exact':True,'d_ledger_to_live_sheet_exact':True,'h_historical_ledger_to_live_sheet_and_note_exact':True,'h_values_and_notes_preserved_exact':True,'full_grid_narrow_write_readback':True,'fresh_h_account_ids':[],'fresh_h_count':0,'h_preserved_count':len(targetids),'pending_h_account_ids':sorted(targetids),'historical_h_note_read_at_min':times[0],'historical_h_note_read_at_max':times[-1],'h_sum_usd':str(sum((Decimal(e['amount'])for e in ledger['accounts'].values()),Decimal(0))),'pending_ui':receipt['pending_ui'],'card_proofs_updated':0,'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':proved,'average_period':periods,'totals_usd':{key:str(sum((Decimal(x[key])for x in plan['planned']),Decimal(0)))for key in ['average_daily','balance','month_spend']},'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':inv['visible_invoice_numbers'],'invoice_period':inv['invoice_period'],'invoice_outside_scope':inv['outside_accounts'],'totals_validated_columns':['F','G','H','I','J'],'subtotal_checks':checks,'lease_free':True,'owned_tabs_created':0,'pc1_blocker':{'stage':'H_and_D','reason':'approved_chrome_not_live','details':'Fresh list_windows has no Chrome window; list_apps sees chrome.exe PID19372 only. Pixels show Logitech G HUB, not Meta. Cannot establish approved authenticated surface; no input/reload/alternate profile attempted. Not evidence of global Facebook logout.','evidence':str(P/'blocked.png')},'payments_executed':0,'meta_writes':0,'cron_changes':0,'workbook_sheet_count':len(new),'other_sheet_properties_unchanged':True,'other_sheet_data_unchanged':True,'closure_receipt':str(B/'closure-current.json'),'report_infra_status':'pending_cron_delivery_restriction_no_manual_message'}
save(B/'closure-current.json',out)
print(json.dumps({k:out[k]for k in ['status','accounts','groups','fresh_h_count','h_preserved_count','historical_h_note_read_at_min','historical_h_note_read_at_max','historical_d_blank_count','historical_d_verified_values','average_period','totals_usd','invoice_due_usd','visible_invoice_numbers','invoice_period','lease_free','other_sheet_data_unchanged','closure_receipt']},ensure_ascii=False))
