#!/usr/bin/env python3
"""Continuous prepared landing batch. All diagnostic stdout stays local."""
from __future__ import annotations
import argparse,asyncio,importlib.util,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3 import landing_batch as batch
from ares_campaign_v3.landing_lean import observe_prepared,observation_url,VISUAL_PROMPT
from ares_campaign_v3.landing_mobile import MOBILE_PROMPT
from ares_campaign_v3.landing_reliability import run_directory


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',type=Path,required=True);p.add_argument('--owner',required=True);p.add_argument('--manifest',type=Path);p.add_argument('--pc1-session-id',required=True)
    a=p.parse_args()
    if a.pc1_session_id!=os.environ.get('HERMES_SESSION_ID'):raise ValueError('real runtime session required')
    q=core.Queue();scope=json.loads(a.scope.read_text());batch.validate_scope(q,scope,a.owner)
    if a.manifest:batch.store_manifest(q,scope,json.loads(a.manifest.read_text()),a.owner)
    prepared=batch.cached_manifest(q,scope,a.owner)
    if prepared['missing']:return {'state':'MAPPING_REQUIRED','missing':prepared['missing'],'browser_actions':0}
    # Validate every URL before acquiring desktop or navigating the first item.
    for item in prepared['items']:batch.validate_mapping(q,item)
    executable=shutil.which('hermes')
    if not executable:raise ValueError('Hermes runtime unavailable')
    sys.path.insert(0,str(Path(executable).resolve().parents[2]))
    from tools.computer_use import tool as ct
    from tools.vision_tools import vision_analyze_tool
    spec=importlib.util.spec_from_file_location('batch_capture',core.BASE/'scripts/ares-direct-traffic-sample.py');assert spec and spec.loader
    sampler=importlib.util.module_from_spec(spec);spec.loader.exec_module(sampler)
    lock=core.BASE/'scripts/mgs-pc1-computer-use-lock.py';leased=False;safe=True;stop=False
    deadline=min(float(scope.get('deadline',time.time()+10500)),time.time()+10500)
    def pause(*unused):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGINT,pause);signal.signal(signal.SIGTERM,pause)
    def lease(action):
        r=subprocess.run([sys.executable,str(lock),action,'--agent','ares','--session-id',a.pc1_session_id]+(['--thread-id',core.INCIDENT_THREAD,'--ttl','900'] if action=='acquire' else ['--ttl','900'] if action=='renew' else []),capture_output=True,text=True,timeout=20)
        if r.returncode:raise ValueError('PC1 lease busy/unavailable')
    def call(args):
        result=ct.handle_computer_use(args,session_id=a.pc1_session_id);return json.loads(result) if isinstance(result,str) else result
    def read_visual():
        shot=sampler.capture_screen(ct,a.pc1_session_id)
        if not shot.get('screenshot_path'):raise ValueError('minimal visual read missing')
        return asyncio.run(vision_analyze_tool(shot['screenshot_path'],VISUAL_PROMPT))
    def capture_visual():return sampler.capture_screen(ct,a.pc1_session_id)
    def review_visual(shot,prompt=VISUAL_PROMPT):return asyncio.run(vision_analyze_tool(shot['screenshot_path'],prompt))
    def read_mobile():return asyncio.run(vision_analyze_tool(capture_visual()['screenshot_path'],MOBILE_PROMPT))
    def execute(item,attempt):
        nonlocal safe
        directory=run_directory(q,a.owner,item['job'],item['index'],attempt);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        def save_open(value):
            (directory/'normal-open.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
        safe=False
        result,e=observe_prepared(call,read_visual,observation_url(item['url']),item['mapping_source'],on_owned=save_open,read_mobile=read_mobile,capture_visual=capture_visual,review_visual=review_visual)
        safe=e.get('tab_closed_verified') is True or (e.get('no_tab_opened') is True and e.get('browser_inputs_zero_verified') is True)
        (directory/'lean-result.json').write_text(json.dumps({'result':result,'evidence':e,'batch_scope':scope['id']},ensure_ascii=False,indent=2))
        return result,e
    try:
        try:lease('acquire');leased=True
        except ValueError:
            first=q.job(scope['first_job'])
            if first['state']=='RUNNING' and first['owner']==a.owner:q.deferred(first['key'],a.owner)
            return {'state':'WAITING_PC1','browser_actions':0}
        return batch.run(q,scope,a.owner,execute,before_attempt=lambda:lease('renew'),should_stop=lambda:stop or time.time()>=deadline)
    finally:
        # One backend release at the END, not a5s teardown between every URL.
        ct.release_computer_use_session(a.pc1_session_id)
        if leased and safe:lease('release')


if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False))
    except Exception as exc:print(json.dumps({'state':'BATCH_RECOVERY_REQUIRED','reason':str(exc)[:180]},ensure_ascii=False));sys.exit(1)
