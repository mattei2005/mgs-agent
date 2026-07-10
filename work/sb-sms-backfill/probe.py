#!/usr/bin/env python3
import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright

STATE=Path('/tmp/smartbidding_state_headed.json')
OUT=Path('/root/mgs-agent/work/sb-sms-backfill')
OUT.mkdir(parents=True, exist_ok=True)

async def main():
    captured=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        kwargs={
            'viewport':{'width':1600,'height':1000},
            'user_agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        }
        if STATE.exists(): kwargs['storage_state']=str(STATE)
        ctx=await browser.new_context(**kwargs)
        page=await ctx.new_page()
        async def on_response(resp):
            if '/report/performance_per_sms' not in resp.url: return
            req=resp.request
            try: body=await resp.json()
            except Exception:
                try: body=(await resp.text())[:5000]
                except Exception: body=None
            captured.append({'url':resp.url,'status':resp.status,'method':req.method,'post_data':req.post_data,'response':body})
        page.on('response',on_response)
        await page.goto('https://app.smartbiddingdigital.com/reports/sms',wait_until='domcontentloaded',timeout=120000)
        await page.wait_for_timeout(15000)
        title=await page.title()
        text=(await page.locator('body').inner_text())[:3000]
        result={'final_url':page.url,'title':title,'botguard':'BotGuardError' in text,'auth0':'auth0.com' in page.url,'captures':captured}
        (OUT/'probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps({'final_url':page.url,'title':title,'botguard':result['botguard'],'auth0':result['auth0'],'captures':len(captured),'statuses':[c['status'] for c in captured]}))
        await browser.close()

asyncio.run(main())
