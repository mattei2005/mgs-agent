"""Seal local probe evidence; do not mutate queue, contract or business state."""
import json,hashlib,os,sqlite3,subprocess,fcntl,re
from pathlib import Path
from datetime import datetime,timezone,timedelta
B=Path(__file__).parent
ROOT=Path('/root/mgs-agent')
KEY='79cd082a20c22a736307765f'
os.umask(0o077)
def load(p):return json.loads(Path(p).read_text())
def save(n,v):
    with (B/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
rec=load(B/'reconciliation.json'); probe=load(B/'retry-probe-receipt.json')
release=load(B/'retry-lease-release.json')
assert not release['readback']['locked'] and release['release_exit']==0
assert not probe['errors'] and probe['save_dialog_count']==1
assert sha(ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json')==rec['contract_sha256']
ledger=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
assert all(not ledger.get(k) for k in rec['pending_account_ids'])
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select key,state,cause,owner,attempts,failures,due,lease_until from requests where key=?',(KEY,)).fetchone())
assert row['owner']==rec['queue']['owner'];os.kill(int(row['owner'].split(':')[1]),0)
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
r=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True)
schedules=[l for l in r.stdout.splitlines() if 'alerts-infra-failed-alert-resolver.py' in l and not l.lstrip().startswith('#')]
assert len(schedules)==1 and schedules[0].startswith('2-57/5 * * * * ')
now=datetime.now(timezone.utc);n=now.replace(second=0,microsecond=0)+timedelta(minutes=1)
while n.minute not in range(2,58,5):n+=timedelta(minutes=1)
visual={'inspected_with':'vision_analyze','approved_accounts_access_confirmed':True,'business_id_visible_in_url':'155263197283282','business_name_not_proven_in_pixels':True,'profile_Rodolfo_confirmed_in_AX':True,'profile_name_not_visible_in_pixels':True,'authentication_gate_on_approved_surface':False,'page_error_on_approved_surface':False,'native_save_as_dialog_confirmed':True,'native_authentication_dialog_demonstrated':False,'dialog_preserved':True,'desktop_available_not_proven':True,'human_currently_present_not_proven':True,'original_tabs_count':6,'original_tabs_preserved':True,'captures':probe['captures']}
save('visual-verification.json',visual)
final={'observed_at':now.isoformat(),'queue':row,'owner_alive':True,'heartbeat':hb,'consumer_schedule':schedules[0].split(' flock',1)[0],'next_scheduled_consumer_check_utc':n.isoformat(),'writer_lock_free':True,'lease_free_readback':True,'contract_unchanged_from_preflight':True,'pending_ledger_entries_still_absent':True,'later_tick_gate_preserved': [dict(x) for x in q.execute('select key,state,owner,attempts,failures from requests where key=?',('6373afb33275674610c06b6a',))]}
save('final-state.json',final)
evidence={'operation_key':KEY,'source_key':'native:zeus:2ee720363d7d:20261125T0802:historical-d','mode':'probe_only','status':'waiting_resource','cause':'pc1_save_as_dialog_present_preserved','observed_at':now.isoformat(),'authority_receipt':str(B/'authority-readback.json'),'reconciliation_receipt':str(B/'reconciliation.json'),'sheet_readback':str(B/'sheet-readback.json'),'final_readback':str(B/'final-state.json'),'native_contract_hash':rec['native_contract_hash'],'scope':{'sheet_id':794137639,'active_account_count':rec['active_account_count'],'exact_live_ids_verified':rec['exact_live_ids_verified'],'pending_account_ids':rec['pending_account_ids'],'pending_stage':'D historical explicit Paid card instrument proofs ONLY','new_account_D_separate_not_adopted':'1770569568407466','archived_accounts_excluded':True},'visual_readback':visual,'continuity':final,'side_effects':{'input_actions':0,'tabs_created':0,'tabs_closed':0,'sheet_writes':0,'meta_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'business_delivery_messages':0,'queue_mutations':0,'canonical_infrastructure_modified':False,'local_diagnostic_artifacts_only':True},'local_diagnostic_error':{'kind':'sqlite_column_lookup','error':'no such column: operation_key','resolved':'PRAGMA confirmed primary key column key; same read succeeded; no writes'},'auth_ready':False,'auth_ready_reason_not_emitted':'Accounts access does not remove preserved native Save As desktop gate. No resumption authorized in probe_only.','next_step':'Existing supervisor retains ownership/backoff. Revalidate same windows without input; preserve Save As. Only after resource gate cleared may existing authorized executor collect the same five D proofs. No financial phase replay or duplicate delivery.','business_complete':False,'delivery_complete':False,'independent_closure_not_claimed':True}
save('recovery-evidence.json',evidence)
hashes={p.name:sha(p) for p in sorted(B.iterdir()) if p.is_file() and p.name!='evidence-sha256.json'}
save('evidence-sha256.json',hashes)
assert all(sha(B/name)==h for name,h in load(B/'evidence-sha256.json').items())
print(json.dumps({'checkpoint':str(B/'recovery-evidence.json'),'status':evidence['status'],'mode':evidence['mode'],'hashes_verified':True,'lease_free':True,'owner_alive':True,'pending_D_count':len(rec['pending_account_ids']),'next_consumer_scheduled_check_utc':n.isoformat(),'retry_time_not_guaranteed':True}))
