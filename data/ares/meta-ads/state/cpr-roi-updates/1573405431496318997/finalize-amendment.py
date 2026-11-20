import pathlib,json,importlib.util,sys,hashlib,shutil
from datetime import datetime
from croniter import croniter
R=pathlib.Path(__file__).parent;H=pathlib.Path('/root/.hermes/profiles/ares');A=R/'amendments/1573430872906924114'
s=importlib.util.spec_from_file_location('daily_final',H/'scripts/shein-daily-report.py');assert s and s.loader;d=importlib.util.module_from_spec(s);sys.modules[s.name]=d;s.loader.exec_module(d)
m=d.load(R/'manifest.json');job=d.load(R/'scheduler-readback.json');jobs=d.load(H/'cron/jobs.json');jobs=jobs if isinstance(jobs,list) else jobs['jobs'];live=next(j for j in jobs if j['id']==m['scheduler_job_id']);assert all(live[k]==job[k] for k in ['enabled','state','schedule','script','timezone','no_agent','deliver','failure_deliver','repeat','next_run_at']);assert live['enabled'] and live['repeat']['times']==len(m['slots'])==17
post=d.load(R/'schedule-after.json');assert post['pass'] and not post['selection']['operational_conflicts'] and post['selection']['ticks']==m['slots'];it=croniter(live['schedule']['expr'],datetime.fromisoformat(m['slots'][0]).replace(hour=15,minute=20,second=0,microsecond=0));assert [it.get_next(datetime).isoformat() for _ in m['slots']]==m['slots']
from cron.scheduler_script import _get_script_timeout
timeout=_get_script_timeout();assert timeout>165
qa=[d.load(R/n) for n in ['tests.json','additional-tests.json','amendment-tests.json']];assert all(q['pass'] and q['errors']==q['failures']==0 for q in qa)
for rel,sha in d.load(A/'initial-hashes.json').items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==sha
run=R/'runs'/m['schedule_reference_run'];snap=d.load(run/'snapshot.json');parts=d.load(run/'update-parts.json');complete=d.load(run/'complete.json');dc=d.Discord();ids=[]
for i,part in enumerate(parts):
 rec=d.load(run/f'delivery-{i}.json');assert rec['status']=='GET_VERIFIED';remote=dc.call('GET','/channels/'+m['thread_id']+'/messages/'+rec['message_id']);assert (remote['content'],remote['author']['id'],remote['channel_id'])==(part,d.BOT_ID,m['thread_id']);ids.append(remote['id'])
assert len(ids)==len(set(ids))==complete['parts'];assert set(snap['rows'])=={c['id'] for c in m['campaigns']} and len(snap['rows'])==complete['campaigns']==11
m.update(state='ACTIVE_FINITE_SCHEDULE_VERIFIED',verified_at=d.now(),scheduler_script_timeout_seconds=timeout,wrapper_timeout_seconds=165);m.pop('schedule_blocker',None);m.pop('proposed_schedule',None);d.save(R/'manifest.json',m)
result={'state':m['state'],'request_id':m['request_id'],'amendment_message_id':m['amendment_message_id'],'account_id':m['account_id'],'thread_id':m['thread_id'],'initial_preserved':True,'amendment_delivery_message_ids':ids,'campaigns':complete['campaigns'],'new':sorted(complete['new']),'edited':sorted(complete['edited']),'meta_at':complete['observed_at'],'sb_at':complete['sb_at'],'next_update':m['slots'][0],'last_update':m['slots'][-1],'expires_at':m['expires_at'],'future_updates':len(m['slots']),'tests_passed':sum(q['tests_run'] for q in qa),'scheduler_job_id':live['id'],'scheduler_script_timeout':timeout,'post_audit_no_conflict':True,'meta_writes':0,'sb_writes':0}
d.save(A/'final-reconciliation.json',result)
paths=[pathlib.Path(m['runner']),pathlib.Path(m['wrapper']),R/'schedule-audit.py',R/'amend-select.py',R/'amend-preflight.py',R/'test_updates.py',R/'test_additional.py',R/'test_amendment.py',pathlib.Path(__file__),H/'scripts/shein-daily-report.py',H/'scripts/shein_financial_source.py',H/'scripts/shein-g004-roi-watch-20261029.py',H/'scripts/joe_custom_report_table.py'];entries=[]
for i,src in enumerate(paths):
 dst=A/'code'/f'{i:02}-{src.name}';dst.parent.mkdir(exist_ok=True,mode=0o700);shutil.copy2(src,dst);assert src.read_bytes()==dst.read_bytes();entries.append({'path':str(dst),'source':str(src),'role':'reusable_code','sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
d.save(A/'artifact-index.json',{'status':'DURABLE_VERIFIED','entries':entries});d.save(A/'inventory.json',{'request_id':m['request_id'],'amendment_message_id':m['amendment_message_id'],'scheduler_job_id':live['id'],'runner':m['runner'],'wrapper':m['wrapper'],'state':m['state'],'schedule':live['schedule'],'file_index':'artifact-index.json'})
print(json.dumps(result,ensure_ascii=False))
