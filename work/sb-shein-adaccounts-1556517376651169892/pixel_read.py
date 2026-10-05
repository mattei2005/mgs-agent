import asyncio,json,pathlib,re
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json',viewport={'width':1600,'height':1000});page=await c.new_page();h={}
  async def req(q):
   if q.url.startswith(API):
    hs=await q.all_headers()
    if hs.get('authorization'):h['authorization']=hs['authorization']
  page.on('request',req)
  pubs=json.load(open(W/'publishers-safe.json'));selected=[x for x in pubs if x['publisherName'].lower() in ['growpowerhub','escalatepower','boostingecon','yolokfx','mavroa']];assert len(selected)==5
  await page.goto('https://app.smartbiddingdigital.com/company/digital-trust/yolokfx/wrapper',wait_until='networkidle',timeout=90000)
  out={}
  for x in selected:
   key=x['publisherId'];r=await c.request.get(API+'/wrapperconfig/'+key,headers=h);assert r.status==200;v=await r.json()
   s=await c.request.get(API+'/wrapperconfig/'+key+'/status',headers=h);assert s.status==200
   # Only pixel configuration is projected; wrapper contains private sections.
   def project(z):
    if isinstance(z,dict):return {k:({'present':bool(a),'value':'[redacted]' if a else ''} if re.search(r'token|secret|password|credential',k,re.I) else project(a)) for k,a in z.items()}
    if isinstance(z,list):return [project(a) for a in z]
    return z
   out[key]={'companyId':x['companyId'],'publisherName':x['publisherName'],'url':x['url'],'top_keys':list(v),'config_keys':list(v['config']),'pixels':project(v['config'].get('pixels')),'status':await s.json()}
  (W/'pixel-before-safe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
  await page.get_by_text('Pixels',exact=True).click();await page.get_by_role('button',name='Add pixel',exact=True).click()
  print('pixel modal',(await page.locator('body').inner_text())[-2000:])
  print('pixel fields',await page.locator('input,select,textarea').evaluate_all('es=>es.map(e=>({tag:e.tagName,id:e.id,name:e.name,type:e.type,placeholder:e.placeholder}))'))
  await b.close()
asyncio.run(main())
