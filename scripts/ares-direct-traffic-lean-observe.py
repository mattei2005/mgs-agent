#!/usr/bin/env python3
"""Single-item compatibility CLI; same mechanical core as continuous batches."""
from __future__ import annotations
import argparse,asyncio,importlib.util,json,os,shutil,subprocess,sys,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_lean import observe_prepared,observation_url,tracking_query_matches,VISUAL_PROMPT,lean_enabled
from ares_campaign_v3.landing_mobile import MOBILE_PROMPT
from ares_campaign_v3.landing_reliability import run_directory

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['key','owner','pc1-session-id','url','mapping-source']:p.add_argument('--'+name,required=True)
    p.add_argument('--index',type=int,required=True);a=p.parse_args()
    if not lean_enabled() or a.pc1_session_id!=os.environ.get('HERMES_SESSION_ID'):raise ValueError('active lean route and actual runtime session required')
    q=core.Queue();j=q.owned(a.key,a.owner);link=j['payload']['links'][a.index];a.url=observation_url(a.url)
    source=urllib.parse.urlsplit(link['effective_campaign_url']);target=urllib.parse.urlsplit(a.url)
    if source.hostname!=target.hostname or not tracking_query_matches(target.query,source.query) or core.re.search(r'/(quiz|chat)(/|$)',target.path,core.re.I):raise ValueError('exact prepared landing/query required')
    if link.get('landing_url') and observation_url(link['landing_url'])!=a.url:raise ValueError('frozen landing differs')
    core.scope(a.url);executable=shutil.which('hermes')
    if not executable:raise ValueError('Hermes runtime unavailable')
    sys.path.insert(0,str(Path(executable).resolve().parents[2]))
    from tools.computer_use import tool as ct
    from tools.vision_tools import vision_analyze_tool
    spec=importlib.util.spec_from_file_location('single_capture',core.BASE/'scripts/ares-direct-traffic-sample.py');assert spec and spec.loader
    sampler=importlib.util.module_from_spec(spec);spec.loader.exec_module(sampler)
    lock=core.BASE/'scripts/mgs-pc1-computer-use-lock.py';leased=False;safe=True
    def lease(action):
        r=subprocess.run([sys.executable,str(lock),action,'--agent','ares','--session-id',a.pc1_session_id]+(['--ttl','900','--thread-id',j['payload']['source_thread_id']] if action=='acquire' else []),capture_output=True,text=True,timeout=20)
        if r.returncode:raise ValueError('PC1 busy/unavailable')
    def call(args):
        r=ct.handle_computer_use(args,session_id=a.pc1_session_id);return json.loads(r) if isinstance(r,str) else r
    def read_visual():
        shot=sampler.capture_screen(ct,a.pc1_session_id)
        if not shot.get('screenshot_path'):raise ValueError('minimal visual read missing')
        return asyncio.run(vision_analyze_tool(shot['screenshot_path'],VISUAL_PROMPT))
    def capture_visual():return sampler.capture_screen(ct,a.pc1_session_id)
    def review_visual(shot):return asyncio.run(vision_analyze_tool(shot['screenshot_path'],VISUAL_PROMPT))
    def read_mobile():return asyncio.run(vision_analyze_tool(capture_visual()['screenshot_path'],MOBILE_PROMPT))
    try:
        lease('acquire');leased=True;q.begin(a.key,a.owner,a.index);j=q.job(a.key)
        directory=run_directory(q,a.owner,a.key,a.index,j['links'][a.index]['attempt']);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        def persist(value):(directory/'normal-open.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
        safe=False;result,e=observe_prepared(call,read_visual,a.url,a.mapping_source,on_owned=persist,read_mobile=read_mobile,capture_visual=capture_visual,review_visual=review_visual)
        safe=e.get('tab_closed_verified') is True or (e.get('no_tab_opened') is True and e.get('browser_inputs_zero_verified') is True)
        (directory/'lean-result.json').write_text(json.dumps({'result':result,'evidence':e},ensure_ascii=False,indent=2));q.result(a.key,a.owner,a.index,result,e)
        return {'state':q.job(a.key)['state'],'result':result,'screenshot_series':False}
    finally:
        ct.release_computer_use_session(a.pc1_session_id)
        if leased and safe:lease('release')

if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False))
    except Exception as exc:print(json.dumps({'state':'RECOVERY_REQUIRED','reason':str(exc)[:180]},ensure_ascii=False));sys.exit(1)
