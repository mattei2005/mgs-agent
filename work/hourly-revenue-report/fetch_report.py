#!/usr/bin/env python3
import asyncio, json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

URL='https://app.smartbiddingdigital.com/reports/photo-by-vertical'
API='https://api.jbfdigital.com.br/photo/performance_per_vertical'
STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
OUT=Path('/root/mgs-agent/work/hourly-revenue-report')
NY=ZoneInfo('America/New_York')

def rows_of(data):
    if isinstance(data,list): return data
    if isinstance(data,dict): return next((data[k] for k in ('data','rows','result','results') if isinstance(data.get(k),list)),[])
    return []

async def main():
    companies=json.loads((OUT/'company.json').read_text(encoding='utf-8'))
    publishers=[p['publisherId'] for c in companies for p in c['publishers'] if p.get('publisherId')]
    if len(publishers)!=52 or len(set(publishers))!=52: raise RuntimeError(f'publisher scope mismatch {len(publishers)}/{len(set(publishers))}')
    now=datetime.now(NY)
    dates=[now.date().isoformat(),now.date().fromordinal(now.date().toordinal()-1).isoformat()]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
            page=await ctx.new_page(); reqs=[]
            page.on('request',lambda r: reqs.append(r) if r.url.split('?')[0]==API else None)
            await page.goto(URL,wait_until='domcontentloaded',timeout=120000)
            for _ in range(60):
                await page.wait_for_timeout(1000)
                if reqs: break
            if not reqs: raise RuntimeError('no authenticated photo request')
            headers={k:v for k,v in reqs[-1].headers.items() if k.lower() not in {'content-length','host','origin','referer'}}
            base=reqs[-1].post_data_json
            results={}
            for date in dates:
                for diff in (False,True):
                    payload=json.loads(json.dumps(base))
                    payload['filter']['initialDate']=f'{date}T12:00:00.000Z'
                    payload['filter']['finalDate']=f'{date}T12:00:00.000Z'
                    payload['filter']['publishers']=publishers
                    payload['diferential']=diff
                    r=await ctx.request.post(API,headers=headers,data=payload,timeout=120000)
                    if r.status not in (200,201): raise RuntimeError(f'photo {date} diff={diff} HTTP {r.status}')
                    data=await r.json(); rows=rows_of(data)
                    key=f'{date}-'+('incremental' if diff else 'cumulative')
                    (OUT/f'{key}.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
                    results[key]={
                        'status':r.status,'rows':len(rows),
                        'dates':sorted(set(str(x.get('DATE')) for x in rows)),
                        'companies':Counter(str(x.get('COMPANY')) for x in rows),
                        'domains':len(set((str(x.get('COMPANY')),str(x.get('DOMAIN'))) for x in rows)),
                        'times':dict(sorted(Counter(int(x.get('TIME')) for x in rows if x.get('TIME') is not None).items())),
                    }
            print(json.dumps({'now_et':now.isoformat(timespec='seconds'),'publishers':len(publishers),'results':results},ensure_ascii=False))
        finally:
            await browser.close()

asyncio.run(main())
