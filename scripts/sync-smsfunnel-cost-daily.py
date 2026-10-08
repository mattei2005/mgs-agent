#!/usr/bin/env python3
"""Import actual daily SMS Funnel send cost for creditoparaveiculo quizzes.

Credentials are resolved at runtime and never printed or persisted.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BASE = Path('/root/mgs-agent')
IMPORTER = BASE / 'scripts/import-smsfunnel-cost-day.php'
API_BASE = 'https://web2.smsfunnel.com.br/api'
DOMAIN = 'creditoparaveiculo'
PROVIDER = 'smsfunnel'
REMOTE_HOST = '162.55.28.179'
REMOTE_USER = 'zeus'
REMOTE_WP = '/home/runcloud2/webapps/creditoparaveiculo'
SSH_ITEM = 'Runcloud Server 02 - 162.55.28.179- zeus Acesso'
SMS_ITEM = 'SMS Funnel Dashboard'
ALERT_CHANNEL = '1498132022634483894'
FINANCE_APP = '/home/mgsfinance/releases/pg-auth-1545934831664242748'
FINANCE_STATE = BASE / 'data/finance-sms-usage-state.json'
FINANCE_AUTHORITY = '1555464947394285580'
SP = ZoneInfo('America/Sao_Paulo')
MANAGERS = tuple(f'G{i:03d}' for i in range(1, 7))
VEHICLES = ('carro', 'moto')
STAGES = (1, 2, 3)
EXPECTED_KEYS = {(vehicle, manager, stage) for vehicle in VEHICLES for manager in MANAGERS for stage in STAGES}
NAME_RE = re.compile(
    r'^AUTOMAÇÃO QUIZ (?P<kind>ENTRADA|MOTO) - CREDITOPARAVEICULO - '
    r'(?P<manager>G00[1-6]) - DISPARO (?P<stage>[123])$',
    re.IGNORECASE,
)


def cents(value) -> int:
    return int((Decimal(str(value or 0)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def canonical_hash(value) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(blob).hexdigest()


def parse_campaign(campaign: dict) -> dict | None:
    name = str(campaign.get('name') or '').strip()
    if 'CREDITOPARAVEICULO' not in name.upper() or 'QUIZ' not in name.upper():
        return None
    match = NAME_RE.match(name)
    if not match:
        raise RuntimeError(f'Unrecognized creditoparaveiculo quiz campaign name: {name}')
    campaign_id = str(campaign.get('id') or '')
    created_at = str(campaign.get('created_at') or '')
    try:
        created_date_sp = datetime.fromisoformat(created_at.replace('Z', '+00:00')).astimezone(SP).date().isoformat()
    except ValueError as exc:
        raise RuntimeError(f'Invalid SMS Funnel campaign created_at for {name}') from exc
    raw_sequences = campaign.get('sequences')
    sequences = raw_sequences if isinstance(raw_sequences, list) else []
    sms_sequences = [row for row in sequences if str(row.get('sequence_type') or '').lower() == 'sms' and not row.get('deleted_at')]
    if len(sms_sequences) != 1 or not str(sms_sequences[0].get('id') or ''):
        raise RuntimeError(f'Expected one SMS sequence for campaign: {name}')
    return {
        'vehicle': 'moto' if match.group('kind').upper() == 'MOTO' else 'carro',
        'manager_code': match.group('manager').upper(),
        'stage': int(match.group('stage')),
        'campaign_id': campaign_id,
        'campaign_name': name,
        'campaign_active': bool(campaign.get('active')),
        'created_date_sp': created_date_sp,
        'sequence_id': str(sms_sequences[0].get('id')),
    }


def validate_campaign_topology(campaigns: list[dict]) -> list[dict]:
    parsed = []
    by_key = {}
    for campaign in campaigns:
        row = parse_campaign(campaign)
        if row is None:
            continue
        if not row['campaign_id']:
            raise RuntimeError('SMS Funnel campaign missing id')
        key = (row['vehicle'], row['manager_code'], row['stage'])
        if key in by_key:
            raise RuntimeError(f'Duplicate SMS Funnel campaign topology key: {key}')
        by_key[key] = row
        parsed.append(row)
    actual = set(by_key)
    if actual != EXPECTED_KEYS:
        missing = sorted(EXPECTED_KEYS - actual)
        extra = sorted(actual - EXPECTED_KEYS)
        raise RuntimeError(f'SMS Funnel campaign topology mismatch: missing={missing} extra={extra}')
    return sorted(parsed, key=lambda row: (row['vehicle'], row['manager_code'], row['stage']))


def resolve_sms_login() -> tuple[str, str]:
    env = os.environ.copy()
    vault = env.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')
    proc = subprocess.run(
        ['op', 'item', 'get', SMS_ITEM, '--vault', vault, '--format', 'json', '--reveal'],
        text=True, capture_output=True, env=env, timeout=90,
    )
    if proc.returncode != 0:
        raise RuntimeError('Could not resolve SMS Funnel credential from 1Password')
    fields = {
        str(item.get('label') or item.get('id') or '').lower(): str(item.get('value') or '')
        for item in json.loads(proc.stdout).get('fields', [])
    }
    email = fields.get('username') or fields.get('email') or ''
    password = fields.get('password') or ''
    if not email or not password:
        raise RuntimeError('SMS Funnel credential is incomplete')
    return email, password


def authenticated_session() -> tuple[requests.Session, dict]:
    email, password = resolve_sms_login()
    session = requests.Session()
    session.headers.update({'User-Agent': 'MGS-Zeus-SMSFunnel-CostSync/1.0'})
    response = session.post(
        f'{API_BASE}/login', json={'email': email, 'password': password, 'utm': ''}, timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f'SMS Funnel login returned HTTP {response.status_code}')
    token = str((response.json() or {}).get('access_token') or '')
    if not token:
        raise RuntimeError('SMS Funnel login token missing')
    return session, {'Authorization': f'Bearer {token}'}


def fetch_campaigns(session: requests.Session, headers: dict) -> list[dict]:
    all_rows = []
    for page in range(1, 21):
        response = session.get(
            f'{API_BASE}/campaigns',
            params={'page': page, 'per_page': 100, 'global': 'false', 't': str(int(time.time() * 1000))},
            headers=headers, timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(f'SMS Funnel campaigns returned HTTP {response.status_code}')
        payload = response.json() or {}
        rows = payload.get('data') if isinstance(payload, dict) else payload
        rows = rows if isinstance(rows, list) else []
        all_rows.extend(rows)
        if len(rows) < 100:
            break
    else:
        raise RuntimeError('SMS Funnel campaigns pagination exceeded safety limit')
    return validate_campaign_topology(all_rows)


def fetch_unit_cost(session: requests.Session, headers: dict, target_date: str) -> int:
    next_date = (date.fromisoformat(target_date) + timedelta(days=1)).isoformat()
    response = session.get(
        f'{API_BASE}/analytics/funnel-performance',
        params={
            'start_date': target_date, 'end_date': next_date,
            'global': 'false', 't': str(int(time.time() * 1000)),
        },
        headers=headers, timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f'SMS Funnel consolidated analytics returned HTTP {response.status_code}')
    totals = ((response.json() or {}).get('data') or {}).get('totals') or {}
    unit_cost_cents = cents(totals.get('sms_unit_cost'))
    if unit_cost_cents <= 0:
        raise RuntimeError('SMS Funnel unit cost is missing or zero')
    return unit_cost_cents


def fetch_campaign_day(session: requests.Session, headers: dict, campaign: dict, target_date: str, unit_cost_cents: int) -> dict:
    response = session.get(
        f"{API_BASE}/analytics/funnel-performance/{campaign['campaign_id']}/sequences",
        params={
            'start_date': target_date, 'end_date': target_date,
            'global': 'false', 't': str(int(time.time() * 1000)),
        },
        headers=headers, timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"SMS Funnel sequence analytics HTTP {response.status_code} for {campaign['vehicle']}/{campaign['manager_code']}/D{campaign['stage']}"
        )
    payload = response.json() or {}
    rows = payload.get('data') if isinstance(payload, dict) else payload
    rows = rows if isinstance(rows, list) else []
    if len(rows) > 1:
        raise RuntimeError(
            f"Unexpected sequence row count {len(rows)} for {campaign['vehicle']}/{campaign['manager_code']}/D{campaign['stage']}"
        )
    if not rows:
        source = {
            'sequence_id': campaign['sequence_id'],
            'sms_sent': 0,
            'cost': 0,
            'analytics_empty_zero': True,
        }
    else:
        source = rows[0]
    sms_sent = int(Decimal(str(source.get('sms_sent') or 0)))
    api_cost_cents = cents(source.get('cost'))
    formula_cost_cents = sms_sent * unit_cost_cents
    if sms_sent < 0 or abs(api_cost_cents - formula_cost_cents) > 1:
        raise RuntimeError(
            f"SMS Funnel cost mismatch for {campaign['vehicle']}/{campaign['manager_code']}/D{campaign['stage']}: "
            f'api={api_cost_cents} formula={formula_cost_cents}'
        )
    sequence_id = str(source.get('sequence_id') or '')
    if not sequence_id:
        raise RuntimeError('SMS Funnel sequence analytics row missing sequence_id')
    if sequence_id != campaign['sequence_id']:
        raise RuntimeError(
            f"SMS Funnel sequence identity mismatch for {campaign['vehicle']}/{campaign['manager_code']}/D{campaign['stage']}"
        )
    return {
        'cost_date': target_date,
        'provider': PROVIDER,
        'domain': DOMAIN,
        'vehicle': campaign['vehicle'],
        'manager_code': campaign['manager_code'],
        'stage': campaign['stage'],
        'campaign_id': campaign['campaign_id'],
        'campaign_name': campaign['campaign_name'],
        'sequence_id': sequence_id,
        'sms_sent': sms_sent,
        'unit_cost_cents': unit_cost_cents,
        'cost_cents': formula_cost_cents,
        'source_hash': canonical_hash({'campaign': campaign, 'analytics': source, 'date': target_date}),
    }


def fetch_day(session: requests.Session, headers: dict, campaigns: list[dict], target_date: str) -> dict:
    unit_cost_cents = fetch_unit_cost(session, headers, target_date)
    records = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fetch_campaign_day, session, headers, campaign, target_date, unit_cost_cents): campaign
            for campaign in campaigns
        }
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda row: (row['vehicle'], row['manager_code'], row['stage']))
    if len(records) != len(EXPECTED_KEYS):
        raise RuntimeError(f'Expected {len(EXPECTED_KEYS)} SMS cost records, got {len(records)}')
    stage_totals = {
        str(stage): sum(row['sms_sent'] for row in records if row['stage'] == stage)
        for stage in STAGES
    }
    expected = {
        'records': len(records),
        'sms_sent': sum(row['sms_sent'] for row in records),
        'cost_cents': sum(row['cost_cents'] for row in records),
        'unit_cost_cents': unit_cost_cents,
        'stage_1_sent': stage_totals['1'],
        'stage_2_sent': stage_totals['2'],
        'stage_3_sent': stage_totals['3'],
    }
    return {
        'source': 'smsfunnel:/analytics/funnel-performance/{campaign_id}/sequences',
        'target_date': target_date,
        'provider': PROVIDER,
        'domain': DOMAIN,
        'timezone': 'America/Sao_Paulo',
        'records': records,
        'expected': expected,
    }


def fetch_dashboard_day(session, headers, target_date):
    """Same source used by the live DashboardComponent.dailySents chart."""
    day = date.fromisoformat(target_date)
    today = datetime.now(SP).date()
    if day >= today:
        raise RuntimeError('SMS dashboard date must be closed')
    response = session.get(f'{API_BASE}/daily-sents', params={'startDate': target_date, 't': str(int(time.time() * 1000))}, headers=headers, timeout=90)
    if response.status_code != 200:
        raise RuntimeError(f'SMS dashboard daily-sents HTTP {response.status_code}')
    raw = response.json()
    values, labels = raw.get('data'), raw.get('labels')
    weekday_names = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')
    expected_labels = [weekday_names[(day.weekday()+i)%7] for i in range(8)]
    if not isinstance(values, list) or len(values) != 8 or labels != expected_labels:
        raise RuntimeError('SMS dashboard date-window correspondence failed')
    quantity = values[0]
    if type(quantity) is not int or quantity < 0:
        raise RuntimeError('SMS dashboard count is not a nonnegative integer')
    proof = {'authority': '1557758039962951733', 'endpoint': '/daily-sents', 'date': target_date, 'source_timezone': 'America/Sao_Paulo', 'quantity': quantity}
    return {**proof, 'source_hash': canonical_hash(proof)}


def fetch_exact_finance_day(session: requests.Session, headers: dict, campaigns: list[dict], target_date: str, analytics: dict) -> dict:
    """Dashboard controls total; exact detail controls Gs, variance stays unassigned."""
    dashboard = fetch_dashboard_day(session, headers, target_date)
    official = dashboard['quantity']
    per_page = 5000

    def page_task(page: int) -> dict:
        response = session.get(
            f'{API_BASE}/messages',
            params={'date': target_date, 'page': page, 'per_page': per_page, 't': str(int(time.time() * 1000))},
            headers=headers, timeout=300,
        )
        if response.status_code != 200:
            raise RuntimeError(f'SMS Funnel messages page {page} failed with HTTP {response.status_code}')
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get('data'), list) or body.get('current_page') != page or type(body.get('last_page')) is not int or not 1 <= body['last_page'] <= 1000 or type(body.get('total')) is not int:
            raise RuntimeError('SMS message pagination metadata invalid')
        return body

    first = page_task(1)
    detail = list(first['data'])
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(page_task, page) for page in range(2, first['last_page']+1)]
        for future in as_completed(futures):
            body = future.result()
            if body['total'] != first['total'] or body['last_page'] != first['last_page']:
                raise RuntimeError('SMS detail changed during pagination')
            detail.extend(body['data'])
    if len(detail) != first['total'] or len({row.get('id') for row in detail}) != len(detail) or any(not row.get('id') for row in detail):
        raise RuntimeError('SMS detail incomplete or duplicate IDs')
    if any(str(row.get('sent_day') or '')[:10] != target_date for row in detail):
        raise RuntimeError('SMS detail includes another accounting date')
    sent = [row for row in detail if row.get('sent') is True]
    if len(detail) != len(sent):
        raise RuntimeError(f'Non-sent rows present in closed SMS day: rows={len(detail)} sent={len(sent)}')
    sequence_manager = {str(c['sequence_id']): c['manager_code'] for c in campaigns}
    if len(sequence_manager) != len(campaigns):
        raise RuntimeError('Ambiguous SMS sequence attribution')
    sequence_counts = Counter(str(row.get('sequence_id') or '') for row in sent)
    unknown = sorted(sequence for sequence in sequence_counts if sequence not in sequence_manager)
    if unknown:
        raise RuntimeError(f'Unallocated SMS sequences for {target_date}: {len(unknown)}')
    manager_counts = Counter()
    for sequence, amount in sequence_counts.items():
        manager_counts[sequence_manager[sequence]] += amount
    if sum(manager_counts.values()) != len(sent):
        raise RuntimeError('SMS manager attribution does not close to detail')
    if fetch_dashboard_day(session, headers, target_date) != dashboard:
        raise RuntimeError('SMS dashboard total changed during collection')
    unit = int(analytics['expected']['unit_cost_cents'])
    records = []
    for manager in MANAGERS:
        count = int(manager_counts.get(manager, 0))
        sequences = sorted((sequence, amount) for sequence, amount in sequence_counts.items() if sequence_manager[sequence] == manager)
        records.append({'manager_code': manager, 'sms_sent': count, 'cost_cents': count * unit, 'source_hash': canonical_hash({'date': target_date, 'manager': manager, 'sequences': sequences})})
    bundle = canonical_hash({'date': target_date, 'dashboard_proof': dashboard, 'unit_cost_cents': unit, 'records': records})
    return {
        'authority': FINANCE_AUTHORITY,
        'date': target_date,
        'period': target_date[:7],
        'scenario_id': 'workspace-' + target_date[:7],
        'source': 'SMS Funnel dashboard',
        'dashboard_proof': dashboard,
        'reconciliation': {'observed_sms_sent': len(sent), 'official_sms_sent': official, 'unattributed_sms_difference': official-len(sent), 'unattributed_cost_difference_cents': (official-len(sent))*unit, 'manager_assigned': None},
        'source_bundle_sha256': bundle,
        'unit_cost_cents': unit,
        'records': records,
        'expected': {'manager_records': 6, 'sms_sent': official, 'cost_cents': official * unit},
        'analytics_crosscheck': {'sms_sent': analytics['expected']['sms_sent'], 'difference': official - analytics['expected']['sms_sent'], 'authoritative': False},
        'privacy': {'raw_messages_persisted': False, 'pii_persisted': False, 'links_opened': False},
    }


def get_ssh_password() -> str:
    env = os.environ.copy()
    vault = env.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')
    proc = subprocess.run(
        ['op', 'item', 'get', SSH_ITEM, '--vault', vault, '--fields', 'label=password', '--reveal'],
        text=True, capture_output=True, env=env, timeout=90,
    )
    password = proc.stdout.strip()
    if proc.returncode != 0 or not password:
        raise RuntimeError('Could not resolve RunCloud SSH credential from 1Password')
    return password


def import_remote(payload: dict) -> dict:
    password = get_ssh_password()
    env = os.environ.copy()
    env['SSHPASS'] = password
    ssh_opts = [
        '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
        '-o', 'StrictHostKeyChecking=accept-new', '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts_mgs',
        '-o', 'ConnectTimeout=20',
    ]
    remote_dir = '/var/tmp/mgs-smsfunnel-cost'
    remote_payload = remote_dir + '/mgs-smsfunnel-cost-day.json'
    remote_importer = remote_dir + '/import-smsfunnel-cost-day.php'
    prepare = subprocess.run(
        ['sshpass', '-e', 'ssh', *ssh_opts, f'{REMOTE_USER}@{REMOTE_HOST}', f'mkdir -p {remote_dir} && chmod 755 {remote_dir}'],
        text=True, capture_output=True, env=env, timeout=60,
    )
    if prepare.returncode != 0:
        raise RuntimeError('Failed to prepare RunCloud SMS cost import runtime')
    with tempfile.TemporaryDirectory(prefix='mgs-sms-cost-', dir=str(BASE / 'work')) as tmp:
        local_payload = Path(tmp) / 'mgs-smsfunnel-cost-day.json'
        local_importer = Path(tmp) / 'import-smsfunnel-cost-day.php'
        local_payload.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        local_importer.write_text(IMPORTER.read_text(encoding='utf-8'), encoding='utf-8')
        scp = subprocess.run(
            ['sshpass', '-e', 'scp', *ssh_opts, str(local_payload), str(local_importer), f'{REMOTE_USER}@{REMOTE_HOST}:{remote_dir}/'],
            text=True, capture_output=True, env=env, timeout=120,
        )
        if scp.returncode != 0:
            raise RuntimeError('Failed to transfer SMS cost payload/importer to RunCloud')
        remote = (
            'set -e; '
            f'chmod 644 {remote_payload} {remote_importer}; '
            f"result=$(sudo -u runcloud2 MGS_SMS_COST_PAYLOAD_PATH={remote_payload} wp --path={REMOTE_WP} eval-file {remote_importer} --skip-themes); "
            'printf "%s\\n" "$result"'
        )
        run = subprocess.run(
            ['sshpass', '-e', 'ssh', *ssh_opts, f'{REMOTE_USER}@{REMOTE_HOST}', remote],
            text=True, capture_output=True, env=env, timeout=180,
        )
        if run.returncode != 0 or 'DAILY_SMS_COST_IMPORT_OK' not in run.stdout:
            diagnostic = (run.stderr or run.stdout or 'no remote diagnostic').strip().replace('\n', ' ')[-800:]
            raise RuntimeError(f'WordPress SMS cost import/readback failed: {diagnostic}')
        return json.loads(run.stdout.strip().splitlines()[-1])


def import_finance(plan: dict) -> dict:
    sys.path.insert(0, str(BASE / 'apps/finance-system/deploy'))
    from runcloud_ops import ssh
    payload = (json.dumps(plan, ensure_ascii=False) + '\n').encode()
    rows = []
    for phase in ('rehearse', 'apply', 'verify'):
        command = f'sudo -n -u mgsfinance /usr/bin/node {FINANCE_APP}/sms-usage-cli.mjs {phase} mgs_finance'
        output = ssh(command, input_data=payload, timeout=600)
        lines = [json.loads(line) for line in output.splitlines() if line.strip().startswith('{')]
        if len(lines) != 1:
            raise RuntimeError(f'Finance SMS {phase} did not return one verified result')
        rows.append(lines[0])
    if len(rows) != 3 or [row.get('phase') for row in rows] != ['rehearse', 'apply', 'verify'] or not all(row.get('pass') for row in rows):
        raise RuntimeError('Finance SMS import did not return the three verified phases')
    verify = rows[-1]
    lock_path = '/var/lock/mgs-finance-sms-usage-state.lock'
    with open(lock_path, 'a', encoding='utf-8') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(FINANCE_STATE.read_text(encoding='utf-8')) if FINANCE_STATE.exists() else {'version': 1, 'days': {}}
        state.setdefault('days', {})[plan['date']] = {
            'source_bundle_sha256': plan['source_bundle_sha256'],
            'sms_sent': plan['expected']['sms_sent'],
            'cost_cents': plan['expected']['cost_cents'],
            'revision': verify['revision'],
            'audit_id': verify['audit_id'],
            'verified_at': datetime.now(ZoneInfo('UTC')).isoformat(),
        }
        state['last_success_date'] = max(state['days'])
        temp = FINANCE_STATE.with_suffix('.tmp')
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        os.chmod(temp, 0o600)
        os.replace(temp, FINANCE_STATE)
    return {
        'pass': True,
        'date': plan['date'],
        'sms_sent': plan['expected']['sms_sent'],
        'cost_cents': plan['expected']['cost_cents'],
        'revision': verify['revision'],
        'audit_id': verify['audit_id'],
        'source_bundle_sha256': plan['source_bundle_sha256'],
        'already_applied': rows[1].get('already_applied', False),
    }


def discord_alert(message: str) -> bool:
    token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
    if not token:
        return False
    data = json.dumps({
        'content': f'<@344196393512075265> Falha no cron diário de custo real SMS Funnel: {message}',
        'allowed_mentions': {'users': ['344196393512075265']},
    }, ensure_ascii=False).encode()
    request = urllib.request.Request(
        f'https://discord.com/api/v10/channels/{ALERT_CHANNEL}/messages', data=data,
        headers={'Authorization': f'Bot {token}', 'Content-Type': 'application/json', 'User-Agent': 'MGS-SMSFunnel-Cost/1.0'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status in (200, 201)


def date_range(start: str, end: str):
    current = date.fromisoformat(start)
    final = date.fromisoformat(end)
    while current <= final:
        yield current.isoformat()
        current += timedelta(days=1)


def parse_args():
    default_date = (datetime.now(SP).date() - timedelta(days=1)).isoformat()
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=None, help='one closed SMS Funnel date YYYY-MM-DD')
    parser.add_argument('--from', dest='from_date', default=None, help='backfill start date YYYY-MM-DD')
    parser.add_argument('--to', dest='to_date', default=None, help='backfill end date YYYY-MM-DD')
    parser.add_argument('--fetch-only', action='store_true')
    route = parser.add_mutually_exclusive_group()
    route.add_argument('--dash-only', action='store_true', help='update only the finance dashboard')
    route.add_argument('--wp-only', action='store_true', help='update only the WordPress cost ledger')
    parser.add_argument('--no-alert', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.from_date or args.to_date:
        if not args.from_date or not args.to_date or args.date:
            parser.error('--from and --to must be used together without --date')
    else:
        args.date = args.date or default_date
    return args


def main() -> int:
    sys.path.insert(0, str(BASE / 'apps/finance-system'))
    from finance_release_guard import admit_entrypoint
    admit_entrypoint(BASE / 'apps/finance-system')
    args = parse_args()
    try:
        dates = list(date_range(args.from_date, args.to_date)) if args.from_date else [date.fromisoformat(args.date).isoformat()]
        session, headers = authenticated_session()
        campaigns = fetch_campaigns(session, headers)
        summaries = []
        for target_date in dates:
            payload = fetch_day(session, headers, campaigns, target_date)
            summary = {'target_date': target_date, **payload['expected']}
            finance_plan = None
            if target_date >= '2026-10-01' and not args.wp_only:
                finance_plan = fetch_exact_finance_day(session, headers, campaigns, target_date, payload)
                summary['finance_expected'] = finance_plan['expected']
                summary['finance_source_bundle_sha256'] = finance_plan['source_bundle_sha256']
                summary['finance_records'] = finance_plan['records']
                summary['analytics_crosscheck'] = finance_plan['analytics_crosscheck']
            if not args.fetch_only:
                if not args.dash_only:
                    summary['wordpress_readback'] = import_remote(payload)
                if finance_plan is not None:
                    summary['finance_readback'] = import_finance(finance_plan)
            summaries.append(summary)
        print(json.dumps({
            'status': 'FETCH_OK' if args.fetch_only else 'SYNC_OK',
            'from': dates[0], 'to': dates[-1], 'days': len(dates), 'results': summaries,
        }, ensure_ascii=False))
        return 0
    except Exception as exc:
        safe = f'{type(exc).__name__}: {str(exc).replace(chr(10), " ")[-1000:]}'
        print(json.dumps({'status': 'SYNC_FAILED', 'error': safe}, ensure_ascii=False))
        if not args.no_alert and not args.fetch_only:
            try:
                discord_alert(safe)
            except Exception:
                pass
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
