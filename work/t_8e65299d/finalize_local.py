"""Finalize only local scheduling/inventory/audit; no Meta/Drive operation."""
import fcntl,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_8e65299d';sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3 import shein_request_queue as q,shein_decision_wait as dw
R='shein-1565747351543480374';O='shein-1565261967260647536-c3';now=datetime.now(timezone.utc).isoformat()
rpath=B/'data/ares/meta-ads/audit/shein/campaigns/intake'/R/'request.json';request=json.loads(rpath.read_text())
p=q.job_path(B,R)
with p.with_suffix('.dispatch.lock').open('a+') as dispatch,p.with_suffix('.lock').open('a+') as lock:
 for h in [dispatch,lock]:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
 job=json.loads(p.read_text());assert job['attempts']==0 and job['maintenance_hold']['task_id']=='t_8e65299d'
 deps=q.dependencies(request,request['account'],B);assert deps==[]
 job['dependencies']=deps
 job['dependency_validation']={'at':now,'task_id':'t_8e65299d','status':'DEPENDENCY_READY_ONLY',
     'media_readiness_verified':False,'source':'work/t_8e65299d/installation-readback.json',
     'execution_requires':'Explicit Ares --take-foreground then original central runner'}
 q.atomic(p,job)
base=json.loads((W/'baseline.json').read_text())
for path,digest in base.items():
 if 'single-clone/' in path or '/request.json' in path:assert dw.digest(B/path)==digest,path
files=[B/'scripts/ares_campaign_v3/shein_request_queue.py',B/'scripts/ares_campaign_v3/shein_decision_wait.py',B/'tests/test_shein_decision_wait.py',dw.record_path(B,O),Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/shein-request-queue-decision-waits.md')]
reg=json.loads((W/'regression-final.json').read_text());assert reg['exit_code']==0 and not reg['failed'] and not reg['module_origin_mismatch']
entry={'id':'shein-inert-review-queue-t_8e65299d','agent':'zeus','type':'central-shein-human-decision-wait-scheduling',
       'status':'installed_dependency_ready_only_held_for_ares','updated_at':now,'task_id':'t_8e65299d',
       'request_id':R,'historical_request_id':O,'account_id':request['account'],'operation':'SHEIN-US-DIRECT',
       'authority':['context/routes.md#delegação-histórica-de-recovery-ares--zeus','kanban:t_8e65299d'],
       'files':[{'path':str(p),'sha256':dw.digest(p),'size_bytes':p.stat().st_size} for p in files],
       'tests':reg,'dependencies_readonly':[],'media_readiness_verified':False,'queue_attempts':0,
       'queue_maintenance_hold':True,'foreground_handoff_executor':'ares','next_task':'t_8f7a90a8',
       'original_input_sha256':dw.digest(rpath),'historical_state_sha256':base['data/ares/meta-ads/state/shein-campaigns/single-clone/'+O+'/state.json'],
       'historical_review':'UNANSWERED; 006/007 PAUSED; runner POSTPROCESS_PENDING preserved',
       'meta_writes':0,'drive_writes':0,'uploads':0,'inventory_reservations':0,
       'credential_budget_strategy_guard_or_sla_changed':False,'gateway_restart':False,
       'queue_service':'ares-shein-request-queue.service; stopped idle worker, reloaded with durable hold',
       'backup':str(W/'rollback'),'live_evidence':str(W/'live-readonly.json'),
       'rollback':'Keep durable hold and reconcile foreground ownership/effects before restoring original queue code. Never restore stale job or rewrite history; no deletion implied.'}
inv=B/'data/infra-inventory.json'
with inv.with_suffix('.maintenance.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 before=inv.read_bytes();d=json.loads(before);rows=d.setdefault('runtime_artifacts',[])
 matches=[i for i,x in enumerate(rows) if isinstance(x,dict) and x.get('id')==entry['id']]
 assert len(matches)<=1
 if matches:rows[matches[0]]=entry
 else:rows.append(entry)
 backup=W/'rollback/infra-inventory-before.json'
 if not backup.exists():backup.write_bytes(before)
 assert inv.read_bytes()==before,'concurrent inventory write; retry fresh'
 q.atomic(inv,d)
 after=json.loads(inv.read_text());assert len([x for x in after['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==entry['id']])==1
with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','task_id':'t_8e65299d','action':'shein_inert_review_queue_installed','request_id':R,'historical_request_id':O,'inventory_id':entry['id'],'result':'dependency ready only; durable maintenance hold; Ares-only foreground handoff','tests_passed':reg['passed'],'subtests_passed':reg['subtests_passed'],'original_input_unchanged':True,'historical_state_unchanged':True,'provider_writes':0,'gateway_restart':False},ensure_ascii=False)+'\n')
(W/'deployment-receipt.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'inventory_id':entry['id'],'tests_passed':reg['passed'],'subtests_passed':reg['subtests_passed'],'deps':deps,'job_attempts':job['attempts'],'hold':True,'source_hashes':entry['files'][:3]},ensure_ascii=False))
