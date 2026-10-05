import asyncio,json,pathlib,subprocess,re,concurrent.futures
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
async def main():
 items=json.loads(subprocess.check_output(['op','item','list','--vault','MGS Conteúdo','--format','json']))
 candidates=[i for i in items if any(s in i['title'].lower() for s in ['meta','facebook','bisu','smartbidding','conversion','capi']) and not any(s in i['title'].lower() for s in ['wordpress','digitaltrchat','proxy'])]
 def load(i):return json.loads(subprocess.check_output(['op','item','get',i['id'],'--vault','MGS Conteúdo','--format','json','--reveal']))
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:credentials=list(pool.map(load,candidates))
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json');page=await c.new_page();h={}
  async def req(q):
   if q.url.startswith(API):
    hs=await q.all_headers()
    if hs.get('authorization'):h['authorization']=hs['authorization']
  page.on('request',req);await page.goto('https://app.smartbiddingdigital.com/company/digital-trust/yolokfx/wrapper',wait_until='networkidle',timeout=90000)
  out={}
  for dom in ['yolokfx','mavroa']:
   r=await c.request.get(API+'/wrapperconfig/digital-trust_'+dom,headers=h);assert r.status==200;v=await r.json();t=v['config']['pixels'][0]['token'];assert t and '*' not in t
   matches=[]
   for i in credentials:
    for f in i.get('fields',[]):
     value=f.get('value')
     if isinstance(value,str) and t in value:matches.append({'item_id':i['id'],'title':i['title'],'field_id':f['id'],'field_label':f.get('label'),'exact':t==value})
   out[dom]={'pixel_id':v['config']['pixels'][0]['id'],'matched':bool(matches),'matches':matches,'canonical_items_examined':len(credentials)}
  (W/'pixel-vault-resolution-safe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out));await b.close()
asyncio.run(main())
