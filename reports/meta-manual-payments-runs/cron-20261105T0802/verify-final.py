"""Read-only final acceptance: fresh API/invoices; PC1 blocked, no H writes."""
import json,sys,re,subprocess
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from collections import Counter
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B=Path(__file__).parent
H=Path('/root/mgs-agent/data/meta-manual-payments')
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def value(c):return next(iter(c.get('userEnteredValue',{}).values()),None)
def money(c):return Decimal(str(c.get('effectiveValue',{}).get('numberValue',c.get('userEnteredValue',{}).get('numberValue',0))))
def authored(sh):
 out={k:v for k,v in sh.items()if k!='data'};out['data']=[]
 for grid in sh.get('data',[]):
  rows=[]
  for row in grid.get('rowData',[]):
   cs=[{k:v for k,v in x.items()if k in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']}for x in row.get('values',[])]
   while cs and not cs[-1]:cs.pop()
   rows.append({'values':cs}if cs else {})
  while rows and not rows[-1]:rows.pop()
  out['data'].append({'rowData':rows})
 return out
c=load(H/'digital-trust-workbook-contract.json');ph=load(B/'phases.json');m=load(B/'final-metrics.json');R=Path(m['run_dir']);P=Path(ph['publish_pay_now']['run_dir']);N=Path(ph['refresh_september_invoices']['run_dir'])
plan=load(R/'plan.json');assert m['status']=='updated_metrics_pending_card_history'and m['pending_ui']==plan['pending_ui']
assert {x['account_id']for x in m['pending_ui']}=={'1481815942722118','1543098427832443'}
g.load_env();sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod'
t=g.service_account_access_token();status,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200
save(B/'final-workbook-readback.json',book);baseline=load(B/'baseline.json');old={s['properties']['sheetId']:s for s in baseline['sheets']};new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)
assert all(old[s]['properties']==new[s]['properties']for s in old)
other_unchanged=all(authored(old[s])==authored(new[s])for s in old if s!=c['sheet_id'])
def rows_by_id(sh):
 accounts={};totals=[]
 for row in sh.get('data',[{}])[0].get('rowData',[]):
  cs=row.get('values',[]);cs=cs+[{}]*max(0,10-len(cs));mt=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))
  if mt:assert mt[1]not in accounts;accounts[mt[1]]=cs
  elif str(value(cs[0])).startswith('TOTAL'):totals.append(cs)
 return accounts,totals
accounts,totals=rows_by_id(new[c['sheet_id']]);previous,_=rows_by_id(old[c['sheet_id']]);assert len(accounts)==47 and set(accounts)==set(c['account_ids'])=={x['id']for x in plan['planned']}
for p in plan['planned']:
 cs=accounts[p['id']];assert [value(cs[i])for i in [0,1,2]]==[p['name'],p['method'],p['default']]
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
  assert money(cs[col])==Decimal(p[key])and plan['collected_at']in cs[col].get('note','')
  assert 'USD'in str(cs[col].get('userEnteredFormat',{}))
 assert '2026-11-01'in cs[9]['note']and p['month_period']['until']<='2026-11-05'
ledger=load(H/'pc1-pay-now-ledger.json')['accounts'];targets={x['account_id']for x in load(P/'targets.json')}
assert len(targets)==36 and targets==set(ledger)==set(c['pay_now_account_ids'])
assert not list(P.glob('*-receipt.json'))and not list(P.glob('publication-receipt-*'))
for aid,e in ledger.items():
 receipt=load(Path(e['receipt']));cs=accounts[aid];assert receipt['account_id']==aid
 assert money(cs[7])==Decimal(e['amount'])==Decimal(receipt['amount'])
 assert e['read_at']==receipt['read_at']and e['read_at']in cs[7]['note']and e['source']=='accounts_list_current_balance'and e['source']in cs[7]['note']
 assert cs[7].get('userEnteredValue')==previous[aid][7].get('userEnteredValue')and cs[7].get('note')==previous[aid][7].get('note')
card=load(H/'pc1-card-ledger.json')['accounts'];gaps=[]
for aid,cs in accounts.items():
 assert cs[3].get('userEnteredValue')==previous[aid][3].get('userEnteredValue')and cs[3].get('note')==previous[aid][3].get('note')
 e=card.get(aid)
 if e and e.get('latest_card'):
  proof=e['latest_card'];assert money(cs[3])==Decimal(proof['amount'])and e['read_at']in cs[3].get('note','')and proof['method']in cs[3]['note']
 else:
  assert value(cs[3])is None;gaps.append({'account_id':aid,'name':value(cs[0]),'reason':'no_charge_located_historical'if e else'no_historical_card_instrument_proof_collected'})
inv=load(N/'receipt.json');invoices=load(N/'invoice-collection.json');assert invoices==load(H/'september-invoice-ledger.json');visible=0
for aid,cs in accounts.items():
 e=invoices['by_account'].get(aid)
 if e and Decimal(e['due'])>0:assert str(value(cs[4]))==e['invoice'];visible+=1
 else:assert value(cs[4])is None
 if e:assert money(cs[5])==Decimal(e['due'])
 elif value(cs[1])=='Linha de crédito':assert value(cs[5])==0
 else:assert value(cs[5])is None
assert visible==inv['visible_invoice_numbers']and sum((money(x[5])for x in accounts.values()),Decimal(0))==Decimal(inv['tab_due_usd'])
subtotal_checks=[];assert len(totals)==3
for cs in totals:
 label=value(cs[0]);subset=[x for x in accounts.values()if label.startswith('TOTAL GERAL')or('CARTÃO'in label and value(x[1])=='Cartão de crédito')or('LINHA'in label and value(x[1])=='Linha de crédito')]
 for col in [5,6,7,8,9]:
  expected=sum((money(x[col])for x in subset),Decimal(0))
  if value(cs[col])is None:assert expected==0;continue
  formula=cs[col].get('userEnteredValue',{}).get('formulaValue');assert formula and formula.startswith('=ROUND(SUM(')and money(cs[col])==expected
  subtotal_checks.append({'label':label,'column':chr(65+col),'formula':formula,'value':str(expected)})
lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
times=sorted(e['read_at']for e in ledger.values())
out={'status':'partial_updated_validated_pc1_auth_blocked','verified_at':datetime.now().astimezone().isoformat(),'accounts':47,'groups':dict(Counter(value(x[1])for x in accounts.values())),'validated_metrics_at':plan['collected_at'],'run_dir':str(R),'pay_now_run_dir':str(P),'invoice_run_dir':str(N),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'d_ledger_to_live_sheet_exact':True,'h_source_to_live_sheet_and_note_exact':True,'fresh_h_account_ids':[],'fresh_h_count':0,'h_preserved_count':len(targets),'pending_h_account_ids':sorted(targets),'h_read_at_min':times[0],'h_read_at_max':times[-1],'h_sum_usd':str(sum((Decimal(e['amount'])for e in ledger.values()),Decimal(0))),'pending_ui':m['pending_ui'],'card_proofs_updated':0,'renewed_card_proof_ids':[],'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':len(accounts)-len(gaps),'average_period':[dict(x)for x in {tuple(sorted(p['average_period'].items()))for p in plan['planned']}],'month_periods':[dict(x)for x in {tuple(sorted(p['month_period'].items()))for p in plan['planned']}],'current_day_partial':True,'totals_usd':{key:str(sum((Decimal(p[key])for p in plan['planned']),Decimal(0)))for key in ['average_daily','balance','month_spend']},'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':visible,'invoice_period':inv['invoice_period'],'invoice_outside_scope':inv['outside_accounts'],'subtotal_checks':subtotal_checks,'lease_free':True,'pc1_blocker':{'type':'meta_2fa_reauthentication','business_id':c['business_id'],'surface':'facebook.com/security/twofactor/reauth/','screenshot':str(P/'blocked.png'),'completed_h_reads':0,'requires_human_authentication':True,'owned_tab_closed':True},'payments_executed':0,'meta_writes':0,'workbook_sheet_count':len(new),'other_sheet_properties_unchanged':True,'other_sheet_data_unchanged':other_unchanged,'closure_receipt':str(B/'closure-current.json'),'report_infra_status':'pending'}
save(B/'closure-current.json',out)
print(json.dumps({k:out[k]for k in ['status','accounts','groups','validated_metrics_at','fresh_h_count','h_preserved_count','h_read_at_min','h_read_at_max','pending_ui','historical_d_blank_count','average_period','totals_usd','invoice_due_usd','visible_invoice_numbers','other_sheet_data_unchanged','lease_free']},ensure_ascii=False))
