"""Read-only isolated Chromium renderer. Signed preview URLs stay in memory."""
from __future__ import annotations
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from websockets.sync.client import connect


def render_previews(urls, *, chrome_path, timeout=35, allow_local=False, expect_video=None):
    for url in urls:
        p=urlparse(url)
        if not (p.scheme=='https' and p.hostname=='business.facebook.com' and p.path=='/ads/api/preview_iframe.php'):
            if not (allow_local and p.scheme=='http' and p.hostname=='127.0.0.1'):
                raise ValueError('preview URL outside authorized renderer')
    if not Path(chrome_path).is_file():raise ValueError('media QA Chromium runtime unavailable')
    root=Path(os.environ.get('TMPDIR') or '/root/.hermes/profiles/ares/cache/scratch');root.mkdir(parents=True,exist_ok=True)
    results=[]
    with tempfile.TemporaryDirectory(prefix='ares-media-qa-',dir=root) as directory:
        proc=subprocess.Popen([chrome_path,'--headless=new','--no-sandbox','--disable-dev-shm-usage','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+directory,'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            portfile=Path(directory)/'DevToolsActivePort';deadline=time.monotonic()+timeout
            while not portfile.exists():
                if proc.poll() is not None or time.monotonic()>deadline:raise ValueError('media QA renderer startup failed')
                time.sleep(.1)
            port=int(portfile.read_text().splitlines()[0]);browser=json.load(urlopen(f'http://127.0.0.1:{port}/json/version',timeout=5))
            with connect(browser['webSocketDebuggerUrl'],open_timeout=5,max_size=8*1024*1024) as ws:
                sequence=0
                def call(method,params=None,session=None):
                    nonlocal sequence
                    sequence+=1;msg={'id':sequence,'method':method,'params':params or {}}
                    if session:msg['sessionId']=session
                    ws.send(json.dumps(msg));limit=time.monotonic()+timeout
                    while time.monotonic()<limit:
                        answer=json.loads(ws.recv(timeout=max(.1,limit-time.monotonic())))
                        if answer.get('id')==sequence:
                            if answer.get('error'):raise ValueError('media QA CDP rejected operation')
                            return answer.get('result') or {}
                    raise ValueError('media QA renderer command timeout')
                for index, url in enumerate(urls):
                    target=call('Target.createTarget',{'url':url})['targetId']
                    sid=call('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId'];limit=time.monotonic()+timeout;media={}
                    while time.monotonic()<limit:
                        evaluated=call('Runtime.evaluate',{'expression':'''JSON.stringify({videos:Array.from(document.querySelectorAll('video')).map(v=>({duration:v.duration,readyState:v.readyState,width:v.videoWidth,height:v.videoHeight,error:v.error?.code||null})),images:Array.from(document.querySelectorAll('img')).filter(i=>i.complete&&i.naturalWidth>100&&i.naturalHeight>100&&i.width>100&&i.height>100).map(i=>({width:i.naturalWidth,height:i.naturalHeight}))})''','returnByValue':True},sid)
                        value=evaluated.get('result',{}).get('value');media=json.loads(value) if value else {}
                        videos=[v for v in media.get('videos',[]) if v.get('readyState',0)>=2 and (v.get('duration') or 0)>0 and v.get('width',0)>0 and v.get('height',0)>0 and not v.get('error')]
                        if videos or (not (expect_video or [False]*len(urls))[index] and media.get('images')):break
                        time.sleep(.2)
                    results.append(media);call('Target.closeTarget',{'targetId':target})
        except Exception as exc:
            raise ValueError('media preview rendering unavailable; activation remains PAUSED') from exc
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    return results
