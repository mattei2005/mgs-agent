#!/usr/bin/env python3
"""Scoped MCP transport and resumable plans for the approved October PC1 routine.
No browser side effect occurs on import, --check or --self-test.
"""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path
import random
import select
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo

CONTRACT = Path('/root/mgs-agent/data/adspower-warming-20261008/contract.json')
BRIDGE = '/root/mgs-agent/scripts/mgs-pc1-adspower-mcp-ssh.sh'
TZ = ZoneInfo('America/New_York')
ALLOWED = {'get-group-list','get-browser-list','get-browser-active','open-browser',
           'close-browser','connect-browser-with-ws','open-new-page','navigate',
           'get-page-visible-text','get-page-html','click-element','fill-input',
           'press-key','scroll-element','hover-element'}


def load_contract():
    c = json.loads(CONTRACT.read_text())
    assert c['timezone'] == 'America/New_York'
    assert len(c['profiles']) == len({p['profile_id'] for p in c['profiles']}) == 4
    assert len(c['dates']) == len(set(c['dates'])) == 8
    assert c['likes'] == [2, 5] and c['comments'] == [1, 3]
    assert c['post_video_wait_seconds'] == [40, 90]
    return c


def text(result):
    return '\n'.join(x.get('text','') for x in result.get('content',[]) if x.get('type') == 'text')


class Client:
    """Keep raw results in memory; never print inventory, HTML, WS or stderr."""
    def __init__(self):
        self.contract = load_contract()
        self.ids = {p['profile_id'] for p in self.contract['profiles']}
        self.seq = 0
        self.last_result = None
        env = {**os.environ, 'MGS_ADSPOWER_OPERATOR':'zeus',
               'MGS_ADSPOWER_THREAD_ID':self.contract['thread_id']}
        self.process = subprocess.Popen([BRIDGE], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
        try:
            self.rpc('initialize', {'protocolVersion':'2024-11-05','capabilities':{},
                'clientInfo':{'name':'mgs-approved-warming','version':'1'}})
            self.rpc('notifications/initialized', notify=True)
            tool_list = self.rpc('tools/list')
            assert tool_list is not None
            self.schemas = {t['name']:t['inputSchema'] for t in tool_list['tools']}
        except BaseException:
            self.shutdown()
            raise

    def rpc(self, method, params=None, notify=False):
        self.seq += 1
        msg = {'jsonrpc':'2.0', 'method':method}
        if params is not None: msg['params'] = params
        if not notify: msg['id'] = self.seq
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(json.dumps(msg)+'\n')
        self.process.stdin.flush()
        if notify: return None
        deadline = time.monotonic()+90
        while time.monotonic() < deadline:
            if not select.select([self.process.stdout],[],[],max(0,deadline-time.monotonic()))[0]:
                raise TimeoutError('PC1 MCP response timed out; reconcile effects before retry')
            line = self.process.stdout.readline()
            if not line: raise RuntimeError('PC1 MCP transport closed')
            try: result = json.loads(line)
            except ValueError: continue
            if result.get('id') != self.seq: continue
            if 'error' in result:
                code = result['error'].get('code')
                if code == -32001: raise RuntimeError('PC1_LEASE_BUSY')
                raise RuntimeError('PC1_MCP_ERROR code='+str(code))
            return result['result']
        raise TimeoutError('PC1 MCP response timed out')

    def call(self, name, args=None):
        args = dict(args or {})
        if name not in ALLOWED: raise ValueError('Tool is outside approved routine')
        if name not in self.schemas: raise ValueError('Tool absent from live MCP schema')
        if name in {'open-browser','close-browser','get-browser-active'}:
            if args.get('profile_id') not in self.ids: raise ValueError('Profile outside approved scope')
        if name == 'connect-browser-with-ws' and args.get('userId') not in self.ids:
            raise ValueError('Attach outside approved scope')
        if name == 'get-browser-list' and args.get('group_id') != self.contract['group_id']:
            raise ValueError('Inventory must use exact approved group')
        if name == 'navigate':
            from urllib.parse import urlsplit
            u = urlsplit(args.get('url',''))
            if u.scheme != 'https' or u.hostname not in {'www.facebook.com','facebook.com'}:
                raise ValueError('Navigation outside Facebook')
        if name == 'fill-input':
            if 'textbox' not in args.get('selector','') or 'contenteditable' not in args.get('selector',''):
                raise ValueError('Only grounded comment textboxes may be filled')
            if not isinstance(args.get('text'),str) or len(args['text']) > 300:
                raise ValueError('Comment must be brief and non-sensitive')
        if name == 'open-browser':
            args.update({'headless':'0','ip_tab':'0','last_opened_tabs':'1','proxy_detection':'1',
                         'password_filling':'0','password_saving':'0','delete_cache':'0','cdp_mask':'1'})
        result = self.rpc('tools/call', {'name':name,'arguments':args})
        assert result is not None
        self.last_result = result
        output = text(result)
        if result.get('isError') or output.startswith(('page.','Browser not connected','Failed to','Error:')):
            raise RuntimeError('PC1_TOOL_FAILURE '+name+'; inspect private last_result, never dump it')
        return result

    def data(self, name, args=None):
        result = self.call(name, args)
        if 'structuredContent' in result: return result['structuredContent']
        return json.loads(text(result))

    def shutdown(self):
        p = getattr(self,'process',None)
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(timeout=10)
            except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=5)

    def __enter__(self): return self
    def __exit__(self, *args): self.shutdown()


def new_plan(c, date):
    rng = random.SystemRandom()
    return {'date':date,'timezone':c['timezone'],'state':'planned','profiles':[
        {**p,'likes_target':rng.randint(*c['likes']),
         'comments_target':rng.randint(*c['comments']),
         'post_video_wait_seconds':rng.randint(*c['post_video_wait_seconds']),
         'initial_active':None,'opened_by_run':False,'status':'pending',
         'likes':[],'comments':[],'video':{},'closed_verified':False}
        for p in c['profiles']]}


def prepare_run(date):
    c = load_contract()
    now = datetime.now(TZ)
    if date not in c['dates'] or now.date().isoformat() != date:
        raise ValueError('Not the exact approved execution date')
    if not (9*60+32 <= now.hour*60+now.minute < 12*60):
        raise ValueError('Outside approved morning window; do not open profiles')
    directory = CONTRACT.parent/'runs'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory/(date+'.json')
    with (directory/(date+'.lock')).open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not path.exists():
            with path.open('x') as f: json.dump(new_plan(c,date),f,ensure_ascii=False,indent=2)
        result = json.loads(path.read_text())
    return path, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--self-test',action='store_true')
    ap.add_argument('--prepare')
    args = ap.parse_args()
    c = load_contract()
    if args.self_test:
        for date in c['dates']:
            plan = new_plan(c,date)
            assert len(plan['profiles']) == 4
            for p in plan['profiles']:
                assert 2 <= p['likes_target'] <= 5 and 1 <= p['comments_target'] <= 3
                assert 40 <= p['post_video_wait_seconds'] <= 90
                assert not p['likes'] and not p['comments'] and not p['closed_verified']
        assert 'evaluate-script' not in ALLOWED and 'delete-browser' not in ALLOWED
        print(json.dumps({'self_test':'passed','dates':len(c['dates']),'profiles':4,
                          'browser_side_effects':0,'scope_guard':'passed'}))
    elif args.prepare:
        path, plan = prepare_run(args.prepare)
        print(json.dumps({'run_state_path':str(path),'plan':plan},ensure_ascii=False))
    else:
        print(json.dumps({'valid':True,'dates':c['dates'],'profiles':[
            {k:p[k] for k in ('profile_id','profile_no','name')} for p in c['profiles']],
            'timezone':c['timezone'],'start_time':c['start_time'],
            'browser_side_effects':0},ensure_ascii=False))

if __name__ == '__main__': main()
