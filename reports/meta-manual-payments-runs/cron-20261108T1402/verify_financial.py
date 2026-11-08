import sys,json,shutil,subprocess,re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from collections import Counter
launcher=shutil.which('hermes');assert launcher
R=Path(launcher).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2));p.chmod(0o600)
def value(c):return next(iter(c.get('userEnteredValue',{}).values()),None)
def money(c):return Decimal(str(c.get('effectiveValue',{}).get('numberValue',0)))
def authored(s):
 out={k:v for k,v in s.items()if k!='data'};out['data']=[]
 for gr in s.get('data',[]):
  rows=[]
  for row in gr.get('rowData',[]):
   cells=[{k:v for k,v in x.items()if k in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']}for x in row.get('values',[])]
   while cells and not cells[-1]:cells.pop()
   rows.append({'values':cells}if cells else{})
  while rows and not rows[-1]:rows.pop()
  out['data'].append({'rowData':rows})
 return out
c=load(H/'digital-trust-workbook-contract.json');ph=load(B/'phases.json');previous=load(B/'contract-before.json')['latest_refresh_qualification'];N=Path(ph['refresh_september_invoices']['run_dir']);P=Path(ph['publish_pay_now']['run_dir'])
assert ph['refresh_workbook']['status']=='blocked'and 'insights_daily_aggregate_mismatch' in ph['refresh_workbook']['error']
assert not list(P.glob('*-receipt.json'))and (P/'blocked.png').exists()
save(P/'visual-verification.json',{'verified_account_ids':[],'accounts_list_checks':{},'status':'blocked_before_first_accounts_row','reason':'facebook_twofactor_reauth','inspected_screenshot':str(P/'blocked.png')})
r=subprocess.run([sys.executable,str(S/'validate_workbook_readonly.py'),'--spreadsheet-id',c['spreadsheet_id'],'--sheet-id',str(c['sheet_id']),'--business-id',c['business_id']],capture_output=True,text=True,timeout=180)
(B/'validation-final.stdout').write_text(r.stdout);(B/'validation-final.stderr').write_text(r.stderr);assert r.returncode==0,r.stdout
print('Structural validator:',r.stdout,flush=True)
g.load_env();t=g.service_account_access_token();status,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save(B/'final-workbook-readback.json',book)
old={s['properties']['sheetId']:s for s in load(B/'baseline.json')['sheets']};new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)and all(old[k]['properties']==new[k]['properties']for k in old)
other=all(authored(old[k])==authored(new[k])for k in old if k!=c['sheet_id'])
def extract(sheet):
 accounts={};totals=[]
 for row in sheet['data'][0]['rowData']:
  cs=row.get('values',[]);cs=cs+[{}]*max(0,10-len(cs));m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))
  if m:assert m[1]not in accounts;accounts[m[1]]=cs
  elif str(value(cs[0])).startswith('TOTAL'):totals.append(cs)
 return accounts,totals
acc,tots=extract(new[c['sheet_id']]);prev,_=extract(old[c['sheet_id']]);assert len(acc)==47 and set(acc)==set(c['account_ids'])
for aid,cs in acc.items():
 for col in [0,1,2,3,6,7,8,9]:
  assert {k:v for k,v in cs[col].items()if k in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']}=={k:v for k,v in prev[aid][col].items()if k in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']},(aid,col)
plan=load(Path(previous['run_dir'])/'plan.json');assert {x['id']for x in plan['planned']}==set(acc)
for p in plan['planned']:
 cs=acc[p['id']];assert [value(cs[i])for i in [0,1,2]]==[p['name'],p['method'],p['default']]
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert money(cs[col])==Decimal(p[key])and plan['collected_at']in cs[col]['note']and 'USD'in str(cs[col]['userEnteredFormat'])
ledger=load(H/'pc1-pay-now-ledger.json')['accounts'];targets={x['account_id']for x in load(P/'targets.json')};assert targets==set(ledger)==set(c['pay_now_account_ids'])
for aid,e in ledger.items():assert money(acc[aid][7])==Decimal(e['amount'])and e['read_at']in acc[aid][7]['note']and e['source']in acc[aid][7]['note']
card=load(H/'pc1-card-ledger.json')['accounts'];gaps=[]
for aid,cs in acc.items():
 e=card.get(aid)
 if e and e.get('latest_card'):
  p=e['latest_card'];assert money(cs[3])==Decimal(p['amount'])and e['read_at']in cs[3]['note']and p['method']in cs[3]['note']
 else:
  assert value(cs[3])is None;gaps.append({'account_id':aid,'name':value(cs[0]),'reason':'no_charge_located_historical'if e else'no_historical_card_instrument_proof_collected'})
inv=load(N/'receipt.json');il=load(N/'invoice-collection.json');assert il==load(H/'september-invoice-ledger.json');visible=0
for aid,cs in acc.items():
 e=il['by_account'].get(aid)
 if e and Decimal(e['due'])>0:assert str(value(cs[4]))==e['invoice'];visible+=1
 else:assert value(cs[4])is None
 if e:assert money(cs[5])==Decimal(e['due'])
 elif value(cs[1])=='Linha de crédito':assert value(cs[5])==0
 else:assert value(cs[5])is None
assert visible==inv['visible_invoice_numbers']and sum((money(x[5])for x in acc.values()),Decimal(0))==Decimal(inv['tab_due_usd']);checks=[];assert len(tots)==3
for cs in tots:
 label=value(cs[0]);subset=[x for x in acc.values()if label.startswith('TOTAL GERAL')or('CARTÃO'in label and value(x[1])=='Cartão de crédito')or('LINHA'in label and value(x[1])=='Linha de crédito')]
 for col in [5,6,7,8,9]:
  expected=sum((money(x[col])for x in subset),Decimal(0))
  if value(cs[col])is None:assert expected==0;continue
  formula=cs[col]['userEnteredValue'].get('formulaValue');assert formula and formula.startswith('=ROUND(SUM(')and money(cs[col])==expected;checks.append({'label':label,'column':chr(65+col),'formula':formula,'value':str(expected)})
lease=json.loads(subprocess.check_output([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],text=True));assert not lease['locked']
diags=[load(p)for p in sorted(Path('/root/mgs-agent/reports/meta-manual-payments-runs').glob('insights-reconcile-20261108T14*.json'))];assert len(diags)==2 and all(x['account_id']=='7840111366055613'for x in diags)
diff=Decimal(diags[-1]['after_totals'][1])-Decimal(diags[-1]['after_totals'][0])
out={'status':'partial_invoices_validated_metrics_blocked_insights_and_pc1_2fa','verified_at':datetime.now().astimezone().isoformat(),'accounts':47,'groups':dict(Counter(value(x[1])for x in acc.values())),'fresh_metrics_count':0,'metrics_preserved_count':47,'validated_metrics_at':plan['collected_at'],'run_dir':previous['run_dir'],'failed_api_collection':ph['refresh_workbook'],'insights_blocker':{'account_id':'7840111366055613','name':'Yolokfx-US-SHEIN-EN-01-G002','month_daily':diags[-1]['after_totals'][0],'month_aggregate':diags[-1]['after_totals'][1],'difference_usd':str(diff),'bounded_rereads':2,'cause':'Provider returned inconsistent daily and aggregate Insights; internal provider cause unproven','writes_from_failed_collection':0},'source_to_live_sheet_cgij_exact':True,'metrics_source_is_previous_snapshot':True,'invoice_source_to_live_sheet_ef_exact':True,'d_ledger_to_live_sheet_exact':True,'h_source_to_live_sheet_and_note_exact':True,'fresh_h_account_ids':[],'fresh_h_count':0,'h_preserved_count':len(targets),'pending_h_account_ids':sorted(targets),'preserved_h_times':{aid:ledger[aid]['read_at']for aid in targets},'h_sum_usd':str(sum((Decimal(e['amount'])for e in ledger.values()),Decimal(0))),'pending_ui':previous['pending_ui'],'pending_ui_freshness':'previous_verified_collection_only; current API refresh blocked before complete pending enumeration','card_proofs_updated':0,'historical_d_gaps':gaps,'historical_d_blank_count':len(gaps),'historical_d_verified_values':47-len(gaps),'average_period':previous['average_period'],'month_periods':previous['month_periods'],'current_day_partial':True,'totals_usd':previous['totals_usd'],'invoice_due_usd':inv['tab_due_usd'],'visible_invoice_numbers':visible,'invoice_period':inv['invoice_period'],'invoice_outside_scope':inv['outside_accounts'],'invoice_run_dir':str(N),'pay_now_run_dir':str(P),'subtotal_checks':checks,'lease_free':True,'pc1_blocker':{'type':'facebook_twofactor_reauth','account':'Rodolfo Mattei','message':'Confirm it’s you with your authentication app','screenshot':str(P/'blocked.png'),'no_bypass_or_retry':True},'payments_executed':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'workbook_sheet_count':len(book['sheets']),'other_sheet_properties_unchanged':True,'other_sheet_data_unchanged':other,'ui_cleanup':{'initial_browser_tabs_visually_counted':8,'final_browser_tabs_visually_counted':8,'owned_tabs_closed':True,'lease_free':True,'final_screenshot':str(B/'surface-final.png')},'closure_receipt':str(B/'closure-current.json'),'report_infra_status':'pending'}
save(B/'closure-current.json',out);print(json.dumps({k:out[k]for k in ['status','accounts','groups','fresh_metrics_count','validated_metrics_at','fresh_h_count','h_preserved_count','historical_d_blank_count','invoice_due_usd','other_sheet_data_unchanged','lease_free','insights_blocker']},ensure_ascii=False))
