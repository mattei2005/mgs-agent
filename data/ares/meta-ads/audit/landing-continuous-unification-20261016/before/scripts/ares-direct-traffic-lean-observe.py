#!/usr/bin/env python3
"""One normal-tab lean observation under the existing queue and PC1 lease."""
import argparse,asyncio,importlib.util,json,os,shutil,subprocess,sys,time,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_lean import open_normal,close_normal,scroll_owned,structured_visual,VISUAL_PROMPT,lean_enabled
from ares_campaign_v3.landing_reliability import run_directory

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['key','owner','pc1-session-id','url','mapping-source']:p.add_argument('--'+name,required=True)
 p.add_argument('--index',type=int,required=True);a=p.parse_args()
 if not lean_enabled():raise ValueError('Lean route not approved')
 if a.pc1_session_id!=os.environ.get('HERMES_SESSION_ID'):raise ValueError('Actual runtime session required')
 q=core.Queue();j=q.owned(a.key,a.owner);link=j['payload']['links'][a.index]
 from ares_campaign_v3.landing_lean import observation_url,tracking_query_matches
 a.url=observation_url(a.url)
 source=urllib.parse.urlsplit(link['effective_campaign_url']);target=urllib.parse.urlsplit(a.url)
 if source.hostname!=target.hostname or not tracking_query_matches(target.query,source.query) or '/quiz/' in target.path or '/chat/' in target.path:raise ValueError('Exact prepared landing/query required')
 if link.get('landing_url') and observation_url(link['landing_url'])!=a.url:raise ValueError('Frozen landing differs')
 core.scope(a.url)
 lock=core.BASE/'scripts/mgs-pc1-computer-use-lock.py'
 def lease(action):
  r=subprocess.run([sys.executable,str(lock),action,'--agent','ares','--session-id',a.pc1_session_id]+(['--ttl','900','--thread-id',j['payload']['source_thread_id']] if action=='acquire' else []),capture_output=True,text=True,timeout=20)
  if r.returncode:raise ValueError('PC1 busy/unavailable')
 lease('acquire')
 executable=shutil.which('hermes')
 if not executable:raise ValueError('Hermes runtime unavailable')
 sys.path.insert(0,str(Path(executable).resolve().parents[2]))
 from tools.computer_use import tool as ct
 from tools.vision_tools import vision_analyze_tool
 spec=importlib.util.spec_from_file_location('lean_capture',core.BASE/'scripts/ares-direct-traffic-sample.py');assert spec and spec.loader
 sampler=importlib.util.module_from_spec(spec);spec.loader.exec_module(sampler)
 def call(args):
  r=ct.handle_computer_use(args,session_id=a.pc1_session_id);return json.loads(r) if isinstance(r,str) else r
 proof=None;begun=False;safe_to_release=True
 e:dict=dict(observation_mode='LEAN_NORMAL_NEW_TAB',observed_url=a.url,resolved_landing_url=a.url,mapping_source=a.mapping_source)
 result='ERROR';error=None
 try:
  q.begin(a.key,a.owner,a.index);begun=True;j=q.job(a.key)
  directory=run_directory(q,a.owner,a.key,a.index,j['links'][a.index]['attempt']);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
  def persist(value):
   nonlocal proof;proof=value
   (directory/'normal-open.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
  safe_to_release=False
  proof=open_normal(call,a.url,persist);e['normal_opening']=proof;e['opened_at']=proof['opened_at']
  visual=None
  for reread in range(2):
   shot=sampler.capture_screen(ct,a.pc1_session_id)
   if not shot.get('screenshot_path'):raise ValueError('Minimal visual read missing')
   visual=structured_visual(asyncio.run(vision_analyze_tool(shot['screenshot_path'],VISUAL_PROMPT)))
   if all(visual[k] for k in ['active_normal_chrome','unobstructed','landing_loaded']):break
   if reread==0:time.sleep(1)
  if not visual or not all(visual[k] for k in ['active_normal_chrome','unobstructed','landing_loaded']):raise ValueError('Landing not loaded/foreground; not NO_AD')
  e.update(visual=visual,network_ad_confirmed=visual['network_ad_visible'],ad_description=visual['description'],visual_review=visual['description'])
  if visual['network_ad_visible']:
   e['scroll_result']=scroll_owned(call,proof['target'])
   e['observation_started_at']=time.time();t=time.monotonic();time.sleep(10);e['visible_seconds']=time.monotonic()-t;e['observation_ended_at']=time.time();result='PASS'
  else:result='NO_AD'
 except Exception as exc:error=type(exc).__name__+': '+str(exc)[:180];e['diagnosis']=error
 finally:
  try:
   if proof and proof.get('new_window_created'):
    closure=close_normal(call,proof);safe_to_release=True;e.update(closure);e.setdefault('normal_opening',proof);e.setdefault('opened_at',proof.get('opened_at',proof.get('opened_intent_at',time.time())))
   elif begun and proof is None:safe_to_release=True;e.update(no_tab_opened=True,browser_inputs_zero_verified=True)
   if begun:
    (directory/'lean-result.json').write_text(json.dumps(dict(result=result,evidence=e),ensure_ascii=False,indent=2));q.result(a.key,a.owner,a.index,result,e)
  finally:
   ct.release_computer_use_session(a.pc1_session_id)
   if safe_to_release:lease('release')
 return {'state':q.job(a.key)['state'],'result':result,'diagnosis':error,'screenshot_series':False}
if __name__=='__main__':
 try:print(json.dumps(main(),ensure_ascii=False))
 except Exception as exc:print(json.dumps({'state':'RECOVERY_REQUIRED','reason':type(exc).__name__+': '+str(exc)[:180]},ensure_ascii=False));sys.exit(1)
