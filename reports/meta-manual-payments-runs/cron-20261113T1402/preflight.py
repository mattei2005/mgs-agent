import os,json,sys,shutil,subprocess,contextlib
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;os.chmod(B,0o700)
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
g.load_env();keys=['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'];assert all(os.getenv(k)=='service_account' for k in keys)
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa.get('private_key')
c=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json').read_text());assert len(c['account_ids'])==55 and len(set(c['account_ids']))==55
jobs=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());jobs=jobs if isinstance(jobs,list) else jobs['jobs'];j=next(j for j in jobs if j['id']==c['cron_job_id']);assert j['fire_claim'] and j['last_dispatch']['scheduled_at']=='2026-11-13T14:02:00-05:00'
(B/'job-before.json').write_text(json.dumps(j,ensure_ascii=False,indent=2));(B/'contract-before.json').write_text(json.dumps(c,ensure_ascii=False,indent=2))
lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';session=os.environ['HERMES_SESSION_ID'];a=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id',c['thread_id'],'--ttl','300'],capture_output=True,text=True);assert a.returncode==0,a.stdout
try:
 os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
 with open(B/'cua-startup.log','w') as sink,contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
  from tools.computer_use_tool import handle_computer_use,release_computer_use_session
  from tools.computer_use import cua_backend
  cua_backend._computer_use_max_image_dimension=lambda:3200
  result=handle_computer_use({'action':'capture','mode':'ax','pid':22596,'window_id':131572},session_id=session)
 d=json.loads(result) if isinstance(result,str) else result
 (B/'initial-capture.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));assert not d.get('error'),d.get('error')
 if d.get('elements_file'):shutil.copy2(d['elements_file'],B/'initial-elements.json')
 if d.get('screenshot_path'):shutil.copy2(d['screenshot_path'],B/'initial.png')
 print(json.dumps({'status':'surface_captured','screenshot':str(B/'initial.png'),'width':d.get('width'),'height':d.get('height'),'native_gate':any(e.get('label')=='Windows Security' for e in d.get('elements',[]))}))
finally:
 try:release_computer_use_session(session)
 finally:subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
t=g.service_account_access_token();sid=c['spreadsheet_id'];code,drive=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+sid+'?supportsAllDrives=true&fields=id,name,trashed,capabilities(canEdit)',t,quota_project='mgs-core-prod');assert code==200 and drive['capabilities']['canEdit'] and not drive.get('trashed')
code,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+sid+'?includeGridData=true',t,quota_project='mgs-core-prod');assert code==200
(B/'workbook-before.json').write_text(json.dumps(book,ensure_ascii=False));(B/'drive-before.json').write_text(json.dumps(drive));(B/'preflight.json').write_text(json.dumps({'status':'pass','at':datetime.now().astimezone().isoformat(),'sheets':len(book['sheets']),'canonical_service_account':True,'drive_canEdit':True,'sheets_http':code,'payments_authorized':False},indent=2))
print(json.dumps({'status':'preflight_pass','all_sheets_baseline':len(book['sheets']),'canonical_sa':True,'canEdit':True}))
