import os,sys,json,shutil,subprocess,time,re
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400;cua_backend._computer_use_max_image_dimension=lambda:3200
B=Path(__file__).parent;s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';bind=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text())
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True);assert r.returncode==0,'lease_busy'
def call(x):
 d=handle_computer_use(x,session_id=s);return json.loads(d) if isinstance(d,str) else d
def cap():
 d=call({'action':'capture','mode':'ax','pid':bind['pid'],'window_id':bind['window_id']});assert not d.get('error');full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d;return full,full.get('elements',[])
def action(x):
 r=call(x);assert r.get('ok') is True and not r.get('code') and not r.get('error');return r
def tabs(es):return [e for e in es if e.get('role')=='TabItem' and e.get('bounds',[0,99999])[1]<50]
try:
 ws=json.loads(subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=45).stdout)['windows'];assert not any(w.get('app_name')=='CredentialUIBroker.exe' for w in ws),'native_auth_dialog_present'
 full,es=cap();text='\n'.join(e.get('label','') for e in es);assert 'Rodolfo' in text and not re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you',text,re.I)
 original=tabs(es);(B/'native-navigation-baseline.json').write_text(json.dumps(full,ensure_ascii=False));buttons=[e for e in es if e.get('role')=='Button' and e.get('label')=='New Tab'];assert len(buttons)==1;action({'action':'click','element':buttons[0]['index']});time.sleep(1)
 full,es=cap();assert len(tabs(es))==len(original)+1 and tabs(es)[-1]['label'].startswith('New Tab'),'new_tab_not_confirmed'
 edits=[e for e in es if e.get('role')=='Edit' and e.get('label')=='Address and search bar'];assert len(edits)==1
 action({'action':'set_value','element':edits[0]['index'],'value':'https://business.facebook.com/latest/billing_hub/accounts/?business_id=155263197283282'});action({'action':'key','keys':'return','delivery_mode':'foreground','bring_to_front':True})
 for i in range(20):
  time.sleep(2);full,es=cap();text='\n'.join(e.get('label','') for e in es if e.get('role')!='TabItem')
  if re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you|Log in to Facebook',text,re.I) or ('Accounts' in text and any(e.get('role')=='Edit' and e.get('label')=='Search' for e in es)):break
 (B/'native-navigation-elements.json').write_text(json.dumps(full,ensure_ascii=False));v=call({'action':'capture','mode':'vision','pid':bind['pid'],'window_id':bind['window_id']});assert v.get('screenshot_path');shutil.copy2(v['screenshot_path'],B/'native-navigation.png')
 print(json.dumps({'screenshot':str(B/'native-navigation.png'),'authentication_gate':bool(re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you|Log in to Facebook',text,re.I)),'accounts_search':any(e.get('role')=='Edit' and e.get('label')=='Search' for e in es),'original_tab_count':len(original),'current_tab_count':len(tabs(es)),'owned_tab_left_open_for_current_run':True}))
finally:
 release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)
