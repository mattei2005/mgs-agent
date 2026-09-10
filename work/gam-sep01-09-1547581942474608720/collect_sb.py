import asyncio,json,re
from pathlib import Path
from collections import Counter
from playwright.async_api import async_playwright
P=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/tmp/gam-sb-audit-state.json',viewport={'width':1600,'height':1000})
  page=await c.new_page()
  requests=[]
  page.on('request',lambda r: requests.append(r) if '/report/performance_per_campaigns' in r.url else None)
  await page.goto('https://app.smartbiddingdigital.com/reports/adgroup',wait_until='domcontentloaded')
  for i in range(40):
   if requests:break
   if 'auth0.com' in page.url:raise RuntimeError('SB_LOGIN_REQUIRED')
   await page.wait_for_timeout(500)
  assert requests,'SB request not observed'
  text=await page.locator('body').inner_text()
  assert 'Zeus - Agent' in text,'Identity not verified'
  req=requests[-1];h=await req.all_headers();headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')}
  assert 'authorization' in headers
  output=[]
  for n in range(1,10):
   day=f'2026-09-{n:02}'
   body={'initialDate':day+'T15:00:00.000Z','finalDate':day+'T15:00:00.000Z','publishers':['digital-trust_yolokfx'],'currency':'CAD'}
   res=await c.request.post(req.url,headers=headers,data=body,timeout=90000)
   assert res.status in (200,201),f'HTTP {res.status}'
   data=await res.json();assert isinstance(data,list)
   assert all(r['DATE']==day and r['DOMAIN']=='yolokfx' for r in data)
   assert len({r['PK_JBF_PERFORMANCE_PER_ADGROUP'] for r in data})==len(data)
   output.append({'request':body,'status':res.status,'data':data})
   (P/'sb-daily.json').write_text(json.dumps(output,ensure_ascii=False))
   print(day,'rows',len(data),flush=True)
  body={'initialDate':'2026-09-01T15:00:00.000Z','finalDate':'2026-09-09T15:00:00.000Z','publishers':['digital-trust_yolokfx'],'currency':'CAD'}
  res=await c.request.post(req.url,headers=headers,data=body,timeout=90000);assert res.status in (200,201)
  data=await res.json();assert isinstance(data,list)
  key='PK_JBF_PERFORMANCE_PER_ADGROUP';daily={r[key]:r for q in output for r in q['data']};combined={r[key]:r for r in data}
  assert len(data)==len(combined) and daily==combined,'Combined/daily mismatch'
  (P/'sb-verification.json').write_text(json.dumps({'identity':'Zeus - Agent','days':9,'daily_rows':len(daily),'combined_rows':len(data),'combined_exact_match':True,'endpoint':req.url,'currency':'CAD'},ensure_ascii=False,indent=2))
  print('VERIFIED',len(daily),'daily and combined exact match')
  await b.close()
asyncio.run(main())
