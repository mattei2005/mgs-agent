import asyncio,json
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from urllib.parse import urlencode
from playwright.async_api import async_playwright
P=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']);c=await b.new_context(storage_state='/tmp/gam-sb-audit-state.json');page=await c.new_page()
  async with page.expect_request(lambda r:'/report/performance_per_campaigns' in r.url,timeout=90000) as pending:await page.goto('https://app.smartbiddingdigital.com/reports/adgroup',wait_until='domcontentloaded')
  req=await pending.value;h=await req.all_headers();headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')}
  results=[];single=[]
  for day in ('2026-09-07','2026-09-08'):
   body={'initialDate':day+'T15:00:00.000Z','finalDate':day+'T15:00:00.000Z','publishers':['digital-trust_yolokfx'],'currency':'CAD'}
   res=await c.request.post(req.url,headers=headers,data=body,timeout=90000);data=await res.json();assert isinstance(data,list);assert all(r['DATE']==day and r['DOMAIN']=='yolokfx' for r in data);single+=data;results.append({'type':'adgroup','status':res.status,'request':body,'data':data});print('DAY',day,'ROWS',len(data),'SUM',sum(Decimal(str(r['REVENUE'])) for r in data))
  initial=json.loads((P/'sb-yolo-queries.json').read_text())[0]['data'];key='PK_JBF_PERFORMANCE_PER_ADGROUP';a={r[key]:r for r in initial};s={r[key]:r for r in single};print('COMBINED_SINGLE_EXACT',a==s,'UNIQUE',len(s));assert a==s
  params=[('initialDate','2026-09-07T15:00:00.000Z'),('finalDate','2026-09-08T15:00:00.000Z'),('publishers[]','digital-trust_yolokfx'),('currency','CAD')]
  url='https://api.jbfdigital.com.br/report/performance_per_domain?'+urlencode(params);res=await c.request.get(url,headers=headers,timeout=90000);data=await res.json();results.append({'type':'domain','status':res.status,'url':url,'data':data});print('DOMAIN',res.status,json.dumps(data,ensure_ascii=False)[:5500]);
  (P/'sb-yolo-verification.json').write_text(json.dumps(results,ensure_ascii=False));await b.close()
asyncio.run(main())
