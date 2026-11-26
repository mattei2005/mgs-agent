from pathlib import Path
from datetime import datetime
import json,hashlib,subprocess,importlib.util,sys,shutil,re,ast
R=Path(__file__).parent;B=Path('/root/mgs-agent');H=Path('/root/.hermes/profiles/ares')
s=importlib.util.spec_from_file_location('final07',H/'scripts/shein-g004-mavroa07-cpr-roi-20261126.py');assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
x=m.load(R/'manifest.json');initial=m.load(R/'runs/initial/complete.json');snap=m.load(R/'runs/initial/snapshot.json');parts=m.load(R/'runs/initial/update-parts.json');d,_,_=m.helpers();dc=d.Discord();ids=[]
for i,part in enumerate(parts):
 rec=m.load(R/f'runs/initial/delivery-{i}.json');assert rec['status']=='GET_VERIFIED';obj=dc.call('GET','/channels/'+m.TID+'/messages/'+rec['message_id']);assert (obj['content'],obj['channel_id'],obj['author']['id'])==(part,m.TID,d.BOT_ID);ids.append(obj['id'])
assert len(ids)==len(set(ids))==initial['parts'];assert set(snap['rows'])=={c['id'] for c in x['campaigns']};assert all(c['reasons']==['created_today'] for c in x['campaigns']);assert not x['dynamic_discovery']['enabled']
qa=m.load(R/'tests.json');assert qa['pass'] and qa['errors']==qa['failures']==0 and qa['tests_run']==20
assert m.load(R/'initial-replay-verification.json')['pass'];assert m.load(R/'baseline-classification-test.json')['pass'];assert m.load(R/'schedule-after.json')['pass']
jobs=m.load(H/'cron/jobs.json');jobs=jobs if isinstance(jobs,list) else jobs['jobs'];j=next(j for j in jobs if j['id']==x['scheduler_job_id']);assert j['enabled'] and j['state']=='scheduled' and j['no_agent'] and j['script']==Path(x['wrapper']).name and j['deliver']==j['failure_deliver']=='local';assert j['timezone']==x['timezone_name'] and j['repeat']=={'times':len(x['slots']),'completed':0};assert j['next_run_at']==x['slots'][0];assert j['schedule']['expr']==','.join(map(str,x['minutes']))+' * 26 11 *';m.save(R/'scheduler-readback.json',j)
# Verify the registered wrapper's regular scheduler path is silent outside its slots.
out=subprocess.run(['bash',x['wrapper']],capture_output=True,text=True,timeout=180);assert out.returncode==0 and not out.stdout;m.save(R/'scheduled-wrapper-not-due.json',{'pass':True,'exit':out.returncode,'stdout_empty':True,'observed_at':datetime.now().astimezone().isoformat()})
x.update(state='ACTIVE_FINITE_SCHEDULE_VERIFIED',verified_at=datetime.now().astimezone().isoformat());m.save(R/'manifest.json',x)
result={'status':x['state'],'request_id':m.REQUEST,'account_id':m.AID,'thread_id':m.TID,'message_ids':ids,'campaigns':len(snap['rows']),'numbers':sorted(initial['new']),'first_meta_cut':initial['observed_at'],'first_sb_cut':initial['sb_at'],'tests_passed':qa['tests_run'],'baseline_cases_passed':3,'next':j['next_run_at'],'last':x['slots'][-1],'slots':len(x['slots']),'expires_at':x['expires_at'],'fixed_cohort':True,'meta_writes':0,'dashboard_writes':0,'schedule_verified':True,'first_delivery_exact_get_verified':True,'future_deliveries_observed':False}
m.save(R/'final-reconciliation.json',result)
# Archive reviewed reusable code only, preserving source hashes for future same-scope reuse.
paths=[Path(x['runner']),Path(x['wrapper']),R/'test_fixed.py',R/'freeze-cohort.py',R/'schedule-audit.py',Path(__file__),H/'scripts/shein-g004-cpr-watch-20261102.py',H/'scripts/shein-g004-roi-watch-20261029.py',H/'scripts/shein_financial_source.py',H/'scripts/shein-daily-report.py',H/'scripts/joe_custom_report_table.py',B/'data/ares/meta-ads/state/cpr-updates/1570877060862312680/schedule-audit.py']
entries=[]
for i,p in enumerate(paths):
 dst=R/'code'/f'{i:02}-{p.name}';dst.parent.mkdir(exist_ok=True,mode=0o700);shutil.copy2(p,dst);assert dst.read_bytes()==p.read_bytes();entries.append({'path':str(dst),'source':str(p),'role':'reusable_code','sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
for name in ['manifest.json','authorization.json','binding.json','tests.json','additional-tests.json','baseline-classification-test.json','review-approved.json','initial-replay-verification.json','schedule-before.json','schedule-after.json','scheduler-readback.json','final-reconciliation.json','scheduled-wrapper-not-due.json']:
 p=R/name;assert p.exists();entries.append({'path':str(p),'role':'current_evidence','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for name in ['account','frozen-campaigns','adsets','insights','sb','delay']:
 for suffix in ['.json','-observed-at.json']:
  p=R/'runs/initial'/(name+suffix);assert p.exists();entries.append({'path':str(p),'role':'current_source','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for name in ['snapshot.json','membership-evidence.json','update-parts.json','complete.json',*[f'delivery-{i}.json' for i in range(len(parts))]]:
 p=R/'runs/initial'/name;assert p.exists();entries.append({'path':str(p),'role':'current_receipt','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
m.save(R/'artifact-index.json',{'status':'DURABLE_VERIFIED','entries':entries});m.save(R/'inventory.json',{'request_id':m.REQUEST,'runner':x['runner'],'wrapper':x['wrapper'],'account_id':m.AID,'thread_id':m.TID,'scheduler_job_id':j['id'],'state':x['state'],'artifact_index':str(R/'artifact-index.json')})
if not (R/'report-infra-result.txt').exists():
 out=subprocess.run([str(B/'scripts/send-report-infra-embed.sh'),'--action','criada','--type','script/data/cron','--path',str(R)+'; '+x['runner']+'; '+x['wrapper'],'--reason','Pedido Joe '+m.REQUEST+': CPR e ROI Mavroa07 cada30min somente26nov; coorte fixa criadas hoje ate13h19EST; sem writes Meta/SB; nao altera enrollment Intraday anterior','--evidence',f'{qa["tests_run"]} testes verdes +3 casos classificacao baseline; {len(snap["rows"])}campanhas inicial GET; wrapper dryrun/initial/replay/scheduled silencioso validados; auditoria global pre/pos sem conflito operacional; {len(x["slots"])}slots '+x['slots'][0]+' a '+x['slots'][-1]+'; expira '+x['expires_at']+'; job '+j['id']+' enabled no_agent local'],capture_output=True,text=True,timeout=120,check=True);(R/'report-infra-result.txt').write_text(out.stdout)
match=re.search(r'message_id=(\d+)',(R/'report-infra-result.txt').read_text());assert match;mid=match.group(1);obj=dc.call('GET','/channels/1498132022634483894/messages/'+mid);assert obj['id']==mid and not obj.get('content') and obj['embeds'] and not obj['mentions'];m.save(R/'report-infra-readback.json',{'id':mid,'content_empty':True,'mentions':0,'embeds':len(obj['embeds']),'get_verified':True})
print(json.dumps(result,ensure_ascii=False))
