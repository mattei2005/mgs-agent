#!/usr/bin/env python3
import sys
# Avoid this file name shadowing Python's stdlib inspect module.
if sys.path and sys.path[0].endswith('sb-financeadx-us-emp-20260818'):
    sys.path.pop(0)
import asyncio, datetime as dt, json, re, subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
RUN = BASE / 'work/sb-financeadx-us-emp-20260818'
BACKUP = BASE / 'backups/sb-financeadx-us-emp-20260818'
STATE = Path('/root/.local/share/mgs/smartbidding_state_headed.json')
TARGET = 'https://app.smartbiddingdigital.com/company/digital-trust/financeadx/routing'
API = 'https://api.jbfdigital.com.br'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
TZ = ZoneInfo('America/New_York')


def now():
    return dt.datetime.now(TZ).isoformat(timespec='seconds')


def creds():
    user = subprocess.check_output(['op','item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--field','username','--reveal'], text=True).strip()
    password = subprocess.check_output(['op','item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--field','password','--reveal'], text=True).strip()
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
    return True


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


async def main():
    RUN.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(storage_state=str(STATE), viewport={'width':1600,'height':1000}, user_agent=UA)
    page = await ctx.new_page()
    captured = {}

    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            h = await req.all_headers()
            if h.get('authorization'):
                captured.update(h)

    page.on('request', on_req)
    try:
        await page.goto(TARGET, wait_until='domcontentloaded', timeout=90000)
        await page.wait_for_timeout(5000)
        did_login = await ensure_login(page, ctx)
        if did_login:
            await page.goto(TARGET, wait_until='domcontentloaded', timeout=90000)
            await page.wait_for_timeout(5000)
        if not captured.get('authorization'):
            raise RuntimeError('authenticated API header was not captured')
        headers = {k:v for k,v in captured.items() if k.lower() in {'authorization','accept','content-type'}}
        headers.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
        resp = await ctx.request.post(f'{API}/routing', headers=headers, data={'publishers':['digital-trust_financeadx']}, timeout=120000)
        text = await resp.text()
        try:
            pools = json.loads(text)
        except Exception:
            raise RuntimeError(f'non-json routing response status={resp.status}')
        if resp.status not in (200,201) or not isinstance(pools, list):
            raise RuntimeError(f'bad routing response status={resp.status} type={type(pools).__name__}')
        (BACKUP / 'before-list.json').write_text(json.dumps(pools, ensure_ascii=False, indent=2))
        matches = []
        for row in pools:
            name = str(row.get('NAME') or '')
            if name.startswith('fax-us-emp-es-drip') or name.startswith('fax-us-emp-es-mct'):
                pool_id = row.get('ID')
                detail = row
                if pool_id is not None:
                    gr = await ctx.request.get(f'{API}/routing/{pool_id}', headers=headers, timeout=120000)
                    gt = await gr.text()
                    try:
                        gd = json.loads(gt)
                        if gr.status in (200,201) and isinstance(gd, dict):
                            detail = gd
                    except Exception:
                        pass
                matches.append(detail)
        (BACKUP / 'before-target-pools.json').write_text(json.dumps(matches, ensure_ascii=False, indent=2))
        summary = {
            'inspected_at_et': now(),
            'final_url': page.url,
            'title': await page.title(),
            'list_status': resp.status,
            'total_pools': len(pools),
            'matched_pools': len(matches),
            'pools': []
        }
        for d in sorted(matches, key=lambda x: str(x.get('NAME') or '')):
            rr = parse_routes(d.get('ROUTES'))
            summary['pools'].append({
                'id': d.get('ID'), 'name': d.get('NAME'), 'source': d.get('SOURCE'),
                'country': d.get('COUNTRY'), 'vertical': d.get('VERTICAL'),
                'language': d.get('LANGUAGE'), 'medium': d.get('MEDIUM'),
                'append_params': d.get('APPEND_PARAMS'), 'routes': len(rr),
                'route_names': [r.get('route') for r in rr],
            })
        (RUN / 'inspect-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        await browser.close()
        await p.stop()


if __name__ == '__main__':
    asyncio.run(main())
