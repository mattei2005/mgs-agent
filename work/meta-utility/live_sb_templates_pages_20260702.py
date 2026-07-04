#!/usr/bin/env python3
import asyncio, json, pathlib, re, csv
from collections import Counter, defaultdict
from playwright.async_api import async_playwright

OUT=pathlib.Path('/root/mgs-agent/work/meta-utility/live-check-20260702')
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'

async def text(loc):
    try: return await loc.inner_text(timeout=3000)
    except Exception: return ''

async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        ctx=await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent=UA)
        page=await ctx.new_page()
        requests=[]; responses=[]; req_headers={}
        async def on_req(req):
            if '/broadcast/Messenger' in req.url or '/campaigns/Messenger' in req.url:
                requests.append({'method':req.method,'url':req.url})
                req_headers[req.url]=req.headers
        async def on_resp(resp):
            if '/broadcast/Messenger' in resp.url or '/campaigns/Messenger' in resp.url:
                try:
                    data=await resp.json()
                    n=len(data) if isinstance(data,list) else None
                except Exception:
                    n=None
                responses.append({'status':resp.status,'url':resp.url,'count':n})
        page.on('request',on_req); page.on('response',on_resp)
        await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='networkidle',timeout=90000)
        await page.wait_for_timeout(2500)
        # messenger
        try:
            await page.locator('.p-dropdown').first.click(timeout=10000); await page.wait_for_timeout(500)
            await page.get_by_text('Messenger', exact=True).last.click(timeout=10000); await page.wait_for_timeout(3000)
        except Exception: pass
        # Broadcast Template live
        await page.get_by_text('Broadcast Template', exact=True).click(timeout=15000); await page.wait_for_timeout(6000)
        broadcast_url=None
        for r in reversed(requests):
            if r['method']=='GET' and '/broadcast/Messenger' in r['url']:
                broadcast_url=r['url']; break
        if not broadcast_url: raise RuntimeError('no broadcast url')
        headers={k:v for k,v in req_headers[broadcast_url].items() if not k.startswith(':') and k.lower() not in ('content-length','host')}
        headers['content-type']='application/json'
        br=await ctx.request.get(broadcast_url,headers=headers)
        broadcast=await br.json()
        # Page live. Try to click Page tab and trigger whatever current dashboard selection returns.
        await page.get_by_text('Page', exact=True).click(timeout=15000); await page.wait_for_timeout(6000)
        body=(await text(page.locator('body'))).replace('\n',' ')
        page_url=None
        for r in reversed(requests):
            if r['method']=='GET' and '/campaigns/Messenger' in r['url']:
                page_url=r['url']; break
        if not page_url: raise RuntimeError('no campaigns page url')
        pr=await ctx.request.get(page_url,headers=headers)
        pages=await pr.json()
        # If visible label/paginator can be captured, include it.
        visible=body[:5000]
        # Build by exact template name from live page rows
        page_counts=Counter((x.get('BROADCAST_TEMPLATE_NAME') or '').strip() for x in pages if x.get('BROADCAST_TEMPLATE_NAME'))
        page_status=Counter(x.get('STATUS') for x in pages)
        rows=[]
        for b in sorted(broadcast,key=lambda x:(x.get('NAME') or '').lower()):
            name=b.get('NAME') or ''
            msgs=b.get('MESSAGES') or '[]'
            try: mcount=len(json.loads(msgs)) if isinstance(msgs,str) else len(msgs or [])
            except Exception: mcount=None
            rows.append({'NAME':name,'PAGES_LIVE':page_counts.get(name,0),'MESSAGES_LIVE':mcount,'BROADCAST_PAGES_FIELD':b.get('PAGES'),'COMPANY':b.get('COMPANY'),'LANGUAGE':b.get('LANGUAGE')})
        (OUT/'broadcast-live.json').write_text(json.dumps(broadcast,ensure_ascii=False,indent=2))
        (OUT/'pages-live.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2))
        (OUT/'network.json').write_text(json.dumps({'requests':requests,'responses':responses,'broadcast_url':broadcast_url,'page_url':page_url,'visible_head':visible,'page_status':page_status},ensure_ascii=False,indent=2))
        with (OUT/'templates-live-pages.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['NAME','PAGES_LIVE','MESSAGES_LIVE','BROADCAST_PAGES_FIELD','COMPANY','LANGUAGE'])
            w.writeheader(); w.writerows(rows)
        print(json.dumps({'broadcast_templates':len(broadcast),'page_rows_live':len(pages),'templates_with_pages_live':sum(1 for r in rows if r['PAGES_LIVE']),'csv':str(OUT/'templates-live-pages.csv'),'network':str(OUT/'network.json')},ensure_ascii=False,indent=2))
        await browser.close()
if __name__=='__main__': asyncio.run(main())
