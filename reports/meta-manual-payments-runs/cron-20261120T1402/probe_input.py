import os,sys,json,shutil,subprocess,time
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
B=Path(__file__).parent;session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
p=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','240'],capture_output=True,text=True);assert p.returncode==0,'lease_busy'
def call(args):
 raw=handle_computer_use(args,session_id=session);return json.loads(raw) if isinstance(raw,str) else raw
try:
 binding=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text())
 args={'action':'capture','pid':binding['pid'],'window_id':binding['window_id'],'mode':'ax'}
 d=call(args);assert not d.get('error');es=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d
 labels='\n'.join(e.get('label','') for e in es.get('elements',[]))
 assert not any(v.lower() in labels.lower() for v in ['Windows Security','If you don\'t have a passkey','Confirm it\'s you','temporarily blocked']), 'gate'
 assert 'Rodolfo' in labels and 'Accounts' in labels
 # Diagnose one read-only search-field interaction, no tab navigation or closing.
 ss=[e for e in es['elements'] if e.get('role') in ['Edit','TextField','SearchBox'] and e.get('label')=='Search'];assert len(ss)==1
 x,y,w,h=ss[0]['bounds'];assert 0<x<x+w<=d['width']+4 and 0<y<y+h<=d['height']+4
 for i,a in enumerate([{'action':'click','coordinate':[round(x+min(180,w/2)),round(y+h/2)],'delivery_mode':'foreground','bring_to_front':True},{'action':'type','text':'Openzed-US-CC-EN-01','delivery_mode':'foreground'}]):
  r=call(a);(B/f'input-action-{i}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({'step':i,**{k:r.get(k) for k in ['ok','action','error','code','effect','verified','delivery_mode','verdict','message','meta']}}),flush=True)
  assert not r.get('error') and r.get('ok') is not False and not r.get('code')
  time.sleep(1)
 time.sleep(5);d=call(args);(B/'probe-after.json').write_text(json.dumps(d,ensure_ascii=False));es=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d;(B/'probe-after-elements.json').write_text(json.dumps(es,ensure_ascii=False));v=call({**args,'mode':'vision'});shutil.copy2(v['screenshot_path'],B/'probe-after.png');print(json.dumps({'screenshot':str(B/'probe-after.png'),'search':[e for e in es.get('elements',[]) if e.get('label')=='Search'],'matches':[e['label'] for e in es.get('elements',[]) if e.get('role')=='DataItem' and '336562339356179' in e.get('label','')]}))
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
