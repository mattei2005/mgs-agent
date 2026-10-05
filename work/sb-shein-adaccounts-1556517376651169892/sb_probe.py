import asyncio,json,re,subprocess,os,pathlib
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');W.mkdir(exist_ok=True)
API='https://api.jbfdigital.com.br'
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled','--disable-dev-shm-usage'])
  ctx=await browser.new_context(viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
  page=await ctx.new_page();headers={};requests=[]
  async def on_request(req):
   if req.url.startswith(API):
    h=await req.all_headers()
    if h.get('authorization'):headers['authorization']=h['authorization']
    requests.append({'method':req.method,'path':req.url.split('?')[0].replace(API,''),'query_keys':list(__import__('urllib.parse',fromlist=['parse_qs']).parse_qs(__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(req.url).query))})
  page.on('request',on_request)
  await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=90000)
  if await page.locator('input[type=password]').count():
   item=json.loads(subprocess.check_output(['op','item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--format','json','--reveal']))
   f={x.get('id'):x.get('value') for x in item.get('fields',[])}
   user=next((x.get('value') for x in item['fields'] if x.get('id')=='username' and x.get('value')),None)
   password=next((x.get('value') for x in item['fields'] if x.get('id')=='password' and x.get('value')),None)
   assert user and password
   await page.locator('input[name=username],input[type=email]').first.fill(user)
   await page.locator('input[type=password]').fill(password)
   await page.get_by_role('button',name=re.compile('Continue|Log in',re.I)).first.click()
   await page.wait_for_url('https://app.smartbiddingdigital.com/**',timeout=90000)
  await page.wait_for_timeout(5000)
  assert headers.get('authorization'),'missing authenticated API header'
  r=await ctx.request.get(API+'/company',headers=headers,timeout=60000);assert r.status==200
  raw=await r.json();safe=[]
  # Explicit allowlisted schema projection; never persist company raw fields.
  companies=raw if isinstance(raw,list) else raw.get('data',[])
  for c in companies:
   cid=c.get('companyId') or c.get('ID') or c.get('id');name=c.get('name') or c.get('NAME')
   pubs=c.get('publishers') or c.get('Publishers') or []
   if str(cid) in ['digital-trust','digital-trust-2'] or str(name).lower() in ['digital trust','digital trust 2']:
    for a in pubs:safe.append({'companyId':cid,'companyName':name,'publisherId':a.get('publisherId') or a.get('id') or a.get('ID'),'publisherName':a.get('name') or a.get('NAME'),'url':a.get('url') or a.get('URL'),'active':a.get('active')})
  (W/'publishers-safe.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2))
  state='/root/.local/share/mgs/smartbidding_state_headed.json';await ctx.storage_state(path=state);os.chmod(state,0o600)
  out={'url':page.url,'title':await page.title(),'body':(await page.locator('body').inner_text())[:5000],'requests':requests,'company_shape':list(companies[0]) if companies else [],'publishers_safe_count':len(safe),'target_publishers':[s for s in safe if any(n in str(s).lower() for n in ['growpower','escalate','vizioid'])],'inputs':await page.locator('input,select,button').evaluate_all('(els)=>els.map(e=>({tag:e.tagName,text:e.innerText?.slice(0,100),name:e.name,placeholder:e.placeholder,role:e.getAttribute("role")}))')}
  (W/'sb-initial-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
  await browser.close()
asyncio.run(main())
