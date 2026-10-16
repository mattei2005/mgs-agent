#!/usr/bin/env python3
"""Run the explicitly requested supervised normal-tab replay, sequentially."""
import asyncio,importlib.util,json,os,sys,time,subprocess,signal
from pathlib import Path
PAUSE_REQUESTED=False
OWNED_WINDOW_UNCERTAIN=False
def pause_after_current(*unused):
 global PAUSE_REQUESTED
 PAUSE_REQUESTED=True
signal.signal(signal.SIGINT,pause_after_current)
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_lean import open_normal,close_normal,structured_visual,VISUAL_PROMPT
BASE=Path('/root/mgs-agent');ROUND=BASE/'data/ares/meta-ads/landing-followup/supervised-repeat-20261016-062358'
SID=os.environ['HERMES_SESSION_ID'];THREAD='1559932317861158993'
sys.path.insert(0,'/root/.hermes/hermes-agent-stage-main-7cc3fb8c-mgs')
from tools.computer_use import tool as ct
from tools.vision_tools import vision_analyze_tool
spec=importlib.util.spec_from_file_location('sampler',BASE/'scripts/ares-direct-traffic-sample.py');sampler=importlib.util.module_from_spec(spec);spec.loader.exec_module(sampler)
q=core.Queue(ROUND/'normal-phase');dc=core.Discord()
manifest=json.loads((ROUND/'manifest.json').read_text());statepath=ROUND/'normal-results.json'
state=json.loads(statepath.read_text()) if statepath.exists() else {'authority_message_id':'1560615018133717053','started_at':time.time(),'items':{},'round_complete':False,'manager_notifications':0}
def save():
 p=statepath.with_suffix('.new');p.write_text(json.dumps(state,ensure_ascii=False,indent=2));os.chmod(p,0o600);os.replace(p,statepath)
def lock(action):
 r=subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),action,'--agent','ares','--session-id',SID]+(['--ttl','900'] if action=='renew' else []),capture_output=True,text=True,timeout=20)
 if r.returncode:raise ValueError('PC1 lease unavailable')
 return json.loads(r.stdout)
def call(a):
 r=ct.handle_computer_use(a,session_id=SID);return json.loads(r) if isinstance(r,str) else r
def notice(item,status):
 done=sum(x['state']=='PASS_LEAN' for x in state['items'].values());deferred=sum(x['state'] in ['DEFERRED_NO_AD','REVIEW_REQUIRED'] for x in state['items'].values());processed=sum(x['state'] in ['PASS_LEAN','DEFERRED_NO_AD','REVIEW_REQUIRED'] for x in state['items'].values())
 key='normal-replay:'+str(item['campaign'])+':'+status
 content=(f"**Rodada supervisionada — campanha {item['campaign']}**\n"+('✅ Anúncio identificado · rolagem · 10 segundos · aba normal fechada.' if status=='PASS_LEAN' else '⚠️ Sem anúncio após as tentativas; aba fechada e próximos links liberados.')+f'\n✅ Concluídos com anúncio: **{done}/33** · ⏳ Ainda não processados: **{33-processed}** · para retorno/revisão: **{deferred}**.\n🔄 Uma aba NOVA normal por tentativa. Avisos somente aqui.')
 with q.tx():
  q.prepare_message(key,THREAD,content);q.event(None,'progress_update_authorized',{'notification_key':key,'authority_message_id':'1560613464874029137','per_item':True})
 dc.deliver(q,key)
 print(json.dumps({'campaign':item['campaign'],'state':status,'done':done,'remaining_unprocessed':33-processed,'delivery':'VERIFIED'}),flush=True)
def observe(item):
 global OWNED_WINDOW_UNCERTAIN
 from ares_campaign_v3.landing_lean import observation_url
 item=dict(item,url=observation_url(item['url']))
 lock('renew');proofpath=ROUND/'normal-phase'/f"c{item['campaign']}-attempt{len(state['items'].get(str(item['campaign']),{}).get('attempts',[]))+1}.json"
 proof=None
 def persist(p):
  nonlocal proof;proof=p;proofpath.write_text(json.dumps(p,ensure_ascii=False,indent=2));os.chmod(proofpath,0o600)
 start=time.time();result={'started_at':start,'url':item['url'],'browser_mode':'NORMAL','new_tab_required':True}
 try:
  OWNED_WINDOW_UNCERTAIN=True
  proof=open_normal(call,item['url'],persist)
  visual=None
  # Loading is not ad absence. Re-read the SAME new tab once, without navigation.
  for visual_read in range(2):
   shot=sampler.capture_screen(ct,SID)
   if not shot.get('screenshot_path'):raise ValueError('Minimal visual read absent')
   raw=asyncio.run(vision_analyze_tool(shot['screenshot_path'],VISUAL_PROMPT))
   visual=structured_visual(raw);result['visual']=visual
   if visual['active_normal_chrome'] and visual['unobstructed'] and visual['landing_loaded']:break
   if visual_read==0:time.sleep(1)
  if not visual or not visual['active_normal_chrome'] or not visual['unobstructed'] or not visual['landing_loaded']:raise ValueError('Loaded foreground normal landing not confirmed; never NO_AD')
  found=visual['network_ad_visible']
  if found:
   from ares_campaign_v3.landing_lean import scroll_owned
   scroll=scroll_owned(call,proof['target'])
   t=time.monotonic();time.sleep(10);result['dwell_seconds']=time.monotonic()-t
  result['result']='PASS_LEAN' if found else 'NO_AD'
 finally:
  if proof and proof.get('new_window_created'):
   result['closure']=close_normal(call,proof);OWNED_WINDOW_UNCERTAIN=False
  elif proof is None:OWNED_WINDOW_UNCERTAIN=False
  ct.release_computer_use_session(SID)
  result['ended_at']=time.time();result['elapsed_seconds']=result['ended_at']-start
  proofpath.with_name(proofpath.stem+'-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return result
save()
try:
 for item in manifest:
  if PAUSE_REQUESTED:state['paused_after_current']=True;save();break
  key=str(item['campaign']);record=state['items'].setdefault(key,{'state':'READY','attempts':[]})
  if record['state'] in ['PASS_LEAN','DEFERRED_NO_AD','REVIEW_REQUIRED']:continue
  core.scope(item['url'])
  while sum(a.get('result')=='NO_AD' for a in record['attempts'])<3:
   if PAUSE_REQUESTED:record['state']='READY';save();break
   record['state']='OPENING';save()
   try:r=observe(item)
   except Exception as exc:
    failed_path=ROUND/'normal-phase'/f"c{item['campaign']}-attempt{len(record['attempts'])+1}-result.json"
    failed=json.loads(failed_path.read_text()) if failed_path.exists() else {}
    if not (failed.get('closure') or {}).get('tab_closed_verified'):record['state']='NEEDS_RECONCILIATION';record['error']=str(exc)[:180];save();raise
    failed.update(result='ERROR',diagnosis=str(exc)[:180]);record['attempts'].append(failed)
    if sum(a.get('result')=='ERROR' for a in record['attempts'])>=3:
     record['state']='TECHNICAL_REPAIR';record['error']=str(exc)[:180];save();break
    save();continue
   record['attempts'].append(r);save()
   if r['result']=='PASS_LEAN':record['state']='PASS_LEAN';save();notice(item,'PASS_LEAN');break
  else:record['state']='DEFERRED_NO_AD';save();notice(item,'DEFERRED_NO_AD')
 for item in manifest:
  if PAUSE_REQUESTED:break
  record=state['items'].get(str(item['campaign']))
  if not record or record['state']!='DEFERRED_NO_AD':continue
  r=observe(item);record['attempts'].append(r);record['state']='PASS_LEAN' if r['result']=='PASS_LEAN' else 'REVIEW_REQUIRED';save();notice(item,record['state'])
 state['round_complete']=all(r['state'] in ['PASS_LEAN','REVIEW_REQUIRED'] for r in state['items'].values()) and len(state['items'])==len(manifest);state['completed_at']=time.time();save()
 print(json.dumps({'round_complete':state['round_complete'],'states':{s:sum(r['state']==s for r in state['items'].values()) for s in set(r['state'] for r in state['items'].values())}}),flush=True)
finally:
 if not OWNED_WINDOW_UNCERTAIN:lock('release')
