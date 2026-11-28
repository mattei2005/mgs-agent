import os,sys,json,shutil,subprocess,time,re
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R));from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200;cua_backend._cua_configured_ax_max_elements=lambda:2400
B=Path(__file__).parent/'surface-recovered';B.mkdir(mode=0o700,exist_ok=True);bind=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text());session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
def call(a):
 x=handle_computer_use(a,session_id=session);return json.loads(x)if isinstance(x,str)else x
def cap():
 d=call({'action':'capture','mode':'ax',**{k:bind[k]for k in ['pid','window_id']}});assert not d.get('error');e=json.loads(Path(d['elements_file']).read_text())if d.get('elements_file')else d;labels='\n'.join(x.get('label','')for x in e.get('elements',[]));assert not re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you|Log in to Facebook',labels,re.I),'auth_gate';return d,e,labels
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True);assert not r.returncode
try:
 time.sleep(15);d,e,labels=cap();(B/'before-elements.json').write_text(json.dumps(e));print(json.dumps({'error_surface':bool(re.search(r'page isn.t available',labels,re.I)),'accounts':'Accounts' in labels,'buttons':[x.get('label') for x in e.get('elements',[]) if x.get('role')=='Button' and re.search('Reload|Refresh',x.get('label',''),re.I)]}),flush=True)
 matches=[x for x in e['elements']if x.get('role')=='Button'and x.get('label')=='Reload page'];assert len(matches)==1
 action=call({'action':'click','element':matches[0]['index']});assert action.get('ok')and not action.get('error');time.sleep(6)
 for _ in range(10):
  d,e,labels=cap()
  if 'Accounts'in labels and 'Outstanding balance'in labels:break
  time.sleep(3)
 (B/'surface-elements.json').write_text(json.dumps(e));v=call({'action':'capture','mode':'vision',**{k:bind[k]for k in ['pid','window_id']}});shutil.copy2(v['screenshot_path'],B/'surface.png');print(json.dumps({'accounts':'Accounts'in labels,'balance_header':'Outstanding balance'in labels,'screenshot':str(B/'surface.png')}))
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
