import json,os,sys,subprocess,pathlib,runpy
B=pathlib.Path(__file__).parent
H=pathlib.Path('/root/mgs-agent/data/meta-manual-payments')
S=pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
launcher=pathlib.Path(subprocess.check_output(['which','hermes'],text=True).strip()).resolve()
R=launcher.parents[2];PY=launcher.read_text().splitlines()[1].split(' -I ',1)[0].removeprefix('exec ')
sys.path.insert(0,str(R));sys.path.insert(0,'/root/mgs-agent/scripts')
from pm.environments import activate_dependencies
activate_dependencies(R)
def save(n,d):
 p=B/n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def worker(name,*args):
 code='import sys,runpy;from pathlib import Path;sys.path.insert(0,'+repr(str(R))+');from pm.environments import activate_dependencies;activate_dependencies(Path('+repr(str(R))+'));sys.argv='+repr([str(S/name),*args])+';runpy.run_path('+repr(str(S/name))+',run_name="__main__")'
 r=subprocess.run([PY,'-c',code],capture_output=True,text=True,timeout=540)
 p=B/(name+'-last-output.txt');p.write_text(r.stdout+'\n'+r.stderr);p.chmod(0o600)
 objs=[]
 for l in r.stdout.splitlines():
  try:objs.append(json.loads(l))
  except ValueError:pass
 print(json.dumps({'worker':name,'exit':r.returncode,'results':objs,'output':str(p)},ensure_ascii=False),flush=True)
 if r.returncode:raise SystemExit(r.returncode)
 return objs[-1] if objs else {}
mode=sys.argv[1]
if mode=='preflight':
 import mgs_google_workspace_auth as g
 g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
 c=json.loads((H/'digital-trust-workbook-contract.json').read_text());save('contract-before.json',c)
 sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod'and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['private_key']
 t=g.service_account_access_token()
 st,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,name,capabilities',t,quota_project='mgs-core-prod');assert st==200 and d['capabilities']['canEdit'];save('drive.json',d)
 st,d=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert st==200;save('baseline.json',d)
 os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
 from tools.computer_use_tool import handle_computer_use,release_computer_use_session
 surface=json.loads((H/'pc1-browser-surface.json').read_text())
 try:
  v=handle_computer_use({'action':'capture','mode':'ax','pid':surface['pid'],'window_id':surface['window_id']},session_id=os.environ['HERMES_SESSION_ID']);v=json.loads(v)if isinstance(v,str)else v;save('surface-ax-receipt.json',v)
  v=handle_computer_use({'action':'capture','mode':'vision','pid':surface['pid'],'window_id':surface['window_id']},session_id=os.environ['HERMES_SESSION_ID']);v=json.loads(v)if isinstance(v,str)else v;save('surface-vision-receipt.json',v);print(json.dumps({'preflight':'google_ok','sheets':len(d['sheets']),'surface':v},ensure_ascii=False))
 finally:release_computer_use_session(os.environ['HERMES_SESSION_ID'])
elif mode=='phases':
 ph={}
 for name in ['regroup_funding','refresh_september_invoices','refresh_workbook','publish_pay_now']:
  args=['--prepare']if name=='publish_pay_now'else ['--apply','--allow-history-pending']if name=='refresh_workbook'else ['--apply']
  ph[name]=worker(name+'.py',*args);save('phases.json',ph)
elif mode=='worker':worker(sys.argv[2],*sys.argv[3:])
