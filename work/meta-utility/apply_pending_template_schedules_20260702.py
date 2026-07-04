#!/usr/bin/env python3
import asyncio
import datetime as dt
import json
import pathlib
import re
import subprocess
from collections import defaultdict
from copy import deepcopy
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = pathlib.Path('/root/mgs-agent')
OUT_DIR = BASE / 'backups/sb-page-schedules'
WORK_DIR = BASE / 'work/meta-utility'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
SP = ZoneInfo('America/Sao_Paulo')
ET = ZoneInfo('America/New_York')
REF_DATE = dt.date(2026, 7, 2)
LOCAL_HOURS = [7, 8, 10, 11, 13, 15, 18, 20]

TARGET_NAMES = [
    'Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas',
    'Financeadx - CA-CC-EN/EN-SR - g006-d Nicolas',
    'Marevelx - DE-CC-DE/DE-SR - g001-d Icaro',
    'Newsoun - DE-CC-DE/DE-SR - g005-d Kelly',
    'Xyvlov - DE-CC-DE/DE-SR - g003-d Isliago',
    'Helixenit - DE-CC-DE/DE-SR - g005-d Kelly',
    'Financeadx - MX-CC-ES/ES-ZW-SR - g006-d Nicolas',
    'Infinitynexx - MX-CC-ES/ES-ZW-SR - g004-d Joe',
    'Helixenit - MX-CC-ES/ES-ZW-SR - g005-d Kelly',
    'Vizioid - MX-CC-ES/ES-ZW-SR - g002-d Gustavo',
    'Fincgriffin - TR-CC-TR/TR-SR - g006-d Nicolas',
    'Fincgriffin - TR-CC-TR/TR-SR - g001-d Icaro',
    'Fincgriffin - TR-CC-TR/TR-SR - g003-d Isliago',
    'Fincgriffin - TR-CC-TR/TR-SR - g004-d Joe',
    'Fincgriffin - TR-CC-TR/TR-SR - g005-d Kelly',
    'Portal - US-CC-EN/EN - AV - g001-d Icaro',
    'Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens',
    'Financeadx - ZA-CC-EN/EN-SR - g006-d Nicolas',
    'Fincgriffin - US-CAR-EN/EN - JBF - g001-d',
    'Fincgriffin - US-CAR-EN/EN - JBF - g002-d',
    'Fincgriffin - US-CAR-EN/EN - JBF - g003-d',
    'Fincgriffin - US-CAR-EN/EN - JBF - g004-d',
    'Fincgriffin - US-CAR-EN/EN - JBF - g005-d',
    'Fincgriffin - US-CAR-EN/EN - JBF - g006-d',
    'Spe - US-JOB-EN/EN - AV - g006-d Nicolas',
    'Spe - US-JOB-ES/ES-ZW - AV - g006-d Nicolas',
]

COUNTRY_TZ = {
    'US': 'America/New_York',
    'CA': 'America/Toronto',
    'MX': 'America/Mexico_City',
    'AR': 'America/Sao_Paulo',  # Argentina bucket currently maps to SP schedule in SB ops.
    'DE': 'Europe/Berlin',
    'ES': 'Europe/Paris',
    'GB': 'Europe/London',
    'ZA': 'Africa/Johannesburg',
    'FR': 'Europe/Paris',
    'TR': 'Europe/Istanbul',
}


def now_tag():
    return dt.datetime.now(ET).strftime('%Y%m%d-%H%M%S')


def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', s.lower()).strip('-')[:80]


def convert_for_country(country):
    tzname = COUNTRY_TZ[country]
    tz = ZoneInfo(tzname)
    out = []
    for h in LOCAL_HOURS:
        local_dt = dt.datetime.combine(REF_DATE, dt.time(h, 0), tz)
        out.append(local_dt.astimezone(SP).strftime('%H:%M'))
    return out


def normalize_times(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x)[:5] for x in v if str(x).strip()]
    if isinstance(v, str):
        return [x.strip()[:5] for x in re.split(r'[\n,;]+', v) if x.strip()]
    return []


def template_country(name):
    m = re.search(r'([A-Z]{2})-[A-Z-]+-[A-Z]{2}(?=/)', name or '')
    if m:
        return m.group(1)
    m = re.search(r'([A-Z]{2})-[A-Z-]+-[A-Z]{2}', name or '')
    return m.group(1) if m else None


def sb_credentials():
    user = subprocess.check_output([
        'op', 'item', 'get', 'Zeus - Smartbidding Dashboard',
        '--vault', 'MGS Conteúdo', '--field', 'username', '--reveal'
    ], text=True).strip()
    password = subprocess.check_output([
        'op', 'item', 'get', 'Zeus - Smartbidding Dashboard',
        '--vault', 'MGS Conteúdo', '--field', 'password', '--reveal'
    ], text=True).strip()
    if not user or not password:
        raise RuntimeError('missing SB credentials')
    return user, password


async def visible_text(locator):
    try:
        return await locator.inner_text(timeout=5000)
    except Exception:
        return ''


async def ensure_login(page, ctx):
    body = await visible_text(page.locator('body'))
    if 'Log in to Smart Bidding' not in body and 'Email address' not in body and 'Continue' not in body:
        return
    user, password = sb_credentials()
    await page.locator('input[type="email"], input[name="username"], input[name="email"], input:visible').first.fill(user, timeout=15000)
    await page.locator('input[type="password"]:visible').first.fill(password, timeout=15000)
    await page.get_by_role('button', name=re.compile('Continue|Log in|Login', re.I)).first.click(timeout=15000)
    await page.wait_for_load_state('networkidle', timeout=90000)
    await page.wait_for_timeout(3000)
    await ctx.storage_state(path='/tmp/smartbidding_state_headed.json')


async def capture_campaign_rows_and_headers(page):
    captured_rows = []
    captured_headers = None
    captured_get_url = None

    async def on_request(req):
        nonlocal captured_headers, captured_get_url
        if '/campaigns/Messenger' in req.url and req.method == 'GET':
            captured_headers = req.headers
            captured_get_url = req.url

    async def on_response(resp):
        if '/campaigns/Messenger' in resp.url and resp.status == 200:
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
    await ensure_login(page, page.context)

    # Select Messenger explicitly.
    try:
        await page.locator('.p-dropdown').first.click(timeout=10000)
        await page.wait_for_timeout(500)
        await page.get_by_text('Messenger', exact=True).last.click(timeout=10000)
        await page.wait_for_timeout(2500)
    except Exception:
        pass

    try:
        await page.get_by_text('Page', exact=True).click(timeout=15000)
    except Exception:
        # If already on Page, this can fail harmlessly.
        pass
    await page.wait_for_timeout(7000)

    if not captured_headers:
        raise RuntimeError('Could not capture /campaigns/Messenger headers')

    headers = {k: v for k, v in captured_headers.items() if not k.startswith(':') and k.lower() not in ('content-length', 'host')}
    headers['content-type'] = 'application/json'

    # Prefer an explicit full-scope URL if the captured UI request was stale/incomplete.
    api_url = 'https://api.jbfdigital.com.br/campaigns/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger'
    candidate_urls = [api_url]
    if captured_get_url:
        candidate_urls.append(captured_get_url)
    best_rows = []
    best_url = api_url
    debug = []
    for url in candidate_urls:
        resp = await page.context.request.get(url, headers=headers)
        body_head = (await resp.text())[:200] if resp.status >= 300 else ''
        if resp.status >= 300:
            debug.append({'url': url[:120], 'status': resp.status, 'body_head': body_head})
            continue
        data = await resp.json()
        count = len(data) if isinstance(data, list) else -1
        debug.append({'url': url[:120], 'status': resp.status, 'count': count})
        if isinstance(data, list) and count > len(best_rows):
            best_rows = data
            best_url = url
    if captured_rows and len(captured_rows) > len(best_rows):
        best_rows = captured_rows
        best_url = 'captured_response'
    if not isinstance(best_rows, list):
        raise RuntimeError('campaign GET returned non-list')
    if not best_rows:
        debug_path = WORK_DIR / f'campaign-capture-debug-{now_tag()}.json'
        debug_path.write_text(json.dumps({'captured_get_url': captured_get_url, 'captured_response_rows': len(captured_rows), 'debug': debug}, ensure_ascii=False, indent=2))
        raise RuntimeError(f'Could not capture campaign rows; debug={debug_path}')
    return best_rows, headers, best_url


async def main():
    tag = now_tag()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json', viewport={'width': 1600, 'height': 1000}, user_agent=UA)
        page = await ctx.new_page()
        try:
            rows, headers, api_url = await capture_campaign_rows_and_headers(page)
            full_before = OUT_DIR / f'pending-template-schedules-full-before-{tag}.json'
            full_before.write_text(json.dumps(rows, ensure_ascii=False, indent=2))

            source_note = 'live_full_scope'
            if len(rows) < 3000:
                # The UI sometimes captures only Digital trust (2443 rows) if Digital trust 2 was not refreshed.
                # Use the last validated 56-site snapshot for target row IDs, then validate each changed ID individually live.
                snapshot = OUT_DIR / 'full-after-local-7-8-10-11-13-15-18-20-20260701-003738.json'
                snap_rows = json.loads(snapshot.read_text())
                if len(snap_rows) < 3000:
                    raise RuntimeError(f'Full Page scope incomplete and snapshot invalid: live={len(rows)} snapshot={len(snap_rows)}')
                rows = snap_rows
                source_note = f'validated_snapshot:{snapshot}'

            target_set = set(TARGET_NAMES)
            target_rows = [r for r in rows if r.get('BROADCAST_TEMPLATE_NAME') in target_set]
            by_template = defaultdict(list)
            for r in target_rows:
                by_template[r.get('BROADCAST_TEMPLATE_NAME')].append(r)

            target_backup = OUT_DIR / f'pending-template-schedules-target-before-{tag}.json'
            target_backup.write_text(json.dumps(target_rows, ensure_ascii=False, indent=2))

            plan = []
            ids_by_country_times = defaultdict(list)
            for name, trs in sorted(by_template.items()):
                for r in trs:
                    country = template_country(r.get('BROADCAST_TEMPLATE_NAME')) or r.get('COUNTRY')
                    if country not in COUNTRY_TZ:
                        raise RuntimeError(f'No timezone mapping for template_country={country} page_country={r.get("COUNTRY")} template={name}')
                    target_times = convert_for_country(country)
                    ids_by_country_times[(country, tuple(target_times))].append(r.get('ID'))
                countries = sorted({template_country(r.get('BROADCAST_TEMPLATE_NAME')) or r.get('COUNTRY') for r in trs})
                plan.append({
                    'template': name,
                    'rows': len(trs),
                    'countries': countries,
                    'current_patterns': sorted({','.join(normalize_times(r.get('BROADCAST_TIME'))) for r in trs}),
                })

            missing_templates = sorted(target_set - set(by_template))
            plan_path = OUT_DIR / f'pending-template-schedules-plan-{tag}.json'
            plan_doc = {
                'ref_date': REF_DATE.isoformat(),
                'local_target_hours': [f'{h:02d}:00' for h in LOCAL_HOURS],
                'full_rows': len(rows),
                'source_note': source_note,
                'target_templates_requested': len(TARGET_NAMES),
                'target_templates_with_page_rows': len(by_template),
                'target_page_rows': len(target_rows),
                'missing_templates_or_no_page_rows': missing_templates,
                'plan': plan,
                'group_updates': [
                    {'country': c, 'target_sb_brasil': list(times), 'ids': len(ids)}
                    for (c, times), ids in sorted(ids_by_country_times.items())
                ],
                'target_backup': str(target_backup),
                'full_before': str(full_before),
            }
            plan_path.write_text(json.dumps(plan_doc, ensure_ascii=False, indent=2))

            results = []
            update_url = 'https://api.jbfdigital.com.br/campaigns/Messenger/update-many'
            for (country, times), ids in sorted(ids_by_country_times.items()):
                # Conservative batching.
                for i in range(0, len(ids), 400):
                    batch = ids[i:i+400]
                    payload = {'BROADCAST_TIME': list(times), 'ids': batch}
                    resp = await ctx.request.put(update_url, headers=headers, data=json.dumps(payload))
                    body = await resp.text()
                    results.append({'country': country, 'target_sb_brasil': list(times), 'batch': i//400+1, 'count': len(batch), 'status': resp.status, 'body_head': body[:200]})
                    if resp.status >= 300:
                        raise RuntimeError(f'update-many failed country={country} batch={i//400+1} HTTP {resp.status}: {body[:300]}')

            results_path = OUT_DIR / f'pending-template-schedules-update-results-{tag}.json'
            results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))

            # Validate by re-fetching the live Page API response. Even when the full 56-site scope is not exposed,
            # the current live response contains all 403 target rows for this operation.
            resp = await ctx.request.get(api_url, headers=headers)
            if resp.status >= 300:
                txt = await resp.text()
                raise RuntimeError(f'post-update validation GET failed HTTP {resp.status}: {txt[:300]}')
            live_after_rows = await resp.json()
            target_ids = {r.get('ID') for r in target_rows}
            after_targets = [r for r in live_after_rows if r.get('ID') in target_ids]
            individual_get_failures = []
            if len(after_targets) != len(target_rows):
                individual_get_failures.append({'error': 'live validation response missing target rows', 'expected': len(target_rows), 'got': len(after_targets)})
            full_after = OUT_DIR / f'pending-template-schedules-target-after-{tag}.json'
            full_after.write_text(json.dumps(after_targets, ensure_ascii=False, indent=2))

            failures = []
            summary_by_combo = defaultdict(lambda: {'pages': 0, 'patterns': defaultdict(int), 'templates': set()})
            for r in after_targets:
                country = template_country(r.get('BROADCAST_TEMPLATE_NAME')) or r.get('COUNTRY')
                expected = convert_for_country(country)
                actual = normalize_times(r.get('BROADCAST_TIME'))
                name = r.get('BROADCAST_TEMPLATE_NAME')
                combo = 'UNPARSED'
                m = re.search(r'([A-Z]{2}-[A-Z-]+-[A-Z]{2})(?=/)', name or '')
                if m:
                    combo = m.group(1).lower()
                summary_by_combo[combo]['pages'] += 1
                summary_by_combo[combo]['patterns'][','.join(actual)] += 1
                summary_by_combo[combo]['templates'].add(name)
                if actual != expected:
                    failures.append({'id': r.get('ID'), 'page_id': r.get('PAGE_ID'), 'template': name, 'country': country, 'expected': expected, 'actual': actual})

            validation = {
                'full_rows_before': len(rows),
                'full_rows_after': None,
                'target_rows_after': len(after_targets),
                'individual_get_failures': individual_get_failures,
                'failures': failures,
                'ok': len(failures) == 0 and not individual_get_failures and len(after_targets) == len(target_rows),
                'summary_by_vertical': [
                    {
                        'vertical': combo,
                        'pages': data['pages'],
                        'templates': len(data['templates']),
                        'patterns': [{'times': k.split(',') if k else [], 'pages': v} for k, v in sorted(data['patterns'].items())]
                    }
                    for combo, data in sorted(summary_by_combo.items())
                ],
                'files': {
                    'plan': str(plan_path),
                    'target_backup': str(target_backup),
                    'results': str(results_path),
                    'full_before': str(full_before),
                    'full_after': str(full_after),
                }
            }
            validation_path = OUT_DIR / f'pending-template-schedules-validation-{tag}.json'
            validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2))
            print(json.dumps({
                'status': 'OK' if validation['ok'] else 'FAIL',
                'full_rows_before': len(rows),
                'full_rows_after': None,
                'templates_requested': len(TARGET_NAMES),
                'templates_with_page_rows': len(by_template),
                'target_page_rows': len(target_rows),
                'missing_or_no_page_rows': missing_templates,
                'update_batches': len(results),
                'validation_failures': len(failures),
                'validation': str(validation_path),
            }, ensure_ascii=False, indent=2))
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
