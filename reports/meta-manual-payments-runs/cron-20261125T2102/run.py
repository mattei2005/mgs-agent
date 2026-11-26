import os,sys,json,shutil,subprocess,runpy,re,fcntl
from pathlib import Path
from datetime import datetime
os.umask(0o077)
B=Path(__file__).parent
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts');H=Path('/root/mgs-agent/data/meta-manual-payments')
def save(name,d):
 p=B/name
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
 p.chmod(0o600)
def job():return next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs'] if x['id']=='2ee720363d7d')
if sys.argv[1]=='preflight':
 c=json.loads((H/'digital-trust-workbook-contract.json').read_text());assert c['recurring_scope']['mode']=='active_tab_only' and not c['balance_views']['enabled'] and c['sheet_id']==794137639 and set(c['account_ids'])==set(c['recurring_scope']['account_ids']) and c['business_id']=='155263197283282' and not c['payments_authorized'];save('contract-before.json',c)
 j=job();assert j['last_dispatch']['scheduled_at']=='2026-11-25T21:02:00-05:00' and j['fire_claim']['by'];save('job-before.json',j)
 with (H/'writer.lock').open('a') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
 g.load_env();assert all(os.getenv(k)=='service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
 sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['private_key'];t=g.service_account_access_token()
 for name,url in [('drive-before.json','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,name,capabilities,trashed'),('workbook-before.json','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true')]:
  st,d=g.api_json('GET',url,t,quota_project='mgs-core-prod');assert st==200
  if name.startswith('drive'):assert d['capabilities']['canEdit'] and not d.get('trashed')
  save(name,d)
 print(json.dumps({'status':'preflight_pass','accounts':len(c['account_ids']),'h_targets':len(c['pay_now_account_ids']),'all_tabs_baseline':True}))
elif sys.argv[1]=='surface':
 os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
 from tools.computer_use_tool import handle_computer_use,release_computer_use_session
 from tools.computer_use import cua_backend
 cua_backend._computer_use_max_image_dimension=lambda:3200;cua_backend._cua_configured_ax_max_elements=lambda:2400
 session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';p=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True)
 if p.returncode:save('surface-lease-busy.json',json.loads(p.stdout));raise RuntimeError('pc1_lease_busy')
 try:
  binding=json.loads((H/'pc1-browser-surface.json').read_text());w=subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=45);assert w.returncode==0;windows=json.loads(w.stdout)['windows'];candidates=[x for x in windows if 'chrome' in str(x.get('app_name','')).lower() or 'credential' in str(x.get('app_name','')).lower()]
  save('window-discovery.json',[{'pid':x['pid'],'window_id':x['window_id'],'minimized':x.get('minimized'),'approved_handle':x['pid']==binding['pid'] and x['window_id']==binding['window_id'],'save_dialog':str(x.get('title','')).lower() in ['save as','salvar como'],'native_credential':'credential' in str(x.get('app_name','')).lower()} for x in candidates]);assert sum(x['pid']==binding['pid'] and x['window_id']==binding['window_id'] for x in candidates)==1,'approved_chrome_not_live'
  args={'action':'capture','pid':binding['pid'],'window_id':binding['window_id'],'mode':'ax'};raw=handle_computer_use(args,session_id=session);d=json.loads(raw) if isinstance(raw,str) else raw;assert not d.get('error');save('surface.json',d);es=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d;save('surface-elements.json',es)
  raw=handle_computer_use({**args,'mode':'vision'},session_id=session);v=json.loads(raw) if isinstance(raw,str) else raw;pic=v.get('screenshot_path');assert pic and Path(pic).is_file();shutil.copy2(pic,B/'surface.png')
  labels='\n'.join(x.get('label','') for x in es.get('elements',[]));print(json.dumps({'screenshot':str(B/'surface.png'),'pid':binding['pid'],'window_id':binding['window_id'],'profile_rodolfo':'Rodolfo' in labels,'passkey_gate':bool(re.search(r'If you don.t have a passkey for Facebook|security/twofactor/reauth|Confirm it.s you',labels,re.I)),'native_gate':'Windows Security' in labels,'accounts':'Accounts' in labels,'windows':json.loads((B/'window-discovery.json').read_text())}))
 finally:release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
elif sys.argv[1]=='worker':
 name=sys.argv[2];sys.argv=[str(S/name)]+sys.argv[3:];runpy.run_path(str(S/name),run_name='__main__')
