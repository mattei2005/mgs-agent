import sys,os,json,shutil,subprocess
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R));from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
B=Path(__file__).parent;label=sys.argv[1];session=os.environ['HERMES_SESSION_ID'];L='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
r=subprocess.run([sys.executable,L,'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','180'],capture_output=True,text=True);assert r.returncode==0
try:
 surface=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text())
 for mode in ['ax','vision']:
  d=handle_computer_use({'action':'capture','mode':mode,**{k:surface[k]for k in ['pid','window_id']}},session_id=session);d=json.loads(d)if isinstance(d,str)else d
  assert not d.get('error');(B/(label+'-'+mode+'.json')).write_text(json.dumps(d,ensure_ascii=False));
  if d.get('elements_file'):shutil.copy2(d['elements_file'],B/(label+'-elements.json'))
  if d.get('screenshot_path'):shutil.copy2(d['screenshot_path'],B/(label+'.png'))
 print(json.dumps({'status':'captured','screenshot':str(B/(label+'.png')),'elements':str(B/(label+'-elements.json'))}))
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,L,'release','--agent','zeus','--session-id',session],capture_output=True)
