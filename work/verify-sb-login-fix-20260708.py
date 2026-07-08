#!/usr/bin/env python3
import asyncio,json,urllib.parse
SB_STATE='/tmp/smartbidding_state_headed.json'; API='https://api.jbfdigital.com.br'; TARGET='01b78b7d-ad85-73a8-9ca5-a91b8799d2da'
async def main():
 from playwright.async_api import async_playwright
 p=await async_playwright().start(); b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
 ctx=await b.new_context(storage_state=SB_STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
 page=await ctx.new_page(); headers={}
 async def on_req(req):
  if 'api.jbfdigital.com.br' in req.url: headers.update(await req.all_headers())
 page.on('request',on_req); await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=60000); await page.wait_for_timeout(5000)
 h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}; h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
 comp=await (await ctx.request.get(API+'/company',headers=h,timeout=120000)).json(); pubs=[]
 for c in comp:
  cname=str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ','-')
  if cname in ('digital-trust','digital-trust-2'):
   pubs += [pub.get('publisherId') for pub in c.get('publishers') or [] if pub.get('publisherId')]
 qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
 rows=await (await ctx.request.get(API+'/campaigns/Messenger?'+qs,headers=h,timeout=120000)).json()
 row=next(r for r in rows if r.get('ID')==TARGET)
 out={k:row.get(k) for k in ['ID','LOGIN','USER_LOGIN','MESSENGER_USER_ID','PROFILE_NAME','PAGE_NAME','PAGE_ID','FB_PAGE_ID','UTM_CAMPAIGN','STATUS','COMPANY']}
 print(json.dumps(out,ensure_ascii=False,indent=2))
 await b.close(); await p.stop()
asyncio.run(main())
