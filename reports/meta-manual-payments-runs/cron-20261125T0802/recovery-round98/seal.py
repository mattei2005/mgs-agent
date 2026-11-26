"""Seal actual round-98 reads; no business or queue state mutation."""
import os,json,hashlib,sqlite3,subprocess,fcntl
from pathlib import Path
from datetime import datetime,timezone,timedelta
os.umask(0o077)
B=Path(__file__).parent
ROOT=Path('/root/mgs-agent')
KEY='79cd082a20c22a736307765f'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,d):
    with (B/n).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
rec=load(B/'reconciliation.json')
probe=load(B/'retry-probe-receipt.json')
auth=load(B/'authority-readback.json')
cpath=ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json'
c=load(cpath)
assert sha(cpath)==rec['contract_sha256']
assert all(m['status']==200 for m in auth['messages']) and auth['current_registry_rodolfo_authorized']
pending=[i for i in rec['source']['pending_account_ids'] if i in c['pending_new_account_fields']['D_account_ids']]
assert pending==rec['pending_account_ids']
assert set(c['pending_new_account_fields']['D_account_ids'])-set(pending)=={'1770569568407466'}
ledger=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
assert not any(ledger.get(i) for i in pending)
assert probe['save_dialog_count']==1 and probe['input_actions']==0 and not probe['errors']
assert not load(B/'retry-lease-release.json')['readback']['locked']
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True)
q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone())
assert row['state']=='running' and row['owner']==rec['queue']['owner']
os.kill(int(row['owner'].split(':')[1]),0)
assert json.loads(row['source'])==rec['source']
related=dict(q.execute('select key,state,owner,due,attempts,failures from requests where key=?',('6373afb33275674610c06b6a',)).fetchone())
assert related['state']=='waiting_human' and related['owner'] is None
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
assert q.execute("select value from service where key='enabled'").fetchone()[0]=='true'
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fcntl.flock(f,fcntl.LOCK_UN)
lease=json.loads(subprocess.run(['python3',str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout)
assert not lease['locked']
def tabs(p):return [e['label'].split(' - Memory usage')[0] for e in load(p).get('elements',[]) if e.get('role')=='TabItem' and e.get('bounds',[0,99999])[1]<50]
current=tabs(B/'approved-retry-elements.json')
assert current==tabs(B.parent/'recovery-round97/approved-retry-elements.json') and len(current)==6
assert any(e.get('role')=='Button' and e.get('label')=='Rodolfo' for e in load(B/'approved-retry-elements.json').get('elements',[]))
jobs=load('/root/.hermes/profiles/zeus/cron/jobs.json')
j=next(x for x in (jobs if isinstance(jobs,list) else jobs['jobs']) if x['id']==rec['source']['job_id'])
assert j['enabled'] and not j.get('fire_claim') and j['last_dispatch']['scheduled_at']==rec['last_dispatch_scheduled_at']
workers=[]
names={'read_pc1_billing_history.py','read_pc1_history_uia.py','read-transaction-history.py','refresh_workbook.py','record_pc1_proof.py','publish_pay_now.py','read_pc1_accounts_list.py','regroup_funding.py','refresh_september_invoices.py'}
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name)==os.getpid():continue
    try:args=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
    except OSError:continue
    if any(Path(a).name in names for a in args):workers.append(int(p.name))
assert not workers
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout
consumer=[s for s in cron.splitlines() if not s.lstrip().startswith('#') and 'alerts-infra-failed-alert-resolver' in s]
assert len(consumer)==1
schedule=' '.join(consumer[0].split()[:5])
assert schedule=='2-57/5 * * * *'
now=datetime.now(timezone.utc)
next_tick=now.replace(second=0,microsecond=0)+timedelta(minutes=1)
while next_tick.minute not in range(2,58,5):next_tick+=timedelta(minutes=1)
visual={'inspected_with':'vision_analyze','save_as_dialog_confirmed_in_pixels':True,'dialog_preserved':True,'approved_accounts_access_confirmed':True,'business_id':'155263197283282','profile_Rodolfo_confirmed_in_AX':True,'profile_name_not_visible_in_pixels':True,'meta_authentication_challenge_demonstrated':False,'historical_paid_card_table_visible':False,'original_tabs_count':len(current),'original_tabs_preserved':True,'captures':probe['captures']}
save('visual-verification.json',visual)
final={'observed_at':now.isoformat(),'queue':{k:row[k] for k in ['state','owner','attempts','failures','due','lease_until']},'queue_owner_alive':True,'consumer_heartbeat':hb,'consumer_schedule':schedule,'next_consumer_scheduled_check_utc':next_tick.isoformat(),'next_native_run_at':j['next_run_at'],'fire_claim':j.get('fire_claim'),'writer_lock_free':True,'financial_worker_processes':workers,'lease':lease,'pending_account_ids':pending,'canonical_pending_new_account_fields':c['pending_new_account_fields'],'related_occurrence':related,'original_tabs_preserved':True,'contract_sha256_unchanged':True}
save('final-state.json',final)
evidence={'operation_key':KEY,'source_key':row['source_key'],'mode':'resume_safe','status':'waiting_resource','cause':'pc1_save_as_dialog_present_preserved','observed_at':now.isoformat(),'authority_receipt':str(B/'authority-readback.json'),'reconciliation_receipt':str(B/'reconciliation.json'),'sheet_readback':str(B/'sheet-readback.json'),'final_readback':str(B/'final-state.json'),'native_contract_hash':rec['source']['contract_hash'],'scope':{'sheet_id':c['sheet_id'],'active_account_count':len(c['account_ids']),'exact_live_ids_verified':True,'pending_stage':'D historical explicit Paid card instrument proofs ONLY','pending_account_ids':pending,'new_account_D_separate_not_adopted':'1770569568407466','archived_accounts_excluded':True},'visual_readback':visual,'capture_diagnostic':{'capture_errors_this_round':probe['errors'],'capture_responses_saved_before_error_checks':True,'local_sql_probe_error':'Initial read-only query used nonexistent operation_key column; schema inspected, corrected to key, same request successfully read. No database write.'},'continuity':{'state':row['state'],'queue_owner':row['owner'],'owner_alive':True,'attempts':row['attempts'],'failures':row['failures'],'consumer_heartbeat':hb,'consumer_schedule':schedule,'next_consumer_scheduled_check_utc':next_tick.isoformat(),'retry_at':None,'retry_scheduling_owner':'Existing supervisor consumes this diagnostic and applies resource backoff; no queue mutation by worker. Scheduled consumer check is not a guaranteed retry time.','next_step':'Reacquire lease; revalidate windows. Preserve human Save As dialog. When desktop is available, collect only five original D proofs in small persisted batches; canonical record_pc1_proof only after pixel verification, reconcile pending fields/readback. Preserve new-account D separately and later waiting_human occurrence. No metrics/funding/invoices/H replay or duplicate delivery.'},'side_effects':{'input_actions':0,'tabs_created':0,'tabs_closed':0,'sheet_writes':0,'meta_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'business_delivery_messages':0,'canonical_infrastructure_modified':False,'local_diagnostic_artifacts_only':True},'lease_free_readback':True,'business_complete':False,'delivery_complete':False,'independent_closure_not_claimed':True}
save('recovery-evidence.json',evidence)
manifest={str(p):sha(p) for p in B.iterdir() if p.is_file() and p.suffix in ['.json','.png','.py'] and p.name!='evidence-sha256.json'}
save('evidence-sha256.json',manifest)
assert all(sha(p)==h for p,h in load(B/'evidence-sha256.json').items())
assert load(B/'recovery-evidence.json')['scope']['pending_account_ids']==pending
print(json.dumps({'checkpoint':str(B/'recovery-evidence.json'),'status':'waiting_resource','pending_ids':pending,'live_ids_exact_verified':len(c['account_ids']),'supervisor':row['owner'],'supervisor_alive':True,'lease_free':True,'hash_readback_valid':True,'original_tabs_preserved':True,'business_writes':0,'consumer_schedule':schedule,'next_consumer_scheduled_check_utc':next_tick.isoformat()}))
