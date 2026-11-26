import os,sys,json,shutil,subprocess,time
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400;cua_backend._computer_use_max_image_dimension=lambda:3200
B=Path(__file__).parent;s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';bind=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text())
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True);assert not r.returncode,'lease_busy'
def call(x):
 d=handle_computer_use(x,session_id=s);return json.loads(d) if isinstance(d,str) else d
def capture():
 d=call({'action':'capture','mode':'ax','pid':bind['pid'],'window_id':bind['window_id']});assert not d.get('error');return json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d
try:
 d=capture();(B/'reload-before-elements.json').write_text(json.dumps(d));e=d.get('elements',[]);assert not any('Windows Security' in x.get('label','') for x in e)
 choices=[x for x in e if x.get('role')=='Button' and x.get('label')=='Reload page'];print('reload_matches',len(choices));assert len(choices)==1
 r=call({'action':'click','element':choices[0]['index']});assert r.get('ok') is True and not r.get('error') and not r.get('code');time.sleep(10)
 d=capture();(B/'reload-after-elements.json').write_text(json.dumps(d));v=call({'action':'capture','mode':'vision','pid':bind['pid'],'window_id':bind['window_id']});shutil.copy2(v['screenshot_path'],B/'reload-after.png');print(json.dumps({'screenshot':str(B/'reload-after.png'),'accounts':any(x.get('label')=='Accounts' for x in d.get('elements',[]))}))
finally:
 release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)
