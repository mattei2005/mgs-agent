import asyncio,json,pathlib
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json',viewport={'width':1600,'height':1000});page=await c.new_page();assets=set();reqs=[]
  def req(r):
   if r.url.startswith('https://app.smartbiddingdigital.com/') and '.js' in r.url:assets.add(r.url)
   if r.url.startswith(API):reqs.append({'method':r.method,'path':r.url.split('?')[0].replace(API,'')})
  page.on('request',req)
  await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='networkidle',timeout=90000)
  await page.get_by_text('Inventory',exact=True).first.click();await page.wait_for_timeout(500)
  links=await page.locator('a[href]').evaluate_all('es=>es.map(e=>({text:e.innerText,url:e.getAttribute("href")}))')
  print('wrapper links',[x for x in links if 'wrapper' in json.dumps(x).lower()])
  found=[x for x in links if 'wrapper' in x['url'].lower()];assert found
  await page.goto('https://app.smartbiddingdigital.com'+found[0]['url'],wait_until='networkidle',timeout=90000)
  for u in sorted(assets):
   if 'Wrapper' not in u and 'wrapper' not in u:continue
   r=await c.request.get(u);text=await r.text();f=W/('bundle-'+u.rsplit('/',1)[-1].split('?')[0]);f.write_text(text);print('bundle',f.name,len(text))
  out={'url':page.url,'requests':reqs,'body':(await page.locator('body').inner_text())[-7000:],'inputs':await page.locator('input,button,select').evaluate_all('es=>es.map(e=>({tag:e.tagName,text:e.innerText?.slice(0,80),id:e.id,name:e.name,placeholder:e.placeholder,role:e.getAttribute("role")}))')}
  (W/'wrapper-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
  await b.close()
asyncio.run(main())
