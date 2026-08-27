#!/usr/bin/env python3
import base64
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
import websocket

ROOT = Path('/root/mgs-agent/work/landing-shein-vizioid/20260827T135436Z')
CHROME = '/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome'
PROFILE = ROOT / 'chrome-profile-cdp'
LOG = ROOT / 'chromium-cdp.log'
PROFILE.mkdir(parents=True, exist_ok=True)

sock = socket.socket()
sock.bind(('127.0.0.1', 0))
PORT = sock.getsockname()[1]
sock.close()

cmd = [
    CHROME,
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--hide-scrollbars',
    '--remote-allow-origins=*',
    f'--remote-debugging-port={PORT}',
    f'--user-data-dir={PROFILE}',
    '--window-size=390,844',
    'about:blank',
]

class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=20, origin='http://127.0.0.1')
        self.counter = 0

    def call(self, method, params=None):
        self.counter += 1
        ident = self.counter
        self.ws.send(json.dumps({'id': ident, 'method': method, 'params': params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get('id') != ident:
                continue
            if 'error' in msg:
                raise RuntimeError(f'{method}: {msg["error"]}')
            return msg.get('result', {})

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result['result'].get('value')

    def close(self):
        self.ws.close()


def wait_ready(cdp, expected_fragment=None, timeout=30):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = cdp.evaluate("JSON.stringify({ready:document.readyState,url:location.href})")
        state = json.loads(last)
        if state['ready'] == 'complete' and (not expected_fragment or expected_fragment in state['url']):
            return state
        time.sleep(0.2)
    raise TimeoutError(last)


def inspect(cdp, label):
    raw = cdp.evaluate("""JSON.stringify((() => {
      const card=document.querySelector('.mgs-dq-card');
      if(!card) return {error:'card_missing'};
      const r=card.getBoundingClientRect();
      const links=[...document.querySelectorAll('[data-mgs-dq-cta]')];
      return {
        label:%s,
        url:location.href,
        width:innerWidth,
        height:innerHeight,
        scrollWidth:document.documentElement.scrollWidth,
        scrollHeight:document.documentElement.scrollHeight,
        card:{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height},
        model:document.body.dataset.model,
        manager:document.body.dataset.manager,
        ctas:links.length,
        hrefs:links.map(a=>a.href),
        forms:document.forms.length,
        inputs:document.querySelectorAll('input').length,
        logo:!!document.querySelector('.mgs-dq-logo img'),
        title:document.title
      };
    })())""" % json.dumps(label))
    result = json.loads(raw)
    if result.get('error'):
        raise AssertionError(result)
    return result


def screenshot(cdp, path):
    result = cdp.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
    path.write_bytes(base64.b64decode(result['data']))


def click_cta(cdp, index):
    cdp.evaluate("document.querySelectorAll('[data-mgs-dq-cta]')[%d].scrollIntoView({block:'center'})" % index)
    time.sleep(0.2)
    raw = cdp.evaluate("JSON.stringify((() => {const r=document.querySelectorAll('[data-mgs-dq-cta]')[%d].getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};})())" % index)
    pos = json.loads(raw)
    cdp.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pos['x'], 'y': pos['y']})
    cdp.call('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': pos['x'], 'y': pos['y'], 'button': 'left', 'clickCount': 1})
    cdp.call('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': pos['x'], 'y': pos['y'], 'button': 'left', 'clickCount': 1})
    return wait_ready(cdp, '/rec-us-app-shein-circle-of-style/')['url']


def validate_destination(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_adgroup', 'fbclid', 'custom']
    return {
        'base': f'{parsed.scheme}://{parsed.netloc}{parsed.path}',
        'params': params,
        'exact_once': all(len(params.get(key, [])) == 1 for key in keys),
    }

proc = None
cdp = None
try:
    with LOG.open('ab') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)
    endpoint = f'http://127.0.0.1:{PORT}'
    deadline = time.time() + 20
    targets = None
    while time.time() < deadline:
        try:
            targets = requests.get(endpoint + '/json', timeout=2).json()
            if targets:
                break
        except Exception:
            time.sleep(0.2)
    if not targets:
        raise RuntimeError('cdp_endpoint_unavailable')
    page = next(x for x in targets if x.get('type') == 'page')
    cdp = CDP(page['webSocketDebuggerUrl'])
    cdp.call('Page.enable')
    cdp.call('Runtime.enable')
    cdp.call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})

    query = 'utm_source=facebook&utm_medium=g002-s&utm_campaign=b02fb02c27&utm_adgroup=b02fb02c27g01&fbclid=browserfb&custom=browsercustom'
    v2_url = 'https://vizioid.com/quiz/us/sh2-g002/?' + query
    cdp.call('Page.navigate', {'url': v2_url})
    wait_ready(cdp, '/quiz/us/sh2-g002/')
    v2 = inspect(cdp, 'v2')
    screenshot(cdp, ROOT / 'vizioid-v2-mobile-390x844.png')
    v2_click = validate_destination(click_cta(cdp, 0))

    v1_url = 'https://vizioid.com/quiz/us/sh1-g002/?' + query
    cdp.call('Page.navigate', {'url': v1_url})
    wait_ready(cdp, '/quiz/us/sh1-g002/')
    v1 = inspect(cdp, 'v1')
    screenshot(cdp, ROOT / 'vizioid-v1-mobile-390x844.png')
    v1_click = validate_destination(click_cta(cdp, 1))

    for item, model, logo in [(v2, 'lp2', True), (v1, 'lp1', False)]:
        assert item['width'] == 390
        assert item['scrollWidth'] <= item['width']
        assert item['card']['left'] >= 0 and item['card']['right'] <= item['width']
        assert item['model'] == model and item['manager'] == 'G002'
        assert item['ctas'] == 2 and item['forms'] == 0 and item['inputs'] == 0
        assert item['logo'] is logo
    for clicked in [v2_click, v1_click]:
        assert clicked['base'] == 'https://vizioid.com/rec-us-app-shein-circle-of-style/'
        assert clicked['exact_once']

    output = {
        'chromium': CHROME,
        'viewport': '390x844',
        'v2': v2,
        'v2_click': v2_click,
        'v1': v1,
        'v1_click': v1_click,
        'screenshots': [str(ROOT / 'vizioid-v2-mobile-390x844.png'), str(ROOT / 'vizioid-v1-mobile-390x844.png')],
    }
    print(json.dumps(output, ensure_ascii=False, separators=(',', ':')))
finally:
    if cdp is not None:
        try:
            cdp.close()
        except Exception:
            pass
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
