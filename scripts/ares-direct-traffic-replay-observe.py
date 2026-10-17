#!/usr/bin/env python3
"""One explicitly authorized replay, separate from immutable original validation."""
import argparse,asyncio,importlib.util,json,os,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_lean import observe_prepared,VISUAL_PROMPT,observation_url
from ares_campaign_v3.landing_mobile import MOBILE_PROMPT
from ares_campaign_v3.landing_batch import validate_mapping


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',type=Path,required=True);p.add_argument('--pc1-session-id',required=True);a=p.parse_args()
    if a.pc1_session_id!=os.environ.get('HERMES_SESSION_ID'):raise ValueError('actual runtime session required')
    q=core.Queue();s=json.loads(a.scope.read_text());core.identifier(s['authority_message_id'])
    if s.get('authority_user_id')!='344196393512075265' or s.get('authority_thread_id')!=core.INCIDENT_THREAD or s.get('maximum_visits')!=1:raise ValueError('exact one-visit Rodolfo replay authority required')
    j=q.job(s['job']);idx=s['index'];before=j['links'][idx]
    if j['state']!='COMPLETE' or before['state'] not in {'PASSED','RESOLVED_BY_OPERATOR'}:raise ValueError('replay only for an already terminal target')
    if s.get('payload_digest')!=j['digest']:raise ValueError('immutable original request differs')
    item=validate_mapping(q,s);item['url']=observation_url(item['url']);round_id='mobile-replay:'+s['authority_message_id']
    for row in q.db.execute("SELECT detail FROM events WHERE job=? AND kind='explicit_replay_result'",(s['job'],)):
        d=json.loads(row['detail'])
        if d.get('round_id')==round_id:return dict(state='REPLAY_ALREADY_RECORDED',result=d['result'],evidence_file=d['evidence_file'])
    if any(json.loads(r['detail']).get('round_id')==round_id for r in q.db.execute("SELECT detail FROM events WHERE job=? AND kind='explicit_replay_started'",(s['job'],))):raise ValueError('existing replay needs reconciliation; no second visit')
    if q.db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','RECONCILING','REPAIRING','NEEDS_RECONCILIATION','WAITING_HUMAN_UNCLOSED')").fetchone():return {'state':'WAITING_EXISTING_OBSERVER','browser_actions':0}
    sys.path.insert(0,str(Path(shutil.which('hermes')).resolve().parents[2]));from tools.computer_use import tool as ct
    from tools.vision_tools import vision_analyze_tool
    spec=importlib.util.spec_from_file_location('replay_capture',core.BASE/'scripts/ares-direct-traffic-sample.py');sampler=importlib.util.module_from_spec(spec);spec.loader.exec_module(sampler)
    lock=core.BASE/'scripts/mgs-pc1-computer-use-lock.py';safe=True;leased=False;directory=a.scope.parent/'replay';directory.mkdir(exist_ok=True)
    def lease(action):
        args=[sys.executable,str(lock),action,'--agent','ares','--session-id',a.pc1_session_id]
        if action=='acquire':args+=['--ttl','900','--thread-id',core.INCIDENT_THREAD]
        r=subprocess.run(args,capture_output=True,text=True,timeout=20)
        if r.returncode:raise ValueError('physical PC1 unavailable')
    def call(args):
        r=ct.handle_computer_use(args,session_id=a.pc1_session_id);return json.loads(r) if isinstance(r,str) else r
    def capture_visual():return sampler.capture_screen(ct,a.pc1_session_id)
    def review_visual(shot):return asyncio.run(vision_analyze_tool(shot['screenshot_path'],VISUAL_PROMPT))
    def read_visual():return review_visual(capture_visual())
    def read_mobile():return asyncio.run(vision_analyze_tool(capture_visual()['screenshot_path'],MOBILE_PROMPT))
    try:
        lease('acquire');leased=True
        with q.tx():q.event(s['job'],'explicit_replay_started',{'round_id':round_id,'idx':idx,'authority_message_id':s['authority_message_id'],'maximum_visits':1,'original_state_preserved':before['state']})
        safe=False
        result,e=observe_prepared(call,read_visual,item['url'],item['mapping_source'],on_owned=lambda v:(directory/'normal-open.json').write_text(json.dumps(v,indent=2)),read_mobile=read_mobile,capture_visual=capture_visual,review_visual=review_visual)
        safe=e.get('tab_closed_verified') is True or (e.get('no_tab_opened') is True and e.get('browser_inputs_zero_verified') is True)
        if result in {'PASS','NO_AD'}:
            from ares_campaign_v3.landing_lean import validate_lean_observation
            validate_lean_observation(e,j['payload']['links'][idx],negative=result=='NO_AD')
        e=core.preserve_evidence(e,'replay-'+s['authority_message_id'],idx,1)
        output=directory/'result.json';output.write_text(json.dumps({'round_id':round_id,'result':result,'evidence':e},ensure_ascii=False,indent=2))
        with q.tx():q.event(s['job'],'explicit_replay_result',{'round_id':round_id,'idx':idx,'result':result,'evidence_file':str(output),'original_state_preserved':True,'original_attempt_count_preserved':before['attempt']})
        after=q.job(s['job']);assert after['state']==j['state'] and after['links'][idx]==before
        return {'state':'REPLAY_RECORDED','result':result,'evidence_file':str(output),'tab_closed_verified':e.get('tab_closed_verified'),'tab_open_seconds':e.get('tab_open_seconds'),'mobile':e.get('mobile_emulation'),'original_history_unchanged':True}
    finally:
        ct.release_computer_use_session(a.pc1_session_id)
        if leased and safe:lease('release')

if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False))
    except Exception as exc:print(json.dumps({'state':'REPLAY_RECOVERY_REQUIRED','reason':type(exc).__name__+': '+str(exc)[:160]}));sys.exit(1)
