#!/usr/bin/env python3
import base64
import json
import re
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
import websocket

WORK = Path('/root/mgs-agent/work/mgs-direct-quiz-v3-20260911T140923Z')
CHROME = Path('/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome')
HTML = WORK / 'local-preview-root/quiz/us/sh3-g002/index.html'
SHOT = WORK / 'local-v3-mobile-390x844.png'
LOG = WORK / 'local-v3-chromium.log'
PROFILE = WORK / 'local-v3-chrome-profile'
PROFILE.mkdir(parents=True, exist_ok=True)

sock = socket.socket()
sock.bind(('127.0.0.1', 0))
port = sock.getsockname()[1]
sock.close()
url = HTML.as_uri() + '?utm_source=facebook&utm_medium=g002-s&utm_campaign=local&utm_adgroup=localg01&fbclid=LOCAL&custom_x=abc'
cmd = [
    str(CHROME), '--headless=new', '--no-sandbox', '--disable-gpu',
    '--disable-dev-shm-usage', '--hide-scrollbars', '--allow-file-access-from-files',
    '--remote-allow-origins=*', f'--remote-debugging-port={port}',
    f'--user-data-dir={PROFILE}', '--window-size=390,844', 'about:blank',
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
            message = json.loads(self.ws.recv())
            if message.get('id') != ident:
                continue
            if 'error' in message:
                raise RuntimeError(f'{method}: {message["error"]}')
            return message.get('result', {})
    def evaluate(self, expression):
        response = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
        if 'exceptionDetails' in response:
            raise RuntimeError(response['exceptionDetails'])
        return response['result'].get('value')
    def close(self):
        self.ws.close()

proc = None
cdp = None
try:
    with LOG.open('ab') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)
    endpoint = f'http://127.0.0.1:{port}'
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
    page = next(item for item in targets if item.get('type') == 'page')
    cdp = CDP(page['webSocketDebuggerUrl'])
    cdp.call('Page.enable')
    cdp.call('Runtime.enable')
    cdp.call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
    cdp.call('Page.navigate', {'url': url})
    deadline = time.time() + 20
    while time.time() < deadline:
        ready = cdp.evaluate('document.readyState')
        if ready == 'complete':
            break
        time.sleep(0.2)
    time.sleep(1.2)
    raw = cdp.evaluate("""JSON.stringify((() => {
      const card=document.querySelector('.mgs-dq-category-card');
      const r=card.getBoundingClientRect();
      const links=[...document.querySelectorAll('[data-mgs-dq-cta]')];
      return {
        url:location.href,width:innerWidth,height:innerHeight,
        scrollWidth:document.documentElement.scrollWidth,
        scrollHeight:document.documentElement.scrollHeight,
        card:{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height},
        model:document.body.dataset.model,manager:document.body.dataset.manager,
        categories:document.querySelectorAll('.mgs-dq-category').length,
        ctas:links.length,hrefs:links.map(a=>a.href),
        forms:document.forms.length,inputs:document.querySelectorAll('input').length,
        images:[...document.images].map(i=>({src:i.src,complete:i.complete,w:i.naturalWidth,h:i.naturalHeight})),
        countdown:document.querySelector('[data-mgs-dq-countdown]').textContent,
        disclaimerHidden:document.querySelector('[data-mgs-dq-disclaimer-box]').hidden,
        title:document.title
      };
    })())""")
    result = json.loads(raw)
    capture = cdp.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
    SHOT.write_bytes(base64.b64decode(capture['data']))
    cdp.evaluate("document.querySelector('[data-mgs-dq-disclaimer-toggle]').click()")
    expanded = json.loads(cdp.evaluate("JSON.stringify({expanded:document.querySelector('[data-mgs-dq-disclaimer-toggle]').getAttribute('aria-expanded'),hidden:document.querySelector('[data-mgs-dq-disclaimer-box]').hidden})"))

    assert result['width'] == 390 and result['height'] == 844, result
    assert result['scrollWidth'] <= result['width'], result
    assert result['card']['left'] >= 0 and result['card']['right'] <= result['width'], result
    assert result['card']['bottom'] <= result['height'], result
    assert result['model'] == 'lp3' and result['manager'] == 'G002', result
    assert result['categories'] == 6 and result['ctas'] == 7, result
    assert result['forms'] == 0 and result['inputs'] == 0, result
    assert all(image['complete'] and image['w'] > 0 and image['h'] > 0 for image in result['images']), result
    assert re.fullmatch(r'\d{2}:\d{2}:\d{2}', result['countdown']), result
    assert result['disclaimerHidden'] is True, result
    assert expanded == {'expanded': 'true', 'hidden': False}, expanded
    for href in result['hrefs']:
        parsed = urlparse(href)
        params = parse_qs(parsed.query, keep_blank_values=True)
        for key in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_adgroup', 'fbclid', 'custom_x'):
            assert len(params.get(key, [])) == 1, (href, key, params)
    print(json.dumps({'result': result, 'expanded': expanded, 'screenshot': str(SHOT)}, ensure_ascii=False, separators=(',', ':')))
finally:
    if cdp is not None:
        try: cdp.close()
        except Exception: pass
    if proc is not None:
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=5)
