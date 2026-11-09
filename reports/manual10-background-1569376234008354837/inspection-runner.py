import os,sys,json,shutil,time,contextlib,argparse,re,subprocess
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--start',type=int,default=0);P.add_argument('--count',type=int,default=4);a=P.parse_args()
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
with open(os.devnull,'w') as sink,contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
 from pm.environments import activate_dependencies
 activate_dependencies(R)
 os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
 from tools.computer_use_tool import handle_computer_use,release_computer_use_session
 from tools.computer_use import cua_backend
 cua_backend._cua_configured_ax_max_elements=lambda:3000
 cua_backend._computer_use_max_image_dimension=lambda:1920
SID=os.environ['HERMES_SESSION_ID'];B=Path('/root/mgs-agent/reports/manual10-background-1569376234008354837');scope=json.load(open(B/'scope.json'));pairs=[(c,ad) for c in scope['campaigns'] for ad in c['ads']]
es=[];last={};pid=wid=None;foreground=set()
def lease():
 r=subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','renew','--agent','zeus','--session-id',SID,'--ttl','1800'],capture_output=True,text=True);assert r.returncode==0,'lease_lost'
def call(x):
 with open(os.devnull,'w') as sink,contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):r=handle_computer_use(x,session_id=SID)
 return json.loads(r) if isinstance(r,str) else r
def cap():
 global es,last
 last=call({'action':'capture','mode':'som','pid':pid,'window_id':wid})
 assert not last.get('error') and (last.get('elements_file') or last.get('elements')),'capture_failed'
 es=json.load(open(last['elements_file']))['elements'] if last.get('elements_file') else last['elements']
 return es
def act(x):
 lease();typ=x['action'];d=call({**x,**({'delivery_mode':'foreground'} if typ in foreground else {})})
 if d.get('code')=='background_unavailable':
  cap();foreground.add(typ)
  if 'element' in x:raise RuntimeError('recapture_requires_semantic_retry')
  d=call({**x,'delivery_mode':'foreground'})
 assert not d.get('error') and not d.get('code'),str(d.get('code') or d.get('error'))
 return d
def shot(name):
 p=last.get('screenshot_path');assert p and Path(p).is_file(),'screenshot_missing'
 dst=B/name;shutil.copy2(p,dst)
 (B/(name+'.json')).write_text(json.dumps({'elements':es,'width':last.get('width'),'height':last.get('height')},ensure_ascii=False,indent=2))
 return str(dst)
def nav(url):
 lease();act({'action':'key','keys':'ctrl+l'});time.sleep(.2);cap()
 ee=[e for e in es if e.get('role')=='Edit' and e.get('label')=='Address and search bar'];assert len(ee)==1
 act({'action':'set_value','element':ee[0]['index'],'value':url});cap();act({'action':'key','keys':'return'});time.sleep(4)
def heading():
 hs=[e for e in es if e.get('label')=='Advantage+ creative enhancements'];return hs[0] if len(hs)==1 else None
def find_buttons(label):return [e for e in es if e.get('role')=='Button' and e.get('label')==label]
def close_modal():
 cap();bs=find_buttons('Cancel')
 if len(bs)==1:
  act({'action':'click','element':bs[0]['index']});time.sleep(.6);cap();assert not find_buttons('Cancel'),'modal_not_closed'
def click_feature_edit():
 if heading() and heading()['bounds'][1]>1800:
  act({'action':'key','keys':'ctrl+end'});time.sleep(.3);cap()
 for k in range(10):
  h=heading();assert h,'enhancement_heading_missing';y=h['bounds'][1]
  bs=[e for e in find_buttons('Edit') if e.get('bounds') and y-20<=e['bounds'][1]<y+180]
  assert len(bs)==1,'section_edit_not_unique'
  by=bs[0]['bounds'][1]
  if 220<=y and by<1200:
   return bs[0]
  amount=min(100,max(3,round(abs(y-520)/10.5)));direction='down' if y>520 else 'up'
  act({'action':'scroll','direction':direction,'amount':amount,'coordinate':[1200,1000]});time.sleep(.5);cap()
  new=heading()
  if new and abs(new['bounds'][1]-y)<2:
   act({'action':'scroll','direction':direction,'amount':amount,'coordinate':[1200,1000],'delivery_mode':'foreground'});time.sleep(.5);cap();new=heading();assert new and abs(new['bounds'][1]-y)>2,'scroll_noop'
 raise RuntimeError('section_scroll_limit')
try:
 ws=[w for w in call({'action':'list_windows'}).get('windows',[]) if w.get('app_name','').lower()=='chrome.exe'];assert len(ws)==1
 pid=ws[0]['pid'];wid=ws[0]['window_id']
 for index in range(a.start,min(a.start+a.count,len(pairs))):
  c,ad=pairs[index];out=B/(ad['id']+'-inspection.json')
  if out.exists() and json.load(open(out)).get('inspection_complete'):continue
  lease();close_modal();nav('https://adsmanager.facebook.com/adsmanager/manage/ads/edit?act='+c['account_id']+'&selected_ad_ids='+ad['id'])
  deadline=time.monotonic()+45;ready=False
  while time.monotonic()<deadline:
   cap();text='\n'.join(e.get('label','') for e in es)
   if re.search(r'^Windows Security$|Log in to Facebook|Confirm it.s you|authentication app',text,re.I|re.M):raise RuntimeError('authentication_gate')
   identity=any(e.get('role')=='Hyperlink' and ' '.join(e.get('label','').split())==' '.join(c['name'].split()) for e in es)
   adname=any(e.get('role')=='ComboBox' and e.get('label')==ad['name'] for e in es)
   previews=[e for e in es if e.get('role')=='Button' and e.get('label','').startswith('Advanced preview')]
   if identity and adname and (heading() or len(previews)==1):ready=True;break
   time.sleep(1)
  assert ready,'exact_editor_or_section_not_ready'
  top=shot(ad['id']+'-editor-top.png')
  if heading():
   route='Edit ad -> Ad creative -> Advantage+ creative enhancements Edit -> full panel'
   btn=click_feature_edit();section=shot(ad['id']+'-section-edit.png')
   act({'action':'click','element':btn['index']});time.sleep(1);cap()
  else:
   route='Edit ad; enhancements section not exposed -> Advanced preview -> Advantage+ creative tab -> full panel'
   section=shot(ad['id']+'-section-not-exposed.png')
   previews=[e for e in es if e.get('role')=='Button' and e.get('label','').startswith('Advanced preview')];assert len(previews)==1
   act({'action':'click','element':previews[0]['index']});time.sleep(.6);cap()
   tabs=[e for e in es if e.get('role')=='TabItem' and e.get('label')=='Advantage+ creative']
   if not tabs:
    # The prior capture verified the background invocation did not open it.
    previews=[e for e in es if e.get('role')=='Button' and e.get('label','').startswith('Advanced preview')];assert len(previews)==1
    act({'action':'click','element':previews[0]['index'],'delivery_mode':'foreground'});time.sleep(1);cap()
    tabs=[e for e in es if e.get('role')=='TabItem' and e.get('label')=='Advantage+ creative']
   assert len(tabs)==1,'preview_tab_missing'
   act({'action':'click','element':tabs[0]['index']});time.sleep(.6);cap()
  if not find_buttons('Cancel'):
   # Inspect fresh state before escalating a verified no-op.
   h=heading();assert h
   bs=[e for e in find_buttons('Edit') if e.get('bounds') and h['bounds'][1]-20<=e['bounds'][1]<h['bounds'][1]+180];assert len(bs)==1
   act({'action':'click','element':bs[0]['index'],'delivery_mode':'foreground'});time.sleep(1);cap()
  assert find_buttons('Cancel'),'enhancement_modal_not_open'
  deadline=time.monotonic()+25
  while time.monotonic()<deadline:
   controls=[e for e in es if e.get('role') in ['Button','CheckBox'] and e.get('bounds') and e['bounds'][1]>=350 and e.get('label') not in ['Close','Close \u200b','Save','Cancel','Tab search','New Tab']]
   if any(e.get('label') in ['Add overlays','Visual touch-ups','Add music','Text improvements','Add animation','Generate backgrounds','Background generation'] for e in controls):break
   time.sleep(1);cap()
  assert any(e.get('role')=='TabItem' and e.get('label')=='Advantage+ creative' for e in es),'wrong_modal_not_advantage_creative'
  assert any(e.get('label') in ['Add overlays','Visual touch-ups','Add music','Text improvements','Add animation','Generate backgrounds','Background generation'] for e in controls),'feature_panel_not_populated'
  panel=shot(ad['id']+'-full-panel.png')
  # All labels include below-viewport controls; also capture the lower panel.
  full_labels=[e.get('label','') for e in es];bg=[e for e in es if re.search(r'generate backgrounds|background generation|background variations|gerar.*fundo|gera.{0,5}.*plano de fundo',e.get('label',''),re.I)]
  labels=[{'role':e.get('role'),'label':e.get('label'),'bounds':e.get('bounds')} for e in controls]
  act({'action':'scroll','direction':'down','amount':60,'coordinate':[1200,1050]});time.sleep(.5);cap();bottom=shot(ad['id']+'-panel-lower.png')
  bg2=[e for e in es if re.search(r'generate backgrounds|background generation|background variations|gerar.*fundo|gera.{0,5}.*plano de fundo',e.get('label',''),re.I)]
  matches=bg+bg2
  rec={'index':index,'campaign_id':c['id'],'campaign_name':c['name'],'campaign_number':c['number'],'account':c['account'],'account_id':c['account_id'],'manager':c['manager'],'ad_id':ad['id'],'ad_name':ad['name'],'api_scope_enrollment':'OPT_IN','manual_route':route,'inspection_complete':True,'named_control_found':bool(matches),'background_matches':[{'role':e.get('role'),'label':e.get('label'),'bounds':e.get('bounds')} for e in matches],'panel_controls':labels,'screenshots':{'top':top,'section':section,'panel':panel,'lower':bottom},'no_toggle_save_publish':True}
  close_modal();rec['closed_with_cancel']=True;out.write_text(json.dumps(rec,ensure_ascii=False,indent=2))
  print(json.dumps({'index':index,'campaign':c['number'],'account':c['account'],'ad':ad['name'],'complete':True,'named_control_found':bool(matches)}),flush=True)
except Exception as e:
 try:
  if last.get('screenshot_path'):shot('last-error-screen.png')
 except Exception:pass
 err={'stage':'manual10','error_type':type(e).__name__,'detail':str(e),'index':locals().get('index')};(B/'last-error.json').write_text(json.dumps(err,ensure_ascii=False,indent=2));print(json.dumps(err),flush=True);raise SystemExit(2)
finally:release_computer_use_session(SID)
