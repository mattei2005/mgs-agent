"""Read-only capture diagnosis after failed AX, preserve all inputs."""
import os,sys,json,subprocess,shutil,hashlib
from pathlib import Path
from datetime import datetime,timezone
os.umask(0o077)
B=Path(__file__).parent; ROOT=Path('/root/mgs-agent')
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']=str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh')
os.environ['MGS_CONTINUITY_OPERATION_KEY']='79cd082a20c22a736307765f'
session='recovery-79cd082a-round97-capture';os.environ['HERMES_SESSION_ID']=session
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400
cua_backend._computer_use_max_image_dimension=lambda:3200
def save(n,d):
 with (B/n).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
lock=ROOT/'scripts/mgs-pc1-computer-use-lock.py'
def lease(action):
 args=[sys.executable,str(lock),action]
 if action!='status':args+=['--agent','zeus','--session-id',session]
 if action=='acquire':args+=['--thread-id','1563926766286803004','--ttl','240']
 r=subprocess.run(args,capture_output=True,text=True,timeout=20)
 return r.returncode,json.loads(r.stdout)
rc,d=lease('acquire');save('retry-lease-acquire.json',d)
if rc:print(json.dumps(d));sys.exit(0)
try:
 r=subprocess.run([str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh'),'call','list_windows'],capture_output=True,text=True,timeout=50);assert r.returncode==0
 windows=json.loads(r.stdout)['windows'];bind=json.loads((ROOT/'data/meta-manual-payments/pc1-browser-surface.json').read_text())
 approved=[w for w in windows if w['pid']==bind['pid'] and w['window_id']==bind['window_id']];assert len(approved)==1
 import re
 dialogs=[w for w in windows if re.search('Save As|Salvar como',w.get('title',''),re.I)]
 save('retry-window-discovery.json',[{'pid':w['pid'],'window_id':w['window_id'],'approved':w in approved,'save_as_dialog':w in dialogs,'minimized':w.get('minimized')} for w in windows])
 captures={};errors=[]
 for label,w in [('approved',approved[0])]+[(f'save-dialog-{i}',w) for i,w in enumerate(dialogs)]:
  for mode in ['ax','vision']:
   raw=handle_computer_use({'action':'capture','mode':mode,'pid':w['pid'],'window_id':w['window_id']},session_id=session)
   d=json.loads(raw) if isinstance(raw,str) else raw
   save(label+'-'+mode+'-response.json',d)
   if d.get('error'):
    errors.append({'label':label,'mode':mode,'error':d['error']});print(json.dumps(errors[-1]));continue
   if mode=='ax':
    full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d;save(label+'-retry-elements.json',full)
   if d.get('screenshot_path'):
    dest=B/(label+'-retry-'+mode+'.png');shutil.copy2(d['screenshot_path'],dest)
    captures[label+'-'+mode]={'pid':w['pid'],'window_id':w['window_id'],'screenshot':str(dest),'width':d.get('width'),'height':d.get('height')}
 result={'observed_at':datetime.now(timezone.utc).isoformat(),'captures':captures,'errors':errors,'save_dialog_count':len(dialogs),'input_actions':0,'tabs_created':0,'tabs_closed':0}
 save('retry-probe-receipt.json',result);print(json.dumps(result))
finally:
 release_computer_use_session(session)
 rc,d=lease('release');_,s=lease('status');save('retry-lease-release.json',{'release_exit':rc,'release':d,'readback':s})
