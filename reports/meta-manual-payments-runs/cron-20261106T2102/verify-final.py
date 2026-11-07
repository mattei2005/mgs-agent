import json,sys,subprocess,re
from pathlib import Path
from datetime import datetime,date,timedelta
from decimal import Decimal
from collections import Counter
from zoneinfo import ZoneInfo
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments')
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),None)
def money(c):return Decimal(str(c.get('effectiveValue',{}).get('numberValue',c.get('userEnteredValue',{}).get('numberValue',0))))
def authored(sh):
 out={k:v for k,v in sh.items()if k!='data'};out['data']=[]
 for grid in sh.get('data',[]):
  rows=[]
  for row in grid.get('rowData',[]):
   cs=[{k:v for k,v in x.items()if k in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']}for x in row.get('values',[])]
   while cs and not cs[-1]:cs.pop()
   rows.append({'values':cs}if cs else{})
  while rows and not rows[-1]:rows.pop()
  out['data'].append({'rowData':rows})
 return out
c=load(H/'digital-trust-workbook-contract.json');ph=load(B/'phases.json');R=Path(ph['refresh_workbook']['run_dir']);P=Path(ph['publish_pay_now']['run_dir']);N=Path(ph['refresh_september_invoices']['run_dir']);plan=load(R/'plan.json');pending=ph['refresh_workbook']['pending_ui'];assert pending==plan['pending_ui']
g.load_env();sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod';t=g.service_account_access_token();status,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save(B/'final-workbook-readback.json',book)
old={s['properties']['sheetId']:s for s in load(B/'baseline.json')['sheets']};new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)and all(old[k]['properties']==new[k]['properties']for k in old)
other=all(authored(old[k])==authored(new[k])for k in old if k!=c['sheet_id'])
def extract(sh):
 acc={};tot=[]
 for row in sh['data'][0]['rowData']:
  cs=row.get('values',[]);cs=cs+[{}]*max(0,10-len(cs));m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))
  if m:assert m[1]not in acc;acc[m[1]]=cs
  elif str(val(cs[0])).startswith('TOTAL'):tot.append(cs)
 return acc,tot
accounts,totals=extract(new[c['sheet_id']]);previous,_=extract(old[c['sheet_id']]);assert len(accounts)==47 and set(accounts)==set(c['account_ids'])=={p['id']for p in plan['planned']}
for p in plan['planned']:
 cs=accounts[p['id']];assert [val(cs[i])for i in [0,1,2]]==[p['name'],p['method'],p['default']]
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert money(cs[col])==Decimal(p[key])and plan['collected_at']in cs[col]['note']and 'USD'in str(cs[col]['userEnteredFormat'])
 local=datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(p['timezone'])).date();assert p['month_period']=={'since':c['month_since'],'until':min(local,date.fromisoformat(c['month_until'])).isoformat()};assert p['average_period']=={'since':(local-timedelta(days=3)).isoformat(),'until':(local-timedelta(days=1)).isoformat()}
 for col in [3,7]:assert cs[col].get('userEnteredValue')==previous[p['id']][col].get('userEnteredValue')and cs[col].get('note')==previous[p['id']][col].get('note')
ledger=load(H/'pc1-pay-now-ledger.json')['accounts'];targets={x['account_id']for x in load(P/'targets.json')};assert targets==set(ledger)==set(c['pay_now_account_ids']);assert not list(P.glob('*-receipt.json'))
for aid,e in ledger.items():assert money(accounts[aid][7])==Decimal(e['amount'])and e['read_at']in accounts[aid][7]['note']and e['source']in accounts[aid][7]['note']
card=load(H/'pc1-card-ledger.json')['accounts'];gaps=[]
for aid,cs in accounts.items():
 e=card.get(aid)
 if e and e.get('latest_card'):
  p=e['latest_card'];assert money(cs[3])==Decimal(p['amount'])and e['read_at']in cs[3]['note']and p['method']in cs[3]['note']
 else:
  assert val(cs[3])is None;gaps.append({'account_id':aid,'name':val(cs[0]),'reason':'no_charge_located_historical'if e else'no_historical_card_instrument_proof_collected'})
inv=load(N/'receipt.json');il=load(N/'invoice-collection.json');assert il==load(H/'september-invoice-ledger.json');visible=0
for aid,cs in accounts.items():
 e=il['by_account'].get(aid)
 if e and Decimal(e['due'])>0:assert str(val(cs[4]))==e['invoice'];visible+=1
 else:assert val(cs[4])is None
 if e:assert money(cs[5])==Decimal(e['due'])
 elif val(cs[1])=='Linha de crédito':assert val(cs[5])==0
 else:assert val(cs[5])is None
assert visible==inv['visible_invoice_numbers']and sum((money(x[5])for x in accounts.values()),Decimal(0))==Decimal(inv['tab_due_usd']);checks=[];assert len(totals)==3
for cs in totals:
 label=val(cs[0]);subset=[x for x in accounts.values()if label.startswith('TOTAL GERAL')or('CARTÃO'in label and val(x[1])=='Cartão de crédito')or('LINHA'in label and val(x[1])=='Linha de crédito')]
 for col in [5,6,7,8,9]:
  expected=sum((money(x[col])for x in subset),Decimal(0))
  if val(cs[col])is None:assert expected==0;continue
  f=cs[col]['userEnteredValue'].get('formulaValue');assert f and f.startswith('=ROUND(SUM(')and money(cs[col])==expected;checks.append({'label':label,'column':chr(65+col),'formula':f,'value':str(expected)})
lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked'];times=sorted(e['read_at']for e in ledger.values())
out={'status':'partial_updated_validated_pc1_reauthentication_required','verified_at':datetime.now().astimezone().isoformat(),'accounts':47,'groups':dict(Counter(val(x[1])for x in accounts.values())),'validated_metrics_at':plan['collected_at'],'run_dir':str(R),'pay_now_run_dir':str(P),'invoice_run_dir':str(N),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'d_ledger_to_live_sheet_exact':True,'h_source_to_live_sheet_and_note_exact':True,'fresh_h_account_ids':[],'fresh_h_count':0,'h_preserved_count':len(targets),'pending_h_account_ids':sorted(targets),'h_read_at_min':times[0],'h_read_at_max':times[-1],'h_sum_usd':str(sum((Decimal(e['amount'])for e in ledger.values()),Decimal(0))),'pending_ui':pending,'card_proofs_updated':0,'renewed_card_proof_ids':[],'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':len(accounts)-len(gaps),'average_period':[dict(x)for x in {tuple(sorted(p['average_period'].items()))for p in plan['planned']}],'month_periods':[dict(x)for x in {tuple(sorted(p['month_period'].items()))for p in plan['planned']}],'current_day_partial':True,'totals_usd':{key:str(sum((Decimal(p[key])for p in plan['planned']),Decimal(0)))for key in ['average_daily','balance','month_spend']},'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':visible,'invoice_period':inv['invoice_period'],'invoice_outside_scope':inv['outside_accounts'],'subtotal_checks':checks,'lease_free':True,'pc1_blocker':{'type':'facebook_twofactor_reauth','account':'Rodolfo Mattei','message':'Confirm it’s you with your authentication app','screenshot':str(P/'blocked.png'),'no_bypass_or_retry':True},'payments_executed':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'workbook_sheet_count':len(book['sheets']),'other_sheet_properties_unchanged':True,'other_sheet_data_unchanged':other,'ui_cleanup':{'initial_browser_tabs_visually_counted':6,'final_browser_tabs_visually_counted':6,'owned_tabs_closed':True,'lease_free':True,'final_screenshot':str(B/'surface-final.png')},'closure_receipt':str(B/'closure-current.json')}
save(B/'closure-current.json',out);print(json.dumps({k:v for k,v in out.items()if k not in ['subtotal_checks','historical_d_gaps','pending_h_account_ids']},ensure_ascii=False))
