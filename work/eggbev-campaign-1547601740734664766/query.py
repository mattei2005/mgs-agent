import asyncio,json
from pathlib import Path
from collections import defaultdict
from decimal import Decimal as D
from playwright.async_api import async_playwright
P=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']);c=await b.new_context(storage_state='/tmp/gam-sb-audit-state.json');page=await c.new_page()
  for label,route,needle in [('adgroup','adgroup','/report/performance_per_campaigns'),('messenger','messenger','/report/messenger'),('message','messenger_message','/report/message')]:
   requests=[]
   def listen(r):
    if needle in r.url and r.method=='POST':requests.append(r)
   page.on('request',listen)
   await page.goto('https://app.smartbiddingdigital.com/reports/'+route,wait_until='domcontentloaded')
   for _ in range(60):
    if requests:break
    if 'auth0.com' in page.url:raise RuntimeError('LOGIN_REQUIRED')
    await page.wait_for_timeout(500)
   page.remove_listener('request',listen)
   assert requests,('No endpoint',label);assert 'Zeus - Agent' in await page.locator('body').inner_text()
   req=requests[-1];h=await req.all_headers();headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')}
   body=json.loads(req.post_data or '{}');body.update({'initialDate':'2026-09-01T15:00:00.000Z','finalDate':'2026-09-09T15:00:00.000Z','publishers':['digital-trust_eggbev'],'currency':'CAD'})
   res=await c.request.post(req.url,headers=headers,data=body,timeout=90000);assert res.status in (200,201);data=await res.json()
   (P/(label+'.json')).write_text(json.dumps({'route':route,'endpoint':req.url,'request':body,'status':res.status,'data':data},ensure_ascii=False,indent=2))
   print(label,'type',type(data).__name__,'count',len(data) if isinstance(data,(list,dict)) else None,flush=True)
   if isinstance(data,list) and data:
    print('FIELDS',list(data[0]));emp=[r for r in data if str(r.get('VERTICAL',r.get('vertical',''))).lower() in ('emp','loan','loans')]
    keys=['DATE','DOMAIN','VERTICAL','COUNTRY','UTM_CAMPAIGN','UTM_ADGROUP','CAMPAIGN_NAME','ACCOUNT_NAME','REVENUE','UTM_CONTENT','PAGE_NAME','FB_PAGEID','SOURCE']
    print('EMP_COUNT',len(emp),'EMP_SAMPLE',json.dumps([{k:r.get(k) for k in keys if k in r} for r in emp[:8]],ensure_ascii=False))
    (P/(label+'-emp.json')).write_text(json.dumps(emp,ensure_ascii=False,indent=2))
  await b.close()
asyncio.run(main())
