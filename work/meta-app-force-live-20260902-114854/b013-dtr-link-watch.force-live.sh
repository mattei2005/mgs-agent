#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="/var/lock/b013-dtr-link-watch-force-live-20260902.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

BASE_DIR="/root/mgs-agent"
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a

PYTHON_BIN="${MGS_B013_DTR_PYTHON:-/root/.local/share/mgs/sb-venv/bin/python}"
exec "$PYTHON_BIN" - <<'PY'
import asyncio
import csv
import importlib.util
import json
import os
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

VAULT = os.environ.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')
CONFIG_ITEM_LABEL = 'BOT B013-4 Token - Dayanna Regis'
# Resolve the exact current B013-4 registry item. The app-name and channel
# identity guards below prevent a stale predecessor credential from running.
CONFIG_ITEM = os.environ.get('MGS_B013_CONFIG_ITEM', CONFIG_ITEM_LABEL)
DISCORD_BOT_ITEM = os.environ.get('MGS_DISCORD_BOT_ITEM', 'Discord Bot - Zeus')
STATE_PATH = Path(os.environ.get('MGS_B013_DTR_STATE', '/root/mgs-agent/data/b013-dtr-link-monitor-state.json'))
GRAPH_VERSION = os.environ.get('MGS_META_GRAPH_VERSION', 'v20.0')
GRAPH = f'https://graph.facebook.com/{GRAPH_VERSION}'
RODOLFO_ID = '344196393512075265'
POSSIBLE_RESTRICTION_ROLE_IDS = (
    '1185978575782936586',  # Super Admin
    '1496256346994249912',  # Gestor de Trafego
    '1496260941787168848',  # Admin
)
POSSIBLE_RESTRICTION_EMOJIS = '🚨🚨🚨🚨🚨'
INFRA_CHANNEL_ID = '1498132022634483894'
DRY_RUN = os.environ.get('MGS_B013_DTR_DRY_RUN', '').lower() in {'1', 'true', 'yes'}
FORCE_LIVE_ALERT = os.environ.get('MGS_B013_DTR_FORCE_LIVE_ALERT', '').lower() in {'1', 'true', 'yes'}
UNKNOWN_ALERT_THRESHOLD = int(os.environ.get('MGS_B013_DTR_UNKNOWN_ALERT_THRESHOLD', '2'))
ALERT_COOLDOWN_MINUTES = int(os.environ.get('MGS_B013_DTR_ALERT_COOLDOWN_MINUTES', '360'))
MAX_TARGETS = int(os.environ.get('MGS_B013_DTR_MAX_TARGETS', '0') or '0')
REQUIRE_MIGRADO_TRUE = os.environ.get('MGS_B013_DTR_REQUIRE_MIGRADO_TRUE', '0').lower() in {'1', 'true', 'yes'}
OP_RESOLVER_PATH = Path('/root/mgs-agent/scripts/mgs-op-item-resolver.py')
GOOGLE_AUTH_HELPER_PATH = Path('/root/mgs-agent/scripts/mgs_google_workspace_auth.py')
GOOGLE_QUOTA_PROJECT = ''

_op_spec = importlib.util.spec_from_file_location('mgs_op_item_resolver', OP_RESOLVER_PATH)
if not _op_spec or not _op_spec.loader:
    raise RuntimeError(f'cannot load 1Password resolver: {OP_RESOLVER_PATH}')
OP_RESOLVER=importlib.util.module_from_spec(_op_spec)
_op_spec.loader.exec_module(OP_RESOLVER)
_google_auth_spec = importlib.util.spec_from_file_location('mgs_google_workspace_auth', GOOGLE_AUTH_HELPER_PATH)
if not _google_auth_spec or not _google_auth_spec.loader:
    raise RuntimeError(f'cannot load Google Service Account helper: {GOOGLE_AUTH_HELPER_PATH}')
GOOGLE_AUTH = importlib.util.module_from_spec(_google_auth_spec)
_google_auth_spec.loader.exec_module(GOOGLE_AUTH)


def now_dt():
    return datetime.now(ZoneInfo('America/New_York'))


def now_iso():
    return now_dt().isoformat(timespec='seconds')


def norm(value):
    s = str(value or '').strip().casefold()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s)


def app_key_from_sheet_value(value):
    raw = str(value or '').strip().upper()
    m = re.fullmatch(r'B\s*0*(\d{1,3})(?:\s*-\s*(\d+)|\s*([A-Z]+))?', raw)
    if not m:
        return raw
    key = f"B{int(m.group(1)):03d}"
    if m.group(2):
        key += '-' + m.group(2)
    elif m.group(3):
        key += m.group(3)
    return key


def load_config():
    item = OP_RESOLVER.get_item_json(CONFIG_ITEM, VAULT)
    app_id = OP_RESOLVER.field_value(item, 'app_id', required=True)
    app_name = (OP_RESOLVER.field_value(item, 'app_name') or '').strip().upper()
    alert_channel_id = (OP_RESOLVER.field_value(item, 'alert_channel_id') or '').strip()
    if app_name != 'B013-4':
        raise RuntimeError('B013-4 config identity mismatch; refusing stale predecessor credentials')
    if alert_channel_id != '1522830283240505385':
        raise RuntimeError('B013-4 alert channel mismatch; refusing to post or reconcile')
    return {
        'app_id': app_id,
        'app_name': app_name,
        'app_secret': OP_RESOLVER.field_value(item, 'app_secret', required=True),
        'dtr_base_url': (OP_RESOLVER.field_value(item, 'dtr_base_url') or 'https://digitaltrchat.com').rstrip('/'),
        'sheet_id': OP_RESOLVER.field_value(item, 'sheet_id') or '1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY',
        'sheet_gid': OP_RESOLVER.field_value(item, 'sheet_gid') or '542936436',
        'alert_channel_id': alert_channel_id,
    }


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {'_corrupt_backup_at': now_iso(), 'accounts': {}}
    return {'_created_at': now_iso(), 'accounts': {}}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(STATE_PATH)


def graph(path, params, token):
    q = urllib.parse.urlencode({**params, 'access_token': token})
    req = urllib.request.Request(f'{GRAPH}{path}?{q}', headers={'User-Agent': 'MGS-Zeus-B013-DTR-Link-Watch/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            headers = {k.lower(): v for k, v in r.headers.items()}
            return r.status, headers, json.loads(r.read().decode('utf-8', 'replace') or '{}')
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            body = json.loads(raw)
        except Exception:
            body = {'raw': raw[:500]}
        return e.code, {k.lower(): v for k, v in e.headers.items()}, body


def sheet_rows(config):
    token = google_service_account_access_token()
    title = sheet_title_for_gid(config, token)
    rng = quote_sheet_range(title, 'A:N')
    status, body = sheets_request(
        'GET',
        f"/spreadsheets/{config['sheet_id']}/values/{urllib.parse.quote(rng, safe='')}?majorDimension=ROWS",
        token,
    )
    if status != 200:
        raise RuntimeError(f'Sheets B013-4 read failed status={status} body={str(body)[:300]}')
    values = body.get('values') or []
    if not values:
        raise RuntimeError('Sheets B013-4 read returned no rows')
    headers = [str(x) for x in values[0]]
    removed_header = 'Removidos acumulado' if 'Removidos acumulado' in headers else ('zzzaa' if 'zzzaa' in headers else '')
    required_headers = {'User', 'Segurador', 'PG', 'USUARIO', 'NO APP'}
    missing_headers = sorted(required_headers - set(headers))
    if missing_headers:
        raise RuntimeError(f'Sheets B013-4 required headers missing: {missing_headers}')
    targets = []
    for idx, values_row in enumerate(values[1:], start=2):
        padded = list(values_row) + [''] * max(0, len(headers) - len(values_row))
        row = dict(zip(headers, padded[:len(headers)]))
        row['Removidos acumulado'] = row.get(removed_header, '') if removed_header else ''
        if app_key_from_sheet_value(row.get('NO APP')) != 'B013-4':
            continue
        migrado = str(row.get('Migrado') or row.get('Migracao') or '').strip().upper()
        sheet_x = str(row.get('Removidos acumulado') or '').strip().upper()
        if REQUIRE_MIGRADO_TRUE and migrado != 'TRUE':
            continue
        user = (row.get('User') or '').strip()
        segurador = (row.get('Segurador') or '').strip()
        if not user or not segurador:
            continue
        targets.append({
            'row': idx,
            'sheet_x': (row.get('Removidos acumulado') or '').strip(),
            'user': user,
            'segurador': segurador,
            'profile_id': (row.get('USUARIO') or '').strip(),
            'pages': (row.get('PG') or '').strip(),
        })
    if MAX_TARGETS:
        targets = targets[:MAX_TARGETS]
    return targets


def map_dtr_items(users):
    mapped, missing, _errors, _cache = OP_RESOLVER.resolve_dtr_items(users, VAULT)
    # The metadata cache is intentionally long-lived to reduce 1Password use,
    # but a cache miss must be confirmed live before becoming an incident.
    if missing:
        refreshed, _still_missing, _refresh_errors, _fresh_cache = OP_RESOLVER.resolve_dtr_items(
            missing, VAULT, force_refresh=True
        )
        mapped.update(refreshed)
    return {username: row['id'] for username, row in mapped.items()}


def extract_token_from_html(src):
    # DigitalTRChat renders the active FB connection token in graph.facebook.com/me/picture URLs.
    # Never print or persist this token.
    vals = re.findall(r'access_token=([^&"\']+)', src)
    return urllib.parse.unquote(vals[0]) if vals else ''


def should_alert(prev, key, status):
    alerts = prev.setdefault('alerts', {})
    item = alerts.get(key) or {}
    if item.get('status') != status:
        return True
    ts = item.get('at')
    try:
        last = datetime.fromisoformat(ts) if ts else None
    except Exception:
        last = None
    if not last:
        return True
    return (now_dt() - last).total_seconds() >= ALERT_COOLDOWN_MINUTES * 60


def mark_alert(prev, key, status):
    prev.setdefault('alerts', {})[key] = {'status': status, 'at': now_iso()}


def clear_alert(prev, key):
    alerts = prev.setdefault('alerts', {})
    alerts.pop(key, None)


def persistent_unknown_status(rows):
    parts = sorted(
        f"{str(r.get('user') or '').strip().casefold()}|{norm(r.get('segurador'))}|{str(r.get('link_status') or 'unknown')}"
        for r in rows
    )
    return f"persistent_unknowns={len(rows)};" + ';'.join(parts)


def post_request_with_rate_limit_retry(req, max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt >= max_attempts:
                raise
            raw = exc.read().decode('utf-8', 'replace')
            try:
                body = json.loads(raw or '{}')
            except Exception:
                body = {}
            retry_after = body.get('retry_after') or exc.headers.get('X-RateLimit-Reset-After') or exc.headers.get('Retry-After') or 1.0
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = 1.0
            time.sleep(min(max(delay, 0.25), 15.0) + 0.15)


def post_discord(config, content, embed=None, allowed_mentions=None):
    if allowed_mentions is None:
        allowed_mentions = {'users': [RODOLFO_ID]}
    if DRY_RUN:
        print(json.dumps({'dry_run_alert': content, 'embed': embed, 'allowed_mentions': allowed_mentions}, ensure_ascii=False))
        return 0
    token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
    if not token:
        raise RuntimeError('local Zeus Discord bot token unavailable')
    payload = {'content': content, 'allowed_mentions': allowed_mentions}
    if embed:
        payload['embeds'] = [embed]
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{config['alert_channel_id']}/messages",
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bot {token}', 'User-Agent': 'MGS-Zeus-B013-DTR-Link-Watch/1.0'},
        method='POST',
    )
    return post_request_with_rate_limit_retry(req)


def possible_restriction_content():
    role_mentions = ' '.join(f'<@&{role_id}>' for role_id in POSSIBLE_RESTRICTION_ROLE_IDS)
    return f'{POSSIBLE_RESTRICTION_EMOJIS}\n{role_mentions}'


def possible_restriction_allowed_mentions():
    return {'parse': [], 'roles': list(POSSIBLE_RESTRICTION_ROLE_IDS)}


def possible_restriction_embed(app_name, affected_count):
    return {
        'title': f'{app_name} - POSSÍVEL RESTRIÇÃO',
        'description': (
            'O monitor tentou verificar essas contas em **duas ou mais execuções**, '
            'mas não recebeu informações confiáveis para confirmar se continuam conectadas.\n\n'
            'Para evitar marcações incorretas, **a planilha não foi alterada**.'
        ),
        'color': 16776960,
        'fields': [
            {'name': 'Contas afetadas', 'value': str(affected_count), 'inline': True},
            {
                'name': 'O que isso significa',
                'value': 'Ainda não existe confirmação de desconexão. Pode ser uma falha temporária no acesso ao DigitalTRChat ou à Meta.',
                'inline': False,
            },
            {
                'name': 'O que fazer agora',
                'value': (
                    '1. Verificar se as contas abrem normalmente no **DigitalTRChat**.\n'
                    '2. Confirmar se os acessos continuam ativos na **Meta**.\n'
                    '3. Se o problema persistir, revisar as credenciais dessas contas.'
                ),
                'inline': False,
            },
            {
                'name': 'Proteção aplicada',
                'value': 'Nenhuma conta foi marcada como removida e nenhuma alteração foi feita na planilha.',
                'inline': False,
            },
        ],
    }


def google_service_account_access_token():
    global GOOGLE_QUOTA_PROJECT
    GOOGLE_QUOTA_PROJECT = GOOGLE_AUTH.service_account_project_id()
    return GOOGLE_AUTH.service_account_access_token(GOOGLE_AUTH.SHEETS_SCOPE)


def sheets_request(method, path, token, payload=None, attempts=3):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus-B013-DTR-Link-Watch/2.0'}
    if GOOGLE_QUOTA_PROJECT:
        headers['x-goog-user-project'] = GOOGLE_QUOTA_PROJECT
    last_transport_error = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(
            f'https://sheets.googleapis.com/v4{path}',
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, json.loads(r.read().decode('utf-8', 'replace') or '{}')
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'replace')
            try:
                body = json.loads(raw)
            except Exception:
                body = {'raw': raw[:500]}
            if e.code in {429, 500, 502, 503, 504} and attempt < attempts:
                time.sleep(attempt)
                continue
            return e.code, body
        except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
            last_transport_error = e
            if attempt < attempts:
                time.sleep(attempt)
                continue
            raise RuntimeError(f'Sheets transport failed after {attempts} attempts: {type(e).__name__}') from e
    raise RuntimeError(f'Sheets transport failed: {type(last_transport_error).__name__ if last_transport_error else "unknown"}')


def sheet_title_for_gid(config, token):
    status, body = sheets_request('GET', f"/spreadsheets/{config['sheet_id']}?fields=sheets(properties(sheetId,title))", token)
    if status != 200:
        raise RuntimeError(f'Sheets metadata failed status={status} body={str(body)[:300]}')
    gid = int(config['sheet_gid'])
    for sh in body.get('sheets') or []:
        props = sh.get('properties') or {}
        if int(props.get('sheetId')) == gid:
            return props.get('title')
    raise RuntimeError(f'Sheet gid not found: {gid}')


def quote_sheet_range(title, cell_range):
    return "'" + str(title).replace("'", "''") + "'!" + cell_range


def sync_sheet_x(config, results):
    """Write X only for a confirmed unlinked verdict; preserve unknown rows fail-closed."""
    updates = []
    desired_by_row = {}
    unknown_rows = 0
    for r in results:
        if not r.get('row'):
            continue
        verdict = r.get('verdict')
        if verdict == 'linked':
            desired = ''
        elif verdict == 'unlinked_confirmed':
            desired = 'X'
        else:
            unknown_rows += 1
            continue
        current = 'X' if str(r.get('sheet_x') or '').strip().upper() == 'X' else ''
        desired_by_row[int(r['row'])] = desired
        if desired != current:
            updates.append((int(r['row']), desired))
    result = {
        'enabled': True,
        'checked_rows': len(desired_by_row),
        'marked': sum(1 for v in desired_by_row.values() if v == 'X'),
        'unknown_preserved': unknown_rows,
        'updates_needed': len(updates),
        'updated': False,
        'checked_at': now_iso(),
    }
    if DRY_RUN or not updates:
        return result
    token = google_service_account_access_token()
    title = sheet_title_for_gid(config, token)
    data = []
    for row, value in updates:
        rng = quote_sheet_range(title, f'A{row}:A{row}')
        data.append({'range': rng, 'majorDimension': 'ROWS', 'values': [[value]]})
    status, body = sheets_request(
        'POST',
        f"/spreadsheets/{config['sheet_id']}/values:batchUpdate",
        token,
        {'valueInputOption': 'RAW', 'data': data},
    )
    if status not in {200, 201}:
        raise RuntimeError(f'Sheets B013-4 X sync failed status={status} body={str(body)[:300]}')
    result.update({'updated': True, 'updated_cells': body.get('totalUpdatedCells'), 'updated_ranges': len(data)})
    return result


async def login(ctx, base_url, item):
    bundle = OP_RESOLVER.get_login_bundle(item, VAULT)
    username = bundle['username']
    password = bundle['password']
    page = await ctx.new_page()
    await page.goto(base_url + '/home/login', wait_until='domcontentloaded', timeout=60000)
    inputs = page.locator('input:visible')
    await inputs.nth(0).fill(username)
    await inputs.nth(1).fill(password)
    await page.locator('button:visible, input[type=submit]:visible').last.click()
    await page.wait_for_timeout(3000)
    await page.goto(base_url + '/social_accounts/index', wait_until='domcontentloaded', timeout=60000)
    return page


async def inspect_item(browser, config, item, targets):
    ctx = await browser.new_context(viewport={'width': 1600, 'height': 1000})
    page = await login(ctx, config['dtr_base_url'], item)
    try:
        csrf = await page.locator('#csrf_token').input_value(timeout=4000)
    except Exception:
        csrf = ''
    accounts = await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el => ({id: el.getAttribute('data-id') || el.dataset.id || '', name: (el.innerText || el.textContent || '').trim()})).filter(x => x.id || x.name)""")
    by_name = {norm(a['name']): a for a in accounts}
    results = []
    app_token = f"{config['app_id']}|{config['app_secret']}"
    for target in targets:
        rec = {**target, 'dtr_item': item, 'checked_at': now_iso(), 'linked': False, 'verdict': 'unknown', 'link_status': 'unknown', 'pages_visible': None, 'graph_pages': None, 'connected_pages': None, 'error': None}
        acc = by_name.get(norm(target['segurador']))
        if not acc:
            rec.update({'link_status': 'not_found_in_dtr_switcher', 'error': 'account_not_found_in_dtr_switcher'})
            results.append(rec)
            continue
        rec['dtr_account_id'] = acc.get('id')
        sw = await ctx.request.post(config['dtr_base_url'] + '/social_accounts/fb_rx_account_switch', form={'id': acc.get('id'), 'csrf_token': csrf}, headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': config['dtr_base_url'] + '/social_accounts/index'})
        rec['switch_status'] = sw.status
        await page.goto(config['dtr_base_url'] + '/social_accounts/index', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(900)
        body = await page.locator('body').inner_text()
        m = re.search(r'(\d+)\s+Pages', body)
        rec['pages_visible'] = int(m.group(1)) if m else None
        rec['active_label'] = await page.evaluate("""() => (document.querySelector('.account_switch.d-none')?.innerText || document.querySelector('.nav-link-user')?.innerText || '').trim()""")
        token = extract_token_from_html(await page.content())
        if not token:
            rec.update({'link_status': 'no_token_in_dtr_html', 'error': 'no_token_in_dtr_html'})
            results.append(rec)
            continue
        st, headers, dbg = graph('/debug_token', {'input_token': token, 'fields': 'app_id,application,is_valid,scopes,user_id,expires_at'}, app_token)
        data = dbg.get('data') or {}
        rec['debug_status'] = st
        rec['debug_app_id'] = data.get('app_id')
        rec['debug_application'] = data.get('application')
        rec['debug_is_valid'] = data.get('is_valid')
        rec['linked'] = bool(st == 200 and data.get('is_valid') is True and str(data.get('app_id')) == str(config['app_id']))
        if rec['linked']:
            rec['verdict'] = 'linked'
            rec['link_status'] = 'linked'
            st2, _, accs = graph('/me/accounts', {'fields': 'id,name,access_token', 'limit': '250'}, token)
            pages = accs.get('data') or [] if st2 == 200 else []
            rec['accounts_status'] = st2
            rec['graph_pages'] = len(pages)
            connected = 0
            for pg in pages:
                pst, _, subs = graph(f"/{pg.get('id')}/subscribed_apps", {'fields': 'id,name', 'limit': '100'}, pg.get('access_token', ''))
                apps = subs.get('data') or [] if pst == 200 else []
                if any(str(a.get('id')) == str(config['app_id']) for a in apps):
                    connected += 1
            rec['connected_pages'] = connected
        else:
            err = dbg.get('error') or {}
            err_message = str(err.get('message') or '')
            app_mismatch_confirmed = (
                st in {400, 403}
                and int(err.get('code') or 0) == 100
                and 'app_id' in err_message.casefold()
                and 'did not match the viewing app' in err_message.casefold()
            )
            if st == 200 or app_mismatch_confirmed:
                # A valid debug payload for another app, or Graph's explicit
                # App_id/View-App mismatch, is sufficient evidence that the DTR
                # token is not linked to B013-4. Other HTTP errors remain unknown.
                rec['verdict'] = 'unlinked_confirmed'
                rec['link_status'] = 'token_app_mismatch' if app_mismatch_confirmed else 'not_linked_or_invalid'
            else:
                rec['verdict'] = 'unknown'
                rec['link_status'] = 'debug_token_check_failed'
            rec['error'] = {
                'code': err.get('code'),
                'type': err.get('type'),
                'message': err_message[:300] or 'debug_token did not validate against B013-4',
            }
        results.append(rec)
    await ctx.close()
    return results


def summarize(results):
    linked = [r for r in results if r.get('verdict') == 'linked']
    return {
        'targets': len(results),
        'linked': len(linked),
        'unlinked_confirmed': sum(1 for r in results if r.get('verdict') == 'unlinked_confirmed'),
        'unknown': sum(1 for r in results if r.get('verdict') not in {'linked', 'unlinked_confirmed'}),
        'not_linked_or_error': sum(1 for r in results if r.get('verdict') != 'linked'),
        'total_dtr_pages_visible': sum(int(r.get('pages_visible') or 0) for r in linked),
        'total_graph_pages': sum(int(r.get('graph_pages') or 0) for r in linked),
        'total_connected_pages': sum(int(r.get('connected_pages') or 0) for r in linked),
        'linked_debug_valid': sum(1 for r in linked if r.get('debug_is_valid') is True),
        'linked_accounts_status_200': sum(1 for r in linked if r.get('accounts_status') == 200),
        'linked_dtr_pages_zero_graph': sum(
            1 for r in linked
            if int(r.get('pages_visible') or 0) > 0 and int(r.get('graph_pages') or 0) == 0
        ),
    }


def app_capability_health(summary):
    """Detect an app-wide functional permission collapse without sending messages.

    A valid debug_token only proves token/app identity. B013-4 can still lose its
    advanced page permissions when its owning Business Manager is restricted.
    Cross-account DTR-vs-Graph inventory is the safe read-only capability probe.
    """
    min_accounts = 3
    linked = int(summary.get('linked') or 0)
    debug_valid = int(summary.get('linked_debug_valid') or 0)
    accounts_ok = int(summary.get('linked_accounts_status_200') or 0)
    dtr_pages = int(summary.get('total_dtr_pages_visible') or 0)
    graph_pages = int(summary.get('total_graph_pages') or 0)
    zero_graph_accounts = int(summary.get('linked_dtr_pages_zero_graph') or 0)
    evidence_sufficient = (
        linked >= min_accounts
        and debug_valid >= min_accounts
        and accounts_ok >= min_accounts
        and dtr_pages > 0
    )
    if evidence_sufficient and graph_pages == 0 and zero_graph_accounts >= min_accounts:
        status = 'blocked'
    elif evidence_sufficient and graph_pages > 0:
        status = 'healthy'
    else:
        status = 'inconclusive'
    return {
        'status': status,
        'linked_accounts': linked,
        'debug_valid': debug_valid,
        'accounts_status_200': accounts_ok,
        'dtr_pages_visible': dtr_pages,
        'graph_pages_visible': graph_pages,
        'dtr_pages_zero_graph_accounts': zero_graph_accounts,
        'checked_at': now_iso(),
    }


def build_alert_lines(changes, failures):
    lines = []
    if changes:
        lines.append('Mudanças:')
        for c in changes[:12]:
            lines.append(f"- {c['segurador']} ({c['user']}): {c['old']} → {c['new']}")
    if failures:
        lines.append('Falhas atuais:')
        for f in failures[:12]:
            err = f.get('error') or f.get('link_status')
            if isinstance(err, dict):
                err = err.get('message') or err.get('type') or err.get('code')
            lines.append(f"- {f['segurador']} ({f['user']}): {err}")
    return '\n'.join(lines)[:1800]


def code_blocks(text):
    lines = str(text or '').rstrip().splitlines() or ['']
    blocks = []
    current = []
    current_len = 0
    max_inner = 1988
    for line in lines:
        line_len = len(line) + (1 if current else 0)
        if current and current_len + line_len > max_inner:
            blocks.append('```\n' + '\n'.join(current).rstrip() + '\n```')
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += line_len
    if current:
        blocks.append('```\n' + '\n'.join(current).rstrip() + '\n```')
    return blocks


def post_code_blocks(config, text):
    for block in code_blocks(text):
        post_discord(config, block)


def code_block(text):
    blocks = code_blocks(text)
    return blocks[0] if blocks else '```\n\n```'


def section_block(title, body):
    line = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
    return f"{line}\n{title}\n{line}\n{body or 'Nenhum.'}"


def display_bot_email(value):
    text = str(value or '').strip()
    if not text or text == 'sem email':
        return 'sem email'
    return text.split('@', 1)[0]


def fmt_status_rows(results):
    current = [r for r in results if r.get('linked')]
    rows = ['BOT EMAIL                 | SEGURADOR                | PERFIL ID          | PÁGINAS']
    for r in sorted(current, key=lambda x: (str(x.get('user') or '').lower(), str(x.get('segurador') or '').lower())):
        user = display_bot_email(r.get('user'))[:24]
        seg = str(r.get('segurador') or 'sem segurador')[:24]
        profile_id = str(r.get('profile_id') or '-')[:18]
        pages = str(r.get('pages') or (r.get('connected_pages') if r.get('connected_pages') is not None else '-'))
        rows.append(f"{user:<25} | {seg:<24} | {profile_id:<18} | {pages}")
    return '\n'.join(rows)


def fmt_change_rows(changes, mode=None):
    if mode == 'removed':
        changes = [
            c for c in changes
            if c.get('kind') == 'removed'
            or (not c.get('kind') and c.get('new') != 'linked')
        ]
    elif mode == 'added':
        changes = [
            c for c in changes
            if c.get('kind') == 'added'
            or (not c.get('kind') and c.get('new') == 'linked')
        ]
    if not changes:
        return 'Nenhum.'
    rows = ['BOT EMAIL                 | SEGURADOR                | MUDANÇA']
    for c in changes[:30]:
        rows.append(f"{str(c.get('user') or '')[:24]:<25} | {str(c.get('segurador') or '')[:24]:<24} | {c.get('old')} → {c.get('new')}")
    return '\n'.join(rows)


def fmt_pending_rows(failures):
    if not failures:
        return 'Nenhum.'
    rows = ['BOT EMAIL                 | SEGURADOR                | PERFIL ID          | PÁGINAS']
    for f in failures[:30]:
        rows.append(f"{display_bot_email(f.get('user'))[:24]:<25} | {str(f.get('segurador') or '')[:24]:<24} | {str(f.get('profile_id') or '-')[:18]:<18} | {str(f.get('pages') or '-')[:12]}")
    return '\n'.join(rows)


def b013_summary_embed(summary, failures, unknowns, requested=False):
    capability = app_capability_health(summary)
    if capability.get('status') == 'blocked':
        severity = 'CRÍTICO'
        color = 15158332
    elif failures or unknowns:
        severity = 'ATENÇÃO'
        color = 16776960
    else:
        severity = 'OK'
        color = 5763719
    if requested:
        description = 'Alerta live solicitado. Dados consultados agora no DTR/ChatPion e Meta Graph e reconciliados com a planilha.'
    else:
        description = 'Mudança de conexão detectada. Dados consultados agora no DTR/ChatPion e Meta Graph e reconciliados com a planilha.'
    return {
        'title': 'Meta APP - B013-4',
        'description': description,
        'color': color,
        'fields': [
            {'name': 'ESTADO', 'value': severity, 'inline': True},
            {'name': 'CONTAGEM', 'value': f"{summary.get('linked')}/{summary.get('targets')}", 'inline': True},
            {'name': 'PENDENTES', 'value': str(summary.get('not_linked_or_error')), 'inline': True},
            {'name': 'PÁGINAS', 'value': f"{summary.get('total_connected_pages')} conectadas", 'inline': True},
            {'name': 'DTR', 'value': f"{summary.get('total_dtr_pages_visible')} visíveis", 'inline': True},
            {'name': 'META', 'value': f"{summary.get('total_graph_pages')} visíveis", 'inline': True},
        ],
        'footer': {'text': 'MGS Zeus • App Connection Watch'},
    }


def post_live_alert(config, summary, results, changes, failures, unknowns, sheet_sync):
    embed = b013_summary_embed(summary, failures, unknowns, requested=True)
    post_discord(config, f'<@{RODOLFO_ID}>', embed)
    post_code_blocks(config, section_block('👥 USUÁRIOS ATUAIS', fmt_status_rows(results)))
    sections = [
        section_block('➖ USUÁRIOS REMOVIDOS AGORA', fmt_change_rows(changes, 'removed')),
        section_block('🆕 USUÁRIOS ADICIONADOS AGORA', fmt_change_rows(changes, 'added')),
        section_block('📦 REMOVIDOS CONFIRMADOS', fmt_pending_rows(failures)),
    ]
    if unknowns:
        sections.append(section_block('⚠️ INCONCLUSIVOS — PLANILHA PRESERVADA', fmt_pending_rows(unknowns)))
    movement = '\n\n'.join(sections)
    post_code_blocks(config, movement)


async def main():
    config = load_config()
    targets = sheet_rows(config)
    item_by_user = map_dtr_items([t['user'] for t in targets])
    grouped = defaultdict(list)
    results = []
    for t in targets:
        item = item_by_user.get(t['user'].casefold())
        if not item:
            results.append({**t, 'checked_at': now_iso(), 'linked': False, 'verdict': 'unknown', 'link_status': 'missing_dtr_1p_item', 'error': 'missing_dtr_1p_item'})
        else:
            grouped[item].append(t)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        for item, tgts in grouped.items():
            try:
                results.extend(await inspect_item(browser, config, item, tgts))
            except Exception as e:
                for t in tgts:
                    results.append({**t, 'dtr_item': item, 'checked_at': now_iso(), 'linked': False, 'verdict': 'unknown', 'link_status': 'item_check_failed', 'error': str(e)[:300]})
        await browser.close()

    state = load_state()
    accounts_state = state.setdefault('accounts', {})
    initialized = bool(state.get('initialized'))
    changes = []
    failures = []
    unknowns = []
    seen_keys = set()
    for r in results:
        key = f"{r.get('user','').casefold()}|{norm(r.get('segurador'))}"
        seen_keys.add(key)
        prev = accounts_state.get(key, {})
        old = prev.get('link_status')
        new = r.get('link_status')
        verdict = r.get('verdict')
        consecutive_unknown = int(prev.get('consecutive_unknown') or 0) + 1 if verdict == 'unknown' else 0
        r['consecutive_unknown'] = consecutive_unknown
        if initialized and not old:
            # A newly assigned B013 target is a material addition even when its
            # first DTR/Meta validation is inconclusive. Previously this branch
            # was silently absorbed into the baseline because only old->new
            # transitions were recorded.
            changes.append({
                'user': r.get('user'),
                'segurador': r.get('segurador'),
                'old': 'not_monitored',
                'new': new,
                'kind': 'added',
            })
        elif initialized and old != new and verdict != 'unknown':
            changes.append({
                'user': r.get('user'),
                'segurador': r.get('segurador'),
                'old': old,
                'new': new,
                'kind': 'added' if new == 'linked' else 'removed',
            })
        prev.update(r)
        prev['last_seen_at'] = now_iso()
        accounts_state[key] = prev
        if verdict == 'unlinked_confirmed':
            failures.append(r)
        elif verdict == 'unknown':
            unknowns.append(r)

    # Detect rows moved away from B013. Remove the stale baseline entry so a
    # future reassignment is correctly emitted as a new addition.
    if initialized:
        for key in sorted(set(accounts_state) - seen_keys):
            prev = accounts_state.pop(key)
            changes.append({
                'user': prev.get('user'),
                'segurador': prev.get('segurador'),
                'old': prev.get('link_status') or 'monitored',
                'new': 'removed_from_b013',
                'kind': 'removed',
            })

    summary = summarize(results)
    capability = app_capability_health(summary)
    try:
        sheet_sync = sync_sheet_x(config, results)
    except Exception as e:
        sheet_sync = {'enabled': True, 'updated': False, 'error': str(e)[:500], 'checked_at': now_iso()}
    state.update({
        'initialized': True,
        'config_item': CONFIG_ITEM_LABEL,
        'config_item_ref': CONFIG_ITEM,
        'app_id': config['app_id'],
        'alert_channel_id': config['alert_channel_id'],
        'app_capability': capability,
        '_updated_at': now_iso(),
        '_last_run_summary': {**summary, 'app_capability': capability, 'sheet_sync': sheet_sync},
    })
    alerts_sent = 0
    link_change_alert_sent = False
    if (not DRY_RUN) and initialized and changes and should_alert(state, 'b013_link_health', f"changes={len(changes)} failures={len(failures)}"):
        embed = b013_summary_embed(summary, failures, unknowns, requested=FORCE_LIVE_ALERT)
        post_discord(config, f'<@{RODOLFO_ID}>', embed)
        post_code_blocks(config, section_block('👥 USUÁRIOS ATUAIS', fmt_status_rows(results)))
        sections = [
            section_block('➖ USUÁRIOS REMOVIDOS AGORA', fmt_change_rows(changes, 'removed')),
            section_block('🆕 USUÁRIOS ADICIONADOS AGORA', fmt_change_rows(changes, 'added')),
            section_block('📦 REMOVIDOS CONFIRMADOS', fmt_pending_rows(failures)),
        ]
        if unknowns:
            sections.append(section_block('⚠️ INCONCLUSIVOS — PLANILHA PRESERVADA', fmt_pending_rows(unknowns)))
        post_code_blocks(config, '\n\n'.join(sections))
        mark_alert(state, 'b013_link_health', f"changes={len(changes)} failures={len(failures)}")
        alerts_sent += 1
        link_change_alert_sent = True
    capability_status = capability.get('status')
    capability_alert_open = (
        ((state.get('alerts') or {}).get('b013_app_capability') or {}).get('status') == 'blocked'
    )
    if (
        (not DRY_RUN)
        and initialized
        and capability_status == 'blocked'
        and should_alert(state, 'b013_app_capability', 'blocked')
    ):
        embed = {
            'title': 'B013-4 — Messenger bloqueado por permissões/BM',
            'description': 'Os tokens continuam válidos, mas o app perdeu acesso funcional às páginas. O DTR pode registrar o disparo enquanto a Meta falha no OAuth e não entrega as mensagens.',
            'color': 15158332,
            'fields': [
                {'name': 'ESTADO', 'value': 'CRÍTICO — CAPACIDADE BLOQUEADA', 'inline': False},
                {'name': 'EVIDÊNCIA DTR', 'value': f"{capability['dtr_pages_visible']} páginas visíveis", 'inline': True},
                {'name': 'EVIDÊNCIA META', 'value': f"0 páginas via Graph ({capability['accounts_status_200']} consultas HTTP 200)", 'inline': True},
                {'name': 'TOKENS', 'value': f"{capability['debug_valid']}/{capability['linked_accounts']} válidos no debug_token", 'inline': True},
                {'name': 'CAUSA PROVÁVEL', 'value': 'BM proprietária restrita ou verificação empresarial exigida, deixando permissões avançadas inativas. O endpoint de permissões pode continuar mostrando live e não é prova de entrega.', 'inline': False},
                {'name': 'AÇÃO', 'value': 'Pausar disparos B013. Solicitar revisão/verificação da BM; se não liberar, mover o app para uma BM saudável. Retomar quando o monitor confirmar a recuperação funcional das permissões e das páginas via Meta Graph.', 'inline': False},
            ],
            'footer': {'text': 'MGS Zeus • B013 Messenger Capability Watch'},
        }
        post_discord(config, f'<@{RODOLFO_ID}>', embed)
        mark_alert(state, 'b013_app_capability', 'blocked')
        alerts_sent += 1
    elif (
        (not DRY_RUN)
        and initialized
        and capability_status == 'healthy'
        and capability_alert_open
    ):
        embed = {
            'title': 'B013-4 — capacidade Messenger recuperada',
            'description': 'A Meta voltou a expor páginas via Graph para tokens B013 válidos. A falha funcional de permissões/BM deixou de ser detectada.',
            'color': 5763719,
            'fields': [
                {'name': 'ESTADO', 'value': 'RECUPERADO', 'inline': True},
                {'name': 'DTR', 'value': f"{capability['dtr_pages_visible']} páginas visíveis", 'inline': True},
                {'name': 'META GRAPH', 'value': f"{capability['graph_pages_visible']} páginas visíveis", 'inline': True},
                {'name': 'PRÓXIMO PASSO', 'value': 'Capacidade funcional restabelecida; os disparos B013 podem ser retomados sem confirmação manual adicional.', 'inline': False},
            ],
            'footer': {'text': 'MGS Zeus • B013 Messenger Capability Watch'},
        }
        post_discord(config, f'<@{RODOLFO_ID}>', embed)
        clear_alert(state, 'b013_app_capability')
        alerts_sent += 1
    persistent_unknowns = [r for r in unknowns if int(r.get('consecutive_unknown') or 0) >= UNKNOWN_ALERT_THRESHOLD]
    unknown_status = persistent_unknown_status(persistent_unknowns)
    if (not DRY_RUN) and initialized and persistent_unknowns and should_alert(state, 'b013_unknown_health', unknown_status):
        embed = possible_restriction_embed(config['app_name'], len(persistent_unknowns))
        # This is an app-operational alert and belongs in the B013 channel.
        # #alerts-infra is reserved exclusively for canonical REPORT-INFRA embeds.
        post_discord(
            config,
            possible_restriction_content(),
            embed,
            allowed_mentions=possible_restriction_allowed_mentions(),
        )
        post_discord(
            config,
            f'{POSSIBLE_RESTRICTION_EMOJIS}.',
            allowed_mentions={'parse': []},
        )
        mark_alert(state, 'b013_unknown_health', unknown_status)
        alerts_sent += 1
    elif (not DRY_RUN) and initialized and not persistent_unknowns:
        # Reset only after recovery so a genuinely new incident alerts at once.
        clear_alert(state, 'b013_unknown_health')
    if (not DRY_RUN) and FORCE_LIVE_ALERT and not link_change_alert_sent:
        # Manual/live alert must be a fresh monitor view, not a state-delta view.
        # Current users and accumulated removals come from this DTR/Meta run;
        # do not show cached removed/added deltas from previous state.
        post_live_alert(config, summary, results, [], failures, unknowns, sheet_sync)
        alerts_sent += 1
    state['_last_run_summary']['alerts_sent'] = alerts_sent
    if not DRY_RUN:
        save_state(state)
    if DRY_RUN:
        print(json.dumps({'summary': summary, 'app_capability': capability, 'failures': failures, 'unknowns': unknowns, 'changes': changes}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
PY
