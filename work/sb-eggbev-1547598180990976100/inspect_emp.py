import asyncio,json,re
from pathlib import Path
from collections import defaultdict
from decimal import Decimal as D
from playwright.async_api import async_playwright
P=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']);c=await b.new_context(storage_state='/tmp/gam-sb-audit-state.json');page=await c.new_page();requests=[]
  page.on('request',lambda r:requests.append(r) if '/report/' in r.url and r.method=='POST' else None)
  await page.goto('https://app.smartbiddingdigital.com/reports/url',wait_until='domcontentloaded')
  for _ in range(60):
   if any(('url' in r.url.lower() or 'queryBuilder' in r.url or 'performance_per_operation' in r.url) for r in requests):break
   if 'auth0.com' in page.url:raise RuntimeError('LOGIN_REQUIRED')
   await page.wait_for_timeout(500)
  assert 'Zeus - Agent' in await page.locator('body').inner_text()
  candidates=[r for r in requests if 'url' in r.url.lower() or 'queryBuilder' in r.url or 'performance_per_operation' in r.url]
  print('CANDIDATES',[(r.url,r.post_data) for r in candidates][:2])
  if not candidates:
   print('ENDPOINTS',sorted({r.url for r in requests}));await b.close();return
  req=candidates[-1];h=await req.all_headers();headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')}
  body=json.loads(req.post_data);body.update({'initialDate':'2026-09-01T15:00:00.000Z','finalDate':'2026-09-09T15:00:00.000Z','publishers':['digital-trust_eggbev'],'currency':'CAD'})
  res=await c.request.post(req.url,headers=headers,data=body,timeout=90000);assert res.status in (200,201);data=await res.json()
  (P/'url-period.json').write_text(json.dumps({'request':body,'endpoint':req.url,'status':res.status,'data':data},ensure_ascii=False,indent=2))
  print('TYPE',type(data).__name__)
  if isinstance(data,list):
   print('ROWS',len(data),'FIELDS',list(data[0]) if data else [])
   rows=[r for r in data if r.get('vertical',r.get('VERTICAL'))=='emp'];print('EMP_ROWS',len(rows),'LOAN_URLS',sorted({r.get('url','') for r in rows}))
  else:print('KEYS',list(data) if isinstance(data,dict) else '')
  await b.close()
asyncio.run(main())
