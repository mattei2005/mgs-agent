#!/usr/bin/env python3
import asyncio,json,pathlib,urllib.parse,csv
from collections import Counter
from playwright.async_api import async_playwright
OUT=pathlib.Path('/root/mgs-agent/work/meta-utility/live-check-20260702-full')
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
DT2=['digital-trust-2_cliquet','digital-trust-2_openzed','digital-trust-2_openzedfinanzas','digital-trust-2_wantabrand','digital-trust-2_wantabrandfinance','digital-trust-2_wavesbee','digital-trust-2_zuout','digital-trust-2_zuoutfinanzas']
async def main():
 OUT.mkdir(parents=True,exist_ok=True)
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  ctx=await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent=UA)
  page=await ctx.new_page(); reqs=[]; hdr={}
  async def on_req(req):
   if '/campaigns/Messenger' in req.url or '/broadcast/Messenger' in req.url:
    reqs.append({'method':req.method,'url':req.url}); hdr[req.url]=req.headers
  page.on('request',on_req)
  await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='networkidle',timeout=90000); await page.wait_for_timeout(2500)
  try:
   await page.locator('.p-dropdown').first.click(timeout=10000); await page.wait_for_timeout(500); await page.get_by_text('Messenger',exact=True).last.click(timeout=10000); await page.wait_for_timeout(2500)
  except Exception: pass
  await page.get_by_text('Broadcast Template',exact=True).click(timeout=15000); await page.wait_for_timeout(4000)
  burl=[r['url'] for r in reqs if '/broadcast/Messenger' in r['url']][-1]
  h={k:v for k,v in hdr[burl].items() if not k.startswith(':') and k.lower() not in ('content-length','host')}; h['content-type']='application/json'
  br=await ctx.request.get(burl,headers=h); broadcast=await br.json()
  await page.get_by_text('Page',exact=True).click(timeout=15000); await page.wait_for_timeout(5000)
  purl=[r['url'] for r in reqs if '/campaigns/Messenger' in r['url']][-1]
  parsed=urllib.parse.urlparse(purl); qs=urllib.parse.parse_qs(parsed.query)
  companies=qs.get('companies[]',[])
  full_companies=companies+[c for c in DT2 if c not in companies]
  q='&'.join('companies[]='+urllib.parse.quote(c) for c in full_companies)+'&source=Messenger'
  full_url='https://api.jbfdigital.com.br/campaigns/Messenger?'+q
  pr=await ctx.request.get(full_url,headers=h); pages=await pr.json()
  page_counts=Counter((x.get('BROADCAST_TEMPLATE_NAME') or '').strip() for x in pages if x.get('BROADCAST_TEMPLATE_NAME'))
  rows=[]
  for b in sorted(broadcast,key=lambda x:(x.get('NAME') or '').lower()):
   name=b.get('NAME') or ''; msgs=b.get('MESSAGES') or '[]'
   try: mcount=len(json.loads(msgs)) if isinstance(msgs,str) else len(msgs or [])
   except Exception: mcount=None
   rows.append({'NAME':name,'PAGES_LIVE':page_counts.get(name,0),'MESSAGES_LIVE':mcount,'BROADCAST_PAGES_FIELD':b.get('PAGES'),'COMPANY':b.get('COMPANY'),'LANGUAGE':b.get('LANGUAGE')})
  (OUT/'broadcast-live.json').write_text(json.dumps(broadcast,ensure_ascii=False,indent=2)); (OUT/'pages-live-fullquery.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)); (OUT/'meta.json').write_text(json.dumps({'broadcast_templates':len(broadcast),'page_rows':len(pages),'companies':full_companies,'full_url':full_url},ensure_ascii=False,indent=2))
  with (OUT/'templates-live-pages.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['NAME','PAGES_LIVE','MESSAGES_LIVE','BROADCAST_PAGES_FIELD','COMPANY','LANGUAGE']); w.writeheader(); w.writerows(rows)
  print(json.dumps({'broadcast_templates':len(broadcast),'page_rows_live':len(pages),'companies':len(full_companies),'templates_with_pages_live':sum(1 for r in rows if r['PAGES_LIVE']),'csv':str(OUT/'templates-live-pages.csv')},ensure_ascii=False,indent=2))
  await browser.close()
if __name__=='__main__': asyncio.run(main())
