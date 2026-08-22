#!/usr/bin/env python3
import asyncio
import datetime as dt
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
RUN = BASE / 'work/sb-smart-routing/20260821-lyzmo-gb-cc-en'
BACKUP = BASE / 'backups/sb-smart-routing/20260821-lyzmo-gb-cc-en'
STATE = '/root/.local/share/mgs/smartbidding_state_headed.json'
TARGET = 'https://app.smartbiddingdigital.com/company/digital-trust/lyzmo/routing'
API = 'https://api.jbfdigital.com.br'
PUBLISHER = 'digital-trust_lyzmo'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
TZ = ZoneInfo('America/New_York')
AUTH_MESSAGE_ID = '1540457286785572994'
TARGET_NAMES = [f'ly-gb-cc-en-drip {i:03d}' for i in range(1, 7)]
META_KEYS = ('ID', 'COMPANY', 'DOMAIN', 'NAME', 'SOURCE', 'COUNTRY', 'VERTICAL', 'MEDIUM', 'LANGUAGE', 'APPEND_PARAMS')


def now():
    return dt.datetime.now(TZ).isoformat(timespec='seconds')


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def parse_routes(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    raise RuntimeError('invalid ROUTES shape')


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def route_identity(route):
    return {
        'route': str(route.get('route') or '').strip(),
        'utm_content': str(route.get('utm_content') or '').strip(),
    }


def route_stable(route):
    return {
        'route': str(route.get('route') or '').strip(),
        'utm_content': str(route.get('utm_content') or '').strip(),
        'url': str(route.get('url') or '').strip(),
        'jbf_operation': str(route.get('jbf_operation') or '').strip(),
        'healthy': bool(route.get('healthy', True)),
        'freeze': bool(route.get('freeze', False)),
    }


def pool_core(pool):
    return {
        'meta': {k: pool.get(k) for k in META_KEYS},
        'routes': [route_stable(r) for r in parse_routes(pool.get('ROUTES'))],
    }


def unrelated_signature(pools, target_ids):
    out = []
    for pool in pools:
        if pool.get('ID') in target_ids:
            continue
        out.append({
            'id': pool.get('ID'),
            'meta': {k: pool.get(k) for k in META_KEYS},
            'identities': sorted((route_identity(r)['route'], route_identity(r)['utm_content']) for r in parse_routes(pool.get('ROUTES'))),
        })
    return sorted(out, key=lambda x: (str(x['id']), str(x['meta'].get('NAME'))))


def sequence_index(route_name):
    if route_name == 'ly-gb-cc-en-drip-m0-1':
        return 0
    if route_name == 'ly-gb-cc-en-drip-nm':
        return 1
    match = re.fullmatch(r'ly-gb-cc-en-drip-m([1-9]|1[0-9]|2[0-8])-1', route_name)
    if not match:
        raise RuntimeError(f'unexpected route identity: {route_name}')
    return int(match.group(1)) + 1


def expected_groups():
    sequence = ['ly-gb-cc-en-drip-m0-1', 'ly-gb-cc-en-drip-nm'] + [f'ly-gb-cc-en-drip-m{i}-1' for i in range(1, 29)]
    return [sequence[i:i + 5] for i in range(0, 30, 5)]


def build_plan(targets):
    ordered = [targets[name] for name in TARGET_NAMES]
    if len({p.get('ID') for p in ordered}) != 6:
        raise RuntimeError('target pool IDs are not unique')
    all_routes = [r for p in ordered for r in parse_routes(p.get('ROUTES'))]
    if len(all_routes) != 30:
        raise RuntimeError(f'expected 30 routes, got {len(all_routes)}')
    identity_map = {}
    for route in all_routes:
        name = route_identity(route)['route']
        if name in identity_map:
            raise RuntimeError(f'duplicate route identity: {name}')
        sequence_index(name)
        identity_map[name] = route_identity(route)
    groups = expected_groups()
    expected_flat = [name for group in groups for name in group]
    if set(identity_map) != set(expected_flat):
        missing = sorted(set(expected_flat) - set(identity_map))
        extra = sorted(set(identity_map) - set(expected_flat))
        raise RuntimeError(f'route coverage mismatch missing={missing} extra={extra}')

    slot_profiles = []
    for pool in ordered:
        routes = parse_routes(pool.get('ROUTES'))
        if len(routes) != 5:
            raise RuntimeError(f'{pool.get("NAME")}: expected 5 routes')
        slot_profiles.append([(str(r.get('url') or '').strip(), str(r.get('jbf_operation') or '').strip()) for r in routes])
    if any(profile != slot_profiles[0] for profile in slot_profiles[1:]):
        raise RuntimeError('URL/operation slot sequence differs between pools')
    if any(not url or not op for url, op in slot_profiles[0]):
        raise RuntimeError('blank URL/operation in canonical slot sequence')

    plans = []
    for pool, group in zip(ordered, groups):
        old_routes = parse_routes(pool.get('ROUTES'))
        new_routes = []
        for slot, route_name in enumerate(group):
            new_route = deepcopy(old_routes[slot])
            new_route['route'] = identity_map[route_name]['route']
            new_route['utm_content'] = identity_map[route_name]['utm_content']
            new_routes.append(new_route)
        plans.append({'before': pool, 'routes': new_routes})
    return plans, slot_profiles[0]


def payload(pool, routes):
    result = {k: pool.get(k) for k in META_KEYS}
    result['ROUTES'] = json.dumps(routes, ensure_ascii=False, separators=(',', ':'))
    return result


async def open_auth():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(storage_state=STATE, viewport={'width': 1600, 'height': 1000}, user_agent=UA)
    page = await ctx.new_page()
    captured = {}

    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            headers = await req.all_headers()
            if headers.get('authorization'):
                captured.update(headers)

    page.on('request', on_req)
    await page.goto(TARGET, wait_until='networkidle', timeout=90000)
    await page.wait_for_timeout(2500)
    body = await page.locator('body').inner_text(timeout=15000)
    if 'Log in to Smart Bidding' in body or 'Email address' in body:
        raise RuntimeError('Smart Bidding session expired during apply')
    if not captured.get('authorization'):
        raise RuntimeError('authenticated API header not captured')
    headers = {k: v for k, v in captured.items() if k.lower() in {'authorization', 'accept', 'content-type'}}
    headers.update({'origin': 'https://app.smartbiddingdigital.com', 'referer': 'https://app.smartbiddingdigital.com/'})
    return pw, browser, ctx, page, headers


async def list_pools(ctx, headers):
    response = await ctx.request.post(f'{API}/routing', headers=headers, data={'publishers': [PUBLISHER]}, timeout=120000)
    data = await response.json()
    if response.status not in (200, 201) or not isinstance(data, list):
        raise RuntimeError(f'bad routing list status={response.status}')
    return response.status, data


async def fetch_targets(ctx, headers, pools):
    by_name = {}
    for name in TARGET_NAMES:
        rows = [p for p in pools if p.get('NAME') == name]
        if len(rows) != 1:
            raise RuntimeError(f'{name}: expected one pool, found {len(rows)}')
        pool_id = rows[0].get('ID')
        response = await ctx.request.get(f'{API}/routing/{pool_id}', headers=headers, timeout=120000)
        detail = await response.json()
        if response.status not in (200, 201) or not isinstance(detail, dict):
            raise RuntimeError(f'{name}: detail read failed status={response.status}')
        by_name[name] = detail
    return by_name


async def post_pool(ctx, headers, pool, routes):
    pool_id = pool.get('ID')
    response = await ctx.request.post(f'{API}/routing/{pool_id}', headers=headers, data=payload(pool, routes), timeout=120000)
    text = await response.text()
    try:
        body = json.loads(text)
    except Exception:
        body = text
    if response.status not in (200, 201):
        raise RuntimeError(f'pool {pool_id} write failed status={response.status} body={str(body)[:250]}')
    return {'http': response.status, 'body': body}


def validate_targets(targets, plans, slot_profile):
    errors = []
    groups = expected_groups()
    for plan, expected_names in zip(plans, groups):
        before = plan['before']
        actual = targets.get(before.get('NAME'))
        if not actual:
            errors.append(f'{before.get("NAME")}: missing')
            continue
        if {k: actual.get(k) for k in META_KEYS} != {k: before.get(k) for k in META_KEYS}:
            errors.append(f'{before.get("NAME")}: metadata changed')
        routes = parse_routes(actual.get('ROUTES'))
        identities = [route_identity(r)['route'] for r in routes]
        if identities != expected_names:
            errors.append(f'{before.get("NAME")}: route order mismatch {identities}')
        expected_utms = [route_identity(r)['utm_content'] for r in plan['routes']]
        if [route_identity(r)['utm_content'] for r in routes] != expected_utms:
            errors.append(f'{before.get("NAME")}: utm order mismatch')
        actual_slots = [(str(r.get('url') or '').strip(), str(r.get('jbf_operation') or '').strip()) for r in routes]
        if actual_slots != slot_profile:
            errors.append(f'{before.get("NAME")}: URL/operation slot sequence changed')
    return errors


async def rollback(ctx, headers, originals, updated_ids):
    results = []
    for pool in originals:
        if pool.get('ID') not in updated_ids:
            continue
        response = await post_pool(ctx, headers, pool, parse_routes(pool.get('ROUTES')))
        results.append({'id': pool.get('ID'), 'name': pool.get('NAME'), 'http': response['http']})
    return results


async def apply_and_validate():
    RUN.mkdir(parents=True, exist_ok=True)
    pw = browser = ctx = page = None
    originals = []
    updated_ids = []
    unrelated_before = None
    plans = None
    slot_profile = None
    try:
        pw, browser, ctx, page, headers = await open_auth()
        list_http, before_list = await list_pools(ctx, headers)
        before_targets = await fetch_targets(ctx, headers, before_list)
        originals = [before_targets[name] for name in TARGET_NAMES]
        plans, slot_profile = build_plan(before_targets)
        target_ids = {p.get('ID') for p in originals}
        unrelated_before = unrelated_signature(before_list, target_ids)
        preflight = {
            'at_et': now(),
            'authorization_message_id': AUTH_MESSAGE_ID,
            'list_http': list_http,
            'target_ids': sorted(target_ids),
            'target_structural_sha256': digest([pool_core(p) for p in originals]),
            'unrelated_signature_sha256': digest(unrelated_before),
            'slot_profile_sha256': digest(slot_profile),
            'm0_url': slot_profile[0][0],
            'nm_url': slot_profile[1][0],
            'expected_groups': expected_groups(),
        }
        dump(RUN / '02-apply-preflight.json', preflight)
        dump(BACKUP / 'fresh-before-apply-targets.json', originals)
        writes = []
        for plan in plans:
            pool = plan['before']
            response = await post_pool(ctx, headers, pool, plan['routes'])
            updated_ids.append(pool.get('ID'))
            writes.append({'id': pool.get('ID'), 'name': pool.get('NAME'), 'http': response['http']})
            dump(RUN / f"write-{pool.get('ID')}.json", {'id': pool.get('ID'), 'name': pool.get('NAME'), 'http': response['http'], 'response': response['body']})
        _, immediate_list = await list_pools(ctx, headers)
        immediate_targets = await fetch_targets(ctx, headers, immediate_list)
        errors = validate_targets(immediate_targets, plans, slot_profile)
        unrelated_after = unrelated_signature(immediate_list, set(updated_ids))
        if unrelated_after != unrelated_before:
            errors.append('unrelated pool identities/metadata changed')
        if errors:
            rollback_results = await rollback(ctx, headers, originals, set(updated_ids))
            dump(RUN / 'rollback.json', {'errors': errors, 'results': rollback_results, 'at_et': now()})
            raise RuntimeError('immediate validation failed; rollback applied: ' + '; '.join(errors))
        dump(RUN / '90-immediate-targets.json', [immediate_targets[name] for name in TARGET_NAMES])
        immediate = {
            'writes': writes,
            'errors': [],
            'target_structural_sha256': digest([pool_core(immediate_targets[name]) for name in TARGET_NAMES]),
            'unrelated_signature_sha256': digest(unrelated_after),
            'm0_url': slot_profile[0][0],
            'nm_url': slot_profile[1][0],
            'validated_at_et': now(),
        }
        dump(RUN / '91-immediate-validation.json', immediate)
    finally:
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

    # Independent fresh browser/context readback.
    pw2 = browser2 = ctx2 = page2 = None
    try:
        pw2, browser2, ctx2, page2, headers2 = await open_auth()
        http2, readback_list = await list_pools(ctx2, headers2)
        readback_targets = await fetch_targets(ctx2, headers2, readback_list)
        errors = validate_targets(readback_targets, plans, slot_profile)
        unrelated_readback = unrelated_signature(readback_list, {p.get('ID') for p in originals})
        if unrelated_readback != unrelated_before:
            errors.append('unrelated pool identities/metadata changed in independent readback')
        result = {
            'status': 'success' if not errors else 'failed',
            'authorization_message_id': AUTH_MESSAGE_ID,
            'http': http2,
            'pool_count': len(readback_targets),
            'route_count': sum(len(parse_routes(p.get('ROUTES'))) for p in readback_targets.values()),
            'groups': {name: [route_identity(r)['route'] for r in parse_routes(readback_targets[name].get('ROUTES'))] for name in TARGET_NAMES},
            'slot_url_sequence_sha256': digest(slot_profile),
            'm0_url': slot_profile[0][0],
            'nm_url': slot_profile[1][0],
            'blank_operations': sum(not str(r.get('jbf_operation') or '').strip() for p in readback_targets.values() for r in parse_routes(p.get('ROUTES'))),
            'unrelated_signature_sha256': digest(unrelated_readback),
            'errors': errors,
            'validated_at_et': now(),
            'evidence_dir': str(RUN),
            'backup_dir': str(BACKUP),
        }
        dump(RUN / 'independent-readback.json', result)
        if errors:
            # Fresh-session validation failed: restore every target from the fresh backup.
            rollback_results = await rollback(ctx2, headers2, originals, {p.get('ID') for p in originals})
            dump(RUN / 'independent-failure-rollback.json', {'errors': errors, 'results': rollback_results, 'at_et': now()})
            raise RuntimeError('independent readback failed; rollback applied: ' + '; '.join(errors))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if browser2:
            await browser2.close()
        if pw2:
            await pw2.stop()


if __name__ == '__main__':
    asyncio.run(apply_and_validate())
