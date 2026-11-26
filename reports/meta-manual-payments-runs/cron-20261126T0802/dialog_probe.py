import sys,os,json,shutil,subprocess
from pathlib import Path
B=Path(__file__).parent;R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id','1563926766286803004','--ttl','180'],capture_output=True,text=True);assert not r.returncode
try:
 windows=json.loads(subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,check=True,timeout=45).stdout)['windows'];matches=[w for w in windows if str(w.get('title','')).lower() in ['save as','salvar como']];assert len(matches)==1
 w=matches[0];raw=handle_computer_use({'action':'capture','mode':'vision','pid':w['pid'],'window_id':w['window_id']},session_id=s);d=json.loads(raw) if isinstance(raw,str) else raw;assert not d.get('error') and d.get('screenshot_path');shutil.copy2(d['screenshot_path'],B/'save-dialog.png');(B/'save-dialog.png').chmod(0o600)
 p={'pid':w['pid'],'window_id':w['window_id'],'screenshot':str(B/'save-dialog.png'),'input_actions':0,'tabs_created':0,'tabs_closed':0,'verified_at':__import__('datetime').datetime.now().astimezone().isoformat()};(B/'dialog-probe.json').write_text(json.dumps(p,indent=2));print(json.dumps(p))
finally:
 release_computer_use_session(s);r=subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True);assert not r.returncode
