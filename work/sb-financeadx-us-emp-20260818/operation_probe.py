#!/usr/bin/env python3
import asyncio, json
from playwright.async_api import async_playwright

STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
TARGET='https://app.smartbiddingdigital.com/company/digital-trust/financeadx/routing'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
URLS=[
 'https://financeadx.com/rec-us-prestamo-alliant-credit-union',
 'https://financeadx.com/rec-us-prestamo-achieve',
 'https://financeadx.com/rec-us-prestamo-grace-loan-advance',
 'https://financeadx.com/rec-us-prestamo-wells-fargo',
]

def norm(u): return str(u or '').strip().rstrip('/')

async def main():
    target={norm(u) for u in URLS}; rows=[]; request_data=[]
    p=await async_playwright().start()
    browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent=UA)
    page=await ctx.new_page()
    async def on_req(req):
        if '/report/performance_per_operation' in req.url:
            try: request_data.append(req.post_data_json)
            except Exception: request_data.append(req.post_data)
    async def on_resp(resp):
        if '/report/performance_per_operation' not in resp.url or resp.status not in (200,201): return
        try:
            data=await resp.json()
            for x in data if isinstance(data,list) else []:
                if norm(x.get('url')) in target:
                    rows.append({k:x.get(k) for k in ('company','domain','country','vertical','page_type','utm_source','slot_id','product','url','jbf_operation')})
        except Exception: pass
    page.on('request',on_req); page.on('response',on_resp)
    try:
        await page.goto(TARGET,wait_until='networkidle',timeout=90000); await page.wait_for_timeout(4000)
        unique=[]; seen=set()
        for x in rows:
            key=json.dumps(x,sort_keys=True,ensure_ascii=False)
            if key not in seen: seen.add(key); unique.append(x)
        print(json.dumps({'title':await page.title(),'request_data':request_data,'matches':unique,'match_count':len(unique)},ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()
if __name__=='__main__': asyncio.run(main())
