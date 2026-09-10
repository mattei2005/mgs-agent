import asyncio,json
from collections import defaultdict
from decimal import Decimal as D
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
  req=requests[-1];print('ROUTE',page.url)
  options=await page.locator('select').evaluate_all('(els)=>els.map(e=>({value:e.value,options:[...e.options].filter(o=>/eggbev/i.test(o.textContent+o.value)).map(o=>({text:o.textContent,value:o.value}))}))')
  resp=await req.response();data=await resp.json()
  if isinstance(data,list):
   assert all(isinstance(r,dict) for r in data)
  h=await req.all_headers();headers={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','x-user-email','x-api-key')}
  pubs=[]
  for e in options:
   for o in e['options']:
    if 'eggbev' in o['value'].lower():pubs.append(o['value'])
  if not pubs and isinstance(data,list):pubs=sorted({r['PUBLISHER'] for r in data if r.get('DOMAIN')=='eggbev'})
  assert len(pubs)==1,('Publisher discovery',pubs)
  body={'initialDate':'2026-09-01T15:00:00.000Z','finalDate':'2026-09-09T15:00:00.000Z','publishers':pubs,'vertical':[],'currency':'CAD'}
  res=await c.request.post(req.url,headers=headers,data=body,timeout=90000);assert res.status in (200,201)
  result=await res.json();assert isinstance(result,list)
  (P/'vertical-period.json').write_text(json.dumps({'identity':'Zeus - Agent','route':page.url,'endpoint':req.url,'status':res.status,'request':body,'data':result},ensure_ascii=False,indent=2))
  key='PK_JBF_PERFORMANCE_PER_VERTICAL';assert len({r[key] for r in result})==len(result)
  assert all(r['PUBLISHER']==pubs[0] and r['DOMAIN']=='eggbev' and '2026-09-01'<=r['DATE']<='2026-09-09' for r in result)
  daily=[]
  for d in range(1,10):
   day=f'2026-09-{d:02}';q={**body,'initialDate':day+'T15:00:00.000Z','finalDate':day+'T15:00:00.000Z'}
   res=await c.request.post(req.url,headers=headers,data=q,timeout=90000);assert res.status in (200,201);rows=await res.json();assert isinstance(rows,list) and all(r['DATE']==day for r in rows)
   daily.extend(rows)
  assert len({r[key] for r in daily})==len(daily)
  assert {r[key]:r for r in daily}=={r[key]:r for r in result}
  groups=defaultdict(lambda:{'rows':0,'gross':D(0),'net':D(0)});days=defaultdict(set)
  for r in result:
   g=groups[(r['COUNTRY'],r['VERTICAL'])];g['rows']+=1;g['gross']+=D(str(r['REVENUE']));g['net']+=D(str(r['NET_REVENUE']));days[r['COUNTRY']].add(r['DATE'])
  summary={'identity':'Zeus - Agent','publisher':pubs[0],'period':['2026-09-01','2026-09-09'],'currency':'CAD','rows':len(result),'daily_combined_exact_match':True,'groups':[{'country':k[0],'vertical':k[1],**v,'days':sorted(days[k[0]])} for k,v in sorted(groups.items())]}
  (P/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str));print(json.dumps(summary,ensure_ascii=False,default=str))
  await b.close()
asyncio.run(main())
