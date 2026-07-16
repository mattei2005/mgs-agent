#!/usr/bin/env python3
import argparse, asyncio, json, pathlib, urllib.parse
from playwright.async_api import async_playwright
ap=argparse.ArgumentParser();ap.add_argument('--state',default='/root/.local/share/mgs/smartbidding_state_ares.json');ap.add_argument('--out',default='/root/mgs-agent/work/sb-purple-pages-excel-20260716/sb-pages-live.json');args=ap.parse_args()
STATE=args.state
OUT=pathlib.Path(args.out)
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent=UA)
  page=await ctx.new_page(); headers={}
  async def on_req(req):
   if 'api.jbfdigital.com.br/company' in req.url: headers.update(await req.all_headers())
  page.on('request',on_req)
  await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=90000)
  await page.wait_for_timeout(5000)
  h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}
  h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
  if 'authorization' not in {k.lower() for k in h}: raise RuntimeError('Ares auth header not captured')
  rc=await ctx.request.get('https://api.jbfdigital.com.br/company',headers=h,timeout=120000); companies=await rc.json()
  pubs=[]
  for c in companies if isinstance(companies,list) else []:
   for pub in c.get('publishers') or []:
    if pub.get('active') and pub.get('publisherId'): pubs.append(pub['publisherId'])
  qs='&'.join('companies[]='+urllib.parse.quote(str(x)) for x in pubs)+'&source=Messenger'
  r=await ctx.request.get('https://api.jbfdigital.com.br/campaigns/Messenger?'+qs,headers=h,timeout=120000); rows=await r.json()
  if r.status!=200 or not isinstance(rows,list): raise RuntimeError(f'campaigns response {r.status} {type(rows).__name__}')
  OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps({'publishers':pubs,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'publishers':len(pubs),'rows':len(rows),'keys':sorted(rows[0].keys()) if rows else []},ensure_ascii=False))
  await browser.close()
asyncio.run(main())
