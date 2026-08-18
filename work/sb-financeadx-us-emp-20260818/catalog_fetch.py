#!/usr/bin/env python3
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
TARGET='https://app.smartbiddingdigital.com/company/digital-trust/financeadx/routing'
API='https://api.jbfdigital.com.br'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
OUT=Path('/root/mgs-agent/backups/sb-financeadx-us-emp-20260818/operations-catalog-before.json')
URLS=[
 'https://financeadx.com/rec-us-prestamo-alliant-credit-union',
 'https://financeadx.com/rec-us-prestamo-achieve',
 'https://financeadx.com/rec-us-prestamo-grace-loan-advance',
 'https://financeadx.com/rec-us-prestamo-wells-fargo',
]

def norm(s): return str(s or '').strip().rstrip('/').lower()
def contains_target(obj,target):
    if isinstance(obj,dict): return any(contains_target(v,target) for v in obj.values())
    if isinstance(obj,list): return any(contains_target(v,target) for v in obj)
    return norm(obj)==target or target in norm(obj)

async def main():
    p=await async_playwright().start(); browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent=UA); page=await ctx.new_page(); captured={}
    async def req(r):
        if 'api.jbfdigital.com.br' in r.url:
            h=await r.all_headers()
            if h.get('authorization'): captured.update(h)
    page.on('request',req)
    try:
        await page.goto(TARGET,wait_until='networkidle',timeout=90000); await page.wait_for_timeout(3000)
        if not captured.get('authorization'): raise RuntimeError('auth header not captured')
        h={k:v for k,v in captured.items() if k.lower() in {'authorization','accept','content-type'}}; h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
        r=await ctx.request.get(f'{API}/operations/digital-trust_financeadx',headers=h,timeout=120000); data=await r.json()
        OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2))
        matches={}
        for u in URLS:
            t=norm(u); found=[]
            items=data if isinstance(data,list) else [data]
            for x in items:
                if contains_target(x,t): found.append(x)
            matches[u]=found
        print(json.dumps({'http':r.status,'type':type(data).__name__,'count':len(data) if isinstance(data,list) else None,'matches':matches},ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()
if __name__=='__main__': asyncio.run(main())
