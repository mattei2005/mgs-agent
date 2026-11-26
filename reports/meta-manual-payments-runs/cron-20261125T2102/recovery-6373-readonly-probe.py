import os,sys,json,shutil,subprocess,re,fcntl,sqlite3
from pathlib import Path
from datetime import datetime
os.umask(0o077)
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
cua_backend._cua_configured_ax_max_elements=lambda:2400
B=Path(__file__).parent/('recovery-6373-'+datetime.now().strftime('%Y%m%dT%H%M%S'));B.mkdir()
C=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json').read_text())
bind=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text())
s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
def save(n,d):
 p=B/n
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def call(x):
 d=handle_computer_use(x,session_id=s);return json.loads(d) if isinstance(d,str) else d
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id',C['thread_id'],'--ttl','180'],capture_output=True,text=True)
if r.returncode:
 save('busy.json',json.loads(r.stdout));print(json.dumps({'status':'waiting_resource','evidence':str(B/'busy.json')}));raise SystemExit(0)
try:
 ws=json.loads(subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,check=True,timeout=45).stdout)['windows']
 safe=[{k:w.get(k) for k in ['pid','window_id','minimized']}|{'save_dialog':str(w.get('title','')).lower() in ['save as','salvar como'],'native_credential':w.get('app_name')=='CredentialUIBroker.exe','approved_handle':w.get('pid')==bind['pid'] and w.get('window_id')==bind['window_id']} for w in ws]
 save('windows.json',safe)
 targets=[('approved',w) for w in ws if w.get('pid')==bind['pid'] and w.get('window_id')==bind['window_id']]+[('save-dialog',w) for w in ws if str(w.get('title','')).lower() in ['save as','salvar como']]
 assert len([x for x in targets if x[0]=='approved'])==1
 res={}
 for name,w in targets:
  d=call({'action':'capture','mode':'ax','pid':w['pid'],'window_id':w['window_id']});assert not d.get('error'),d.get('error')
  full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d;save(name+'-elements.json',full)
  labels='\n'.join(e.get('label','') for e in full.get('elements',[]))
  v=call({'action':'capture','mode':'vision','pid':w['pid'],'window_id':w['window_id']});assert v.get('screenshot_path') and not v.get('error');shutil.copy2(v['screenshot_path'],B/(name+'.png'))
  res[name]={'pid':w['pid'],'window_id':w['window_id'],'screenshot':str(B/(name+'.png')),'elements':str(B/(name+'-elements.json')),'profile_rodolfo':'Rodolfo' in labels,'accounts':'Accounts' in labels,'passkey_or_login_gate':bool(re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you|Log in to Facebook',labels,re.I))}
 save('probe.json',{'operation':'6373afb33275674610c06b6a','at':datetime.now().astimezone().isoformat(),'windows':safe,'captures':res,'input_actions':0,'business_writes':0,'tabs_created':0,'tabs_closed':0})
 print(json.dumps({'evidence':str(B/'probe.json'),'captures':res}))
finally:
 release_computer_use_session(s)
 r=subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True);assert not r.returncode
