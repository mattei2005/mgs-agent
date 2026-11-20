import pathlib,json,hashlib,shutil,importlib.util,sys
from datetime import datetime
R=pathlib.Path(__file__).parent;H=pathlib.Path('/root/.hermes/profiles/ares');s=importlib.util.spec_from_file_location('reconcile_daily',H/'scripts/shein-daily-report.py');assert s and s.loader;d=importlib.util.module_from_spec(s);sys.modules[s.name]=d;s.loader.exec_module(d)
m=d.load(R/'manifest.json');initial=d.load(R/'runs/initial/complete.json');parts=d.load(R/'runs/initial/update-parts.json');dc=d.Discord();ids=[]
for i,part in enumerate(parts):
 rec=d.load(R/f'runs/initial/delivery-{i}.json');assert rec['status']=='GET_VERIFIED';remote=dc.call('GET','/channels/'+m['thread_id']+'/messages/'+rec['message_id']);assert (remote['content'],remote['channel_id'],remote['author']['id'])==(part,m['thread_id'],d.BOT_ID);ids.append(remote['id'])
infra=dc.call('GET','/channels/1498132022634483894/messages/1573407294857941042');assert infra['id']=='1573407294857941042' and not infra['content'] and infra['embeds'] and not infra['mentions'];d.save(R/'report-infra-readback.json',{'id':infra['id'],'channel_id':infra['channel_id'],'content_empty':not infra['content'],'mentions':len(infra['mentions']),'embeds':len(infra['embeds'])})
qa=[d.load(R/n) for n in ['tests.json','additional-tests.json']];assert all(x['pass'] and not x['errors'] and not x['failures'] for x in qa)
snap=d.load(R/'runs/initial/snapshot.json');assert set(snap['rows'])=={x['id'] for x in m['campaigns']} and len(ids)==len(set(ids))==initial['parts'];assert not m.get('scheduler_job_id')
paths=[pathlib.Path(m['runner']),pathlib.Path(m['wrapper']),R/'test_updates.py',R/'test_additional.py',R/'schedule-audit.py',H/'scripts/shein-g004-cpr-watch-20261102.py',H/'scripts/shein-g004-roi-watch-20261029.py',H/'scripts/shein_financial_source.py',H/'scripts/shein-daily-report.py',H/'scripts/joe_custom_report_table.py',pathlib.Path(__file__)]
entries=[]
for i,src in enumerate(paths):
 dst=R/'code'/f'{i:02}-{src.name}';dst.parent.mkdir(exist_ok=True,mode=0o700);shutil.copy2(src,dst);assert dst.read_bytes()==src.read_bytes();entries.append({'path':str(dst),'source':str(src),'role':'reusable_code','sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
d.save(R/'artifact-index.json',{'status':'DURABLE_VERIFIED','entries':entries})
result={'status':m['state'],'request_id':m['request_id'],'account_id':m['account_id'],'thread_id':m['thread_id'],'message_ids':ids,'campaigns':len(snap['rows']),'numbers':sorted(initial['new']),'first_delivery_meta_at':initial['observed_at'],'first_delivery_sb_at':initial['sb_at'],'tests_passed':sum(x['tests_run'] for x in qa),'schedule_created':False,'blocker':m['schedule_blocker'],'proposed_schedule':m['proposed_schedule'],'meta_writes':0,'sb_writes':0,'initial_parts_exact_get_verified':True,'next_step':'Await operator decision on delayed start; re-audit before scheduling, preserve first delivery receipt.'}
d.save(R/'final-reconciliation.json',result);d.save(R/'inventory.json',{'request_id':m['request_id'],'runner':m['runner'],'wrapper':m['wrapper'],'scope':m['account_id'],'source_thread':m['thread_id'],'scheduler_job_id':None,'state':m['state'],'report_infra_message_id':infra['id'],'files':entries})
print(json.dumps({k:v for k,v in result.items() if k not in ['proposed_schedule','blocker']},ensure_ascii=False))
