"""Seal actual round36 progress and current resource blocker; no business writes."""
import os,json,hashlib,sqlite3,fcntl,subprocess,shutil
from pathlib import Path
from datetime import datetime,timezone
os.umask(0o077)
B=Path(__file__).parent; A=B.parent/'recovery-round36'; ROOT=Path('/root/mgs-agent');KEY='79cd082a20c22a736307765f'
def load(p):return json.loads(Path(p).read_text())
def save(n,d):
 with (B/n).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
rec=load(B/'reconciliation.json'); probe=load(B/'probe-receipt.json'); auth=load(B/'authority-readback.json');rel=load(B/'lease-release.json')
cpath=ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json';c=load(cpath);ledger=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
pending=c['pending_new_account_fields']['D_account_ids'];assert pending==rec['pending_account_ids'] and not any(ledger.get(k) for k in pending)
assert hashlib.sha256(cpath.read_bytes()).hexdigest()==rec['contract_sha256']
assert all(m['status']==200 for m in auth['messages']) and auth['current_registry_rodolfo_authorized']
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone());os.kill(int(row['owner'].split(':')[1]),0)
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
jobs=load('/root/.hermes/profiles/zeus/cron/jobs.json');j=next(x for x in(jobs if isinstance(jobs,list)else jobs['jobs'])if x['id']=='2ee720363d7d');assert not j.get('fire_claim') and j['enabled']
workers=[]; names={'read_pc1_billing_history.py','read_pc1_history_uia.py','read-transaction-history.py','refresh_workbook.py','record_pc1_proof.py','publish_pay_now.py','regroup_funding.py','refresh_september_invoices.py'}
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:args=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
 except OSError:continue
 if any(Path(a).name in names for a in args):workers.append(int(p.name))
assert not workers
with (ROOT/'data/meta-manual-payments/writer.lock').open('r')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
lease=json.loads(subprocess.run(['python3',str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout
consumer=[s for s in cron.splitlines()if not s.lstrip().startswith('#')and'alerts-infra-failed-alert-resolver'in s];assert consumer
baseline=[]
def tabs(p):
 return[e['label'].split(' - Memory usage')[0]for e in load(p).get('elements',[])if e.get('role')=='TabItem'and e.get('bounds',[0,99999])[1]<50]
baseline=tabs(A/'approved-elements.json');assert len(baseline)==6
pairs=[]
for before in A.glob('**/*-tabs-before.json'):
 after=before.with_name(before.name.replace('-tabs-before.json','-tabs-after.json'))
 assert after.exists() and tabs(before)==tabs(after)==baseline
 pairs.append({'before':str(before),'after':str(after),'original_tab_parity':True})
assert len(pairs)==4 and tabs(B/'approved-elements.json')==baseline
assert probe['save_dialog_count']==1 and probe['input_actions']==0 and not rel['readback']['locked']
old=Path('/root/.hermes/profiles/zeus/cache/images/computer_use_0ee2960b921d46a3b3b515cf88ae5028.png')
if old.exists():shutil.copy2(old,A/'standard-worker-failure.png')
now=datetime.now(timezone.utc).isoformat()
final={'observed_at':now,'queue':{k:row[k]for k in['state','owner','attempts','failures','due','lease_until']},'owner_alive':True,'consumer_heartbeat':hb,'consumer_schedule':' '.join(consumer[0].split()[:5]),'fire_claim':j.get('fire_claim'),'last_dispatch':j['last_dispatch']['scheduled_at'],'next_native_run_at':j['next_run_at'],'writer_lock_free':True,'financial_workers':workers,'lease':lease,'pending_account_ids':pending,'original_tabs_count':len(baseline),'tab_parity_pairs':pairs}
save('final-state.json',final)
e={'operation_key':KEY,'source_key':row['source_key'],'mode':'resume_safe','status':'waiting_resource','cause':'pc1_save_as_dialog_returned_during_read_attempts_preserved','observed_at':now,'authority_receipt':str(B/'authority-readback.json'),'reconciliation_receipt':str(B/'reconciliation.json'),'final_readback':str(B/'final-state.json'),'native_contract_hash':rec['native_contract_hash'],'scope':{'sheet_id':c['sheet_id'],'active_account_count':len(c['account_ids']),'pending_stage':'D historical explicit Paid card instrument proofs only','pending_account_ids':pending,'archived_accounts_excluded':True},'progress':{'initial_save_dialog_count':0,'initial_accounts_access_verified_in_pixels':True,'exact_first_account_detail_access_verified':True,'first_account_id':'1034081997659047','first_account_name':'Eggbev-US-CC-EN-01','first_account_receipt':str(A/'history-uia1/1034081997659047-receipt.json'),'historical_paid_card_proof_obtained':False,'canonical_proof_publisher_invoked':False,'failures':[{'worker':'read_pc1_billing_history.py','reason':'billing_page_not_verified','actual_surface':'original Accounts list; target navigation not verified'},{'worker':'local read-only transaction link extension','reason':'transaction_history_not_ready'},{'worker':'local read-only diagnostic','reason':'direct_url_suggestion_not_unique'},{'worker':'local read-only foreground diagnostic','reason':'action assertion; underlying response not persisted; exact action failure cause unproven'}],'blind_retry_stopped':True},'surface':{'final_probe':str(B/'probe-receipt.json'),'save_as_dialog_confirmed_in_pixels':True,'dialog_preserved':True,'meta_authentication_challenge_demonstrated':False,'final_accounts_access_verified':True,'history_access_not_verified':True,'original_tabs_preserved':True,'original_tab_count':len(baseline),'all_attempt_tab_parity_verified':True,'lease_free_readback':True},'continuity':{'queue_owner':row['owner'],'owner_alive':True,'state':row['state'],'attempts':row['attempts'],'failures':row['failures'],'consumer_heartbeat':hb,'consumer_schedule':final['consumer_schedule'],'retry_at':None,'retry_scheduling_owner':'existing supervisor consumes this diagnostic and applies resource backoff; no queue mutation by this worker','next_step':'Reacquire lease and inspect live dialogs before input. Preserve Save As. Once PC1 is free, diagnose exact UI action response before another navigation retry; use proven native UIA detail route. Read visible View transaction history in own tab with immediate capture and persisted response, not blind table polling. Resume only these five D proofs; record only through canonical record_pc1_proof after actual Paid card pixels, then reconcile pending fields/readback. Keep later H35/D2 under ce11800d217d22dba6a58dcc; no completed-layer or business-delivery replay.'},'side_effects':{'sheet_writes':0,'meta_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'business_delivery_messages':0,'canonical_infrastructure_modified':False,'local_diagnostic_artifacts_only':True},'business_complete':False,'delivery_complete':False,'independent_closure_not_claimed':True}
save('recovery-evidence.json',e)
manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for folder in[A,B]for p in folder.rglob('*')if p.is_file()and p.suffix in['.json','.png','.py','.txt']and p.name!='evidence-sha256.json'}
save('evidence-sha256.json',manifest)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in manifest.items())
assert load(B/'recovery-evidence.json')['scope']['pending_account_ids']==pending
print(json.dumps({'checkpoint':str(B/'recovery-evidence.json'),'status':'waiting_resource','pending_ids':pending,'supervisor':row['owner'],'supervisor_alive':True,'lease_free':True,'hash_readback_valid':True,'original_tabs_preserved':True,'business_writes':0}))
