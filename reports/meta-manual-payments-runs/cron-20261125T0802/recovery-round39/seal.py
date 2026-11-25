"""Seal the verified resource gate without retrying business actions."""
import os,json,hashlib,sqlite3,subprocess,fcntl
from pathlib import Path
from datetime import datetime,timezone
os.umask(0o077)
B=Path(__file__).parent
ROOT=Path('/root/mgs-agent')
KEY='79cd082a20c22a736307765f'
def load(p):return json.loads(Path(p).read_text())
def save(n,d):
    with (B/n).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
rec=load(B/'reconciliation.json');probe=load(B/'probe-receipt.json');auth=load(B/'authority-readback.json')
cp=ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json'
c=load(cp)
assert hashlib.sha256(cp.read_bytes()).hexdigest()==rec['contract_sha256']
assert all(m['status']==200 for m in auth['messages']) and auth['current_registry_rodolfo_authorized']
pending=c['pending_new_account_fields']['D_account_ids']
assert pending==rec['pending_account_ids']
ledger=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
assert not any(ledger.get(k) for k in pending)
assert probe['save_dialog_count']==1 and probe['input_actions']==0
assert not load(B/'lease-release.json')['readback']['locked']
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone())
assert row['state']=='running'
os.kill(int(row['owner'].split(':')[1]),0)
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
lease=json.loads(subprocess.run(['python3',str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout)
assert not lease['locked']
def tabs(p):
    return [e['label'].split(' - Memory usage')[0] for e in load(p).get('elements',[]) if e.get('role')=='TabItem' and e.get('bounds',[0,99999])[1]<50]
current=tabs(B/'approved-elements.json');baseline=tabs(B.parent/'recovery-round38/approved-elements.json')
assert current==baseline and len(current)==6
jobs=load('/root/.hermes/profiles/zeus/cron/jobs.json')
j=next(x for x in (jobs if isinstance(jobs,list) else jobs['jobs']) if x['id']=='2ee720363d7d')
assert j['enabled'] and not j.get('fire_claim')
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
now=datetime.now(timezone.utc).isoformat()
final={'observed_at':now,'queue':{k:row[k] for k in ['state','owner','attempts','failures','due','lease_until']},'queue_owner_alive':True,'consumer_heartbeat':hb,'consumer_schedule':' '.join(consumer[0].split()[:5]),'next_native_run_at':j['next_run_at'],'fire_claim':j.get('fire_claim'),'writer_lock_free':True,'financial_worker_processes':workers,'lease':lease,'pending_account_ids':pending,'original_tabs_count':len(current),'original_tabs_preserved':True,'contract_sha256_unchanged':True}
save('final-state.json',final)
e={'operation_key':KEY,'source_key':row['source_key'],'mode':'resume_safe','status':'waiting_resource','cause':'pc1_save_as_dialog_present_preserved','observed_at':now,'authority_receipt':str(B/'authority-readback.json'),'reconciliation_receipt':str(B/'reconciliation.json'),'final_readback':str(B/'final-state.json'),'native_contract_hash':rec['native_contract_hash'],'scope':{'sheet_id':c['sheet_id'],'active_account_count':len(c['account_ids']),'pending_stage':'D historical explicit Paid card instrument proofs ONLY','pending_account_ids':pending,'archived_accounts_excluded':True},'visual_readback':{'inspected_with':'vision_analyze','save_as_dialog_confirmed_in_pixels':True,'dialog_preserved':True,'approved_accounts_access_confirmed':True,'business_id':'155263197283282','meta_authentication_challenge_demonstrated':False,'historical_paid_card_table_visible':False,'original_tabs_count':len(current),'original_tabs_preserved':True,'captures':probe['captures']},'continuity':{'state':row['state'],'queue_owner':row['owner'],'owner_alive':True,'attempts':row['attempts'],'failures':row['failures'],'consumer_heartbeat':hb,'consumer_schedule':final['consumer_schedule'],'retry_at':None,'retry_scheduling_owner':'Existing supervisor consumes this diagnostic and applies resource backoff; no queue mutation by this worker.','next_step':'Reacquire lease and inspect live windows; preserve unrelated Save As dialog. Only after resource is free, persist exact UI-action response before navigation retry, collect five missing historical D proofs in actual Paid/card pixels, use canonical record_pc1_proof and reconcile exact contract pending fields/readback. Preserve original six tabs. Later tick H35/D2 remains separate ce11800d217d22dba6a58dcc. Do not repeat completed financial layers or delivery.'},'side_effects':{'input_actions':0,'tabs_created':0,'tabs_closed':0,'sheet_writes':0,'meta_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'business_delivery_messages':0,'canonical_infrastructure_modified':False,'local_diagnostic_artifacts_only':True},'lease_free_readback':True,'business_complete':False,'delivery_complete':False,'independent_closure_not_claimed':True}
save('recovery-evidence.json',e)
manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in B.iterdir() if p.is_file() and p.suffix in ['.json','.png','.py'] and p.name!='evidence-sha256.json'}
save('evidence-sha256.json',manifest)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in load(B/'evidence-sha256.json').items())
assert load(B/'recovery-evidence.json')['scope']['pending_account_ids']==pending
print(json.dumps({'checkpoint':str(B/'recovery-evidence.json'),'status':'waiting_resource','pending_ids':pending,'supervisor':row['owner'],'supervisor_alive':True,'lease_free':True,'hash_readback_valid':True,'original_tabs_preserved':True,'business_writes':0}))
