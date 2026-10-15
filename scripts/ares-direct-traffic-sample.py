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


def collect(capture, *, pause=time.sleep, max_frames=12,max_seconds=45):
    all_frames=[];chain=[];started=time.monotonic()
    for _ in range(max_frames):
        if time.monotonic()-started>max_seconds:break
        frame=capture();all_frames.append(frame)
        if chain and not (0 < frame['monotonic_seconds']-chain[-1]['monotonic_seconds'] <= 10
                          and 0 < frame['captured_at']-chain[-1]['captured_at'] <= 12):chain=[]
        chain.append(frame)
        if len(chain)>=3 and chain[-1]['monotonic_seconds']-chain[0]['monotonic_seconds']>=10 and chain[-1]['captured_at']-chain[0]['captured_at']>=10:
            return {'state':'CAPTURED_NOT_PASS','samples':chain,'all_frames':all_frames}
        pause(.5)
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
    from tools.computer_use.tool import handle_computer_use,release_computer_use_session
    def capture():
        cli.require_pc1_lease(a.pc1_session_id)
        image=None
        for _ in range(2):
            out=handle_computer_use({'action':'capture','mode':'vision','app':'screen'},session_id=a.pc1_session_id)
            if isinstance(out,str):out=json.loads(out)
            image=out.get('screenshot_path') or (out.get('meta') or {}).get('screenshot_path')
            if image:break
        if not image:raise ValueError('capture failed; no image evidence')
        path=Path(image);epoch=path.stat().st_mtime
        return {'screenshot':str(path),'captured_at':epoch,'monotonic_seconds':time.monotonic()-(time.time()-epoch),
                'analysis':out.get('vision_analysis'),'screen_unchanged':out.get('screen_unchanged',False),'composited_desktop':True}
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
            def call(args):
                cli.require_pc1_lease(a.pc1_session_id)
                r=handle_computer_use(args,session_id=a.pc1_session_id)
                return json.loads(r) if isinstance(r,str) else r
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
