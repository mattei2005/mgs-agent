import os,sys,json,shutil,re,copy,subprocess
from pathlib import Path
from datetime import datetime
from decimal import Decimal
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');C=H/'digital-trust-workbook-contract.json';c=json.loads(C.read_text());before=json.loads((B/'workbook-before.json').read_text());plan=json.loads(Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261119T080617535852/plan.json').read_text());api=json.loads(Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261119T080617535852/receipt.json').read_text());invdir=Path('/root/mgs-agent/reports/meta-manual-payments-runs/september-20261119T080534391356');inv=json.loads((invdir/'invoice-collection.json').read_text());hledger=json.loads((H/'pc1-pay-now-ledger.json').read_text())
def save(p,d):
 p=Path(p);p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
g.load_env();t=g.service_account_access_token();status,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save(B/'final-workbook.json',after)
a={s['properties']['sheetId']:s for s in after['sheets']};b={s['properties']['sheetId']:s for s in before['sheets']};assert set(a)==set(b)
for sid in a:
 if sid!=c['sheet_id']:assert a[sid]==b[sid],'other_sheet_data_changed'
 assert a[sid]['properties']==b[sid]['properties'],'sheet_properties_changed'
def rows(sh):return sh['data'][0]['rowData']
def mapping(sh):
 out={}
 for r in rows(sh):
  cells=r.get('values',[])
  if cells and (m:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):assert m[1] not in out;out[m[1]]=cells
 return out
am=mapping(a[c['sheet_id']]);bm=mapping(b[c['sheet_id']]);assert set(am)==set(bm)==set(c['account_ids'])=={p['id'] for p in plan['planned']}
def uv(cell):return cell.get('userEnteredValue',{})
for p in plan['planned']:
 aid=p['id'];v=am[aid];old=bm[aid];assert uv(v[2])=={'stringValue':p['default']}
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
  assert Decimal(str(uv(v[col])['numberValue']))==Decimal(p[key]),'cgij_mismatch_'+aid
  assert plan['collected_at'] in v[col]['note']
 for col in [0,1,3,7]:assert v[col]==old[col],'preserved_cell_changed_'+aid+'_'+str(col)
 if aid in c['pay_now_account_ids']:
  h=hledger['accounts'][aid];assert Decimal(str(uv(v[7])['numberValue']))==Decimal(h['amount']);assert h['read_at'] in v[7].get('note','') and h['source'] in v[7].get('note','')
 iv=inv['by_account'].get(aid)
 if iv:
  expected=iv['invoice'] if Decimal(iv['due'])>0 and iv['status']!='Paid' else None
  assert uv(v[4]).get('stringValue')==expected
  assert Decimal(str(uv(v[5])['numberValue']))==Decimal(iv['due'])
 else:
  assert not uv(v[4])
  if p['method']=='Linha de crédito':assert uv(v[5])=={'numberValue':0}
  else:assert not uv(v[5])
assert json.loads((H/'september-invoice-ledger.json').read_text())==inv
lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
jd=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());j=next(x for x in (jd if isinstance(jd,list) else jd['jobs']) if x['id']==c['cron_job_id']);oldj=json.loads((B/'job-before.json').read_text());assert j['fire_claim']['by']==oldj['fire_claim']['by'];assert j['last_dispatch']==oldj['last_dispatch'];assert j['schedule']==oldj['schedule'] and j['timezone']==oldj['timezone'] and j['enabled'];assert datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
now=datetime.now().astimezone().isoformat();receipt={'status':'partial_validated_waiting_human_meta_passkey','scheduled_at':j['last_dispatch']['scheduled_at'],'updated_at':now,'evidence':str(B/'partial-receipt.json'),'business_refresh_complete':False,'accounts':len(am),'fresh_metrics_count':len(plan['planned']),'api_run_dir':str(Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261119T080617535852')),'api_collected_at':plan['collected_at'],'fresh_h_count':0,'preserved_h_count':len(c['pay_now_account_ids']),'h_run_dir':'/root/mgs-agent/reports/meta-manual-payments-runs/pay-now-20261119T080619770022','h_source':c['h_source'],'h_values_notes_original_times_preserved':True,'pending_ui':api['pending_ui'],'pending_h_account_ids':c['pay_now_account_ids'],'h_ledger_to_live_sheet_exact':True,'d_values_notes_preserved':True,'source_parity_cgij':True,'invoice_source_to_live_sheet_exact':True,'invoice_period':inv['invoice_period'],'invoice_due_usd':inv['tab_total_usd'],'other_sheet_data_unchanged':True,'other_sheets_count':len(a)-1,'authentication_observed':True,'authentication_evidence':'/root/mgs-agent/reports/meta-manual-payments-runs/pay-now-20261119T080619770022/blocked.png','lease_free':True,'groups':json.loads((B/'structural-validation.json').read_text())['groups'],'average_periods':sorted({(p['average_period']['since'],p['average_period']['until']) for p in plan['planned']}),'month_periods':sorted({(p['month_period']['since'],p['month_period']['until']) for p in plan['planned']}),'meta_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_cron_delivery_only_no_direct_send','delivery':'automatic_final_only_exact_authentication_notice','next_step':'Human Meta passkey authentication required in approved Chrome PC1; reconcile claim/writer and resume missing H40 and current pending D under same contract/job.'}
save(B/'partial-receipt.json',receipt);save(B/'contract-before-seal.json',c);c['latest_refresh_qualification']=receipt;c['pending_card_history']={'status':'blocked_meta_passkey','account_ids':[p['account_id'] for p in api['pending_ui']],'pending_ui':api['pending_ui'],'evidence':receipt['evidence']};save(C,c)
assert json.loads(C.read_text())['latest_refresh_qualification']==json.loads(json.dumps(receipt))
ip=Path('/root/mgs-agent/data/infra-inventory.json');inventory=json.loads(ip.read_text());key='meta-manual-payments-cron-20261119T0802';assert not any(x.get('id')==key for x in inventory.get('runtime_artifacts',[]));inventory.setdefault('runtime_artifacts',[]).append({'id':key,'type':'financial_refresh_receipt','agent':'zeus','status':receipt['status'],'evidence':receipt['evidence'],'updated_at':now,'report_infra_status':receipt['report_infra_status']});save(ip,inventory);assert sum(x.get('id')==key for x in json.loads(ip.read_text())['runtime_artifacts'])==1
with Path('/root/mgs-agent/logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'meta_manual_payments_refresh_partial','job_id':j['id'],'scheduled_at':receipt['scheduled_at'],'accounts':55,'h_fresh':0,'h_preserved':40,'pending_ui':len(api['pending_ui']),'blocker':'confirmed_meta_passkey','receipt':receipt['evidence'],'payments_executed':0,'billing_changes':0,'report_infra_status':receipt['report_infra_status']},ensure_ascii=False)+'\n')
print(json.dumps({'status':receipt['status'],'source_parity_cgij':True,'invoice_parity':True,'h_d_preserved':True,'other_sheets_unchanged':True,'lease_free':True,'pending_ui':len(api['pending_ui']),'next_run_at':j['next_run_at']}))
