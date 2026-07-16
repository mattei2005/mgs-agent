#!/usr/bin/env python3
import argparse,asyncio,json,pathlib,urllib.parse
from playwright.async_api import async_playwright
ap=argparse.ArgumentParser();ap.add_argument('--state',default='/root/.local/share/mgs/smartbidding_state_ares.json');args=ap.parse_args()
STATE=args.state;RUN=pathlib.Path('/root/mgs-agent/work/sb-purple-pages-excel-20260716');API='https://api.jbfdigital.com.br'
async def main():
 br=json.load(open('/tmp/sb-ares-live-cron-design.json'))['rows'];target=next(r for r in br if r.get('NAME')=='Infinitynexx - MX-CC-ES/ES-ZW-SR - g004-d Joe');pages=json.load(open(RUN/'sb-pages-live.json'))['rows'];page_row=next(r for r in pages if r.get('BROADCAST_TEMPLATE_ID')==target.get('ID'))
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']);c=await b.new_context(storage_state=STATE,viewport={'width':1600,'height':1000});page=await c.new_page();h={}
  async def req(r):
   if API in r.url:h.update(await r.all_headers())
  page.on('request',req);await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=60000);await page.wait_for_timeout(5000);hh={k:v for k,v in h.items() if k.lower() in {'authorization','accept','content-type'}};hh.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
  paths=[f'/broadcast/Messenger/{target["ID"]}',f'/broadcast/Messenger/trail/{target["ID"]}',f'/campaigns/Messenger/{page_row["ID"]}',f'/campaigns/Messenger/trail/{page_row["ID"]}'];out=[]
  for path in paths:
   r=await c.request.get(API+path,headers=hh,timeout=120000);txt=await r.text()
   try:d=json.loads(txt)
   except:d={'text':txt[:500]}
   out.append({'path':path,'status':r.status,'type':type(d).__name__,'data':d})
  (RUN/'sb-api-trail-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps([{'path':x['path'],'status':x['status'],'type':x['type'],'keys':list(x['data'])[:30] if isinstance(x['data'],dict) else None,'len':len(x['data']) if hasattr(x['data'],'__len__') else None} for x in out],ensure_ascii=False));await b.close()
asyncio.run(main())
