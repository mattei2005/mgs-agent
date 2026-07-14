#!/usr/bin/env python3
"""Fetch one closed Smart Bidding SMS day and import it into mgs-quiz-carro.

Secrets are used only in memory/environment and are never printed or persisted.
"""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
SB_STATE = Path('/root/.local/share/mgs/smartbidding_state_headed.json')
IMPORTER = BASE / 'scripts/import-sb-sms-revenue-day.php'
API = 'https://api.jbfdigital.com.br/report/performance_per_sms'
DASHBOARD = 'https://app.smartbiddingdigital.com/reports/sms'
PUBLISHER = 'digital-trust_creditoparaveiculo'
DOMAIN = 'creditoparaveiculo'
REMOTE_HOST = 'runcloud-inc02.162-55-28-179.sslip.io'
REMOTE_USER = 'zeus'
REMOTE_WP = '/home/runcloud2/webapps/creditoparaveiculo'
SSH_ITEM = 'Runcloud Server 02 - 162.55.28.179- zeus Acesso'
ALERT_CHANNEL = '1498132022634483894'
NY = ZoneInfo('America/New_York')
SP = ZoneInfo('America/Sao_Paulo')


def cents(value):
    return int((Decimal(str(value or 0)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def canonical_hash(rows):
    cleaned = []
    for row in rows:
        cleaned.append({k: row.get(k) for k in sorted(row)})
    blob = json.dumps(cleaned, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(blob).hexdigest()


def aggregate_rows(rows, target_date):
    by_pk = {}
    for row in rows:
        if row.get('DATE') != target_date:
            raise RuntimeError(f'SB response escaped target date: {row.get("DATE")}')
        if row.get('COMPANY') != 'digital-trust' or row.get('PUBLISHER') != PUBLISHER or row.get('DOMAIN') != DOMAIN:
            raise RuntimeError('SB response escaped publisher/domain scope')
        pk = str(row.get('PK_JBF_PERFORMANCE_PER_SMS') or '')
        if not pk:
            raise RuntimeError('SB response row missing source PK')
        by_pk[pk] = row
    if not by_pk:
        raise RuntimeError(f'No Smart Bidding revenue rows returned for {target_date}; refusing to store zero')

    grouped = defaultdict(list)
    for row in by_pk.values():
        grouped[str(row.get('UTM_CAMPAIGN') or '').strip()].append(row)

    records = []
    for campaign, group in sorted(grouped.items()):
        records.append({
            'revenue_date': target_date,
            'publisher': PUBLISHER,
            'domain': DOMAIN,
            'utm_campaign': campaign,
            'revenue_cents': sum(cents(r.get('REVENUE')) for r in group),
            'net_revenue_cents': sum(cents(r.get('NET_REVENUE')) for r in group),
            'investment_cents': sum(cents(r.get('INVESTIMENT')) for r in group),
            'source_rows': len(group),
            'source_hash': canonical_hash(group),
        })
    expected = {
        'groups': len(records),
        'source_rows': len(by_pk),
        'revenue_cents': sum(r['revenue_cents'] for r in records),
        'net_revenue_cents': sum(r['net_revenue_cents'] for r in records),
        'investment_cents': sum(r['investment_cents'] for r in records),
    }
    return {
        'source': 'smartbidding:/report/performance_per_sms',
        'metric': 'NET_REVENUE',
        'target_date': target_date,
        'publisher': PUBLISHER,
        'domain': DOMAIN,
        'records': records,
        'expected': expected,
    }


async def fetch_day(target_date):
    if not SB_STATE.exists() or SB_STATE.stat().st_size < 1000:
        raise RuntimeError('Smart Bidding authenticated state is unavailable')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx = await browser.new_context(
                storage_state=str(SB_STATE),
                viewport={'width': 1600, 'height': 1000},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            )
            page = await ctx.new_page()
            future = asyncio.get_running_loop().create_future()

            async def capture(req):
                if '/report/performance_per_sms' in req.url and not future.done():
                    future.set_result(req)

            page.on('request', capture)
            await page.goto(DASHBOARD, wait_until='domcontentloaded', timeout=120000)
            request = await asyncio.wait_for(future, timeout=120)
            headers = await request.all_headers()
            safe_headers = {k: v for k, v in headers.items() if k.lower() in {'authorization', 'content-type', 'origin', 'referer', 'user-agent'}}
            payload = {
                'initialDate': target_date + 'T12:00:00.000Z',
                'finalDate': target_date + 'T12:00:00.000Z',
                'publishers': [PUBLISHER],
                'currency': None,
            }
            response = await ctx.request.post(API, headers=safe_headers, data=payload, timeout=180000)
            if response.status not in (200, 201):
                raise RuntimeError(f'Smart Bidding SMS API returned HTTP {response.status}')
            rows = await response.json()
            if not isinstance(rows, list):
                raise RuntimeError('Smart Bidding SMS API response is not a list')
            return rows
        finally:
            await browser.close()


def get_ssh_password():
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


def import_remote(payload):
    password = get_ssh_password()
    env = os.environ.copy()
    env['SSHPASS'] = password
    ssh_opts = [
        '-o', 'PreferredAuthentications=password',
        '-o', 'PubkeyAuthentication=no',
        '-o', 'StrictHostKeyChecking=accept-new',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts_mgs',
        '-o', 'ConnectTimeout=20',
    ]
    remote_dir = '/var/tmp/mgs-sb-sms-revenue'
    remote_payload = remote_dir + '/mgs-sb-sms-revenue-day.json'
    remote_importer = remote_dir + '/import-sb-sms-revenue-day.php'
    prepare = subprocess.run(
        ['sshpass', '-e', 'ssh', *ssh_opts, f'{REMOTE_USER}@{REMOTE_HOST}', f'mkdir -p {remote_dir} && chmod 755 {remote_dir}'],
        text=True, capture_output=True, env=env, timeout=60,
    )
    if prepare.returncode != 0:
        raise RuntimeError('Failed to prepare persistent RunCloud import runtime')
    with tempfile.TemporaryDirectory(prefix='mgs-sb-daily-', dir='/root/mgs-agent/work') as tmp:
        local_payload = Path(tmp) / 'mgs-sb-sms-revenue-day.json'
        local_importer = Path(tmp) / 'import-sb-sms-revenue-day.php'
        local_payload.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        local_importer.write_text(IMPORTER.read_text(encoding='utf-8'), encoding='utf-8')
        scp = subprocess.run(
            ['sshpass', '-e', 'scp', *ssh_opts, str(local_payload), str(local_importer), f'{REMOTE_USER}@{REMOTE_HOST}:{remote_dir}/'],
            text=True, capture_output=True, env=env, timeout=120,
        )
        if scp.returncode != 0:
            raise RuntimeError('Failed to transfer daily revenue payload/importer to RunCloud')
        remote = (
            'set -e; '
            f'chmod 644 {remote_payload} {remote_importer}; '
            f"result=$(sudo -u runcloud2 MGS_SB_PAYLOAD_PATH={remote_payload} wp --path={REMOTE_WP} eval-file {remote_importer} --skip-themes); "
            'printf "%s\\n" "$result"'
        )
        run = subprocess.run(
            ['sshpass', '-e', 'ssh', *ssh_opts, f'{REMOTE_USER}@{REMOTE_HOST}', remote],
            text=True, capture_output=True, env=env, timeout=180,
        )
        if run.returncode != 0 or 'DAILY_REVENUE_IMPORT_OK' not in run.stdout:
            raw_diagnostic = (run.stderr or run.stdout or 'no remote diagnostic').strip().replace('\n', ' ')
            diagnostic = raw_diagnostic[-800:]
            raise RuntimeError(f'WordPress daily revenue import/readback failed: {diagnostic}')
        return json.loads(run.stdout.strip().splitlines()[-1])


def discord_alert(message):
    token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
    if not token:
        return False
    data = json.dumps({
        'content': f'<@344196393512075265> Falha no cron diário de receita SMS Smart Bidding: {message}',
        'allowed_mentions': {'users': ['344196393512075265']},
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f'https://discord.com/api/v10/channels/{ALERT_CHANNEL}/messages',
        data=data,
        headers={'Authorization': f'Bot {token}', 'Content-Type': 'application/json', 'User-Agent': 'MGS-SB-SMS-Revenue/1.0'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status in (200, 201)


def parse_args():
    default_date = (datetime.now(SP).date() - timedelta(days=1)).isoformat()
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=default_date, help='closed SB date YYYY-MM-DD; default yesterday in America/Sao_Paulo')
    ap.add_argument('--fetch-only', action='store_true', help='fetch and validate without WordPress write')
    ap.add_argument('--no-alert', action='store_true', help=argparse.SUPPRESS)
    return ap.parse_args()


def main():
    args = parse_args()
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
        rows = asyncio.run(fetch_day(args.date))
        payload = aggregate_rows(rows, args.date)
        if args.fetch_only:
            print(json.dumps({'status': 'FETCH_OK', 'target_date': args.date, **payload['expected']}, ensure_ascii=False))
            return 0
        imported = import_remote(payload)
        print(json.dumps({'status': 'SYNC_OK', 'target_date': args.date, **payload['expected'], 'readback': imported}, ensure_ascii=False))
        return 0
    except Exception as exc:
        error_text = str(exc).replace('\n', ' ')
        safe = f'{type(exc).__name__}: {error_text[-1000:]}'
        print(json.dumps({'status': 'SYNC_FAILED', 'target_date': args.date, 'error': safe}, ensure_ascii=False))
        if not args.no_alert and not args.fetch_only:
            try:
                discord_alert(safe)
            except Exception:
                pass
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
