#!/usr/bin/env python3
"""Keep 1-week Discord threads from auto-archiving.

Scans active Discord threads visible to MGS agent bot tokens and posts a small
keepalive message once per thread/archive cycle when a 1-week thread has <= 24h
before auto-archive.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_DIR = pathlib.Path('/root/mgs-agent')
PROFILES_DIR = pathlib.Path('/root/.hermes/profiles')
STATE_PATH = BASE_DIR / 'data' / 'discord-thread-archive-warning-state.json'
LOG_PREFIX = 'monitor-discord-thread-archive-warnings'

GUILD_ID = '1185714635991679006'  # MGS Digital Corp
ZEUS_CHANNEL_ID = '1496267442899521627'
RODOLFO_ID = '344196393512075265'
AGENTS = ('zeus', 'atena', 'ares', 'hera')
AUTO_ARCHIVE_1_WEEK_MINUTES = 10080
WARN_WINDOW_SECONDS = 24 * 3600
USER_AGENT = 'MGS-thread-archive-warning-monitor/1.0'
DISCORD_EPOCH_MS = 1420070400000
KEEPALIVE_MESSAGE = 'Mantendo a thread ativa para não arquivar automaticamente.'


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def parse_discord_ts(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    normalized = value.replace('Z', '+00:00')
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def snowflake_ts(snowflake: str | None) -> dt.datetime | None:
    if not snowflake or not str(snowflake).isdigit():
        return None
    try:
        ms = (int(snowflake) >> 22) + DISCORD_EPOCH_MS
        return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc)
    except Exception:
        return None


def load_env_token(profile: str) -> str | None:
    path = PROFILES_DIR / profile / '.env'
    if not path.exists():
        return None
    token = None
    for raw_line in path.read_text(errors='ignore').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        if key.strip() == 'DISCORD_BOT_TOKEN':
            token = val.strip().strip('"').strip("'")
    return token or None


def api_json(token: str, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    url = 'https://discord.com/api/v10' + endpoint
    data = None
    headers = {'Authorization': f'Bot {token}', 'User-Agent': USER_AGENT}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            if body:
                return resp.status, json.loads(body.decode('utf-8'))
            return resp.status, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {'raw': body[:300]}
        return exc.code, parsed


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {'alerts': {}, 'last_run': None}
    try:
        data = json.loads(STATE_PATH.read_text())
    except Exception:
        return {'alerts': {}, 'last_run': None, 'state_error': 'unreadable'}
    if not isinstance(data, dict):
        return {'alerts': {}, 'last_run': None, 'state_error': 'invalid'}
    data.setdefault('alerts', {})
    return data


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    tmp.replace(STATE_PATH)


def thread_link(thread_id: str) -> str:
    return f'https://discord.com/channels/{GUILD_ID}/{thread_id}'


def collect_threads(now: dt.datetime) -> tuple[dict[str, dict[str, Any]], list[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for agent in AGENTS:
        token = load_env_token(agent)
        if not token:
            errors.append(f'{agent}: token ausente')
            continue
        status, data = api_json(token, 'GET', f'/guilds/{GUILD_ID}/threads/active')
        if status != 200:
            code = data.get('code') if isinstance(data, dict) else None
            msg = data.get('message') if isinstance(data, dict) else data
            errors.append(f'{agent}: HTTP {status} {code or ""} {msg}')
            continue
        for thread in (data or {}).get('threads', []):
            meta = thread.get('thread_metadata') or {}
            if meta.get('archived'):
                continue
            auto_archive_minutes = int(meta.get('auto_archive_duration') or 0)
            if auto_archive_minutes != AUTO_ARCHIVE_1_WEEK_MINUTES:
                continue
            thread_id = str(thread.get('id'))
            archive_ts = parse_discord_ts(meta.get('archive_timestamp'))
            last_message_ts = snowflake_ts(str(thread.get('last_message_id') or ''))
            activity_ts = max([t for t in (archive_ts, last_message_ts) if t], default=None)
            if not activity_ts:
                continue
            archive_at = activity_ts + dt.timedelta(minutes=auto_archive_minutes)
            remaining = (archive_at - now).total_seconds()
            if remaining <= 0 or remaining > WARN_WINDOW_SECONDS:
                continue
            item = by_id.setdefault(thread_id, {
                'id': thread_id,
                'name': thread.get('name') or '(sem título)',
                'parent_id': str(thread.get('parent_id') or ''),
                'activity_at': activity_ts,
                'archive_at': archive_at,
                'remaining_seconds': remaining,
                'auto_archive_minutes': auto_archive_minutes,
                'agents': set(),
            })
            item['agents'].add(agent)
            if archive_at < item['archive_at']:
                item['archive_at'] = archive_at
                item['activity_at'] = activity_ts
                item['remaining_seconds'] = remaining
    return by_id, errors


def format_alert(items: list[dict[str, Any]], errors: list[str], now: dt.datetime) -> str:
    lines = [
        f'<@{RODOLFO_ID}>',
        '',
        'Threads que vão ficar ocultas em até 24h:',
        '',
    ]
    for item in sorted(items, key=lambda x: x['archive_at']):
        hours = max(0, int(round(item['remaining_seconds'] / 3600)))
        agents = ','.join(sorted(item['agents']))
        name = re.sub(r'\s+', ' ', str(item['name'])).strip()
        if len(name) > 80:
            name = name[:77] + '...'
        lines.append(f'- {name} — ~{hours}h restantes — agentes: {agents}')
        lines.append(f'  {thread_link(item["id"])}')
    if errors:
        lines.extend(['', 'Observação: alguns agentes tiveram erro de leitura:'])
        for err in errors[:4]:
            lines.append(f'- {err[:160]}')
    lines.append('')
    lines.append(f'Check: {iso_z(now)}')
    return '\n'.join(lines)


def format_failure_alert(failed: list[dict[str, Any]], errors: list[str], now: dt.datetime) -> str:
    lines = [
        f'<@{RODOLFO_ID}>',
        '',
        'Falhei ao manter vivas algumas threads que vão arquivar em até 24h:',
        '',
    ]
    for item in failed[:10]:
        name = re.sub(r'\s+', ' ', str(item.get('name') or '(sem título)')).strip()
        if len(name) > 80:
            name = name[:77] + '...'
        detail = str(item.get('post_error') or item.get('post_status') or 'erro desconhecido')[:180]
        lines.append(f'- {name} — {detail}')
        lines.append(f'  {thread_link(str(item["id"]))}')
    if errors:
        lines.extend(['', 'Erros de leitura adicionais:'])
        for err in errors[:4]:
            lines.append(f'- {err[:160]}')
    lines.append('')
    lines.append(f'Check: {iso_z(now)}')
    return '\n'.join(lines)


def post_zeus(message: str) -> tuple[int, Any]:
    token = load_env_token('zeus')
    if not token:
        return 0, {'message': 'Zeus token ausente'}
    return api_json(token, 'POST', f'/channels/{ZEUS_CHANNEL_ID}/messages', {'content': message[:1900]})


def post_thread_keepalive(item: dict[str, Any]) -> tuple[int, Any, str | None]:
    """Post a keepalive in the target thread using a bot that can see it."""
    seen_by = set(item.get('agents') or [])
    candidates = [agent for agent in AGENTS if agent in seen_by]
    if 'zeus' not in candidates:
        candidates.append('zeus')

    last_status = 0
    last_data: Any = {'message': 'sem token candidato'}
    for agent in candidates:
        token = load_env_token(agent)
        if not token:
            last_status = 0
            last_data = {'message': f'{agent}: token ausente'}
            continue
        status, data = api_json(
            token,
            'POST',
            f'/channels/{item["id"]}/messages',
            {'content': KEEPALIVE_MESSAGE},
        )
        if status in (200, 201):
            return status, data, agent
        last_status, last_data = status, data
    return last_status, last_data, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Do not post or persist alert state')
    parser.add_argument('--json', action='store_true', help='Print machine-readable summary')
    parser.add_argument('--force-alert', action='store_true', help='Ignore state and alert again')
    args = parser.parse_args()

    now = now_utc()
    state = load_state()
    threads, errors = collect_threads(now)
    alerts = state.setdefault('alerts', {})
    pending: list[dict[str, Any]] = []
    for item in threads.values():
        archive_key = iso_z(item['archive_at'])
        key = f'{item["id"]}:{archive_key}'
        if args.force_alert or key not in alerts:
            item['state_key'] = key
            pending.append(item)

    posted = False
    post_status: int | None = None
    post_error: Any = None
    bumped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    if pending:
        if args.dry_run:
            print(format_alert(pending, errors, now))
            print('')
            print(f'DRY-RUN: postaria em {len(pending)} thread(s): {KEEPALIVE_MESSAGE}')
        else:
            for item in pending:
                status, data, posted_by = post_thread_keepalive(item)
                if status in (200, 201):
                    posted = True
                    bumped.append(item)
                    alerts[item['state_key']] = {
                        'thread_id': item['id'],
                        'name': item['name'],
                        'archive_at': iso_z(item['archive_at']),
                        'bumped_at': iso_z(now),
                        'posted_by': posted_by,
                        'message_id': str((data or {}).get('id') or ''),
                        'agents': sorted(item['agents']),
                    }
                else:
                    item['post_status'] = status
                    item['post_error'] = data
                    failed.append(item)
            if failed:
                post_status, data = post_zeus(format_failure_alert(failed, errors, now))
                if post_status not in (200, 201):
                    post_error = data
                state['last_run'] = iso_z(now)
                state['last_seen_candidates'] = len(threads)
                state['last_pending_alerts'] = len(pending)
                state['last_bumped'] = len(bumped)
                state['last_failed_bumps'] = len(failed)
                state['last_errors'] = errors[-10:]
                save_state(state)
                print(f'{LOG_PREFIX}: keepalive failed count={len(failed)} zeus_alert_status={post_status} error={post_error}', file=sys.stderr)
                return 2
    # prune old alert keys after 30 days
    cutoff = now - dt.timedelta(days=30)
    for key, val in list(alerts.items()):
        alerted_at = parse_discord_ts(str((val or {}).get('alerted_at') or (val or {}).get('bumped_at')))
        if alerted_at and alerted_at < cutoff:
            alerts.pop(key, None)
    state['last_run'] = iso_z(now)
    state['last_seen_candidates'] = len(threads)
    state['last_pending_alerts'] = len(pending)
    state['last_bumped'] = len(bumped)
    state['last_failed_bumps'] = len(failed)
    state['last_errors'] = errors[-10:]
    if not args.dry_run:
        save_state(state)

    summary = {
        'ok': True,
        'dry_run': args.dry_run,
        'candidates': len(threads),
        'pending_alerts': len(pending),
        'bumped': len(bumped),
        'failed_bumps': len(failed),
        'posted': posted,
        'post_status': post_status,
        'errors': errors,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(f'{LOG_PREFIX}: OK candidates={len(threads)} pending_alerts={len(pending)} bumped={len(bumped)} failed_bumps={len(failed)} errors={len(errors)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
