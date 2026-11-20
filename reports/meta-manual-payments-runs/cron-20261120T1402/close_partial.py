import os,sys,json,shutil,re,subprocess,fcntl,time
from pathlib import Path
from datetime import datetime
from decimal import Decimal
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
from mgs_automation_continuity import Queue,native_contract_hash
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');C=H/'digital-trust-workbook-contract.json'
c=json.loads(C.read_text());before=json.loads((B/'workbook-before.json').read_text())
def last_json(name):
 return [json.loads(s) for s in (B/name).read_text().splitlines() if s.startswith('{')][-1]
def save(path,data):
 p=Path(path);p.write_text(json.dumps(data,ensure_ascii=False,indent=2));p.chmod(0o600)
def uv(cell):return cell.get('userEnteredValue',{})
def mapping(sh):
 out={}
 for block in sh.get('data',[]):
  for row in block.get('rowData',[]):
   v=row.get('values',[])
   if v and (m:=re.search(r'^ID da conta: (\d+)\b',v[0].get('note',''))):
    assert m[1] not in out;out[m[1]]=v
 return out
api_dir=Path(last_json('api.log')['run_dir']);inv_dir=Path(last_json('invoices.log')['run_dir']);h_dir=Path(last_json('h_prepare.log')['run_dir'])
plan=json.loads((api_dir/'plan.json').read_text());api=json.loads((api_dir/'receipt.json').read_text());inv=json.loads((inv_dir/'invoice-collection.json').read_text());hledger=json.loads((H/'pc1-pay-now-ledger.json').read_text())
assert last_json('h-batch1.log')['reason']=='searched_row_not_ready_336562339356179'
probe=json.loads((B/'input-action-0.json').read_text());assert probe['code']=='foreground_unavailable' and probe['meta']['actual_foreground_window_id']==8258278
with (H/'writer.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 g.load_env();t=g.service_account_access_token();status,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save(B/'final-workbook.json',after)
 a={s['properties']['sheetId']:s for s in after['sheets']};b={s['properties']['sheetId']:s for s in before['sheets']};assert set(a)==set(b)
 other_unchanged=all(a[sid]==b[sid] for sid in a if sid!=c['sheet_id']);assert other_unchanged,'other_sheet_data_changed'
 for sid in a:assert a[sid]['properties']==b[sid]['properties'],'sheet_properties_changed'
 am=mapping(a[c['sheet_id']]);bm=mapping(b[c['sheet_id']]);assert set(am)==set(bm)==set(c['account_ids'])=={p['id'] for p in plan['planned']};assert len(am)==55
 blanks=[]
 for p in plan['planned']:
  aid=p['id'];v=am[aid];old=bm[aid];assert uv(v[2])=={'stringValue':p['default']}
  for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
   assert Decimal(str(uv(v[col])['numberValue']))==Decimal(p[key]),'cgij_mismatch_'+aid
   assert plan['collected_at'] in v[col]['note']
  for col in [0,1,3,7]:assert v[col]==old[col],'preserved_cell_changed_'+aid+'_'+str(col)
  if not uv(v[3]):blanks.append({'account_id':aid,'name':p.get('name'),'state':'historical_blank_preserved_not_zero'})
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
 now=datetime.now().astimezone().isoformat()
 receipt={'status':'partial_validated_blocked_pc1_foreground','scheduled_at':j['last_dispatch']['scheduled_at'],'updated_at':now,'evidence':str(B/'partial-receipt.json'),'business_refresh_complete':False,'accounts':len(am),'fresh_metrics_count':len(plan['planned']),'api_run_dir':str(api_dir),'api_collected_at':plan['collected_at'],'fresh_h_count':0,'preserved_h_count':len(c['pay_now_account_ids']),'h_run_dir':str(h_dir),'h_source':c['h_source'],'h_values_notes_original_times_preserved':True,'pending_ui':api['pending_ui'],'pending_h_account_ids':c['pay_now_account_ids'],'h_ledger_to_live_sheet_exact':True,'d_values_notes_preserved':True,'historical_d_blanks_all_authorized_ids':blanks,'source_parity_cgij':True,'invoice_source_to_live_sheet_exact':True,'invoice_period':inv['invoice_period'],'invoice_due_usd':inv['tab_total_usd'],'other_sheet_data_unchanged':other_unchanged,'other_sheets_count':len(a)-1,'authentication_observed':False,'blocker':'Windows refused foreground activation of exact Chrome hwnd983880; foreground remains AvastUI.exe hwnd8258278 pid23396. Canonical search remained empty. One fresh-bounds foreground diagnostic was refused before typing. No Meta/passkey/Windows authentication gate in inspected Accounts images. No further input attempted.','blocker_evidence':str(B/'input-action-0.json'),'browser_tab_exact_parity_established':False,'browser_tab_parity_qualification':'Complete initial AX preserved. Failed input routing does not prove ctrl+t/ctrl+w landed; no uncertain preexisting tab was closed.','lease_free':True,'groups':json.loads((B/'structural-validation.json').read_text())['groups'],'average_periods':sorted({(p['average_period']['since'],p['average_period']['until'])for p in plan['planned']}),'month_periods':sorted({(p['month_period']['since'],p['month_period']['until'])for p in plan['planned']}),'meta_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_cron_delivery_only_no_direct_send','delivery':'automatic_final_only_short_real_blocker','next_step':'Owner minimizes/resolves Avast window without disabling protection and leaves approved Rodolfo Chrome available. Zeus revalidates same surface, resumes H40/current pending D only with same contract/job; no duplicate writer or completed-phase replay.'}
 source_key='native:zeus:'+j['id']+':20261120T1402'
 q=Queue();source={'kind':'native','profile':'zeus','job_id':j['id'],'contract_hash':native_contract_hash(j),'thread_id':c['thread_id'],'scheduled_at':receipt['scheduled_at'],'resource':'pc1','session_id':os.environ['HERMES_SESSION_ID'],'financial_receipt':receipt['evidence'],'run_dir':str(B),'completed_layers':['funding','invoices','metrics','source_to_sheet_readback'],'pending_layers':['H40_Accounts_outstanding_balance','D8_new_generic_events_instrument','final_API_reconciliation_and_validation'],'pending_account_ids_H':c['pay_now_account_ids'],'pending_account_ids_D':[x['account_id']for x in api['pending_ui']],'pending_cause':'pc1_foreground_avast_interception','time_sensitive':False,'resume_policy':receipt['next_step']+' Human/foreground probe only until exact Chrome activation works; preserve native human/security gate and original slot. Final delivery is automatic from current cron; never repeat notice or claim business completion from scheduler success.'}
 row=q.enqueue(source_key,source,'pc1_foreground_avast_interception');assert not row['owner'];q.defer(row['key'],'waiting_human','pc1_foreground_avast_interception',delay=3600,observation='Bloqueado: Windows manteve Avast em primeiro plano e recusou ativação do Chrome. É necessária intervenção local sem desativar proteção; nenhuma autenticação Meta foi exigida. '+receipt['next_step'])
 qr=q.get(row['key']);assert qr['state']=='waiting_human'and qr['owner']is None;receipt['continuity_key']=qr['key'];receipt['continuity_source_key']=source_key;receipt['retry_probe_at']=datetime.fromtimestamp(qr['due']).astimezone().isoformat();heartbeat=json.loads(q.db.execute("select value from service where key='heartbeat'").fetchone()[0]);receipt['continuity_consumer_heartbeat']=heartbeat;assert time.time()-heartbeat['at']<900;q.close()
 save(B/'partial-receipt.json',receipt);save(B/'contract-before-seal.json',c);c['latest_refresh_qualification']=receipt;c['pending_card_history']={'status':'blocked_pc1_foreground','account_ids':[p['account_id']for p in api['pending_ui']],'pending_ui':api['pending_ui'],'evidence':receipt['evidence']};save(C,c);assert json.loads(C.read_text())['latest_refresh_qualification']==json.loads(json.dumps(receipt))
 ip=Path('/root/mgs-agent/data/infra-inventory.json');inventory=json.loads(ip.read_text());key='meta-manual-payments-cron-20261120T1402';assert not any(x.get('id')==key for x in inventory.get('runtime_artifacts',[]));inventory.setdefault('runtime_artifacts',[]).append({'id':key,'type':'financial_refresh_receipt','agent':'zeus','status':receipt['status'],'evidence':receipt['evidence'],'updated_at':now,'report_infra_status':receipt['report_infra_status']});save(ip,inventory);assert sum(x.get('id')==key for x in json.loads(ip.read_text())['runtime_artifacts'])==1
 with Path('/root/mgs-agent/logs/events-audit.jsonl').open('a')as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'meta_manual_payments_refresh_partial','job_id':j['id'],'scheduled_at':receipt['scheduled_at'],'accounts':55,'h_fresh':0,'h_preserved':40,'pending_ui':len(api['pending_ui']),'blocker':'pc1_foreground_avast_interception','receipt':receipt['evidence'],'continuity_key':qr['key'],'payments_executed':0,'billing_changes':0,'report_infra_status':receipt['report_infra_status']},ensure_ascii=False)+'\n')
 print(json.dumps({'status':receipt['status'],'source_parity_cgij':True,'invoice_parity':True,'h_d_preserved':True,'other_sheets_unchanged':other_unchanged,'lease_free':True,'pending_ui':len(api['pending_ui']),'historical_blank_count':len(blanks),'continuity_state':qr['state'],'retry_probe_at':receipt['retry_probe_at'],'next_run_at':j['next_run_at']}))
