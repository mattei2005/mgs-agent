import os,sys,json,subprocess,shutil,sqlite3,fcntl
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
B=Path(__file__).parent;B.chmod(0o700); H=Path('/root/mgs-agent/data/meta-manual-payments');S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2));p.chmod(0o600)
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());save(B/'contract-before.json',c)
job=next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs']if x['id']==c['cron_job_id']);assert job['fire_claim'] and job['last_dispatch']['scheduled_at']=='2026-11-08T21:02:00-05:00';save(B/'dispatch.json',job)
con=sqlite3.connect('file:/root/.hermes/profiles/zeus/cron/executions.db?mode=ro',uri=True);active=con.execute("select id,status,scheduled_instant from executions where job_id=? and status in ('claimed','running')",(job['id'],)).fetchall();assert len(active)==1;save(B/'active-execution.json',active)
with(H/'writer.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod';t=g.service_account_access_token()
status,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,trashed,capabilities(canEdit)',t,quota_project='mgs-core-prod');assert status==200 and d['capabilities']['canEdit']and not d['trashed']
status,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save(B/'baseline.json',book);print('SA, single writer, Drive canEdit, Sheets baseline PASS',flush=True)
ph={}
for name,args in [('regroup_funding',['--apply']),('refresh_september_invoices',['--apply']),('refresh_workbook',['--apply','--allow-history-pending']),('publish_pay_now',['--prepare'])]:
 r=subprocess.run([sys.executable,str(S/(name+'.py')),*args],capture_output=True,text=True,timeout=550);(B/(name+'-stdout.txt')).write_text(r.stdout);(B/(name+'-stderr.txt')).write_text(r.stderr)
 try:d=json.loads(r.stdout)
 except ValueError:d={'status':'unparsed','returncode':r.returncode}
 ph[name]=d;save(B/'phases.json',ph);print(name,json.dumps(d,ensure_ascii=False),flush=True)
 if r.returncode or d.get('status')=='blocked':sys.exit(2)
