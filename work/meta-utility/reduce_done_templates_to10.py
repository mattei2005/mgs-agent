#!/usr/bin/env python3
import asyncio, csv, datetime, json, pathlib, re
from copy import deepcopy
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

WORK = pathlib.Path('/root/mgs-agent/work/meta-utility')
BACKUP_DIR = pathlib.Path('/root/mgs-agent/backups/sb-templates')
OUT_DIR = WORK / 'bulk-reduce-to10-20260630'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
NOW = datetime.datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d-%H%M%S')

AUDIT_FILES = [
    WORK/'us-cc-en-reduce-to-70-20260630/reduce70-results.json',
    WORK/'us-cc-en-reduce-to-70-20260630/us-cc-en-apply-best70-missing-results.json',
    WORK/'gb-cc-en-apply-best70-20260630/gb-cc-en-apply-best70-results.json',
    WORK/'gb-cc-en-apply-best70-20260630/gb-cc-en-apply-best70-extra-results.json',
    WORK/'us-cc-es-apply-best70-20260630/us-cc-es-apply-best70-results.json',
    WORK/'us-cc-es-apply-best70-20260630/us-cc-es-apply-best70-extra-results.json',
    WORK/'es-cc-es-apply-best70-20260630/es-cc-es-test6-update-and-apply-best70-results.json',
]


def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', s.lower()).strip('-')[:90]


def parse_messages(row):
    msgs = row.get('MESSAGES') or '[]'
    if isinstance(msgs, str):
        return json.loads(msgs)
    return msgs if isinstance(msgs, list) else []


def collect_targets():
    seen = {}
    for path in AUDIT_FILES:
        data = json.loads(path.read_text())
        rows = data.get('results') or data.get('update_results') or []
        for r in rows:
            name = r.get('template') or r.get('name')
            if not name:
                continue
            seen[name] = {'name': name, 'source_audit': str(path)}
    return list(seen.values())


def build_10_from_current(current_msgs):
    ordered = sorted(current_msgs, key=lambda m: int(m.get('MESSAGE_ID') or 0))
    if len(ordered) < 10:
        raise RuntimeError(f'current template has only {len(ordered)} messages')
    out = []
    for i, msg in enumerate(ordered[:10], 1):
        m = deepcopy(msg)
        m['MESSAGE_ID'] = i
        # Keep message content/link exactly; remove stale approval counters if present, because this is an install payload.
        for k in ['APPROVED', 'REJECTED', 'INVALID_FORMAT', 'ERROR', 'REJECTED_REASON']:
            m.pop(k, None)
        out.append(m)
    return out


async def capture_rows_headers():
    captured_rows = []
    captured_headers = None
    post_url = 'https://api.jbfdigital.com.br/broadcast/Messenger'
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json', viewport={'width': 1600, 'height': 1000}, user_agent=UA)
    page = await ctx.new_page()

    async def on_request(req):
        nonlocal captured_headers, post_url
        if '/broadcast/Messenger' in req.url and req.method == 'GET':
            captured_headers = req.headers
            post_url = req.url.split('?')[0]

    async def on_response(resp):
        if '/broadcast/Messenger' in resp.url and resp.status == 200:
            try:
                data = await resp.json()
                if isinstance(data, list):
                    captured_rows.extend(data)
            except Exception:
                pass

    page.on('request', on_request)
    page.on('response', on_response)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='networkidle', timeout=90000)
    await page.wait_for_timeout(2500)
    try:
        await page.locator('.p-dropdown').first.click(timeout=10000)
        await page.wait_for_timeout(500)
        await page.get_by_text('Messenger', exact=True).last.click(timeout=10000)
        await page.wait_for_timeout(2500)
    except Exception:
        pass
    await page.get_by_text('Broadcast Template', exact=True).click(timeout=15000)
    await page.wait_for_timeout(7000)
    if not captured_rows or not captured_headers:
        await browser.close(); await p.stop()
        raise RuntimeError('Could not capture SB broadcast rows/headers')
    dedup = {}
    for r in captured_rows:
        dedup[r.get('ID') or r.get('NAME')] = r
    headers = {k: v for k, v in captured_headers.items() if not k.startswith(':') and k.lower() not in ('content-length', 'host')}
    headers['content-type'] = 'application/json'
    return p, browser, ctx, page, list(dedup.values()), headers, post_url


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    targets = collect_targets()
    p, browser, ctx, page, rows, headers, post_url = await capture_rows_headers()
    row_by_name = {r.get('NAME'): r for r in rows}
    results = []
    try:
        missing = [t['name'] for t in targets if t['name'] not in row_by_name]
        if missing:
            raise RuntimeError('Missing templates in SB: ' + json.dumps(missing, ensure_ascii=False))
        for target in targets:
            name = target['name']
            row = row_by_name[name]
            before_msgs = parse_messages(row)
            new_msgs = build_10_from_current(before_msgs)
            backup_json = BACKUP_DIR / f'{safe_name(name)}-before-reduce10-{NOW}.json'
            backup_csv = BACKUP_DIR / f'{safe_name(name)}-before-reduce10-{NOW}.csv'
            backup_json.write_text(json.dumps(row, ensure_ascii=False, indent=2))
            with backup_csv.open('w', encoding='utf-8-sig', newline='') as f:
                cols = ['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2']
                w = csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n')
                w.writeheader()
                for m in sorted(before_msgs, key=lambda x: int(x.get('MESSAGE_ID') or 0)):
                    w.writerow({'MESSAGE ID':m.get('MESSAGE_ID',''),'TEXT':m.get('TEXT',''),'DESCRIPTION':m.get('DESCRIPTION',''),'IMAGE':m.get('IMAGE',''),'CTA 1':m.get('CTA_1',''),'LINK 1':m.get('LINK_1',''),'CTA 2':m.get('CTA_2',''),'LINK 2':m.get('LINK_2',''),'TEXT 2':m.get('TEXT_2','')})
            payload = deepcopy(row)
            payload['MESSAGES'] = json.dumps(new_msgs, ensure_ascii=False, separators=(',', ':'))
            resp = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
            if resp.status >= 300:
                txt = await resp.text()
                raise RuntimeError(f'POST failed {name}: HTTP {resp.status} {txt[:300]}')
            results.append({'template': name, 'id': row.get('ID'), 'before_messages': len(before_msgs), 'after_requested': 10, 'post_status': resp.status, 'backup_json': str(backup_json), 'backup_csv': str(backup_csv), 'first_text': new_msgs[0].get('TEXT','')[:100], 'last_text': new_msgs[-1].get('TEXT','')[:100]})
        # Validate with fresh captured response.
        rows2 = []
        async def on_response2(resp):
            if '/broadcast/Messenger' in resp.url and resp.status == 200:
                try:
                    data = await resp.json()
                    if isinstance(data, list):
                        rows2.extend(data)
                except Exception:
                    pass
        page.on('response', on_response2)
        await page.reload(wait_until='networkidle', timeout=90000)
        await page.wait_for_timeout(6000)
        dedup2 = {}
        for r in rows2:
            dedup2[r.get('ID') or r.get('NAME')] = r
        by_name2 = {r.get('NAME'): r for r in dedup2.values()}
        validation = []
        for target in targets:
            name = target['name']
            r = by_name2.get(name)
            if not r:
                validation.append({'template': name, 'validated': False, 'error': 'not found after refresh'})
                continue
            count = len(parse_messages(r))
            validation.append({'template': name, 'count': count, 'validated': count == 10})
        audit = {
            'status': 'OK',
            'executed_at_et': datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),
            'targets': len(targets),
            'results': results,
            'validation': validation,
            'all_validated': all(v.get('validated') for v in validation) and len(validation) == len(targets),
            'backup_glob': str(BACKUP_DIR / f'*-before-reduce10-{NOW}.*'),
            'source_audits': [str(p) for p in AUDIT_FILES],
        }
        out = OUT_DIR / f'reduce-done-templates-to10-results-{NOW}.json'
        out.write_text(json.dumps(audit, ensure_ascii=False, indent=2))
        print(json.dumps({'status':'OK','targets':len(targets),'templates_updated':len(results),'all_validated':audit['all_validated'],'audit':str(out)}, ensure_ascii=False, indent=2))
    finally:
        try: await browser.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass

if __name__ == '__main__':
    asyncio.run(main())
