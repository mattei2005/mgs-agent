#!/usr/bin/env python3
import asyncio, json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from playwright.async_api import async_playwright

STATE=Path('/tmp/smartbidding_state_headed.json')
OUT=Path('/root/mgs-agent/work/sb-sms-backfill')
API='https://api.jbfdigital.com.br/report/performance_per_sms'
TARGET='digital-trust_creditoparaveiculo'

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        ctx=await browser.new_context(storage_state=str(STATE),viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
        page=await ctx.new_page()
        req_future=asyncio.get_running_loop().create_future()
        async def capture_req(req):
            if '/report/performance_per_sms' in req.url and not req_future.done():
                req_future.set_result(req)
        page.on('request',capture_req)
        await page.goto('https://app.smartbiddingdigital.com/reports/sms',wait_until='domcontentloaded',timeout=120000)
        req=await asyncio.wait_for(req_future,timeout=120)
        headers=await req.all_headers()
        safe_headers={k:v for k,v in headers.items() if k.lower() in ('authorization','content-type','origin','referer','user-agent')}
        payload={
            'initialDate':'2020-01-01T00:00:00.000Z',
            'finalDate':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            'publishers':[TARGET],
            'currency':None,
        }
        resp=await ctx.request.post(API,headers=safe_headers,data=payload,timeout=180000)
        if resp.status not in (200,201):
            raise RuntimeError(f'Historical SMS API HTTP {resp.status}: {(await resp.text())[:300]}')
        rows=await resp.json()
        if not isinstance(rows,list): raise RuntimeError('Historical response is not a list')
        wrong=[r for r in rows if r.get('PUBLISHER')!=TARGET or r.get('DOMAIN') not in ('creditoparaveiculo','creditoparaveiculo.com')]
        if wrong: raise RuntimeError(f'Historical response leaked {len(wrong)} non-target rows')
        rows.sort(key=lambda r:(r.get('DATE',''),str(r.get('PK_JBF_PERFORMANCE_PER_SMS',''))))
        (OUT/'historical-creditoparaveiculo-raw.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        dates=sorted({r.get('DATE') for r in rows if r.get('DATE')})
        revenue=sum((Decimal(str(r.get('REVENUE') or 0)) for r in rows),Decimal('0'))
        net=sum((Decimal(str(r.get('NET_REVENUE') or 0)) for r in rows),Decimal('0'))
        summary={'status':'OK','rows':len(rows),'dates':len(dates),'first_date':dates[0] if dates else None,'last_date':dates[-1] if dates else None,'revenue':str(revenue),'net_revenue':str(net),'publisher':TARGET}
        (OUT/'historical-creditoparaveiculo-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
        print(json.dumps(summary,ensure_ascii=False))
        await browser.close()

asyncio.run(main())
