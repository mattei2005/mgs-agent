import os,json,sys,shutil,subprocess,contextlib
from pathlib import Path
B=Path(__file__).resolve().parent
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
a=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True);assert a.returncode==0,a.stdout
try:
 with open(B/'capture-startup.log','w') as sink,contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
  from tools.computer_use_tool import handle_computer_use,release_computer_use_session
  from tools.computer_use import cua_backend
  cua_backend._computer_use_max_image_dimension=lambda:3200
  raw=handle_computer_use({'action':'capture','mode':'vision','pid':22596,'window_id':131572},session_id=session)
 d=json.loads(raw)if isinstance(raw,str)else raw;assert not d.get('error'),d.get('error');assert d.get('screenshot_path');shutil.copy2(d['screenshot_path'],B/'initial.png');print(json.dumps({'screenshot':str(B/'initial.png'),'width':d.get('width'),'height':d.get('height')}))
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
