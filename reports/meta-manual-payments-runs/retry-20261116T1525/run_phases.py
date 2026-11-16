import sys,json,os,subprocess,shutil
from pathlib import Path
from datetime import datetime
B=Path(__file__).resolve().parent; BASE=Path('/root/mgs-agent');sys.path.insert(0,str(BASE/'scripts'))
import mgs_google_workspace_auth as g
g.load_env();keys=['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'];assert all(os.getenv(k)=='service_account' for k in keys)
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa.get('private_key')
c=json.loads((B/'contract-before.json').read_text());t=g.service_account_access_token();sid=c['spreadsheet_id']
code,drive=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+sid+'?supportsAllDrives=true&fields=id,name,trashed,capabilities(canEdit)',t,quota_project='mgs-core-prod');assert code==200 and drive['capabilities']['canEdit'] and not drive.get('trashed')
code,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+sid+'?includeGridData=true',t,quota_project='mgs-core-prod');assert code==200
assert not (B/'workbook-before.json').exists();(B/'workbook-before.json').write_text(json.dumps(book,ensure_ascii=False));(B/'drive-before.json').write_text(json.dumps(drive))
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts');launch=BASE/'reports/meta-manual-payments-runs/cron-20261116T1402/launch.py'
j=json.loads((B/'job-before.json').read_text());p={'requested_at':datetime.now().astimezone().isoformat(),'source_message_id':'1571982992975597571','job_id':j['id'],'dispatch':j.get('last_dispatch'),'fire_claim':j['fire_claim'],'completed':{}}
assert not (B/'progress.json').exists()
for name,script,args in [('funding','regroup_funding.py',['--apply']),('invoices','refresh_september_invoices.py',['--apply']),('api','refresh_workbook.py',['--apply','--allow-history-pending']),('h_prepare','publish_pay_now.py',['--prepare'])]:
 q=subprocess.run([sys.executable,str(launch),str(S/script),*args],text=True,capture_output=True,timeout=300)
 (B/(name+'.log')).write_text(q.stdout+'\n'+q.stderr)
 try:data=json.loads(q.stdout)
 except Exception:data=json.loads(q.stdout.strip().splitlines()[-1])
 p['completed'][name]={'returncode':q.returncode,'stdout':json.dumps(data,ensure_ascii=False)};(B/'progress.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
 print(json.dumps({'phase':name,'rc':q.returncode,'result':data},ensure_ascii=False),flush=True);assert q.returncode==0,(name,'failed')
