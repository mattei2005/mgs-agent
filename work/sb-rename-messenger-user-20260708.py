#!/usr/bin/env python3
import asyncio,json,urllib.parse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
SB_STATE='/tmp/smartbidding_state_headed.json'; API='https://api.jbfdigital.com.br'
OUT=Path('/root/mgs-agent/work/sb-login-correction-20260708'); OUT.mkdir(parents=True,exist_ok=True)
NY=ZoneInfo('America/New_York')
USER_ID='01b78b7d-ec6e-7198-1ce1-8d50704d4973'
CORRECT='disparosconectaportal@gmail.com'
OLD='disparosconecta@gmail.com'

def norm(v): return '' if v is None else str(v).strip()
def pub_user(u): return {k:u.get(k) for k in ['ID','ACCOUNT_ID','LOGIN','NAME','PUBLISHER_ID','COMPANY','URL','ID_1','ACTIVE'] if k in u}
async def context():
 from playwright.async_api import async_playwright
 p=await async_playwright().start(); b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
 ctx=await b.new_context(storage_state=SB_STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
 page=await ctx.new_page(); headers={}
 async def on_req(req):
  if 'api.jbfdigital.com.br' in req.url: headers.update(await req.all_headers())
 page.on('request',on_req); await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=60000); await page.wait_for_timeout(5000)
 h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}; h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
 return p,b,ctx,h
async def publishers(ctx,h):
 rc=await ctx.request.get(API+'/company',headers=h,timeout=120000); companies=await rc.json(); pubs=[]
 for c in companies:
  cname=str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ','-')
  if cname in ('digital-trust','digital-trust-2'):
   for pub in c.get('publishers') or []:
    if pub.get('publisherId'): pubs.append(pub.get('publisherId'))
 if len(pubs)<56: raise RuntimeError(f'incomplete pubs {len(pubs)}')
 return pubs
async def fetch_users(ctx,h,pubs):
 qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
 r=await ctx.request.get(API+'/users/Messenger?'+qs,headers=h,timeout=120000)
 if r.status!=200: raise RuntimeError(f'GET users {r.status}: {(await r.text())[:300]}')
 data=await r.json()
 u=next((x for x in data if norm(x.get('ID'))==USER_ID),None)
 if not u: raise RuntimeError('target user not found')
 return data,u
async def main():
 stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
 p,b,ctx,h=await context()
 try:
  pubs=await publishers(ctx,h)
  users,before=await fetch_users(ctx,h,pubs)
  backup={'created_at':datetime.now(NY).isoformat(timespec='seconds'),'before':before,'before_public':pub_user(before)}
  bp=OUT/f'backup-before-user-rename-{stamp}.json'; bp.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')
  if norm(before.get('LOGIN')).lower()==CORRECT:
   print(json.dumps({'status':'already_ok','backup':str(bp),'before':pub_user(before)},ensure_ascii=False,indent=2)); return
  payload=dict(before); payload['LOGIN']=CORRECT
  # keep only observed user columns; POST is the dashboard's upsert route for account subresources.
  allowed=['ID','ACCOUNT_ID','LOGIN','NAME','PUBLISHER_ID','COMPANY','URL','ID_1','ACTIVE']
  payload={k:payload.get(k) for k in allowed if k in payload}
  attempts=[]
  for method,url in [('POST',API+'/users/Messenger'),('PUT',API+'/users/Messenger')]:
   r=await ctx.request.fetch(url,method=method,headers={**h,'content-type':'application/json'},data=json.dumps(payload,ensure_ascii=False),timeout=120000)
   txt=await r.text(); attempts.append({'method':method,'status':r.status,'response':txt[:500]})
   if 200 <= r.status < 300: break
  else:
   raise RuntimeError('all user update attempts failed '+json.dumps(attempts,ensure_ascii=False))
  await asyncio.sleep(1)
  _,after=await fetch_users(ctx,h,pubs)
  validation={'user_id':norm(after.get('ID'))==USER_ID,'login':norm(after.get('LOGIN')).lower()==CORRECT,'name_preserved':norm(after.get('NAME'))==norm(before.get('NAME'))}
  result={'status':'updated','backup':str(bp),'attempts':attempts,'before':pub_user(before),'after':pub_user(after),'validation':validation}
  rp=OUT/f'result-user-rename-{stamp}.json'; rp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  if not all(validation.values()): raise RuntimeError('validation failed '+json.dumps(result,ensure_ascii=False))
  print(json.dumps({'status':'updated','result':str(rp),'validation':validation,'after':pub_user(after)},ensure_ascii=False,indent=2))
 finally:
  await b.close(); await p.stop()
asyncio.run(main())
