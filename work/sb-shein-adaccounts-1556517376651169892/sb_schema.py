import asyncio,json,pathlib,re
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json',viewport={'width':1600,'height':1000});page=await c.new_page();assets=set()
  page.on('request',lambda r:assets.add(r.url) if r.url.startswith('https://app.smartbiddingdigital.com/') and '.js' in r.url else None)
  await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='networkidle',timeout=90000)
  await page.get_by_text('Google',exact=True).first.click();await page.get_by_text('Facebook',exact=True).first.click();await page.wait_for_timeout(2500)
  await page.get_by_role('button',name='New Account',exact=True).click();await page.wait_for_timeout(500)
  details=await page.locator('input,select,textarea,form').evaluate_all('''es=>es.map(e=>({tag:e.tagName,name:e.name,id:e.id,type:e.type,required:e.required,placeholder:e.placeholder,classes:e.className,label:e.labels?Array.from(e.labels).map(l=>l.innerText):[],value:/token|secret|password/i.test(e.name+e.id)||e.type==='password'?'[redacted]':e.value}))''')
  for u in sorted(assets):
   r=await c.request.get(u);text=await r.text()
   if any(s in text for s in ['New Facebook Account','ACCOUNT_NAME','/accounts/']):
    f=W/('bundle-'+u.rsplit('/',1)[-1].split('?')[0]);f.write_text(text)
    print('bundle',f.name,len(text))
  out={'fields':details,'modal_footer':(await page.locator('body').inner_text())[-500:]};(W/'sb-form-fields.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
  await b.close()
asyncio.run(main())
