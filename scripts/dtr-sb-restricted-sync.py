#!/usr/bin/env python3
"""DigitalTRChat #2022 -> SmartBidding RESTRICTED_UNTIL sync.

Discovers MGS DigitalTRChat 1Password items, scans recent Completed campaign reports
for #2022 temporary Messenger restrictions, matches the affected FB page to live
SmartBidding Messenger Page rows, and optionally writes RESTRICTED_UNTIL with live
readback validation.

Default mode is dry-run. Cron uses --apply and stays quiet unless changes/errors.
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
DTR_DETECT = BASE / 'scripts/dtr-detect-restricted-pages.py'
SB_STATE = '/tmp/smartbidding_state_headed.json'
NY = ZoneInfo('America/New_York')
LOG_DIR = BASE / 'logs'


def norm(v):
    return '' if v is None else str(v).strip()


def date_only(v):
    return norm(v)[:10]


def now_stamp():
    return datetime.now(NY).strftime('%Y%m%d-%H%M%S')


def op_items():
    env = os.environ.copy()
    cmd = ['op', 'item', 'list', '--vault', env.get('OP_DEFAULT_VAULT', 'MGS Conteúdo'), '--format', 'json']
    out = subprocess.check_output(cmd, env=env, text=True)
    items = json.loads(out)
    titles = []
    seen = set()
    for item in items:
        title = item.get('title') or ''
        tl = title.lower().strip()
        if not tl.startswith('digitaltrchat - disparos'):
            continue
        if title in seen:
            continue
        seen.add(title)
        titles.append(title)
    return sorted(titles, key=str.lower)


async def get_sb_context():
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
            headers.update(await req.all_headers())

    page.on('request', on_req)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(5000)
    h = {k: v for k, v in headers.items() if k.lower() in {'authorization', 'accept', 'content-type'}}
    h.update({'origin': 'https://app.smartbiddingdigital.com', 'referer': 'https://app.smartbiddingdigital.com/'})
    return p, browser, ctx, h


async def fetch_sb_rows(ctx, h):
    rc = await ctx.request.get('https://api.jbfdigital.com.br/company', headers=h, timeout=120000)
    companies = await rc.json()
    pubs = []
    for company in companies:
        for pub in company.get('publishers') or []:
            if pub.get('active') and pub.get('publisherId'):
                pubs.append(pub['publisherId'])
    qs = '&'.join('companies[]=' + urllib.parse.quote(x) for x in pubs) + '&source=Messenger'
    r = await ctx.request.get('https://api.jbfdigital.com.br/campaigns/Messenger?' + qs, headers=h, timeout=120000)
    rows = await r.json()
    if r.status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'bad campaigns response status={r.status} type={type(rows).__name__}')
    return pubs, rows


def index_sb_rows(rows, today):
    by_fb = {}
    by_name = {}
    for r in rows:
        status = norm(r.get('STATUS'))
        if status != 'Broadcast':
            continue
        ru = date_only(r.get('RESTRICTED_UNTIL'))
        # The sync is for currently unrestricted Broadcast pages only. Existing future
        # restrictions are handled by the SB monitor and should not be rewritten.
        if ru and ru >= today:
            continue
        fb = norm(r.get('FB_PAGE_ID'))
        if fb:
            by_fb.setdefault(fb, []).append(r)
        name = norm(r.get('PAGE_NAME')).lower()
        if name:
            by_name.setdefault(name, []).append(r)
    return by_fb, by_name


def run_dtr_detector(item, limit_campaigns, timeout_sec):
    cmd = [sys.executable, str(DTR_DETECT), '--item', item, '--limit-campaigns', str(limit_campaigns)]
    cp = subprocess.run(cmd, cwd=str(BASE), text=True, capture_output=True, timeout=timeout_sec)
    if cp.returncode != 0:
        return {'ok': False, 'item': item, 'error': cp.stderr[-1000:] or cp.stdout[-1000:] or f'rc={cp.returncode}', 'restrictions_found': []}
    try:
        return json.loads(cp.stdout)
    except Exception as exc:
        return {'ok': False, 'item': item, 'error': f'json_parse_failed: {exc}; stdout_tail={cp.stdout[-1000:]}', 'restrictions_found': []}


async def apply_update(ctx, h, row, target_date):
    payload = {'RESTRICTED_UNTIL': target_date, 'ids': [str(row.get('ID'))]}
    r = await ctx.request.put('https://api.jbfdigital.com.br/campaigns/Messenger/update-many', headers=h, data=json.dumps(payload), timeout=120000)
    text = await r.text()
    try:
        body = json.loads(text) if text else None
    except Exception:
        body = text[:500]
    return r.status, body


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Write RESTRICTED_UNTIL in SmartBidding. Default is dry-run.')
    ap.add_argument('--limit-items', type=int, default=0, help='Limit DTR items for testing. 0 = all.')
    ap.add_argument('--limit-campaigns', type=int, default=10, help='Recent Completed DTR campaigns per item.')
    ap.add_argument('--detector-timeout', type=int, default=90)
    ap.add_argument('--quiet-noop', action='store_true', help='Print nothing when no changes/errors.')
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_log = LOG_DIR / f'dtr-sb-restricted-sync-{now_stamp()}.json'
    today = datetime.now(NY).date().isoformat()
    items = op_items()
    if args.limit_items and args.limit_items > 0:
        items = items[:args.limit_items]

    summary = {
        'ok': True,
        'mode': 'apply' if args.apply else 'dry-run',
        'started_at': datetime.now(NY).isoformat(timespec='seconds'),
        'today': today,
        'items_total': len(items),
        'items_scanned': 0,
        'sb_rows': 0,
        'eligible_sb_rows': 0,
        'dtr_restrictions_found': 0,
        'matched_unrestricted': 0,
        'already_restricted_or_not_broadcast': 0,
        'unmatched': 0,
        'updated': 0,
        'validated': 0,
        'errors': [],
        'changes': [],
        'log': str(run_log),
    }

    p = browser = ctx = None
    try:
        p, browser, ctx, h = await get_sb_context()
        pubs, rows = await fetch_sb_rows(ctx, h)
        summary['sb_rows'] = len(rows)
        by_fb, by_name = index_sb_rows(rows, today)
        summary['eligible_sb_rows'] = sum(len(v) for v in by_fb.values())

        for item in items:
            summary['items_scanned'] += 1
            det = run_dtr_detector(item, args.limit_campaigns, args.detector_timeout)
            if not det.get('ok'):
                summary['errors'].append({'item': item, 'error': det.get('error')})
                continue
            found = det.get('restrictions_found') or []
            summary['dtr_restrictions_found'] += len(found)
            for f in found:
                target_date = date_only(f.get('restricted_until'))
                if not target_date:
                    summary['errors'].append({'item': item, 'page_name': f.get('page_name'), 'error': 'missing_restricted_until'})
                    continue
                matches = []
                fb = norm(f.get('fb_page_id'))
                if fb:
                    matches = by_fb.get(fb, [])
                if not matches:
                    matches = by_name.get(norm(f.get('page_name')).lower(), [])
                if not matches:
                    # Check if it exists but is already restricted or non-Broadcast for accounting.
                    exists = [r for r in rows if (fb and norm(r.get('FB_PAGE_ID')) == fb) or (norm(r.get('PAGE_NAME')).lower() == norm(f.get('page_name')).lower())]
                    if exists:
                        summary['already_restricted_or_not_broadcast'] += 1
                    else:
                        summary['unmatched'] += 1
                    continue
                if len(matches) > 1:
                    # Avoid ambiguous writes; require FB_PAGE_ID to disambiguate.
                    summary['errors'].append({'item': item, 'page_name': f.get('page_name'), 'fb_page_id': fb, 'error': f'ambiguous_sb_match_{len(matches)}'})
                    continue
                row = matches[0]
                before = date_only(row.get('RESTRICTED_UNTIL'))
                change = {
                    'item': item,
                    'page_name': row.get('PAGE_NAME'),
                    'page_id': row.get('PAGE_ID'),
                    'fb_page_id': row.get('FB_PAGE_ID'),
                    'user_login': row.get('USER_LOGIN'),
                    'profile_name': row.get('PROFILE_NAME'),
                    'before': before,
                    'after': target_date,
                    'dtr_time': f.get('restricted_until_time'),
                    'campaign_id': f.get('campaign_id'),
                    'applied': False,
                    'validated': False,
                }
                summary['matched_unrestricted'] += 1
                if args.apply:
                    status, body = await apply_update(ctx, h, row, target_date)
                    change['write_status'] = status
                    if status < 200 or status >= 300:
                        change['write_response'] = body
                        summary['errors'].append({'item': item, 'page_name': row.get('PAGE_NAME'), 'error': f'sb_write_status_{status}'})
                    else:
                        summary['updated'] += 1
                        change['applied'] = True
                        _, rows_after = await fetch_sb_rows(ctx, h)
                        rb = [r for r in rows_after if norm(r.get('ID')) == norm(row.get('ID'))]
                        got = date_only(rb[0].get('RESTRICTED_UNTIL')) if rb else None
                        change['readback'] = got
                        change['validated'] = got == target_date
                        if change['validated']:
                            summary['validated'] += 1
                        else:
                            summary['errors'].append({'item': item, 'page_name': row.get('PAGE_NAME'), 'error': f'readback_mismatch_{got}_expected_{target_date}'})
                summary['changes'].append(change)

    except Exception as exc:
        summary['ok'] = False
        summary['errors'].append({'fatal': type(exc).__name__, 'error': str(exc)})
    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()
        summary['finished_at'] = datetime.now(NY).isoformat(timespec='seconds')
        run_log.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if args.quiet_noop and not summary['changes'] and not summary['errors']:
        return 0

    if summary['changes'] or summary['errors']:
        title = 'DTR → SB Restricted Until — atualizado' if args.apply and summary['updated'] else 'DTR → SB Restricted Until — revisão'
        print(title)
        print(f"Itens DTR escaneados: {summary['items_scanned']}/{summary['items_total']}")
        print(f"#2022 encontrados: {summary['dtr_restrictions_found']} | matches SB elegíveis: {summary['matched_unrestricted']} | updates validados: {summary['validated']}")
        if summary['changes']:
            for ch in summary['changes'][:10]:
                status = 'aplicado' if ch.get('applied') else 'dry-run'
                print(f"- {ch.get('page_name')} ({ch.get('fb_page_id')}): {ch.get('before') or 'vazio'} → {ch.get('after')} | {status}")
            if len(summary['changes']) > 10:
                print(f"- +{len(summary['changes'])-10} no log")
        if summary['errors']:
            print(f"Erros: {len(summary['errors'])} — ver log")
        print(f"Log: {run_log}")
    else:
        print(json.dumps({k: summary[k] for k in ['ok','mode','items_scanned','items_total','sb_rows','dtr_restrictions_found','matched_unrestricted','updated','validated','log']}, ensure_ascii=False, indent=2))

    return 0 if summary['ok'] and not summary['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
