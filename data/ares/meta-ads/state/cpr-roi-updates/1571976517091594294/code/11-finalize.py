import json,hashlib,shutil,importlib.util,sys
from pathlib import Path
from datetime import datetime
from croniter import croniter
R=Path(__file__).parent;HOME=Path('/root/.hermes/profiles/ares');BASE=Path('/root/mgs-agent')
s=importlib.util.spec_from_file_location('final_daily',HOME/'scripts/shein-daily-report.py');assert s is not None and s.loader is not None
d=importlib.util.module_from_spec(s);sys.modules[s.name]=d;s.loader.exec_module(d)
m=d.load(R/'manifest.json');initial=d.load(R/'runs/initial/complete.json');tests=d.load(R/'tests.json');extra=d.load(R/'additional-tests.json');audit=d.load(R/'schedule-after.json');job=d.load(R/'scheduler-readback.json')
assert tests['pass'] and extra['pass'] and audit['pass'] and not audit['selection']['operational_conflicts']
assert audit['selection']['ticks']==m['slots'];assert len(m['slots'])==job['repeat']['times']
actual=d.load(HOME/'cron/jobs.json');jobs=actual if isinstance(actual,list) else actual['jobs'];live=next(j for j in jobs if j['id']==m['scheduler_job_id']);assert all(live[k]==job[k] for k in ['enabled','state','script','schedule','deliver','failure_deliver','no_agent','timezone','repeat','next_run_at']);assert live['enabled'] is True
iterator=croniter(job['schedule']['expr'],datetime.fromisoformat(m['slots'][0]).replace(hour=0,minute=0));ticks=[iterator.get_next(datetime).isoformat() for _ in m['slots']];assert ticks==m['slots']
parts=d.load(R/'runs/initial/update-parts.json');dc=d.Discord();ids=[]
for i,part in enumerate(parts):
 rec=d.load(R/f'runs/initial/delivery-{i}.json');assert rec['status']=='GET_VERIFIED'
 remote=dc.call('GET','/channels/'+m['thread_id']+'/messages/'+rec['message_id'])
 assert (remote['content'],remote['channel_id'],remote['author']['id'])==(part,m['thread_id'],d.BOT_ID)
 ids.append(remote['id'])
assert len(ids)==len(set(ids))==initial['parts'];snap=d.load(R/'runs/initial/snapshot.json');assert len(snap['rows'])==len(snap['campaigns'])==initial['campaigns']
m['state']='ACTIVE_FINITE_SCHEDULE_VERIFIED';m['verified_at']=d.now();m['scheduler_script_timeout_seconds']=3600;m['wrapper_timeout_seconds']=165;d.save(R/'manifest.json',m)
paths=[Path(m['runner']),Path(m['wrapper']),R/'test_updates.py',R/'test_additional.py',R/'schedule-audit.py',Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-updates/1570877060862312680/schedule-audit.py'),HOME/'scripts/shein-g004-cpr-watch-20261102.py',HOME/'scripts/shein-g004-roi-watch-20261029.py',HOME/'scripts/shein_financial_source.py',HOME/'scripts/shein-daily-report.py',HOME/'scripts/joe_custom_report_table.py',Path(__file__)]
index=[]
for i,src in enumerate(paths):
 dst=R/'code'/f'{i:02}-{src.name}';dst.parent.mkdir(exist_ok=True,mode=0o700);shutil.copy2(src,dst);raw=src.read_bytes();assert raw==dst.read_bytes();index.append({'path':str(dst),'source':str(src),'role':'reusable_code','sha256':hashlib.sha256(raw).hexdigest()})
d.save(R/'artifact-index.json',{'status':'DURABLE_VERIFIED','entries':index})
result={'status':'ACTIVE_FINITE_SCHEDULE_VERIFIED','request_id':m['request_id'],'account_id':m['account_id'],'thread_id':m['thread_id'],'message_ids':ids,'campaigns':initial['campaigns'],'numbers':initial['new'],'tests_passed':tests['tests_run']+extra['tests_run'],'first_delivery_meta_at':initial['observed_at'],'first_delivery_sb_at':initial['sb_at'],'next_update':m['slots'][0],'last_update':m['slots'][-1],'expires_at':m['expires_at'],'future_updates':len(m['slots']),'meta_writes':0,'sb_writes':0,'scheduler_job_id':m['scheduler_job_id'],'post_audit_no_operational_conflicts':True,'effective_script_timeout_seconds':3600,'wrapper_timeout_seconds':165,'initial_parts_exact_get_verified':True}
d.save(R/'final-reconciliation.json',result);print(json.dumps(result,ensure_ascii=False))
