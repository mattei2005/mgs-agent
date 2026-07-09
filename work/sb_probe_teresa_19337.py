#!/usr/bin/env python3
import asyncio, importlib.util, json, urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright
BASE=Path('/root/mgs-agent'); API='https://api.jbfdigital.com.br'; SB_STATE='/tmp/smartbidding_state_headed.json'
def norm(v): return '' if v is None else str(v).strip()
def pub(r): return {k:norm(r.get(k)) for k in ['ID','LOGIN','USER_LOGIN','PROFILE_NAME','PAGE_NAME','PAGE_ID','FB_PAGE_ID','UTM_CAMPAIGN','STATUS','COMPANY','PUBLISHER_ID']}
async def main():
 p=await async_playwright().start(); browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
 ctx=await browser.new_context(storage_state=SB_STATE, viewport={'width':1600,'height':1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
 page=await ctx.new_page(); headers={}
 page.on('request', lambda req: asyncio.create_task(req.all_headers()).add_done_callback(lambda fut: headers.update(fut.result()) if 'api.jbfdigital.com.br' in req.url and not fut.exception() else None))
 await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000); await page.wait_for_timeout(6000)
 h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}; h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
 comps=await (await ctx.request.get(API+'/company',headers=h,timeout=120000)).json(); pubs=[]
 for c in comps:
  cname=str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ','-')
  if cname in ('digital-trust','digital-trust-2'):
   pubs += [x.get('publisherId') for x in c.get('publishers') or [] if x.get('publisherId')]
 qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
 rows=await (await ctx.request.get(API+'/campaigns/Messenger?'+qs,headers=h,timeout=120000)).json()
 targets={'id':'69dbcccc-20a5-2168-a11d-a659def1f7ec','fb':'1063903433472026','pg':'19337'}
 matches=[pub(r) for r in rows if norm(r.get('ID'))==targets['id'] or norm(r.get('FB_PAGE_ID'))==targets['fb'] or norm(r.get('PAGE_ID'))==targets['pg']]
 print(json.dumps({'rows':len(rows),'matches':matches}, ensure_ascii=False, indent=2))
 await browser.close(); await p.stop()
asyncio.run(main())
