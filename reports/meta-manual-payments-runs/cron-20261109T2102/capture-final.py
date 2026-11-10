import sys,os,json,subprocess,shutil
from pathlib import Path
B=Path(__file__).parent;os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._computer_use_max_image_dimension=lambda:3200
cua_backend._cua_configured_ax_max_elements=lambda:2400
session=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py'
r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','180'],capture_output=True,text=True);assert r.returncode==0,'pc1_busy'
try:
 for mode in ['ax','vision']:
  raw=handle_computer_use({'action':'capture','mode':mode,'pid':19372,'window_id':328816},session_id=session);d=json.loads(raw)if isinstance(raw,str)else raw;assert not d.get('error');(B/('surface-final-'+mode+'.json')).write_text(json.dumps(d))
  if d.get('elements_file'):shutil.copy2(d['elements_file'],B/'surface-final-elements.json')
  if mode=='vision':shutil.copy2(d['screenshot_path'],B/'surface-final.png')
 d=json.loads((B/'surface-final-elements.json').read_text());labels=[x.get('label','')for x in d.get('elements',[])];gate={'status':'blocked_native_auth_surface_conflict_no_input','native_windows_security_ax':any(x=='Windows Security'for x in labels),'approved_profile_rodolfo_ax':any('Rodolfo'in x for x in labels),'pid':19372,'window_id':328816,'initial_screenshot':str(B/'surface-initial.png'),'final_screenshot':str(B/'surface-final.png'),'keyboard_mouse_input':0,'owned_tabs_created':0,'h_fresh_count':0,'human_action':'Concluir ou fechar pessoalmente o diálogo Windows Security no PC1 e deixar a janela Meta disponível; não há prova de logout global Meta.'};assert gate['native_windows_security_ax'];(B/'ui-blocker.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2));print(json.dumps(gate,ensure_ascii=False))
finally:
 release_computer_use_session(session);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True)
