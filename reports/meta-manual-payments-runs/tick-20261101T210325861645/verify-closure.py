#!/usr/bin/env python3
"""Bounded read-only acceptance for this financial tick; no external writes."""
import json,sys,re,os,subprocess
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from collections import Counter
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B=Path(__file__).parent
H=Path('/root/mgs-agent/data/meta-manual-payments')
P=Path('/root/mgs-agent/reports/meta-manual-payments-runs/pay-now-20261101T210410721266')
R=Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261101T213423238430')
N=Path('/root/mgs-agent/reports/meta-manual-payments-runs/september-20261101T210337047513')
def load(p):return json.loads(p.read_text())
def save(p,d):
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2));os.chmod(p,0o600)
def num(c):return Decimal(str(c.get('effectiveValue',{}).get('numberValue',c.get('userEnteredValue',{}).get('numberValue',0))))
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),None)
c=load(H/'digital-trust-workbook-contract.json');plan=load(R/'plan.json');receipt=load(R/'receipt.json');assert receipt['status']=='updated_metrics_pending_card_history' and {e['account_id'] for e in receipt['pending_ui']}=={'648687381127947','1414197490675732','2852476828464907'}
g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod'and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';token=g.service_account_access_token()
s,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',token,quota_project='mgs-core-prod');assert s==200
save(B/'final-workbook-readback.json',book)
baseline=load(B/'baseline-workbook.json');old={x['properties']['sheetId']:x for x in baseline['sheets']};new={x['properties']['sheetId']:x for x in book['sheets']};assert set(old)==set(new)
for sid in old:
 if sid!=c['sheet_id']:assert old[sid]==new[sid],'other_sheet_changed'
 else:assert old[sid]['properties']==new[sid]['properties'],'target_properties_changed'
rows=new[c['sheet_id']]['data'][0]['rowData'];accounts={};totals=[]
for i,row in enumerate(rows):
 cells=row.get('values',[])
 if not cells:continue
 cells=cells+[{}]*max(0,10-len(cells));m=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))
 if m:
  assert m[1]not in accounts;accounts[m[1]]=(i,cells)
 elif str(val(cells[0])).startswith('TOTAL'):totals.append(cells)
assert len(accounts)==47 and set(accounts)==set(c['account_ids'])
for p in plan['planned']:
 ri,cells=accounts[p['id']];assert val(cells[0])==p['name']and val(cells[1])==p['method']and val(cells[2])==p['default']
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
  assert num(cells[col])==Decimal(p[key]);assert plan['collected_at']in cells[col].get('note','')
ledger=load(H/'pc1-pay-now-ledger.json');checks=load(P/'visual-verification.json');targetids={x['account_id']for x in load(P/'targets.json')};assert set(checks['verified_account_ids'])==targetids==set(ledger['accounts'])==set(c['pay_now_account_ids'])
for aid,e in ledger['accounts'].items():
 cells=accounts[aid][1];assert num(cells[7])==Decimal(e['amount']);assert e['read_at']in cells[7]['note']and e['source']in cells[7]['note']and e['receipt']in cells[7]['note'];assert e['source']=='accounts_list_current_balance'and e['visual_account_verified'];assert checks['accounts_list_checks'][aid]['name']==val(cells[0])
card=load(H/'pc1-card-ledger.json')['accounts'];gaps=[];proved=0
for aid,(ri,cells)in accounts.items():
 e=card.get(aid)
 if e and e.get('latest_card'):
  proof=e['latest_card'];assert num(cells[3])==Decimal(proof['amount']);assert e['read_at']in cells[3].get('note','')and proof['method']in cells[3]['note'];proved+=1
 else:
  assert val(cells[3])is None
  gaps.append({'account_id':aid,'name':val(cells[0]),'method':val(cells[1]),'reason':'no_charge_located_historical'if e else'no_historical_card_instrument_proof_collected','last_ui_read_at':e.get('read_at')if e else None})
inv=load(N/'receipt.json');assert inv['visible_invoice_numbers']==0 and Decimal(inv['tab_due_usd'])==0
assert all(val(cells[4])is None for _,cells in accounts.values())
subtotal_checks=[]
for cells in totals:
 label=val(cells[0]);subset=[x[1]for x in accounts.values()if label.startswith('TOTAL GERAL')or('CARTÃO'in label and val(x[1][1])=='Cartão de crédito')or('LINHA'in label and val(x[1][1])=='Linha de crédito')]
 for col in [5,6,7,8,9]:
  if val(cells[col])is None:assert sum((num(x[col])for x in subset),Decimal(0))==0;continue
  formula=cells[col].get('userEnteredValue',{}).get('formulaValue');assert formula and formula.startswith('=ROUND(SUM(')
  expected=sum((num(x[col])for x in subset),Decimal(0));assert num(cells[col])==expected
  subtotal_checks.append({'label':label,'column':chr(65+col),'formula':formula,'value':str(expected)})
assert len(totals)==3
lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert lease['locked']is False
periods=[dict(p)for p in {tuple(sorted(x['average_period'].items()))for x in plan['planned']}]
times=sorted(e['read_at']for e in ledger['accounts'].values())
out={'status':'financial_metrics_validated_pending_d_history','verified_at':datetime.now().astimezone().isoformat(),'accounts':len(accounts),'groups':dict(Counter(val(cells[1])for _,cells in accounts.values())),'validated_metrics_at':plan['collected_at'],'run_dir':str(R),'pay_now_run_dir':str(P),'source_to_live_sheet_cgij_exact':True,'d_ledger_to_live_sheet_exact':True,'h_source_to_live_sheet_and_note_exact':True,'full_grid_narrow_write_readback':True,'fresh_h_account_ids':sorted(targetids),'fresh_h_count':len(targetids),'h_preserved_count':0,'pending_h_account_ids':[],'h_read_at_min':times[0],'h_read_at_max':times[-1],'h_sum_usd':str(sum((Decimal(x['amount'])for x in ledger['accounts'].values()),Decimal(0))),'pending_ui':receipt['pending_ui'],'card_proofs_updated':1,'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':proved,'average_period':periods,'totals_usd':{key:str(sum((Decimal(x[key])for x in plan['planned']),Decimal(0)))for key in ['average_daily','balance','month_spend']},'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':inv['visible_invoice_numbers'],'invoice_period':inv['invoice_period'],'totals_validated_columns':['F','G','H','I','J'],'subtotal_checks':subtotal_checks,'lease_free':True,'pc1_blocker':{'stage':'D_history','account_id':'648687381127947','reason':'billing_page_not_verified; screenshot New Tab with typed target URL; no provider/auth gate proven; UI stopped, no reload/alternate profile','evidence':'/root/.hermes/profiles/zeus/cache/images/computer_use_36aa04f3fb924b05b87d5a4d7cfd2efe.png'},'payments_executed':0,'meta_writes':0,'cron_changes':0,'workbook_sheet_count':len(new),'other_sheet_properties_unchanged':True,'other_sheet_data_unchanged':True,'other_sheet_data_preservation_qualification':'Full native grid baseline captured before first apply; unrelated tab identical at closure.','closure_receipt':str(B/'closure-current.json'),'report_infra_status':'pending_cron_delivery_restriction_no_manual_message'}
save(B/'closure-current.json',out)
print(json.dumps({k:out[k]for k in ['status','accounts','groups','fresh_h_count','h_sum_usd','historical_d_blank_count','historical_d_verified_values','average_period','totals_usd','invoice_period','lease_free','other_sheet_data_unchanged','closure_receipt']},ensure_ascii=False))
