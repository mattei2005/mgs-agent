#!/usr/bin/env python3
"""Capture frames from a YouTube reference using Ares's persistent Chromium profile."""
from __future__ import annotations

import argparse, json, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

DEFAULT_PROFILE = Path('/root/.hermes/profiles/ares/browser-profiles/youtube-chromium')
DEFAULT_OUT = Path('/root/mgs-agent/data/ares/creative-ops/references/youtube-frames')

def slug(url: str) -> str:
    m=re.search(r'(?:shorts/|watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})', url)
    return m.group(1) if m else 'youtube-reference'

ap=argparse.ArgumentParser()
ap.add_argument('url')
ap.add_argument('--profile-dir', default=str(DEFAULT_PROFILE))
ap.add_argument('--out-dir', default=str(DEFAULT_OUT))
ap.add_argument('--times', default='0,2,4,6,8,10,12,14')
ap.add_argument('--headed', action='store_true')
args=ap.parse_args()
out=Path(args.out_dir)/slug(args.url)
out.mkdir(parents=True, exist_ok=True)
profile=Path(args.profile_dir); profile.mkdir(parents=True, exist_ok=True)
frames=[]
with sync_playwright() as p:
    ctx=p.chromium.launch_persistent_context(str(profile), headless=not args.headed, viewport={'width':1280,'height':1920}, locale='en-US', timezone_id='America/New_York', args=['--disable-blink-features=AutomationControlled','--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required'])
    page=ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
    page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(6000)
    page.keyboard.press('Space')
    page.wait_for_timeout(1500)
    info=page.evaluate("""() => { const v=document.querySelector('video'); const pr=window.ytInitialPlayerResponse||{}; return {video: v ? {duration: Number.isFinite(v.duration)?v.duration:null, readyState:v.readyState, videoWidth:v.videoWidth, videoHeight:v.videoHeight, currentSrc:v.currentSrc||''}:null, playability:(pr.playabilityStatus||{}), details:(pr.videoDetails||{})}; }""")
    if not info.get('video') or info['video'].get('readyState',0) <= 0:
        (out/'status.json').write_text(json.dumps({'ok':False,'info':info}, indent=2, ensure_ascii=False)+'\n')
        ctx.close(); raise SystemExit(10)
    vloc=page.locator('video').first
    for ts in [float(x) for x in args.times.split(',') if x.strip()]:
        page.evaluate("""async (t) => { const v=document.querySelector('video'); v.currentTime=Math.min(t, Math.max(0, (isFinite(v.duration)?v.duration:15)-0.2)); await new Promise(r=>setTimeout(r,900)); v.pause(); }""", ts)
        page.wait_for_timeout(600)
        path=out/f'frame_{int(ts*1000):05d}ms.png'
        try:
            vloc.screenshot(path=str(path))
        except Exception:
            page.screenshot(path=str(path), full_page=False)
        frames.append(str(path))
    (out/'status.json').write_text(json.dumps({'ok':True,'url':args.url,'info':info,'frames':frames}, indent=2, ensure_ascii=False)+'\n')
    ctx.close()
print(json.dumps({'ok':True,'out_dir':str(out),'frames':frames}, indent=2))
