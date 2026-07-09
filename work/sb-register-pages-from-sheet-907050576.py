#!/usr/bin/env python3
import argparse
import asyncio
import csv
import json
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
OUTDIR = BASE / 'reports'
OUTDIR.mkdir(parents=True, exist_ok=True)
API = 'https://api.jbfdigital.com.br'
SB_STATE = '/tmp/smartbidding_state_headed.json'
SHEET_ID = '1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
GID = '907050576'
NY = ZoneInfo('America/New_York')
SCHEDULE = ['08:00']
IGNORE_LIST = BASE / 'data/mgs-global-page-ignore-list.json'

LOGIN_HEADER = 'Vou colocar os campos que voce tem que saber para fazer o cadastro na dash da SB PAGE Messenger User'
ALLOWED_SAVE = [
    'ID','PUBLISHER_ID','MESSENGER_USER_ID','PAGE_ID','FB_PAGE_ID','PAGE_NAME','UTM_CAMPAIGN','LEADS','STATUS','SOURCE',
    'VERTICAL','COUNTRY','NOTES','HOLDER1','HOLDER2','ADVERTISER','DATE_START','BROADCAST_TEMPLATE_ID','BROADCAST_TIME',
    'BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID','BROADCAST_LAST_SCHEDULE','RESTRICTED_UNTIL'
]


def norm(v):
    return '' if v is None else str(v).strip()


def low(v):
    return norm(v).lower()


def status_map(v):
    return {'ready': 'Ready', 'broadcast': 'Broadcast', 'campaign': 'Campaign', 'blocked': 'Blocked', 'on-hold': 'On-hold'}.get(low(v), norm(v))


def country_map(v):
    m = {
        'united states': 'US', 'usa': 'US', 'us': 'US',
        'united kingdom': 'GB', 'uk': 'GB', 'gb': 'GB',
        'canada': 'CA', 'ca': 'CA',
        'mexico': 'MX', 'méxico': 'MX', 'mx': 'MX',
        'brazil': 'BR', 'brasil': 'BR', 'br': 'BR',
        'germany': 'DE', 'de': 'DE',
        'spain': 'ES', 'es': 'ES',
        'france': 'FR', 'fr': 'FR',
        'south africa': 'ZA', 'za': 'ZA',
        'argentina': 'AR', 'ar': 'AR',
    }
    return m.get(low(v), norm(v))


def vertical_map(v):
    m = {
        'credit card': 'CC', 'credit cards': 'CC', 'cc': 'CC',
        'loan': 'LOANS', 'loans': 'LOANS',
        'jobs': 'JOBS', 'job': 'JOBS',
        'games': 'GAMES', 'gaming': 'GAMES',
        'auto': 'AUTO', 'car': 'AUTO',
    }
    return m.get(low(v), norm(v))


def source_map(v):
    return {'facebook': 'FACEBOOK', 'fb': 'FACEBOOK'}.get(low(v), norm(v))


def load_ignore_keys():
    if not IGNORE_LIST.exists():
        return set()
    try:
        data = json.loads(IGNORE_LIST.read_text(encoding='utf-8'))
    except Exception:
        return set()
    keys = set()
    for e in data.get('entries', []):
        bot = low(e.get('bot_user'))
        pg = norm(e.get('page_id_pg'))
        fb = norm(e.get('fb_page_id'))
        if fb:
            keys.add(('fb', fb))
        if bot and pg:
            keys.add(('bot_pg', bot, pg))
    return keys


def is_ignored(login, page_id, fb_page_id, ignore_keys):
    return (fb_page_id and ('fb', fb_page_id) in ignore_keys) or (login and page_id and ('bot_pg', login, page_id) in ignore_keys)


def sheet_rows():
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req, timeout=45).read().decode('utf-8-sig', 'replace')
    raw = list(csv.reader(data.splitlines()))
    if not raw:
        raise RuntimeError('empty sheet')
    header = raw[0]
    ignore_keys = load_ignore_keys()
    out = []
    for idx, row in enumerate(raw[1:], start=2):
        vals = dict(zip(header, row))
        login = low(vals.get(LOGIN_HEADER))
        fb = norm(vals.get('FB Page ID'))
        page_id = norm(vals.get('Page ID'))
        page_name = norm(vals.get('Page Name'))
        if not (login and fb and page_id and page_name):
            continue
        if is_ignored(login, page_id, fb, ignore_keys):
            continue
        vals['_sheet_row'] = idx
        out.append(vals)
    return header, out


async def sb_context():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(
        storage_state=SB_STATE,
        viewport={'width': 1600, 'height': 1000},
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    )
    page = await ctx.new_page()
    headers = {}

    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            try:
                headers.update(await req.all_headers())
            except Exception:
                pass

    page.on('request', on_req)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(6000)
    body = (await page.locator('body').inner_text(timeout=10000))[:2000]
    if 'BotGuardError' in body or ('Log in' in body and 'Zeus - Agent' not in body):
        raise RuntimeError('SB session not authenticated or BotGuard/login screen')
    h = {k: v for k, v in headers.items() if k.lower() in {'authorization', 'accept', 'content-type'}}
    h.update({'origin': 'https://app.smartbiddingdigital.com', 'referer': 'https://app.smartbiddingdigital.com/'})
    return p, browser, ctx, h


async def fetch_companies(ctx, h):
    r = await ctx.request.get(API + '/company', headers=h, timeout=120000)
    txt = await r.text()
    if r.status != 200:
        raise RuntimeError(f'/company {r.status}: {txt[:300]}')
    return json.loads(txt)


def full_publishers(companies):
    pubs = []
    counts = []
    for c in companies:
        cname = str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ', '-')
        if cname not in ('digital-trust', 'digital-trust-2'):
            continue
        cps = []
        for pub in c.get('publishers') or []:
            pid = pub.get('publisherId')
            if pid:
                pubs.append(pid)
                cps.append(pid)
        counts.append({'company': cname, 'publishers_all': len(cps)})
    if len(pubs) < 56:
        raise RuntimeError(f'incomplete publisher scope: {len(pubs)} {counts}')
    return pubs, counts


async def fetch_pages(ctx, h, pubs):
    qs = '&'.join('companies[]=' + urllib.parse.quote(x) for x in pubs) + '&source=Messenger'
    r = await ctx.request.get(API + '/campaigns/Messenger?' + qs, headers=h, timeout=120000)
    txt = await r.text()
    if r.status != 200:
        raise RuntimeError(f'/campaigns/Messenger {r.status}: {txt[:300]}')
    rows = json.loads(txt)
    if not isinstance(rows, list):
        raise RuntimeError('pages response not list')
    if len(rows) < 2500:
        raise RuntimeError(f'incomplete pages rows: {len(rows)}')
    return rows


async def fetch_templates(ctx, h):
    r = await ctx.request.get(API + '/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger', headers=h, timeout=120000)
    txt = await r.text()
    if r.status != 200:
        raise RuntimeError(f'/broadcast/Messenger {r.status}: {txt[:300]}')
    data = json.loads(txt)
    if not isinstance(data, list):
        raise RuntimeError('templates response not list')
    return data


async def fetch_users(ctx, h, pubs):
    qs = '&'.join('companies[]=' + urllib.parse.quote(x) for x in pubs) + '&source=Messenger'
    for url in [API + '/users/Messenger?' + qs, API + '/users/Messenger']:
        r = await ctx.request.get(url, headers=h, timeout=120000)
        txt = await r.text()
        if r.status == 200:
            try:
                data = json.loads(txt)
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    raise RuntimeError('could not fetch users')


def user_index(users, pages):
    idx = {}
    for u in users:
        login = low(u.get('LOGIN') or u.get('USER_LOGIN') or u.get('email'))
        mid = u.get('ID') or u.get('MESSENGER_USER_ID') or u.get('id')
        if login and mid:
            idx.setdefault(login, str(mid))
    for r in pages:
        login = low(r.get('USER_LOGIN') or r.get('LOGIN'))
        mid = r.get('MESSENGER_USER_ID')
        if login and mid:
            idx.setdefault(login, str(mid))
    return idx


def template_fallback_for_login(login, templates):
    # Fallback for new Messenger users with no existing Page rows. Prefer the site/country/language template visible in Broadcast Template.
    rules = [
        ('disparosducapesuscces@gmail.com', ['Ducapes - US-CC-ES']),
        ('disparosopenzedloancarusen@gmail.com', ['Openzed - US-CC-EN', 'Openzed - US']),
        ('disparosportalusaen@gmail.com', ['Portal - US-CC-EN']),
        ('disparoszytivaspain@gmail.com', ['ZytivaFinanzas - ES-CC-ES']),
    ]
    for exact, needles in rules:
        if login == exact:
            matches=[]
            for t in templates:
                name = norm(t.get('NAME'))
                if any(n in name for n in needles) and 'NAO USAR' not in name.upper() and not name.lower().startswith('teste'):
                    matches.append(t)
            if matches:
                matches.sort(key=lambda t: int(t.get('PAGES') or 0), reverse=True)
                t=matches[0]
                return {'BROADCAST_TEMPLATE_ID': norm(t.get('ID')), 'BROADCAST_TEMPLATE_NAME': norm(t.get('NAME')), 'source_row_id': None, 'source_page': None, 'source_status': 'template_fallback'}
    return None


def template_index(pages):
    candidates = defaultdict(list)
    for r in pages:
        login = low(r.get('USER_LOGIN') or r.get('LOGIN'))
        tid = norm(r.get('BROADCAST_TEMPLATE_ID'))
        tname = norm(r.get('BROADCAST_TEMPLATE_NAME'))
        if not login or not tid:
            continue
        status = low(r.get('STATUS'))
        score = 0
        if status == 'broadcast': score += 20
        if status == 'campaign': score += 15
        if status == 'ready': score += 10
        if tname: score += 5
        if isinstance(r.get('BROADCAST_TIME'), list) and r.get('BROADCAST_TIME'): score += 2
        candidates[login].append((score, r))
    out = {}
    for login, arr in candidates.items():
        arr.sort(key=lambda x: x[0], reverse=True)
        r = arr[0][1]
        out[login] = {
            'BROADCAST_TEMPLATE_ID': norm(r.get('BROADCAST_TEMPLATE_ID')),
            'BROADCAST_TEMPLATE_NAME': norm(r.get('BROADCAST_TEMPLATE_NAME')),
            'source_row_id': r.get('ID'),
            'source_page': r.get('PAGE_NAME'),
            'source_status': r.get('STATUS'),
        }
    return out


def build_payload(row, messenger_user_id, template_id):
    return {
        'MESSENGER_USER_ID': messenger_user_id,
        'PAGE_ID': norm(row.get('Page ID')),
        'FB_PAGE_ID': norm(row.get('FB Page ID')),
        'PAGE_NAME': norm(row.get('Page Name')),
        'UTM_CAMPAIGN': norm(row.get('UTM Campaign')) or ('pg_' + norm(row.get('Page ID'))),
        'STATUS': status_map(row.get('Status')),
        'SOURCE': source_map(row.get('Source')),
        'VERTICAL': vertical_map(row.get('Vertical')),
        'COUNTRY': country_map(row.get('Country')),
        'NOTES': norm(row.get('NOTES')),
        'BROADCAST_TEMPLATE_ID': template_id,
        'BROADCAST_CURRENT_MESSAGE_ID': norm(row.get('Current Message ID')) or '1',
        'BROADCAST_MESSAGE_ID': norm(row.get('Message ID')) or '-1',
        'BROADCAST_TIME': list(SCHEDULE),
    }


def public_row(r):
    return {k: r.get(k) for k in ['ID','MESSENGER_USER_ID','LOGIN','USER_LOGIN','PAGE_ID','FB_PAGE_ID','PAGE_NAME','UTM_CAMPAIGN','STATUS','SOURCE','VERTICAL','COUNTRY','NOTES','BROADCAST_TEMPLATE_ID','BROADCAST_TEMPLATE_NAME','BROADCAST_TIME','BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID']}


async def post_page(ctx, h, payload):
    r = await ctx.request.post(API + '/campaigns/Messenger', headers={**h, 'content-type': 'application/json'}, data=json.dumps(payload, ensure_ascii=False), timeout=120000)
    txt = await r.text()
    return r.status, txt[:1000]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['dry-run','apply'], default='dry-run')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    stamp = datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    _, rows_sheet = sheet_rows()
    if args.limit:
        rows_sheet = rows_sheet[:args.limit]

    p, browser, ctx, h = await sb_context()
    try:
        companies = await fetch_companies(ctx, h)
        pubs, pub_counts = full_publishers(companies)
        pages = await fetch_pages(ctx, h, pubs)
        users = await fetch_users(ctx, h, pubs)
        templates = await fetch_templates(ctx, h)
        uidx = user_index(users, pages)
        tidx = template_index(pages)

        existing_by_fb = {norm(r.get('FB_PAGE_ID')): r for r in pages if norm(r.get('FB_PAGE_ID'))}
        existing_by_page = defaultdict(list)
        for r in pages:
            if norm(r.get('PAGE_ID')):
                existing_by_page[norm(r.get('PAGE_ID'))].append(r)

        planned = []
        existing = []
        skipped = []
        for row in rows_sheet:
            login = low(row.get(LOGIN_HEADER))
            fb = norm(row.get('FB Page ID'))
            page_id = norm(row.get('Page ID'))
            page_name = norm(row.get('Page Name'))
            hit = existing_by_fb.get(fb)
            if hit:
                existing.append({'sheet_row': row['_sheet_row'], 'reason': 'FB_PAGE_ID already in SB', 'sheet': row, 'sb': public_row(hit)})
                continue
            # Page ID can repeat across contexts; only treat as conflict if same login or exact page name/fb absent but likely same page.
            same_page_hits = [r for r in existing_by_page.get(page_id, []) if low(r.get('USER_LOGIN') or r.get('LOGIN')) == login]
            if same_page_hits:
                existing.append({'sheet_row': row['_sheet_row'], 'reason': 'PAGE_ID already in SB for same login', 'sheet': row, 'sb': public_row(same_page_hits[0])})
                continue
            mid = uidx.get(login)
            tinfo = tidx.get(login) or template_fallback_for_login(login, templates)
            if not mid:
                skipped.append({'sheet_row': row['_sheet_row'], 'reason': 'MESSENGER_USER_ID not found for login', 'login': login, 'sheet': row})
                continue
            if not tinfo:
                skipped.append({'sheet_row': row['_sheet_row'], 'reason': 'template not found from existing same-login rows', 'login': login, 'sheet': row})
                continue
            payload = build_payload(row, mid, tinfo['BROADCAST_TEMPLATE_ID'])
            planned.append({'sheet_row': row['_sheet_row'], 'login': login, 'fb_page_id': fb, 'page_id': page_id, 'page_name': page_name, 'payload': payload, 'template': tinfo, 'sheet': row})

        report = {
            'created_at': datetime.now(NY).isoformat(timespec='seconds'),
            'mode': args.mode,
            'sheet_id': SHEET_ID,
            'gid': GID,
            'sheet_rows': len(rows_sheet),
            'live_rows_before': len(pages),
            'publisher_scope': pub_counts,
            'planned_count': len(planned),
            'existing_count': len(existing),
            'skipped_count': len(skipped),
            'existing': existing,
            'skipped': skipped,
            'planned': planned,
        }
        plan_path = OUTDIR / f'sb-register-pages-907050576-plan-{stamp}.json'
        plan_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({
            'mode': args.mode,
            'sheet_rows': len(rows_sheet),
            'live_rows_before': len(pages),
            'planned': len(planned),
            'existing': len(existing),
            'skipped': len(skipped),
            'planned_by_login': dict(Counter(x['login'] for x in planned)),
            'skipped_reasons': dict(Counter(x['reason'] for x in skipped)),
            'plan_path': str(plan_path),
        }, ensure_ascii=False, indent=2), flush=True)
        if args.mode == 'dry-run':
            return

        results = []
        for i, item in enumerate(planned, start=1):
            status, text = await post_page(ctx, h, item['payload'])
            new_id = ''
            try:
                obj = json.loads(text)
                new_id = norm(obj.get('ID'))
            except Exception:
                pass
            results.append({'i': i, 'sheet_row': item['sheet_row'], 'login': item['login'], 'page_name': item['page_name'], 'page_id': item['page_id'], 'fb_page_id': item['fb_page_id'], 'status': status, 'new_id': new_id, 'response': text[:500]})
            print(json.dumps({'progress': i, 'of': len(planned), 'sheet_row': item['sheet_row'], 'page': item['page_name'], 'status': status, 'new_id': new_id}, ensure_ascii=False), flush=True)

        pages_after = await fetch_pages(ctx, h, pubs)
        after_by_fb = {norm(r.get('FB_PAGE_ID')): r for r in pages_after if norm(r.get('FB_PAGE_ID'))}
        validations = []
        for item in planned:
            rb = after_by_fb.get(item['fb_page_id'])
            ok = bool(rb and norm(rb.get('PAGE_ID')) == item['page_id'] and norm(rb.get('UTM_CAMPAIGN')) == 'pg_' + item['page_id'] and rb.get('BROADCAST_TIME') == SCHEDULE and norm(rb.get('COUNTRY')) == country_map(item['sheet'].get('Country')) and norm(rb.get('VERTICAL')) == vertical_map(item['sheet'].get('Vertical')) and norm(rb.get('SOURCE')) == source_map(item['sheet'].get('Source')) and norm(rb.get('STATUS')) == status_map(item['sheet'].get('Status')))
            validations.append({'sheet_row': item['sheet_row'], 'page_name': item['page_name'], 'fb_page_id': item['fb_page_id'], 'page_id': item['page_id'], 'ok': ok, 'readback': public_row(rb) if rb else None})

        final = {
            **report,
            'mode': 'apply',
            'results': results,
            'live_rows_after': len(pages_after),
            'validation_ok_count': sum(1 for x in validations if x['ok']),
            'validation_fail_count': sum(1 for x in validations if not x['ok']),
            'validations': validations,
        }
        final_path = OUTDIR / f'sb-register-pages-907050576-apply-{stamp}.json'
        final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({
            'mode': 'apply_done',
            'attempted': len(planned),
            'http_created_or_ok': sum(1 for r in results if 200 <= int(r['status']) < 300),
            'validation_ok': final['validation_ok_count'],
            'validation_fail': final['validation_fail_count'],
            'existing_skipped': len(existing),
            'skipped': len(skipped),
            'live_rows_after': len(pages_after),
            'final_path': str(final_path),
            'failures': [x for x in validations if not x['ok']][:10],
        }, ensure_ascii=False, indent=2), flush=True)
    finally:
        await browser.close()
        await p.stop()


if __name__ == '__main__':
    asyncio.run(main())
