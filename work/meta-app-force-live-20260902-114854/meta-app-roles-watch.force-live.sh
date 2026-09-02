#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="/var/lock/meta-app-roles-watch-force-live-20260902.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

BASE_DIR="/root/mgs-agent"
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a

python3 - <<'PY'
import importlib.util
import hashlib
import json
import os
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import socket
import re
import time
import unicodedata

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

VAULT = os.environ.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')
APP_ITEMS_ENV = os.environ.get('MGS_META_APP_ROLE_ITEMS', '').strip()
REGISTRY_PATH = Path('/root/mgs-agent/data/meta-app-registry.json')
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
VERIFICATION_IGNORED_IDENTITIES_RAW = tuple(
    str(value).strip()
    for value in ((REGISTRY.get('verification_ignored_profiles') or {}).get('identities') or [])
    if str(value).strip()
)
IDENTITY_BASELINE_PATH = Path('/root/mgs-agent/data/meta-app-role-identity-baseline.json')
IDENTITY_BASELINE = json.loads(IDENTITY_BASELINE_PATH.read_text(encoding='utf-8'))


def is_b013_dtr_app(value):
    """Keep every B013 replacement generation on the dedicated DTR route."""
    return str(value or '').strip().upper().startswith('B013')


ACTIVE_APP_CONFIGS = {
    str(row['app']).strip().upper(): row
    for row in (REGISTRY.get('apps') or [])
    if not is_b013_dtr_app(row.get('app'))
}
APP_ITEM_TO_KEY = {
    str(row['onepassword_item_title']).strip(): app
    for app, row in ACTIVE_APP_CONFIGS.items()
}
WEBHOOK_ITEM = os.environ.get('MGS_APP_RATE_LIMIT_WEBHOOK_ITEM', 'Discord Webhook - app-rate-limit')
SPREADSHEET_ID = os.environ.get('MGS_META_APP_ROLES_SPREADSHEET_ID', '1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY')
SHEET_GID = int(os.environ.get('MGS_META_APP_ROLES_SHEET_GID', '542936436'))
SHEET_REMOVED_COLUMN = os.environ.get('MGS_META_APP_ROLES_REMOVED_COLUMN', 'A')
GOOGLE_AUTH_MODE = os.environ.get('MGS_META_APP_ROLES_GOOGLE_AUTH_MODE', 'service_account').lower()
GOOGLE_QUOTA_PROJECT = ''
SYNC_SHEET_REMOVED = os.environ.get('MGS_META_APP_ROLES_SYNC_SHEET_REMOVED', '1').lower() not in {'0', 'false', 'no'}
STATE_PATH = Path(os.environ.get('MGS_META_APP_ROLES_STATE', '/root/mgs-agent/data/meta-app-role-monitor-state.json'))
ALERT_PAUSE_PATH = Path(os.environ.get(
    'MGS_META_APP_ROLE_ALERT_PAUSE_PATH',
    '/root/mgs-agent/data/meta-app-role-alert-pause.json',
))
OP_RESOLVER_PATH = Path('/root/mgs-agent/scripts/mgs-op-item-resolver.py')
_op_spec = importlib.util.spec_from_file_location('mgs_op_item_resolver', OP_RESOLVER_PATH)
if not _op_spec or not _op_spec.loader:
    raise RuntimeError(f'cannot load 1Password resolver: {OP_RESOLVER_PATH}')
OP_RESOLVER=importlib.util.module_from_spec(_op_spec)
_op_spec.loader.exec_module(OP_RESOLVER)
GOOGLE_AUTH_HELPER_PATH = Path('/root/mgs-agent/scripts/mgs_google_workspace_auth.py')
_google_auth_spec = importlib.util.spec_from_file_location('mgs_google_workspace_auth', GOOGLE_AUTH_HELPER_PATH)
if not _google_auth_spec or not _google_auth_spec.loader:
    raise RuntimeError(f'cannot load Google Service Account helper: {GOOGLE_AUTH_HELPER_PATH}')
GOOGLE_AUTH = importlib.util.module_from_spec(_google_auth_spec)
_google_auth_spec.loader.exec_module(GOOGLE_AUTH)
GRAPH_VERSION = os.environ.get('MGS_META_GRAPH_VERSION', 'v20.0')
BASE = f'https://graph.facebook.com/{GRAPH_VERSION}'
RODOLFO_ID = '344196393512075265'
RESTRICTION_ALERT_ROLE_IDS = (
    '1185978575782936586',  # Super Admin
    '1496256346994249912',  # Gestor de Trafego
    '1496260941787168848',  # Admin
)
RESTRICTION_ALERT_EMOJIS = '🚨🚨🚨🚨🚨'
DRY_RUN = os.environ.get('MGS_META_APP_ROLES_DRY_RUN', '').lower() in {'1', 'true', 'yes'}
FORCE_SNAPSHOT_REQUESTED = os.environ.get('MGS_META_APP_ROLES_FORCE_SNAPSHOT', '').lower() in {'1', 'true', 'yes'}
SNAPSHOT_ALLOW_TOKEN = os.environ.get('MGS_META_APP_ROLES_ALLOW_SNAPSHOT', '')
# Safety guard after Rodolfo's correction: operational resend/cron/manual alert
# must never become a snapshot just because FORCE_SNAPSHOT was left in a shell
# command. Snapshot mode is only allowed when explicitly unlocked with the
# exact token below, making accidental/manual misuse fail closed into live mode.
FORCE_SNAPSHOT = FORCE_SNAPSHOT_REQUESTED and SNAPSHOT_ALLOW_TOKEN == 'EXPLICIT_RODOLFO_SNAPSHOT'
SNAPSHOT_BLOCKED = FORCE_SNAPSHOT_REQUESTED and not FORCE_SNAPSHOT
# Manual/test path requested by Rodolfo: force the same polished app-roles
# Discord alert layout from live Meta + sheet data, without pretending there was
# a cron delta and without enabling snapshot mode.
FORCE_LIVE_ALERT = os.environ.get('MGS_META_APP_ROLES_FORCE_LIVE_ALERT', '').lower() in {'1', 'true', 'yes'}
# Manual operator close-loop: after Rodolfo verifies an app is not restricted,
# force one clean recovery/false-positive notice in the app channel using fresh
# Graph checks, without fabricating a role delta or snapshot.
FORCE_RECOVERY_NOTICE = os.environ.get('MGS_META_APP_ROLES_FORCE_RECOVERY_NOTICE', '').lower() in {'1', 'true', 'yes'}
ALERT_COOLDOWN_MINUTES = int(os.environ.get('MGS_META_APP_ROLES_ALERT_COOLDOWN_MINUTES', '60'))
API_BLOCKED_ALERT_COOLDOWN_MINUTES = int(os.environ.get('MGS_META_APP_ROLES_API_BLOCKED_ALERT_COOLDOWN_MINUTES', '1440'))
# Rodolfo requested deterministic spacing between B001-B010 checks so the
# Graph/1Password calls never start as one burst when the cron fires.
APP_STAGGER_SECONDS = max(0.0, float(os.environ.get('MGS_META_APP_ROLE_STAGGER_SECONDS', '4')))
DISCORD_BOT_ITEM = os.environ.get('MGS_DISCORD_BOT_ITEM', 'Discord Bot - Zeus')
INFRA_ALERT_CHANNEL_ID = os.environ.get('MGS_INFRA_ALERT_CHANNEL_ID', '1498132022634483894')
APP_ALERT_CHANNELS = {app: str(row['channel_id']) for app, row in ACTIVE_APP_CONFIGS.items()}
APP_OWNER_PROFILES = {app: str(row.get('admin') or 'n/a') for app, row in ACTIVE_APP_CONFIGS.items()}
APP_RETIRED_OWNER_PROFILES_BY_APP = {
    'B005-2': {'Wana Hsh'},
    'B006-2': {'Mic Vb', 'Crislaine Carvalho'},
    'B007': {'พรชนิตว์ ฑีฆะวัฒน์'},
}
REPLACEMENT_APP_ITEMS = {}
# Every B013 replacement uses the dedicated DTR/ChatPion route, not Meta /roles. B011 and B012
# are normal role-based apps in the current 13-app registry.
DTR_ONLY_APP_ITEMS = {
    str(row['onepassword_item_title']).strip()
    for row in (REGISTRY.get('apps') or [])
    if is_b013_dtr_app(row.get('app'))
}
ROLE_RECONCILIATION_EXCLUDED_APPS = {
    str(row['app']).strip().upper()
    for row in (REGISTRY.get('apps') or [])
    if is_b013_dtr_app(row.get('app'))
}

# B006 was disabled by Rodolfo after a Meta restriction and replaced by B006-2.
# On 2026-07-30 he explicitly confirmed that the new app contains the same 17
# seguradores as the last healthy B006 baseline. He later changed the owner to
# Crislaine Oliveira, who is already one of those 17 and also has Sheet pages.
# Meta exposes different app-scoped IDs in the replacement app. This baseline is
# valid only while the exact confirmed B006-2 role-ID set remains unchanged.
# If any ID drifts, reconciliation fails closed and the Sheet markers are
# preserved until the new set can be attributed safely.
APP_CONFIRMED_MIGRATION_ROLE_SETS = {
    'B006-2': {
        'predecessor': 'B006',
        'confirmed_by': 'Rodolfo Mattei',
        'confirmed_at': '2026-07-30T14:11:24-04:00',
        'source_message_id': '1532450556965294131',
        'owner_role_id': '2422296368256372',
        'owner_in_segurador_set': True,
        'role_ids': {
            '1042430454842244', '1068745469440349', '1072737581757122',
            '1077864728004347', '122168083070691114', '122182709060896419',
            '122183492348687502', '1543606970634041', '1790515048970966',
            '2180440732745809', '2422296368256372', '2457237834799098',
            '2552104718562986', '27374813002200790', '27454886677517224',
            '2808957192817509', '3203779656499693',
        },
        'segurador_names': (
            'Abah Ngatimin', 'Anre Kameza', 'Crislaine Oliveira',
            'Edleide Gomes', 'Gentil Alves Ribeiro', 'Gia Huy', 'Indah',
            'Isidoro Cristina Barbosa Martins', 'Jayadi Thaha Patonangi',
            'Maria Silva Nobrega', 'Millena Kelly', 'Rori Ginbresil Ginting',
            'Simone Oliveira', 'SobiRin Kemana Mana',
            'Tiago De Oliveira Vianna', 'Valentino Simanjuntak',
            'Viviane Moura',
        ),
    },
}

# The Meta Developers UI can expose a confirmed app role that /{app_id}/roles
# omits for visibility reasons. Apply the UI-only identity only while the exact
# raw API role-ID signature remains unchanged; any drift preserves Sheet markers
# fail-closed instead of trusting a stale exception.
APP_CONFIRMED_UI_ROLE_OVERRIDES = {
    'B005-2': {
        'confirmed_by': 'Rodolfo Mattei',
        'confirmed_at': '2026-08-07T23:24:48-04:00',
        'source_message_id': '1535488162107883631',
        'raw_role_count': 135,
        'raw_role_ids_sha256': 'a4d01b7d39c366f345c32aa498941de4b0db4ec384d4d7b16fec2124089ad971',
        'raw_role_ids_observed_at': '2026-08-07T23:33:45-04:00',
        'ui_only_names': ('Lollo Abu Abu',),
    },
}


def canonical_app_key(item_code):
    # Keep replacement app labels visible in alerts/state (e.g. B005-2), while
    # APP_ALERT_CHANNELS can map them back to the same operational Discord channel.
    return str(item_code or '').strip()

# Severity thresholds are percentages returned by Meta in X-App-Usage.
# 100 means the app is at/over the limit and may stop sending/serving requests.
SEVERITY_ORDER = {'ok': 0, 'attention': 1, 'risk': 2, 'critical': 3}
SEVERITY_LABEL = {
    'ok': 'OK',
    'attention': 'ATENÇÃO',
    'risk': 'RISCO',
    'critical': 'CRÍTICO',
}
SEVERITY_COLOR = {
    'ok': 5763719,
    'attention': 16776960,
    'risk': 16753920,
    'critical': 15158332,
}


def now_dt():
    return datetime.now(ZoneInfo('America/New_York'))


def now_iso():
    return now_dt().isoformat(timespec='seconds')


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def load_active_alert_pause():
    """Load an app-scoped Discord alert pause and ignore it after expiry."""
    if not ALERT_PAUSE_PATH.exists():
        return {'apps': set(), 'until': None}
    try:
        raw = json.loads(ALERT_PAUSE_PATH.read_text(encoding='utf-8'))
        apps = {
            canonical_app_key(app)
            for app in (raw.get('apps') or [])
            if canonical_app_key(app) in APP_ALERT_CHANNELS
        }
        mode = str(raw.get('mode') or '').strip().lower()
        if mode == 'manual':
            return {
                'apps': apps,
                'until': None,
                'expired': False,
                'manual': True,
                'reason': str(raw.get('reason') or '')[:300],
            }
        until = parse_dt(raw.get('until'))
        if not until:
            return {'apps': set(), 'until': None, 'invalid': True}
        if until.tzinfo is None:
            until = until.replace(tzinfo=ZoneInfo('America/New_York'))
        if now_dt() >= until:
            return {'apps': set(), 'until': until.isoformat(), 'expired': True}
        return {'apps': apps, 'until': until.isoformat(), 'expired': False, 'manual': False}
    except Exception as exc:
        return {'apps': set(), 'until': None, 'invalid': True, 'error': str(exc)[:300]}


ACTIVE_ALERT_PAUSE = load_active_alert_pause()
PAUSED_APP_ALERTS = set(ACTIVE_ALERT_PAUSE.get('apps') or set())
SUPPRESSED_ALERT_DELIVERIES = 0


def op(args, timeout=45, attempts=4, base_delay=1):
    """Run 1Password CLI with retry before surfacing a credential-read failure.

    Rodolfo's operational rule: credential checks must not alert from a
    one-off 1Password read miss. Try up to 4 times; only the 4th consecutive
    failure is reportable.
    """
    last_msg = 'op command failed'
    for attempt in range(1, attempts + 1):
        try:
            p = subprocess.run(['op', *args], text=True, capture_output=True, timeout=timeout)
            if p.returncode == 0:
                return p.stdout
            last_msg = (p.stderr or p.stdout or 'op command failed')[:300]
        except subprocess.TimeoutExpired:
            last_msg = f'op command timed out after {timeout}s'
        if attempt < attempts:
            time.sleep(base_delay * attempt)
    raise RuntimeError(last_msg)


def discover_app_items():
    if APP_ITEMS_ENV:
        return [x.strip() for x in APP_ITEMS_ENV.split(',') if x.strip() and x.strip() not in DTR_ONLY_APP_ITEMS]
    # The registry is the current exact 12-app role scope. Do not rediscover
    # retired lookalike tokens from the vault.
    return [ACTIVE_APP_CONFIGS[app]['onepassword_item_title'] for app in ACTIVE_APP_CONFIGS]


def op_field(item, field, required=True, attempts=4):
    """Read a 1Password field with 4-attempt confirmation.

    A single failed/empty credential read is not operational proof that the
    credential is missing. Retry before returning empty or raising, so alerts
    only fire after four consecutive read failures.
    """
    last_msg = ''
    for attempt in range(1, attempts + 1):
        try:
            p = subprocess.run(
                ['op', 'item', 'get', item, '--vault', VAULT, '--field', field, '--reveal'],
                text=True,
                capture_output=True,
                timeout=30,
            )
            if p.returncode == 0:
                value = p.stdout.strip()
                if value:
                    return value
                last_msg = f'1Password field empty: item={item} field={field}'
            else:
                last_msg = (p.stderr or p.stdout or f'1Password field read failed: item={item} field={field}')[:300]
        except subprocess.TimeoutExpired:
            last_msg = f'1Password field read timed out: item={item} field={field}'
        if attempt < attempts:
            time.sleep(attempt)
    if required:
        raise RuntimeError(last_msg or f'1Password field missing: item={item} field={field}')
    return ''


def urlopen_with_retry(req, timeout=25, attempts=3, base_delay=2):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
            last_exc = e
            if attempt >= attempts:
                raise
            time.sleep(base_delay * attempt)
    raise last_exc


def google_access_token():
    """Return a short-lived canonical MGS Sheets token without printing secrets."""
    global GOOGLE_QUOTA_PROJECT
    if GOOGLE_AUTH_MODE != 'service_account':
        raise RuntimeError(f'unsupported Google auth mode after MGS cutover: {GOOGLE_AUTH_MODE}')
    GOOGLE_QUOTA_PROJECT = GOOGLE_AUTH.service_account_project_id()
    return GOOGLE_AUTH.service_account_access_token(GOOGLE_AUTH.SHEETS_SCOPE)


def sheets_request(method, path, token, payload=None):
    data = None
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'MGS-Zeus-Meta-App-Roles-Watch/2.2'}
    if GOOGLE_AUTH_MODE == 'service_account' and GOOGLE_QUOTA_PROJECT:
        headers['x-goog-user-project'] = GOOGLE_QUOTA_PROJECT
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(f'https://sheets.googleapis.com/v4{path}', data=data, headers=headers, method=method)
    try:
        with urlopen_with_retry(req, timeout=25, attempts=3) as r:
            raw = r.read().decode('utf-8', 'replace')
            return r.status, json.loads(raw or '{}')
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            body = json.loads(raw)
        except Exception:
            body = {'raw': raw[:500]}
        return e.code, body


def sheet_title_for_gid(token):
    status, body = sheets_request(
        'GET',
        f'/spreadsheets/{SPREADSHEET_ID}?fields=sheets(properties(sheetId,title))',
        token,
    )
    if status != 200:
        raise RuntimeError(f'Sheets metadata failed status={status} body={str(body)[:300]}')
    for sheet in body.get('sheets') or []:
        props = sheet.get('properties') or {}
        if int(props.get('sheetId', -1)) == SHEET_GID:
            return props.get('title')
    raise RuntimeError(f'Sheet gid not found: {SHEET_GID}')


def quote_sheet_range(title, cell_range):
    safe_title = str(title).replace("'", "''")
    return f"'{safe_title}'!{cell_range}"


SHEET_ROWS = None


def load_sheet_rows():
    """Read the migration tab through the canonical MGS Service Account only."""
    global SHEET_ROWS
    if SHEET_ROWS is not None:
        return SHEET_ROWS
    token = google_access_token()
    title = sheet_title_for_gid(token)
    rng = quote_sheet_range(title, 'A:Z')
    status, body = sheets_request(
        'GET',
        f'/spreadsheets/{SPREADSHEET_ID}/values/{urllib.parse.quote(rng, safe="")}?majorDimension=ROWS',
        token,
    )
    if status != 200:
        raise RuntimeError(f'Sheets values read failed status={status} body={str(body)[:300]}')
    values = body.get('values') or []
    if not values:
        raise RuntimeError(f'Sheets values read returned no rows for gid={SHEET_GID}')
    headers = [str(x) for x in values[0]]
    removed_header = 'Removidos acumulado' if 'Removidos acumulado' in headers else ('zzzaa' if 'zzzaa' in headers else '')
    required_headers = {'User', 'Segurador', 'USUARIO', 'NO APP'}
    missing_headers = sorted(required_headers - set(headers))
    if missing_headers:
        raise RuntimeError(f'Sheets required headers missing: {missing_headers}')
    rows = []
    for values_row in values[1:]:
        padded = list(values_row) + [''] * max(0, len(headers) - len(values_row))
        row = dict(zip(headers, padded[:len(headers)]))
        row['Removidos acumulado'] = row.get(removed_header, '') if removed_header else ''
        rows.append(row)
    SHEET_ROWS = rows
    return SHEET_ROWS


def graph_get(path, params, token):
    q = urllib.parse.urlencode({**params, 'access_token': token})
    req = urllib.request.Request(f'{BASE}{path}?{q}', headers={'User-Agent': 'MGS-Zeus-Meta-App-Roles-Watch/2.0'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            headers = {k.lower(): v for k, v in r.headers.items()}
            raw = r.read().decode('utf-8', 'replace')
            return r.status, headers, json.loads(raw or '{}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            data = json.loads(body)
        except Exception:
            data = {'raw': body[:500]}
        return e.code, {k.lower(): v for k, v in e.headers.items()}, data


def graph_get_all_pages(path, params, token):
    """Read every Graph page until paging.next is absent, with no total-role cap."""
    status, headers, body = graph_get(path, params, token)
    if status != 200 or 'error' in body:
        return status, headers, body

    merged_headers = dict(headers)
    all_rows = list(body.get('data') or [])
    page_count = 1
    seen_next_urls = set()
    next_url = ((body.get('paging') or {}).get('next') or '').strip()

    while next_url:
        if next_url in seen_next_urls:
            raise RuntimeError('Graph roles pagination loop detected')
        seen_next_urls.add(next_url)
        req = urllib.request.Request(
            next_url,
            headers={'User-Agent': 'MGS-Zeus-Meta-App-Roles-Watch/2.0'},
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                page_status = response.status
                page_headers = {k.lower(): v for k, v in response.headers.items()}
                raw = response.read().decode('utf-8', 'replace')
                page_body = json.loads(raw or '{}')
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8', 'replace')
            try:
                page_body = json.loads(raw)
            except Exception:
                page_body = {'raw': raw[:500]}
            page_status = exc.code
            page_headers = {k.lower(): v for k, v in exc.headers.items()}

        merged_headers.update(page_headers)
        if page_status != 200 or 'error' in page_body:
            return page_status, merged_headers, page_body
        all_rows.extend(page_body.get('data') or [])
        page_count += 1
        next_url = ((page_body.get('paging') or {}).get('next') or '').strip()

    return 200, merged_headers, {'data': all_rows, '_page_count': page_count}


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {'_corrupt_backup_at': now_iso(), 'apps': {}}
    return {'apps': {}, '_created_at': now_iso()}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(STATE_PATH)


def post_request_with_rate_limit_retry(req, max_attempts=5):
    """POST to Discord, honoring HTTP 429 retry_after before failing closed."""
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
            retry_after = (
                body.get('retry_after')
                or exc.headers.get('X-RateLimit-Reset-After')
                or exc.headers.get('Retry-After')
                or 1.0
            )
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = 1.0
            time.sleep(min(max(delay, 0.25), 15.0) + 0.15)


def post_webhook(content, embed=None, app_name=None, allowed_mentions=None):
    global SUPPRESSED_ALERT_DELIVERIES
    channel_id = APP_ALERT_CHANNELS.get(app_name or '')
    if canonical_app_key(app_name) in PAUSED_APP_ALERTS:
        SUPPRESSED_ALERT_DELIVERIES += 1
        return 204
    if allowed_mentions is None:
        allowed_mentions = {'users': [RODOLFO_ID]}
    if DRY_RUN:
        print(json.dumps({'dry_run_alert': content, 'app': app_name, 'channel_id': channel_id, 'embed_title': (embed or {}).get('title'), 'fields': (embed or {}).get('fields', []), 'allowed_mentions': allowed_mentions}, ensure_ascii=False))
        return 0
    payload = {'content': content, 'allowed_mentions': allowed_mentions}
    if embed:
        payload['embeds'] = [embed]
    if channel_id:
        bot_token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
        if not bot_token:
            raise RuntimeError('local Zeus Discord bot token unavailable')
        req = urllib.request.Request(
            f'https://discord.com/api/v10/channels/{channel_id}/messages',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f'Bot {bot_token}', 'User-Agent': 'MGS-Zeus-Meta-App-Roles-Watch/2.1'},
            method='POST',
        )
        return post_request_with_rate_limit_retry(req)
    url = op_field(WEBHOOK_ITEM, 'webhook_url', required=False) or op_field(WEBHOOK_ITEM, 'credential')
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus-Meta-App-Roles-Watch/2.1'},
        method='POST',
    )
    return post_request_with_rate_limit_retry(req)


def post_infra_alert(content, embed=None):
    if DRY_RUN:
        print(json.dumps({'dry_run_infra_alert': content, 'embed_title': (embed or {}).get('title'), 'fields': (embed or {}).get('fields', [])}, ensure_ascii=False))
        return 0
    bot_token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
    if not bot_token:
        raise RuntimeError('local Zeus Discord bot token unavailable')
    payload = {'content': content, 'allowed_mentions': {'users': [RODOLFO_ID]}}
    if embed:
        payload['embeds'] = [embed]
    req = urllib.request.Request(
        f'https://discord.com/api/v10/channels/{INFRA_ALERT_CHANNEL_ID}/messages',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bot {bot_token}', 'User-Agent': 'MGS-Zeus-Meta-App-Roles-Watch/2.3'},
        method='POST',
    )
    with urlopen_with_retry(req, timeout=20, attempts=3) as r:
        return r.status


def usage_from_headers(headers):
    raw = headers.get('x-app-usage') or headers.get('x-business-use-case-usage') or ''
    data = {}
    max_pct = 0
    metric = None
    if raw:
        try:
            data = json.loads(raw)
            # X-App-Usage: {"call_count":4,"total_cputime":0,"total_time":0}
            if isinstance(data, dict):
                for k, v in data.items():
                    try:
                        if isinstance(v, dict):
                            for kk, vv in v.items():
                                pct = int(float(vv))
                                if pct > max_pct:
                                    max_pct, metric = pct, f'{k}.{kk}'
                        else:
                            pct = int(float(v))
                            if pct > max_pct:
                                max_pct, metric = pct, k
                    except Exception:
                        continue
        except Exception:
            data = {'raw': raw[:300]}
    if max_pct >= 95:
        severity = 'critical'
    elif max_pct >= 85:
        severity = 'risk'
    elif max_pct >= 70:
        severity = 'attention'
    else:
        severity = 'ok'
    return {'raw': raw, 'parsed': data, 'max_pct': max_pct, 'max_metric': metric, 'severity': severity}


def fmt_usage(usage):
    metric = usage.get('max_metric') or 'n/a'
    return f"{usage.get('max_pct', 0)}% ({metric})"


def should_alert_cooldown(prev, key, severity, cooldown_minutes=None):
    if canonical_app_key(prev.get('app_name')) in PAUSED_APP_ALERTS:
        return False
    if cooldown_minutes is None:
        cooldown_minutes = ALERT_COOLDOWN_MINUTES
    last = ((prev.get('alerts') or {}).get(key) or {}).get(severity)
    last_dt = parse_dt(last)
    if not last_dt:
        return True
    return now_dt() - last_dt >= timedelta(minutes=cooldown_minutes)


def mark_alert(prev, key, severity):
    if canonical_app_key(prev.get('app_name')) in PAUSED_APP_ALERTS:
        return
    prev.setdefault('alerts', {}).setdefault(key, {})[severity] = now_iso()


def alert_timestamp(prev, key, severity):
    return ((prev.get('alerts') or {}).get(key) or {}).get(severity)


def check_is_transient_meta_api(name, chk):
    """True for isolated Meta/Facebook HTTP turbulence, not app disconnect.

    Example observed by Rodolfo: /me returned HTTP 503 with an HTML
    "Facebook | Error" body while app_metadata/roles/debug_token were OK.
    That should be an operational warning and must auto-close on recovery.
    """
    try:
        status = int(chk.get('status') or 0)
    except Exception:
        status = 0
    return name == 'user_token_me' and status in {500, 502, 503, 504}


def uses_shared_admin_model(app_name):
    """B001-B012 have no unique operational app-admin profile.

    Rodolfo confirmed that every segurador in these apps is an administrator.
    The profile behind the monitor token is therefore credential metadata, not
    an app-health owner whose /me status or name belongs in manager alerts.
    """
    match = re.match(r'^B(\d{3})(?:-|$)', str(app_name or '').strip().upper())
    return bool(match and 1 <= int(match.group(1)) <= 12)


def health_check_is_ignored(app_name, check_name):
    if check_name == 'debug_token':
        return True
    return check_name == 'user_token_me' and uses_shared_admin_model(app_name)


def admin_alert_fields(app_name, label='Perfil admin do app'):
    if uses_shared_admin_model(app_name):
        return []
    return [{
        'name': label,
        'value': APP_OWNER_PROFILES.get(app_name, 'n/a'),
        'inline': True,
    }]


def monitored_check_summary(snap):
    app_name = snap.get('app_name')
    names = [
        name for name in (snap.get('checks') or {})
        if not health_check_is_ignored(app_name, name)
    ]
    return ' • '.join(f'{name} OK' for name in names) or 'checks operacionais OK'


def monitored_checks_ok(snap):
    app_name = snap.get('app_name')
    for name, chk in (snap.get('checks') or {}).items():
        if health_check_is_ignored(app_name, name):
            continue
        if not chk.get('ok'):
            return False
    return True


def unresolved_check_alert(prev):
    # Recovery notices must close a concrete health incident observed by this
    # script, not any historical alert timestamp in state. Old `checks.critical`
    # alerts from before this close-loop feature exist in state for several apps;
    # using them here caused green recovery notices to be sent on every healthy
    # cron even though no new red/attention alert had just happened.
    incident = parse_dt(prev.get('last_check_incident_at'))
    if not incident:
        return False
    recovered = parse_dt(prev.get('last_check_recovered_at'))
    return not recovered or recovered < incident


def extract_error(data):
    err = data.get('error', data if isinstance(data, dict) else {'raw': str(data)[:300]})
    return {
        'code': err.get('code'),
        'type': err.get('type'),
        'message': str(err.get('message', err))[:500],
    }


def is_api_access_blocked_error(exc):
    return 'API access blocked' in str(exc)


def is_application_deleted_error(exc):
    """Meta Graph symptom for an app moved to Developers > Restritos."""
    return 'application has been deleted' in str(exc).casefold()


def restriction_alert_content():
    role_mentions = ' '.join(f'<@&{role_id}>' for role_id in RESTRICTION_ALERT_ROLE_IDS)
    return f'{RESTRICTION_ALERT_EMOJIS}\n{role_mentions}'


def restriction_alert_allowed_mentions():
    return {'parse': [], 'roles': list(RESTRICTION_ALERT_ROLE_IDS)}


def restriction_alert_embed(app_name, consecutive_errors):
    return {
        'title': f'{app_name} - APP ENTROU EM RESTRIÇÃO',
        'description': (
            f'A Meta colocou o app **{app_name}** na categoria **Restritos**.\n\n'
            'Ele continua aparecendo no painel Developers, mas **não consegue mais operar normalmente**.'
        ),
        'color': SEVERITY_COLOR['critical'],
        'fields': [
            {
                'name': 'O que pode acontecer',
                'value': 'As páginas ligadas a esse app podem parar de enviar mensagens ou perder a integração com o sistema.',
                'inline': False,
            },
            {
                'name': 'O que fazer agora',
                'value': (
                    '1. Não iniciar novos disparos por esse app.\n'
                    '2. Confirmar o app em **Meta Developers > Restritos**.\n'
                    '3. Preparar o app substituto e migrar as páginas afetadas.'
                ),
                'inline': False,
            },
            {
                'name': 'Confirmação do monitor',
                'value': (
                    f'Problema detectado em **{consecutive_errors} verificações consecutivas**.\n'
                    'Resposta da Meta: **Application has been deleted**.'
                ),
                'inline': False,
            },
        ],
    }


def display_role(role):
    role = str(role or '').strip()
    if role == 'administrators':
        return 'Admin'
    return role or 'Admin'


SHEET_USERS = None
SHEET_APP_BY_NAME = None
SHEET_APP_BY_PROFILE_ID = None
SHEET_OLD_PROFILE_NAMES_BY_APP = None
SHEET_PROFILE_ERROR = None


def norm_name(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(value or '')).strip()).casefold()


VERIFICATION_IGNORED_IDENTITIES = {
    norm_name(value) for value in VERIFICATION_IGNORED_IDENTITIES_RAW
}


def is_verification_ignored_identity(*values):
    return any(
        norm_name(value) in VERIFICATION_IGNORED_IDENTITIES
        for value in values
        if str(value or '').strip()
    )


def is_verification_ignored_role(role):
    return is_verification_ignored_identity(role.get('name'), role.get('id'))


def is_verification_ignored_sheet_row(row):
    return is_verification_ignored_identity(
        row.get('Segurador'),
        row.get('User'),
        row.get('USUARIO'),
    )


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


def load_sheet_users():
    global SHEET_USERS, SHEET_APP_BY_NAME, SHEET_APP_BY_PROFILE_ID, SHEET_OLD_PROFILE_NAMES_BY_APP, SHEET_PROFILE_ERROR
    if SHEET_USERS is not None:
        return SHEET_USERS
    SHEET_USERS = {}
    SHEET_APP_BY_NAME = {}
    SHEET_APP_BY_PROFILE_ID = {}
    SHEET_OLD_PROFILE_NAMES_BY_APP = {}
    try:
        for row in load_sheet_rows():
            name = row.get('Segurador') or ''
            profile_id = row.get('USUARIO') or ''  # Column K in tab Migracao 22/06.
            bot_email = row.get('User') or ''      # Column A: bot user email.
            app_key = app_key_from_sheet_value(row.get('NO APP'))
            if name.strip():
                name_norm = norm_name(name)
                SHEET_USERS[name_norm] = {
                    'profile_id': profile_id.strip(),
                    'bot_email': bot_email.strip(),
                    'pages': (row.get('PG') or '').strip(),
                    'app_key': app_key,
                }
                if app_key:
                    SHEET_APP_BY_NAME[name_norm] = app_key
            if profile_id.strip() and app_key:
                SHEET_APP_BY_PROFILE_ID[profile_id.strip().casefold()] = app_key
            obs = row.get('OBS') or ''
            m = re.search(r'perfil\s+antigo\s*:\s*([^;\n\r]+)', obs, flags=re.I)
            if app_key and m:
                old_name = norm_name(m.group(1))
                if old_name:
                    SHEET_OLD_PROFILE_NAMES_BY_APP.setdefault(app_key, set()).add(old_name)
        SHEET_PROFILE_ERROR = None
    except Exception as e:
        SHEET_PROFILE_ERROR = str(e)[:300]
    return SHEET_USERS


def sheet_user(name, app_key=None):
    row = load_sheet_users().get(norm_name(name)) or {}
    is_owner = norm_name(name) in {norm_name(x) for x in APP_OWNER_PROFILES.values()}
    # Different Facebook profiles can share the same display name. Do not render
    # a Sheet row assigned to another app as if it belonged to this app's owner.
    current_owner = norm_name(name) == norm_name(APP_OWNER_PROFILES.get(app_key))
    if current_owner and row.get('app_key') and row.get('app_key') != app_key:
        row = {}
    return {
        'profile_id': row.get('profile_id') or ('owner do app' if is_owner else 'sem ID'),
        'bot_email': row.get('bot_email') or 'sem email',
        'pages': row.get('pages') or '-',
        'app_key': row.get('app_key'),
    }


def is_owner_housekeeping_removal(role, app_key):
    """True for expected owner-profile housekeeping, not a segurador incident."""
    name_norm = norm_name(role.get('name'))
    if not name_norm:
        return False
    retired_for_app = {norm_name(x) for x in APP_RETIRED_OWNER_PROFILES_BY_APP.get(app_key, set())}
    if name_norm in retired_for_app:
        return True
    for owner_app, owner_name in APP_OWNER_PROFILES.items():
        if owner_app != app_key and name_norm == norm_name(owner_name):
            return True
    return False


def sheet_removed_roles_for_app(app_key):
    """Rows currently marked X in the migration sheet for the app.

    Manual/live alerts must reflect the same operational truth the cron uses for
    Column A / Removidos acumulado, not only state.cumulative_removed from role
    deltas observed after the monitor was initialized.
    """
    removed = []
    try:
        for row in load_sheet_rows():
            if is_verification_ignored_sheet_row(row):
                continue
            if app_key_from_sheet_value(row.get('NO APP')) != app_key:
                continue
            if str(row.get('Removidos acumulado') or '').strip().upper() != 'X':
                continue
            name = (row.get('Segurador') or '').strip()
            profile_id = (row.get('USUARIO') or '').strip()
            if not (name or profile_id):
                continue
            removed.append({
                'id': profile_id,
                'name': name or profile_id,
                'role': 'administrators',
            })
    except Exception:
        return []
    return removed


def role_still_assigned_to_app(role, app_key):
    """False when sheet moved this segurador/profile to another app.

    Cumulative removals are only active incidents while the sheet still says the
    user belongs to this app. If Ially/Rodolfo moved the row to B011/Bxxx, the
    old app must stop showing it as Removidos acumulados.
    """
    if is_verification_ignored_role(role):
        return False
    load_sheet_users()
    name_app = (SHEET_APP_BY_NAME or {}).get(norm_name(role.get('name')))
    profile_id = (sheet_user(role.get('name')).get('profile_id') or '').strip()
    profile_app = None
    if profile_id and profile_id not in {'sem ID', 'owner do app'}:
        profile_app = (SHEET_APP_BY_PROFILE_ID or {}).get(profile_id.casefold())
    assigned_app = profile_app or name_app
    return not assigned_app or assigned_app == app_key


def sync_sheet_removed_accumulated(state, successful_app_keys=None):
    """Reconcile sheet intent with current Meta roles and mirror missing users to column A.

    The sheet is the operational intent: each row with APP PROVISORIO says which Meta app
    should contain that segurador/profile. The previous implementation only
    mirrored cumulative_removed deltas observed after this monitor started, so
    users that were already absent before state creation never got an X. This
    function is intentionally a full reconciler every run:
      - row has APP PROVISORIO + Segurador/USUARIO and profile is absent from current Meta roles => X
      - row is present in current Meta roles => blank
      - row cannot be tied to a monitored app => preserve/blank safely and report counts
    """
    if not SYNC_SHEET_REMOVED:
        return {'enabled': False, 'updated': False}

    rows = load_sheet_rows()

    def app_key_from_row(row):
        return app_key_from_sheet_value(row.get('NO APP'))

    successful_app_keys = set(successful_app_keys or [])
    current_by_app = {}
    removed_by_app = {}
    for app_key, app_state in (state.get('apps') or {}).items():
        if app_key not in successful_app_keys:
            continue
        reconciliation = app_state.get('role_identity_reconciliation') or {}
        roles = app_state.get('operational_roles') or app_state.get('roles') or []
        removed = app_state.get('cumulative_removed') or []
        pending_expected_only = (
            reconciliation.get('status') == 'pending_expected_role_acceptance'
            and int(reconciliation.get('unresolved_meta_names_count') or 0) == 0
            and len(roles) == int(reconciliation.get('raw_role_count') or len(roles))
        )
        current_by_app[app_key] = {
            'ids': {str(r.get('id') or '').strip() for r in roles if str(r.get('id') or '').strip()},
            'names': {norm_name(r.get('name')) for r in roles if norm_name(r.get('name'))},
            # A count below expected_sheet_roles is a real present/absent snapshot
            # when every returned identity resolved. Preserve fail-closed only for
            # genuine identity ambiguity, partial lookup or baseline drift.
            'identity_blocked': (
                reconciliation.get('safe_for_sheet') is False
                and not pending_expected_only
            ),
        }
        removed_by_app[app_key] = {
            'ids': {str(r.get('id') or '').strip() for r in removed if str(r.get('id') or '').strip()},
            'names': {norm_name(r.get('name')) for r in removed if norm_name(r.get('name'))},
            'roles': removed,
        }

    sheet_ids_by_app = {}
    sheet_names_by_app = {}
    desired_values = []
    existing_values = []
    marked_missing = 0
    marked_cumulative = 0
    present_count = 0
    unknown_app_rows = 0
    identity_blocked_rows = 0
    blank_intent_rows = 0
    ignored_verification_rows = 0
    checked_intent_rows = 0

    for row in rows:
        existing_values.append((row.get('Removidos acumulado') or '').strip())
        if is_verification_ignored_sheet_row(row):
            desired_values.append([''])
            ignored_verification_rows += 1
            continue
        app_key = app_key_from_row(row)
        seg_norm = norm_name(row.get('Segurador'))
        profile_id = str(row.get('USUARIO') or '').strip()
        has_intent = bool(app_key and (seg_norm or profile_id))
        if not has_intent:
            desired_values.append([''])
            blank_intent_rows += 1
            continue

        if app_key in ROLE_RECONCILIATION_EXCLUDED_APPS:
            # The active B013 generation uses the dedicated DTR/page-token monitor, not app roles.
            # Do not clear or write X here; that dedicated route owns reconciliation.
            desired_values.append(['X' if (row.get('Removidos acumulado') or '').strip().upper() == 'X' else ''])
            continue

        sheet_ids_by_app.setdefault(app_key, set())
        sheet_names_by_app.setdefault(app_key, set())
        if profile_id:
            sheet_ids_by_app[app_key].add(profile_id)
        if seg_norm:
            sheet_names_by_app[app_key].add(seg_norm)

        current = current_by_app.get(app_key)
        if not current:
            # Do not invent removals for an app that was not checked successfully.
            # Keep the previous marker and surface the count in state/reporting.
            desired_values.append(['X' if (row.get('Removidos acumulado') or '').strip().upper() == 'X' else ''])
            unknown_app_rows += 1
            continue

        present = bool((profile_id and profile_id in current['ids']) or (seg_norm and seg_norm in current['names']))
        if present:
            # Positive identity evidence is safe even while the app is below its
            # expected-role gate. A recovered segurador must have a stale X cleared;
            # fail-closed applies only to absent/unattributed rows.
            desired_values.append([''])
            present_count += 1
            checked_intent_rows += 1
            continue

        if current.get('identity_blocked'):
            # The role set is incomplete or unattributed. Preserve the existing
            # marker for absent rows instead of inventing removals, but never let
            # this gate retain X for identities proven present above.
            desired_values.append(['X' if (row.get('Removidos acumulado') or '').strip().upper() == 'X' else ''])
            identity_blocked_rows += 1
            continue

        checked_intent_rows += 1
        cumulative = removed_by_app.get(app_key, {'ids': set(), 'names': set()})
        previously_removed = bool((profile_id and profile_id in cumulative['ids']) or (seg_norm and seg_norm in cumulative['names']))

        if previously_removed:
            desired_values.append(['X'])
            marked_cumulative += 1
        else:
            desired_values.append(['X'])
            marked_missing += 1

    # Roles removed from Meta that no longer have a corresponding row in the sheet.
    unmatched_removed = 0
    for app_key, removed in removed_by_app.items():
        sheet_ids = sheet_ids_by_app.get(app_key, set())
        sheet_names = sheet_names_by_app.get(app_key, set())
        for role in removed.get('roles') or []:
            profile_id = str(role.get('id') or '').strip()
            name = norm_name(role.get('name'))
            if not ((profile_id and profile_id in sheet_ids) or (name and name in sheet_names)):
                unmatched_removed += 1

    desired_flat = [v[0] for v in desired_values]
    result_base = {
        'enabled': True,
        'rows': len(rows),
        'checked_intent_rows': checked_intent_rows,
        'present': present_count,
        'marked': sum(1 for v in desired_flat if v == 'X'),
        'marked_missing_current_meta': marked_missing,
        'marked_cumulative_removed': marked_cumulative,
        'unknown_app_rows': unknown_app_rows,
        'identity_blocked_rows': identity_blocked_rows,
        'blank_intent_rows': blank_intent_rows,
        'ignored_verification_rows': ignored_verification_rows,
        'unmatched_removed': unmatched_removed,
        'checked_at': now_iso(),
    }
    if existing_values == desired_flat:
        return {**result_base, 'updated': False}

    if DRY_RUN:
        return {
            **result_base,
            'updated': False,
            'would_update': True,
            'updates_needed': sum(1 for before, after in zip(existing_values, desired_flat) if before != after),
        }

    token = google_access_token()
    title = sheet_title_for_gid(token)
    last_row = len(rows) + 1
    rng = quote_sheet_range(title, f'{SHEET_REMOVED_COLUMN}2:{SHEET_REMOVED_COLUMN}{last_row}')
    status, body = sheets_request(
        'PUT',
        f'/spreadsheets/{SPREADSHEET_ID}/values/{urllib.parse.quote(rng, safe="")}?valueInputOption=RAW',
        token,
        {'range': rng, 'majorDimension': 'ROWS', 'values': desired_values},
    )
    if status not in {200, 201}:
        raise RuntimeError(f'Sheets update failed status={status} body={str(body)[:300]}')
    # Keep the in-run Service Account cache coherent so the alert immediately
    # reflects the values just written instead of reading stale public-export data.
    for row, desired in zip(rows, desired_flat):
        row['Removidos acumulado'] = desired
    return {**result_base, 'updated': True, 'updated_range': body.get('updatedRange')}


def fit_cell(value, width):
    text = str(value or '')
    if len(text) <= width:
        return text.ljust(width)
    return (text[:max(1, width - 1)] + '…').ljust(width)


def display_bot_email(value):
    text = str(value or '').strip()
    if not text or text == 'sem email':
        return 'sem email'
    return text.split('@', 1)[0]


def sorted_roles_for_display(roles, app_key=None):
    def key(r):
        user = sheet_user(r.get('name'), app_key=app_key)
        return (user['bot_email'].casefold(), str(r.get('name') or '').casefold(), user['profile_id'].casefold())
    return sorted(roles or [], key=key)


def fmt_roles(roles, app_key=None):
    if not roles:
        return 'Nenhum usuário retornado.'
    roles_sorted = sorted_roles_for_display(roles, app_key=app_key)
    lines = [
        f"{fit_cell('BOT EMAIL', 24)} | {fit_cell('SEGURADOR', 24)} | {fit_cell('PERFIL ID', 18)} | PÁGINAS",
        '',
    ]
    for r in roles_sorted:
        user = sheet_user(r.get('name'), app_key=app_key)
        profile_display = user['profile_id']
        if profile_display == 'sem ID' and r.get('id'):
            profile_display = str(r.get('id'))
        lines.append(
            f"{fit_cell(display_bot_email(user['bot_email']), 24)} | "
            f"{fit_cell(r.get('name'), 24)} | "
            f"{fit_cell(profile_display, 18)} | "
            f"{user['pages']}"
        )
    return '\n'.join(lines)


def fmt_delta_roles(roles, app_key=None):
    if not roles:
        return 'Nenhum.'
    return fmt_roles(roles, app_key=app_key)


def clip_field(value, limit=1000):
    text = str(value or '')
    if len(text) <= limit:
        return text
    return text[:limit - 24].rstrip() + f"\n… +{len(text) - (limit - 24)} chars"


def code_block(text):
    text = str(text or '').rstrip()
    # Discord message limit is 2000 chars. Keep a hard cap with room for fences.
    if len(text) > 1988:
        text = text[:1960].rstrip() + '\n... conteúdo truncado'
    return '```\n' + text + '\n```'


def code_blocks(text):
    """Return one or more Discord-safe code blocks without hiding rows.

    App-role lists can exceed one Discord message, especially when Rodolfo asks
    for all users in every B001–B010/B011 channel. Split by line instead of
    hiding rows or truncating the table.
    """
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


def post_code_blocks(text, app_name=None):
    for block in code_blocks(text):
        post_webhook(block, app_name=app_name)


SECTION_LINE = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'


def section_block(title, body):
    return '\n'.join([
        SECTION_LINE,
        title,
        SECTION_LINE,
        str(body or '').rstrip(),
    ])


def role_key(r):
    return str(r.get('id') or '')


def operational_roles_for_app(app_key, roles):
    """Return display/sheet identities while preserving raw Graph roles in state.

    A confirmed migration set is applied only when the exact app-scoped role-ID
    set still matches Rodolfo's confirmation. Any drift fails closed: raw roles
    remain visible and the sheet synchronizer preserves its existing markers.
    """
    raw_roles = [dict(r) for r in (roles or [])]
    # Legacy migration/UI overrides apply only to the exact historical app key.
    # Replacement suffixes (for example B005-3 and current B006-2 after a new
    # registry cutover) must use fresh Graph names unless re-confirmed for that
    # exact app/token generation.
    ui_cfg = APP_CONFIRMED_UI_ROLE_OVERRIDES.get(app_key) if app_key not in ACTIVE_APP_CONFIGS or app_key == 'B007' else None
    if ui_cfg:
        operational = [dict(r) for r in raw_roles]
        current_names = {norm_name(r.get('name')) for r in operational if norm_name(r.get('name'))}
        missing_ui_names = [
            name for name in (ui_cfg.get('ui_only_names') or ())
            if norm_name(name) not in current_names
        ]
        if not missing_ui_names:
            operational.sort(key=lambda r: (r.get('name', '').lower(), role_key(r)))
            return operational, {
                'mode': 'graph_names_with_confirmed_ui_override',
                'status': 'native_api_visibility_restored',
                'safe_for_sheet': True,
                'raw_role_count': len(raw_roles),
                'operational_role_count': len(operational),
                'ui_only_names_applied': [],
                'confirmed_by': ui_cfg.get('confirmed_by'),
                'confirmed_at': ui_cfg.get('confirmed_at'),
                'source_message_id': ui_cfg.get('source_message_id'),
            }

        actual_ids = sorted(role_key(r) for r in raw_roles if role_key(r))
        actual_signature = hashlib.sha256(('\n'.join(actual_ids) + '\n').encode('utf-8')).hexdigest()
        expected_count = int(ui_cfg.get('raw_role_count') or 0)
        expected_signature = str(ui_cfg.get('raw_role_ids_sha256') or '')
        if len(actual_ids) != expected_count or actual_signature != expected_signature:
            return raw_roles, {
                'mode': 'graph_names_with_confirmed_ui_override',
                'status': 'blocked_role_id_drift',
                'safe_for_sheet': False,
                'raw_role_count': len(raw_roles),
                'expected_raw_role_count': expected_count,
                'source_message_id': ui_cfg.get('source_message_id'),
            }

        applied_names = []
        for name in missing_ui_names:
            operational.append({
                'id': f'confirmed-ui:{app_key}:{norm_name(name)}',
                'name': name,
                'role': 'administrators',
                'identity_source': 'rodolfo_confirmed_meta_ui',
            })
            applied_names.append(name)
        operational.sort(key=lambda r: (r.get('name', '').lower(), role_key(r)))
        return operational, {
            'mode': 'graph_names_with_confirmed_ui_override',
            'status': 'applied',
            'safe_for_sheet': True,
            'raw_role_count': len(raw_roles),
            'operational_role_count': len(operational),
            'ui_only_names_applied': applied_names,
            'confirmed_by': ui_cfg.get('confirmed_by'),
            'confirmed_at': ui_cfg.get('confirmed_at'),
            'source_message_id': ui_cfg.get('source_message_id'),
        }

    cfg = APP_CONFIRMED_MIGRATION_ROLE_SETS.get(app_key) if app_key not in ACTIVE_APP_CONFIGS else None
    if not cfg:
        unresolved = [
            r for r in raw_roles
            if role_key(r) and norm_name(r.get('name')) == norm_name(role_key(r))
        ]
        # App-scoped IDs change when users move to a replacement app. If Meta
        # returns only numeric IDs and no resolvable names, those IDs cannot be
        # matched safely to Sheet USUARIO/Segurador identities. Preserve current
        # X markers instead of inventing a mass removal until an exact migration
        # set is confirmed.
        if raw_roles and len(unresolved) == len(raw_roles):
            return raw_roles, {
                'mode': 'graph_names',
                'status': 'blocked_unresolved_names',
                'safe_for_sheet': False,
                'raw_role_count': len(raw_roles),
                'unresolved_meta_names_count': len(unresolved),
            }
        return raw_roles, {
            'mode': 'graph_names',
            'status': 'not_configured',
            'safe_for_sheet': True,
            'raw_role_count': len(raw_roles),
            'unresolved_meta_names_count': len(unresolved),
        }

    actual_ids = {role_key(r) for r in raw_roles if role_key(r)}
    expected_ids = set(cfg.get('role_ids') or set())
    unresolved = [r for r in raw_roles if role_key(r) and norm_name(r.get('name')) == norm_name(role_key(r))]
    if actual_ids != expected_ids:
        return raw_roles, {
            'mode': 'confirmed_migration_set',
            'status': 'blocked_role_id_drift',
            'safe_for_sheet': False,
            'raw_role_count': len(raw_roles),
            'confirmed_role_count': len(expected_ids),
            'missing_role_ids_count': len(expected_ids - actual_ids),
            'unexpected_role_ids_count': len(actual_ids - expected_ids),
            'unresolved_meta_names_count': len(unresolved),
            'source_message_id': cfg.get('source_message_id'),
        }

    owner_name = APP_OWNER_PROFILES.get(app_key, '')
    owner_role_id = str(cfg.get('owner_role_id') or '').strip()
    owner_roles = [
        r for r in raw_roles
        if (owner_role_id and role_key(r) == owner_role_id)
        or (not owner_role_id and norm_name(r.get('name')) == norm_name(owner_name))
    ]
    if len(owner_roles) != 1:
        return raw_roles, {
            'mode': 'confirmed_migration_set',
            'status': 'blocked_owner_identity',
            'safe_for_sheet': False,
            'raw_role_count': len(raw_roles),
            'owner_matches': len(owner_roles),
            'unresolved_meta_names_count': len(unresolved),
            'source_message_id': cfg.get('source_message_id'),
        }

    owner_in_segurador_set = bool(cfg.get('owner_in_segurador_set'))
    operational = []
    for name in cfg.get('segurador_names') or ():
        is_owner = owner_in_segurador_set and norm_name(name) == norm_name(owner_name)
        operational.append({
            'id': owner_role_id if is_owner else f'confirmed-migration:{app_key}:{norm_name(name)}',
            'name': name,
            'role': 'administrators',
            'identity_source': (
                'rodolfo_confirmed_owner_role_id'
                if is_owner else 'rodolfo_confirmed_predecessor_set'
            ),
        })
    if not owner_in_segurador_set:
        operational.append({
            **owner_roles[0],
            'name': owner_name,
            'identity_source': 'rodolfo_confirmed_owner_role_id',
        })
    return operational, {
        'mode': 'confirmed_migration_set',
        'status': 'applied',
        'safe_for_sheet': True,
        'predecessor': cfg.get('predecessor'),
        'confirmed_by': cfg.get('confirmed_by'),
        'confirmed_at': cfg.get('confirmed_at'),
        'source_message_id': cfg.get('source_message_id'),
        'raw_role_count': len(raw_roles),
        'operational_role_count': len(operational),
        'confirmed_segurador_count': len(cfg.get('segurador_names') or ()),
        'unresolved_meta_names_count': len(unresolved),
    }


def role_identity_keys(r):
    keys = set()
    rid = role_key(r)
    if rid:
        keys.add(f'id:{rid}')
    name_norm = norm_name(r.get('name'))
    if name_norm:
        keys.add(f'name:{name_norm}')
    profile_id = (sheet_user(r.get('name')).get('profile_id') or '').strip()
    if profile_id and profile_id not in {'sem ID', 'owner do app'}:
        keys.add(f'profile:{profile_id.casefold()}')
    return keys


def role_matches_any(r, identity_keys):
    return bool(role_identity_keys(r) & identity_keys)


def merge_unique_roles(*role_lists):
    """Merge roles when any stable identity overlaps.

    Meta returns the numeric app-role user id while the Sheet can carry a
    username/profile id for the same person.  Using one arbitrarily selected
    identity key as the dictionary key duplicates those records.  Treat the
    identity-key set as an equivalence relation and merge all overlapping
    groups, including transitive matches.
    """
    merged = []
    identities = []
    for roles in role_lists:
        for r in roles or []:
            keys = role_identity_keys(r)
            matches = [i for i, known in enumerate(identities) if keys & known]
            if not matches:
                merged.append(dict(r))
                identities.append(set(keys))
                continue

            first = matches[0]
            combined_role = dict(merged[first])
            combined_keys = set(identities[first]) | keys
            for i in matches[1:]:
                combined_role.update(merged[i])
                combined_keys.update(identities[i])
            combined_role.update(r)
            merged[first] = combined_role
            identities[first] = combined_keys
            for i in reversed(matches[1:]):
                del merged[i]
                del identities[i]

    return sorted(merged, key=lambda r: (r.get('name', '').lower(), role_key(r)))


def build_app_snapshot(item, previous_app_state=None):
    item_data = OP_RESOLVER.get_item_json(item, VAULT)
    app_id = OP_RESOLVER.field_value(item_data, 'app_id', required=True)
    item_code = APP_ITEM_TO_KEY.get(item) or item.replace('BOT ', '').replace(' Token', '')
    raw_app_name = OP_RESOLVER.field_value(item_data, 'app_name')
    # Active state, alerts and channel routing use the exact registry key.
    app_name = canonical_app_key(item_code)
    access_token = OP_RESOLVER.field_value(item_data, 'access_token')
    app_secret = OP_RESOLVER.field_value(item_data, 'app_secret', 'secret_key')
    if not app_secret:
        raise RuntimeError(f'app_secret missing for {item}')
    app_token = f'{app_id}|{app_secret}'

    checks = {}
    merged_headers = {}

    # App metadata using app token: verifies app exists/access is valid and gives X-App-Usage.
    st_app, h_app, d_app = graph_get(f'/{app_id}', {'fields': 'id,name,category,link,app_domains'}, app_token)
    merged_headers.update(h_app)
    checks['app_metadata'] = {'status': st_app, 'ok': st_app == 200 and 'error' not in d_app}
    if not checks['app_metadata']['ok']:
        checks['app_metadata']['error'] = extract_error(d_app)

    # Roles: detects segurador/admin removal/addition. Follow every Meta page
    # until paging.next is absent; there is no total-role cap.
    st_roles, h_roles, d_roles = graph_get_all_pages(f'/{app_id}/roles', {}, app_token)
    merged_headers.update(h_roles)
    if st_roles != 200 or 'error' in d_roles:
        raise RuntimeError(f'roles query failed app={app_name} status={st_roles} error={extract_error(d_roles)}')
    role_page_count = int(d_roles.get('_page_count') or 1)

    raw_role_rows = []
    for row in d_roles.get('data', []):
        uid = str(row.get('user', '')).strip()
        role = str(row.get('role', '')).strip()
        if uid:
            raw_role_rows.append({'id': uid, 'role': role})

    # Resolve role identities in bounded Graph multi-ID chunks first. Replacement
    # apps can return HTTP 200 with per-ID errors under the app token, while the
    # same IDs resolve individually under the validated user token. Reuse prior
    # state names and query only genuinely new IDs so the fallback is bounded and
    # does not become a per-cycle N+1 quota drain.
    identity_data = {}
    identity_statuses = []
    identity_chunk_size = 50
    previous_roles_by_id = {}
    for previous_role in list((previous_app_state or {}).get('roles') or []) + list((previous_app_state or {}).get('operational_roles') or []):
        previous_uid = str(previous_role.get('id') or '').strip()
        previous_name = str(previous_role.get('name') or '').strip()
        if previous_uid and previous_name and norm_name(previous_name) != norm_name(previous_uid):
            previous_roles_by_id[previous_uid] = previous_name
    if raw_role_rows:
        role_ids = [r['id'] for r in raw_role_rows]
        for offset in range(0, len(role_ids), identity_chunk_size):
            chunk = role_ids[offset:offset + identity_chunk_size]
            final_status = 0
            final_data = {}
            for attempt in range(1, 3):
                final_status, h_users, final_data = graph_get(
                    '/',
                    {'ids': ','.join(chunk), 'fields': 'id,name'},
                    app_token,
                )
                merged_headers.update(h_users)
                if final_status == 200:
                    break
                if final_status not in {500, 502, 503, 504}:
                    break
                time.sleep(attempt)
            if final_status != 200 and access_token:
                fallback_status, h_users, fallback_data = graph_get(
                    '/',
                    {'ids': ','.join(chunk), 'fields': 'id,name'},
                    access_token,
                )
                merged_headers.update(h_users)
                if fallback_status == 200:
                    final_status, final_data = fallback_status, fallback_data
            identity_statuses.append(final_status)
            if isinstance(final_data, dict):
                for uid in chunk:
                    value = final_data.get(uid)
                    if isinstance(value, dict) and value.get('name') and 'error' not in value:
                        identity_data[uid] = value

    cache_resolved_count = 0
    for row in raw_role_rows:
        uid = row['id']
        value = identity_data.get(uid) or {}
        if isinstance(value, dict) and value.get('name') and 'error' not in value:
            continue
        cached_name = previous_roles_by_id.get(uid)
        if cached_name:
            identity_data[uid] = {'id': uid, 'name': cached_name}
            cache_resolved_count += 1

    unresolved_for_individual = [
        row['id'] for row in raw_role_rows
        if not isinstance(identity_data.get(row['id']), dict)
        or not (identity_data.get(row['id']) or {}).get('name')
        or 'error' in (identity_data.get(row['id']) or {})
    ]
    individual_identity_limit = 20
    individual_statuses = []
    individual_resolved_count = 0
    if access_token and len(unresolved_for_individual) <= individual_identity_limit:
        for uid in unresolved_for_individual:
            final_status = 0
            final_data = {}
            for attempt in range(1, 4):
                final_status, h_user, final_data = graph_get(
                    f'/{uid}',
                    {'fields': 'id,name'},
                    access_token,
                )
                merged_headers.update(h_user)
                if final_status == 200 and isinstance(final_data, dict) and final_data.get('name') and 'error' not in final_data:
                    break
                if final_status not in {403, 429, 500, 502, 503, 504}:
                    break
                time.sleep(attempt)
            individual_statuses.append(final_status)
            if final_status == 200 and isinstance(final_data, dict) and final_data.get('name') and 'error' not in final_data:
                identity_data[uid] = final_data
                individual_resolved_count += 1

    all_identities_resolved = all(
        isinstance(identity_data.get(row['id']), dict)
        and (identity_data.get(row['id']) or {}).get('name')
        and 'error' not in (identity_data.get(row['id']) or {})
        for row in raw_role_rows
    )
    identity_status = 200 if all_identities_resolved else (next((s for s in identity_statuses + individual_statuses if s != 200), 206))
    baseline_cfg = ((IDENTITY_BASELINE.get('apps') or {}).get(app_name) or {})
    current_ids = sorted(r['id'] for r in raw_role_rows)
    current_ids_sha256 = hashlib.sha256(('\n'.join(current_ids) + '\n').encode('utf-8')).hexdigest()
    baseline_applied = False
    # New replacement apps often return app-scoped role IDs but omit names from
    # batched multi-ID reads. Use the independently resolved fresh audit only
    # while the exact app-scoped ID signature remains unchanged.
    if (
        baseline_cfg
        and int(baseline_cfg.get('role_count') or 0) == len(raw_role_rows)
        and baseline_cfg.get('ids_sha256') == current_ids_sha256
    ):
        baseline_by_id = {str(r.get('id') or ''): r for r in (baseline_cfg.get('roles') or [])}
        for uid in current_ids:
            if uid not in identity_data and uid in baseline_by_id:
                identity_data[uid] = {
                    'id': uid,
                    'name': baseline_by_id[uid].get('name'),
                }
        baseline_applied = True
    roles = []
    resolved_identity_count = 0
    for row in raw_role_rows:
        uid = row['id']
        identity = identity_data.get(uid) or {}
        name = identity.get('name') if isinstance(identity, dict) and 'error' not in identity else None
        if name:
            resolved_identity_count += 1
        roles.append({'id': uid, 'name': name or uid, 'role': row['role']})
    roles.sort(key=lambda x: (x.get('role', ''), x.get('name', '').lower(), x.get('id', '')))
    checks['roles'] = {'status': st_roles, 'ok': True, 'count': len(roles), 'pages': role_page_count}

    # User/access token checks: catches expired/invalid monitor token and scope drift.
    token_info = {'present': bool(access_token), 'valid': None, 'scopes': [], 'expires_at': None}
    if access_token:
        st_me, h_me, d_me = graph_get('/me', {'fields': 'id,name'}, access_token)
        merged_headers.update(h_me)
        checks['user_token_me'] = {'status': st_me, 'ok': st_me == 200 and 'error' not in d_me}
        if not checks['user_token_me']['ok']:
            checks['user_token_me']['error'] = extract_error(d_me)

        st_dbg, h_dbg, d_dbg = graph_get('/debug_token', {'input_token': access_token}, app_token)
        merged_headers.update(h_dbg)
        dbg = d_dbg.get('data', {}) if isinstance(d_dbg, dict) else {}
        token_info.update({
            'valid': bool(dbg.get('is_valid')),
            'scopes': sorted(dbg.get('scopes') or []),
            'expires_at': dbg.get('expires_at'),
            'app_id': dbg.get('app_id'),
            'type': dbg.get('type'),
        })
        checks['debug_token'] = {'status': st_dbg, 'ok': st_dbg == 200 and token_info['valid'] is True}
        if not checks['debug_token']['ok']:
            checks['debug_token']['error'] = extract_error(d_dbg)
    else:
        checks['user_token_me'] = {'status': None, 'ok': False, 'error': {'message': 'access_token missing in 1Password item'}}
        checks['debug_token'] = {'status': None, 'ok': False, 'error': {'message': 'access_token missing in 1Password item'}}

    usage = usage_from_headers(merged_headers)
    return {
        'item': item,
        'app_id': app_id,
        'app_name': app_name,
        'roles': roles,
        'roles_count': len(roles),
        'x_app_usage': usage.get('raw'),
        'usage': usage,
        'checks': checks,
        'role_identity_resolution': {
            'status': identity_status,
            'requested_count': len(raw_role_rows),
            'resolved_count': resolved_identity_count,
            'unresolved_count': len(raw_role_rows) - resolved_identity_count,
            'mode': 'graph_multi_id_chunked',
            'source_pages': role_page_count,
            'chunk_size': identity_chunk_size,
            'chunks': len(identity_statuses),
            'chunk_statuses': identity_statuses,
            'cache_resolved_count': cache_resolved_count,
            'individual_limit': individual_identity_limit,
            'individual_requested_count': len(unresolved_for_individual) if len(unresolved_for_individual) <= individual_identity_limit else 0,
            'individual_resolved_count': individual_resolved_count,
            'individual_statuses': individual_statuses,
            'baseline_applied': baseline_applied,
            'role_ids_sha256': current_ids_sha256,
        },
        'token_info': token_info,
        'checked_at': now_iso(),
    }


def alert_usage(app_name, prev, snap):
    usage = snap['usage']
    severity = usage['severity']
    previous = (prev.get('usage') or {}).get('severity', 'ok')
    if severity == 'ok':
        return False
    increased = SEVERITY_ORDER[severity] > SEVERITY_ORDER.get(previous, 0)
    repeated_critical = severity == 'critical' and should_alert_cooldown(prev, 'usage', severity)
    if not (increased or repeated_critical):
        return False
    embed = {
        'title': f'Meta App Rate Limit — {app_name}',
        'description': 'Uso do app Meta entrou em zona de risco. Em 95–100%, o app pode parar de responder/enviar.',
        'color': SEVERITY_COLOR[severity],
        'fields': [
            {'name': 'Estado', 'value': SEVERITY_LABEL[severity], 'inline': True},
            {'name': 'Uso máximo', 'value': fmt_usage(usage), 'inline': True},
            *admin_alert_fields(app_name),
            {'name': 'Estado anterior', 'value': SEVERITY_LABEL.get(previous, previous), 'inline': True},
            {'name': 'X-App-Usage', 'value': str(usage.get('parsed') or usage.get('raw') or 'ausente')[:900], 'inline': False},
            {'name': 'Ação', 'value': 'Se persistir em 95%+: reduzir carga/splitar app imediatamente. Para B007/Openzed, tratar como prioridade máxima.', 'inline': False},
        ],
        'footer': {'text': 'MGS Zeus • Meta App Rate Limit Watch'},
    }
    post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=app_name)
    mark_alert(prev, 'usage', severity)
    return True


def alert_token_or_check(app_name, prev, snap):
    bad = []
    transient_bad = []
    for name, chk in (snap.get('checks') or {}).items():
        # debug_token remains state-only here. For B001-B012, /me is also
        # informational because every segurador is an app administrator; the
        # monitor token profile is not a unique app owner or health dependency.
        if health_check_is_ignored(app_name, name):
            continue
        if not chk.get('ok'):
            msg = f"{name}: status={chk.get('status')} {((chk.get('error') or {}).get('message') or '')[:180]}"
            bad.append(msg)
            if check_is_transient_meta_api(name, chk):
                transient_bad.append(msg)
    if not bad:
        return False

    if len(transient_bad) == len(bad):
        severity = 'attention'
        if not should_alert_cooldown(prev, 'transient_checks', severity):
            return False
        embed = {
            'title': f'Meta App Health — {app_name}',
            'description': 'Instabilidade temporária no Meta Graph. App/roles continuam acessíveis; isso não confirma app desconectado.',
            'color': SEVERITY_COLOR[severity],
            'fields': [
                {'name': 'Estado', 'value': 'ATENÇÃO', 'inline': True},
                *admin_alert_fields(app_name),
                {'name': 'Falha isolada', 'value': '\n'.join(transient_bad)[:950], 'inline': False},
                {'name': 'Ação', 'value': 'Aguardar o próximo ciclo. Se recuperar, o monitor enviará aviso de falso positivo/recuperado no canal.', 'inline': False},
            ],
            'footer': {'text': 'MGS Zeus • Meta App Health Watch'},
        }
        post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=app_name)
        mark_alert(prev, 'transient_checks', severity)
        prev['last_check_incident_at'] = now_iso()
        prev['last_check_incident_kind'] = 'transient_meta_api'
        return True

    # Alert immediately on token/app failures; these are not noisy if state/cooldown works.
    severity = 'critical'
    if not should_alert_cooldown(prev, 'checks', severity):
        return False
    embed = {
        'title': f'Meta App Health — {app_name}',
        'description': 'Falha em token/app/check do Meta. Pode indicar token expirado, permissão removida, app inacessível ou developer access quebrado.',
        'color': SEVERITY_COLOR[severity],
        'fields': [
            {'name': 'Estado', 'value': 'CRÍTICO', 'inline': True},
            *admin_alert_fields(app_name),
            {'name': 'Falhas', 'value': '\n'.join(bad)[:950], 'inline': False},
            {'name': 'Ação', 'value': 'Verificar token no 1Password/Graph API Explorer e acesso do app no Meta Developers.', 'inline': False},
        ],
        'footer': {'text': 'MGS Zeus • Meta App Health Watch'},
    }
    post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=app_name)
    mark_alert(prev, 'checks', severity)
    prev['last_check_incident_at'] = now_iso()
    prev['last_check_incident_kind'] = 'critical_health_check'
    return True


def alert_check_recovered(app_name, prev, snap, force=False):
    if not monitored_checks_ok(snap):
        return False
    if not force and not unresolved_check_alert(prev):
        return False
    usage = snap.get('usage') or {}
    embed = {
        'title': f'Meta App Health Recuperado — {app_name}',
        'description': 'Check seguinte voltou OK. Classificação operacional: falso positivo/instabilidade temporária da API Meta, não app desconectado.',
        'color': SEVERITY_COLOR['ok'],
        'fields': [
            {'name': 'Estado', 'value': 'RECUPERADO', 'inline': True},
            {'name': 'App', 'value': app_name, 'inline': True},
            *admin_alert_fields(app_name),
            {'name': 'Checks', 'value': monitored_check_summary(snap), 'inline': False},
            {'name': 'Uso', 'value': fmt_usage(usage), 'inline': True},
            {'name': 'Ação', 'value': 'Nenhuma ação operacional necessária pela Ially neste momento.', 'inline': False},
        ],
        'footer': {'text': 'MGS Zeus • Meta App Health Watch'},
    }
    post_webhook('', embed, app_name=app_name)
    prev['last_check_recovered_at'] = now_iso()
    return True


def alert_roles_snapshot(app_name, prev, snap, removed, added, cumulative_removed):
    roles = snap.get('operational_roles') or snap.get('roles') or []
    usage = snap.get('usage') or {}
    embed = {
        'title': f'Meta APP - {app_name}',
        'description': 'Snapshot atualizado da lista de usuários do app. Ordenado por BOT EMAIL.',
        'color': SEVERITY_COLOR.get(usage.get('severity'), SEVERITY_COLOR['ok']),
        'fields': [
            {'name': 'ESTADO', 'value': SEVERITY_LABEL.get(usage.get('severity'), 'OK'), 'inline': True},
            {'name': 'CONTAGEM', 'value': str(len(roles)), 'inline': True},
            *admin_alert_fields(app_name, label='ADMIN'),
            {'name': 'USO', 'value': fmt_usage(usage), 'inline': True},
        ],
        'footer': {'text': 'MGS Zeus • App Roles Watch'},
    }
    users_block = section_block('👥 USUÁRIOS ATUAIS', fmt_roles(roles, app_key=app_name))
    movement_block = '\n\n'.join([
        section_block('➖ USUÁRIOS REMOVIDOS AGORA', fmt_delta_roles(removed, app_key=app_name)),
        section_block('🆕 USUÁRIOS ADICIONADOS AGORA', fmt_delta_roles(added, app_key=app_name)),
        section_block('📦 REMOVIDOS ACUMULADOS', fmt_delta_roles(cumulative_removed, app_key=app_name)),
    ])
    post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=app_name)
    post_code_blocks(users_block, app_name=app_name)
    post_code_blocks(movement_block, app_name=app_name)
    return True


def alert_roles_live_manual(app_name, snap, removed, added, cumulative_removed):
    """Force-send the cron-style roles alert using fresh/live data.

    This is for Rodolfo's explicit test/resend request. It uses the same visual
    shape as cron role-change alerts, but it does not mutate previous roles or
    pretend a real delta happened.
    """
    roles = snap.get('operational_roles') or snap.get('roles') or []
    usage = snap.get('usage') or {}
    embed = {
        'title': f'Meta APP - {app_name}',
        'description': 'Alerta live solicitado. Dados consultados agora no Meta Graph e reconciliados com a planilha.',
        'color': SEVERITY_COLOR.get(usage.get('severity'), SEVERITY_COLOR['ok']),
        'fields': [
            {'name': 'ESTADO', 'value': SEVERITY_LABEL.get(usage.get('severity'), 'OK'), 'inline': True},
            {'name': 'CONTAGEM', 'value': str(len(roles)), 'inline': True},
            *admin_alert_fields(app_name, label='ADMIN'),
            {'name': 'USO', 'value': fmt_usage(usage), 'inline': True},
        ],
        'footer': {'text': 'MGS Zeus • App Roles Watch'},
    }
    users_block = section_block('👥 USUÁRIOS ATUAIS', fmt_roles(roles, app_key=app_name))
    movement_block = '\n\n'.join([
        section_block('➖ USUÁRIOS REMOVIDOS AGORA', fmt_delta_roles(removed, app_key=app_name)),
        section_block('🆕 USUÁRIOS ADICIONADOS AGORA', fmt_delta_roles(added, app_key=app_name)),
        section_block('📦 REMOVIDOS ACUMULADOS', fmt_delta_roles(cumulative_removed, app_key=app_name)),
    ])
    post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=app_name)
    post_code_blocks(users_block, app_name=app_name)
    post_code_blocks(movement_block, app_name=app_name)
    return True


state = load_state()
state.setdefault('apps', {})
# One-time migration guards: once a replacement state exists, remove the stale
# predecessor key so alerts and baselines stay canonical. Replacement suffixes
# always supersede the immediately preceding active app key.
for replacement_key, retired_key in (('B001-2', 'B001'), ('B001-3', 'B001-2'), ('B002-2', 'B002'), ('B003-2', 'B003'), ('B004-3', 'B004-2'), ('B005-3', 'B005-2'), ('B006-3', 'B006-2'), ('B008-2', 'B008'), ('B009-2', 'B009'), ('B010-2', 'B010')):
    if replacement_key in ACTIVE_APP_CONFIGS and retired_key in state['apps']:
        state['apps'].pop(retired_key, None)
state['_last_discovered_items'] = []
alerts_sent = 0
errors = []
items = discover_app_items()
state['_last_discovered_items'] = items
# Load the migration sheet before evaluating role deltas. The sheet is the
# operational intent layer (APP PROVISORIO/USUARIO/OBS), so role-change alerts must not
# be decided from Meta API state alone.
load_sheet_users()
role_alert_events = []
successful_app_keys = set()

for item_index, item in enumerate(items):
    if item_index and APP_STAGGER_SECONDS:
        time.sleep(APP_STAGGER_SECONDS)
    item_code = APP_ITEM_TO_KEY.get(item) or item.replace('BOT ', '').replace(' Token', '')
    app_key = canonical_app_key(item_code)
    prev = state['apps'].get(app_key, {})
    try:
        snap = build_app_snapshot(item, prev)
        key = app_key
        prev = state['apps'].get(key, prev)
        prev_roles = prev.get('roles') or []
        curr_roles = snap['roles']
        operational_roles, identity_reconciliation = operational_roles_for_app(key, curr_roles)
        expected_sheet_roles = int((ACTIVE_APP_CONFIGS.get(key) or {}).get('expected_sheet_roles') or 0)
        if expected_sheet_roles and len(curr_roles) < expected_sheet_roles:
            identity_reconciliation = {
                **identity_reconciliation,
                'status': 'pending_expected_role_acceptance',
                'safe_for_sheet': False,
                'expected_sheet_roles': expected_sheet_roles,
                'accepted_roles': len(curr_roles),
                'pending_roles': expected_sheet_roles - len(curr_roles),
            }
        snap['operational_roles'] = operational_roles
        snap['role_identity_reconciliation'] = identity_reconciliation
        prev_by = {role_key(r): r for r in prev_roles}
        curr_by = {role_key(r): r for r in curr_roles}
        removed = [prev_by[k] for k in sorted(set(prev_by) - set(curr_by), key=lambda k: prev_by[k].get('name', '').lower())]
        added = [curr_by[k] for k in sorted(set(curr_by) - set(prev_by), key=lambda k: curr_by[k].get('name', '').lower())]
        removed = [
            r for r in removed
            if not is_owner_housekeeping_removal(r, key)
            and not is_verification_ignored_role(r)
        ]
        added = [r for r in added if not is_verification_ignored_role(r)]
        # A Meta API visibility oscillation is not a real role movement when the
        # Rodolfo-confirmed UI identity remains present in both operational views.
        ui_cfg = APP_CONFIRMED_UI_ROLE_OVERRIDES.get(key) or {}
        confirmed_ui_names = {norm_name(name) for name in (ui_cfg.get('ui_only_names') or ())}
        if confirmed_ui_names:
            prev_operational_names = {
                norm_name(r.get('name'))
                for r in (prev.get('operational_roles') or prev_roles)
                if norm_name(r.get('name'))
            }
            curr_operational_names = {
                norm_name(r.get('name'))
                for r in operational_roles
                if norm_name(r.get('name'))
            }
            stable_ui_names = confirmed_ui_names & prev_operational_names & curr_operational_names
            removed = [r for r in removed if norm_name(r.get('name')) not in stable_ui_names]
            added = [r for r in added if norm_name(r.get('name')) not in stable_ui_names]
        initialized = not prev_roles and not prev.get('initialized')
        curr_identity_keys = set()
        for r in list(curr_roles) + list(operational_roles):
            curr_identity_keys.update(role_identity_keys(r))
        old_profile_names = (SHEET_OLD_PROFILE_NAMES_BY_APP or {}).get(key, set())
        cumulative_removed = [
            r for r in merge_unique_roles(prev.get('cumulative_removed') or [], removed)
            if not role_matches_any(r, curr_identity_keys)
            and not is_owner_housekeeping_removal(r, key)
            and norm_name(r.get('name')) not in old_profile_names
            and role_still_assigned_to_app(r, key)
        ]

        state['apps'][key] = {
            **snap,
            'initialized': True,
            'previous_count': len(prev_roles),
            'current_count': len(curr_roles),
            'last_ok_at': snap['checked_at'],
            'consecutive_errors': 0,
            'last_error': None,
            'alerts': prev.get('alerts', {}),
            'last_removed': removed,
            'last_added': added,
            'cumulative_removed': cumulative_removed,
        }
        successful_app_keys.add(key)

        # Defer role/snapshot alerts until after sheet reconciliation below.
        # Rate-limit/token/API-health alerts can still be evaluated immediately;
        # they do not depend on the migration sheet.
        role_alert_events.append({
            'key': key,
            'prev': prev,
            'snap': snap,
            'removed': removed,
            'added': added,
            'cumulative_removed': cumulative_removed,
            'prev_roles': prev_roles,
            'curr_roles': curr_roles,
            'operational_roles': operational_roles,
            'initialized': initialized,
        })

        if alert_usage(key, prev, snap):
            alerts_sent += 1
        health_alert_sent = alert_token_or_check(key, prev, snap)
        if health_alert_sent:
            state['apps'][key]['last_check_incident_at'] = prev.get('last_check_incident_at')
            state['apps'][key]['last_check_incident_kind'] = prev.get('last_check_incident_kind')
            alerts_sent += 1
        elif alert_check_recovered(key, prev, snap, force=FORCE_RECOVERY_NOTICE):
            state['apps'][key]['last_check_recovered_at'] = prev.get('last_check_recovered_at')
            alerts_sent += 1
    except Exception as e:
        errors.append((item, str(e)))
        key = app_key
        prev = state['apps'].get(key, {})
        ce = int(prev.get('consecutive_errors') or 0) + 1
        prev.update({'consecutive_errors': ce, 'last_error': str(e), 'last_error_at': now_iso(), 'initialized': prev.get('initialized', False)})
        state['apps'][key] = prev
        restricted = uses_shared_admin_model(key) and is_application_deleted_error(e)
        blocked = is_api_access_blocked_error(e)
        alert_key = 'app_restricted' if restricted else ('api_access_blocked' if blocked else 'script_error')
        cooldown = API_BLOCKED_ALERT_COOLDOWN_MINUTES if (restricted or blocked) else ALERT_COOLDOWN_MINUTES
        if FORCE_SNAPSHOT and prev.get('roles'):
            embed = {
                'title': f'Meta App Roles — {key}',
                'description': f"Graph API bloqueado agora; lista abaixo é o último snapshot válido ({prev.get('last_ok_at') or 'sem data'}).",
                'color': SEVERITY_COLOR['critical'],
                'fields': [
                    {'name': 'Estado', 'value': 'CRÍTICO', 'inline': True},
                    {'name': 'App', 'value': key, 'inline': True},
                    {'name': 'Contagem', 'value': str(len(prev.get('roles') or [])), 'inline': True},
                    *admin_alert_fields(key),
                    {'name': 'Erro atual', 'value': clip_field(str(e), 900), 'inline': False},
                    {'name': 'Usuários do app', 'value': clip_field(fmt_roles(prev.get('operational_roles') or prev.get('roles') or [], app_key=key)), 'inline': False},
                    {'name': 'Usuários removidos', 'value': clip_field(fmt_delta_roles(prev.get('last_removed') or [], app_key=key)), 'inline': False},
                    {'name': 'Usuários adicionados', 'value': clip_field(fmt_delta_roles(prev.get('last_added') or [], app_key=key)), 'inline': False},
                    {'name': 'Removidos acumulados', 'value': clip_field(fmt_delta_roles(prev.get('cumulative_removed') or [], app_key=key)), 'inline': False},
                ],
                'footer': {'text': 'MGS Zeus • App Roles Watch'},
            }
            post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=key)
            alerts_sent += 1
        if ce >= 2 and should_alert_cooldown(prev, alert_key, 'critical', cooldown_minutes=cooldown):
            if restricted:
                embed = restriction_alert_embed(key, ce)
                post_webhook(
                    restriction_alert_content(),
                    embed,
                    app_name=key,
                    allowed_mentions=restriction_alert_allowed_mentions(),
                )
                post_webhook(
                    f'{RESTRICTION_ALERT_EMOJIS}.',
                    app_name=key,
                    allowed_mentions={'parse': []},
                )
            else:
                title = f'Meta App API Blocked — {key}' if blocked else f'Meta App Monitor — {key}'
                description = (
                    'A Meta está bloqueando chamadas Graph API para este app/token. Não é falha de 1Password/webhook; requer ação no Meta Developers ou substituição do app/token.'
                    if blocked else
                    'Falha repetida ao executar o monitor Meta app-rate-limit/roles.'
                )
                action = (
                    'Abrir Meta Developers no perfil admin do app, verificar restrição/API access blocked e gerar novo token/app se necessário. Monitor reduzido para alerta diário até recuperar.'
                    if blocked else
                    'Verificar 1Password, Graph API, webhook e validade dos tokens.'
                )
                embed = {
                    'title': title,
                    'description': description,
                    'color': SEVERITY_COLOR['critical'],
                    'fields': [
                        {'name': 'Estado', 'value': 'CRÍTICO', 'inline': True},
                        {'name': 'Falhas consecutivas', 'value': str(ce), 'inline': True},
                        *admin_alert_fields(key),
                        {'name': 'Erro', 'value': str(e)[:900], 'inline': False},
                        {'name': 'Ação', 'value': action, 'inline': False},
                    ],
                    'footer': {'text': 'MGS Zeus • Meta App Monitor'},
                }
                post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=key)
            mark_alert(prev, alert_key, 'critical')
            alerts_sent += 1

try:
    sheet_sync = sync_sheet_removed_accumulated(state, successful_app_keys)
    state['_sheet_removed_sync_consecutive_errors'] = 0
except Exception as e:
    sheet_failures = int(state.get('_sheet_removed_sync_consecutive_errors') or 0) + 1
    state['_sheet_removed_sync_consecutive_errors'] = sheet_failures
    sheet_sync = {
        'enabled': SYNC_SHEET_REMOVED,
        'updated': False,
        'error': str(e)[:500],
        'consecutive_errors': sheet_failures,
        'checked_at': now_iso(),
    }
    # Retryable Google/Sheets timeouts happen occasionally. Alert only after two
    # consecutive failed cycles, and route this infra failure to #alerts-infra
    # instead of the B007/app-rate-limit webhook fallback.
    if sheet_failures >= 2 and should_alert_cooldown(state, 'sheet_removed_sync', 'critical', cooldown_minutes=ALERT_COOLDOWN_MINUTES):
        embed = {
            'title': 'Meta App Roles — falha sync planilha',
            'description': 'O monitor de apps não conseguiu sincronizar a coluna de removidos acumulados na planilha de migração.',
            'color': SEVERITY_COLOR['critical'],
            'fields': [
                {'name': 'Estado', 'value': 'CRÍTICO', 'inline': True},
                {'name': 'Planilha', 'value': SPREADSHEET_ID, 'inline': True},
                {'name': 'Sheet/GID', 'value': str(SHEET_GID), 'inline': True},
                {'name': 'Auth mode', 'value': GOOGLE_AUTH_MODE, 'inline': True},
                {'name': 'Erro', 'value': clip_field(str(e), 900), 'inline': False},
                {'name': 'Ação', 'value': 'Verificar OAuth/Service Account, Sheets API habilitada e permissão de escrita da planilha.', 'inline': False},
            ],
            'footer': {'text': 'MGS Zeus • Meta App Roles Watch'},
        }
        try:
            post_infra_alert(f'<@{RODOLFO_ID}>', embed)
            alerts_sent += 1
            mark_alert(state, 'sheet_removed_sync', 'critical')
        except Exception as alert_error:
            sheet_sync['alert_error'] = str(alert_error)[:300]
state['_sheet_removed_sync'] = sheet_sync

# Role-change/snapshot alerts are sent only after the Meta API pass and the
# sheet reconciliation pass have both completed. This prevents planned sheet
# migrations/OBS cleanup from producing false-positive role alerts.
for event in role_alert_events:
    key = event['key']
    prev = event['prev']
    snap = event['snap']
    removed = event['removed']
    added = event['added']
    cumulative_removed = event['cumulative_removed']
    sheet_cumulative_removed = sheet_removed_roles_for_app(key)
    display_cumulative_removed = merge_unique_roles(cumulative_removed, sheet_cumulative_removed)
    prev_roles = event['prev_roles']
    curr_roles = event['curr_roles']
    operational_roles = event['operational_roles']
    initialized = event['initialized']

    # Keep live checks/state reconciliation running, but suppress every
    # app-channel delivery while Rodolfo's temporary pause is active.
    if key in PAUSED_APP_ALERTS:
        continue

    # Alert only on cycle deltas. On the next cron, added users become part of
    # "Usuários do app" and stop appearing as added. Removed users remain only in
    # the removal fields, never inside the current app list.
    # A manual force-live alert is the current view only. Suppress the automatic
    # state-delta alert in the same run so one operator request cannot duplicate
    # the alert family or burst enough messages to hit Discord rate limits.
    if not FORCE_SNAPSHOT and not FORCE_LIVE_ALERT and not initialized and (removed or added):
        severity = 'critical' if removed else 'attention'
        if removed and added:
            description = 'Mudança detectada na lista do app: usuário removido e usuário adicionado.'
        elif removed:
            description = 'Usuário removido da lista do app.'
        else:
            description = 'Usuário adicionado à lista do app.'
        embed = {
            'title': f'Meta APP - {key}',
            'description': description,
            'color': SEVERITY_COLOR[severity],
            'fields': [
                {'name': 'ESTADO', 'value': SEVERITY_LABEL[severity], 'inline': True},
                {'name': 'CONTAGEM', 'value': f'{len(prev_roles)} → {len(curr_roles)}', 'inline': True},
                *admin_alert_fields(key, label='ADMIN'),
                {'name': 'USO', 'value': fmt_usage(snap.get('usage') or {}), 'inline': True},
            ],
            'footer': {'text': 'MGS Zeus • App Roles Watch'},
        }
        users_block = section_block('👥 USUÁRIOS ATUAIS', fmt_roles(operational_roles, app_key=key))
        movement_block = '\n\n'.join([
            section_block('➖ USUÁRIOS REMOVIDOS AGORA', fmt_delta_roles(removed, app_key=key)),
            section_block('🆕 USUÁRIOS ADICIONADOS AGORA', fmt_delta_roles(added, app_key=key)),
            section_block('📦 REMOVIDOS ACUMULADOS', fmt_delta_roles(display_cumulative_removed, app_key=key)),
        ])
        post_webhook(f'<@{RODOLFO_ID}>', embed, app_name=key)
        post_code_blocks(users_block, app_name=key)
        post_code_blocks(movement_block, app_name=key)
        alerts_sent += 1

    if FORCE_LIVE_ALERT:
        # Manual/live alert must be a fresh monitor view, not a state-delta view.
        # Current users come from fresh Meta /roles; accumulated removals come
        # from the live sheet X/reconciliation layer. Do not show cached
        # removed/added deltas from previous state in a forced live resend.
        alert_roles_live_manual(key, snap, [], [], sheet_cumulative_removed)
        alerts_sent += 1

    if FORCE_SNAPSHOT:
        alert_roles_snapshot(key, prev, snap, removed, added, display_cumulative_removed)
        alerts_sent += 1

state['_updated_at'] = now_iso()
state['_last_run_summary'] = {
    'items': items,
    'alerts_sent': alerts_sent,
    'errors_count': len(errors),
    'dry_run': DRY_RUN,
    'force_snapshot_requested': FORCE_SNAPSHOT_REQUESTED,
    'force_snapshot_effective': FORCE_SNAPSHOT,
    'snapshot_blocked': SNAPSHOT_BLOCKED,
    'force_live_alert': FORCE_LIVE_ALERT,
    'force_recovery_notice': FORCE_RECOVERY_NOTICE,
    'active_alert_pause': {
        'apps': sorted(PAUSED_APP_ALERTS),
        'mode': 'manual' if ACTIVE_ALERT_PAUSE.get('manual') else 'until',
        'manual': bool(ACTIVE_ALERT_PAUSE.get('manual')),
        'until': ACTIVE_ALERT_PAUSE.get('until'),
        'expired': bool(ACTIVE_ALERT_PAUSE.get('expired')),
        'invalid': bool(ACTIVE_ALERT_PAUSE.get('invalid')),
        'reason': ACTIVE_ALERT_PAUSE.get('reason'),
    },
    'suppressed_alert_deliveries': SUPPRESSED_ALERT_DELIVERIES,
    'sheet_removed_sync': sheet_sync,
}
if not DRY_RUN:
    save_state(state)

# Silence by default. no_agent cron with empty stdout = no Discord delivery.
# Dry-run intentionally prints compact JSON for validation only.
PY
