#!/usr/bin/env python3
"""One bounded UI opening batch under an existing real PC1/queue lease."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import urllib.parse
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_desktop import open_owned


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--key',required=True);p.add_argument('--owner',required=True)
    p.add_argument('--index',type=int,required=True);p.add_argument('--pc1-session-id',required=True)
    p.add_argument('--url',required=True);p.add_argument('--mapping-source',required=True)
    p.add_argument('--base-window-id',type=int)
    a=p.parse_args();here=Path(__file__).resolve().parent
    s=importlib.util.spec_from_file_location('landing_control_ui',here/'ares-direct-traffic-followup.py')
    assert s is not None and s.loader is not None
    cli=importlib.util.module_from_spec(s);s.loader.exec_module(cli);cli.require_pc1_lease(a.pc1_session_id)
    q=core.Queue();j=q.owned(a.key,a.owner);link=j['links'][a.index]
    if link['state']!='OPEN_INTENT':raise ValueError('persist begin before opening batch')
    original=j['payload']['links'][a.index];source=urllib.parse.urlsplit(original['effective_campaign_url']);target=urllib.parse.urlsplit(a.url)
    if target.scheme!='https' or target.hostname!=source.hostname or target.query!=source.query or re.search(r'/(quiz|chat)(/|$)',target.path,re.I) or not a.mapping_source.strip():
        raise ValueError('exact real landing mapping and unchanged query required')
    if original.get('landing_url') and original['landing_url']!=a.url:raise ValueError('canonical landing differs')
    core.scope(a.url)
    dest=q.root/'runs'/a.owner/'desktop-open.json'
    if dest.exists():raise ValueError('opening already attempted; read proof and reconcile, never replay')
    dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    def save(proof):
        proof.update(queue_key=a.key,owner=a.owner,index=a.index,attempt=link['attempt'],session_id=a.pc1_session_id,mapping_source=a.mapping_source,resolved_landing_url=a.url)
        temp=dest.with_suffix('.new');temp.write_text(json.dumps(proof,ensure_ascii=False,indent=2));os.chmod(temp,0o600);os.replace(temp,dest)
    # Mark intent before the first native input; an uncertain opening is not retried.
    save({'state':'OPENING_INTENT','url_submission_attempted':False})
    executable=shutil.which('hermes')
    if not executable:raise ValueError('Hermes runtime unavailable')
    sys.path.insert(0,str(Path(executable).resolve().parents[2]))
    from tools.computer_use.tool import handle_computer_use,release_computer_use_session
    def call(args):
        cli.require_pc1_lease(a.pc1_session_id)
        result=handle_computer_use(args,session_id=a.pc1_session_id)
        return json.loads(result) if isinstance(result,str) else result
    try:result=open_owned(call,a.url,base_window=a.base_window_id,on_owned=save)
    finally:release_computer_use_session(a.pc1_session_id)
    with q.tx():q.event(a.key,'desktop_open_batch',{'idx':a.index,'attempt':link['attempt'],'owner':a.owner,'proof':str(dest),'elapsed_seconds':result['elapsed_seconds'],'visually_validated':False})
    return {**result,'proof_file':str(dest)}


if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False))
    except Exception as e:print(json.dumps({'state':'UI_BATCH_REVIEW_REQUIRED','reason':str(e)[:180]}));sys.exit(1)
