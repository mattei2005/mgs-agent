import sys,os,json,subprocess,shutil
from pathlib import Path
B=Path(__file__).parent;R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
cua_backend._cua_configured_ax_max_elements=lambda:2400
session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','180'],capture_output=True,text=True);assert r.returncode==0,'pc1_busy'
try:
 for mode in ['ax','vision']:
  raw=handle_computer_use({'action':'capture','mode':mode,'pid':22596,'window_id':131572},session_id=session);d=json.loads(raw)if isinstance(raw,str)else raw;assert not d.get('error');(B/('surface-final-'+mode+'.json')).write_text(json.dumps(d))
  if mode=='ax':
   if d.get('elements_file'):shutil.copy2(d['elements_file'],B/'surface-final-elements.json')
   else:(B/'surface-final-elements.json').write_text(json.dumps(d))
  if mode=='vision':shutil.copy2(d['screenshot_path'],B/'surface-final.png')
 es=json.loads((B/'surface-final-elements.json').read_text()).get('elements',[])
 assert not any(x.get('label')=='Windows Security'for x in es)
 print(json.dumps({'screenshot':str(B/'surface-final.png'),'native_gate':False,'keyboard_mouse_input':0}))
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True)
