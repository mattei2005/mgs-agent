import os,sys,json,subprocess,time,re,shutil
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400;cua_backend._computer_use_max_image_dimension=lambda:3200
B=Path(__file__).parent;bind=json.loads(Path('data/meta-manual-payments/pc1-browser-surface.json').read_text());s=os.environ['HERMES_SESSION_ID'];lock='scripts/mgs-pc1-computer-use-lock.py';phase=sys.argv[1];tag=sys.argv[2];out=B/('owned-h-'+tag);out.mkdir(exist_ok=True)
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True);assert r.returncode==0,'pc1_lease_busy'
def call(x):
 d=handle_computer_use(x,session_id=s);return json.loads(d)if isinstance(d,str)else d
def cap(name):
 d=call({'action':'capture','mode':'ax','pid':bind['pid'],'window_id':bind['window_id']});assert not d.get('error');f=json.loads(Path(d['elements_file']).read_text())if d.get('elements_file')else d;(out/(name+'.json')).write_text(json.dumps(f,ensure_ascii=False));es=f.get('elements',[]);text='\n'.join(e.get('label','')for e in es if e.get('role')!='ListItem');assert not re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you|temporarily blocked|going too fast|Log in to Facebook',text,re.I),'native_or_provider_gate';return es,text
def tabs(es):return[e for e in es if e.get('role')=='TabItem'and e.get('bounds',[0,99999])[1]<50]
def act(x):
 d=call(x);assert d.get('ok')is True and not d.get('code')and not d.get('error');return d
def pic(name):
 d=call({'action':'capture','mode':'vision','pid':bind['pid'],'window_id':bind['window_id']});assert d.get('screenshot_path');shutil.copy2(d['screenshot_path'],out/(name+'.png'))
try:
 pic('initial');es,text=cap('initial')
 if phase=='open':
  original=tabs(es);(out/'original-tabs.json').write_text(json.dumps(original));nb=[e for e in es if e.get('role')=='Button'and e.get('label')=='New Tab'];assert len(nb)==1,'new_tab_button_missing';act({'action':'click','element':nb[0]['index']});time.sleep(1);es,text=cap('new-tab');assert len(tabs(es))==len(original)+1,'new_tab_not_created';fs=[e for e in es if e.get('role')=='Edit'and e.get('label')=='Address and search bar'];assert len(fs)==1
  url='https://business.facebook.com/latest/billing_hub/accounts/?business_id=155263197283282';act({'action':'set_value','element':fs[0]['index'],'value':url});es,text=cap('address-filled');act({'action':'key','keys':'return','delivery_mode':'foreground','bring_to_front':True});deadline=time.monotonic()+65
  while True:
   es,text=cap('ready');
   if 'Accounts'in text and 'Rodolfo'in text and any(e.get('role')=='Edit'and e.get('label')=='Search'for e in es):break
   assert time.monotonic()<deadline,'accounts_not_ready';time.sleep(2)
  assert not any(e.get('label','').startswith('Clear Name contains ')for e in es),'unexpected_filter';pic('ready');print(json.dumps({'status':'owned_accounts_blank_ready','tabs_before':len(original),'tabs_now':len(tabs(es)),'screenshot':str(out/'ready.png')}))
 elif phase=='submit':
  url='https://business.facebook.com/latest/billing_hub/accounts/?business_id=155263197283282';assert any(e.get('role')=='ListItem'and e.get('label','').startswith(url+',')for e in es),'expected_url_suggestion_missing';act({'action':'key','keys':'return','delivery_mode':'foreground','bring_to_front':True});time.sleep(5);es,text=cap('submitted');pic('submitted');print(json.dumps({'status':'submitted','screenshot':str(out/'submitted.png')}))
 elif phase=='close':
  original=json.loads((out/'original-tabs.json').read_text());tt=tabs(es)
  norm=lambda e:e.get('label','').split(' - Memory usage')[0]
  assert [norm(t)for t in tt[:len(original)]]==[norm(t)for t in original],'prefix_changed';assert 1<=len(tt)-len(original)<=2,'ambiguous_tab_count';assert all(t.get('label','').startswith(('Meta Business Suite','New Tab'))for t in tt[len(original):]),'ambiguous_tab_identity'
  while len(tt)>len(original):
   t=max(tt,key=lambda e:e['bounds'][0]);x,y,w,h=t['bounds'];cl=[e for e in es if e.get('role')=='Button'and e.get('label')=='Close'and x<=e.get('bounds',[99999])[0]<x+w and e.get('bounds',[0,99999])[1]<50];assert len(cl)==1;old=len(tt);act({'action':'click','element':cl[0]['index']});time.sleep(1);es,text=cap('closed');tt=tabs(es);assert len(tt)==old-1
  print(json.dumps({'status':'owned_tabs_closed','original_tabs_preserved':True,'tabs':len(tt)}))
finally:
 release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)
