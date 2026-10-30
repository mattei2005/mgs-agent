"""Read-only isolated Chromium renderer. Signed preview URLs stay in memory."""
from __future__ import annotations
import json
import re
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
import sys


def _wait_for_browser(proc, portfile, timeout):
    """Wait for a complete port file AND its matching live loopback endpoint.

    Chromium creates DevToolsActivePort before finishing its write. File
    existence alone is not readiness; partial/empty reads and a listener that
    isn't accepting requests yet must share the same bounded startup budget.
    """
    deadline = time.monotonic() + timeout
    browser_path = re.compile(
        r'/devtools/browser/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-'
        r'[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
    )
    while True:
        if proc.poll() is not None:
            raise ValueError('media QA renderer exited before readiness')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('media QA renderer startup timed out')
        try:
            lines = portfile.read_text(encoding='utf-8').splitlines()
            if (len(lines) != 2 or not re.fullmatch(r'[0-9]{1,5}', lines[0])
                    or not 1 <= int(lines[0]) <= 65535
                    or not browser_path.fullmatch(lines[1])):
                raise ValueError('incomplete DevTools endpoint')
            port = int(lines[0])
            # Recompute after the read so no probe starts with an expired budget.
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('startup budget exhausted')
            with urlopen(f'http://127.0.0.1:{port}/json/version',
                         timeout=min(5, remaining)) as response:
                browser = json.load(response)
            endpoint = urlparse(browser.get('webSocketDebuggerUrl', '')
                                if isinstance(browser, dict) else '')
            if (endpoint.scheme != 'ws' or endpoint.hostname != '127.0.0.1'
                    or endpoint.port != port or endpoint.path != lines[1]
                    or endpoint.username is not None or endpoint.password is not None
                    or endpoint.query or endpoint.fragment):
                raise ValueError('DevTools endpoint mismatch')
        except (OSError, ValueError, TypeError, AttributeError):
            # Retry only readiness failures; never loosen URL/media/activation gates.
            pass
        else:
            if proc.poll() is not None:
                raise ValueError('media QA renderer exited before readiness')
            if time.monotonic() < deadline:
                return browser
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('media QA renderer startup timed out')
        time.sleep(min(.1, remaining))


def render_previews(urls, *, chrome_path, timeout=35, allow_local=False, expect_video=None, python_path=None):
    for url in urls:
        p=urlparse(url)
        if not (p.scheme=='https' and p.hostname=='business.facebook.com' and p.path=='/ads/api/preview_iframe.php'):
            if not (allow_local and p.scheme=='http' and p.hostname=='127.0.0.1'):
                raise ValueError('preview URL outside authorized renderer')
    if not Path(chrome_path).is_file():raise ValueError('media QA Chromium runtime unavailable')
    if python_path and os.path.abspath(python_path) != os.path.abspath(sys.executable):
        run=subprocess.run([python_path,str(Path(__file__).resolve())],input=json.dumps({'urls':urls,'chrome_path':chrome_path,'timeout':timeout,'allow_local':allow_local,'expect_video':expect_video}),text=True,capture_output=True,timeout=timeout*(len(urls)+2)+10)
        if run.returncode!=0:raise ValueError('media preview renderer unavailable; activation remains PAUSED')
        return json.loads(run.stdout)
    try:
        from websockets.sync.client import connect
    except ImportError as exc:
        raise ValueError('media QA renderer Python runtime unavailable') from exc
    root=Path(os.environ.get('TMPDIR') or '/root/.hermes/profiles/ares/cache/scratch');root.mkdir(parents=True,exist_ok=True)
    results=[]
    with tempfile.TemporaryDirectory(prefix='ares-media-qa-',dir=root) as directory:
        proc=subprocess.Popen([chrome_path,'--headless=new','--no-sandbox','--disable-dev-shm-usage','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+directory,'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        try:
            browser=_wait_for_browser(proc,Path(directory)/'DevToolsActivePort',timeout)
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
            # The isolated browser's descendants can still write profile files
            # after the parent exits. Stop only our new process group before
            # TemporaryDirectory cleanup; otherwise ENOTEMPTY masks valid QA.
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait(timeout=5)
            time.sleep(.1)
    return results


def validate_runtime(policy):
    executable=policy.get('python_path') or sys.executable
    if policy.get('enabled') is not True or not Path(executable).is_file() or not os.access(policy.get('chrome_path',''),os.X_OK):
        raise ValueError('SHEIN media QA runtime unavailable before write')
    result=subprocess.run([executable,'-c','from websockets.sync.client import connect'],capture_output=True,timeout=10)
    if result.returncode!=0:raise ValueError('SHEIN media QA dependency unavailable before write')


if __name__=='__main__':
    try:
        inputs=json.load(sys.stdin);print(json.dumps(render_previews(**inputs)))
    except Exception:
        print('media preview rendering failed',file=sys.stderr);sys.exit(1)
