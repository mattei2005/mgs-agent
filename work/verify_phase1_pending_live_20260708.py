#!/usr/bin/env python3
import asyncio,csv,io,json,urllib.parse,urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
BASE=Path('/root/mgs-agent'); API='https://api.jbfdigital.com.br'; STATE='/tmp/smartbidding_state_headed.json'
SHEET='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'; NY=ZoneInfo('America/New_York')
def norm(v): return '' if v is None else str(v).strip()
def low(v): return norm(v).lower()
def csv_gid(gid):
 data=urllib.request.urlopen(urllib.request.Request(f'https://docs.google.com/spreadsheets/d/{SHEET}/gviz/tq?tqx=out:csv&gid={gid}',headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8-sig','replace')
 return [r for r in csv.reader(io.StringIO(data)) if any(c.strip() for c in r)]
async def main():
 p=await async_playwright().start(); b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
 ctx=await b.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
 page=await ctx.new_page(); headers={}
 async def on_req(req):
  if 'api.jbfdigital.com.br' in req.url: headers.update(await req.all_headers())
 page.on('request',on_req); await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=60000); await page.wait_for_timeout(5000)
 h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}; h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
 comps=await (await ctx.request.get(API+'/company',headers=h,timeout=120000)).json(); pubs=[]
 for c in comps:
  cname=str(c.get('name') or c.get('companyId') or '').strip().lower().replace(' ','-')
  if cname in ('digital-trust','digital-trust-2'):
   pubs += [pub.get('publisherId') for pub in c.get('publishers') or [] if pub.get('publisherId')]
 qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
 rows=await (await ctx.request.get(API+'/campaigns/Messenger?'+qs,headers=h,timeout=120000)).json()
 byfb={norm(r.get('FB_PAGE_ID')):r for r in rows if norm(r.get('FB_PAGE_ID'))}
 bypg={}
 for r in rows:
  if norm(r.get('PAGE_ID')): bypg.setdefault(norm(r.get('PAGE_ID')),[]).append(r)
 # pending cadastro from dry-run known sheet
 cad=csv_gid('907050576'); hcad=cad[0]; LOGIN=hcad[0]
 missing_cad=[]; existing_cad=0
 for i,r in enumerate(cad[1:],2):
  if len(r)<4 or not norm(r[0]) or not norm(r[1]) or not norm(r[2]): continue
  hit=byfb.get(norm(r[1]))
  if hit: existing_cad+=1
  else: missing_cad.append({'sheet_row':i,'login':r[0],'fb_page_id':r[1],'page_id':r[2],'page_name':r[3]})
 # SB sem DTR tab live still exists?
 sbtab=csv_gid('860481715'); sb_live=[]; sb_missing=[]
 for i,r in enumerate(sbtab[1:],2):
  if len(r)<9: continue
  fb=norm(r[4]); pg=norm(r[3]); hit=byfb.get(fb) if fb else None
  if not hit and pg: 
   cands=bypg.get(pg,[]); hit=cands[0] if cands else None
  rec={'sheet_row':i,'login':r[0],'page':r[2],'page_id':pg,'fb_page_id':fb,'sheet_status':r[6],'sb_id':r[8] if len(r)>8 else ''}
  if hit:
   rec['live']={k:hit.get(k) for k in ['ID','LOGIN','PAGE_ID','FB_PAGE_ID','PAGE_NAME','STATUS','UTM_CAMPAIGN']}; sb_live.append(rec)
  else: sb_missing.append(rec)
 # login divergence row live
 logtab=csv_gid('1767381854'); login_checks=[]
 for i,r in enumerate(logtab[1:],2):
  if len(r)<12: continue
  bot=r[3]; sb=r[4]; page=r[6]; pg=r[8]; fb=r[10]
  hit=byfb.get(norm(fb)) or (bypg.get(norm(pg),[None])[0])
  login_checks.append({'sheet_row':i,'bot_user':bot,'old_sheet_login':sb,'page':page,'page_id':pg,'fb_page_id':fb,'live_login': hit.get('LOGIN') if hit else None,'live_status': hit.get('STATUS') if hit else None,'resolved': bool(hit and low(hit.get('LOGIN'))==low(bot))})
 out={'checked_at_et':datetime.now(NY).isoformat(timespec='seconds'),'live_rows':len(rows),'publishers':len(pubs),'cadastro_sheet_rows':len(cad)-1,'cadastro_existing':existing_cad,'cadastro_missing':missing_cad,'sb_sem_dtr_tab_rows':len(sbtab)-1,'sb_sem_dtr_live_count':len(sb_live),'sb_sem_dtr_missing_count':len(sb_missing),'sb_sem_dtr_live':sb_live,'sb_sem_dtr_missing_from_sb':sb_missing,'login_difere_live':login_checks}
 path=BASE/'reports'/f'phase1-pending-live-check-{datetime.now(NY).strftime("%Y%m%d-%H%M%S")}.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'live_rows':out['live_rows'],'publishers':out['publishers'],'cadastro_existing':existing_cad,'cadastro_missing':missing_cad,'sb_sem_dtr_live':len(sb_live),'sb_sem_dtr_missing_from_sb':len(sb_missing),'login_difere_live':login_checks,'path':str(path)},ensure_ascii=False,indent=2))
 await b.close(); await p.stop()
asyncio.run(main())
