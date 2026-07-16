#!/usr/bin/env python3
"""Read-only DTR scan for SB pages attached to templates showing pages_utility_messaging errors."""
import asyncio, html, json, os, re, subprocess
from pathlib import Path
from playwright.async_api import async_playwright
BASE=Path('/root/mgs-agent'); RUN=BASE/'work/sb-purple-pages-excel-20260716'
SB=RUN/'sb-pages-live.json'; BROADCAST=Path('/tmp/sb-ares-live-cron-design.json'); OUT=RUN/'dtr-page-error-scan.json'
DTR='https://digitaltrchat.com'; VAULT=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
def clean(s): return html.unescape(re.sub(r'<[^>]+>',' ',str(s or ''))).replace('\xa0',' ').strip()
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').casefold())
def op(args): return subprocess.check_output(['op',*args],text=True).strip()
def item_field(item,field): return op(['item','get',item,'--vault',VAULT,'--field',field,'--reveal'])
def password(item):
 for f in ('credential','password'):
  try:
   v=item_field(item,f)
   if v:return v
  except subprocess.CalledProcessError: pass
 raise RuntimeError('credential field unavailable')
def item_map(logins):
 items=json.loads(op(['item','list','--vault',VAULT,'--format','json'])); candidates=[i for i in items if 'digitaltrchat' in (i.get('title') or '').lower()]
 out={}
 for it in candidates:
  title=it.get('title') or ''; iid=it.get('id') or title
  if not any(x in title.lower() for x in ('infinitynexx','helixenit','lyzmo','fincgriffin')): continue
  try:u=item_field(iid,'username').strip().lower()
  except Exception:continue
  if u in logins:out[u]={'id':iid,'title':title}
 return out
def campaign_form(csrf,page_id,length=20):
 form={'draw':'1','start':'0','length':str(length),'search_page_id':str(page_id),'search_value':'','search_status':'2','campaign_date_range':'','csrf_token':csrf,'order[0][column]':'12','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
 for i in range(14):form.update({f'columns[{i}][data]':str(i),f'columns[{i}][searchable]':'true',f'columns[{i}][orderable]':'true',f'columns[{i}][search][value]':'',f'columns[{i}][search][regex]':'false'})
 return form
def report_form(csrf,cid,length=100):
 form={'draw':'1','start':'0','length':str(length),'campaign_id':str(cid),'csrf_token':csrf,'order[0][column]':'3','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
 for i in range(9):form.update({f'columns[{i}][data]':str(i),f'columns[{i}][searchable]':'true',f'columns[{i}][orderable]':'true',f'columns[{i}][search][value]':'',f'columns[{i}][search][regex]':'false'})
 return form
async def post_json(ctx,url,form,ref):
 r=await ctx.request.post(url,form=form,headers={'X-Requested-With':'XMLHttpRequest','Referer':ref},timeout=60000); txt=await r.text()
 try:return json.loads(txt) if txt else {}
 except:return {'_parse_error':txt[:300],'_status':r.status}
def cid_from(row):
 for c in row:
  m=re.search(r"cam-id=['\"]?(\d+)",str(c))
  if m:return m.group(1)
 return ''
def reason_from(raw):
 t=clean(raw)
 if 'pages_utility_messaging' in t:return 'PAGES_UTILITY_MESSAGING'
 if 'Application does not have permission for this action' in t:return 'APP_NO_PERMISSION'
 if 'Application has been deleted' in t:return 'APP_DELETED'
 if '#2022' in t:return 'PAGE_RESTRICTED_2022'
 return 'OTHER' if t else 'NO_REPORT'
def candidates():
 br=json.loads(BROADCAST.read_text())['rows'];targets=set()
 for r in br:
  ms=json.loads(r['MESSAGES']) if isinstance(r.get('MESSAGES'),str) else r.get('MESSAGES',[])
  if any(isinstance(m.get('REJECTED_REASON'),dict) and any('pages_utility_messaging' in str(k) for k in m['REJECTED_REASON']) for m in ms):targets.add(r['NAME'])
 rows=json.loads(SB.read_text())['rows'];out=[]
 for r in rows:
  if r.get('BROADCAST_TEMPLATE_NAME') in targets:
   out.append({k:r.get(k) for k in ['BROADCAST_TEMPLATE_NAME','PROFILE_NAME','LOGIN','USER_LOGIN','PAGE_NAME','PAGE_ID','FB_PAGE_ID','STATUS','RESTRICTED_UNTIL']})
 return out
async def scan_user(login,item,rows):
 result=[];pw=password(item['id'])
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=await browser.new_context(viewport={'width':1500,'height':900});page=await ctx.new_page();ref=DTR+'/messenger_bot_enhancers/subscriber_broadcast_campaign'
  try:
   await page.goto(DTR+'/home/login',wait_until='domcontentloaded',timeout=60000);inputs=page.locator('input:visible');await inputs.nth(0).fill(login);await inputs.nth(1).fill(pw);await page.locator('button:visible, input[type=submit]:visible').last.click();await page.wait_for_timeout(2500);await page.goto(ref,wait_until='domcontentloaded',timeout=60000);csrf=await page.locator('#csrf_token').input_value(timeout=10000)
   accounts=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el=>({id:el.getAttribute('data-id')||el.dataset.id||'',name:(el.innerText||el.textContent||'').trim()})).filter(x=>x.id||x.name)""")
   if not accounts:accounts=[{'id':'','name':'default'}]
   dedup={};[dedup.setdefault((str(a.get('id') or ''),norm(a.get('name'))),a) for a in accounts];accounts=list(dedup.values())
   for profile,group in __import__('itertools').groupby(sorted(rows,key=lambda x:x.get('PROFILE_NAME') or ''),key=lambda x:x.get('PROFILE_NAME') or ''):
    group=list(group);matches=[a for a in accounts if norm(a.get('name'))==norm(profile)]
    if len(matches)!=1:
     for row in group:result.append({**row,'dtr_result':'ACCOUNT_NOT_UNIQUE','account_matches':len(matches)})
     continue
    acc=matches[0]
    if acc.get('id'):await ctx.request.post(DTR+'/social_accounts/fb_rx_account_switch',form={'id':acc['id'],'csrf_token':csrf},headers={'X-Requested-With':'XMLHttpRequest','Referer':ref},timeout=60000);await page.goto(ref,wait_until='domcontentloaded',timeout=60000);await page.wait_for_timeout(700);csrf=await page.locator('#csrf_token').input_value(timeout=10000)
    options=await page.evaluate("""() => Array.from(document.querySelectorAll('select#search_page_id option,select[name=search_page_id] option')).map(o=>({value:o.value||'',text:(o.innerText||o.textContent||'').trim()})).filter(x=>x.value&&x.value!='0')""");by_pg={str(o['value']):o for o in options}
    for row in group:
     pg=str(row.get('PAGE_ID') or '');base={**row,'dtr_account_id':acc.get('id'),'dtr_account_name':clean(acc.get('name')),'page_in_dtr':pg in by_pg}
     camp=await post_json(ctx,ref+'_data',campaign_form(csrf,pg),ref);data=camp.get('data') or [];cid=''
     for rr in data:
      cid=cid_from(rr)
      if cid:break
     if not cid:result.append({**base,'dtr_result':'NO_COMPLETED_CAMPAIGN','campaign_id':''});continue
     rep=await post_json(ctx,DTR+'/messenger_bot_enhancers/campaign_sent_status_data',report_form(csrf,cid),ref);raw=' '.join(' '.join(str(x) for x in rr) for rr in (rep.get('data') or []));reason=reason_from(raw)
     result.append({**base,'dtr_result':reason,'campaign_id':cid,'latest_report_has_pages_utility_messaging':reason=='PAGES_UTILITY_MESSAGING','latest_report_excerpt':clean(raw)[:5000]})
  finally:await browser.close()
 return result
async def main():
 rows=candidates();by={}
 for r in rows:by.setdefault((r.get('USER_LOGIN') or r.get('LOGIN') or '').lower(),[]).append(r)
 items=item_map(set(by));results=[];errors=[]
 for login,group in by.items():
  if login not in items:errors.append({'login':login,'error':'1Password item not found'});continue
  try:results.extend(await scan_user(login,items[login],group))
  except Exception as e:errors.append({'login':login,'error':f'{type(e).__name__}: {e}'})
 payload={'candidate_rows':len(rows),'users':len(by),'items_found':len(items),'results':results,'errors':errors};OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'candidate_rows':len(rows),'results':len(results),'pages_utility':sum(r.get('latest_report_has_pages_utility_messaging',False) for r in results),'errors':errors},ensure_ascii=False))
asyncio.run(main())
