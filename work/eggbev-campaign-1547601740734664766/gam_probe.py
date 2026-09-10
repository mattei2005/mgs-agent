import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
P=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']);c=await b.new_context(storage_state='/tmp/gam-sb-audit-state.json');page=await c.new_page();requests=[]
  page.on('request',lambda r:requests.append(r) if '/report/' in r.url and r.method=='POST' else None)
  await page.goto('https://app.smartbiddingdigital.com/reports/gam-key-values',wait_until='domcontentloaded')
  for _ in range(60):
   if any('/last_update' not in r.url for r in requests):break
   if 'auth0.com' in page.url:raise RuntimeError('LOGIN_REQUIRED')
   await page.wait_for_timeout(500)
  assert 'Zeus - Agent' in await page.locator('body').inner_text()
  candidates=[r for r in requests if '/last_update' not in r.url]
  if not candidates:
   await page.get_by_text('Select a key',exact=True).click();await page.wait_for_timeout(600)
   print('KEY_OPTIONS',(await page.locator('body').inner_text())[-4500:])
   option=page.get_by_text('utm_campaign',exact=True)
   if await option.count()==1:
    await option.click()
    for _ in range(30):
     if any('/last_update' not in r.url for r in requests):break
     await page.wait_for_timeout(500)
   candidates=[r for r in requests if '/last_update' not in r.url]
  print('REQUESTS',[(r.url,r.post_data) for r in candidates])
  (P/'gam-route-discovery.json').write_text(json.dumps({'route':page.url,'requests':[{'endpoint':r.url,'body':json.loads(r.post_data or '{}')} for r in candidates]},ensure_ascii=False,indent=2))
  if candidates:
   req=candidates[-1];h=await req.all_headers();headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')};body=json.loads(req.post_data or '{}');body.update({'initialDate':'2026-09-01T15:00:00.000Z','finalDate':'2026-09-09T15:00:00.000Z','publishers':['digital-trust_eggbev'],'currency':'CAD'})
   res=await c.request.post(req.url,headers=headers,data=body,timeout=90000);print('STATUS',res.status);assert res.status in (200,201);data=await res.json()
   (P/'gam-keyvalues.json').write_text(json.dumps({'request':body,'endpoint':req.url,'data':data},ensure_ascii=False,indent=2));print('TYPE',type(data).__name__,'COUNT',len(data));print('SAMPLE',json.dumps(data[:2] if isinstance(data,list) else list(data),ensure_ascii=False))
  await b.close()
asyncio.run(main())
