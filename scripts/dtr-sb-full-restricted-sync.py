#!/usr/bin/env python3
"""Full-scope DigitalTRChat -> SmartBidding restricted page sync.

Scope source: Google Sheet gid 562940072 (Migração 22/06), not all 1Password items.
Flow: active bot users from sheet -> matching 1Password item by username -> every
DigitalTRChat top-bar account/segurador -> latest Completed campaign per page ->
classify latest report -> cross-check SmartBidding live -> optionally apply
RESTRICTED_UNTIL for any current #2022 page (pure or mixed) and persist mixed
codes for post-expiry review.
"""
import argparse
import asyncio
import csv
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE_DIR = Path('/root/mgs-agent')
SHEET_ID = '1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY'
MIGRATION_GID = '562940072'
SB_STATE = '/tmp/smartbidding_state_headed.json'
DTR_BASE = 'https://digitaltrchat.com'
NY = ZoneInfo('America/New_York')
STATE_PATH = BASE_DIR / 'data/dtr-sb-restricted-sync-state.json'
LOG_DIR = BASE_DIR / 'logs'

MONTHS_EN={'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}
MONTHS_ES={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
MONTHS_PT={'janeiro':1,'fevereiro':2,'março':3,'marco':3,'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12}


def norm(v):
    return '' if v is None else str(v).strip()


def norm_email(v):
    return norm(v).lower()


def clean_html(value):
    return html.unescape(re.sub(r'<[^>]+>', ' ', str(value or ''))).replace('\u202f',' ').replace('\xa0',' ').strip()


def date_only(v):
    return norm(v)[:10]


def now_iso():
    return datetime.now(NY).isoformat(timespec='seconds')


def sheet_rows():
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={MIGRATION_GID}'
    data = urllib.request.urlopen(url, timeout=60).read().decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(data)))


def active_bot_users_from_sheet(rows):
    users = []
    by_user_rows = defaultdict(list)
    for row in rows:
        user = norm_email(row.get('User'))
        if '@' not in user:
            continue
        if not norm(row.get('NO APP')):
            continue
        if norm(row.get('Removidos acumulado')).upper() == 'X':
            continue
        users.append(user)
        by_user_rows[user].append(row)
    return sorted(set(users)), by_user_rows


def op_json(cmd):
    return json.loads(subprocess.check_output(cmd, text=True, env=os.environ.copy()))


def discover_dtr_items(target_users):
    items = op_json(['op','item','list','--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--format','json'])
    candidates = [i.get('title') for i in items if norm(i.get('title')).lower().startswith('digitaltrchat - disparos')]
    matched = {}
    errors = []
    for title in sorted(set(candidates), key=str.lower):
        try:
            username = subprocess.check_output(
                ['op','item','get',title,'--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--fields','username','--reveal'],
                text=True, env=os.environ.copy(), timeout=20
            ).strip().lower()
        except Exception as exc:
            errors.append({'item': title, 'error': f'op_username_failed: {type(exc).__name__}'})
            continue
        if username in target_users and username not in matched:
            matched[username] = title
    missing = sorted(set(target_users) - set(matched))
    return matched, missing, errors


def op_password(item):
    for field in ('credential','password'):
        try:
            return subprocess.check_output(
                ['op','item','get',item,'--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--fields',field,'--reveal'],
                text=True, env=os.environ.copy(), timeout=30
            ).strip()
        except subprocess.CalledProcessError:
            pass
    raise RuntimeError(f'password field not found for {item}')


def parse_restriction_date(text, year=None):
    t = clean_html(text)
    y = year or datetime.now(NY).year
    m=re.search(r'until\s+([A-Za-z]+)\s+(\d{1,2})\s+at\s+(\d{1,2}):(\d{2})\s*([AP]M)', t, re.I)
    if m:
        mon=MONTHS_EN.get(m.group(1).lower()); day=int(m.group(2)); hh=int(m.group(3)); mm=int(m.group(4)); ap=m.group(5).upper()
        if mon:
            if ap=='PM' and hh!=12: hh+=12
            if ap=='AM' and hh==12: hh=0
            return f'{y:04d}-{mon:02d}-{day:02d}', f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}'
    m=re.search(r'hasta\s+el\s+(\d{1,2})\s+de\s+([A-Za-záéíóúñ]+)\s+a\s+las\s+(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?', t, re.I)
    if m:
        day=int(m.group(1)); mon=MONTHS_ES.get(m.group(2).lower()); hh=int(m.group(3)); mm=int(m.group(4)); ap=m.group(5).lower()
        if mon:
            if ap=='p' and hh!=12: hh+=12
            if ap=='a' and hh==12: hh=0
            return f'{y:04d}-{mon:02d}-{day:02d}', f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}'
    m=re.search(r'at[eé]\s+(\d{1,2})\s+de\s+([A-Za-záéíóúãõç]+).*?(\d{1,2}):(\d{2})', t, re.I)
    if m:
        day=int(m.group(1)); mon=MONTHS_PT.get(m.group(2).lower()); hh=int(m.group(3)); mm=int(m.group(4))
        if mon:
            return f'{y:04d}-{mon:02d}-{day:02d}', f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}'
    return None, None


def classify_report(raw):
    t = clean_html(raw)
    low = t.lower()
    codes = []
    if '#2022' in t or 'temporarily restricted' in low or 'restring' in low:
        codes.append('#2022')
    if '#10' in t or 'outside of allowed window' in low or 'fora do espaço de tempo permitido' in low or 'fuera del período permitido' in low:
        codes.append('#10')
    if '#551' in t or "isn't available" in low or 'não está disponível' in low or 'no se encuentra disponible' in low:
        codes.append('#551')
    if '#100' in t or 'missing one or more params' in low or 'no matching user found' in low or 'não foi possível encontrar o modelo' in low or 'no se puede encontrar la plantilla' in low:
        codes.append('#100')
    if 'application has been deleted' in low or 'aplicativo foi excluído' in low:
        codes.append('APP_DELETED')
    if 'pages_messaging permission' in low or 'permission(s) must be granted' in low or 'before impersonatin' in low:
        codes.append('PERMISSION')
    if 'oauth' in low or 'token' in low or 'session' in low:
        codes.append('TOKEN')
    if not codes and t:
        # Treat explicit success strings as OK, otherwise OTHER.
        if re.search(r'\bSent\b|Enviado|Entregado|Delivered', t, re.I):
            return {'status':'OK','codes':[], 'raw_error':t[:1500], 'restricted_until':None, 'restricted_until_time':None}
        codes.append('OTHER')
    ru, rut = parse_restriction_date(t)
    return {'status':'ERROR' if codes else 'OK', 'codes':codes, 'raw_error':t[:1500], 'restricted_until':ru, 'restricted_until_time':rut}


async def dtr_post_json(ctx, url, form, ref):
    r=await ctx.request.post(url, form=form, headers={'X-Requested-With':'XMLHttpRequest','Referer':ref})
    txt=await r.text()
    try:
        return json.loads(txt) if txt else {}
    except Exception:
        return {'_parse_error': txt[:500]}


def campaign_form(csrf, length, start=0):
    form={'draw':'1','start':str(start),'length':str(length),'search_page_id':'','search_value':'','search_status':'2','campaign_date_range':'','csrf_token':csrf,'order[0][column]':'12','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
    for i in range(14):
        form[f'columns[{i}][data]']=str(i); form[f'columns[{i}][searchable]']='true'; form[f'columns[{i}][orderable]']='true'; form[f'columns[{i}][search][value]']=''; form[f'columns[{i}][search][regex]']='false'
    return form


def report_form(csrf, campaign_id, length=50):
    form={'draw':'1','start':'0','length':str(length),'campaign_id':str(campaign_id),'csrf_token':csrf,'order[0][column]':'3','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
    for i in range(9):
        form[f'columns[{i}][data]']=str(i); form[f'columns[{i}][searchable]']='true'; form[f'columns[{i}][orderable]']='true'; form[f'columns[{i}][search][value]']=''; form[f'columns[{i}][search][regex]']='false'
    return form


async def scan_dtr_user(username, item, limit_campaigns, max_accounts=0):
    password = op_password(item)
    result={'username':username,'item':item,'login_ok':False,'accounts':[], 'pages_scanned':0, 'latest_reports':[], 'errors':[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(viewport={'width':1600,'height':1000})
        page=await ctx.new_page()
        try:
            await page.goto(f'{DTR_BASE}/home/login', wait_until='domcontentloaded', timeout=60000)
            inputs=page.locator('input:visible')
            await inputs.nth(0).fill(username); await inputs.nth(1).fill(password)
            await page.locator('button:visible, input[type=submit]:visible').last.click()
            await page.wait_for_timeout(3500)
            url=f'{DTR_BASE}/messenger_bot_enhancers/subscriber_broadcast_campaign'
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            csrf=await page.locator('#csrf_token').input_value(timeout=10000)
            result['login_ok']=True
            accounts=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map((el,i)=>({id:el.getAttribute('data-id')||el.dataset.id||'', name:(el.innerText||el.textContent||'').trim()})).filter(x=>x.id||x.name)""")
            if not accounts:
                accounts=[{'id':'','name':'default'}]
            # include unique account ids/names only
            seen=set(); uniq=[]
            for acc in accounts:
                key=(acc.get('id') or '')+'|'+(acc.get('name') or '')
                if key not in seen:
                    seen.add(key); uniq.append(acc)
            accounts=uniq[:max_accounts] if max_accounts else uniq
            for acc in accounts:
                acc_id=acc.get('id') or ''
                acc_name=clean_html(acc.get('name') or 'default') or 'default'
                acc_summary={'id':acc_id,'name':acc_name,'campaigns':0,'pages':0,'errors':[]}
                result['accounts'].append(acc_summary)
                try:
                    if acc_id:
                        await ctx.request.post(f'{DTR_BASE}/social_accounts/fb_rx_account_switch', form={'id':acc_id,'csrf_token':csrf}, headers={'X-Requested-With':'XMLHttpRequest','Referer':url}, timeout=60000)
                        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        await page.wait_for_timeout(700)
                        csrf=await page.locator('#csrf_token').input_value(timeout=10000)
                    camp=await dtr_post_json(ctx, url+'_data', campaign_form(csrf, limit_campaigns), url)
                    rows=camp.get('data') or []
                    acc_summary['campaigns']=len(rows)
                    latest_by_page={}
                    for row in rows:
                        action=row[6] if len(row)>6 else ''
                        m=re.search(r"cam-id=['\"]?(\d+)", str(action))
                        if not m: continue
                        cid=m.group(1)
                        page_html=row[3] if len(row)>3 else ''
                        page_name=clean_html(page_html)
                        fb_match=re.search(r'facebook\.com\\?/(\d+)|facebook\.com/(\d+)', str(page_html))
                        fb_id=next((g for g in (fb_match.groups() if fb_match else []) if g), None)
                        key=fb_id or page_name.lower()
                        if key and key not in latest_by_page:
                            latest_by_page[key]={'campaign_id':cid,'page_name':page_name,'fb_page_id':fb_id,'campaign_row_text':clean_html(' '.join(str(x) for x in row))[:1000]}
                    acc_summary['pages']=len(latest_by_page)
                    result['pages_scanned'] += len(latest_by_page)
                    for page_key, meta in latest_by_page.items():
                        rep=await dtr_post_json(ctx, f'{DTR_BASE}/messenger_bot_enhancers/campaign_sent_status_data', report_form(csrf, meta['campaign_id']), url)
                        raw=' '.join(' '.join(str(x) for x in rr) for rr in (rep.get('data') or []))
                        cls=classify_report(raw)
                        item_out={**meta,'account_id':acc_id,'account_name':acc_name,'classification':cls}
                        result['latest_reports'].append(item_out)
                except Exception as exc:
                    acc_summary['errors'].append(f'{type(exc).__name__}: {exc}')
        except Exception as exc:
            result['errors'].append(f'{type(exc).__name__}: {exc}')
        finally:
            await browser.close()
    return result


async def get_sb_context():
    p=await async_playwright().start()
    browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
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
    return p,browser,ctx,h


async def fetch_sb_rows(ctx,h):
    rc=await ctx.request.get('https://api.jbfdigital.com.br/company', headers=h, timeout=120000)
    companies=await rc.json(); pubs=[]
    for company in companies:
        for pub in company.get('publishers') or []:
            if pub.get('active') and pub.get('publisherId'):
                pubs.append(pub['publisherId'])
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    r=await ctx.request.get('https://api.jbfdigital.com.br/campaigns/Messenger?'+qs, headers=h, timeout=120000)
    rows=await r.json()
    if r.status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'bad SB campaigns response status={r.status}')
    return pubs, rows


def sb_index(rows, today):
    by_fb=defaultdict(list); by_name=defaultdict(list)
    for r in rows:
        if norm(r.get('FB_PAGE_ID')):
            by_fb[norm(r.get('FB_PAGE_ID'))].append(r)
        if norm(r.get('PAGE_NAME')):
            by_name[norm(r.get('PAGE_NAME')).lower()].append(r)
    return by_fb, by_name


def operational_sb(row, today):
    status=norm(row.get('STATUS'))
    if status in {'On-hold','Blocked','Bloqueado'}:
        return False
    return status in {'Broadcast','Campaign'}


def active_restricted(row, today):
    ru=date_only(row.get('RESTRICTED_UNTIL'))
    return bool(ru and ru >= today)


async def sb_update_restricted(ctx,h,row,target_date):
    payload={'RESTRICTED_UNTIL':target_date,'STATUS':'Broadcast','ids':[str(row.get('ID'))]}
    r=await ctx.request.put('https://api.jbfdigital.com.br/campaigns/Messenger/update-many', headers=h, data=json.dumps(payload), timeout=120000)
    text=await r.text()
    return r.status, text[:500]


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    return {'mixed_2022':{}, 'runs':[]}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=STATE_PATH.name+'.', dir=str(STATE_PATH.parent))
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(state,f,ensure_ascii=False,indent=2,sort_keys=True); f.write('\n')
    os.replace(tmp, STATE_PATH)


def public_sb(row):
    return {k: row.get(k) for k in ['ID','PAGE_ID','FB_PAGE_ID','PAGE_NAME','USER_LOGIN','PROFILE_NAME','STATUS','RESTRICTED_UNTIL','BROADCAST_TEMPLATE_NAME']}


async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--user', action='append', default=[], help='Restrict run to one or more bot-user emails from the sheet.')
    ap.add_argument('--limit-users', type=int, default=0)
    ap.add_argument('--limit-accounts', type=int, default=0)
    ap.add_argument('--limit-campaigns', type=int, default=1000)
    ap.add_argument('--quiet-noop', action='store_true')
    args=ap.parse_args()

    started=now_iso(); stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_log=LOG_DIR/f'dtr-sb-full-restricted-sync-{stamp}.json'
    today=datetime.now(NY).date().isoformat()
    summary={'ok':True,'mode':'apply' if args.apply else 'dry-run','started_at':started,'today':today,'sheet_gid':MIGRATION_GID,'errors':[], 'changes':[], 'mixed_2022_rows':[], 'log':str(run_log)}
    p=browser=ctx=None
    try:
        rows_sheet=sheet_rows()
        active_users, by_user_rows=active_bot_users_from_sheet(rows_sheet)
        summary.update({'sheet_rows':len(rows_sheet),'active_bot_users':len(active_users)})
        matched, missing, op_errors=discover_dtr_items(set(active_users))
        summary.update({'matched_1p_users':len(matched),'missing_1p_users':missing,'op_errors':op_errors})
        users=sorted(matched)
        if args.user:
            requested={norm_email(u) for u in args.user}
            users=[u for u in users if u in requested]
            missing_requested=sorted(requested-set(users))
            if missing_requested:
                summary['errors'].append({'missing_requested_users':missing_requested})
        if args.limit_users:
            users=users[:args.limit_users]
        p,browser,ctx,h=await get_sb_context()
        pubs,sb_rows=await fetch_sb_rows(ctx,h)
        summary.update({'sb_rows':len(sb_rows),'sb_publishers':len(pubs)})
        by_fb,by_name=sb_index(sb_rows,today)
        state=load_state()
        stats=Counter()
        for username in users:
            scan=await scan_dtr_user(username, matched[username], args.limit_campaigns, args.limit_accounts)
            stats['users_scanned']+=1
            stats['dtr_accounts']+=len(scan.get('accounts') or [])
            stats['dtr_pages_latest_completed']+=scan.get('pages_scanned') or 0
            if scan.get('errors'):
                summary['errors'].append({'user':username,'errors':scan.get('errors')})
            for rep in scan.get('latest_reports') or []:
                cls=rep.get('classification') or {}
                codes=cls.get('codes') or []
                if not codes:
                    stats['latest_ok']+=1
                    continue
                for c in codes:
                    stats[f'code_{c}']+=1
                fb=norm(rep.get('fb_page_id'))
                matches=by_fb.get(fb,[]) if fb else []
                if not matches:
                    matches=by_name.get(norm(rep.get('page_name')).lower(),[])
                if not matches:
                    stats['no_sb_match']+=1
                    continue
                # Prefer exact USER_LOGIN if multiple matches.
                if len(matches)>1:
                    exact=[r for r in matches if norm_email(r.get('USER_LOGIN'))==username]
                    if exact:
                        matches=exact
                if len(matches)>1:
                    stats['ambiguous_sb_match']+=1
                    summary['errors'].append({'user':username,'page':rep.get('page_name'),'fb_page_id':fb,'error':f'ambiguous_sb_match_{len(matches)}'})
                    continue
                sb=matches[0]
                if not operational_sb(sb,today):
                    stats[f'ignored_status_{norm(sb.get("STATUS")) or "blank"}']+=1
                    continue
                if '#2022' in codes:
                    stats['2022_operational']+=1
                    target=cls.get('restricted_until')
                    if not target:
                        stats['2022_missing_date']+=1
                        summary['errors'].append({'user':username,'page':rep.get('page_name'),'error':'2022_missing_restricted_until','codes':codes})
                        continue
                    mixed=len(set(codes)-{'#2022'})>0
                    if mixed:
                        stats['2022_mixed']+=1
                        key=str(sb.get('ID') or sb.get('PAGE_ID') or fb or rep.get('page_name'))
                        mixed_record={'first_seen':state.get('mixed_2022',{}).get(key,{}).get('first_seen') or now_iso(),'last_seen':now_iso(),'needs_post_expiry_review':True,'codes':codes,'dtr':rep,'sb':public_sb(sb),'restricted_until':target}
                        state.setdefault('mixed_2022',{})[key]=mixed_record
                        summary['mixed_2022_rows'].append(mixed_record)
                    else:
                        stats['2022_pure']+=1
                    if active_restricted(sb,today):
                        stats['already_restricted_active']+=1
                        continue
                    change={'user':username,'page_name':sb.get('PAGE_NAME'),'page_id':sb.get('PAGE_ID'),'fb_page_id':sb.get('FB_PAGE_ID'),'status_before':sb.get('STATUS'),'restricted_before':date_only(sb.get('RESTRICTED_UNTIL')),'restricted_after':target,'codes':codes,'mixed':mixed,'applied':False,'validated':False}
                    if args.apply:
                        status, body=await sb_update_restricted(ctx,h,sb,target)
                        change['write_status']=status
                        if 200 <= status < 300:
                            change['applied']=True; stats['updated']+=1
                            _,after_rows=await fetch_sb_rows(ctx,h)
                            rb=[r for r in after_rows if norm(r.get('ID'))==norm(sb.get('ID'))]
                            got=date_only(rb[0].get('RESTRICTED_UNTIL')) if rb else None
                            st=norm(rb[0].get('STATUS')) if rb else None
                            change['readback_restricted_until']=got; change['readback_status']=st
                            change['validated']=(got==target and st=='Broadcast')
                            if change['validated']: stats['validated']+=1
                            else: summary['errors'].append({'user':username,'page':sb.get('PAGE_NAME'),'error':'readback_mismatch','got':got,'status':st,'expected':target})
                        else:
                            change['write_response']=body
                            summary['errors'].append({'user':username,'page':sb.get('PAGE_NAME'),'error':f'sb_write_status_{status}'})
                    summary['changes'].append(change)
        state.setdefault('runs',[]).append({'ts':now_iso(),'mode':summary['mode'],'stats':dict(stats),'log':str(run_log)})
        state['runs']=state['runs'][-20:]
        save_state(state)
        summary['stats']=dict(stats)
    except Exception as exc:
        summary['ok']=False
        summary['errors'].append({'fatal':type(exc).__name__,'error':str(exc)})
    finally:
        if browser: await browser.close()
        if p: await p.stop()
        summary['finished_at']=now_iso()
        run_log.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    no_op=not summary.get('changes') and not summary.get('errors')
    if args.quiet_noop and no_op:
        return 0
    print('DTR → SB páginas restritas — ' + summary['mode'])
    st=summary.get('stats') or {}
    print(f"Planilha gid {MIGRATION_GID}: usuários ativos {summary.get('active_bot_users')} | 1P matches {summary.get('matched_1p_users')}")
    print(f"Scan: usuários {st.get('users_scanned',0)} | seguradores {st.get('dtr_accounts',0)} | páginas/latest Completed {st.get('dtr_pages_latest_completed',0)}")
    print(f"#2022 operacional: {st.get('2022_operational',0)} | puro {st.get('2022_pure',0)} | misto {st.get('2022_mixed',0)} | já restrito {st.get('already_restricted_active',0)}")
    print(f"Updates: {st.get('updated',0)} | validados {st.get('validated',0)} | mudanças pendentes/dry-run {len(summary.get('changes') or [])}")
    if summary.get('errors'):
        print(f"Erros: {len(summary['errors'])} — ver log")
    print(f"Log: {run_log}")
    return 0 if summary.get('ok') and not summary.get('errors') else 1


if __name__=='__main__':
    raise SystemExit(asyncio.run(main()))
