import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
P=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/tmp/gam-sb-audit-state.json',viewport={'width':1600,'height':1000});page=await c.new_page();requests=[]
  page.on('request',lambda r:requests.append(r) if '/report/performance_per_vertical' in r.url else None)
  await page.goto('https://app.smartbiddingdigital.com/reports/vertical',wait_until='domcontentloaded')
  for _ in range(60):
   if requests:break
   if 'auth0.com' in page.url:raise RuntimeError('LOGIN_REQUIRED')
   await page.wait_for_timeout(500)
  assert requests,'Report request not observed';text=await page.locator('body').inner_text();assert 'Zeus - Agent' in text
  req=requests[-1];print('REQUEST',req.url,req.post_data)
  options=await page.locator('select').evaluate_all('(els)=>els.map(e=>({value:e.value,options:[...e.options].filter(o=>/openzed/i.test(o.textContent+o.value)).map(o=>({text:o.textContent,value:o.value}))}))')
  print('OPENZED_OPTIONS',json.dumps(options,ensure_ascii=False))
  resp=await req.response();data=await resp.json();print('INITIAL_TYPE',type(data).__name__)
  if isinstance(data,list):
   print('FIELDS',list(data[0]) if data else []);matches=[r for r in data if 'openzed' in str(r.get('DOMAIN','')).lower()];print('INITIAL_OPENZED',json.dumps(matches,ensure_ascii=False)[:6000])
  h=await req.all_headers();headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')}
  pubs=[]
  for e in options:
   for o in e['options']:
    if 'openzedfinanzas' in o['value'].lower():pubs.append(o['value'])
  if not pubs and isinstance(data,list):pubs=sorted({r['PUBLISHER'] for r in data if r.get('DOMAIN')=='openzedfinanzas'})
  assert len(pubs)==1,('Publisher discovery',pubs)
  body={'initialDate':'2026-09-01T15:00:00.000Z','finalDate':'2026-09-09T15:00:00.000Z','publishers':pubs,'currency':'CAD'}
  res=await c.request.post(req.url,headers=headers,data=body,timeout=90000);assert res.status in (200,201)
  result=await res.json();assert isinstance(result,list)
  (P/'vertical-period.json').write_text(json.dumps({'identity':'Zeus - Agent','route':page.url,'endpoint':req.url,'status':res.status,'request':body,'data':result},ensure_ascii=False,indent=2))
  print('PERIOD_ROWS',len(result));print(json.dumps(result,ensure_ascii=False)[:15000])
  await b.close()
asyncio.run(main())
