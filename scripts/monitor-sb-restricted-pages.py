#!/usr/bin/env python3
"""Monitor SmartBidding Messenger Page rows with active Restricted Until.

By default this is an SB state monitor only: it must not announce "new restricted
pages" as confirmed restricted pages because that requires a live DigitalTRChat
scan of active bot users from the migration sheet. Use --allow-sb-only-alert only
for an explicitly labelled SB-only diagnostic.
Uses the validated SB headed/Xvfb route and live /campaigns/Messenger data.
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
STATE_PATH = BASE / 'data/sb-restricted-pages-monitor.json'
LOG_PREFIX = 'monitor-sb-restricted-pages'
SB_STATE = '/root/.local/share/mgs/smartbidding_state_headed.json'
TARGET_CHANNEL_ID = '1522442220903337984'
TEAM_ROLE_IDS = ['1496256346994249912', '1496260941787168848']
TEAM_MENTIONS = ' '.join(f'<@&{role_id}>' for role_id in TEAM_ROLE_IDS)
NY = ZoneInfo('America/New_York')


def now_iso() -> str:
    return datetime.now(NY).isoformat(timespec='seconds')


def log(msg: str) -> None:
    print(f'[{now_iso()}] {LOG_PREFIX}: {msg}', flush=True)


def norm(value) -> str:
    return '' if value is None else str(value).strip()


def active_restricted(row: dict, today: str) -> bool:
    if norm(row.get('STATUS')).lower() != 'broadcast':
        return False
    ru = norm(row.get('RESTRICTED_UNTIL'))[:10]
    if not ru:
        return False
    # Treat malformed/non-ISO dates as restricted rather than silently ignoring.
    return ru >= today if len(ru) == 10 else True


def row_key(row: dict) -> str:
    return '|'.join([
        norm(row.get('ID')),
        norm(row.get('PAGE_ID')),
        norm(row.get('USER_LOGIN')),
        norm(row.get('RESTRICTED_UNTIL'))[:10],
    ])


def row_public(row: dict) -> dict:
    return {
        'id': row.get('ID'),
        'company': row.get('COMPANY'),
        'publisher_id': row.get('PUBLISHER_ID'),
        'page_name': row.get('PAGE_NAME'),
        'page_id': row.get('PAGE_ID'),
        'fb_page_id': row.get('FB_PAGE_ID'),
        'user_login': row.get('USER_LOGIN'),
        'profile_name': row.get('PROFILE_NAME'),
        'template_id': row.get('BROADCAST_TEMPLATE_ID'),
        'status': row.get('STATUS'),
        'restricted_until': norm(row.get('RESTRICTED_UNTIL'))[:10],
        'broadcast_message_id': row.get('BROADCAST_MESSAGE_ID'),
        'broadcast_current_message_id': row.get('BROADCAST_CURRENT_MESSAGE_ID'),
    }


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            '_meta': {
                'description': 'Estado do monitor de páginas restritas SB Messenger Page.',
                'target_channel_id': TARGET_CHANNEL_ID,
                'created_at': now_iso(),
            },
            'last_check': None,
            'last_total_rows': 0,
            'last_active_restricted_count': 0,
            'active': {},
            'last_alert_sent': None,
        }
    return json.loads(STATE_PATH.read_text(encoding='utf-8'))


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=STATE_PATH.name + '.', dir=str(STATE_PATH.parent))
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp_name, STATE_PATH)


def discord_token() -> str:
    token = os.environ.get('DISCORD_BOT_TOKEN', '').strip().strip('"').strip("'")
    if token:
        return token
    env_path = Path('/root/.hermes/profiles/zeus/.env')
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            if line.startswith('DISCORD_BOT_TOKEN='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return ''


def truncate(value: str, limit: int) -> str:
    value = value or ''
    return value if len(value) <= limit else value[: limit - 1] + '…'


def format_rows(rows: list[dict], limit: int = 12) -> str:
    if not rows:
        return 'nenhuma'
    lines = []
    for item in rows[:limit]:
        lines.append(
            f"{item.get('restricted_until') or '?'} | {item.get('company') or '?'} | "
            f"{item.get('page_name') or '?'} | {item.get('user_login') or '?'} | "
            f"{item.get('profile_name') or '?'}"
        )
    if len(rows) > limit:
        lines.append(f'... +{len(rows) - limit} outras')
    return '\n'.join(lines)


def post_discord(payload: dict) -> int:
    token = discord_token()
    if not token:
        raise RuntimeError('DISCORD_BOT_TOKEN unavailable')
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'https://discord.com/api/v10/channels/{TARGET_CHANNEL_ID}/messages',
        data=data,
        headers={
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'MGS-Zeus-SB-Restricted-Monitor/1.0',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


async def fetch_sb_rows() -> tuple[list[str], list[dict]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
        )
        ctx = await browser.new_context(
            storage_state=SB_STATE,
            viewport={'width': 1600, 'height': 1000},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        )
        page = await ctx.new_page()
        headers = {}

        async def on_req(req):
            if 'api.jbfdigital.com.br/company' in req.url:
                headers.update(await req.all_headers())

        page.on('request', on_req)
        await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        h = {k: v for k, v in headers.items() if k.lower() in {'authorization', 'accept', 'content-type'}}
        h.update({'origin': 'https://app.smartbiddingdigital.com', 'referer': 'https://app.smartbiddingdigital.com/'})

        rc = await ctx.request.get('https://api.jbfdigital.com.br/company', headers=h, timeout=120000)
        companies = await rc.json()
        pubs = []
        for company in companies:
            for pub in company.get('publishers') or []:
                if pub.get('active') and pub.get('publisherId'):
                    pubs.append(pub['publisherId'])
        qs = '&'.join('companies[]=' + urllib.parse.quote(x) for x in pubs) + '&source=Messenger'
        r = await ctx.request.get('https://api.jbfdigital.com.br/campaigns/Messenger?' + qs, headers=h, timeout=120000)
        rows = await r.json()
        await browser.close()
        if r.status != 200 or not isinstance(rows, list):
            raise RuntimeError(f'bad SB campaigns response status={r.status} type={type(rows).__name__}')
        return pubs, rows


def build_payload(total_rows: int, active_rows: list[dict], new_rows: list[dict], resolved_rows: list[dict], initial: bool) -> dict:
    by_date = Counter(r.get('restricted_until') or '?' for r in active_rows)
    by_date_text = '\n'.join(f'{date} — {count}' for date, count in sorted(by_date.items())) or 'nenhuma'
    title = 'SB páginas restritas — baseline inicial' if initial else 'SB páginas restritas — alteração detectada'
    color = 3447003 if initial else 15844367
    return {
        'content': TEAM_MENTIONS,
        'allowed_mentions': {'parse': [], 'roles': TEAM_ROLE_IDS},
        'embeds': [{
            'title': title,
            'color': color,
            'fields': [
                {'name': 'Escopo', 'value': f'`Accounts > Messenger > Page` live\nRows lidas: `{total_rows}`\nStatus monitorado: `Broadcast`', 'inline': False},
                {'name': 'Totais', 'value': f'Ativas restritas: `{len(active_rows)}`\nNovas: `{len(new_rows)}`\nResolvidas/expiradas: `{len(resolved_rows)}`', 'inline': True},
                {'name': 'Por data', 'value': '```\n' + truncate(by_date_text, 950) + '\n```', 'inline': False},
                {'name': 'Novas', 'value': '```\n' + truncate(format_rows(new_rows), 950) + '\n```', 'inline': False},
                {'name': 'Resolvidas/expiradas', 'value': '```\n' + truncate(format_rows(resolved_rows), 950) + '\n```', 'inline': False},
            ],
            'footer': {'text': 'Monitor SB Restricted Pages • Zeus'},
            'timestamp': datetime.now(NY).astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z'),
        }],
    }


def fmt_num(n) -> str:
    try:
        return f'{int(n):,}'.replace(',', '.')
    except Exception:
        return str(n)


def publisher_name(item: dict) -> str:
    return item.get('profile_name') or (str(item.get('publisher_id') or '').split('_', 1)[1] if '_' in str(item.get('publisher_id') or '') else (item.get('company') or '?'))


def compact_new_rows(rows: list[dict], limit: int = 5) -> str:
    if not rows:
        return 'Nenhum novo registro SB desde a última execução.'
    header = 'Entrou registro    Página             FB Page ID          Page ID   Usuário bot        Segurador            Expira SB     Origem'
    lines = [header]
    entered = datetime.now(NY).strftime('%Y-%m-%d %H:%M')
    for item in rows[:limit]:
        page = truncate(item.get('page_name') or '?', 17)
        fb_page_id = truncate(str(item.get('fb_page_id') or '?'), 18)
        page_id = truncate(str(item.get('page_id') or '?'), 8)
        user = truncate((item.get('user_login') or '?').replace('@gmail.com', ''), 17)
        seg = truncate(publisher_name(item), 20)
        exp = item.get('restricted_until') or '?'
        origin = 'SB-only; DTR não lido'
        lines.append(f'{entered:<18} {page:<17} {fb_page_id:<18} {page_id:<8} {user:<17} {seg:<20} {exp:<13} {origin}')
    if len(rows) > limit:
        lines.append(f'... +{len(rows) - limit} novas na Sheet')
    return '\n'.join(lines)


def build_alert_payloads(total_rows: int, active_rows: list[dict], new_rows: list[dict], state: dict) -> list[dict]:
    by_date = Counter(r.get('restricted_until') or '?' for r in active_rows)
    by_date_lines = ['Data saída     Páginas']
    # Rodolfo: ordenar por data, da menor para a maior, não por volume.
    for date, count in sorted(by_date.items(), key=lambda kv: kv[0])[:8]:
        by_date_lines.append(f'{date:<13} {count:>7}')

    status_counts = state.get('last_status_counts') or {}
    campaign_count = int(status_counts.get('Campaign', 0) or 0)
    broadcast_total = int(status_counts.get('Broadcast', 0) or 0)
    sem_restricao = max(0, broadcast_total - len(active_rows))
    ready_count = int(status_counts.get('Ready', 0) or 0)
    review_count = int(status_counts.get('Review', 0) or 0)
    incomplete_count = int(status_counts.get('Incomplete', 0) or 0)
    on_hold_count = int(state.get('last_on_hold_count', status_counts.get('On-hold', 0)) or 0)
    block_count = int(state.get('last_block_count', 0) or 0)

    msg1 = f"""```
REGISTROS SB DE RESTRIÇÃO — MGS
Atualizado em: {datetime.now(NY).strftime('%Y-%m-%d %H:%M %Z')}
Fonte: SmartBidding only; DTR/Bot não lido nesta execução

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESUMO DE PAGINAS - STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Paginas           {fmt_num(total_rows):>5}
Sem Restricao           {fmt_num(sem_restricao):>5}
Campaign                {fmt_num(campaign_count):>5}
Broadcast c/ Restricted {fmt_num(len(active_rows)):>5}
Ready                   {fmt_num(ready_count):>5}
Review                  {fmt_num(review_count):>5}
Incomplete              {fmt_num(incomplete_count):>5}
On-hold                 {fmt_num(on_hold_count):>5}
Blocked                 {fmt_num(block_count):>5}

Novos registros SB      {fmt_num(len(new_rows)):>5}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POR DATA DE SAÍDA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(by_date_lines)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOVOS REGISTROS SB — NÃO CONFIRMADOS PELO BOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{compact_new_rows(new_rows)}
```"""

    msg2 = """```
📘 LEGENDA DE ERROS

Código              Significado
#2022               Página temporariamente restrita pelo Messenger/Facebook para envio de mensagens.
PERMISSION          Permissão obrigatória ausente para impersonar/enviar pela página.
APP_DELETED         Aplicação validada foi deletada.
#10_WINDOW          Mensagem enviada fora da janela permitida pela política do Messenger.
#551_UNAVAILABLE    Pessoa não está disponível no momento.
#100_TEMPLATE       Template com params errados, extras, ausentes ou modelo não encontrado.
TOKEN               Token inválido, expirado ou sessão expirada.
OTHER               Erro não mapeado automaticamente; mensagem exata deve ser registrada.
```"""
    return [
        {'content': f'{TEAM_MENTIONS}\n{msg1}', 'allowed_mentions': {'parse': [], 'roles': TEAM_ROLE_IDS}},
        {'content': msg2, 'allowed_mentions': {'parse': []}},
    ]


async def run(args: argparse.Namespace) -> int:
    log('START')
    today = datetime.now(NY).date().isoformat()
    state = load_state()
    initial = not bool(state.get('last_check'))
    previous = state.get('active') or {}

    pubs, rows = await fetch_sb_rows()
    active_rows = [row_public(r) for r in rows if active_restricted(r, today)]
    active = {row_key(r): row_public(r) for r in rows if active_restricted(r, today)}
    new_keys = sorted(set(active) - set(previous))
    resolved_keys = sorted(set(previous) - set(active))
    new_rows = [active[k] for k in new_keys]
    resolved_rows = [previous[k] for k in resolved_keys]

    status_counts = dict(Counter(norm(r.get('STATUS')) or '?' for r in rows))
    blocked_count = status_counts.get('Blocked', 0) + status_counts.get('Bloqueado', 0)
    on_hold_count = status_counts.get('On-hold', 0)
    sem_restricao_count = max(0, len(rows) - on_hold_count - blocked_count - len(active_rows))
    state.update({
        'last_check': now_iso(),
        'last_total_rows': len(rows),
        'last_active_publishers': len(pubs),
        'last_status_counts': status_counts,
        'last_on_hold_count': on_hold_count,
        'last_block_count': blocked_count,
        'last_sem_restricao_count': sem_restricao_count,
        'last_active_restricted_count': len(active_rows),
        'active': active,
        'last_summary': {
            'by_date': dict(Counter(r.get('restricted_until') or '?' for r in active_rows)),
            'new': len(new_rows),
            'resolved': len(resolved_rows),
        },
        'last_new_rows': new_rows,
        'last_resolved_rows': resolved_rows,
    })

    should_send = bool(new_rows or resolved_rows) or bool(getattr(args, 'force_alert', False))
    if initial and args.send_initial:
        should_send = True
    if initial and not args.send_initial:
        should_send = False

    if should_send and not args.allow_sb_only_alert:
        log(f'SUPPRESSED_SB_ONLY_ALERT rows={len(rows)} active_restricted={len(active_rows)} new={len(new_rows)} resolved={len(resolved_rows)} reason=dtr_not_read')
        should_send = False

    if args.dry_run:
        print(json.dumps({
            'dry_run': True,
            'initial': initial,
            'active_publishers': len(pubs),
            'total_rows': len(rows),
            'active_restricted': len(active_rows),
            'new': len(new_rows),
            'resolved': len(resolved_rows),
            'would_send': should_send,
            'by_date': state['last_summary']['by_date'],
        }, ensure_ascii=False, indent=2))
        log(f'DRY_RUN rows={len(rows)} active_restricted={len(active_rows)} new={len(new_rows)} resolved={len(resolved_rows)} would_send={should_send}')
        return 0

    if should_send:
        statuses = []
        for payload in build_alert_payloads(len(rows), active_rows, new_rows, state):
            statuses.append(post_discord(payload))
        state['last_alert_sent'] = now_iso()
        state['last_alert_http'] = statuses[-1] if statuses else None
        log(f'ALERT_SENT http={statuses} active_restricted={len(active_rows)} new={len(new_rows)} resolved={len(resolved_rows)}')
    else:
        log(f'OK no_alert rows={len(rows)} active_publishers={len(pubs)} active_restricted={len(active_rows)} new={len(new_rows)} resolved={len(resolved_rows)}')

    save_state(state)
    log('OK')
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='Do not save state or post Discord; print summary only.')
    ap.add_argument('--send-initial', action='store_true', help='Send baseline alert on first run. Cron does not use this.')
    ap.add_argument('--force-alert', action='store_true', help='Send current live report regardless of state changes.')
    ap.add_argument('--allow-sb-only-alert', action='store_true', help='Permit Discord posting of explicitly labelled SB-only diagnostic output. Cron must not use this for the restricted-pages channel.')
    return ap.parse_args()


if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(run(parse_args())))
    except Exception as exc:
        log(f'ERROR {type(exc).__name__}: {exc}')
        raise
