#!/usr/bin/env python3
"""Scan DTR/Bot pages missing in SmartBidding for leads/subscribers.

Source: Google Sheet gid=130786795 in Rodolfo's MGS workbook.
Rules from Rodolfo 2026-07-07:
- Pages in Bot but not SB might be unused or forgotten in SB.
- For each Bot user/account/page, open Subscriber Manager and check subscribers.
- If zero/unclear, click Scan and wait up to ~4 minutes.
- If scan hangs/no OK after 4 minutes, refresh and recheck; if still no leads, scan again.
- Do not mark no-lead from a hung scan alone.
"""
import argparse, asyncio, csv, datetime as dt, html, importlib.util, io, json, os, pathlib, re, tempfile, unicodedata, urllib.request
from collections import defaultdict, Counter
from zoneinfo import ZoneInfo

BASE=pathlib.Path('/root/mgs-agent')
SHEET_ID='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
GID='130786795'
DTR_BASE='https://digitaltrchat.com'
NY=ZoneInfo('America/New_York')
STATE=BASE/'data/dtr-missing-sb-page-lead-scan-state.json'
OUTDIR=BASE/'reports/dtr-missing-sb-page-lead-scan'
IGNORE_LIST=BASE/'data/mgs-global-page-ignore-list.json'

spec=importlib.util.spec_from_file_location('health', BASE/'scripts/dtr-sb-page-health-sync.py')
health=importlib.util.module_from_spec(spec); spec.loader.exec_module(health)

def now(): return dt.datetime.now(NY).isoformat(timespec='seconds')
def clean(v): return html.unescape(str(v or '')).strip()
def norm_email(v): return clean(v).lower()
def norm_name(v):
    t=clean(v).lower()
    t=''.join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c))
    t=re.sub(r'[^a-z0-9]+',' ',t)
    return re.sub(r'\s+',' ',t).strip()
def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.', dir=str(path.parent))
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n')
    os.replace(tmp,path)
def load_state():
    if STATE.exists(): return json.loads(STATE.read_text(encoding='utf-8'))
    return {'version':1,'created_at_et':now(),'updated_at_et':now(),'rows':{},'runs':[]}

def parse_sheet():
    url=f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}'
    data=urllib.request.urlopen(url,timeout=60).read().decode('utf-8-sig')
    raw=list(csv.reader(io.StringIO(data)))
    rows=[]
    # First row is a title/header row that also contains the first data row in text.
    if raw:
        r=raw[0]
        try:
            u=re.search(r'DTR Bot user\s+(\S+@\S+)', r[0]).group(1)
            segurador=re.search(r'DTR Segurador\s+(.+)$', r[1]).group(1).strip()
            page=re.search(r'DTR Página\s+(.+)$', r[2]).group(1).strip()
            pg=re.search(r'DTR PAGE_ID/PG\s+(\d+)', r[4]).group(1)
            fb=re.search(r'DTR FB_PAGE_ID\s+(\d+)', r[5]).group(1)
            rows.append({'rownum':1,'bot_user':norm_email(u),'account_name':segurador,'page_name':page,'pg':pg,'fb_page_id':fb,'facebook_url':r[6].replace('Facebook URL ','').strip(),'raw':r})
        except Exception:
            pass
    for idx,r in enumerate(raw[1:], start=2):
        if len(r)<6: continue
        u=norm_email(r[0])
        if '@' not in u: continue
        rows.append({'rownum':idx,'bot_user':u,'account_name':clean(r[1]),'page_name':clean(r[2]),'pg':clean(r[4]),'fb_page_id':clean(r[5]),'facebook_url':clean(r[6]) if len(r)>6 else '', 'raw':r})
    # de-dupe by user/account/pg/fb
    out=[]; seen=set()
    for r in rows:
        k=(r['bot_user'],norm_name(r['account_name']),r['pg'],r['fb_page_id'])
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

def datatable_form(page_id, length=1):
    form={'draw':'2','start':'0','length':str(length),'page_id':str(page_id),'search_value':'','label_id':'','gender':'','email_phone_birth':'','search_status':'','search_date_range':'','search[value]':'','search[regex]':'false'}
    for i in range(10):
        form[f'columns[{i}][data]']=str(i); form[f'columns[{i}][searchable]']='true'; form[f'columns[{i}][orderable]']='true'; form[f'columns[{i}][search][value]']=''; form[f'columns[{i}][search][regex]']='false'
    return form

async def subscriber_count(ctx, page_id, ref):
    r=await ctx.request.post(f'{DTR_BASE}/subscriber_manager/bot_subscribers_data', form=datatable_form(page_id), headers={'X-Requested-With':'XMLHttpRequest','Referer':ref}, timeout=60000)
    txt=await r.text()
    try:
        data=json.loads(txt)
    except Exception:
        return {'ok':False,'status':r.status,'error':'parse_error','raw':txt[:500]}
    rows=data.get('data') or []
    return {'ok':r.status==200,'status':r.status,'recordsTotal':int(data.get('recordsTotal') or 0),'recordsFiltered':int(data.get('recordsFiltered') or 0),'sample_rows':len(rows),'sample_text':re.sub('<[^>]+>',' ', ' '.join(' '.join(str(x) for x in row) for row in rows))[:500]}

async def page_details(ctx, page_id, ref):
    r=await ctx.request.post(f'{DTR_BASE}/subscriber_manager/get_page_details', form={'page_table_id':str(page_id)}, headers={'X-Requested-With':'XMLHttpRequest','Referer':ref}, timeout=60000)
    txt=await r.text()
    try: data=json.loads(txt)
    except Exception: return {'ok':False,'status':r.status,'raw':txt[:500]}
    mid=data.get('middle_column_content') or ''
    text=re.sub('<[^>]+>',' ',mid)
    nums=re.findall(r'(Conversation subscribers|Bot subscribers|24h subscribers|Unavailable|Migrated subscribers)\s*(\d+)', text, re.I)
    return {'ok':r.status==200,'status':r.status,'title':re.sub('<[^>]+>',' ', data.get('title') or '').strip(), 'counts_text':text[:1500], 'counts':nums}

async def scan_once(ctx, page_id, ref, timeout_ms=245000):
    try:
        r=await ctx.request.post(f'{DTR_BASE}/subscriber_manager/import_lead_action', form={'id':str(page_id),'scan_limit':'','folder':'inbox'}, headers={'X-Requested-With':'XMLHttpRequest','Referer':ref}, timeout=timeout_ms)
        txt=await r.text()
        try: data=json.loads(txt) if txt else {}
        except Exception: data={'parse_error':txt[:500]}
        return {'completed':True,'http_status':r.status,'response':data,'ok':str(data.get('status'))=='1'}
    except Exception as exc:
        return {'completed':False,'error':type(exc).__name__+': '+str(exc)[:300],'ok':False}

async def login_context(p, username, password):
    browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
    ctx=await browser.new_context(viewport={'width':1600,'height':1000})
    page=await ctx.new_page()
    await page.goto(f'{DTR_BASE}/home/login', wait_until='domcontentloaded', timeout=60000)
    inputs=page.locator('input:visible')
    await inputs.nth(0).fill(username); await inputs.nth(1).fill(password)
    await page.locator('button:visible, input[type=submit]:visible').last.click(); await page.wait_for_timeout(3500)
    return browser,ctx,page

async def process_user(p, username, item, targets, state, max_pages=0):
    out=[]; errors=[]
    password=health.op_password(item)
    browser,ctx,page=await login_context(p, username, password)
    ref=f'{DTR_BASE}/subscriber_manager/bot_subscribers'
    try:
        await page.goto(ref, wait_until='domcontentloaded', timeout=60000); await page.wait_for_timeout(1200)
        accs=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el=>({id:el.getAttribute('data-id')||el.dataset.id||'', name:(el.innerText||el.textContent||'').trim()})).filter(x=>x.id||x.name)""")
        # de-dupe
        tmp=[]; seen=set()
        for a in accs or [{'id':'','name':'default'}]:
            k=a.get('id','')+'|'+norm_name(a.get('name',''))
            if k not in seen: seen.add(k); tmp.append(a)
        accs=tmp
        acc_by_name=defaultdict(list)
        for a in accs: acc_by_name[norm_name(a.get('name'))].append(a)
        grouped=defaultdict(list)
        for t in targets: grouped[norm_name(t['account_name'])].append(t)
        done=0
        for akey, pages in grouped.items():
            if max_pages and done>=max_pages: break
            matches=acc_by_name.get(akey, [])
            if not matches:
                for t in pages:
                    out.append({**t,'status':'ACCOUNT_NOT_FOUND','checked_at_et':now()})
                continue
            if len(matches)>1:
                # use first but flag duplicate.
                pass
            acc=matches[0]
            if acc.get('id'):
                await ctx.request.post(f'{DTR_BASE}/social_accounts/fb_rx_account_switch', form={'id':acc['id']}, headers={'X-Requested-With':'XMLHttpRequest','Referer':ref}, timeout=60000)
                await page.goto(ref, wait_until='domcontentloaded', timeout=60000); await page.wait_for_timeout(1000)
            dom_pages=await page.evaluate("""() => Array.from(document.querySelectorAll('.page_list_item')).map(li=>({pg:li.getAttribute('page_table_id'), text:(li.innerText||'').trim()}))""")
            dom_by_pg={str(x['pg']):x for x in dom_pages}
            for t in pages:
                if max_pages and done>=max_pages: break
                key=f"{t['bot_user']}::{norm_name(t['account_name'])}::{t['pg']}::{t['fb_page_id']}"
                if state['rows'].get(key,{}).get('final'):
                    out.append(state['rows'][key]); done+=1; continue
                rec={**t,'account_id':acc.get('id'),'account_name_live':acc.get('name'),'checked_at_et':now(),'attempts':[]}
                if str(t['pg']) not in dom_by_pg:
                    rec.update({'status':'PAGE_NOT_FOUND_IN_DTR_ACCOUNT','final':True}); state['rows'][key]=rec; out.append(rec); done+=1; atomic_write(STATE,state); continue
                before=await subscriber_count(ctx,t['pg'],ref)
                rec['before']=before
                if before.get('recordsTotal',0)>0:
                    rec.update({'status':'HAS_LEADS_ALREADY','lead_count':before.get('recordsTotal'),'final':True})
                    state['rows'][key]=rec; out.append(rec); done+=1; atomic_write(STATE,state); continue
                # scan loop up to 3 attempts. Each attempt waits up to 4m; if hung, refresh/recheck before retry.
                final=False
                for attempt in range(1,4):
                    scan=await scan_once(ctx,t['pg'],ref)
                    await page.goto(ref, wait_until='domcontentloaded', timeout=60000); await page.wait_for_timeout(1000)
                    after=await subscriber_count(ctx,t['pg'],ref)
                    details=await page_details(ctx,t['pg'],ref)
                    rec['attempts'].append({'attempt':attempt,'scan':scan,'after':after,'details':details,'at_et':now()})
                    if after.get('recordsTotal',0)>0:
                        rec.update({'status':'HAS_LEADS_AFTER_SCAN','lead_count':after.get('recordsTotal'),'scan_ok_seen':scan.get('ok'), 'final':True}); final=True; break
                    if scan.get('ok'):
                        rec.update({'status':'NO_LEADS_AFTER_SCAN_OK','lead_count':0,'scan_ok_seen':True,'final':True}); final=True; break
                    # otherwise hung/error: refresh was done, retry
                if not final:
                    rec.update({'status':'SCAN_UNRESOLVED_AFTER_3_ATTEMPTS','lead_count':0,'scan_ok_seen':False,'final':False})
                state['rows'][key]=rec; out.append(rec); done+=1; atomic_write(STATE,state)
        return out, errors
    except Exception as exc:
        errors.append({'user':username,'error':type(exc).__name__+': '+str(exc)[:500]})
        return out, errors
    finally:
        await browser.close()

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--limit-pages', type=int, default=0)
    ap.add_argument('--limit-users', type=int, default=0)
    args=ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows=parse_sheet()
    state=load_state(); state['updated_at_et']=now(); state.setdefault('sheet_rows',len(rows))
    users=sorted({r['bot_user'] for r in rows})
    if args.limit_users: users=users[:args.limit_users]
    items, missing, item_errors = health.discover_dtr_items(users)
    state.setdefault('missing_credentials', missing); state.setdefault('credential_errors', item_errors)
    groups=defaultdict(list)
    for r in rows:
        if r['bot_user'] in users: groups[r['bot_user']].append(r)
    all_out=[]; all_errors=[]
    async with health.async_playwright() as p:
        remaining_pages=args.limit_pages
        for u in users:
            if args.limit_pages and remaining_pages<=0: break
            if u not in items:
                for t in groups[u]:
                    rec={**t,'status':'CREDENTIAL_NOT_FOUND','final':False,'checked_at_et':now()}
                    state['rows'][f"{t['bot_user']}::{norm_name(t['account_name'])}::{t['pg']}::{t['fb_page_id']}"]=rec; all_out.append(rec)
                continue
            limit_for_user=remaining_pages if args.limit_pages else 0
            out,errs=await process_user(p,u,items[u],groups[u],state,max_pages=limit_for_user)
            all_out.extend(out); all_errors.extend(errs)
            if args.limit_pages: remaining_pages-=len(out)
    counts=Counter((r.get('status') or 'UNKNOWN') for r in state.get('rows',{}).values())
    state.setdefault('runs',[]).append({'at_et':now(),'processed_returned':len(all_out),'status_counts':dict(counts),'errors':all_errors[:20]})
    state['runs']=state['runs'][-50:]
    atomic_write(STATE,state)
    stamp=dt.datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    report=OUTDIR/f'result-{stamp}.json'
    report.write_text(json.dumps({'sheet_rows':len(rows),'state_counts':dict(counts),'missing_credentials':missing,'errors':all_errors,'rows':list(state.get('rows',{}).values())},ensure_ascii=False,indent=2),encoding='utf-8')
    # CSV concise
    csvp=OUTDIR/f'result-{stamp}.csv'
    with csvp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['bot_user','account_name','page_name','pg','fb_page_id','status','lead_count','scan_ok_seen','checked_at_et'])
        w.writeheader()
        for r in state.get('rows',{}).values(): w.writerow({k:r.get(k,'') for k in w.fieldnames})
    done=sum(1 for r in state.get('rows',{}).values() if r.get('final'))
    print(f'DTR missing-SB lead scan: processed={len(state.get("rows",{}))}/{len(rows)} final={done} has_leads={counts.get("HAS_LEADS_ALREADY",0)+counts.get("HAS_LEADS_AFTER_SCAN",0)} no_leads={counts.get("NO_LEADS_AFTER_SCAN_OK",0)} unresolved={counts.get("SCAN_UNRESOLVED_AFTER_3_ATTEMPTS",0)} missing_creds={len(missing)} report={report}')

if __name__=='__main__':
    asyncio.run(main())
