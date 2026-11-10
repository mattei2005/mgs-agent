import json,sys,os,subprocess,shutil,sqlite3,fcntl
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;B.chmod(0o700);H=Path('/root/mgs-agent/data/meta-manual-payments');S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());g.load_env()
assert c['month_since']=='2026-11-01' and len(set(c['account_ids']))==47 and c['payments_authorized'] is False
assert all(os.getenv(k)=='service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['private_key'];t=g.service_account_access_token()
s,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,capabilities',t,quota_project='mgs-core-prod');assert s==200 and d['capabilities']['canEdit']
s,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert s==200
assert not (B/'baseline.json').exists();(B/'baseline.json').write_text(json.dumps(book,ensure_ascii=False));(B/'baseline.json').chmod(0o600)
con=sqlite3.connect('file:/root/.hermes/profiles/zeus/cron/executions.db?mode=ro',uri=True);con.row_factory=sqlite3.Row
active=[dict(x)for x in con.execute("select * from executions where job_id='2ee720363d7d' and status in ('claimed','running')")];assert len(active)==1 and active[0]['id']=='93702f3a63194551847c33c25d19e6e4';(B/'active-execution.json').write_text(json.dumps(active))
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
cua_backend._cua_configured_ax_max_elements=lambda:2400
session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id',c['thread_id'],'--ttl','300'],capture_output=True,text=True);assert r.returncode==0,'pc1_busy'
try:
 for mode in ['ax','vision']:
  raw=handle_computer_use({'action':'capture','mode':mode,'pid':19372,'window_id':328816},session_id=session);d=json.loads(raw)if isinstance(raw,str)else raw;assert not d.get('error');(B/('surface-initial-'+mode+'.json')).write_text(json.dumps(d))
  if d.get('elements_file'):shutil.copy2(d['elements_file'],B/'surface-initial-elements.json')
  if mode=='vision':shutil.copy2(d['screenshot_path'],B/'surface-initial.png')
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True)
print(json.dumps({'status':'preflight_pass','baseline':str(B/'baseline.json'),'screenshot':str(B/'surface-initial.png'),'active_execution':active[0]['id']}))
