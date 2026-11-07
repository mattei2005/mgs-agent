import json,sys,re,subprocess,shutil
from pathlib import Path
from datetime import datetime,date,timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal
from collections import Counter
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R));from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments')
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2));p.chmod(0o600)
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),None)
def money(c):return Decimal(str(c.get('effectiveValue',{}).get('numberValue',0)))
def authored(s):
 out={k:v for k,v in s.items()if k!='data'};out['data']=[]
 for gr in s.get('data',[]):
  rs=[]
  for row in gr.get('rowData',[]):
   cs=[{k:v for k,v in x.items()if k in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']}for x in row.get('values',[])]
   while cs and not cs[-1]:cs.pop()
   rs.append({'values':cs}if cs else{})
  while rs and not rs[-1]:rs.pop()
  out['data'].append({'rowData':rs})
 return out
c=load(H/'digital-trust-workbook-contract.json');ph=load(B/'phases.json');R=Path(ph['refresh_workbook']['run_dir']);P=Path(ph['publish_pay_now']['run_dir']);N=Path(ph['refresh_september_invoices']['run_dir']);plan=load(R/'plan.json')
g.load_env();t=g.service_account_access_token();status,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save(B/'final-workbook-readback.json',book)
old={s['properties']['sheetId']:s for s in load(B/'baseline.json')['sheets']};new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)and all(old[k]['properties']==new[k]['properties']for k in old)
other=all(authored(old[k])==authored(new[k])for k in old if k!=c['sheet_id'])
def extract(sh):
 acc={};tot=[]
 for r in sh['data'][0]['rowData']:
  cs=r.get('values',[]);cs=cs+[{}]*max(0,10-len(cs));m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))
  if m:assert m[1]not in acc;acc[m[1]]=cs
  elif str(val(cs[0])).startswith('TOTAL'):tot.append(cs)
 return acc,tot
acc,tots=extract(new[c['sheet_id']]);prev,_=extract(old[c['sheet_id']]);assert len(acc)==47 and set(acc)==set(c['account_ids'])=={p['id']for p in plan['planned']}
for p in plan['planned']:
 cs=acc[p['id']];assert [val(cs[i])for i in [0,1,2]]==[p['name'],p['method'],p['default']]
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert money(cs[col])==Decimal(p[key])and plan['collected_at']in cs[col]['note']and 'USD'in str(cs[col]['userEnteredFormat'])
 local=datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(p['timezone'])).date();assert p['month_period']=={'since':c['month_since'],'until':min(local,date.fromisoformat(c['month_until'])).isoformat()};assert p['average_period']=={'since':(local-timedelta(days=3)).isoformat(),'until':(local-timedelta(days=1)).isoformat()}
 renewed={x['account_id'] for x in ph['initial_refresh_workbook']['pending_ui']}
 if p['id'] not in renewed:assert cs[3].get('userEnteredValue')==prev[p['id']][3].get('userEnteredValue')and cs[3].get('note')==prev[p['id']][3].get('note')
ledger=load(H/'pc1-pay-now-ledger.json')['accounts'];targets={x['account_id']for x in load(P/'targets.json')};assert targets==set(ledger)==set(c['pay_now_account_ids']);assert {x.name.removesuffix('-receipt.json') for x in P.glob('*-receipt.json')}==targets;visual=load(P/'visual-verification.json');assert set(visual['verified_account_ids'])==targets
for aid,e in ledger.items():assert money(acc[aid][7])==Decimal(e['amount'])and e['read_at']in acc[aid][7]['note']and e['source']in acc[aid][7]['note']
card=load(H/'pc1-card-ledger.json')['accounts'];gaps=[]
for aid,cs in acc.items():
 e=card.get(aid)
 if e and e.get('latest_card'):
  p=e['latest_card'];assert money(cs[3])==Decimal(p['amount'])and e['read_at']in cs[3]['note']and p['method']in cs[3]['note']
 else:
  assert val(cs[3])is None;gaps.append({'account_id':aid,'name':val(cs[0]),'reason':'no_charge_located_historical'if e else'no_historical_card_instrument_proof_collected'})
inv=load(N/'receipt.json');il=load(N/'invoice-collection.json');assert il==load(H/'september-invoice-ledger.json');visible=0
for aid,cs in acc.items():
 e=il['by_account'].get(aid)
 if e and Decimal(e['due'])>0:assert str(val(cs[4]))==e['invoice'];visible+=1
 else:assert val(cs[4])is None
 if e:assert money(cs[5])==Decimal(e['due'])
 elif val(cs[1])=='Linha de crédito':assert val(cs[5])==0
 else:assert val(cs[5])is None
assert visible==inv['visible_invoice_numbers']and sum((money(x[5])for x in acc.values()),Decimal(0))==Decimal(inv['tab_due_usd']);checks=[];assert len(tots)==3
for cs in tots:
 label=val(cs[0]);subset=[x for x in acc.values()if label.startswith('TOTAL GERAL')or('CARTÃO'in label and val(x[1])=='Cartão de crédito')or('LINHA'in label and val(x[1])=='Linha de crédito')]
 for col in [5,6,7,8,9]:
  expected=sum((money(x[col])for x in subset),Decimal(0))
  if val(cs[col])is None:assert expected==0;continue
  f=cs[col]['userEnteredValue'].get('formulaValue');assert f and f.startswith('=ROUND(SUM(')and money(cs[col])==expected;checks.append({'label':label,'column':chr(65+col),'formula':f,'value':str(expected)})
lease= json.loads(subprocess.check_output([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],text=True));assert not lease['locked'];times=sorted(e['read_at']for e in ledger.values())
out={'status':'partial_updated_validated_pc1_reauthentication_required','verified_at':datetime.now().astimezone().isoformat(),'accounts':47,'groups':dict(Counter(val(x[1])for x in acc.values())),'validated_metrics_at':plan['collected_at'],'run_dir':str(R),'pay_now_run_dir':str(P),'invoice_run_dir':str(N),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'d_ledger_to_live_sheet_exact':True,'h_source_to_live_sheet_and_note_exact':True,'fresh_h_account_ids':[],'fresh_h_count':0,'h_preserved_count':len(targets),'pending_h_account_ids':sorted(targets),'h_read_at_min':times[0],'h_read_at_max':times[-1],'h_sum_usd':str(sum((Decimal(e['amount'])for e in ledger.values()),Decimal(0))),'pending_ui':plan['pending_ui'],'card_proofs_updated':0,'renewed_card_proof_ids':[],'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':47-len(gaps),'average_period':[dict(x)for x in {tuple(sorted(p['average_period'].items()))for p in plan['planned']}],'month_periods':[dict(x)for x in {tuple(sorted(p['month_period'].items()))for p in plan['planned']}],'current_day_partial':True,'totals_usd':{key:str(sum((Decimal(p[key])for p in plan['planned']),Decimal(0)))for key in ['average_daily','balance','month_spend']},'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':visible,'invoice_period':inv['invoice_period'],'invoice_outside_scope':inv['outside_accounts'],'subtotal_checks':checks,'lease_free':True,'pc1_blocker':{'type':'facebook_twofactor_reauth','account':'Rodolfo Mattei','message':'Confirm it’s you with your authentication app','screenshot':str(P/'blocked.png'),'no_bypass_or_retry':True},'payments_executed':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'workbook_sheet_count':len(book['sheets']),'other_sheet_properties_unchanged':True,'other_sheet_data_unchanged':other,'ui_cleanup':{'initial_browser_tabs_visually_counted':6,'final_browser_tabs_visually_counted':6,'owned_tabs_closed':True,'lease_free':True,'final_screenshot':str(B/'surface-final.png')},'closure_receipt':str(B/'closure-current.json')}
assert not plan['pending_ui']
for aid in targets:
 e=ledger[aid];receipt=load(P/(aid+'-receipt.json'));check=visual['accounts_list_checks'][aid]
 assert e['read_at']==receipt['read_at'] and Decimal(e['amount'])==Decimal(receipt['amount'])==Decimal(check['balance_usd']) and e['source']=='accounts_list_current_balance'
 assert check['row_account_id']==aid and check['business_id']==c['business_id'] and check['name']==receipt['name'] and check['valid_billing_list']
for aid in renewed:
 e=card[aid];assert datetime.fromisoformat(e['read_at'])>datetime.fromisoformat(ph['initial_refresh_workbook']['snapshot_at'])
out.update(status='updated_validated_with_historical_card_gaps',fresh_h_account_ids=sorted(targets),fresh_h_count=len(targets),h_preserved_count=0,pending_h_account_ids=[],card_proofs_updated=len(renewed),renewed_card_proof_ids=sorted(renewed),pc1_blocker=None)
save(B/'closure-current.json',out);print(json.dumps({k:v for k,v in out.items()if k not in ['subtotal_checks','historical_d_gaps','pending_h_account_ids']},ensure_ascii=False))
