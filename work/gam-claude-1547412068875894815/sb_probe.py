import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000})
  page=await c.new_page(); events=[]; tasks=[]
  async def capture(res):
   if '/report/' in res.url or '/publisher' in res.url:
    try:
     body=await res.json(); item={'url':res.url,'status':res.status,'request':res.request.post_data,'body':body}; events.append(item)
    except Exception: pass
  page.on('response',lambda r:tasks.append(asyncio.create_task(capture(r))))
  await page.goto('https://app.smartbiddingdigital.com/reports/adgroup',wait_until='domcontentloaded',timeout=90000)
  await page.wait_for_timeout(5000)
  if 'auth0.com' in page.url:
   import subprocess
   result=subprocess.run(['bash','-lc',"set -a; source /root/mgs-agent/.env >/dev/null 2>&1; set +a; op item get 'Zeus - Smartbidding Dashboard' --vault 'MGS Conteúdo' --format json"],capture_output=True,text=True,check=True)
   item=json.loads(result.stdout); fields={f.get('id'):f.get('value') for f in item.get('fields',[])}
   assert fields.get('username') and fields.get('password'), 'Missing canonical login fields'
   await page.locator('input[name="username"]').fill(fields['username'])
   await page.locator('input[name="password"]').fill(fields['password'])
   await page.get_by_role('button',name='Continue',exact=True).click()
   await page.wait_for_timeout(18000)
   if 'auth0.com' in page.url:
    print('AUTH_BLOCKED', (await page.locator('body').inner_text())[:500]); await b.close(); return
  else: await page.wait_for_timeout(13000)
  await c.storage_state(path='/tmp/gam-sb-audit-state.json')
  Path('/tmp/gam-sb-audit-state.json').chmod(0o600)
  print('URL',page.url.split('?')[0]); print('BODY',(await page.locator('body').inner_text())[:14000])
  print('INPUTS',await page.locator('input').evaluate_all('(els)=>els.map(e=>({type:e.type,placeholder:e.placeholder,value:e.value,aria:e.getAttribute("aria-label")}))') if 'smartbiddingdigital.com' in page.url else 'LOGIN_WALL')
  await asyncio.gather(*tasks); (ROOT/'sb-probe.json').write_text(json.dumps(events,ensure_ascii=False)); print('EVENTS',[(x['url'],x['status'],type(x['body']).__name__,len(x['body']) if hasattr(x['body'],'__len__') else None,x['request']) for x in events]); await b.close()
asyncio.run(main())
