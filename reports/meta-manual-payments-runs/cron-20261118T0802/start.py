import os,sys,json,fcntl,subprocess
from pathlib import Path
from datetime import datetime
B=Path(__file__).resolve().parent;os.chmod(B,0o700);sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_finance_continuity import read_workbook
import mgs_google_workspace_auth as g
from mgs_automation_continuity import Queue,native_contract_hash
c=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json').read_text());j=next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs']if x['id']==c['cron_job_id'])
assert j['last_dispatch']['scheduled_at']=='2026-11-18T08:02:00-05:00' and j['fire_claim'] and j['origin']['user_id']=='344196393512075265' and j['origin']['thread_id']==c['thread_id']
assert len(c['account_ids'])==len(set(c['account_ids']))==55 and c['h_source']=='accounts_list_outstanding_balance' and c['business_id']=='155263197283282' and c['payments_authorized'] is False
q=Queue();active=[{'key':x['key'],'state':x['state'],'owner':x['owner']}for x in q.open()if x['state']=='running' and json.loads(x['source']).get('job_id')==j['id']];assert not active,active
for name,data in [('job-before',j),('contract-before',c)]:
 p=B/(name+'.json');assert not p.exists();p.write_text(json.dumps(data,ensure_ascii=False,indent=2));os.chmod(p,0o600)
g.load_env();sa=g.load_service_account();assert (sa['project_id'],sa['client_email'])==('mgs-core-prod','mgsagent@mgs-core-prod.iam.gserviceaccount.com') and sa.get('private_key')
t=g.service_account_access_token();code,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,name,capabilities,trashed',t,quota_project='mgs-core-prod');assert code==200 and d['capabilities']['canEdit'] and not d['trashed']
with open('/root/mgs-agent/data/meta-manual-payments/writer.lock','a')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);book=read_workbook(c);assert not(B/'workbook-before.json').exists();(B/'workbook-before.json').write_text(json.dumps(book,ensure_ascii=False));(B/'drive-before.json').write_text(json.dumps(d));fcntl.flock(f,fcntl.LOCK_UN)
net=json.loads(subprocess.run(['tailscale','status','--json'],capture_output=True,text=True,check=True,timeout=20).stdout);peer=next(v for v in net['Peer'].values()if v.get('HostName','').lower()=='pc1')
r=subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=50)
probe={'at':datetime.now().astimezone().isoformat(),'self_online':net['Self']['Online'],'pc1_online':peer['Online'],'ssh_returncode':r.returncode,'ssh_timeout':'timed out' in r.stderr.lower(),'auth_gate_observed':False}
(B/'network-preflight.json').write_text(json.dumps(probe,indent=2));(B/'preflight.json').write_text(json.dumps({'status':'google_baseline_pass_pc1_unavailable'if r.returncode else 'pc1_discovery_available','sheets':len(book['sheets']),'canonical_sa':True,'canEdit':True,'sheets_http':200,'active_finance_recovery':active,'contract_hash':native_contract_hash(j)},indent=2))
if r.returncode==0:
 windows=json.loads(r.stdout).get('windows',[]);print(json.dumps({'status':'pc1_available','windows':[{'pid':w.get('pid'),'window_id':w.get('window_id'),'chrome':'chrome'in str(w.get('app_name','')).lower()}for w in windows]}))
else:print(json.dumps({'status':'prewrite_baseline_saved_pc1_offline','sheets':len(book['sheets']),'probe':probe}))
