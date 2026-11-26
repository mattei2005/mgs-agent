import os,sys,json,shutil,subprocess,re
from pathlib import Path
os.umask(0o077)
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
B=Path(__file__).parent;s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id','1563926766286803004','--ttl','180'],capture_output=True,text=True);assert r.returncode==0,'lease_busy'
try:
 w=json.loads(subprocess.run(['scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=60,check=True).stdout)['windows']
 safe=[{k:x.get(k) for k in ['pid','window_id','app_name','is_on_screen','minimized']} for x in w]
 (B/'desktop-discovery.json').write_text(json.dumps(safe))
 candidates=[x for x in w if x.get('app_name','').lower()=='lockapp.exe'];assert len(candidates)==1
 x=candidates[0]
 out={'windows':safe,'chrome_windows':sum('chrome' in x.get('app_name','').lower() for x in w),'native_credential_windows':sum('credential' in x.get('app_name','').lower() for x in w)}
 for mode in ['ax','vision']:
  raw=handle_computer_use({'action':'capture','mode':mode,'pid':x['pid'],'window_id':x['window_id']},session_id=s);d=json.loads(raw) if isinstance(raw,str) else raw
  (B/('lockapp-'+mode+'.json')).write_text(json.dumps(d))
  if d.get('screenshot_path'):
   shutil.copy2(d['screenshot_path'],B/('lockapp-'+mode+'.png'));out[mode+'_screenshot']=str(B/('lockapp-'+mode+'.png'))
  if d.get('elements_file'):shutil.copy2(d['elements_file'],B/'lockapp-elements.json')
  out[mode+'_ok']=d.get('ok');out[mode+'_error']=d.get('error');out[mode+'_code']=d.get('code')
 print(json.dumps(out))
finally:
 release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)
