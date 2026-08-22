#!/usr/bin/env python3
import sys

# Avoid this filename shadowing Python's stdlib inspect module.
if sys.path and sys.path[0].endswith('20260821-lyzmo-gb-cc-en'):
    sys.path.pop(0)

import asyncio
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
RUN = BASE / 'work/sb-smart-routing/20260821-lyzmo-gb-cc-en'
BACKUP = BASE / 'backups/sb-smart-routing/20260821-lyzmo-gb-cc-en'
STATE = Path('/root/.local/share/mgs/smartbidding_state_headed.json')
TARGET = 'https://app.smartbiddingdigital.com/company/digital-trust/lyzmo/routing'
API = 'https://api.jbfdigital.com.br'
PUBLISHER = 'digital-trust_lyzmo'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
TZ = ZoneInfo('America/New_York')
TARGET_RE = re.compile(r'^ly-gb-cc-en-drip(?:\s+00[1-6])?$')


def now():
    return dt.datetime.now(TZ).isoformat(timespec='seconds')


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def parse_routes(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def creds():
    user = subprocess.check_output([
        'op', 'item', 'get', 'Zeus - Smartbidding Dashboard', '--vault', 'MGS Conteúdo',
        '--field', 'username', '--reveal'
    ], text=True).strip()
    password = subprocess.check_output([
        'op', 'item', 'get', 'Zeus - Smartbidding Dashboard', '--vault', 'MGS Conteúdo',
        '--field', 'password', '--reveal'
    ], text=True).strip()
    if not user or not password:
        raise RuntimeError('missing Smart Bidding credentials')
    return user, password


async def ensure_login(page, ctx):
    body = await page.locator('body').inner_text(timeout=15000)
    if 'Log in to Smart Bidding' not in body and 'Email address' not in body:
        return False
    user, password = creds()
    await page.locator('input[type="email"]:visible, input[name="username"]:visible, input[name="email"]:visible, input:visible').first.fill(user, timeout=15000)
    await page.locator('input[type="password"]:visible').first.fill(password, timeout=15000)
    await page.get_by_role('button', name=re.compile('Continue|Log in|Login', re.I)).first.click(timeout=15000)
    await page.wait_for_load_state('networkidle', timeout=90000)
    await page.wait_for_timeout(3000)
    await ctx.storage_state(path=str(STATE))
    STATE.chmod(0o600)
    return True


async def main():
    RUN.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(storage_state=str(STATE), viewport={'width': 1600, 'height': 1000}, user_agent=UA)
    page = await ctx.new_page()
    captured = {}

    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            headers = await req.all_headers()
            if headers.get('authorization'):
                captured.update(headers)

    page.on('request', on_req)
    try:
        await page.goto(TARGET, wait_until='domcontentloaded', timeout=90000)
        await page.wait_for_timeout(5000)
        if await ensure_login(page, ctx):
            await page.goto(TARGET, wait_until='domcontentloaded', timeout=90000)
            await page.wait_for_timeout(5000)
        if not captured.get('authorization'):
            raise RuntimeError('authenticated API header was not captured')
        headers = {k: v for k, v in captured.items() if k.lower() in {'authorization', 'accept', 'content-type'}}
        headers.update({'origin': 'https://app.smartbiddingdigital.com', 'referer': 'https://app.smartbiddingdigital.com/'})
        resp = await ctx.request.post(f'{API}/routing', headers=headers, data={'publishers': [PUBLISHER]}, timeout=120000)
        pools = await resp.json()
        if resp.status not in (200, 201) or not isinstance(pools, list):
            raise RuntimeError(f'bad routing response status={resp.status} type={type(pools).__name__}')
        dump(BACKUP / 'before-list.json', pools)
        matches = []
        for row in pools:
            name = str(row.get('NAME') or '').strip()
            if not TARGET_RE.fullmatch(name):
                continue
            detail = row
            pool_id = row.get('ID')
            if pool_id is not None:
                gr = await ctx.request.get(f'{API}/routing/{pool_id}', headers=headers, timeout=120000)
                if gr.status in (200, 201):
                    candidate = await gr.json()
                    if isinstance(candidate, dict):
                        detail = candidate
            matches.append(detail)
        dump(BACKUP / 'before-target-pools.json', matches)
        concise = []
        for pool in sorted(matches, key=lambda x: str(x.get('NAME') or '')):
            routes = parse_routes(pool.get('ROUTES'))
            concise.append({
                'id': pool.get('ID'),
                'name': pool.get('NAME'),
                'source': pool.get('SOURCE'),
                'country': pool.get('COUNTRY'),
                'vertical': pool.get('VERTICAL'),
                'language': pool.get('LANGUAGE'),
                'medium': pool.get('MEDIUM'),
                'append_params': pool.get('APPEND_PARAMS'),
                'route_count': len(routes),
                'routes': [str(r.get('route') or '') for r in routes],
                'utm_contents': [str(r.get('utm_content') or '') for r in routes],
                'url_sequence_sha256': digest([str(r.get('url') or '').strip() for r in routes]),
                'blank_operations': sum(not str(r.get('jbf_operation') or '').strip() for r in routes),
            })
        summary = {
            'inspected_at_et': now(),
            'final_url': page.url,
            'title': await page.title(),
            'list_http': resp.status,
            'publisher': PUBLISHER,
            'total_pools': len(pools),
            'matched_pools': len(matches),
            'target_snapshot_sha256': digest(matches),
            'pools': concise,
            'backup': str(BACKUP / 'before-target-pools.json'),
        }
        dump(RUN / 'inspect-summary.json', summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        await browser.close()
        await pw.stop()


if __name__ == '__main__':
    asyncio.run(main())
