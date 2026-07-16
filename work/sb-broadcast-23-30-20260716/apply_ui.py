#!/usr/bin/env python3
import argparse,asyncio,datetime as dt,json,re
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
BASE=Path('/root/mgs-agent');RUN=BASE/'work/sb-broadcast-23-30-20260716';PLAN=RUN/'plan.json';STATE='/root/.local/share/mgs/smartbidding_state_ares.json';JOURNAL=RUN/'journal.jsonl';TZ=ZoneInfo('America/New_York');UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
def now():return dt.datetime.now(TZ).isoformat(timespec='seconds')
def compact(s):return re.sub(r'\s+',' ',s or '').strip()
def journal(rec):
 with JOURNAL.open('a',encoding='utf-8') as f:f.write(json.dumps({'at_et':now(),**rec},ensure_ascii=False)+'\n')
def core(msgs):return [{'MESSAGE_ID':int(m.get('MESSAGE_ID') or 0),'TEXT':m.get('TEXT') or '','CTA_1':m.get('CTA_1') or m.get('CTA 1') or '','LINK_1':m.get('LINK_1') or m.get('LINK 1') or ''} for m in msgs]
def parse_msgs(row):
 x=row.get('MESSAGES') or [];return json.loads(x) if isinstance(x,str) else x
async def navigate_broadcast(page):
 await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='networkidle',timeout=90000);await page.wait_for_timeout(1200)
 try:
  await page.locator('.p-dropdown').first.click(timeout=8000);await page.wait_for_timeout(250);await page.get_by_text('Messenger',exact=True).last.click(timeout=8000);await page.wait_for_timeout(1000)
 except:pass
 await page.get_by_text('Broadcast Template',exact=True).click(timeout=12000);await page.wait_for_timeout(4000)
async def find_row(page,name):
 loc=page.get_by_text(name,exact=True)
 if await loc.count():return loc.first.locator('xpath=ancestor::tr')
 # Main table global filter. The search button reveals the text field; all dimensions are selected by default.
 fin=page.locator('input.p-inputtext:visible')
 if not await fin.count():
  await page.locator('button:has(.pi-search)').first.click(timeout=10000);await page.wait_for_timeout(350);fin=page.locator('input.p-inputtext:visible')
 if not await fin.count():raise RuntimeError(f'global filter unavailable for: {name}')
 await fin.last.fill(name);await fin.last.press('Enter');await page.wait_for_timeout(900)
 loc=page.get_by_text(name,exact=True)
 if not await loc.count():raise RuntimeError(f'row not found: {name}')
 return loc.first.locator('xpath=ancestor::tr')
async def confirm_if_present(page):
 await page.wait_for_timeout(400)
 dialogs=page.locator('[role="dialog"]:visible,.p-dialog:visible,.modal:visible')
 if await dialogs.count()<3:return False
 dlg=dialogs.last;txt=compact(await dlg.inner_text())
 for label in ('Yes','Confirm','Delete','OK','Erase all'):
  btn=dlg.get_by_role('button',name=re.compile(f'^{re.escape(label)}$',re.I))
  if await btn.count():await btn.first.click();await page.wait_for_timeout(500);return True
 raise RuntimeError(f'unhandled confirmation: {txt[:300]}')
async def refresh_rows(page,target_id=None,expected_core=None):
 captured=[];probe={'url':None,'headers':None}
 async def handler(resp):
  if '/broadcast/Messenger' in resp.url and resp.status==200:
   try:
    d=await resp.json()
    if isinstance(d,list):
     captured.extend(d);probe['url']=resp.url;probe['headers']=await resp.request.all_headers()
   except:pass
 page.on('response',handler)
 await page.reload(wait_until='networkidle',timeout=90000);await page.wait_for_timeout(2500)
 if probe['url'] and probe['headers']:
  # Fresh authenticated API readback avoids stale table state after modal Save.
  raw_headers=probe['headers'];drop=('host','content-length','if-none-match','if-modified-since','cache-control','pragma')
  safe_headers={k:v for k,v in raw_headers.items() if not k.startswith(':') and k.lower() not in drop};safe_headers['cache-control']='no-cache';safe_headers['pragma']='no-cache'
  sep='&' if '?' in probe['url'] else '?'
  for attempt in range(4):
   probe_url=f"{probe['url']}{sep}__mgs_readback={int(dt.datetime.now().timestamp()*1000)}-{attempt}"
   resp=await page.context.request.get(probe_url,headers=safe_headers,timeout=90000)
   if resp.ok:
    d=await resp.json()
    if isinstance(d,list):
     captured=d
     if target_id and expected_core is not None:
      rr=next((r for r in d if r.get('ID')==target_id),None)
      if rr and core(parse_msgs(rr))==expected_core:break
   await page.wait_for_timeout(1000)
 page.remove_listener('response',handler)
 ded={}
 for r in captured:ded[r.get('ID') or r.get('NAME')]=r
 return list(ded.values())
async def apply_one(page,item):
 name=item['name'];target=item['target_count'];csvp=item['csv'];events=[]
 row=await find_row(page,name);row_text=compact(await row.inner_text())
 await row.locator('button').nth(0).click(timeout=10000);await page.wait_for_timeout(650)
 dialogs=page.locator('[role="dialog"]:visible,.p-dialog:visible,.modal:visible');parent=dialogs.last
 parent_name=await parent.locator('input[type="text"]').first.input_value()
 if parent_name!=name:raise RuntimeError(f'wrong parent modal for {name}: {parent_name}')
 await parent.locator('button.btn-notifications').first.click(timeout=10000);await page.wait_for_timeout(650)
 dialogs=page.locator('[role="dialog"]:visible,.p-dialog:visible,.modal:visible');msgdlg=dialogs.last
 if compact(name) not in compact(await msgdlg.inner_text()):raise RuntimeError(f'wrong messages modal for {name}')
 await msgdlg.get_by_text('Import',exact=True).click(timeout=10000);await page.wait_for_timeout(350)
 # Stage full replacement inside the modal. It is not persisted until Update + parent Save.
 await msgdlg.get_by_role('button',name=re.compile(r'Erase all',re.I)).click(timeout=10000);await confirm_if_present(page);await page.wait_for_timeout(350)
 await msgdlg.locator('input[type="file"]').set_input_files(csvp);await page.wait_for_timeout(350)
 upload=msgdlg.get_by_role('button',name=re.compile(r'^\s*Upload\s*$',re.I))
 if await upload.count():await upload.click(timeout=10000)
 await page.wait_for_timeout(900)
 txt=compact(await msgdlg.inner_text());events.append({'step':'staged_import','text':txt[-500:]})
 m=re.search(r'Uploaded messages:\s*(\d+).*?Total messages:\s*(\d+)',txt,re.I)
 if not m or int(m.group(1))!=target or int(m.group(2))!=target:raise RuntimeError(f'{name}: import count check failed: {txt[-500:]}')
 if item['requires_approval']:
  btn=msgdlg.get_by_role('button',name=re.compile(r'Run Approvals',re.I))
  if not await btn.count():raise RuntimeError(f'{name}: Run Approvals button missing')
  await btn.click(timeout=30000);events.append({'step':'run_approval_clicked'});await page.wait_for_timeout(700)
 # Rodolfo-mandated order: Run Approval -> Update -> Save.
 await msgdlg.get_by_role('button',name=re.compile(r'^Update$',re.I)).click(timeout=15000);events.append({'step':'update_clicked'});await page.wait_for_timeout(650)
 save=page.locator('button:visible').filter(has_text=re.compile(r'^\s*Save\s*$',re.I)).last
 if not await save.count():
  vis=page.locator('[role="dialog"]:visible,.p-dialog:visible,.modal:visible')
  debug=[]
  for i in range(await vis.count()):
   d=vis.nth(i);debug.append({'i':i,'text':compact(await d.inner_text())[:700],'buttons':await d.locator('button').all_inner_texts()})
  raise RuntimeError(f'{name}: parent Save missing; dialogs={json.dumps(debug,ensure_ascii=False)}')
 await save.click(timeout=30000);events.append({'step':'save_clicked'});await page.wait_for_timeout(1300)
 expected=core(item['messages']);rows=await refresh_rows(page,item['id'],expected);live=next((r for r in rows if r.get('ID')==item['id']),None)
 if not live:raise RuntimeError(f'{name}: readback row missing')
 live_msgs=parse_msgs(live);actual=core(live_msgs)
 if actual!=expected:
  result={'template':name,'id':item['id'],'status':'saved_pending_fresh_readback','target':target,'pages':item['pages'],'approval_clicked':bool(item['requires_approval']),'observed_count':len(actual),'events':events}
  journal(result);return result
 result={'template':name,'id':item['id'],'status':'validated','target':target,'pages':item['pages'],'approval_clicked':bool(item['requires_approval']),'events':events}
 journal(result);return result
async def main():
 ap=argparse.ArgumentParser();ap.add_argument('--target',action='append');ap.add_argument('--all-pending',action='store_true');args=ap.parse_args()
 data=json.loads(PLAN.read_text(encoding='utf-8'));items=data['templates']
 done=set()
 if JOURNAL.exists():
  for line in JOURNAL.read_text(encoding='utf-8').splitlines():
   try:
    r=json.loads(line)
    if r.get('status') in ('validated','saved_pending_fresh_readback'):done.add(r.get('template'))
   except:pass
 if args.target:
  wanted=set(args.target);items=[x for x in items if x['name'] in wanted]
  missing=wanted-{x['name'] for x in items}
  if missing:raise SystemExit(f'targets missing from plan: {sorted(missing)}')
 elif args.all_pending:items=[x for x in items if x['name'] not in done]
 else:raise SystemExit('use --target or --all-pending')
 results=[]
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']);c=await b.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent=UA);page=await c.new_page();await navigate_broadcast(page)
  try:
   for item in items:
    if item['name'] in done:continue
    try:results.append(await apply_one(page,item))
    except Exception as e:
     journal({'template':item['name'],'id':item['id'],'status':'error','error':str(e)});raise
  finally:await b.close()
 print(json.dumps({'status':'OK','processed':len(results),'results':results},ensure_ascii=False,indent=2))
asyncio.run(main())
