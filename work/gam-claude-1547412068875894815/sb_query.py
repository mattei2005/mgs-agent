import asyncio,json
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from playwright.async_api import async_playwright
P=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']); c=await b.new_context(storage_state='/tmp/gam-sb-audit-state.json',viewport={'width':1600,'height':1000}); page=await c.new_page()
  async with page.expect_request(lambda r:'/report/performance_per_campaigns' in r.url,timeout=90000) as pending:
   await page.goto('https://app.smartbiddingdigital.com/reports/adgroup',wait_until='domcontentloaded')
  request=await pending.value; h=await request.all_headers(); headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')}; assert 'authorization' in headers
  results=[]
  for curr in ['CAD',None]:
   body={'initialDate':'2026-09-07T15:00:00.000Z','finalDate':'2026-09-08T15:00:00.000Z','publishers':['digital-trust_yolokfx'],'currency':curr}
   res=await c.request.post(request.url,headers=headers,data=body,timeout=90000); data=await res.json();results.append({'status':res.status,'request':body,'data':data})
   if not isinstance(data,list):print('ERROR',res.status,str(data)[:300]);continue
   by=defaultdict(lambda:defaultdict(lambda:Decimal(0)))
   for r in data:
    for f in ['REVENUE','NET_REVENUE','REVENUE_ESTIMATED','REVENUE_TOTAL']:by[(r.get('DATE'),r.get('ACCOUNT_NAME'),r.get('CUSTOMER_ID'))][f]+=Decimal(str(r.get(f,0)))
   print('QUERY',curr,'STATUS',res.status,'COUNT',len(data),'PUBLISHERS',sorted(set(r.get('PUBLISHER','') for r in data)),'KEY_UNIQUE',len(set(r['PK_JBF_PERFORMANCE_PER_ADGROUP'] for r in data)))
   print(json.dumps([{'date':k[0],'account':k[1],'account_id':k[2],**v} for k,v in sorted(by.items())],ensure_ascii=False,default=str))
  (P/'sb-yolo-queries.json').write_text(json.dumps(results,ensure_ascii=False))
  print('SELECTS',await page.locator('select').evaluate_all('(els)=>els.map(e=>({text:e.innerText,value:e.value}))'))
  await b.close()
asyncio.run(main())
