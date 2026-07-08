#!/usr/bin/env python3
import asyncio, csv, json, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
BASE=Path('/root/mgs-agent'); OUTDIR=BASE/'reports'; OUTDIR.mkdir(exist_ok=True)
API='https://api.jbfdigital.com.br'; STATE='/tmp/smartbidding_state_headed.json'; SHEET_ID='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'; GID='907050576'; NY=ZoneInfo('America/New_York')
LOGIN_HEADER='Vou colocar os campos que voce tem que saber para fazer o cadastro na dash da SB PAGE Messenger User'
def norm(v): return '' if v is None else str(v).strip()
def low(v): return norm(v).lower()
def get_sheet():
 data=urllib.request.urlopen(urllib.request.Request(f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}',headers={'User-Agent':'Mozilla/5.0'}),timeout=45).read().decode('utf-8-sig','replace')
 raw=list(csv.reader(data.splitlines())); header=raw[0]; out=[]
 for i,row in enumerate(raw[1:],2):
  d=dict(zip(header,row));
  if low(d.get(LOGIN_HEADER)) and norm(d.get('FB Page ID')) and norm(d.get('Page ID')):
   d['_sheet_row']=i; out.append(d)
 return out
async def main():
 sheet=get_sheet()
 p=await async_playwright().start(); b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']); ctx=await b.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
 page=await ctx.new_page(); headers={}
 async def on_req(req):
  if 'api.jbfdigital.com.br' in req.url: headers.update(await req.all_headers())
 page.on('request',on_req); await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=60000); await page.wait_for_timeout(5000)
 h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}; h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
 comps=await (await ctx.request.get(API+'/company',headers=h,timeout=120000)).json(); pubs=[]
 for c in comps:
  cname=str(c.get('name') or c.get('companyId') or '').strip().lower().replace(' ','-')
  if cname in ('digital-trust','digital-trust-2'):
   for pub in c.get('publishers') or []:
    if pub.get('publisherId'): pubs.append(pub['publisherId'])
 qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
 rows=await (await ctx.request.get(API+'/campaigns/Messenger?'+qs,headers=h,timeout=120000)).json()
 byfb={norm(r.get('FB_PAGE_ID')):r for r in rows if norm(r.get('FB_PAGE_ID'))}
 ok=[]; bad=[]; missing=[]
 for s in sheet:
  fb=norm(s.get('FB Page ID')); r=byfb.get(fb)
  if not r:
   missing.append({'sheet_row':s['_sheet_row'],'login':s.get(LOGIN_HEADER),'page':s.get('Page Name'),'page_id':s.get('Page ID'),'fb_page_id':fb})
   continue
  checks={
   'page_id': norm(r.get('PAGE_ID'))==norm(s.get('Page ID')),
   'utm': norm(r.get('UTM_CAMPAIGN'))=='pg_'+norm(s.get('Page ID')),
   'schedule': r.get('BROADCAST_TIME')==['08:00'],
   'status': norm(r.get('STATUS'))=='Ready',
   'country': norm(r.get('COUNTRY'))=='US',
   'vertical': norm(r.get('VERTICAL'))=='CC',
   'source': norm(r.get('SOURCE'))=='FACEBOOK',
  }
  item={'sheet_row':s['_sheet_row'],'login':s.get(LOGIN_HEADER),'page':s.get('Page Name'),'page_id':s.get('Page ID'),'fb_page_id':fb,'sb_id':r.get('ID'),'checks':checks,'readback':{k:r.get(k) for k in ['ID','LOGIN','USER_LOGIN','PAGE_ID','FB_PAGE_ID','PAGE_NAME','UTM_CAMPAIGN','STATUS','COUNTRY','VERTICAL','SOURCE','BROADCAST_TIME','BROADCAST_TEMPLATE_NAME']}}
  if all(checks.values()): ok.append(item)
  else: bad.append(item)
 out={'created_at':datetime.now(NY).isoformat(timespec='seconds'),'sheet_rows':len(sheet),'live_rows':len(rows),'ok_count':len(ok),'bad_count':len(bad),'missing_count':len(missing),'ok':ok,'bad':bad,'missing':missing}
 path=OUTDIR/f'sb-register-pages-907050576-final-audit-{datetime.now(NY).strftime("%Y%m%d-%H%M%S")}.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'sheet_rows':len(sheet),'live_rows':len(rows),'ok':len(ok),'bad':len(bad),'missing':len(missing),'missing_rows':missing,'bad_rows':bad[:5],'path':str(path)},ensure_ascii=False,indent=2))
 await b.close(); await p.stop()
asyncio.run(main())
