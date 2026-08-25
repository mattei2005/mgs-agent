#!/usr/bin/env python3
"""Controlled fixed-30 SmartBidding Broadcast Template repair.

Rodolfo-approved 2026-08-03 flow:
- green-only templates are never reset;
- red slots are replaced together from the durable approved bank;
- purple-only templates are reset without changing visible content;
- every write is one POST (Update+Save equivalent), verified all-gray, then one Approval;
- readback occurs only after pages*30*12s plus margin;
- direct Discord embeds report lifecycle transitions per template without noisy ID dumps.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections import Counter
from copy import deepcopy
from zoneinfo import ZoneInfo

BASE = pathlib.Path('/root/mgs-agent')
CONFIG_PATH = BASE / 'data/sb-broadcast-template-repair-config.json'
STATE_PATH = BASE / 'data/sb-broadcast-template-repair-state.json'
BANK_PATH = BASE / 'data/utility-message-bank.json'
BACKUP_ROOT = BASE / 'backups/sb-broadcast-template-repair'
LOG_PATH = BASE / 'logs/sb-broadcast-template-repair.jsonl'
LOCK_PATH = pathlib.Path('/tmp/sb-broadcast-template-repair.lock')
POSTER = BASE / 'scripts/discord-bot-post.py'
DEFAULT_CHANNEL = '1522487422510694450'
SP = ZoneInfo('America/Sao_Paulo')
ET = ZoneInfo('America/New_York')
MESSAGE_COUNT = 30
SECONDS_PER_MESSAGE_PAGE = 12
DIGEST_HOUR_SP = 23
STATUS_FIELDS = ('APPROVED', 'INVALID_FORMAT', 'REJECTED', 'ERROR', 'REJECTED_REASON')
FIRST_NAME_TOKEN = '{{first_name}}'
ALLOWED_COMPANIES = {'digital-trust', 'digital-trust-2'}
LIST_URL = 'https://api.jbfdigital.com.br/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger'

spec = importlib.util.spec_from_file_location('legacy_rollout_helpers', BASE / 'scripts/sb-utility-rollout-manager.py')
assert spec and spec.loader
rollout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollout)


def now_sp() -> dt.datetime:
    return dt.datetime.now(SP)


def now_et() -> dt.datetime:
    return dt.datetime.now(ET)


def iso_sp(value: dt.datetime | None = None) -> str:
    return (value or now_sp()).isoformat(timespec='seconds')


def atomic_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def load_json(path: pathlib.Path, default: dict) -> dict:
    if not path.exists():
        return deepcopy(default)
    return json.loads(path.read_text(encoding='utf-8'))


def default_config() -> dict:
    return {
        'version': 1,
        'enabled': False,
        'channel_id': DEFAULT_CHANNEL,
        'stage': 'canary',
        'auto_promote': True,
        'canary_template_id': None,
        'max_pages': 150,
        'margin_minutes': 60,
        'start_hour_sp': 8,
        'cutoff_hour_sp': 0,
        'staged_templates_per_day': 3,
        'full_templates_per_day': 6,
        'max_no_progress_cycles': 2,
    }


def default_state() -> dict:
    return {
        'version': 1,
        'created_at_sp': iso_sp(),
        'updated_at_sp': iso_sp(),
        'templates': {},
        'runs': [],
        'alerts': {},
        'stage_evidence': {'canary_passed': False, 'staged_passed': False},
    }


def append_log(event: str, **fields) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {'at_sp': iso_sp(), 'event': event, **fields}
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')


def acquire_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open('w')
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def visible(value: str) -> str:
    return re.sub('[\u200b\u200c\u200d\ufeff\u2060]', '', value or '')


def normalized(value: str) -> str:
    return re.sub(r'\s+', ' ', visible(value).strip().lower())


def remove_first_name_placeholder(value: str) -> str:
    """Remove the forbidden Messenger placeholder without leaving bad punctuation."""
    if FIRST_NAME_TOKEN not in (value or ''):
        return value
    result = re.sub(r',\s*\{\{first_name\}\}\s*!', '!', value)
    result = re.sub(r'\{\{first_name\}\}\s*,\s*', '', result)
    result = result.replace(FIRST_NAME_TOKEN, '')
    result = re.sub(r'[ \t]+([,!?;:])', r'\1', result)
    result = re.sub(r'([ \t]){2,}', ' ', result)
    result = '\n'.join(line.rstrip() for line in result.split('\n'))
    return re.sub(r'\n{3,}', '\n\n', result).strip()


def sanitize_first_name_message(message: dict) -> tuple[dict, bool]:
    result = deepcopy(message)
    changed = False
    for key, value in list(result.items()):
        if isinstance(value, str) and FIRST_NAME_TOKEN in value:
            result[key] = remove_first_name_placeholder(value)
            changed = True
    return result, changed


def text_cta_hash(message: dict) -> str:
    payload = [normalized(message.get('TEXT') or ''), normalized(message.get('CTA_1') or message.get('CTA 1') or '')]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def content_projection(message: dict) -> dict:
    return {key: value for key, value in message.items() if key not in STATUS_FIELDS}


def content_hash(messages: list[dict]) -> str:
    ordered = sorted((content_projection(m) for m in messages), key=lambda m: int(m.get('MESSAGE_ID') or 0))
    raw = json.dumps(ordered, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


def strip_status(message: dict) -> dict:
    result = deepcopy(message)
    for key in STATUS_FIELDS:
        result.pop(key, None)
    return result


def status_color(message: dict) -> str:
    return rollout.status_color(rollout.status_of(message))


def counts_for(messages: list[dict]) -> dict:
    counts = Counter(status_color(message) for message in messages)
    return {color: int(counts.get(color, 0)) for color in ('verde', 'cinza', 'vermelho', 'roxo')}


def parse_messages(row: dict) -> list[dict]:
    return sorted(rollout.parse_messages(row), key=lambda item: int(item.get('MESSAGE_ID') or 0))


def row_id(row: dict) -> str:
    return str(row.get('ID') or row.get('id') or '')


def pages_for(row: dict) -> int:
    try:
        return int(float(row.get('PAGES') or 0))
    except (TypeError, ValueError):
        return 0


def active_production(row: dict, exact_30: bool = True) -> bool:
    name = str(row.get('NAME') or '').strip()
    lowered = name.lower()
    company = str(row.get('COMPANY') or '').strip().lower()
    if company not in ALLOWED_COMPANIES:
        return False
    if not name or lowered.startswith('teste-') or 'nao usar' in lowered or 'não usar' in lowered:
        return False
    if pages_for(row) <= 0:
        return False
    return not exact_30 or len(parse_messages(row)) == MESSAGE_COUNT


def parse_vertical(name: str) -> str:
    match = re.search(r'\b([A-Z]{2})[-_ ]([A-Z0-9]{2,8})[-_ ]([A-Z]{2})\b', (name or '').upper())
    return '-'.join(match.groups()) if match else ''


def compact_template_name(name: str, limit: int = 90) -> str:
    value = re.sub(r'\s+', ' ', name or '').strip()
    return value if len(value) <= limit else value[: limit - 3].rstrip() + '...'


def link_map(messages: list[dict]) -> dict:
    return {int(m.get('MESSAGE_ID') or 0): m.get('LINK_1') or m.get('LINK 1') or '' for m in messages}


def upsert_bank_observation(bank: dict, template: str, message: dict, color: str, vertical: str, observed_at: str) -> tuple[str, dict]:
    key = text_cta_hash(message)
    country, language = ('', '')
    parts = vertical.split('-')
    if len(parts) >= 2:
        country, language = parts[0], parts[-1]
    records = bank.setdefault('records', {})
    record = records.setdefault(key, {
        'text_cta_hash': key,
        'vertical': vertical,
        'country': country,
        'language': language,
        'text': message.get('TEXT') or '',
        'cta_1': message.get('CTA_1') or message.get('CTA 1') or '',
        'first_seen_at': now_et().isoformat(timespec='seconds'),
        'last_seen_at': None,
        'first_approved_at': None,
        'last_approved_at': None,
        'approved_count': 0,
        'rejected_count': 0,
        'gray_count': 0,
        'purple_count': 0,
        'status': 'testing',
        'seen_in': [],
        'usage': [],
    })
    record['last_seen_at'] = now_et().isoformat(timespec='seconds')
    status = rollout.status_of(message) or 'GRAY'
    if color == 'verde':
        if not record.get('first_approved_at'):
            record['first_approved_at'] = record['last_seen_at']
        record['last_approved_at'] = record['last_seen_at']
        record['approved_count'] = int(record.get('approved_count') or 0) + 1
        record['status'] = 'mixed_history' if int(record.get('rejected_count') or 0) else 'approved'
    elif color == 'vermelho':
        record['rejected_count'] = int(record.get('rejected_count') or 0) + 1
        record['status'] = 'mixed_history' if int(record.get('approved_count') or 0) else 'rejected'
    elif color == 'roxo':
        record['purple_count'] = int(record.get('purple_count') or 0) + 1
        if int(record.get('approved_count') or 0) and not int(record.get('rejected_count') or 0):
            record['status'] = 'approved_diagnostic'
        elif not int(record.get('approved_count') or 0):
            record['status'] = 'diagnostic'
    elif color == 'cinza':
        record['gray_count'] = int(record.get('gray_count') or 0) + 1
    record.setdefault('seen_in', []).append({
        'template': template,
        'message_id': int(message.get('MESSAGE_ID') or 0),
        'observed_color': color,
        'observed_status': status,
        'observed_at': observed_at,
    })
    record['seen_in'] = record['seen_in'][-100:]
    return key, record


def sync_bank(bank: dict, rows: list[dict]) -> dict:
    observed_at = iso_sp()
    counts = Counter()
    templates = 0
    for row in rows:
        if not active_production(row, exact_30=True):
            continue
        templates += 1
        vertical = parse_vertical(str(row.get('NAME') or ''))
        for message in parse_messages(row):
            color = status_color(message)
            upsert_bank_observation(bank, str(row.get('NAME') or ''), message, color, vertical, observed_at)
            counts[color] += 1
    bank['updated_at_et'] = now_et().isoformat(timespec='seconds')
    bank['last_sync'] = {'at_sp': observed_at, 'templates': templates, 'messages': sum(counts.values()), 'counts': dict(counts), 'source': 'sb-broadcast-template-repair'}
    return {'templates': templates, 'messages': sum(counts.values()), 'counts': dict(counts)}


def approved_candidates(bank: dict, vertical: str, used_hashes: set[str], used_texts: set[str]) -> list[dict]:
    candidates = []
    for key, record in bank.get('records', {}).items():
        if record.get('vertical') != vertical or key in used_hashes:
            continue
        if int(record.get('approved_count') or 0) <= 0 or int(record.get('rejected_count') or 0) > 0:
            continue
        text = record.get('text') or ''
        cta = record.get('cta_1') or ''
        if FIRST_NAME_TOKEN in text or FIRST_NAME_TOKEN in cta:
            continue
        if not text or not cta or normalized(text) in used_texts:
            continue
        candidates.append(record)
    candidates.sort(key=lambda rec: (-int(rec.get('approved_count') or 0), rec.get('last_approved_at') or '', rec.get('text_cta_hash') or ''))
    unique = []
    seen_texts = set(used_texts)
    for record in candidates:
        text_key = normalized(record.get('text') or '')
        if not text_key or text_key in seen_texts:
            continue
        seen_texts.add(text_key)
        unique.append(record)
    return unique


def duplicate_replacement_ids(messages: list[dict]) -> set[int]:
    """Return duplicate slots to replace while preserving the safest occurrence."""
    groups: dict[str, list[dict]] = {}
    for message in messages:
        groups.setdefault(normalized(message.get('TEXT') or ''), []).append(message)
    rank = {'verde': 0, 'cinza': 1, 'roxo': 2, 'vermelho': 3}
    replace: set[int] = set()
    for text, grouped in groups.items():
        if not text or len(grouped) <= 1:
            continue
        keeper = min(
            grouped,
            key=lambda item: (
                rank.get(status_color(item), 9),
                int(item.get('MESSAGE_ID') or 0),
            ),
        )
        keeper_id = int(keeper.get('MESSAGE_ID') or 0)
        replace.update(
            int(item.get('MESSAGE_ID') or 0)
            for item in grouped
            if int(item.get('MESSAGE_ID') or 0) != keeper_id
        )
    return replace


def build_repair(row: dict, bank: dict) -> dict:
    messages = parse_messages(row)
    before = counts_for(messages)
    vertical = parse_vertical(str(row.get('NAME') or ''))
    red_ids = {
        int(message.get('MESSAGE_ID') or 0)
        for message in messages
        if status_color(message) == 'vermelho'
    }
    duplicate_ids = duplicate_replacement_ids(messages)
    placeholder_ids = {
        int(message.get('MESSAGE_ID') or 0)
        for message in messages
        if any(isinstance(value, str) and FIRST_NAME_TOKEN in value for value in message.values())
    }
    target_ids = red_ids | duplicate_ids
    purple_slots = [message for message in messages if status_color(message) == 'roxo']
    if before['verde'] == MESSAGE_COUNT and not duplicate_ids and not placeholder_ids:
        return {
            'action': 'skip_green', 'before': before, 'messages': messages,
            'replaced_slots': [], 'duplicate_slots': [], 'deficit': 0,
            'reason': 'template_100_percent_green_unique',
        }
    if not target_ids and not purple_slots and not placeholder_ids:
        return {
            'action': 'wait_gray', 'before': before, 'messages': messages,
            'replaced_slots': [], 'duplicate_slots': [], 'deficit': 0,
            'reason': 'no_red_purple_or_duplicates',
        }
    prepared = []
    for message in messages:
        sanitized, _ = sanitize_first_name_message(strip_status(message))
        prepared.append(sanitized)
    replaced_slots = []
    if target_ids:
        retained = [
            message for message in messages
            if int(message.get('MESSAGE_ID') or 0) not in target_ids
        ]
        used_hashes = {text_cta_hash(message) for message in retained}
        used_texts = {normalized(message.get('TEXT') or '') for message in retained}
        candidates = approved_candidates(bank, vertical, used_hashes, used_texts)
        required = len(target_ids)
        if len(candidates) < required:
            deficit = required - len(candidates)
            return {
                'action': 'needs_generation', 'before': before, 'messages': messages,
                'replaced_slots': [], 'duplicate_slots': sorted(duplicate_ids),
                'target_slots': sorted(target_ids), 'deficit': deficit,
                'approved_available': len(candidates), 'approved_required': required,
                'vertical': vertical,
                'reason': f'approved_bank_deficit:{len(candidates)}/{required}',
            }
        candidate_iter = iter(candidates)
        for message in prepared:
            message_id = int(message.get('MESSAGE_ID') or 0)
            if message_id not in target_ids:
                continue
            candidate = next(candidate_iter)
            message['TEXT'] = candidate['text']
            message['CTA_1'] = candidate['cta_1']
            message.pop('CTA 1', None)
            used_hashes.add(candidate['text_cta_hash'])
            used_texts.add(normalized(candidate['text']))
            replaced_slots.append({
                'message_id': message_id,
                'text_cta_hash': candidate['text_cta_hash'],
                'reason': 'red_and_duplicate' if message_id in red_ids and message_id in duplicate_ids
                else 'red' if message_id in red_ids else 'duplicate',
            })
        if red_ids and duplicate_ids:
            action = 'replace_red_duplicates_reset'
        elif red_ids:
            action = 'replace_red_reset'
        else:
            action = 'replace_duplicates_reset'
    elif placeholder_ids:
        action = 'sanitize_first_name_reset'
    else:
        action = 'reset_purple'
    texts = [normalized(message.get('TEXT') or '') for message in prepared]
    if not all(texts) or len(texts) != len(set(texts)):
        return {
            'action': 'blocked', 'before': before, 'messages': messages,
            'replaced_slots': [], 'duplicate_slots': sorted(duplicate_ids), 'deficit': 0,
            'reason': 'unique_visible_text_postcondition_failed',
        }
    if link_map(prepared) != link_map(messages):
        return {
            'action': 'blocked', 'before': before, 'messages': messages,
            'replaced_slots': [], 'duplicate_slots': sorted(duplicate_ids), 'deficit': 0,
            'reason': 'link_invariant_guard',
        }
    return {
        'action': action, 'before': before, 'messages': prepared,
        'replaced_slots': replaced_slots, 'duplicate_slots': sorted(duplicate_ids),
        'sanitized_slots': sorted(placeholder_ids),
        'deficit': 0, 'reason': None,
    }


def next_midnight(value: dt.datetime | None = None) -> dt.datetime:
    current = value or now_sp()
    return (current + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def eta_seconds(pages: int) -> int:
    return int(pages) * MESSAGE_COUNT * SECONDS_PER_MESSAGE_PAGE


def deadline_for(pages: int, started: dt.datetime, margin_minutes: int) -> dt.datetime:
    return started + dt.timedelta(seconds=eta_seconds(pages), minutes=margin_minutes)


def fits_window(pages: int, config: dict, started: dt.datetime | None = None) -> bool:
    start = started or now_sp()
    return deadline_for(pages, start, int(config.get('margin_minutes') or 60)) < next_midnight(start)


def classify_rows(rows: list[dict], bank: dict, config: dict, state: dict) -> list[dict]:
    today = now_sp().date().isoformat()
    candidates = []
    for row in rows:
        if not active_production(row, exact_30=True):
            continue
        key = row_id(row)
        pages = pages_for(row)
        if pages > int(config.get('max_pages') or 150) or not fits_window(pages, config):
            continue
        template_state = state.get('templates', {}).get(key, {})
        if template_state.get('status') == 'pending':
            continue
        if template_state.get('last_started_date') == today:
            continue
        plan = build_repair(row, bank)
        if plan['action'] not in {
            'replace_red_reset',
            'replace_red_duplicates_reset',
            'replace_duplicates_reset',
            'reset_purple',
            'sanitize_first_name_reset',
        }:
            continue
        before = plan['before']
        mixed = bool(before['vermelho'] and before['roxo'])
        priority = (0 if mixed else 1 if before['vermelho'] else 2, pages, str(row.get('NAME') or ''))
        candidates.append({'row': row, 'plan': plan, 'priority': priority})
    return sorted(candidates, key=lambda item: item['priority'])


def colors_line(counts: dict) -> str:
    return f"🟢 {counts.get('verde', 0)}   ⚪ {counts.get('cinza', 0)}   🔴 {counts.get('vermelho', 0)}   🟣 {counts.get('roxo', 0)}"


def page_label(pages: int) -> str:
    return f'{pages} página' if int(pages) == 1 else f'{pages} páginas'


def discord_embed(event: str, item: dict) -> dict:
    name = compact_template_name(item.get('template') or '')
    palette = {
        'started': (0x3498DB, 'PROCESSAMENTO INICIADO'),
        'completed': (0x2ECC71, '100% VERDE'),
        'improved': (0x57F287, 'RESULTADO POSITIVO'),
        'no_progress': (0xF1C40F, 'SEM PROGRESSO'),
        'blocked': (0xE74C3C, 'PROCESSAMENTO BLOQUEADO'),
        'daily': (0x5865F2, 'RESUMO DIÁRIO'),
    }
    color, label = palette.get(event, (0x95A5A6, event.upper()))
    fields = []
    if event == 'daily':
        fields = [
            {'name': 'Templates processados', 'value': str(item.get('processed', 0)), 'inline': True},
            {'name': 'Concluídos/melhores', 'value': str(item.get('positive', 0)), 'inline': True},
            {'name': 'Bloqueados', 'value': str(item.get('blocked', 0)), 'inline': True},
            {'name': 'Resumo', 'value': item.get('summary') or 'Nenhuma alteração.', 'inline': False},
        ]
        title = f'Broadcast Templates — {label}'
    else:
        title = f'{label} — {name}'
        fields.append({'name': 'Template', 'value': item.get('template') or '-', 'inline': False})
        fields.append({'name': 'Escopo', 'value': f"{page_label(int(item.get('pages') or 0))} • 30 mensagens • {item.get('vertical') or '-'}", 'inline': True})
        if item.get('before'):
            fields.append({'name': 'Antes', 'value': colors_line(item['before']), 'inline': False})
        if item.get('after'):
            fields.append({'name': 'Depois', 'value': colors_line(item['after']), 'inline': False})
        fields.append({'name': 'Ação', 'value': item.get('action_label') or '-', 'inline': False})
        if item.get('approval_started_at_sp'):
            fields.append({'name': 'Approval', 'value': f"Iniciado {item['approval_started_at_sp'][11:16]} SP • Readback após {item.get('due_at_sp', '-')[11:16]} SP", 'inline': False})
        fields.append({'name': 'Próximo passo', 'value': item.get('next_step') or '-', 'inline': False})
    payload = {
        'content': '',
        'embeds': [{
            'title': title[:256],
            'color': color,
            'fields': fields[:25],
            'footer': {'text': f"Ciclo {item.get('cycle', '-')} • ID {str(item.get('template_id', '-'))[:8]}"},
            'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        }],
        'allowed_mentions': {'parse': []},
    }
    return payload


def post_discord(payload: dict, channel_id: str, dry_run: bool = False) -> str | None:
    command = [sys.executable, str(POSTER), '--channel-id', str(channel_id)]
    if dry_run:
        command.append('--dry-run')
    result = subprocess.run(command, input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f'discord_post_failed_rc_{result.returncode}:{result.stderr.strip()[:200]}')
    match = re.search(r'message_id=([0-9]+)', result.stdout)
    return match.group(1) if match else None


def post_event(state: dict, config: dict, event: str, item: dict, dry_run: bool = False) -> str | None:
    fingerprint_parts = [
        event, item.get('template_id'), item.get('cycle'),
        item.get('before'), item.get('after'), item.get('action_label'),
    ]
    if event == 'daily':
        # A premature empty digest must not suppress the real end-of-day result.
        fingerprint_parts.extend([
            item.get('processed'), item.get('positive'), item.get('blocked'), item.get('summary'),
        ])
    fingerprint_raw = json.dumps(fingerprint_parts, ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha256(fingerprint_raw.encode()).hexdigest()
    if not dry_run and fingerprint in state.setdefault('alerts', {}):
        return state['alerts'][fingerprint].get('message_id')
    message_id = post_discord(discord_embed(event, item), str(config.get('channel_id') or DEFAULT_CHANNEL), dry_run=dry_run)
    if not dry_run:
        state.setdefault('alerts', {})[fingerprint] = {'event': event, 'template_id': item.get('template_id'), 'at_sp': iso_sp(), 'message_id': message_id}
    return message_id


def safe_post_event(state: dict, config: dict, event: str, item: dict, dry_run: bool = False) -> str | None:
    try:
        return post_event(state, config, event, item, dry_run=dry_run)
    except Exception as exc:
        item['notify_error'] = f'{type(exc).__name__}:{str(exc)[:300]}'
        append_log('discord_notify_failed', event_name=event, template_id=item.get('template_id'), template=item.get('template'), error=item['notify_error'])
        return None


def remaining_daily_capacity(state: dict, configured_limit: int, today: str) -> int:
    started_today = sum(
        1
        for item in state.get('templates', {}).values()
        if item.get('last_started_date') == today
    )
    return max(0, int(configured_limit) - started_today)


async def capture_live():
    return await rollout.capture_rows_headers()


async def fetch_rows(ctx, headers) -> list[dict]:
    response = await ctx.request.get(LIST_URL, headers=headers)
    if response.status >= 300:
        raise RuntimeError(f'live_readback_failed_http_{response.status}')
    data = await response.json()
    if not isinstance(data, list):
        raise RuntimeError('live_readback_payload_not_list')
    dedup = {}
    for row in data:
        dedup[row_id(row) or str(row.get('NAME') or '')] = row
    return list(dedup.values())


async def approve(ctx, headers, template_id: str) -> None:
    attempts = []
    for url in (
        f'https://api.jbfdigital.com.br/broadcast/messenger/{template_id}/approve',
        f'https://api.jbfdigital.com.br/broadcast/Messenger/{template_id}/approve',
    ):
        response = await ctx.request.post(url, headers=headers)
        attempts.append(response.status)
        if response.status < 300:
            return
    raise RuntimeError('approval_failed_http_' + '_'.join(map(str, attempts)))


def safe_backup_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', name.lower()).strip('-')[:100]


def record_run(state: dict, run: dict) -> None:
    state.setdefault('runs', []).append(run)
    state['runs'] = state['runs'][-200:]
    state['updated_at_sp'] = iso_sp()


async def live_audit(notify: bool = False, dry_notify: bool = False) -> dict:
    config = load_json(CONFIG_PATH, default_config())
    state = load_json(STATE_PATH, default_state())
    bank = load_json(BANK_PATH, {'version': 1, 'records': {}})
    p = browser = ctx = page = None
    try:
        p, browser, ctx, page, rows, headers, post_url = await capture_live()
        sync = sync_bank(bank, rows)
        atomic_json(BANK_PATH, bank)
        targets = [row for row in rows if active_production(row, exact_30=True)]
        aggregate = Counter()
        summaries = []
        for row in targets:
            counts = counts_for(parse_messages(row))
            aggregate.update(counts)
            plan = build_repair(row, bank)
            summaries.append({
                'id': row_id(row),
                'template': row.get('NAME'),
                'company': row.get('COMPANY'),
                'pages': pages_for(row),
                'vertical': parse_vertical(str(row.get('NAME') or '')),
                'counts': counts,
                'action': plan['action'],
                'reason': plan.get('reason'),
                'deficit': int(plan.get('deficit') or 0),
                'duplicate_slots': plan.get('duplicate_slots') or [],
                'fits_window_now': fits_window(pages_for(row), config),
            })
        result = {'status': 'ok', 'at_sp': iso_sp(), 'rows_received': len(rows), 'targets_exact30': len(targets), 'counts': dict(aggregate), 'bank_sync': sync, 'templates': summaries}
        append_log('live_audit', rows=len(rows), targets=len(targets), counts=dict(aggregate))
        return result
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass
        if p:
            try: await p.stop()
            except Exception: pass


async def dispatch(apply: bool, auto_canary: bool, notify: bool, dry_notify: bool = False) -> dict:
    config = load_json(CONFIG_PATH, default_config())
    state = load_json(STATE_PATH, default_state())
    bank = load_json(BANK_PATH, {'version': 1, 'records': {}})
    if apply and not config.get('enabled'):
        raise RuntimeError('executor_disabled_in_config')
    p = browser = ctx = page = None
    run = {'at_sp': iso_sp(), 'mode': 'apply' if apply else 'dry_run', 'stage': config.get('stage'), 'templates': [], 'errors': []}
    try:
        p, browser, ctx, page, rows, headers, post_url = await capture_live()
        sync_bank(bank, rows)
        atomic_json(BANK_PATH, bank)
        candidates = classify_rows(rows, bank, config, state)
        if auto_canary or config.get('stage') == 'canary':
            chosen_id = str(config.get('canary_template_id') or '')
            if chosen_id:
                candidates = [item for item in candidates if row_id(item['row']) == chosen_id]
            candidates = candidates[:1]
        else:
            raw_limit = config.get('staged_templates_per_day') if config.get('stage') == 'staged' else config.get('full_templates_per_day')
            limit = remaining_daily_capacity(state, int(raw_limit or 3), now_sp().date().isoformat())
            candidates = candidates[:limit]
        for candidate in candidates:
            row = candidate['row']; plan = candidate['plan']; key = row_id(row); name = str(row.get('NAME') or '')
            messages_before = parse_messages(row)
            pages = pages_for(row); started = now_sp(); due = deadline_for(pages, started, int(config.get('margin_minutes') or 60))
            old = state.setdefault('templates', {}).get(key, {})
            cycle = int(old.get('cycle') or 0) + 1
            item = {
                'template_id': key, 'template': name, 'vertical': parse_vertical(name), 'pages': pages,
                'cycle': cycle, 'stage': config.get('stage'), 'before': plan['before'], 'action': plan['action'],
                'replaced_slots': [slot['message_id'] for slot in plan.get('replaced_slots', [])],
                'sanitized_slots': plan.get('sanitized_slots', []),
                'content_hash_before': content_hash(messages_before), 'content_hash_after': content_hash(plan['messages']),
                'approval_started_at_sp': iso_sp(started), 'due_at_sp': iso_sp(due),
                'no_progress_cycles': int(old.get('no_progress_cycles') or 0),
            }
            if plan['action'] in {'replace_red_reset', 'replace_red_duplicates_reset', 'replace_duplicates_reset'}:
                red_count = sum(1 for slot in plan['replaced_slots'] if slot.get('reason') in {'red', 'red_and_duplicate'})
                duplicate_count = sum(1 for slot in plan['replaced_slots'] if slot.get('reason') in {'duplicate', 'red_and_duplicate'})
                parts = []
                if red_count:
                    noun = 'vermelha substituída' if red_count == 1 else 'vermelhas substituídas'
                    parts.append(f'{red_count} {noun}')
                if duplicate_count:
                    noun = 'duplicada substituída' if duplicate_count == 1 else 'duplicadas substituídas'
                    parts.append(f'{duplicate_count} {noun}')
                item['action_label'] = ', '.join(parts) + ', reset global e Run Approval'
            elif plan['action'] == 'sanitize_first_name_reset':
                count = len(plan.get('sanitized_slots') or [])
                item['action_label'] = f'{{{{first_name}}}} removido de {count} mensagens, reset global e Run Approval'
            else:
                item['action_label'] = 'Conteúdo preservado, reset global do log e Run Approval'
            item['next_step'] = f"Aguardar ETA; readback automático após {due.strftime('%H:%M')} SP."
            if not apply:
                item['dry_run'] = True
                run['templates'].append(item)
                if notify:
                    safe_post_event(state, config, 'started', item, dry_run=dry_notify)
                continue
            stamp = started.strftime('%Y%m%d-%H%M%S')
            backup_path = BACKUP_ROOT / stamp / f'{safe_backup_name(name)}-before.json'
            atomic_json(backup_path, row)
            payload = deepcopy(row)
            payload['MESSAGES'] = json.dumps(plan['messages'], ensure_ascii=False, separators=(',', ':'))
            response = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
            if response.status >= 300:
                raise RuntimeError(f'post_failed_http_{response.status}:{name}')
            readback = None
            for delay_ms in (1500, 3000, 5000):
                await page.wait_for_timeout(delay_ms)
                readback_rows = await fetch_rows(ctx, headers)
                candidate_readback = next((candidate_row for candidate_row in readback_rows if row_id(candidate_row) == key), None)
                if candidate_readback:
                    candidate_messages = parse_messages(candidate_readback)
                    if content_hash(candidate_messages) == item['content_hash_after'] and counts_for(candidate_messages).get('cinza') == MESSAGE_COUNT:
                        readback = candidate_readback
                        break
            if not readback:
                raise RuntimeError(f'post_readback_did_not_converge_to_expected_gray_content:{name}')
            readback_messages = parse_messages(readback)
            if len(readback_messages) != MESSAGE_COUNT:
                raise RuntimeError(f'post_readback_message_count_mismatch:{name}')
            if content_hash(readback_messages) != item['content_hash_after']:
                raise RuntimeError(f'post_readback_content_hash_mismatch:{name}')
            if link_map(readback_messages) != link_map(messages_before):
                raise RuntimeError(f'post_readback_link_mismatch:{name}')
            reset_counts = counts_for(readback_messages)
            if reset_counts.get('cinza') != MESSAGE_COUNT:
                raise RuntimeError(f'post_readback_not_all_gray:{name}:{reset_counts}')
            await approve(ctx, headers, key)
            item.update({'status': 'pending', 'backup_path': str(backup_path), 'reset_counts': reset_counts, 'last_started_date': started.date().isoformat()})
            state['templates'][key] = item
            for replacement in plan.get('replaced_slots', []):
                record = bank.get('records', {}).get(replacement['text_cta_hash'])
                if record is not None:
                    record.setdefault('usage', []).append({'template': name, 'message_id': replacement['message_id'], 'installed_at': now_et().isoformat(timespec='seconds'), 'mode': 'fixed30_red_repair'})
                    record['usage'] = record['usage'][-100:]
            atomic_json(BANK_PATH, bank)
            # Persist the pending Approval before external notification. A Discord
            # transport failure must never make the checker lose the live cycle.
            state['updated_at_sp'] = iso_sp()
            atomic_json(STATE_PATH, state)
            if notify:
                item['discord_message_id'] = safe_post_event(state, config, 'started', item, dry_run=dry_notify)
            atomic_json(STATE_PATH, state)
            run['templates'].append(item)
            append_log('template_started', template_id=key, template=name, pages=pages, cycle=cycle, action=plan['action'], before=plan['before'], due_at_sp=item['due_at_sp'])
        record_run(state, run)
        atomic_json(STATE_PATH, state)
        return run
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass
        if p:
            try: await p.stop()
            except Exception: pass


async def check_due(notify: bool, dry_notify: bool = False) -> dict:
    config = load_json(CONFIG_PATH, default_config())
    state = load_json(STATE_PATH, default_state())
    pending = [item for item in state.get('templates', {}).values() if item.get('status') == 'pending' and dt.datetime.fromisoformat(item['due_at_sp']) <= now_sp()]
    if not pending:
        return {'status': 'ok', 'checked': 0, 'reason': 'nothing_due'}
    bank = load_json(BANK_PATH, {'version': 1, 'records': {}})
    p = browser = ctx = page = None
    results = []
    try:
        p, browser, ctx, page, rows, headers, post_url = await capture_live()
        sync_bank(bank, rows)
        atomic_json(BANK_PATH, bank)
        by_id = {row_id(row): row for row in rows}
        positive = True
        for item in pending:
            row = by_id.get(str(item['template_id']))
            if not row:
                item.update({'status': 'blocked', 'last_error': 'template_missing_on_readback', 'checked_at_sp': iso_sp()})
                event = 'blocked'; positive = False
                item['action_label'] = 'Template não encontrado no readback'
                item['next_step'] = 'Automação pausada para este template.'
            else:
                messages = parse_messages(row)
                after = counts_for(messages)
                before = item.get('before') or {}
                item['after'] = after
                item['checked_at_sp'] = iso_sp()
                if after.get('verde') == MESSAGE_COUNT:
                    event = 'completed'; item['status'] = 'completed'; item['no_progress_cycles'] = 0
                    item['action_label'] = 'Approval concluído com 30 mensagens verdes'
                    item['next_step'] = 'Template removido da fila; não será resetado novamente.'
                elif after.get('verde', 0) > before.get('verde', 0) or after.get('vermelho', 0) < before.get('vermelho', 0) or after.get('roxo', 0) < before.get('roxo', 0):
                    event = 'improved'; item['status'] = 'eligible_next_day'; item['no_progress_cycles'] = 0
                    item['action_label'] = 'Approval melhorou as contagens do template'
                    item['next_step'] = 'Nova rodada somente no próximo dia, se ainda houver vermelho ou roxo.'
                else:
                    event = 'no_progress'; positive = False
                    cycles = int(item.get('no_progress_cycles') or 0) + 1
                    item['no_progress_cycles'] = cycles
                    if cycles >= int(config.get('max_no_progress_cycles') or 2):
                        item['status'] = 'blocked'
                        item['next_step'] = 'Limite sem progresso atingido; revisão humana necessária.'
                    else:
                        item['status'] = 'eligible_next_day'
                        item['next_step'] = 'Uma última rodada poderá ocorrer no próximo dia.'
                    item['action_label'] = 'Contagens não melhoraram após o ETA completo'
            # Persist the readback decision before notifying so a temporary
            # Discord failure cannot repeat or erase the state transition.
            state['updated_at_sp'] = iso_sp()
            atomic_json(STATE_PATH, state)
            if notify:
                item['discord_result_message_id'] = safe_post_event(state, config, event, item, dry_run=dry_notify)
                atomic_json(STATE_PATH, state)
            results.append({'template_id': item['template_id'], 'event': event, 'after': item.get('after'), 'status': item['status']})
            append_log('template_readback', template_id=item['template_id'], template=item.get('template'), cycle=item.get('cycle'), outcome=event, before=item.get('before'), after=item.get('after'))
        current_stage = config.get('stage')
        stage_items = [item for item in state.get('templates', {}).values() if item.get('stage') == current_stage]
        stage_pending = any(item.get('status') == 'pending' for item in stage_items)
        stage_positive = bool(stage_items) and all(
            item.get('status') in {'completed', 'eligible_next_day'} and not int(item.get('no_progress_cycles') or 0)
            for item in stage_items
        )
        if current_stage == 'canary' and len(stage_items) == 1 and not stage_pending and stage_positive:
            state.setdefault('stage_evidence', {})['canary_passed'] = True
            if config.get('auto_promote'):
                config['stage'] = 'staged'
                atomic_json(CONFIG_PATH, config)
        elif current_stage == 'staged' and len(stage_items) >= int(config.get('staged_templates_per_day') or 3) and not stage_pending and stage_positive:
            state.setdefault('stage_evidence', {})['staged_passed'] = True
            if config.get('auto_promote'):
                config['stage'] = 'full'
                atomic_json(CONFIG_PATH, config)
        state['updated_at_sp'] = iso_sp()
        atomic_json(STATE_PATH, state)
        return {'status': 'ok', 'checked': len(results), 'results': results, 'stage': config.get('stage')}
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass
        if p:
            try: await p.stop()
            except Exception: pass


def daily_digest(
    notify: bool,
    dry_notify: bool = False,
    report_date: str | None = None,
    scheduled: bool = False,
) -> dict:
    config = load_json(CONFIG_PATH, default_config())
    state = load_json(STATE_PATH, default_state())
    current = now_sp()
    if scheduled and current.hour != DIGEST_HOUR_SP:
        return {
            'status': 'skip',
            'reason': 'outside_digest_hour_sp',
            'now_sp': current.isoformat(timespec='seconds'),
            'expected_hour_sp': DIGEST_HOUR_SP,
        }
    if report_date:
        today = dt.date.fromisoformat(report_date).isoformat()
    else:
        today = current.date().isoformat()
    items = [item for item in state.get('templates', {}).values() if str(item.get('approval_started_at_sp') or '').startswith(today)]
    positive = sum(1 for item in items if item.get('status') in {'completed', 'eligible_next_day'} and not item.get('no_progress_cycles'))
    blocked = sum(1 for item in items if item.get('status') == 'blocked')
    rows = []
    for item in sorted(items, key=lambda value: value.get('template') or '')[:12]:
        before = item.get('before') or {}; after = item.get('after') or {}
        rows.append(f"{compact_template_name(item.get('template') or '', 42):<42} | {before.get('verde',0):>2}→{after.get('verde','-'):>2} Vd | {before.get('vermelho',0):>2}→{after.get('vermelho','-'):>2} Vm | {before.get('roxo',0):>2}→{after.get('roxo','-'):>2} Rx | {item.get('status','-')}")
    summary = '```\nTemplate                                   | Verde | Verm. | Roxo  | Estado\n' + '\n'.join(rows) + '\n```' if rows else 'Nenhum template processado hoje.'
    item = {'processed': len(items), 'positive': positive, 'blocked': blocked, 'summary': summary, 'template_id': 'daily', 'cycle': today}
    message_id = safe_post_event(state, config, 'daily', item, dry_run=dry_notify) if notify else None
    atomic_json(STATE_PATH, state)
    return {'status': 'ok', 'processed': len(items), 'positive': positive, 'blocked': blocked, 'message_id': message_id}


def status() -> dict:
    config = load_json(CONFIG_PATH, default_config())
    state = load_json(STATE_PATH, default_state())
    counts = Counter(item.get('status') or 'unknown' for item in state.get('templates', {}).values())
    return {'config': config, 'state_updated_at_sp': state.get('updated_at_sp'), 'template_status_counts': dict(counts), 'runs': len(state.get('runs', []))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['audit', 'dispatch', 'check', 'digest', 'status', 'render-demo'])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--auto-canary', action='store_true')
    parser.add_argument('--notify', action='store_true')
    parser.add_argument('--dry-notify', action='store_true')
    parser.add_argument('--scheduled', action='store_true')
    parser.add_argument('--date')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    lock = acquire_lock()
    if lock is None:
        print(json.dumps({'status': 'skip', 'reason': 'another_instance_running'}))
        return 0
    try:
        if args.command == 'audit':
            result = asyncio.run(live_audit(notify=args.notify, dry_notify=args.dry_notify))
        elif args.command == 'dispatch':
            result = asyncio.run(dispatch(apply=args.apply, auto_canary=args.auto_canary, notify=args.notify, dry_notify=args.dry_notify))
        elif args.command == 'check':
            result = asyncio.run(check_due(notify=args.notify, dry_notify=args.dry_notify))
        elif args.command == 'digest':
            result = daily_digest(
                notify=args.notify,
                dry_notify=args.dry_notify,
                report_date=args.date,
                scheduled=args.scheduled,
            )
        elif args.command == 'status':
            result = status()
        else:
            demo = {
                'template_id': '12345', 'template': 'Wantabrand - US-CC-EN - g001-d Ciro', 'vertical': 'US-CC-EN', 'pages': 12,
                'cycle': 1, 'before': {'verde': 9, 'cinza': 2, 'vermelho': 4, 'roxo': 15},
                'action_label': '4 vermelhas substituídas, reset global e Run Approval',
                'approval_started_at_sp': '2026-08-03T08:00:00-03:00', 'due_at_sp': '2026-08-03T10:12:00-03:00',
                'next_step': 'Aguardar ETA; readback automático sem alertas repetidos.',
            }
            result = discord_embed('started', demo)
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None))
        return 0
    except Exception as exc:
        append_log('command_failed', command=args.command, error=f'{type(exc).__name__}:{str(exc)[:500]}')
        print(json.dumps({'status': 'error', 'error': f'{type(exc).__name__}:{str(exc)}'}, ensure_ascii=False), file=sys.stderr)
        return 1
    finally:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
        except Exception:
            pass


if __name__ == '__main__':
    raise SystemExit(main())
