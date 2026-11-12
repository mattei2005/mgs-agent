import json,sys,os,subprocess,shutil,sqlite3
from pathlib import Path
B=Path(__file__).parent;B.chmod(0o700);H=Path('/root/mgs-agent/data/meta-manual-payments')
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());g.load_env()
assert c['month_since']=='2026-11-01' and len(set(c['account_ids']))==47 and c['payments_authorized'] is False
assert all(os.getenv(k)=='service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
con=sqlite3.connect('file:/root/.hermes/profiles/zeus/cron/executions.db?mode=ro',uri=True);con.row_factory=sqlite3.Row
active=[dict(x)for x in con.execute("select * from executions where job_id='2ee720363d7d' and status in ('claimed','running')")];assert not active,'concurrent_scheduled_writer';(B/'active-execution.json').write_text(json.dumps(active))
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
cua_backend._cua_configured_ax_max_elements=lambda:2400
session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id',c['thread_id'],'--ttl','300'],capture_output=True,text=True);assert r.returncode==0,'pc1_busy'
try:
 for mode in ['ax','vision']:
  raw=handle_computer_use({'action':'capture','mode':mode,'pid':22596,'window_id':67360},session_id=session);d=json.loads(raw)if isinstance(raw,str)else raw;assert not d.get('error');(B/('surface-candidate2-'+mode+'.json')).write_text(json.dumps(d))
  if mode=='ax':
   if d.get('elements_file'):shutil.copy2(d['elements_file'],B/'surface-candidate2-elements.json')
   else:(B/'surface-candidate2-elements.json').write_text(json.dumps(d))
  if mode=='vision':shutil.copy2(d['screenshot_path'],B/'surface-candidate2.png')
 es=json.loads((B/'surface-candidate2-elements.json').read_text()).get('elements',[])
 print(json.dumps({'status':'surface_captured','screenshot':str(B/'surface-candidate2.png'),'native_windows_security_ax':any(x.get('label')=='Windows Security'for x in es),'approved_profile_rodolfo_ax':any('Rodolfo'in x.get('label','')for x in es)}),flush=True)
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True)
