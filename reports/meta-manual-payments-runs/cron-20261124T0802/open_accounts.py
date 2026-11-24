import os,sys,json,shutil,subprocess,time,re
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
cua_backend._cua_configured_ax_max_elements=lambda:2400
B=Path(__file__).parent;bind=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text());s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
def call(a):
 d=handle_computer_use(a,session_id=s);return json.loads(d)if isinstance(d,str)else d
def cap(tag):
 d=call({'action':'capture','mode':'ax','pid':bind['pid'],'window_id':bind['window_id']});assert not d.get('error');full=json.loads(Path(d['elements_file']).read_text())if d.get('elements_file')else d;(B/(tag+'-elements.json')).write_text(json.dumps(full));return full,full.get('elements',[])
def action(a):
 r=call(a);assert r.get('ok')is True and not r.get('code')and not r.get('error');return r
def tabs(es):return[e.get('label','').split(' - Memory usage')[0]for e in es if e.get('role')=='TabItem'and e.get('bounds',[0,99999])[1]<50]
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True);assert r.returncode==0,'lease_busy'
try:
 full,es=cap('native-before');orig=json.loads((B/'surface-elements.json').read_text());assert tabs(es)==tabs(orig.get('elements',[])),'tabs_changed_before_native';text='\n'.join(e.get('label','')for e in es);assert not re.search(r'Windows Security|passkey for Facebook|Confirm it.s you|temporarily blocked',text,re.I)
 new=[e for e in es if e.get('role')=='Button'and e.get('label')=='New Tab'];assert len(new)==1;action({'action':'click','element':new[0]['index']});time.sleep(1);full,es=cap('native-new');assert len(tabs(es))==len(tabs(orig.get('elements',[])))+1
 fields=[e for e in es if e.get('role')=='Edit'and e.get('label')=='Address and search bar'];assert len(fields)==1;url='https://business.facebook.com/latest/billing_hub/accounts/?business_id=155263197283282';action({'action':'set_value','element':fields[0]['index'],'value':url});time.sleep(1);cap('native-address');action({'action':'key','keys':'return','delivery_mode':'foreground','bring_to_front':True});time.sleep(5)
 full,es=cap('native-result');v=call({'action':'capture','mode':'vision','pid':bind['pid'],'window_id':bind['window_id']});shutil.copy2(v['screenshot_path'],B/'native-result.png');text='\n'.join(e.get('label','')for e in es);print(json.dumps({'screenshot':str(B/'native-result.png'),'accounts':'Accounts'in text,'gate':bool(re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you',text,re.I)),'tabs':len(tabs(es))}))
finally:
 release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)
