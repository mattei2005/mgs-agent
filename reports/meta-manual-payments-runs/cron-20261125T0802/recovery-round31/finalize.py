"""Seal read-only diagnostic checkpoint; leave queue transitions to supervisor."""
import json, os, sqlite3, fcntl, hashlib, subprocess
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
B=Path(__file__).parent; ROOT=Path('/root/mgs-agent')
def load(p): return json.loads(Path(p).read_text())
rec=load(B/'reconciliation.json'); probe=load(B/'probe-receipt.json'); lease=load(B/'lease-release.json'); authority=load(B/'authority-readback.json')
c=load(ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json')
ledger=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
jobs=load('/root/.hermes/profiles/zeus/cron/jobs.json'); j=next(x for x in (jobs if isinstance(jobs,list)else jobs['jobs'])if x['id']=='2ee720363d7d')
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',('79cd082a20c22a736307765f',)).fetchone())
os.kill(int(row['owner'].split(':')[1]),0)
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
workers=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit()or int(p.name)==os.getpid():continue
    try: argv=(p/'cmdline').read_bytes().decode(errors='replace').split('\x00')
    except OSError:continue
    for a in argv:
        if Path(a).name in ['refresh_workbook.py','regroup_funding.py','refresh_september_invoices.py','record_pc1_proof.py','read_pc1_billing_history.py','read_pc1_accounts_list.py','publish_pay_now.py']:
            workers.append({'pid':int(p.name),'worker':Path(a).name});break
with (ROOT/'data/meta-manual-payments/writer.lock').open('r')as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True)
consumers=[x for x in cron.stdout.splitlines()if not x.lstrip().startswith('#')and 'alerts-infra-failed-alert-resolver' in x];assert consumers
pending=c['pending_new_account_fields']['D_account_ids']
assert pending==rec['pending_account_ids']and set(pending)<=set(c['account_ids'])
assert not any(ledger.get(k)for k in pending)
assert lease['release_exit']==0 and not lease['readback']['locked']
assert probe['save_dialog_count']==1 and probe['input_actions']==0
assert not workers and not j.get('fire_claim')
assert j['last_dispatch']['scheduled_at']==rec['last_dispatch_scheduled_at']
assert all(x['status']==200 for x in authority['messages'])
now=datetime.now(timezone.utc).isoformat()
related=[dict(r)for r in q.execute('select key,state,owner,due,attempts,failures from requests where key=?',('ce11800d217d22dba6a58dcc',))]
final={'observed_at':now,'job_id':j['id'],'fire_claim':j.get('fire_claim'),'last_dispatch_scheduled_at':j['last_dispatch']['scheduled_at'],'next_run_at':j['next_run_at'],'later_native_tick_observed':True,'later_native_tick_receipt':rec['later_native_tick_receipt'],'writer_lock_free':True,'financial_workers':workers,'pending_D':pending,'pending_H_new_account_fields':c['pending_new_account_fields']['H_account_ids'],'ledger_entries_present':[],'queue':{k:row[k]for k in ['state','owner','attempts','failures','due','lease_until']},'queue_owner_alive':True,'consumer_heartbeat':hb,'consumer_schedule':' '.join(consumers[0].split()[:5]),'related_later_tick_queue':related}
evidence={'operation_key':'79cd082a20c22a736307765f','source_key':'native:zeus:2ee720363d7d:20261125T0802:historical-d','mode':'resume_safe','status':'waiting_resource','cause':'pc1_save_as_dialog_still_open_preserved','observed_at':now,'authority':{'receipt':'authority-readback.json','original_command_message_id':'1563960055504838767','original_context_message_id':'1563960022252392459','current_scope_message_id':'1575022093777637377','recovery_authority_message_id':'1569193434189668453','all_authority_gets_http_200':True,'current_registry_authorized':True},'reconciliation':{'receipt':'reconciliation.json','final_readback':'final-state.json','native_contract_hash':rec['native_contract_hash'],'later_native_tick_observed':True,'later_native_tick_slot':j['last_dispatch']['scheduled_at'],'later_native_tick_receipt':rec['later_native_tick_receipt'],'later_native_tick_status':rec['later_tick_status'],'later_tick_missing_layers_separate_request':rec['later_tick_missing_layers_not_adopted'],'later_tick_queue':related,'writer_lock_free':True,'financial_workers':workers,'pending_ledger_entries_present':[],'completed_financial_layers_replayed':False,'live_sheet_revalidation_performed':False,'local_diagnostic_error_recovered':'SQLite lookup initially used absent operation_key column; PRAGMA identified canonical key column. Corrected read-only query succeeded; no writes.'},'scope':{'sheet_id':c['sheet_id'],'mode':c['recurring_scope']['mode'],'active_account_count':len(c['account_ids']),'pending_stage':'Historical D explicit card instrument proof ONLY for five current active accounts','pending_account_ids':pending,'pending_H_new_account_fields':c['pending_new_account_fields']['H_account_ids'],'archived_accounts_excluded':True,'balance_views_enabled':c['balance_views']['enabled']},'surface':{'receipt':'probe-receipt.json','approved_chrome':{k:probe['captures']['approved'][k]for k in ['pid','window_id']},'approved_active_page_pixels':"What's new in AdBlock; Meta Business Suite tab inactive",'save_as_dialog_confirmed_in_pixels':True,'unrelated_dialog_preserved':True,'meta_authentication_challenge_demonstrated':False,'meta_access_revalidated':False,'auth_ready_claimed':False,'vision_inspected_images':['approved.png','save-dialog-0.png'],'input_actions':0,'tabs_created':0,'tabs_closed':0,'lease_acquired_then_released':True,'lease_free_readback':True,'lease_receipt':'lease-release.json'},'continuity':{'queue_owner':row['owner'],'queue_owner_alive_at_final_verification':True,'queue_state':row['state'],'attempts':row['attempts'],'failures':row['failures'],'consumer_heartbeat':hb,'consumer_cron_verified':final['consumer_schedule'],'retry_at':None,'retry_scheduling_owner':'Existing supervisor consumes this result and applies resource backoff; worker did not mutate queue or dispatch.','next_step':'Reconcile native claim and BOTH occurrence receipts before input. Reacquire lease only when PC1 is available; inspect same approved Chrome and native dialogs. Preserve unrelated Save As dialog and original tabs. Resume only still-missing historical D for the five IDs via actual pixels and narrow canonical record_pc1_proof plus exact pending-fields/readback. Later 14:02 H35/D2 remain owned by ce11800d217d22dba6a58dcc, not adopted here. Do not replay completed metrics/funding/invoices/H, use hardcoded old adapter or duplicate business delivery.'},'side_effects':{'sheet_writes':0,'meta_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'delivery_messages':0,'infrastructure_modified':False,'local_diagnostic_artifacts_only':True},'business_complete':False,'delivery_complete':False,'independent_closure_not_claimed':True}
for name,data in [('final-state.json',final),('recovery-evidence.json',evidence)]:
    with (B/name).open('x')as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in B.iterdir()if p.is_file()and p.name!='probe-private.log'}
with (B/'evidence-sha256.json').open('x')as f:json.dump(manifest,f,indent=2)
print(json.dumps({'checkpoint':str(B/'recovery-evidence.json'),'status':evidence['status'],'pending_ids':pending,'later_native_tick_reconciled':True,'supervisor':row['owner'],'supervisor_alive':True,'lease_free_readback':True,'business_writes':0}))
