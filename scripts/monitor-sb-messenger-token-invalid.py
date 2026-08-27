#!/usr/bin/env python3
"""Mirror Smart Bidding Messenger-token alerts into MGS Discord.

Source of truth: authenticated Smart Bidding notification API. The monitor never
reads, stores, or validates Facebook tokens itself. It filters MGS companies,
deduplicates by SB notification ID, enriches each alert with the live Messenger
page count, and posts through the local Zeus bot with mentions disabled.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
STATE_PATH = BASE / 'data/sb-messenger-token-invalid-monitor.json'
SB_STATE = Path('/root/.local/share/mgs/smartbidding_state_headed.json')
APP_URL = 'https://app.smartbiddingdigital.com/accounts'
API_BASE = 'https://api.jbfdigital.com.br'
TARGET_CHANNEL_ID = '1521350832426188961'
INFRA_CHANNEL_ID = '1498132022634483894'
RODOLFO_ID = '344196393512075265'
MGS_COMPANIES = {'digital-trust', 'digital-trust-2'}
ALERT_TITLE = 'Messenger user token invalid'
NY = ZoneInfo('America/New_York')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
MAX_EMBEDS = 10
MAX_DELIVERED_IDS = 1000


def now_iso() -> str:
    return datetime.now(NY).isoformat(timespec='seconds')


def load_env(path: Path = Path('/root/.hermes/profiles/zeus/.env')) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors='ignore').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def initial_state() -> dict[str, Any]:
    return {
        '_meta': {
            'description': 'Mirror de alertas SB Messenger user token invalid; sem tokens brutos.',
            'target_channel_id': TARGET_CHANNEL_ID,
            'source': API_BASE + '/notification',
            'companies': sorted(MGS_COMPANIES),
            'mentions': 'disabled; matches paginas-restritas channel delivery',
        },
        'last_check': None,
        'last_seen_id': 0,
        'delivered_ids': [],
        'pending': None,
        'last_delivery': None,
        'consecutive_failures': 0,
        'last_error': None,
        'failure_alert_sent_for': 0,
    }


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise RuntimeError('state is not an object')
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write('\n')
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def normalize_alerts(notifications: list[dict[str, Any]], pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exact_counts: Counter[tuple[str, str, str]] = Counter()
    user_counts: Counter[str] = Counter()
    for page in pages:
        user_id = str(page.get('MESSENGER_USER_ID') or '').strip()
        if not user_id:
            continue
        user_counts[user_id] += 1
        company = str(page.get('COMPANY') or '').strip()
        publisher = str(page.get('PUBLISHER_ID') or '').strip()
        domain = ''
        prefix = company + '_'
        if company and publisher.startswith(prefix):
            domain = publisher[len(prefix):]
        if company and domain:
            exact_counts[(user_id, company, domain)] += 1

    alerts: list[dict[str, Any]] = []
    for notification in notifications:
        if str(notification.get('TITLE') or '') != ALERT_TITLE:
            continue
        company = str(notification.get('COMPANY') or '').strip()
        if company not in MGS_COMPANIES:
            continue
        try:
            notification_id = int(str(notification.get('ID') or ''))
        except Exception as exc:
            raise RuntimeError('token alert without numeric ID') from exc
        domain = str(notification.get('DOMAIN') or '').strip()
        created_at = str(notification.get('CREATED_AT') or '').strip()
        try:
            body = json.loads(notification.get('BODY') or '[]')
        except Exception as exc:
            raise RuntimeError(f'invalid token-alert BODY id={notification_id}') from exc
        if not isinstance(body, list) or not body:
            raise RuntimeError(f'empty token-alert BODY id={notification_id}')
        for item in body:
            if not isinstance(item, dict):
                raise RuntimeError(f'non-object token-alert BODY id={notification_id}')
            user_id = str(item.get('user_id') or '').strip()
            exact = exact_counts.get((user_id, company, domain), 0)
            page_count = exact if exact else user_counts.get(user_id, 0)
            alerts.append({
                'notification_id': notification_id,
                'created_at': created_at,
                'company': company,
                'domain': domain,
                'user_id': user_id,
                'user_name': str(item.get('user_name') or '').strip(),
                'user_email': str(item.get('user_email') or '').strip(),
                'segurador_id': str(item.get('segurador_id') or '').strip(),
                'segurador_name': str(item.get('segurador_name') or '').strip(),
                'source': str(item.get('source') or 'unknown').strip(),
                'pages': int(page_count),
                'page_count_scope': 'company-domain-user' if exact else 'user-fallback',
            })
    alerts.sort(key=lambda row: (row['notification_id'], row['user_id']))
    return alerts


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def latest_batch(alerts: list[dict[str, Any]], minutes: int = 5) -> list[dict[str, Any]]:
    if not alerts:
        return []
    latest = max(parse_dt(row['created_at']) for row in alerts)
    cutoff = latest - timedelta(minutes=minutes)
    return [row for row in alerts if parse_dt(row['created_at']) >= cutoff]


def fingerprint(alerts: list[dict[str, Any]], canary: bool) -> str:
    material = json.dumps({
        'canary': canary,
        'rows': [(row['notification_id'], row['user_id'], row['pages']) for row in alerts],
    }, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(material.encode()).hexdigest()[:16]


def build_payloads(alerts: list[dict[str, Any]], canary: bool = False) -> list[dict[str, Any]]:
    if not alerts:
        return []
    payloads: list[dict[str, Any]] = []
    for start in range(0, len(alerts), MAX_EMBEDS):
        chunk = alerts[start:start + MAX_EMBEDS]
        embeds = []
        for row in chunk:
            title_prefix = 'CANÁRIO — ' if canary else ''
            site = (row['domain'] or 'SITE DESCONHECIDO').upper()
            user = row['user_email'] or row['user_name'] or f"ID {row['user_id']}"
            segurador = row['segurador_name'] or f"ID {row['segurador_id']}"
            embeds.append({
                'title': f"{title_prefix}{site} — Token Messenger inválido"[:256],
                'color': 15158332,
                'fields': [
                    {'name': 'User', 'value': user[:1024] or '—', 'inline': False},
                    {'name': 'Segurador', 'value': segurador[:1024] or '—', 'inline': True},
                    {'name': 'Páginas', 'value': str(row['pages']), 'inline': True},
                ],
                'footer': {'text': f"SB #{row['notification_id']} · {row['source']}"},
                'timestamp': row['created_at'],
            })
        payloads.append({'content': '', 'allowed_mentions': {'parse': []}, 'embeds': embeds})
    return payloads


async def fetch_live() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not SB_STATE.exists():
        raise RuntimeError(f'SB storage state missing: {SB_STATE}')
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        try:
            context = await browser.new_context(storage_state=str(SB_STATE), viewport={'width': 1600, 'height': 1000}, user_agent=UA)
            page = await context.new_page()
            captured: dict[str, str] = {}

            async def on_request(request):
                if 'api.jbfdigital.com.br' in request.url:
                    captured.update(await request.all_headers())

            page.on('request', on_request)
            await page.goto(APP_URL, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            body = await page.locator('body').inner_text()
            if 'BotGuardError' in body:
                raise RuntimeError('Smart Bidding BotGuardError')
            headers = {key: value for key, value in captured.items() if key.lower() in {'authorization', 'accept', 'content-type'}}
            if not headers.get('authorization'):
                raise RuntimeError('Smart Bidding authorization header not captured')
            headers.update({'origin': 'https://app.smartbiddingdigital.com', 'referer': 'https://app.smartbiddingdigital.com/'})

            notification_response = await context.request.get(API_BASE + '/notification', headers=headers, timeout=120000)
            notifications = await notification_response.json()
            if notification_response.status != 200 or not isinstance(notifications, list):
                raise RuntimeError(f'bad notification response status={notification_response.status}')

            company_response = await context.request.get(API_BASE + '/company', headers=headers, timeout=120000)
            companies = await company_response.json()
            if company_response.status != 200 or not isinstance(companies, list):
                raise RuntimeError(f'bad company response status={company_response.status}')
            publishers: list[str] = []
            for company in companies:
                for publisher in company.get('publishers') or []:
                    publisher_id = str(publisher.get('publisherId') or '')
                    if publisher.get('active') and publisher_id:
                        publishers.append(publisher_id)
            publishers = sorted(set(publishers))
            if not publishers:
                raise RuntimeError('Smart Bidding active publisher scope is empty')
            query = '&'.join('companies[]=' + urllib.parse.quote(value) for value in publishers) + '&source=Messenger'
            pages_response = await context.request.get(API_BASE + '/campaigns/Messenger?' + query, headers=headers, timeout=120000)
            pages = await pages_response.json()
            if pages_response.status != 200 or not isinstance(pages, list):
                raise RuntimeError(f'bad Messenger pages response status={pages_response.status}')
            return notifications, pages
        finally:
            await browser.close()


def discord_request(method: str, path: str, payload: dict[str, Any] | None = None, allow_404: bool = False) -> tuple[int, Any]:
    load_env()
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('DISCORD_BOT_TOKEN unavailable')
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Authorization': 'Bot ' + token, 'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus-SB-Token-Monitor/1.0'}
    url = 'https://discord.com/api/v10' + path
    for attempt in range(4):
        request = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode(errors='ignore')
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors='ignore')
            if exc.code == 429 and attempt < 3:
                try:
                    delay = float(json.loads(raw).get('retry_after', 1.0)) + 0.15
                except Exception:
                    delay = 1.15
                time.sleep(delay)
                continue
            if allow_404 and exc.code == 404:
                return 404, None
            raise RuntimeError(f'Discord HTTP {exc.code} {method} {path}') from exc
    raise RuntimeError('Discord retry loop exhausted')


def verify_message(channel_id: str, message_id: str, payload: dict[str, Any]) -> None:
    read_status, readback = discord_request('GET', f'/channels/{channel_id}/messages/{message_id}')
    if read_status != 200 or not isinstance(readback, dict):
        raise RuntimeError(f'Discord readback failed status={read_status}')
    if str(readback.get('channel_id')) != str(channel_id):
        raise RuntimeError('Discord channel readback mismatch')
    if (readback.get('content') or '') != (payload.get('content') or ''):
        raise RuntimeError('Discord content readback mismatch')
    actual_mentions = sorted(str(row.get('id')) for row in (readback.get('mentions') or []))
    expected_mentions = sorted(str(value) for value in ((payload.get('allowed_mentions') or {}).get('users') or []))
    if actual_mentions != expected_mentions:
        raise RuntimeError('Discord mention readback mismatch')
    if len(readback.get('embeds') or []) != len(payload.get('embeds') or []):
        raise RuntimeError('Discord embed readback mismatch')


def post_and_verify(channel_id: str, payload: dict[str, Any]) -> str:
    status, message = discord_request('POST', f'/channels/{channel_id}/messages', payload)
    if status not in (200, 201) or not isinstance(message, dict):
        raise RuntimeError(f'Discord POST failed status={status}')
    message_id = str(message.get('id') or '')
    if not message_id:
        raise RuntimeError('Discord POST returned no message ID')
    verify_message(channel_id, message_id, payload)
    return message_id


def deliver_payloads(channel_id: str, payloads: list[dict[str, Any]], dry_run: bool) -> list[str]:
    if dry_run:
        print(json.dumps({'dry_run': True, 'channel_id': channel_id, 'payloads': payloads}, ensure_ascii=False))
        return []
    return [post_and_verify(channel_id, payload) for payload in payloads]


def mark_success(state: dict[str, Any], alerts: list[dict[str, Any]], message_ids: list[str]) -> None:
    ids = sorted({int(row['notification_id']) for row in alerts})
    delivered = [int(value) for value in state.get('delivered_ids') or []]
    delivered = sorted(set(delivered).union(ids))[-MAX_DELIVERED_IDS:]
    state.update({
        'last_check': now_iso(),
        'last_seen_id': max([int(state.get('last_seen_id') or 0), *ids]),
        'delivered_ids': delivered,
        'pending': None,
        'last_delivery': {'at': now_iso(), 'notification_ids': ids, 'message_ids': message_ids},
        'consecutive_failures': 0,
        'last_error': None,
        'failure_alert_sent_for': 0,
    })


def record_failure(path: Path, state: dict[str, Any] | None, error: Exception, dry_run: bool) -> None:
    state = state or initial_state()
    count = int(state.get('consecutive_failures') or 0) + 1
    state['last_check'] = now_iso()
    state['consecutive_failures'] = count
    state['last_error'] = {'at': now_iso(), 'type': type(error).__name__, 'message': str(error)[:500]}
    if not dry_run:
        save_state(path, state)
    if count >= 3 and int(state.get('failure_alert_sent_for') or 0) < count and not dry_run:
        payload = {
            'content': f'<@{RODOLFO_ID}> monitor de token Messenger falhando',
            'allowed_mentions': {'users': [RODOLFO_ID]},
            'embeds': [{
                'title': 'Monitor SB de token Messenger com falha',
                'color': 15158332,
                'fields': [
                    {'name': 'Falhas consecutivas', 'value': str(count), 'inline': True},
                    {'name': 'Erro', 'value': f"```text\n{str(error)[:700]}\n```", 'inline': False},
                    {'name': 'Ação', 'value': 'Intervenção automática do Zeus: validar sessão Smart Bidding, API e transporte Discord.', 'inline': False},
                ],
            }],
        }
        try:
            post_and_verify(INFRA_CHANNEL_ID, payload)
            state['failure_alert_sent_for'] = count
            save_state(path, state)
        except Exception:
            pass


async def run(args: argparse.Namespace) -> int:
    state_path = Path(args.state_path)
    state = load_state(state_path)
    if args.fixture:
        fixture = json.loads(Path(args.fixture).read_text(encoding='utf-8'))
        notifications = fixture.get('notifications') or []
        pages = fixture.get('pages') or []
    else:
        notifications, pages = await fetch_live()
    alerts = normalize_alerts(notifications, pages)
    max_id = max((int(row['notification_id']) for row in alerts), default=0)

    if args.test_alert:
        selected = latest_batch(alerts)
        if not selected:
            raise RuntimeError('no live MGS token alert available for canary')
        payloads = build_payloads(selected, canary=True)
        message_ids = deliver_payloads(args.channel_id, payloads, args.dry_run)
        print(json.dumps({'ok': True, 'mode': 'test-alert', 'alerts': len(selected), 'payloads': len(payloads), 'message_ids': message_ids, 'mentions': 0}, ensure_ascii=False))
        return 0

    if args.baseline or state is None:
        baseline = state or initial_state()
        baseline.update({'last_check': now_iso(), 'last_seen_id': max_id, 'delivered_ids': [], 'pending': None, 'consecutive_failures': 0, 'last_error': None})
        if not args.dry_run:
            save_state(state_path, baseline)
        print(json.dumps({'ok': True, 'mode': 'baseline', 'last_seen_id': max_id, 'alerts_seen': len(alerts), 'state_written': not args.dry_run}, ensure_ascii=False))
        return 0

    pending = state.get('pending')
    if isinstance(pending, dict) and pending.get('notification_ids'):
        pending_ids = {int(value) for value in pending.get('notification_ids') or []}
        pending_alerts = [row for row in alerts if int(row['notification_id']) in pending_ids]
        present_ids = {int(row['notification_id']) for row in pending_alerts}
        if present_ids != pending_ids:
            raise RuntimeError('pending SB notifications are no longer available; refusing cursor advance')
        pending_payloads = build_payloads(pending_alerts, canary=False)
        existing_ids = [str(value) for value in pending.get('message_ids') or []]
        if len(existing_ids) > len(pending_payloads):
            raise RuntimeError('pending state has more Discord messages than payload chunks')
        for index, message_id in enumerate(existing_ids):
            verify_message(args.channel_id, message_id, pending_payloads[index])
        if args.dry_run:
            print(json.dumps({'ok': True, 'mode': 'pending-dry-run', 'pending_ids': sorted(pending_ids), 'verified_message_ids': existing_ids, 'remaining_payloads': len(pending_payloads) - len(existing_ids)}, ensure_ascii=False))
            return 0
        for payload in pending_payloads[len(existing_ids):]:
            existing_ids.append(post_and_verify(args.channel_id, payload))
            state['pending']['message_ids'] = existing_ids
            save_state(state_path, state)
        mark_success(state, pending_alerts, existing_ids)
        save_state(state_path, state)
        print(json.dumps({'ok': True, 'mode': 'pending-reconciled', 'notification_ids': sorted(pending_ids), 'message_ids': existing_ids, 'mentions': 0}, ensure_ascii=False))
        return 0

    delivered = {int(value) for value in state.get('delivered_ids') or []}
    last_seen = int(state.get('last_seen_id') or 0)
    selected = [row for row in alerts if int(row['notification_id']) > last_seen and int(row['notification_id']) not in delivered]
    if not selected:
        state.update({'last_check': now_iso(), 'consecutive_failures': 0, 'last_error': None})
        if not args.dry_run:
            save_state(state_path, state)
        print(json.dumps({'ok': True, 'mode': 'noop', 'last_seen_id': last_seen, 'alerts_seen': len(alerts), 'new_alerts': 0}, ensure_ascii=False))
        return 0

    payloads = build_payloads(selected, canary=False)
    ids = sorted({int(row['notification_id']) for row in selected})
    if args.dry_run:
        deliver_payloads(args.channel_id, payloads, True)
        print(json.dumps({'ok': True, 'mode': 'dry-run', 'new_alerts': len(selected), 'notification_ids': ids, 'payloads': len(payloads), 'message_ids': [], 'mentions': 0}, ensure_ascii=False))
        return 0
    state['pending'] = {'created_at': now_iso(), 'notification_ids': ids, 'fingerprint': fingerprint(selected, False), 'message_ids': []}
    save_state(state_path, state)
    message_ids: list[str] = []
    for payload in payloads:
        message_ids.append(post_and_verify(args.channel_id, payload))
        state['pending']['message_ids'] = message_ids
        save_state(state_path, state)
    mark_success(state, selected, message_ids)
    save_state(state_path, state)
    print(json.dumps({'ok': True, 'mode': 'apply', 'new_alerts': len(selected), 'notification_ids': ids, 'payloads': len(payloads), 'message_ids': message_ids, 'mentions': 0}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Compatibility marker; normal mode applies unless --dry-run.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--test-alert', action='store_true')
    parser.add_argument('--fixture')
    parser.add_argument('--state-path', default=str(STATE_PATH))
    parser.add_argument('--channel-id', default=TARGET_CHANNEL_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = None
    try:
        state = load_state(Path(args.state_path))
        return asyncio.run(run(args))
    except Exception as error:
        record_failure(Path(args.state_path), state, error, args.dry_run or bool(args.fixture))
        print(json.dumps({'ok': False, 'error': type(error).__name__, 'detail': str(error)[:500]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
