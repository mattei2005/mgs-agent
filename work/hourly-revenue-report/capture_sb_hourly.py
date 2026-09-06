#!/usr/bin/env python3
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

URL = 'https://app.smartbiddingdigital.com/reports/photo-by-vertical'
API = 'https://api.jbfdigital.com.br/photo/performance_per_vertical'
STATE = '/root/.local/share/mgs/smartbidding_state_headed.json'
OUT = Path('/root/mgs-agent/work/hourly-revenue-report')

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx = await browser.new_context(storage_state=STATE, viewport={'width': 1600, 'height': 1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
            page = await ctx.new_page()
            seen = []
            async def on_response(resp):
                if resp.url.split('?')[0] == API:
                    req = resp.request
                    try: payload = req.post_data_json
                    except Exception: payload = {'_raw': req.post_data}
                    try: data = await resp.json()
                    except Exception as exc: data = {'_error': type(exc).__name__}
                    seen.append({'status': resp.status, 'payload': payload, 'data': data})
            page.on('response', on_response)
            await page.goto(URL, wait_until='domcontentloaded', timeout=120000)
            for _ in range(60):
                await page.wait_for_timeout(1000)
                if seen: break
            if not seen:
                raise RuntimeError('no hourly report response captured')
            (OUT/'initial-capture.json').write_text(json.dumps(seen[-1], ensure_ascii=False, indent=2), encoding='utf-8')
            data = seen[-1]['data']
            if isinstance(data, list): rows=data
            elif isinstance(data, dict):
                rows=next((data[k] for k in ('data','rows','result','results') if isinstance(data.get(k),list)),[])
            else: rows=[]
            print(json.dumps({'status':seen[-1]['status'],'payload_keys':sorted((seen[-1]['payload'] or {}).keys()) if isinstance(seen[-1]['payload'],dict) else [],'payload':seen[-1]['payload'],'rows':len(rows),'row_keys':sorted(rows[0].keys()) if rows and isinstance(rows[0],dict) else [],'url':page.url,'title':await page.title()},ensure_ascii=False))
        finally:
            await browser.close()

asyncio.run(main())
