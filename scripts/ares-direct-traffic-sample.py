#!/usr/bin/env python3
"""Screenshot batch with optional verified closure of its own new window.
Capture never navigates. Optional closure requires an exact reviewed opening proof.
CAPTURED means cadence evidence only, never confirmation of an ad or PASS.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path


def capture_screen(computer_tool, session_id):
    """Persist real frames now; review them offline, outside the cadence loop.

    The CLI is single-threaded. Scope only the response renderer to this call:
    keep the public handler, lease/approval fences, backend and fresh image save.
    No shared file/config is changed and no visual claim is made here.
    """
    original=computer_tool._should_route_through_aux_vision
    try:
        computer_tool._should_route_through_aux_vision=lambda:False
        out=computer_tool.handle_computer_use({'action':'capture','mode':'vision','app':'screen'},session_id=session_id)
    finally:
        computer_tool._should_route_through_aux_vision=original
    out=json.loads(out) if isinstance(out,str) else out
    # Deferred multimodal responses store the fresh path under meta. Native
    # closure consumers use the normal top-level capture contract.
    image=out.get('screenshot_path') or (out.get('meta') or {}).get('screenshot_path')
    if image:out['screenshot_path']=image
    out['analysis_deferred']=True
    return out


def capture_frame(call):
    for _ in range(2):
        out=call({'action':'capture','mode':'vision','app':'screen'})
        image=out.get('screenshot_path') or (out.get('meta') or {}).get('screenshot_path')
        if image:break
    if not image:raise ValueError('capture failed; no image evidence')
    path=Path(image);epoch=path.stat().st_mtime
    return {'screenshot':str(path),'captured_at':epoch,'monotonic_seconds':time.monotonic()-(time.time()-epoch),
            'analysis':None,'analysis_deferred':out.get('analysis_deferred',False),
            'screen_unchanged':out.get('screen_unchanged',False),'composited_desktop':True}


def collect(capture, *, pause=time.sleep, max_frames=12,max_seconds=45):
    all_frames=[];chain=[];started=time.monotonic()
    for _ in range(max_frames):
        if time.monotonic()-started>max_seconds:break
        try:frame=capture()
        except Exception as exc:
            # Keep prior real frames available for exact-window recovery.
            return {'state':'CAPTURE_ERROR','samples':[],'all_frames':all_frames,'error':str(exc)[:200]}
        all_frames.append(frame)
        if time.monotonic()-started>max_seconds:break
        if chain and not (0 < frame['monotonic_seconds']-chain[-1]['monotonic_seconds'] <= 10
                          and 0 < frame['captured_at']-chain[-1]['captured_at'] <= 12):chain=[]
        chain.append(frame)
        if len(chain)>=3 and chain[-1]['monotonic_seconds']-chain[0]['monotonic_seconds']>=10 and chain[-1]['captured_at']-chain[0]['captured_at']>=10:
            return {'state':'CAPTURED_NOT_PASS','samples':chain,'all_frames':all_frames}
        # Even a fast renderer must leave room for >=10s in twelve frames.
        pause(1)
    return {'state':'CADENCE_NOT_VALIDATED','samples':[],'all_frames':all_frames}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--key',required=True);p.add_argument('--owner',required=True)
    p.add_argument('--pc1-session-id',required=True)
    p.add_argument('--close-owned-window',action='store_true')
    p.add_argument('--exclusive-window-reviewed',action='store_true')
    a=p.parse_args()
    here=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('landing_control',here/'ares-direct-traffic-followup.py')
    assert spec is not None and spec.loader is not None
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    cli.require_pc1_lease(a.pc1_session_id)
    q=cli.Queue();job=q.owned(a.key,a.owner)
    if not any(x['state']=='OPEN_INTENT' for x in job['links']):raise ValueError('existing open intent required; sampler never opens a page')
    executable=shutil.which('hermes')
    if not executable:raise ValueError('Hermes runtime unavailable')
    sys.path.insert(0,str(Path(executable).resolve().parents[2]))
    from tools.computer_use import tool as computer_tool
    release_computer_use_session=computer_tool.release_computer_use_session
    def call(args):
        cli.require_pc1_lease(a.pc1_session_id)
        if args.get('action')=='capture' and args.get('app')=='screen':
            return capture_screen(computer_tool,a.pc1_session_id)
        out=computer_tool.handle_computer_use(args,session_id=a.pc1_session_id)
        return json.loads(out) if isinstance(out,str) else out
    def capture():return capture_frame(call)
    idx=next(x['idx'] for x in job['links'] if x['state']=='OPEN_INTENT')
    from ares_campaign_v3.landing_reliability import run_directory
    directory=run_directory(q,a.owner,a.key,idx,job['links'][idx]['attempt'])
    target=directory/'capture-series.json';target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    def persist(out):
        temp=target.with_suffix('.new');temp.write_text(json.dumps(out,ensure_ascii=False,indent=2));os.chmod(temp,0o600);os.replace(temp,target)
    try:
        proof=None
        if a.close_owned_window:
            if not a.exclusive_window_reviewed:raise ValueError('review exclusive owned window before automatic closure')
            proof=json.loads((directory/'desktop-open.json').read_text())
            idx=next(x['idx'] for x in job['links'] if x['state']=='OPEN_INTENT')
            if (proof.get('queue_key'),proof.get('owner'),proof.get('session_id'),proof.get('index'),proof.get('attempt'))!=(a.key,a.owner,a.pc1_session_id,idx,job['links'][idx]['attempt']):
                raise ValueError('exact current opening proof required')
        out=collect(capture);persist(out)
        if proof is not None and out['state']=='CAPTURED_NOT_PASS':
            from ares_campaign_v3.landing_desktop import close_owned
            out['closure']=close_owned(call,proof,exclusive_reviewed=True)
            persist(out)
    finally:release_computer_use_session(a.pc1_session_id)
    persist(out)
    with q.tx():q.event(a.key,'capture_series_saved',{'owner':a.owner,'path':str(target),'state':out['state'],'frames':len(out['all_frames']),'ad_confirmed':False})
    print(json.dumps({**out,'evidence_file':str(target)},ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'state':'CAPTURE_ERROR','reason':str(exc)[:180]}));sys.exit(1)
