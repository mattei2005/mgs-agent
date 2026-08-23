#!/usr/bin/env python3
"""Daily Smart Bidding restricted-pages operational summary.

Read-only data path:
- active bot users from the canonical migration Sheet;
- current Smart Bidding Messenger rows for the full MGS company scope;
- global page ignore list;
- only current restricted rows, aggregated by exit date and site.

The script never mutates Smart Bidding. By default it posts the summary to the
MGS #paginas-restritas channel. Use --no-post for a live read-only preview.
"""

import argparse
import asyncio
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
DAILY_AUDIT_PATH = BASE / 'scripts/dtr-sb-daily-match-audit.py'
TARGET_CHANNEL_ID = '1522442220903337984'
NY = ZoneInfo('America/New_York')
DISCORD_LIMIT = 2000


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if not spec or not spec.loader:
        raise RuntimeError(f'cannot load module: {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def truncate(value, limit):
    value = str(value or '')
    return value if len(value) <= limit else value[: limit - 1] + '…'


def build_snapshot(raw_rows, active_users, daily, sync, tday=None):
    fb_ignore, bot_pg_ignore = daily.load_ignore_keys()
    active_users = {daily.low(user) for user in active_users if daily.low(user)}
    tday = tday or datetime.now(NY).date().isoformat()
    if not active_users:
        raise RuntimeError('active-user scope is empty; refusing to publish an empty summary')

    scoped = []
    ignored = 0
    for raw in raw_rows:
        bot_user = daily.low(raw.get('USER_LOGIN') or raw.get('LOGIN'))
        if bot_user not in active_users:
            continue
        public = daily.sb_public_from_raw(raw)
        public['_raw'] = raw
        if daily.ignored_page(public, fb_ignore, bot_pg_ignore):
            ignored += 1
            continue
        scoped.append(public)

    if not scoped:
        raise RuntimeError('Smart Bidding active-user scope is empty; refusing to publish')

    # Keep the summary aligned with the canonical production definition:
    # a restriction is active through its exit date (inclusive), and expired
    # dates must not reappear merely because RESTRICTED_UNTIL is still filled.
    restricted = [
        row
        for row in scoped
        if sync.active_restricted(row.get('_raw') or {}, tday)
    ]
    broadcast = [row for row in restricted if daily.low(row.get('status')) == 'broadcast']
    on_hold = [row for row in restricted if daily.low(row.get('status')) == 'on-hold']

    grouped = {}
    for row in broadcast:
        exit_date = daily.norm(row.get('restricted_until'))[:10] or '?'
        bucket = grouped.setdefault(exit_date, {'pages': 0, 'sites': set()})
        bucket['pages'] += 1
        for site in sync.derive_sites(row.get('_raw') or {}).split(','):
            site = site.strip()
            if site and site != '?':
                bucket['sites'].add(site)

    return {
        'sb_rows_scoped': len(scoped),
        'globally_ignored_rows': ignored,
        'restricted_total': len(restricted),
        'broadcast_restricted': len(broadcast),
        'on_hold_ignored': len(on_hold),
        'other_status_restricted': len(restricted) - len(broadcast) - len(on_hold),
        'dates': {
            date: {
                'pages': grouped[date]['pages'],
                'sites': sorted(grouped[date]['sites']),
            }
            for date in sorted(grouped)
        },
    }


def table_lines(snapshot):
    lines = [
        'Data saída   Páginas  Sites',
        '-----------  -------  --------------------------------------------------',
    ]
    for exit_date, item in snapshot['dates'].items():
        sites = ', '.join(item['sites']) or '?'
        lines.append(f"{exit_date:<11}  {item['pages']:>7}  {truncate(sites, 50)}")
    return lines


def render_blocks(snapshot, now=None):
    now = now or datetime.now(NY)
    common = [
        '📊 PÁGINAS RESTRITAS — RESUMO OPERACIONAL',
        f"Atualizado em: {now.strftime('%Y-%m-%d %H:%M %Z')}",
        'Escopo: somente Status SB = Broadcast',
        '',
        f"Broadcast restritas: {snapshot['broadcast_restricted']}",
        f"On-hold ignoradas: {snapshot['on_hold_ignored']}",
        '',
    ]
    header = table_lines({'dates': {}})
    rows = table_lines(snapshot)[2:]

    def wrapped(lines):
        return '```\n' + '\n'.join(lines) + '\n```'

    first = common + header
    blocks = []
    current = first[:]
    for row in rows:
        if len(wrapped(current + [row])) <= DISCORD_LIMIT:
            current.append(row)
            continue
        if current == first:
            raise RuntimeError('one summary row exceeds Discord message limit')
        blocks.append(wrapped(current))
        current = [
            '📊 PÁGINAS RESTRITAS — RESUMO OPERACIONAL (continuação)',
            f"Atualizado em: {now.strftime('%Y-%m-%d %H:%M %Z')}",
            '',
            *header,
            row,
        ]
    blocks.append(wrapped(current))

    if any(len(block) > DISCORD_LIMIT for block in blocks):
        raise RuntimeError('rendered Discord block exceeds 2,000 characters')
    return blocks


def discord_http_status(result):
    """Normalize the shared Discord poster's legacy and current return shapes."""
    if isinstance(result, int):
        return result
    if isinstance(result, dict):
        return result.get('status')
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-post', '--dry-run', action='store_true', dest='no_post')
    args = parser.parse_args()

    daily = load_module('dtr_sb_daily_match_audit', DAILY_AUDIT_PATH)
    audit = daily.load_audit_mod()
    sync = audit.sync
    if sync.TARGET_CHANNEL_ID != TARGET_CHANNEL_ID:
        raise RuntimeError(
            f'target channel drift: sync={sync.TARGET_CHANNEL_ID} expected={TARGET_CHANNEL_ID}'
        )

    sheet_rows = sync.sheet_rows()
    active_users = set(sync.active_users_from_sheet(sheet_rows))
    publishers, raw_rows = asyncio.run(audit.get_sb())
    snapshot = build_snapshot(raw_rows, active_users, daily, sync)
    blocks = render_blocks(snapshot)

    post_statuses = []
    if args.no_post:
        for block in blocks:
            print(block)
    else:
        for block in blocks:
            post_statuses.append(sync.post_discord(block))
        if not post_statuses or any(
            discord_http_status(result) not in (200, 201)
            for result in post_statuses
        ):
            raise RuntimeError(f'Discord delivery failed: statuses={post_statuses}')

    result = {
        'ok': True,
        'mode': 'no-post' if args.no_post else 'posted',
        'channel_id': TARGET_CHANNEL_ID,
        'publishers': len(publishers),
        'active_users': len(active_users),
        'blocks': len(blocks),
        'block_lengths': [len(block) for block in blocks],
        'post_statuses': post_statuses,
        **snapshot,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
