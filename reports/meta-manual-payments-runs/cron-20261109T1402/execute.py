import json,sys,os,subprocess,shutil
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());g.load_env()
assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod'and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['private_key'];t=g.service_account_access_token()
s,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,capabilities',t,quota_project='mgs-core-prod');assert s==200 and d['capabilities']['canEdit'];
s,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert s==200
assert not(B/'baseline.json').exists();(B/'baseline.json').write_text(json.dumps(book,ensure_ascii=False));(B/'baseline.json').chmod(0o600)
(B/'active-execution.json').write_text(json.dumps({'job_id':'2ee720363d7d','scheduled_at':'2026-11-09T14:02:00-05:00','started_at':datetime.now().astimezone().isoformat(),'pid':os.getpid(),'accounts':47,'payment_authorized':False}))
ph={}
for name,args in [('regroup_funding',['--apply']),('refresh_september_invoices',['--apply']),('refresh_workbook',['--apply','--allow-history-pending']),('publish_pay_now',['--prepare'])]:
 r=subprocess.run([sys.executable,str(B/'run.py'),str(S/(name+'.py'))]+args,capture_output=True,text=True,timeout=240)
 (B/(name+'-stdout.txt')).write_text(r.stdout);(B/(name+'-stderr.txt')).write_text(r.stderr)
 d=json.loads(r.stdout.strip().splitlines()[-1]);ph[name]=d;(B/'phases.json').write_text(json.dumps(ph,ensure_ascii=False,indent=2));print(name,json.dumps(d,ensure_ascii=False),flush=True);assert r.returncode==0 and d.get('status')!='blocked'
