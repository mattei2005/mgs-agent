#!/usr/bin/env python3
"""Read-only SMS Funnel sends/cost report for MGS.

The script persists aggregate page counters only. It never stores message text,
names, phones, links, credentials or raw message rows.
"""
from __future__ import annotations

import argparse
import calendar
import importlib.util
import json
import math
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import requests

AUTH_HELPER = Path('/root/mgs-agent/scripts/sync-smsfunnel-cost-daily.py')
DEFAULT_STATE_DIR = Path('/root/.hermes/profiles/ares/cache/scratch')
SP = ZoneInfo('America/Sao_Paulo')
MANAGER_RE = re.compile(r'(?<![A-Z0-9])G00([1-6])(?![0-9])', re.I)
MANAGERS = tuple(f'G{i:03d}' for i in range(1, 7))
RETRYABLE = {429, 500, 502, 503, 504}
PER_PAGE = 5000


def validate_month(value: str) -> str:
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value or ''):
        raise argparse.ArgumentTypeError('month must be YYYY-MM')
    return value


def month_bounds(month: str) -> tuple[str, str, str]:
    year, number = map(int, month.split('-'))
    last = calendar.monthrange(year, number)[1]
    if number == 12:
        next_first = date(year + 1, 1, 1)
    else:
        next_first = date(year, number + 1, 1)
    return f'{year:04d}-{number:02d}-01', f'{year:04d}-{number:02d}-{last:02d}', next_first.isoformat()


def manager_from_text(value: str | None) -> str | None:
    match = MANAGER_RE.search(str(value or '').upper())
    return match.group(0).upper() if match else None


def medium_shape(value: str | None) -> str:
    raw = str(value or '').strip().lower()
    if not raw:
        return 'missing'
    if re.fullmatch(r'g00[1-6]', raw):
        return 'plain'
    if re.fullmatch(r'g00[1-6]-s', raw):
        return 'suffix_s'
    if re.fullmatch(r'g00[1-6]-[a-z0-9_-]+', raw):
        return 'other_suffix'
    return 'other'


def brl(messages: int, unit_cost: Decimal) -> str:
    return str((Decimal(messages) * unit_cost).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def load_auth() -> tuple[str, dict[str, str], requests.Session]:
    spec = importlib.util.spec_from_file_location('mgs_sms_auth', AUTH_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError('SMS Funnel auth helper unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    session, headers = module.authenticated_session()
    return str(module.API_BASE), dict(headers), session


class Client:
    def __init__(self, base: str, headers: dict[str, str], session: requests.Session):
        self.base = base.rstrip('/')
        self.headers = dict(headers)
        self.session = session

    def get(self, path: str, params: dict | None = None, timeout: int = 180):
        for attempt in range(1, 6):
            response = self.session.get(
                self.base + path,
                params=params or {},
                headers=self.headers,
                timeout=timeout,
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code not in RETRYABLE or attempt == 5:
                raise RuntimeError(f'SMS Funnel HTTP {response.status_code} at {path}')
            raw = response.headers.get('Retry-After')
            try:
                wait = float(raw) if raw else float(attempt * 4)
            except (TypeError, ValueError):
                wait = float(attempt * 4)
            time.sleep(max(1.0, min(wait, 65.0)))
        raise AssertionError('unreachable')


def report_rows(client: Client, month: str) -> list[dict]:
    year, number = map(int, month.split('-'))
    payload = client.get('/messages-report', {'month': number, 'year': year}) or []
    rows = payload if isinstance(payload, list) else payload.get('data') or []
    rows = [row for row in rows if str(row.get('counter_date') or '').startswith(month + '-')]
    return sorted(rows, key=lambda row: str(row.get('counter_date') or ''))


def official_summary(client: Client, month: str) -> dict:
    first, _last, next_first = month_bounds(month)
    rows = report_rows(client, month)
    official = sum(int(row.get('quantity') or 0) for row in rows)
    payload = client.get('/analytics/funnel-performance', {
        'start_date': first,
        'end_date': next_first,
        'global': 'false',
        't': str(int(time.time() * 1000)),
    }) or {}
    totals = ((payload.get('data') or {}).get('totals') or {})
    consolidated = int(Decimal(str(totals.get('total_sms_sent') or 0)))
    unit = Decimal(str(totals.get('sms_unit_cost') or 0))
    return {
        'month': month,
        'report_dates': [row.get('counter_date') for row in rows],
        'messages_report_total': official,
        'consolidated_total': consolidated,
        'totals_reconciled': official == consolidated,
        'unit_cost_brl': str(unit),
        'official_cost_brl': brl(official, unit),
        '_rows': rows,
        '_unit': unit,
    }


def load_campaigns(client: Client) -> list[dict]:
    result = []
    seen = set()
    for page in range(1, 51):
        payload = client.get('/campaigns', {
            'page': page,
            'per_page': 100,
            'global': 'false',
            't': str(int(time.time() * 1000)),
        }) or {}
        rows = payload.get('data') if isinstance(payload, dict) else payload
        rows = rows if isinstance(rows, list) else []
        for row in rows:
            campaign_id = str(row.get('id') or '')
            if campaign_id and campaign_id not in seen:
                seen.add(campaign_id)
                result.append(row)
        if len(rows) < 100:
            return result
    raise RuntimeError('campaign pagination exceeded safety limit')


def campaign_catalog(campaigns: list[dict]) -> tuple[dict, dict, dict]:
    sequences = {}
    by_campaign = {}
    shapes = Counter()
    for campaign in campaigns:
        campaign_id = str(campaign.get('id') or '')
        manager = manager_from_text(campaign.get('name'))
        info = {
            'campaign_id': campaign_id,
            'campaign_name': str(campaign.get('name') or ''),
            'manager': manager,
        }
        if campaign_id:
            by_campaign[campaign_id] = info
        for sequence in campaign.get('sequences') or []:
            sequence_id = str(sequence.get('id') or '')
            if sequence_id:
                sequences[sequence_id] = {**info, 'sequence_id': sequence_id}
            values = parse_qs(urlsplit(str(sequence.get('url') or '')).query).get('utm_medium', [])
            if not values:
                shapes['missing'] += 1
            for value in values:
                shapes[medium_shape(value)] += 1
    return sequences, by_campaign, dict(shapes)


def analytics_month(client: Client, month: str, campaigns: list[dict], official: dict, workers: int) -> dict:
    first, last, _next = month_bounds(month)

    def task(campaign: dict):
        campaign_id = str(campaign.get('id') or '')
        manager = manager_from_text(campaign.get('name'))
        if not campaign_id or not manager:
            return None
        payload = client.get(f'/analytics/funnel-performance/{campaign_id}/sequences', {
            'start_date': first,
            'end_date': last,
            'global': 'false',
            't': str(int(time.time() * 1000)),
        }) or {}
        rows = payload.get('data') if isinstance(payload, dict) else payload
        rows = rows if isinstance(rows, list) else []
        return manager, sum(int(Decimal(str(row.get('sms_sent') or 0))) for row in rows)

    counts = Counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(task, campaign) for campaign in campaigns]
        for future in as_completed(futures):
            item = future.result()
            if item:
                counts[item[0]] += item[1]
    unit = official['_unit']
    managers = {
        manager: {'messages': int(counts.get(manager, 0)), 'cost_brl': brl(int(counts.get(manager, 0)), unit)}
        for manager in MANAGERS
    }
    identified = sum(row['messages'] for row in managers.values())
    total = official['messages_report_total']
    return {
        'status': 'PASS' if identified == total else 'PARTIAL_ATTRIBUTION',
        'manager_basis': 'campaign_name_G001_G006_token; current URL suffix ignored',
        'managers': managers,
        'identified': {'messages': identified, 'cost_brl': brl(identified, unit)},
        'unallocated': {'messages': total - identified, 'cost_brl': brl(total - identified, unit)},
    }


def checkpoint_path(state_dir: Path, month: str) -> Path:
    return state_dir / f'smsfunnel-report-{month}-pages.jsonl'


def load_checkpoint(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def append_checkpoint(path: Path, row: dict, lock: Lock):
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock:
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
    os.chmod(path, 0o600)


def resolve_unknown(client: Client, sequence_id: str, sequences: dict, campaigns: dict):
    sequence = client.get(f'/sequences/{sequence_id}') or {}
    campaign_id = str(sequence.get('campaign_id') or '')
    info = campaigns.get(campaign_id)
    if info is None and campaign_id:
        campaign = client.get(f'/campaigns/{campaign_id}') or {}
        info = {
            'campaign_id': campaign_id,
            'campaign_name': str(campaign.get('name') or ''),
            'manager': manager_from_text(campaign.get('name')),
        }
        campaigns[campaign_id] = info
    if info:
        sequences[sequence_id] = {**info, 'sequence_id': sequence_id}


def exact_month(client: Client, month: str, campaigns_raw: list[dict], official: dict, workers: int, state_dir: Path) -> dict:
    sequences, campaigns, shapes = campaign_catalog(campaigns_raw)
    expected = {str(row['counter_date']): int(row.get('quantity') or 0) for row in official['_rows']}
    path = checkpoint_path(state_dir, month)
    records = load_checkpoint(path)
    current_day = datetime.now(SP).date().isoformat()
    # Current-day pages are volatile; discard them from an old checkpoint.
    records = [row for row in records if row.get('date') != current_day]
    existing = {(str(row['date']), int(row['page'])) for row in records}
    tasks = []
    for day, total in expected.items():
        for page in range(1, math.ceil(total / PER_PAGE) + 1):
            if (day, page) not in existing:
                tasks.append((day, page))
    lock = Lock()

    def page_task(day: str, page: int):
        payload = client.get('/messages', {'date': day, 'page': page, 'per_page': PER_PAGE}, 300) or {}
        rows = payload.get('data') if isinstance(payload, dict) else payload
        rows = rows if isinstance(rows, list) else []
        counts = Counter()
        sent_true = 0
        sent_other = 0
        for row in rows:
            if row.get('sent') is True:
                sent_true += 1
                counts[str(row.get('sequence_id') or '')] += 1
            else:
                sent_other += 1
        return {
            'date': day,
            'page': page,
            'rows': len(rows),
            'sent_true': sent_true,
            'sent_other': sent_other,
            'sequence_counts': dict(counts),
        }

    if tasks:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(page_task, day, page) for day, page in tasks]
            for index, future in enumerate(as_completed(futures), 1):
                row = future.result()
                records.append(row)
                append_checkpoint(path, row, lock)
                if index % 20 == 0 or index == len(tasks):
                    print(json.dumps({'month': month, 'pages_done': index, 'pages_remaining': len(tasks) - index}), file=sys.stderr, flush=True)

    page_keys = set()
    detail_rows = 0
    sent_true = 0
    sent_other = 0
    sequence_counts = Counter()
    for row in records:
        key = (str(row['date']), int(row['page']))
        if key in page_keys:
            continue
        page_keys.add(key)
        detail_rows += int(row.get('rows') or 0)
        sent_true += int(row.get('sent_true') or 0)
        sent_other += int(row.get('sent_other') or 0)
        sequence_counts.update({key: int(value) for key, value in (row.get('sequence_counts') or {}).items()})

    for sequence_id in [key for key in sequence_counts if key and key not in sequences]:
        try:
            resolve_unknown(client, sequence_id, sequences, campaigns)
        except Exception:
            pass
    counts = Counter()
    unallocated = 0
    for sequence_id, amount in sequence_counts.items():
        manager = (sequences.get(sequence_id) or {}).get('manager')
        if manager in MANAGERS:
            counts[manager] += amount
        else:
            unallocated += amount
    unit = official['_unit']
    managers_out = {
        manager: {'messages': int(counts.get(manager, 0)), 'cost_brl': brl(int(counts.get(manager, 0)), unit)}
        for manager in MANAGERS
    }
    end_rows = report_rows(client, month)
    end_total = sum(int(row.get('quantity') or 0) for row in end_rows)
    start_total = official['messages_report_total']
    status = 'PASS'
    if detail_rows < start_total:
        status = 'PARTIAL_RETENTION'
    elif unallocated:
        status = 'UNALLOCATED_SEQUENCE'
    elif sent_other or detail_rows != sent_true:
        status = 'NON_SENT_ROWS_PRESENT'
    elif end_total != start_total:
        status = 'PARTIAL_GROWTH'
    return {
        'status': status,
        'manager_basis': 'daily sent=true message rows grouped by sequence_id and campaign G token',
        'pages_processed': len(page_keys),
        'detail_rows': detail_rows,
        'sent_true_rows': sent_true,
        'sent_other_rows': sent_other,
        'messages_report_total_at_start': start_total,
        'messages_report_total_at_end': end_total,
        'messages_report_growth': end_total - start_total,
        'current_url_medium_shapes': shapes,
        'managers': managers_out,
        'identified': {'messages': sum(row['messages'] for row in managers_out.values()), 'cost_brl': brl(sum(row['messages'] for row in managers_out.values()), unit)},
        'unallocated': {'messages': unallocated + max(start_total - detail_rows, 0), 'cost_brl': brl(unallocated + max(start_total - detail_rows, 0), unit)},
        'privacy': {'raw_messages_persisted': False, 'pii_persisted': False, 'links_opened': False},
    }


def public_official(summary: dict) -> dict:
    return {key: value for key, value in summary.items() if not key.startswith('_')}


def parse_args():
    parser = argparse.ArgumentParser(description='Read-only SMS Funnel sends/cost report')
    parser.add_argument('--month', action='append', type=validate_month, required=True, help='YYYY-MM; repeat for several months')
    parser.add_argument('--mode', choices=('totals', 'analytics', 'exact'), default='analytics')
    parser.add_argument('--manager', action='append', choices=MANAGERS, help='narrow displayed managers; repeat as needed')
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--state-dir', type=Path, default=DEFAULT_STATE_DIR)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('--workers must be between 1 and 8')
    args.month = list(dict.fromkeys(args.month))
    return args


def main() -> int:
    args = parse_args()
    base, headers, session = load_auth()
    client = Client(base, headers, session)
    campaigns = load_campaigns(client) if args.mode in {'analytics', 'exact'} else []
    _sequences, _by_campaign, medium_shapes = campaign_catalog(campaigns) if campaigns else ({}, {}, {})
    output = {
        'status': 'PASS',
        'mode': args.mode,
        'requested_months': args.month,
        'generated_at_sp': datetime.now(SP).isoformat(),
        'external_writes_performed': False,
        'scratch_checkpointing': args.mode == 'exact',
        'current_url_medium_shapes': medium_shapes,
        'months': [],
    }
    for month in args.month:
        official = official_summary(client, month)
        row = {'official': public_official(official)}
        if args.mode == 'analytics':
            row['attribution'] = analytics_month(client, month, campaigns, official, args.workers)
        elif args.mode == 'exact':
            row['attribution'] = exact_month(client, month, campaigns, official, args.workers, args.state_dir)
        if args.manager and 'attribution' in row:
            all_managers = row['attribution']['managers']
            row['attribution']['managers'] = {manager: all_managers[manager] for manager in args.manager}
            row['attribution']['display_filter_only'] = args.manager
        output['months'].append(row)
        if not official['totals_reconciled']:
            output['status'] = 'FAIL_TOTAL_RECONCILIATION'
        elif row.get('attribution', {}).get('status') not in {None, 'PASS'} and output['status'] == 'PASS':
            output['status'] = row['attribution']['status']
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if output['status'] == 'FAIL_TOTAL_RECONCILIATION' else 0


if __name__ == '__main__':
    raise SystemExit(main())
