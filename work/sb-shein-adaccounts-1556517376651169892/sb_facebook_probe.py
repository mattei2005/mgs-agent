import asyncio,json,pathlib,urllib.parse
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  ctx=await browser.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
  page=await ctx.new_page();headers={};reqs=[]
  async def req(q):
   if q.url.startswith(API):
    h=await q.all_headers()
    if h.get('authorization'):headers['authorization']=h['authorization']
    u=urllib.parse.urlsplit(q.url);reqs.append({'method':q.method,'path':u.path,'query':{k:v for k,v in urllib.parse.parse_qs(u.query).items() if k in ['companies[]','source']}})
  page.on('request',req)
  await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='networkidle',timeout=90000)
  await page.get_by_text('Google',exact=True).first.click();await page.get_by_text('Facebook',exact=True).first.click()
  await page.wait_for_timeout(3000)
  r=await ctx.request.get(API+'/accounts/Facebook?companies[]=digital-trust&companies[]=digital-trust-2&source=Facebook',headers=headers,timeout=60000);assert r.status==200
  raw=await r.json();rows=raw if isinstance(raw,list) else raw.get('data',[])
  allowed=['ID','COMPANY_ID','PUBLISHER_ID','NAME','ACCOUNT_NAME','ACCOUNT_ID','TIMEZONE','CURRENCY','COUNTRY','VERTICAL','MEDIUM','LANGUAGE','ACTIVE','SOURCE','TOKEN_UPDATED_AT']
  safe=[{k:v for k,v in x.items() if k in allowed} for x in rows]
  targets=[x for x in safe if any(s in json.dumps(x).lower() for s in ['vizioid','growpower','escalate'])]
  (W/'sb-facebook-before-safe.json').write_text(json.dumps({'all_count':len(rows),'keys':list(rows[0]) if rows else [],'targets':targets},ensure_ascii=False,indent=2))
  await page.get_by_role('button',name='New Account',exact=True).click();await page.wait_for_timeout(1000)
  modal=await page.locator('[role=dialog]').all_text_contents()
  out={'url':page.url,'requests':reqs,'row_keys':list(rows[0]) if rows else [],'all_count':len(rows),'targets':targets,'modal':modal,'modal_fields':await page.locator('[role=dialog] input,[role=dialog] select,[role=dialog] textarea,[role=dialog] button').evaluate_all('(es)=>es.map(e=>({tag:e.tagName,name:e.name,type:e.type,id:e.id,placeholder:e.placeholder,text:e.innerText?.slice(0,100),value:(e.type==="password"||/token|secret|password/i.test(e.name+e.id))?"[redacted]":e.value}))')}
  if not modal:out['body_tail']=(await page.locator('body').inner_text())[-4000:]
  (W/'sb-facebook-modal-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
  await browser.close()
asyncio.run(main())
