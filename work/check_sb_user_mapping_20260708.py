#!/usr/bin/env python3
import asyncio,json,urllib.parse
SB_STATE='/tmp/smartbidding_state_headed.json'; API='https://api.jbfdigital.com.br'
TARGET_MUID='01b78b7d-ec6e-7198-1ce1-8d50704d4973'
async def main():
 from playwright.async_api import async_playwright
 p=await async_playwright().start(); b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
 ctx=await b.new_context(storage_state=SB_STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
 page=await ctx.new_page(); headers={}
 async def on_req(req):
  if 'api.jbfdigital.com.br' in req.url: headers.update(await req.all_headers())
 page.on('request',on_req); await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=60000); await page.wait_for_timeout(5000)
 h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}; h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
 rc=await ctx.request.get(API+'/company',headers=h,timeout=120000); companies=await rc.json(); pubs=[]
 for c in companies:
  cname=str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ','-')
  if cname in ('digital-trust','digital-trust-2'):
   for pub in c.get('publishers') or []:
    if pub.get('publisherId'): pubs.append(pub.get('publisherId'))
 qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
 out=[]
 for url in [API+'/users/Messenger?'+qs, API+'/users/Messenger']:
  r=await ctx.request.get(url,headers=h,timeout=120000); txt=await r.text();
  rec={'url':url.split('?')[0],'status':r.status,'found':[],'sample_keys':[]}
  if r.status==200:
   data=json.loads(txt)
   rec['sample_keys']=list(data[0].keys()) if isinstance(data,list) and data else []
   for u in data if isinstance(data,list) else []:
    if str(u.get('ID') or u.get('MESSENGER_USER_ID') or u.get('id') or '')==TARGET_MUID or str(u.get('LOGIN') or u.get('USER_LOGIN') or u.get('email') or '').lower() in ('disparosconectaportal@gmail.com','disparosconecta@gmail.com'):
     rec['found'].append({k:u.get(k) for k in ['ID','LOGIN','USER_LOGIN','EMAIL','NAME','STATUS'] if k in u})
  else: rec['error']=txt[:300]
  out.append(rec)
 print(json.dumps(out,ensure_ascii=False,indent=2))
 await b.close(); await p.stop()
asyncio.run(main())
