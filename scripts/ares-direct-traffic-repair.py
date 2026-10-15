#!/usr/bin/env python3
"""Receipt-backed PC1 observer probe: blank private window, capture, close. No URL."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_desktop import open_blank_owned,close_owned,windows,identity
from ares_campaign_v3.landing_reliability import approve_repair


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--key');p.add_argument('--owner');p.add_argument('--index',type=int)
    p.add_argument('--pc1-session-id',required=True);p.add_argument('--repair-note',required=True)
    p.add_argument('--standalone-probe-id')
    a=p.parse_args();here=Path(__file__).resolve().parent;cli=load('probe_control',here/'ares-direct-traffic-followup.py');cli.require_pc1_lease(a.pc1_session_id)
    if not a.repair_note.strip():raise ValueError('actual diagnosis and correction note required')
    q=core.Queue();standalone=bool(a.standalone_probe_id)
    if standalone:
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',a.standalone_probe_id):raise ValueError('literal probe ID required')
        target=q.root/'probes'/a.standalone_probe_id/'technical-probe.json'
    else:
        if a.key is None or a.owner is None or a.index is None:raise ValueError('exact repair queue identity required')
        j=q.job(a.key)
        if j['state']!='REPAIRING' or j['owner']!=a.owner or j['lease_until']<q.now():raise ValueError('active repair reservation required')
        target=q.root/'runs'/a.owner/'technical-probe.json'
    if target.exists():raise ValueError('probe already attempted; reconcile saved proof, never blindly repeat')
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    proof={'state':'TECHNICAL_PROBE_INTENT','session_id':a.pc1_session_id,'owner':a.owner,'idx':a.index,'repair_note':a.repair_note,'url_navigation':False}
    def save():
        temp=target.with_suffix('.new');temp.write_text(json.dumps(proof,ensure_ascii=False,indent=2));os.chmod(temp,0o600);os.replace(temp,target)
    save()
    if not standalone:
        with q.tx():q.event(a.key,'technical_probe_intent',{'owner':a.owner,'idx':a.index,'probe_file':str(target),'session_id':a.pc1_session_id})
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(core.BASE/'tests'),'-p','test_direct_traffic_landing*.py'],capture_output=True,text=True,timeout=120)
    proof['tests_returncode']=tests.returncode;save()
    if tests.returncode:raise ValueError('observer regressions failed; no probe input performed')
    exe=shutil.which('hermes');sys.path.insert(0,str(Path(exe).resolve().parents[2]))
    from tools.computer_use.tool import handle_computer_use,release_computer_use_session
    sampler=load('probe_sample',here/'ares-direct-traffic-sample.py');owned=None;baseline=[];started=time.monotonic();error=None
    def call(args):
        cli.require_pc1_lease(a.pc1_session_id);r=handle_computer_use(args,session_id=a.pc1_session_id)
        return json.loads(r) if isinstance(r,str) else r
    def opened(partial):
        nonlocal owned
        proof['opening']=partial.copy()
        if partial.get('new_window_created'):owned=partial.copy()
        save()
    def capture():
        r=call({'action':'capture','mode':'vision','app':'screen'});path=r.get('screenshot_path') or (r.get('meta') or {}).get('screenshot_path')
        if not path:raise ValueError('probe capture image missing')
        stamp=Path(path).stat().st_mtime
        return {'screenshot':path,'captured_at':stamp,'monotonic_seconds':time.monotonic()-(time.time()-stamp),'analysis':r.get('vision_analysis'),'composited_desktop':True}
    try:
        baseline=windows(call);proof['baseline']=baseline;save()
        open_blank_owned(call,on_owned=opened)
        proof['series']=sampler.collect(capture);save()
        if proof['series']['state']!='CAPTURED_NOT_PASS':raise ValueError('real capture cadence not validated')
    except Exception as exc:error=str(exc)[:200]
    finally:
        try:
            if owned:proof['closure']=close_owned(call,owned,exclusive_reviewed=True)
            else:
                now=windows(call);proof['no_new_window_verified']={identity(w) for w in now}=={identity(w) for w in baseline}
        except Exception as exc:proof['closure_error']=str(exc)[:160]
        proof['elapsed_seconds']=round(time.monotonic()-started,3);save();release_computer_use_session(a.pc1_session_id)
    closed=(proof.get('closure') or {}).get('state')=='CLOSED_NOT_PASS'
    passed=error is None and closed
    proof['state']='TECHNICAL_PROBE_VERIFIED' if passed else 'TECHNICAL_PROBE_FAILED';proof['error']=error;save()
    if passed and not standalone:
        with q.tx():q.event(a.key,'technical_probe_verified',{'owner':a.owner,'idx':a.index,'probe_file':str(target),'url_navigation':False,'tests_returncode':0,'closure_verified':True,'capture_seconds':proof['series']['samples'][-1]['monotonic_seconds']-proof['series']['samples'][0]['monotonic_seconds']})
        approve_repair(q,a.key,a.owner,a.index,str(target))
    elif not passed and not standalone:
        safe=closed or proof.get('no_new_window_verified') is True
        with q.tx():
            q.db.execute('UPDATE jobs SET state=?,owner=NULL,lease_until=? WHERE key=?',('TECHNICAL_REPAIR' if safe else 'NEEDS_RECONCILIATION',q.now()+60,a.key))
            if not safe:q.db.execute("UPDATE links SET state='ATTENTION',evidence=? WHERE job=? AND idx=?",(json.dumps({'diagnosis':'Technical probe requires exact-window cleanup','technical_probe_evidence_path':str(target),'probe_cleanup_required':True}),a.key,a.index))
            q.event(a.key,'technical_probe_failed',{'owner':a.owner,'idx':a.index,'probe_file':str(target),'safe_cleanup_verified':safe,'ordinary_opening_blocked':True})
    print(json.dumps({'state':proof['state'],'probe_file':str(target),'url_navigation':False,'closure_verified':closed,'elapsed_seconds':proof['elapsed_seconds']}));q.db.close()
    return 0 if passed else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:print(json.dumps({'state':'PROBE_ERROR','reason':str(e)[:180]}));raise SystemExit(1)
