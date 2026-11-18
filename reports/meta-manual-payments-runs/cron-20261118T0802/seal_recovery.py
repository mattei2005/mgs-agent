"""Seal validated occurrence metadata without mutating the supervisor queue."""
import sys,json,os,fcntl,hashlib,sqlite3
from pathlib import Path
from datetime import datetime
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_finance_continuity import validate,observation,CURRENT_KEY
from mgs_dtr_continuity import atomic
BASE=Path('/root/mgs-agent');B=Path(__file__).resolve().parent;H=BASE/'data/meta-manual-payments'
load=lambda p:json.loads(Path(p).read_text())
j=next(j for j in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs'] if j['id']=='2ee720363d7d')
r,c=validate(key=CURRENT_KEY);obs=observation(j);assert obs and obs['verified'] and obs['target']==r['source_key']
with (H/'writer.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 current=load(H/'digital-trust-workbook-contract.json');assert current==c
 atomic(B/'qualification-before-final-seal.json',c['latest_refresh_qualification'])
 qual=dict(r,status='completed_validated',run_kind='scheduled_tick',job_id=j['id'],api_collected_at=r['validated_metrics_at'],delivery='canonical_occurrence_adapter_GET_verified',business_delivery_message_id=obs['message_id'],evidence=str(B/'recovery-financial-validation.json'),run_dir=str(B),next_run_at=j['next_run_at'],schedule_unchanged=True,report_infra_status='pending_this_round')
 c['latest_refresh_qualification']=qual
 c['pending_card_history']={'status':'recent_events_resolved_historical_gaps_qualified','account_ids':[],'pending_ui':[],'historical_blank_count':len(r['historical_blank_d']),'evidence':str(B/'recovery-financial-validation.json')}
 atomic(H/'digital-trust-workbook-contract.json',c);assert load(H/'digital-trust-workbook-contract.json')==c
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
own=dict(q.execute('select key,state,owner,lease_until,due,attempts from requests where key=?',(CURRENT_KEY,)).fetchone());assert own['state']=='running';os.kill(int(own['owner'].split(':')[1]),0)
worker=load('/root/.hermes/shared/automation-continuity/runs/'+CURRENT_KEY+'/worker.json');assert worker['state']=='running';os.kill(worker['pid'],0)
now=datetime.now().astimezone().isoformat()
checkpoint=dict(continuity_key=CURRENT_KEY,source_key=r['source_key'],state='financial_and_delivery_validated_waiting_independent_supervisor',verified_at=now,accounts=55,H_published_readback=40,D_renewed=r['D_verified_published_ids'],pending_account_ids_D=[],pending_account_ids_H=[],pending_layers=['independent_supervisor_queue_closure'],business_refresh_complete=True,business_delivery=obs,payments_executed=0,billing_changes=0,meta_writes=0,cron_changes=0,gateway_restarts=0,ownership=own,worker=worker,queue_mutated_by_worker=False,pc1_lease_free=True,receipt=str(B/'recovery-financial-validation.json'),snapshot=str(B/'recovery-final-workbook.json'),report_infra_status='pending_this_round',next_action='Supervisor consumes this result; exact occurrence observation and canonical verify_only GET. Do not recollect or republish any financial layer or business delivery. Earlier occurrences remain separate.')
atomic(B/'recovery-closure-checkpoint.json',checkpoint)
invpath=BASE/'data/infra-inventory.json';inv=load(invpath);identity='finance-recovery-'+CURRENT_KEY+'-final'
assert not any(e.get('id')==identity for e in inv.get('runtime_artifacts',[]))
paths=['scripts/mgs_finance_continuity.py','scripts/mgs_automation_supervisor.py','tests/test_finance_continuity_delivery.py']
entry={'id':identity,'agent':'zeus','type':'financial_recovery_and_occurrence_adapter','authority_message_id':'1569193434189668453','status':checkpoint['state'],'evidence':str(B/'recovery-closure-checkpoint.json'),'paths':paths,'hashes':{p:hashlib.sha256((BASE/p).read_bytes()).hexdigest() for p in paths},'validation':'107 continuity tests PASS; full live source parity55/H40/D8, pending_ui empty, other tab unchanged; canonical delivery GET verified','business_delivery_message_id':obs['message_id'],'payments_executed':0,'cron_changes':0,'gateway_restarts':0}
inv.setdefault('runtime_artifacts',[]).insert(0,entry);atomic(invpath,inv);matches=[e for e in load(invpath)['runtime_artifacts'] if e.get('id')==identity];assert matches==[entry]
event={'at':now,'agent':'zeus','action':'finance_occurrence_recovered_adapter_extended','authority_message_id':'1569193434189668453','continuity_key':CURRENT_KEY,'source_key':r['source_key'],'receipt':str(B/'recovery-financial-validation.json'),'business_delivery_message_id':obs['message_id'],'tests_passed':107,'queue_closure':'independent_supervisor_pending','paths':paths,'payments_executed':0,'cron_changes':0,'gateway_restarts':0}
with (BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
assert json.loads((BASE/'logs/events-audit.jsonl').read_text().splitlines()[-1])==event
print(json.dumps({'checkpoint':str(B/'recovery-closure-checkpoint.json'),'inventory_id':identity,'contract_readback':True,'audit_readback':True,'owner_alive':True,'delivery_GET':obs['message_id']}))
