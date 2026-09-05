#!/usr/bin/env python3
"""Detect externally applied Smart Bidding page-restriction transitions.

This monitor is deliberately SB-first and read-only for Smart Bidding. It catches
new or renewed active restrictions even when Iris or another writer applied them
before the DTR -> SB sync. DTR remains the later enrichment/source for error code
and exact time; this monitor never attributes the writer without direct evidence.
"""

import argparse
import asyncio
import copy
import importlib.util
import json
import os
import tempfile
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
DAILY_PATH = BASE / 'scripts/dtr-sb-daily-match-audit.py'
REVENUE_PATH = BASE / 'scripts/sync-sb-messenger-revenue-sheet.py'
STATE_PATH = BASE / 'data/sb-restricted-transition-state.json'
TARGET_CHANNEL_ID = '1522442220903337984'
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1sIBGA_CHMtHF1mWgsvjUHfEkvuF3pb9VC5oeg06tHsI/edit?gid=0#gid=0'
NY = ZoneInfo('America/New_York')
DISCORD_LIMIT = 1900
EXCLUDED_STATUSES = {'on-hold', 'blocked'}
HISTORY_COVERAGE_START = '2026-07-15T14:38:01-04:00'
SB_FETCH_RETRY_ATTEMPTS = 3
SB_FETCH_RETRY_DELAYS = (5, 10)


def now_iso():
    return datetime.now(NY).isoformat(timespec='seconds')


def json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f'Object of type {value.__class__.__name__} is not JSON serializable')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load module: {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def transient_sb_error(exc):
    text = f'{type(exc).__name__}: {exc}'.lower()
    transient_markers = (
        'timeout',
        'timed out',
        'bad response 429',
        'bad response 500',
        'bad response 502',
        'bad response 503',
        'bad response 504',
    )
    return any(marker in text for marker in transient_markers)


async def get_sb_with_retry(getter, attempts=SB_FETCH_RETRY_ATTEMPTS, sleep_fn=asyncio.sleep):
    """Retry only transient SB/API failures; preserve fail-closed scope checks."""
    attempts = max(1, int(attempts))
    for attempt in range(1, attempts + 1):
        try:
            return await getter()
        except Exception as exc:
            if attempt >= attempts or not transient_sb_error(exc):
                raise
            delay = SB_FETCH_RETRY_DELAYS[min(attempt - 1, len(SB_FETCH_RETRY_DELAYS) - 1)]
            print(
                f'WARN transient SB fetch failure attempt={attempt}/{attempts}; '
                f'retrying_in={delay}s; error={type(exc).__name__}: {exc}',
                flush=True,
            )
            await sleep_fn(delay)
    raise RuntimeError('SB fetch retry loop ended without result')


def stable_key(row):
    bot = str(row.get('bot_user') or '').strip().lower()
    page_id = str(row.get('page_id') or '').strip()
    fb_page_id = str(row.get('fb_page_id') or '').strip()
    if bot and page_id:
        return f'bot-page:{bot}|{page_id}'
    if fb_page_id:
        return f'fb:{fb_page_id}'
    raise RuntimeError(f'restricted row without stable identity: {row!r}')


def public_row(raw, daily, sync):
    public = daily.sb_public_from_raw(raw)
    public.update({
        'page_name': daily.norm(raw.get('PAGE_NAME')),
        'profile_name': daily.derive_segurador(raw) if hasattr(daily, 'derive_segurador') else daily.norm(raw.get('PROFILE_NAME')),
        'bot_user': daily.low(raw.get('USER_LOGIN') or raw.get('LOGIN')),
        'page_id': daily.norm(raw.get('PAGE_ID')),
        'fb_page_id': daily.norm(raw.get('FB_PAGE_ID')),
        'status': daily.norm(raw.get('STATUS')),
        'restricted_until': daily.norm(raw.get('RESTRICTED_UNTIL'))[:10],
        'utm_campaign': daily.norm(raw.get('UTM_CAMPAIGN')),
        'sites': sync.derive_sites(raw),
    })
    return public


def build_snapshot(raw_rows, active_users, daily, sync, tday=None):
    tday = tday or datetime.now(NY).date().isoformat()
    active_users = {daily.low(user) for user in active_users if daily.low(user)}
    if not active_users:
        raise RuntimeError('active-user scope is empty; refusing to monitor')
    fb_ignore, bot_pg_ignore = daily.load_ignore_keys()
    snapshot = {}
    counts = Counter()
    for raw in raw_rows:
        bot_user = daily.low(raw.get('USER_LOGIN') or raw.get('LOGIN'))
        if bot_user not in active_users:
            continue
        counts['rows_scoped'] += 1
        row = public_row(raw, daily, sync)
        if daily.ignored_page(row, fb_ignore, bot_pg_ignore):
            counts['globally_ignored'] += 1
            continue
        if not sync.active_restricted(raw, tday):
            continue
        counts['active_restricted_all_statuses'] += 1
        status_low = daily.low(row.get('status'))
        counts[f'active_status_{status_low or "unknown"}'] += 1
        if status_low in EXCLUDED_STATUSES:
            counts[f'excluded_status_{status_low}'] += 1
            continue
        key = stable_key(row)
        if key in snapshot:
            raise RuntimeError(f'duplicate restricted-page identity in live SB: {key}')
        snapshot[key] = row
    counts['monitored_active'] = len(snapshot)
    return snapshot, dict(counts)


def snapshot_from_report_sheet(sync):
    token = sync.google_access_token()
    tab = getattr(sync, 'REPORT_TOTAL_TAB', 'Paginas Totais')
    values = sync.read_report_datasets(token, [tab]).get(tab) or []
    if not values:
        raise RuntimeError(f'{tab} report sheet is empty; refusing baseline reconciliation')
    headers = values[0]
    snapshot = {}
    for values_row in values[1:]:
        old = {
            header: (values_row[index] if index < len(values_row) else '')
            for index, header in enumerate(headers)
        }
        row = {
            'page_name': old.get('nome da pagina', ''),
            'profile_name': old.get('segurador', ''),
            'bot_user': str(old.get('bot user', '')).strip().lower(),
            'page_id': str(old.get('page id', '')).strip(),
            'fb_page_id': str(old.get('fb page id', '')).strip(),
            'status': old.get('status sb', 'Broadcast'),
            'restricted_until': str(old.get('data saida', ''))[:10],
            'sites': old.get('sites', ''),
        }
        key = stable_key(row)
        if key in snapshot:
            raise RuntimeError(f'duplicate identity in {tab} report sheet: {key}')
        snapshot[key] = row
    return snapshot


def report_row(row):
    return {
        'nome da pagina': row.get('page_name', ''),
        'fb page id': row.get('fb_page_id', ''),
        'page id': row.get('page_id', ''),
        'bot user': row.get('bot_user', ''),
        'segurador': row.get('profile_name', ''),
        'sites': row.get('sites', ''),
        'status sb': row.get('status', ''),
        'codigos': '',
        'data saida': row.get('restricted_until', ''),
    }


def history_public_row(row):
    """Normalize either a live snapshot row or a report-Sheet row."""
    return {
        'page_name': row.get('page_name') or row.get('nome da pagina') or '',
        'profile_name': row.get('profile_name') or row.get('segurador') or '',
        'bot_user': str(row.get('bot_user') or row.get('bot user') or '').strip().lower(),
        'page_id': str(row.get('page_id') or row.get('page id') or '').strip(),
        'fb_page_id': str(row.get('fb_page_id') or row.get('fb page id') or '').strip(),
        'sites': row.get('sites') or '',
        'status': row.get('status') or row.get('status sb') or '',
        'restricted_until': str(row.get('restricted_until') or row.get('data saida') or '')[:10],
    }


def update_history(history, transitions, confirmed_exits, current, event_at=None):
    """Update one-row-per-page cycle counters without inventing pre-monitor events."""
    event_at = event_at or now_iso()
    result = copy.deepcopy(history) if isinstance(history, dict) else {}
    result.setdefault('coverage_start', HISTORY_COVERAGE_START)
    result.setdefault('source', 'SB live transition monitor; exits require live inactive readback')
    pages = result.setdefault('pages', {})
    if not isinstance(pages, dict):
        raise RuntimeError('restriction history pages must be a mapping')

    def ensure(row):
        public = history_public_row(row)
        key = stable_key(public)
        record = pages.setdefault(key, {
            'entries_detected': 0,
            'exits_confirmed': 0,
            'renewals_detected': 0,
            'status_changes_detected': 0,
            'first_event_at': '',
            'last_entry_at': '',
            'last_exit_at': '',
            'last_renewal_at': '',
            'last_status_change_at': '',
            'currently_restricted': False,
            'current_restricted_until': '',
            'current_status': '',
        })
        for field in ('page_name', 'profile_name', 'bot_user', 'page_id', 'fb_page_id', 'sites'):
            if public.get(field):
                record[field] = public[field]
        if public.get('status'):
            record['last_known_status'] = public['status']
        if public.get('restricted_until'):
            record['last_known_restricted_until'] = public['restricted_until']
        return key, record, public

    for record in pages.values():
        if isinstance(record, dict):
            record['currently_restricted'] = False
            record['current_restricted_until'] = ''
            record['current_status'] = ''

    for item in transitions:
        _, record, public = ensure(item.get('after') or {})
        kind = str(item.get('kind') or '').lower()
        changed = {str(value).lower() for value in item.get('changed') or []}
        if kind == 'nova':
            record['entries_detected'] = int(record.get('entries_detected') or 0) + 1
            record['last_entry_at'] = event_at
        if 'data' in changed or kind.startswith('renovada'):
            record['renewals_detected'] = int(record.get('renewals_detected') or 0) + 1
            record['last_renewal_at'] = event_at
        if 'status' in changed or kind == 'status alterado':
            record['status_changes_detected'] = int(record.get('status_changes_detected') or 0) + 1
            record['last_status_change_at'] = event_at
        if not record.get('first_event_at'):
            record['first_event_at'] = event_at
        record['last_event_at'] = event_at
        record['last_known_status'] = public.get('status') or record.get('last_known_status', '')

    for row in confirmed_exits:
        _, record, _ = ensure(row)
        record['exits_confirmed'] = int(record.get('exits_confirmed') or 0) + 1
        record['last_exit_at'] = event_at
        if not record.get('first_event_at'):
            record['first_event_at'] = event_at
        record['last_event_at'] = event_at

    for row in current.values():
        _, record, public = ensure(row)
        record['currently_restricted'] = True
        record['current_restricted_until'] = public.get('restricted_until') or ''
        record['current_status'] = public.get('status') or ''

    result['updated_at'] = event_at
    result['page_count'] = len(pages)
    result['totals'] = {
        'entries_detected': sum(int(row.get('entries_detected') or 0) for row in pages.values()),
        'exits_confirmed': sum(int(row.get('exits_confirmed') or 0) for row in pages.values()),
        'renewals_detected': sum(int(row.get('renewals_detected') or 0) for row in pages.values()),
        'status_changes_detected': sum(int(row.get('status_changes_detected') or 0) for row in pages.values()),
        'currently_restricted': sum(1 for row in pages.values() if row.get('currently_restricted')),
    }
    return result


def history_sheet_rows(history):
    pages = (history or {}).get('pages') or {}
    coverage = (history or {}).get('coverage_start') or HISTORY_COVERAGE_START
    rows = []
    for record in pages.values():
        fb_page_id = str(record.get('fb_page_id') or '')
        rows.append({
            'link da pagina': f'https://facebook.com/{fb_page_id}' if fb_page_id else '',
            'nome da pagina': record.get('page_name', ''),
            'fb page id': fb_page_id,
            'page id': record.get('page_id', ''),
            'bot user': record.get('bot_user', ''),
            'segurador': record.get('profile_name', ''),
            'sites': record.get('sites', ''),
            'entradas detectadas': int(record.get('entries_detected') or 0),
            'saidas confirmadas': int(record.get('exits_confirmed') or 0),
            'renovacoes': int(record.get('renewals_detected') or 0),
            'mudancas de status': int(record.get('status_changes_detected') or 0),
            'estado atual': 'Restrita' if record.get('currently_restricted') else 'Fora das restritas monitoradas',
            'ultima entrada': record.get('last_entry_at', ''),
            'ultima saida': record.get('last_exit_at', ''),
            'saida prevista atual': record.get('current_restricted_until', ''),
            'cobertura desde': coverage,
        })
    rows.sort(key=lambda row: (
        -int(row['entradas detectadas']),
        -int(row['saidas confirmadas']),
        -int(row['renovacoes']),
        str(row['nome da pagina']).lower(),
        str(row['bot user']).lower(),
        str(row['page id']),
    ))
    return rows


def confirmed_resolutions(resolved, raw_rows, daily, sync, tday):
    live = {}
    for raw in raw_rows:
        try:
            key = stable_key(public_row(raw, daily, sync))
        except RuntimeError:
            continue
        live[key] = raw
    confirmed = []
    for old in resolved:
        current = live.get(stable_key(old))
        if not current:
            continue
        if daily.low(current.get('STATUS')) in EXCLUDED_STATUSES:
            continue
        if not sync.active_restricted(current, tday):
            confirmed.append(report_row(old))
    return confirmed


def compare_snapshots(previous, current):
    transitions = []
    for key in sorted(current):
        now = current[key]
        before = previous.get(key)
        if before is None:
            transitions.append({'kind': 'nova', 'key': key, 'before': None, 'after': now})
            continue
        changed = []
        if str(before.get('restricted_until') or '') != str(now.get('restricted_until') or ''):
            changed.append('data')
        if str(before.get('status') or '').lower() != str(now.get('status') or '').lower():
            changed.append('status')
        if changed:
            if changed == ['data']:
                kind = 'renovada'
            elif changed == ['status']:
                kind = 'status alterado'
            else:
                kind = 'renovada+status'
            transitions.append({
                'kind': kind,
                'key': key,
                'changed': changed,
                'before': before,
                'after': now,
            })
    resolved = [previous[key] for key in sorted(set(previous) - set(current))]
    return transitions, resolved


def load_state():
    if not STATE_PATH.exists():
        return None
    data = json.loads(STATE_PATH.read_text(encoding='utf-8'))
    active = data.get('active')
    if not isinstance(active, dict):
        raise RuntimeError('transition state has invalid active snapshot')
    return data


def save_state(snapshot, counts, transitions, resolved, source, history=None):
    state = {
        '_meta': {
            'description': 'Live SB restriction transitions independent of the writing agent.',
            'target_channel_id': TARGET_CHANNEL_ID,
            'scope': 'active migration-sheet users; global ignore; active restriction; excludes On-hold/Blocked',
        },
        'last_check': now_iso(),
        'baseline_source': source,
        'counts': counts,
        'last_transition_count': len(transitions),
        'last_resolved_count': len(resolved),
        'last_transitions': transitions,
        'active': snapshot,
    }
    if history is not None:
        state['history'] = history
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=STATE_PATH.name + '.', dir=str(STATE_PATH.parent))
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True, default=json_default)
        handle.write('\n')
    os.replace(tmp_name, STATE_PATH)
    return state


def truncate(value, limit):
    value = str(value or '')
    return value if len(value) <= limit else value[: limit - 1] + '…'


def transition_lines(transitions):
    header = 'Página             FB Page ID        Page ID  Bot user           Invest 7d     Rev. 7d       Status    Saída'
    divider = '------------------ ----------------- -------- ------------------ ------------- ------------- --------- ----------'
    lines = [header, divider]
    for item in transitions:
        row = item['after']
        lines.append(
            f"{truncate(row.get('page_name'),18):<18} "
            f"{truncate(row.get('fb_page_id'),17):<17} "
            f"{truncate(row.get('page_id'),8):<8} "
            f"{truncate(str(row.get('bot_user') or '').replace('@gmail.com',''),18):<18} "
            f"{truncate(row.get('investment_7d_brl') or '—',13):<13} "
            f"{truncate(row.get('revenue_7d_brl') or '—',13):<13} "
            f"{truncate(row.get('status'),9):<9} "
            f"{truncate(row.get('restricted_until'),10)}"
        )
    return lines


def render_blocks(transitions, counts, source_label, now=None):
    now = now or datetime.now(NY)
    common = [
        '🔴 PÁGINAS RESTRITAS — TRANSIÇÕES DETECTADAS NA SB',
        f"Atualizado em: {now.strftime('%Y-%m-%d %H:%M %Z')}",
        f'Comparação: {source_label}',
        '',
        f"Novas/renovadas/alteradas: {len(transitions)}",
        f"Broadcast ativas monitoradas: {counts.get('active_status_broadcast', 0)}",
        f"Campaign ativas monitoradas: {counts.get('active_status_campaign', 0)}",
        f"On-hold ignoradas: {counts.get('excluded_status_on-hold', 0)}",
        '',
    ]
    rows = transition_lines(transitions)

    def wrap(lines):
        return '```\n' + '\n'.join(lines) + '\n```'

    blocks = []
    current = common + rows[:2]
    sheet_suffix = f"\n\n**Planilha completa:** <{SHEET_URL}>"
    for row in rows[2:]:
        candidate = wrap(current + [row])
        if not blocks:
            candidate += sheet_suffix
        if len(candidate) <= DISCORD_LIMIT:
            current.append(row)
            continue
        completed = wrap(current)
        if not blocks:
            completed += sheet_suffix
        blocks.append(completed)
        current = [
            '🔴 PÁGINAS RESTRITAS — TRANSIÇÕES DETECTADAS NA SB (continuação)',
            f"Atualizado em: {now.strftime('%Y-%m-%d %H:%M %Z')}",
            '',
            *rows[:2],
            row,
        ]
    completed = wrap(current)
    if not blocks:
        completed += sheet_suffix
    blocks.append(completed)
    if any(len(block) > DISCORD_LIMIT for block in blocks):
        raise RuntimeError('transition alert block exceeds Discord 2,000-character limit')
    return blocks


def discord_status(result):
    if isinstance(result, int):
        return result
    if isinstance(result, dict):
        return result.get('status')
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Rebuild the report Sheet, post confirmed transitions/exits, and save state after readback.')
    parser.add_argument('--dry-run', action='store_true', help='Read live data and print result without post, Sheet write, or state write.')
    parser.add_argument('--reconcile-from-sheet', action='store_true', help='Use current Paginas Totais as the comparison baseline.')
    args = parser.parse_args()
    if args.apply == args.dry_run:
        parser.error('choose exactly one of --apply or --dry-run')

    daily = load_module('dtr_sb_daily_match_audit', DAILY_PATH)
    audit = daily.load_audit_mod()
    sync = audit.sync
    active_users = set(sync.active_users_from_sheet(sync.sheet_rows()))
    publishers, raw_rows = asyncio.run(get_sb_with_retry(audit.get_sb))
    current, counts = build_snapshot(raw_rows, active_users, daily, sync)

    state = load_state()
    if args.reconcile_from_sheet:
        previous = snapshot_from_report_sheet(sync)
        source_label = 'Sheet Paginas Totais anterior → SB live'
        source = 'report-sheet-reconciliation'
    else:
        if state is None:
            raise RuntimeError('state absent; first run must use --reconcile-from-sheet')
        previous = state['active']
        source_label = 'última leitura SB concluída → SB live'
        source = 'previous-live-state'

    transitions, removed_from_snapshot = compare_snapshots(previous, current)
    revenue_meta = None
    if transitions:
        revenue_targets = [dict(item['after']) for item in transitions]
        try:
            revenue = load_module('sb_messenger_revenue_live', REVENUE_PATH)
            report_rows, request_payload = asyncio.run(revenue.fetch_live_report())
            # Validate the exact rolling seven-day window and full dashboard scope
            # before exposing any financial value in Discord.
            revenue.aggregate_report(report_rows, request_payload)
            revenue_meta = {
                'status': 'ok',
                'period_start': str(request_payload.get('initialDate') or '')[:10],
                'period_end': str(request_payload.get('finalDate') or '')[:10],
                'api_rows': len(report_rows),
                'publishers': len(request_payload.get('publishers') or []),
            }
            revenue_meta.update(sync.enrich_revenue_7d(revenue_targets, report_rows))
        except Exception as revenue_exc:
            for target in revenue_targets:
                target['investment_7d'] = None
                target['investment_7d_brl'] = '—'
                target['revenue_7d'] = None
                target['revenue_7d_brl'] = '—'
                target['revenue_7d_match_basis'] = 'unavailable'
            revenue_meta = {
                'status': 'unavailable',
                'error': f'{type(revenue_exc).__name__}: {revenue_exc}',
                'rows': len(transitions),
                'matched': 0,
                'unmatched': len(transitions),
            }
        for item, target in zip(transitions, revenue_targets):
            item['after'] = target
    confirmed_exits = confirmed_resolutions(removed_from_snapshot, raw_rows, daily, sync, sync.today())
    history = update_history((state or {}).get('history'), transitions, confirmed_exits, current)
    history_rows = history_sheet_rows(history)
    transition_blocks = render_blocks(transitions, counts, source_label) if transitions else []
    exit_blocks = sync.build_exited_restrictions_alerts(
        confirmed_exits,
        {'started_at': now_iso()},
    ) if confirmed_exits else []
    sheet_update = None
    sheet_stats = None
    post_results = []

    if args.dry_run:
        for block in [*transition_blocks, *exit_blocks]:
            print(block)
    else:
        sheet_rows, sheet_stats = sync.restricted_sheet_rows(raw_rows, active_users, sync.today())
        sheet_update = sync.write_google_sheet(sheet_rows, sheet_stats)
        if not sheet_update.get('readback_ok'):
            raise RuntimeError('Google Sheet update returned no successful readback')
        for kind, blocks in [('transition', transition_blocks), ('exit', exit_blocks)]:
            for block in blocks:
                result = sync.post_discord(block, mention_roles=not post_results)
                post_results.append({'kind': kind, 'result': result})
                if discord_status(result) not in (200, 201):
                    raise RuntimeError(f'Discord {kind} delivery failed: {result!r}')
        save_state(current, counts, transitions, confirmed_exits, source, history)

    all_blocks = [*transition_blocks, *exit_blocks]
    print(json.dumps({
        'ok': True,
        'mode': 'apply' if args.apply else 'dry-run',
        'channel_id': TARGET_CHANNEL_ID,
        'publishers': len(publishers),
        'active_users': len(active_users),
        'previous_monitored': len(previous),
        'current_monitored': len(current),
        'transitions': transitions,
        'resolved_count': len(confirmed_exits),
        'unconfirmed_removed_count': len(removed_from_snapshot) - len(confirmed_exits),
        'counts': counts,
        'revenue_7d': revenue_meta,
        'sheet_stats': sheet_stats,
        'history': {
            'coverage_start': history.get('coverage_start'),
            'page_count': history.get('page_count'),
            'totals': history.get('totals'),
            'sheet_rows': len(history_rows),
        },
        'blocks': len(all_blocks),
        'block_lengths': [len(block) for block in all_blocks],
        'sheet_update': sheet_update,
        'post_results': post_results,
        'state_written': bool(args.apply),
    }, ensure_ascii=False, indent=2, default=json_default))


if __name__ == '__main__':
    main()
