#!/usr/bin/env python3
import asyncio, csv, html, importlib.util, io, json, os, re, subprocess, sys, unicodedata, urllib.parse, urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
OUTDIR=BASE/'reports'
WORK=BASE/'work'
NY=ZoneInfo('America/New_York')
DTR_BASE='https://digitaltrchat.com'
SB_STATE='/root/.local/share/mgs/smartbidding_state_headed.json'

spec=importlib.util.spec_from_file_location('sync', str(BASE/'scripts/dtr-sb-page-health-sync.py'))
sync=importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)

def norm(v): return '' if v is None else str(v).strip()
def norm_email(v): return norm(v).lower()
def clean(v): return html.unescape(re.sub(r'<[^>]+>',' ',str(v or ''))).replace('\xa0',' ').strip()
def name_norm(v):
    s=unicodedata.normalize('NFC', clean(v)).lower()
    s=re.sub(r'\s+',' ',s)
    return s

def parse_page_card_text(txt):
    # DTR page card format observed: "Analytics <Page Name> [email] <FB_PAGE_ID> | <PG_ID>"
    t=clean(txt)
    t=re.sub(r'^Analytics\s+', '', t).strip()
    m=re.search(r'(?P<fb>\d{12,})\s*\|\s*(?P<pg>\d+)\s*$', t)
    if not m:
        return None
    left=t[:m.start()].strip()
    email=''
    em=re.search(r'([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})', left, re.I)
    if em:
        email=em.group(1)
        name=(left[:em.start()]+' '+left[em.end():]).strip()
    else:
        name=left.strip()
    name=re.sub(r'\s+',' ',name).strip()
    return {'page_name':name,'page_email':email,'fb_page_id':m.group('fb'),'page_id':m.group('pg'),'raw':txt}

async def dtr_collect_user(username, item_id, limit_accounts=0):
    out={'username':username,'login_ok':False,'accounts':[],'pages':[],'errors':[]}
    try:
        password=sync.op_password(item_id)
    except Exception as exc:
        out['errors'].append(f'credential_error:{type(exc).__name__}:{exc}')
        return out
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(viewport={'width':1600,'height':1000})
        page=await ctx.new_page()
        try:
            await page.goto(DTR_BASE+'/home/login', wait_until='domcontentloaded', timeout=60000)
            inputs=page.locator('input:visible')
            await inputs.nth(0).fill(username); await inputs.nth(1).fill(password)
            await page.locator('button:visible, input[type=submit]:visible').last.click()
            await page.wait_for_timeout(2500)
            await page.goto(DTR_BASE+'/social_accounts/index', wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(800)
            out['login_ok']=True
            csrf=''
            try: csrf=await page.locator('#csrf_token').input_value(timeout=5000)
            except Exception: pass
            accs=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el=>({id:el.getAttribute('data-id')||el.dataset.id||'', name:(el.innerText||el.textContent||'').trim()})).filter(x=>x.id||x.name)""")
            if not accs:
                # current/default account label near profile widget
                txt=await page.locator('body').inner_text(timeout=10000)
                accs=[{'id':'','name':'default'}]
            seen=set(); uniq=[]
            for a in accs:
                name=clean(a.get('name') or '') or 'default'; aid=norm(a.get('id'))
                if name in {'Rodolfo Mattei','Geizian Pereira'}: continue
                k=aid+'|'+name
                if k not in seen:
                    seen.add(k); uniq.append({'id':aid,'name':name})
            if limit_accounts: uniq=uniq[:limit_accounts]
            for a in uniq:
                aid=a['id']; aname=a['name']
                acc={'id':aid,'name':aname,'pages':0,'errors':[]}
                try:
                    if aid:
                        await ctx.request.post(DTR_BASE+'/social_accounts/fb_rx_account_switch', form={'id':aid,'csrf_token':csrf}, headers={'X-Requested-With':'XMLHttpRequest','Referer':DTR_BASE+'/social_accounts/index'}, timeout=60000)
                        await page.goto(DTR_BASE+'/social_accounts/index', wait_until='domcontentloaded', timeout=60000)
                        await page.wait_for_timeout(700)
                        try: csrf=await page.locator('#csrf_token').input_value(timeout=5000)
                        except Exception: pass
                    cards=await page.evaluate("""() => Array.from(document.querySelectorAll('.page_list_ul')).map(el => (el.innerText||el.textContent||'').replace(/\\s+/g,' ').trim())""")
                    parsed=[]
                    for txt in cards:
                        row=parse_page_card_text(txt)
                        if row:
                            row.update({'bot_user':username,'account_id':aid,'account_name':aname})
                            parsed.append(row)
                    acc['pages']=len(parsed)
                    out['pages'].extend(parsed)
                except Exception as exc:
                    acc['errors'].append(f'{type(exc).__name__}:{exc}')
                out['accounts'].append(acc)
        except Exception as exc:
            out['errors'].append(f'{type(exc).__name__}:{exc}')
        finally:
            await browser.close()
    return out

async def get_sb():
    from playwright.async_api import async_playwright
    required_companies={'digital-trust','digital-trust-2'}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx=await browser.new_context(storage_state=SB_STATE, viewport={'width':1600,'height':1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
            page=await ctx.new_page(); headers={}
            async def on_req(req):
                if 'api.jbfdigital.com.br' in req.url:
                    headers.update(await req.all_headers())
            page.on('request', on_req)
            await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}
            h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
            rc=await ctx.request.get('https://api.jbfdigital.com.br/company', headers=h, timeout=120000)
            if rc.status != 200:
                raise RuntimeError(f'SB /company bad response {rc.status}: {(await rc.text())[:300]}')
            companies=await rc.json(); pubs=[]; company_counts=[]
            for c in companies:
                cname_raw=c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or ''
                cname=str(cname_raw).strip().lower().replace(' ', '-')
                if cname not in required_companies:
                    continue
                cps=[]; active=0
                for pub in c.get('publishers') or []:
                    pid=pub.get('publisherId')
                    if pid:
                        pubs.append(pid); cps.append(pid)
                        if pub.get('active'): active += 1
                company_counts.append({'company':cname,'publishers_all':len(cps),'publishers_active':active})
            seen_companies={c['company'] for c in company_counts if c['publishers_all'] > 0}
            if seen_companies != required_companies:
                raise RuntimeError(f'SB scope incomplete for PAGE ID audit: publishers={len(pubs)} company_counts={company_counts}; expected non-empty digital-trust + digital-trust-2 child scope')
            qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
            r=await ctx.request.get('https://api.jbfdigital.com.br/campaigns/Messenger?'+qs, headers=h, timeout=120000)
            rows=await r.json()
            if r.status!=200 or not isinstance(rows,list):
                raise RuntimeError(f'SB bad response {r.status}')
            if len(rows) < 2500:
                raise RuntimeError(f'SB scope incomplete for PAGE ID audit: rows={len(rows)} publishers={len(pubs)}; expected full MGS Messenger Page baseline around current post-cleanup baseline >=2500')
            # Auth0 may rotate the refresh token while this context obtains the
            # API access token. Persist that updated browser state atomically;
            # otherwise the next cron can reopen a stale refresh token and 401.
            state_path=Path(SB_STATE)
            tmp_state=state_path.with_name(f'{state_path.name}.tmp-{os.getpid()}')
            await ctx.storage_state(path=str(tmp_state))
            os.chmod(tmp_state, 0o600)
            os.replace(tmp_state, state_path)
            os.chmod(state_path, 0o600)
        finally:
            await browser.close()
    return pubs, rows

def sb_public(r):
    return {'sb_id':norm(r.get('ID')),'bot_user':norm_email(r.get('USER_LOGIN')),'profile_name':norm(r.get('PROFILE_NAME')),'page_name':norm(r.get('PAGE_NAME')),'page_id':norm(r.get('PAGE_ID')),'fb_page_id':norm(r.get('FB_PAGE_ID')),'status':norm(r.get('STATUS')),'restricted_until':norm(r.get('RESTRICTED_UNTIL')),'domain':norm(r.get('DOMAIN')),'company':norm(r.get('COMPANY'))}

def compare(dtr_pages, sb_rows, active_users):
    sb=[sb_public(r) for r in sb_rows if norm_email(r.get('USER_LOGIN')) in active_users]
    by_user_pg=defaultdict(list); by_user_fb=defaultdict(list); by_fb=defaultdict(list); by_user_name=defaultdict(list)
    for r in sb:
        if r['page_id']: by_user_pg[(r['bot_user'],r['page_id'])].append(r)
        if r['fb_page_id']: by_user_fb[(r['bot_user'],r['fb_page_id'])].append(r); by_fb[r['fb_page_id']].append(r)
        if r['page_name']: by_user_name[(r['bot_user'],name_norm(r['page_name']))].append(r)
    matched_sb_ids=set(); issues=[]; ok=0; probable=0
    for d in dtr_pages:
        du=norm_email(d['bot_user']); dpg=norm(d['page_id']); dfb=norm(d['fb_page_id']); dn=name_norm(d['page_name'])
        candidates=[]; basis=''
        if by_user_pg.get((du,dpg)):
            candidates=by_user_pg[(du,dpg)]; basis='user+PAGE_ID'
        elif by_user_fb.get((du,dfb)):
            candidates=by_user_fb[(du,dfb)]; basis='user+FB_PAGE_ID'
        elif dfb and by_fb.get(dfb):
            candidates=by_fb[dfb]; basis='FB_PAGE_ID_global'
        elif by_user_name.get((du,dn)):
            candidates=by_user_name[(du,dn)]; basis='user+PAGE_NAME_probable'; probable+=1
        if len(candidates)==1:
            s=candidates[0]; matched_sb_ids.add(s['sb_id'])
            diffs=[]
            if dpg != s['page_id']: diffs.append('PAGE_ID')
            if dfb != s['fb_page_id']: diffs.append('FB_PAGE_ID')
            if name_norm(d['page_name']) != name_norm(s['page_name']): diffs.append('PAGE_NAME')
            if name_norm(d.get('account_name')) and name_norm(s.get('profile_name')) and name_norm(d.get('account_name')) != name_norm(s.get('profile_name')): diffs.append('SEGURADOR')
            if diffs:
                issues.append({'type':'DIVERGENTE','diffs':diffs,'match_basis':basis,'dtr':d,'sb':s})
            else:
                ok+=1
        elif len(candidates)>1:
            issues.append({'type':'AMBIGUO_SB','diffs':['multiple_candidates'],'match_basis':basis,'dtr':d,'sb_candidates':candidates[:10],'candidate_count':len(candidates)})
        else:
            issues.append({'type':'NO_SB_MATCH','diffs':['missing_in_sb'],'match_basis':'none','dtr':d})
    for s in sb:
        if s['sb_id'] not in matched_sb_ids:
            issues.append({'type':'NO_DTR_MATCH','diffs':['missing_in_dtr'],'sb':s})
    dupes=[]
    for label, rows, keyfn in [
        ('DTR_user_page_id', dtr_pages, lambda r:(norm_email(r['bot_user']),norm(r['page_id']))),
        ('DTR_user_fb_page_id', dtr_pages, lambda r:(norm_email(r['bot_user']),norm(r['fb_page_id']))),
        ('SB_user_page_id', sb, lambda r:(r['bot_user'],r['page_id'])),
        ('SB_user_fb_page_id', sb, lambda r:(r['bot_user'],r['fb_page_id'])),
    ]:
        dd=defaultdict(list)
        for r in rows:
            k=keyfn(r)
            if all(k): dd[k].append(r)
        for k,v in dd.items():
            if len(v)>1: dupes.append({'type':label,'key':k,'count':len(v),'rows':v[:10]})
    return {'sb_filtered_rows':len(sb),'ok_matches':ok,'probable_name_matches_used':probable,'issues':issues,'duplicates':dupes}

async def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--limit-users',type=int,default=0); ap.add_argument('--limit-accounts',type=int,default=0); ap.add_argument('--user', action='append', default=[])
    args=ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    rows=sync.sheet_rows(); active=set(sync.active_users_from_sheet(rows))
    matched, missing, op_errors=sync.discover_dtr_items(active)
    users=sorted(matched)
    if args.user:
        wanted={norm_email(x) for x in args.user}; users=[u for u in users if u in wanted]
    if args.limit_users: users=users[:args.limit_users]
    summary={'started_at':datetime.now(NY).isoformat(timespec='seconds'),'sheet_active_users':len(active),'matched_1p_users':len(matched),'missing_1p_users':missing,'op_errors':op_errors,'users_targeted':len(users),'errors':[]}
    dtr_scans=[]; all_pages=[]
    for i,u in enumerate(users,1):
        print(f'PROGRESS DTR {i}/{len(users)} {u}', flush=True)
        scan=await dtr_collect_user(u, matched[u], args.limit_accounts)
        dtr_scans.append(scan); all_pages.extend(scan.get('pages') or [])
        if scan.get('errors'): summary['errors'].append({'user':u,'errors':scan['errors']})
        print(f"PROGRESS DTR_DONE {u} accounts={len(scan.get('accounts') or [])} pages={len(scan.get('pages') or [])} errors={len(scan.get('errors') or [])}", flush=True)
    print('PROGRESS SB fetch', flush=True)
    pubs, sb_rows=await get_sb()
    cmp=compare(all_pages, sb_rows, active)
    summary.update({'finished_at':datetime.now(NY).isoformat(timespec='seconds'),'dtr_users_scanned':len(dtr_scans),'dtr_login_ok':sum(1 for s in dtr_scans if s.get('login_ok')),'dtr_accounts':sum(len(s.get('accounts') or []) for s in dtr_scans),'dtr_pages':len(all_pages),'sb_publishers':len(pubs),'sb_rows_total':len(sb_rows),'sb_rows_active_users':cmp['sb_filtered_rows'],'ok_matches':cmp['ok_matches'],'probable_name_matches_used':cmp['probable_name_matches_used'],'issues_count':len(cmp['issues']),'duplicates_count':len(cmp['duplicates']),'issue_types':dict(Counter(i['type'] for i in cmp['issues']))})
    raw_path=OUTDIR/f'dtr-sb-id-audit-{stamp}.json'
    csv_path=OUTDIR/f'dtr-sb-id-audit-issues-{stamp}.csv'
    raw={'summary':summary,'dtr_scans':dtr_scans,'sb_rows':[sb_public(r) for r in sb_rows if norm_email(r.get('USER_LOGIN')) in active],'compare':cmp}
    raw_path.write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
    with csv_path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['type','diffs','match_basis','bot_user','segurador_dtr','segurador_sb','page_name_dtr','page_name_sb','page_id_dtr','page_id_sb','fb_page_id_dtr','fb_page_id_sb','sb_status','sb_id'])
        for it in cmp['issues']:
            d=it.get('dtr') or {}; s=it.get('sb') or (it.get('sb_candidates') or [{}])[0]
            w.writerow([it.get('type'), ','.join(it.get('diffs') or []), it.get('match_basis',''), d.get('bot_user') or s.get('bot_user'), d.get('account_name',''), s.get('profile_name',''), d.get('page_name',''), s.get('page_name',''), d.get('page_id',''), s.get('page_id',''), d.get('fb_page_id',''), s.get('fb_page_id',''), s.get('status',''), s.get('sb_id','')])
    summary['json']=str(raw_path); summary['csv']=str(csv_path)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    asyncio.run(main())
