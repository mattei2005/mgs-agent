import os,sys,json,shutil,subprocess,time
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400;cua_backend._computer_use_max_image_dimension=lambda:3200
B=Path(__file__).parent;s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';bind=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text());r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True);assert r.returncode==0,'lease_busy'
def call(x):
 d=handle_computer_use(x,session_id=s);return json.loads(d) if isinstance(d,str) else d
def cap():
 d=call({'action':'capture','mode':'ax','pid':bind['pid'],'window_id':bind['window_id']});assert not d.get('error');full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d;return full,full['elements']
def tabs(es):return [e for e in es if e.get('role')=='TabItem' and e.get('bounds',[0,99999])[1]<50]
def label(e):return e.get('label','').split(' - Memory usage')[0]
try:
 initial=tabs(json.loads((B/'native-navigation-baseline.json').read_text())['elements']);full,es=cap();(B/'cleanup-before.json').write_text(json.dumps(full,ensure_ascii=False));current=tabs(es);assert [label(t) for t in current[:len(initial)]]==[label(t) for t in initial];assert len(current)-len(initial)==2;assert [label(t)for t in current[len(initial):]]==['New Tab','Meta Business Suite']
 while len(current)>len(initial):
  owned=current[-1];x,y,w,h=owned['bounds'];close=[e for e in es if e.get('role')=='Button' and e.get('label')=='Close' and x<=e.get('bounds',[99999])[0]<x+w and e.get('bounds',[0,99999])[1]<50];assert len(close)==1;old=len(current);r=call({'action':'click','element':close[0]['index']});assert r.get('ok') and not r.get('error') and not r.get('code');time.sleep(1);full,es=cap();current=tabs(es);assert len(current)==old-1
 assert [label(t)for t in current]==[label(t)for t in initial];(B/'cleanup-after.json').write_text(json.dumps(full,ensure_ascii=False));print(json.dumps({'status':'owned_tabs_closed_original_prefix_preserved','original_tabs':len(initial),'final_tabs':len(current),'closed_owned_tabs':2,'unrelated_save_dialog_untouched':True}))
finally:
 release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)
