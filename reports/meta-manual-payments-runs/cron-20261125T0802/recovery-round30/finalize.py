"""Seal local diagnostic evidence; no business, queue or scheduler writes."""
import json, os, sqlite3, fcntl, hashlib, subprocess
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
B = Path(__file__).parent
ROOT = Path('/root/mgs-agent')
rec = json.loads((B/'reconciliation.json').read_text())
probe = json.loads((B/'probe-receipt.json').read_text())
authority = json.loads((B/'authority-readback.json').read_text())
lease = json.loads((B/'lease-release.json').read_text())
cp = ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json'
c = json.loads(cp.read_text())
lp = ROOT/'data/meta-manual-payments/pc1-card-ledger.json'
ledger = json.loads(lp.read_text())['accounts']
jobs = json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())
j = next(x for x in (jobs if isinstance(jobs,list) else jobs['jobs']) if x['id']=='2ee720363d7d')
q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
row = dict(q.execute('select * from requests where key=?',('79cd082a20c22a736307765f',)).fetchone())
hb = json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
os.kill(int(row['owner'].split(':')[1]),0)
workers = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name)==os.getpid(): continue
    try: argv = (p/'cmdline').read_bytes().decode(errors='replace').split('\x00')
    except OSError: continue
    for arg in argv:
        if Path(arg).name in ['refresh_workbook.py','regroup_funding.py','refresh_september_invoices.py','record_pc1_proof.py','read_pc1_billing_history.py','read_pc1_accounts_list.py','publish_pay_now.py']:
            workers.append({'pid':int(p.name),'worker':Path(arg).name}); break
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fcntl.flock(f,fcntl.LOCK_UN)
cron = subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True)
consumers = [x for x in cron.stdout.splitlines() if not x.lstrip().startswith('#') and 'alerts-infra-failed-alert-resolver' in x]
assert consumers
pending = c['pending_new_account_fields']['D_account_ids']
assert pending==rec['pending_account_ids'] and set(pending)<=set(c['account_ids'])
assert not any(ledger.get(k) for k in pending)
assert lease['release_exit']==0 and not lease['readback']['locked']
assert probe['save_dialog_count']==1 and probe['input_actions']==0
assert not workers and not j.get('fire_claim')
assert j['last_dispatch']['scheduled_at']==rec['last_dispatch_scheduled_at']
now = datetime.now(timezone.utc).isoformat()
final = {'observed_at':now,'job_id':j['id'],'job_enabled':j['enabled'],'job_state':j['state'],'fire_claim':j.get('fire_claim'),'last_dispatch_scheduled_at':j['last_dispatch']['scheduled_at'],'next_run_at':j['next_run_at'],'later_native_tick_observed':False,'writer_lock_free':True,'financial_workers':workers,'pending_D':pending,'pending_H':c['pending_new_account_fields']['H_account_ids'],'ledger_entries_present':[],'queue':{k:row[k] for k in ['state','owner','attempts','failures','due','lease_until']},'queue_owner_alive':True,'consumer_heartbeat':hb,'consumer_schedule':' '.join(consumers[0].split()[:5]),'contract_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'ledger_sha256':hashlib.sha256(lp.read_bytes()).hexdigest()}
evidence = {'operation_key':'79cd082a20c22a736307765f','source_key':'native:zeus:2ee720363d7d:20261125T0802:historical-d','mode':'resume_safe','status':'waiting_resource','cause':'pc1_save_as_dialog_still_open_preserved','observed_at':now,'authority':{'receipt':'authority-readback.json','original_context_receipt':'original-command-context.json','original_command_message_id':'1563960055504838767','current_scope_message_id':'1575022093777637377','recovery_authority_message_id':'1569193434189668453','all_authority_gets_http_200':all(x['status']==200 for x in authority['messages']),'current_registry_authorized':authority['current_registry_rodolfo_authorized']},'reconciliation':{'receipt':'reconciliation.json','final_readback':'final-state.json','native_contract_hash':rec['native_contract_hash'],'later_native_tick_observed':False,'writer_lock_free':True,'financial_worker_processes_found':workers,'pending_ledger_entries_present':[],'live_sheet_revalidation_performed':False,'completed_financial_layers_replayed':False},'scope':{'sheet_id':c['sheet_id'],'mode':c['recurring_scope']['mode'],'active_account_count':len(c['account_ids']),'pending_stage':'Historical D explicit card instrument proof only','pending_account_ids':pending,'pending_H_account_ids':final['pending_H'],'all_pending_ids_in_active_scope':True,'archived_accounts_excluded':True,'balance_views_enabled':c['balance_views']['enabled']},'surface':{'receipt':'probe-receipt.json','approved_chrome':{k:probe['captures']['approved'][k] for k in ['pid','window_id']},'approved_active_page_pixels':"What's new in AdBlock; Meta Business Suite tab inactive",'save_as_dialog_confirmed_in_pixels':True,'unrelated_dialog_preserved':True,'meta_authentication_challenge_demonstrated':False,'meta_access_revalidated':False,'auth_ready_claimed':False,'vision_inspected_images':['approved.png','save-dialog-0.png'],'input_actions':0,'tabs_created':0,'tabs_closed':0,'lease_acquired_then_released':True,'lease_release_exit':lease['release_exit'],'lease_free_readback':True,'lease_receipt':'lease-release.json'},'continuity':{'queue_owner':row['owner'],'queue_owner_alive_at_final_verification':True,'queue_state_at_final_verification':row['state'],'attempts':row['attempts'],'failures':row['failures'],'consumer_heartbeat':hb,'consumer_cron_verified':final['consumer_schedule'],'retry_at':None,'retry_scheduling_owner':'Existing active supervisor consumes this response and applies resource backoff. Worker did not mutate queue or dispatch.','next_step':'Before next retry reconcile possible 14:02 native tick, claim, workers, writes, authority and ledgers. Reacquire lease only when PC1 available and inspect live windows. Resume only still-missing historical D for these five active IDs using actual pixels and narrow canonical record_pc1_proof, then exact pending-fields readback. Preserve unrelated Save As dialog and original tabs. No completed-layer replay, old hardcoded adapter or duplicate financial delivery.'},'side_effects':{'sheet_writes':0,'meta_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'delivery_messages':0,'infrastructure_modified':False,'local_diagnostic_artifacts_only':True},'business_complete':False,'delivery_complete':False,'independent_closure_not_claimed':True}
for name,data in [('final-state.json',final),('recovery-evidence.json',evidence)]:
    with (B/name).open('x') as f: json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'checkpoint':str(B/'recovery-evidence.json'),'status':'waiting_resource','queue_owner':row['owner'],'attempts':row['attempts'],'pending_ids':pending,'next_native_tick':j['next_run_at'],'lease_free_readback':True}))
