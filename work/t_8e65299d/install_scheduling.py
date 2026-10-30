"""Install scheduling evidence and a dry Ares-only handoff. No provider writes."""
import fcntl,json,sys,subprocess
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3 import shein_request_queue as q, shein_decision_wait as dw
W=B/'work/t_8e65299d';proof=json.loads((W/'live-readonly.json').read_text())
R=proof['request_id'];O=proof['historical_request_id'];s=q.state(B,O);account=s['request']['account']
assert subprocess.run(['systemctl','is-active','ares-shein-request-queue.service'],capture_output=True).returncode!=0
assert proof['authority_live']=='PASS' and proof['history_coverage']['complete']
assert [x['id'] for x in proof['history_coverage']['humans_after_review']]==['1565747351543480374']
assert proof['review']['id']=='1565343225894666345'
assert len(proof['campaigns'])==2 and all(x['status']=='PAUSED' for x in proof['campaigns'])
baseline=json.loads((W/'baseline.json').read_text())
for path,digest in baseline.items():
 if not path.endswith('shein_request_queue.py'):assert dw.digest(B/path)==digest,path
cfg=json.loads((B/'data/ares/meta-ads/engine-v3/config.json').read_text());eroot=Path(cfg['state_root'])
cp=eroot/'checkpoints'/(O+'-'+account+'.json')
record={'schema_version':1,'classification':'WAITING_HUMAN_DECISION','request_id':O,'account_id':account,
        'state_sha256':dw.digest(q.root(B)/'single-clone'/O/'state.json'),
        'checkpoint_sha256':dw.digest(cp),'verified_at':proof['verified_at'],
        'review':{'message_id':proof['review']['id'],'author_id':proof['review']['author_id'],
                  'channel_id':s['request']['source_channel_id'],'thread_id':s['request']['source_thread_id'],
                  'decision':'UNANSWERED','material_difference':True,
                  'differences':['device suggestion omitted','user_age_unknown false -> true']},
        'campaign_readback':proof['campaigns'],'maintenance_task_id':'t_8e65299d',
        'evidence_source':'work/t_8e65299d/live-readonly.json',
        'semantics':'Scheduling classification only. Review unanswered; not terminal, approved, canceled, QA-complete or authorized for activation. No reservation/lease release.'}
jobpath=q.job_path(B,R)
with (q.root(B)/'single-clone'/('account-'+account+'.lock')).open('rb') as account_lock, (eroot/'writer-leases'/(account+'.lock')).open('rb') as lease_lock, jobpath.with_suffix('.dispatch.lock').open('a+') as dispatch,jobpath.with_suffix('.lock').open('a+') as joblock:
 for handle in [account_lock,lease_lock,dispatch,joblock]:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
 lease=json.loads((eroot/'writer-leases'/(account+'.json')).read_text())
 assert lease['status']=='COMPLETE' and lease['blocks_readers'] is False and lease.get('released_at_utc')
 job=json.loads(jobpath.read_text());assert job['attempts']==0 and job['status']=='WAITING'
 job['maintenance_hold']={'task_id':'t_8e65299d','reason':'Dry handoff to owning Ares required before any automatic execution',
                          'executor':'ares','created_at':datetime.now(timezone.utc).isoformat(),
                          'release_route':'ares_campaign_v3.shein_request_queue --take-foreground ORIGINAL_INPUT'}
 q.atomic(jobpath,job)
 q.atomic(dw.record_path(B,O),record)
 dw.evidence(B,s)
r=job['request'];deps=q.dependencies(r,account,B)
assert deps==[],deps
# Fresh direct tick is allowed to run only the hold gate, never the runner.
q.tick(json.loads(jobpath.read_text()),B)
read=json.loads(jobpath.read_text());assert read['attempts']==0 and read['maintenance_hold']==job['maintenance_hold']
for path,digest in baseline.items():
 if 'single-clone/' in path or '/request.json' in path:assert dw.digest(B/path)==digest,path
receipt={'classification':'WAITING_HUMAN_DECISION','dependencies_readonly':deps,'job_hold':read['maintenance_hold'],
         'attempts':read['attempts'],'historical_state_unchanged':True,'intake_unchanged':True,
         'historical_terminal':q.terminal(s),'state_phase':s['phase'],'media_rows':len(q.selected(r,B)),
         'meta_writes':0,'drive_writes':0,'uploads':0,'inventory_reservations':0,
         'record_path':str(dw.record_path(B,O))}
(W/'installation-readback.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
