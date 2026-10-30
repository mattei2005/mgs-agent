"""Exact receipt/service/hold readback after installation; no provider mutation."""
import fcntl,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_8e65299d';sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3 import shein_request_queue as q,shein_decision_wait as dw
from ares_campaign_v3.shein_channel_authority import _get
R='shein-1565747351543480374';O='shein-1565261967260647536-c3'
report=_get('/channels/1498132022634483894/messages/1565761035963465729')
assert report['id']=='1565761035963465729' and report['channel_id']=='1498132022634483894'
assert report['author']['id']=='1496296175014252634' and report.get('content')==''
assert len(report.get('embeds') or [])==1 and not report.get('mentions')
fields={f['name']:f['value'] for f in report['embeds'][0]['fields']}
assert 't_8e65299d' in json.dumps(fields) and '531' in json.dumps(fields)
r=json.loads((B/'data/ares/meta-ads/audit/shein/campaigns/intake'/R/'request.json').read_text())
first=json.loads((q.root(B)/'queue/worker.json').read_text())
time.sleep(32)  # One bounded natural worker cycle, never execute a request as a smoke.
second=json.loads((q.root(B)/'queue/worker.json').read_text())
assert second.get('heartbeat_at') and second.get('heartbeat_at')!=first.get('heartbeat_at')
p=q.job_path(B,R);job=json.loads(p.read_text())
assert job['attempts']==0 and job['maintenance_hold']['task_id']=='t_8e65299d' and job['dependencies']==[]
assert not q.state(B,R),'maintenance must not create the new runner state'
assert q.dependencies(r,r['account'],B)==[]
with (q.root(B)/'single-clone'/('account-'+r['account']+'.lock')).open('rb') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert q.dependencies(r,r['account'],B)==[O], 'live held account must remain a dependency'
base=json.loads((W/'baseline.json').read_text())
for path,digest in base.items():
 if 'single-clone/' in path or '/request.json' in path:assert dw.digest(B/path)==digest,path
receipt=json.loads((W/'deployment-receipt.json').read_text())
assert all(dw.digest(Path(f['path']))==f['sha256'] for f in receipt['files'])
ref=Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/shein-request-queue-decision-waits.md')
assert 'WAITING_HUMAN_DECISION' in ref.read_text() and '--take-foreground' in ref.read_text()
report_proof={'message_id':report['id'],'channel_id':report['channel_id'],'author_id':report['author']['id'],
              'content_empty':True,'one_embed':True,'no_mentions':True,'verified_at':datetime.now(timezone.utc).isoformat(),
              'url':'https://discord.com/channels/1185714635991679006/1498132022634483894/'+report['id']}
inv=B/'data/infra-inventory.json'
with inv.with_suffix('.maintenance.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);before=inv.read_bytes();d=json.loads(before)
 matches=[x for x in d['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==receipt['id']];assert len(matches)==1
 matches[0]['report_infra']=report_proof;matches[0]['worker_heartbeat_verified']=second
 assert inv.read_bytes()==before,'concurrent inventory edit; retry readback only'
 q.atomic(inv,d)
check=json.loads(inv.read_text());entry=[x for x in check['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==receipt['id']]
assert len(entry)==1 and entry[0]['report_infra']==report_proof
out={'report_infra':report_proof,'worker_heartbeat_before':first,'worker_heartbeat_after':second,
     'queue_status':job['status'],'attempts':job['attempts'],'maintenance_hold':True,
     'dependencies':job['dependencies'],'new_runner_state_absent':True,'selected_assets':len(q.selected(r,B)),
     'actual_account_lock_negative':'PASS','original_input_and_historical_state_unchanged':True,
     'installed_hashes_verified':True,'inventory_exact_readback':True,'skill_readback_verified':True,
     'meta_writes':0,'drive_writes':0,'uploads':0,'inventory_reservations':0}
(W/'final-readback.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(W/'report-infra-readback.json').write_text(json.dumps(report_proof,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
