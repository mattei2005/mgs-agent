#!/usr/bin/env python3
import asyncio, json
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
TARGET='https://app.smartbiddingdigital.com/company/digital-trust/financeadx/routing'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'

async def main():
    events=[]
    p=await async_playwright().start()
    browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent=UA)
    page=await ctx.new_page()
    async def on_resp(resp):
        if 'api.jbfdigital.com.br' not in resp.url:
            return
        u=urlsplit(resp.url)
        rec={'method':resp.request.method,'path':u.path,'query':u.query,'status':resp.status}
        try:
            d=await resp.json()
            if isinstance(d,list):
                rec.update({'type':'list','count':len(d),'item_keys':sorted(d[0].keys()) if d and isinstance(d[0],dict) else []})
            elif isinstance(d,dict):
                rec.update({'type':'dict','keys':sorted(d.keys())})
            else:
                rec.update({'type':type(d).__name__})
        except Exception:
            rec['type']='non-json'
        events.append(rec)
    page.on('response',on_resp)
    try:
        await page.goto(TARGET,wait_until='networkidle',timeout=90000)
        await page.wait_for_timeout(4000)
        print(json.dumps({'title':await page.title(),'url':page.url,'events':events},ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()
if __name__=='__main__': asyncio.run(main())
