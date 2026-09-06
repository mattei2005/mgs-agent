#!/usr/bin/env python3
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

URL='https://app.smartbiddingdigital.com/reports/photo-by-vertical'
PHOTO='https://api.jbfdigital.com.br/photo/performance_per_vertical'
COMPANY='https://api.jbfdigital.com.br/company'
STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
OUT=Path('/root/mgs-agent/work/hourly-revenue-report')

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
            page=await ctx.new_page()
            photo_req=[]; company_data=[]
            async def req(r):
                if r.url.split('?')[0]==PHOTO: photo_req.append(r)
            async def resp(r):
                if r.url.split('?')[0]==COMPANY and r.status==200:
                    try: company_data.append(await r.json())
                    except Exception: pass
            page.on('request',req); page.on('response',resp)
            await page.goto(URL,wait_until='domcontentloaded',timeout=120000)
            for _ in range(60):
                await page.wait_for_timeout(1000)
                if photo_req and company_data: break
            if not photo_req: raise RuntimeError('photo request not captured')
            headers={k:v for k,v in photo_req[-1].headers.items() if k.lower() not in {'content-length','host','origin','referer'}}
            if not company_data:
                r=await ctx.request.get(COMPANY,headers=headers)
                if r.status!=200: raise RuntimeError(f'company HTTP {r.status}')
                company_data.append(await r.json())
            data=company_data[-1]
            (OUT/'company.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            def summarize(x):
                if isinstance(x,list):
                    return {'type':'list','count':len(x),'first_keys':sorted(x[0].keys()) if x and isinstance(x[0],dict) else []}
                if isinstance(x,dict):
                    return {'type':'dict','keys':sorted(x.keys()),'list_fields':{k:len(v) for k,v in x.items() if isinstance(v,list)}}
                return {'type':type(x).__name__}
            print(json.dumps(summarize(data),ensure_ascii=False))
            # Print only identifying non-secret fields from likely company/publisher records.
            arr=data if isinstance(data,list) else next((v for v in data.values() if isinstance(v,list)),[])
            sample=[]
            for item in arr[:10]:
                if isinstance(item,dict): sample.append({k:item.get(k) for k in item if k.lower() in {'id','name','company','domain','publisher','label','value','slug'}})
            print(json.dumps({'sample':sample},ensure_ascii=False))
        finally:
            await browser.close()
asyncio.run(main())
