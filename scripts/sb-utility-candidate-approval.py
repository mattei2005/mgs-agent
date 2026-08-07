#!/usr/bin/env python3
"""Approve model-written Utility copies before production-template reuse.

The script never creates copy text. It stages candidates authored by the current
Zeus model, preserves canary slot links/metadata, waits the full Approval ETA,
and promotes only live-green TEXT+CTA records into the durable approved bank.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import fcntl
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile
from collections import Counter
from copy import deepcopy

BASE = pathlib.Path('/root/mgs-agent')
CONFIG_PATH = BASE / 'data/sb-utility-candidate-approval-config.json'
CATALOG_PATH = BASE / 'data/sb-utility-generated-candidates.json'
STATE_PATH = BASE / 'data/sb-utility-candidate-approval-state.json'
BACKUP_ROOT = BASE / 'backups/sb-utility-candidate-approval'
LOG_PATH = BASE / 'logs/sb-utility-candidate-approval.jsonl'
LOCK_PATH = pathlib.Path('/tmp/sb-utility-candidate-approval.lock')

spec = importlib.util.spec_from_file_location('repair', BASE / 'scripts/sb-broadcast-template-repair.py')
assert spec and spec.loader
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def atomic_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
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


def append_log(event: str, **fields) -> None:
    row = {'at_sp': repair.iso_sp(), 'event': event, **fields}
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')


def default_state() -> dict:
    return {
        'version': 1,
        'created_at_sp': repair.iso_sp(),
        'updated_at_sp': repair.iso_sp(),
        'verticals': {},
        'runs': [],
        'alerts': {},
    }


def acquire_lock():
    handle = LOCK_PATH.open('w')
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def zero_width_words(text: str) -> str:
    parts = re.split(r'(\s+)', text or '')
    output = []
    words = 0
    for part in parts:
        output.append(part)
        if part.strip() and not part.isspace():
            words += 1
            if words % 2 == 0:
                output.append('\u200b')
    return ''.join(output)


def formatted_candidate(candidate: dict, vertical: str) -> dict:
    text = str(candidate.get('text') or '').strip()
    cta = str(candidate.get('cta_1') or '').strip()
    if vertical.endswith('-ES'):
        text = zero_width_words(text)
    return {
        'candidate_id': candidate.get('candidate_id'),
        'text': text,
        'cta_1': cta,
        'text_cta_hash': repair.text_cta_hash({'TEXT': text, 'CTA_1': cta}),
    }


def needs_by_vertical(rows: list[dict], bank: dict) -> dict[str, dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        if not repair.active_production(row, exact_30=True):
            continue
        plan = repair.build_repair(row, bank)
        if plan.get('action') != 'needs_generation':
            continue
        vertical = plan.get('vertical') or repair.parse_vertical(str(row.get('NAME') or ''))
        entry = grouped.setdefault(vertical, {'vertical': vertical, 'deficit': 0, 'templates': []})
        entry['deficit'] = max(int(entry['deficit']), int(plan.get('deficit') or 0))
        entry['templates'].append({
            'template_id': repair.row_id(row),
            'template': row.get('NAME'),
            'deficit': int(plan.get('deficit') or 0),
        })
    return grouped


def select_catalog_candidates(
    catalog: dict,
    vertical: str,
    count: int,
    bank: dict,
    state: dict,
    retained_texts: set[str],
) -> list[dict]:
    used_ids = {
        candidate_id
        for item in state.get('verticals', {}).values()
        for candidate_id in item.get('candidate_ids', [])
        if item.get('status') in {'pending', 'completed'}
    }
    selected = []
    seen = set(retained_texts)
    for raw in catalog.get('candidates', {}).get(vertical, []):
        candidate = formatted_candidate(raw, vertical)
        text_key = repair.normalized(candidate['text'])
        bank_record = bank.get('records', {}).get(candidate['text_cta_hash'], {})
        if candidate['candidate_id'] in used_ids or not text_key or text_key in seen:
            continue
        if int(bank_record.get('approved_count') or 0) > 0 or int(bank_record.get('rejected_count') or 0) > 0:
            continue
        seen.add(text_key)
        selected.append(candidate)
        if len(selected) == count:
            break
    return selected


def stage_messages(messages: list[dict], candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    ordered = sorted(messages, key=lambda item: int(item.get('MESSAGE_ID') or 0))
    if len(candidates) > len(ordered):
        raise ValueError('candidate_count_exceeds_canary_slots')
    target_slots = ordered[-len(candidates):] if candidates else []
    target_ids = {int(item.get('MESSAGE_ID') or 0) for item in target_slots}
    by_id = {
        int(slot.get('MESSAGE_ID') or 0): candidate
        for slot, candidate in zip(target_slots, candidates)
    }
    staged = []
    placements = []
    for original in ordered:
        message_id = int(original.get('MESSAGE_ID') or 0)
        message = repair.strip_status(original)
        if message_id in target_ids:
            candidate = by_id[message_id]
            message['TEXT'] = candidate['text']
            message['CTA_1'] = candidate['cta_1']
            message.pop('CTA 1', None)
            placements.append({
                'message_id': message_id,
                'candidate_id': candidate['candidate_id'],
                'text_cta_hash': candidate['text_cta_hash'],
            })
        staged.append(message)
    texts = [repair.normalized(item.get('TEXT') or '') for item in staged]
    if not all(texts) or len(texts) != len(set(texts)):
        raise ValueError('canary_unique_visible_text_guard')
    if repair.link_map(staged) != repair.link_map(ordered):
        raise ValueError('canary_link_invariant_guard')
    return staged, placements


def stage_limit(config: dict) -> int:
    stage = config.get('stage') or 'canary'
    key = {
        'canary': 'canary_verticals_per_day',
        'staged': 'staged_verticals_per_day',
        'full': 'full_verticals_per_day',
    }.get(stage, 'canary_verticals_per_day')
    return int(config.get(key) or 1)


def lifecycle_embed(event: str, item: dict) -> dict:
    palette = {
        'started': (0x3498DB, 'NOVAS COPIES EM APROVAÇÃO'),
        'completed': (0x2ECC71, 'NOVAS COPIES APROVADAS'),
        'partial': (0xF1C40F, 'APROVAÇÃO PARCIAL'),
        'blocked': (0xE74C3C, 'APROVAÇÃO BLOQUEADA'),
    }
    color, title = palette[event]
    fields = [
        {'name': 'Vertical', 'value': item.get('vertical') or '-', 'inline': True},
        {'name': 'Novas copies', 'value': str(len(item.get('candidate_ids') or [])), 'inline': True},
        {'name': 'Template canário', 'value': item.get('template') or '-', 'inline': False},
    ]
    if item.get('candidate_counts'):
        counts = item['candidate_counts']
        fields.append({'name': 'Readback', 'value': repair.colors_line(counts), 'inline': False})
    fields.append({'name': 'Próximo passo', 'value': item.get('next_step') or '-', 'inline': False})
    return {
        'content': '',
        'embeds': [{
            'title': title,
            'color': color,
            'fields': fields,
            'footer': {'text': f"Ciclo {item.get('cycle', '-')} • banco aprovado fail-closed"},
            'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        }],
        'allowed_mentions': {'parse': []},
    }


def notify(config: dict, event: str, item: dict, dry_run: bool = False) -> str | None:
    return repair.post_discord(
        lifecycle_embed(event, item),
        str(config.get('channel_id') or repair.DEFAULT_CHANNEL),
        dry_run=dry_run,
    )


async def plan() -> dict:
    bank = load_json(repair.BANK_PATH, {'version': 1, 'records': {}})
    p = browser = None
    try:
        p, browser, ctx, page, rows, headers, post_url = await repair.capture_live()
        needs = needs_by_vertical(rows, bank)
        return {'status': 'ok', 'at_sp': repair.iso_sp(), 'needs': needs}
    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()


async def stage(apply: bool, do_notify: bool, vertical_filter: str = '') -> dict:
    config = load_json(CONFIG_PATH, {})
    if apply and not config.get('enabled'):
        raise RuntimeError('candidate_executor_disabled')
    catalog = load_json(CATALOG_PATH, {'candidates': {}})
    state = load_json(STATE_PATH, default_state())
    bank = load_json(repair.BANK_PATH, {'version': 1, 'records': {}})
    p = browser = None
    run = {'at_sp': repair.iso_sp(), 'mode': 'apply' if apply else 'dry_run', 'stage': config.get('stage'), 'items': [], 'errors': []}
    try:
        p, browser, ctx, page, rows, headers, post_url = await repair.capture_live()
        needs = needs_by_vertical(rows, bank)
        by_name = {str(row.get('NAME') or ''): row for row in rows}
        choices = []
        for vertical, need in sorted(needs.items(), key=lambda pair: (-pair[1]['deficit'], pair[0])):
            if vertical_filter and vertical != vertical_filter:
                continue
            current = state.get('verticals', {}).get(vertical, {})
            if current.get('status') == 'pending':
                continue
            template_name = config.get('test_templates', {}).get(vertical)
            if not template_name:
                run['errors'].append(f'{vertical}:test_template_not_configured')
                continue
            row = by_name.get(template_name)
            if not row:
                run['errors'].append(f'{vertical}:test_template_not_found')
                continue
            messages = repair.parse_messages(row)
            if len(messages) != 20 or repair.pages_for(row) <= 0:
                run['errors'].append(f'{vertical}:invalid_test_template_shape')
                continue
            deficit = int(need['deficit'])
            target_slots = sorted(messages, key=lambda item: int(item.get('MESSAGE_ID') or 0))[-deficit:]
            retained_ids = {int(item.get('MESSAGE_ID') or 0) for item in target_slots}
            retained_texts = {
                repair.normalized(item.get('TEXT') or '')
                for item in messages
                if int(item.get('MESSAGE_ID') or 0) not in retained_ids
            }
            candidates = select_catalog_candidates(catalog, vertical, deficit, bank, state, retained_texts)
            if len(candidates) < deficit:
                run['errors'].append(f'{vertical}:catalog_deficit:{len(candidates)}/{deficit}')
                continue
            staged_messages, placements = stage_messages(messages, candidates)
            choices.append((vertical, need, row, messages, staged_messages, placements, candidates))
        choices = choices[:stage_limit(config)]
        for vertical, need, row, messages, staged_messages, placements, candidates in choices:
            current = state.get('verticals', {}).get(vertical, {})
            cycle = int(current.get('cycle') or 0) + 1
            started = repair.now_sp()
            due = started + dt.timedelta(
                seconds=repair.pages_for(row) * len(messages) * repair.SECONDS_PER_MESSAGE_PAGE,
                minutes=int(config.get('margin_minutes') or 60),
            )
            item = {
                'vertical': vertical,
                'template_id': repair.row_id(row),
                'template': row.get('NAME'),
                'pages': repair.pages_for(row),
                'cycle': cycle,
                'stage': config.get('stage'),
                'status': 'dry_run' if not apply else 'pending',
                'candidate_ids': [candidate['candidate_id'] for candidate in candidates],
                'placements': placements,
                'content_hash_before': repair.content_hash(messages),
                'content_hash_after': repair.content_hash(staged_messages),
                'approval_attempts': 0,
                'started_at_sp': repair.iso_sp(started),
                'due_at_sp': repair.iso_sp(due),
                'next_step': f"Readback automático após {due.strftime('%H:%M')} SP; somente verdes entram no banco.",
                'production_templates_waiting': need['templates'],
            }
            if not apply:
                run['items'].append(item)
                continue
            stamp = started.strftime('%Y%m%d-%H%M%S')
            backup = BACKUP_ROOT / stamp / f"{repair.safe_backup_name(str(row.get('NAME') or 'canary'))}-before.json"
            atomic_json(backup, row)
            payload = deepcopy(row)
            payload['MESSAGES'] = json.dumps(staged_messages, ensure_ascii=False, separators=(',', ':'))
            response = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
            if response.status >= 300:
                raise RuntimeError(f'candidate_post_failed_http_{response.status}:{vertical}')
            readback = None
            for delay_ms in (1500, 3000, 5000):
                await page.wait_for_timeout(delay_ms)
                fresh_rows = await repair.fetch_rows(ctx, headers)
                candidate_row = next((fresh for fresh in fresh_rows if repair.row_id(fresh) == repair.row_id(row)), None)
                if not candidate_row:
                    continue
                fresh_messages = repair.parse_messages(candidate_row)
                if repair.content_hash(fresh_messages) == item['content_hash_after'] and repair.counts_for(fresh_messages).get('cinza') == len(messages):
                    readback = candidate_row
                    break
            if not readback:
                raise RuntimeError(f'candidate_readback_not_all_gray:{vertical}')
            await repair.approve(ctx, headers, repair.row_id(row))
            item['approval_attempts'] = 1
            item['backup_path'] = str(backup)
            state.setdefault('verticals', {})[vertical] = item
            state['updated_at_sp'] = repair.iso_sp()
            atomic_json(STATE_PATH, state)
            if do_notify:
                item['discord_message_id'] = notify(config, 'started', item)
                atomic_json(STATE_PATH, state)
            run['items'].append(item)
            append_log('candidate_stage_started', vertical=vertical, template=item['template'], candidate_ids=item['candidate_ids'], due_at_sp=item['due_at_sp'])
        state.setdefault('runs', []).append(run)
        state['runs'] = state['runs'][-100:]
        state['updated_at_sp'] = repair.iso_sp()
        atomic_json(STATE_PATH, state)
        return run
    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()


async def check(do_notify: bool) -> dict:
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, default_state())
    bank = load_json(repair.BANK_PATH, {'version': 1, 'records': {}})
    pending = [
        item for item in state.get('verticals', {}).values()
        if item.get('status') == 'pending' and dt.datetime.fromisoformat(item['due_at_sp']) <= repair.now_sp()
    ]
    if not pending:
        return {'status': 'ok', 'checked': 0, 'reason': 'nothing_due'}
    p = browser = None
    results = []
    try:
        p, browser, ctx, page, rows, headers, post_url = await repair.capture_live()
        by_id = {repair.row_id(row): row for row in rows}
        for item in pending:
            row = by_id.get(str(item['template_id']))
            if not row:
                item['status'] = 'blocked'
                item['next_step'] = 'Template canário ausente; revisão humana necessária.'
                event = 'blocked'
            else:
                messages = repair.parse_messages(row)
                by_message_id = {int(message.get('MESSAGE_ID') or 0): message for message in messages}
                candidate_counts = Counter()
                drift = []
                for placement in item.get('placements', []):
                    message = by_message_id.get(int(placement['message_id']))
                    if not message or repair.text_cta_hash(message) != placement['text_cta_hash']:
                        drift.append(int(placement['message_id']))
                        continue
                    color = repair.status_color(message)
                    candidate_counts[color] += 1
                    repair.upsert_bank_observation(
                        bank,
                        str(item.get('template') or ''),
                        message,
                        color,
                        str(item.get('vertical') or ''),
                        repair.iso_sp(),
                    )
                if drift:
                    item['status'] = 'blocked'
                    item['next_step'] = 'Conteúdo do canário divergiu; automação pausada.'
                    item['last_error'] = 'candidate_content_drift'
                    event = 'blocked'
                else:
                    total = len(item.get('placements') or [])
                    item['candidate_counts'] = {
                        color: int(candidate_counts.get(color, 0))
                        for color in ('verde', 'cinza', 'vermelho', 'roxo')
                    }
                    if candidate_counts.get('verde', 0) == total:
                        item['status'] = 'completed'
                        item['next_step'] = 'Copies verdes salvas no banco; templates de produção ficam prontos para reparo.'
                        event = 'completed'
                    elif candidate_counts.get('cinza', 0) and not candidate_counts.get('vermelho', 0) and not candidate_counts.get('roxo', 0) and int(item.get('approval_attempts') or 0) < int(config.get('max_approval_attempts') or 3):
                        await repair.approve(ctx, headers, str(item['template_id']))
                        item['approval_attempts'] = int(item.get('approval_attempts') or 0) + 1
                        due = repair.now_sp() + dt.timedelta(
                            seconds=repair.pages_for(row) * len(messages) * repair.SECONDS_PER_MESSAGE_PAGE,
                            minutes=int(config.get('margin_minutes') or 60),
                        )
                        item['due_at_sp'] = repair.iso_sp(due)
                        item['next_step'] = f"Cinzas reenviadas para Approval; novo readback após {due.strftime('%H:%M')} SP."
                        event = 'partial'
                    else:
                        item['status'] = 'needs_generation'
                        item['next_step'] = 'Verdes foram preservadas; copies não aprovadas serão substituídas por novas candidatas.'
                        event = 'partial'
            item['checked_at_sp'] = repair.iso_sp()
            atomic_json(repair.BANK_PATH, bank)
            state['updated_at_sp'] = repair.iso_sp()
            atomic_json(STATE_PATH, state)
            if do_notify:
                item['discord_result_message_id'] = notify(config, event, item)
                atomic_json(STATE_PATH, state)
            results.append({'vertical': item.get('vertical'), 'status': item.get('status'), 'candidate_counts': item.get('candidate_counts')})
            append_log('candidate_readback', vertical=item.get('vertical'), status=item.get('status'), candidate_counts=item.get('candidate_counts'))
        current_stage = config.get('stage')
        stage_items = [item for item in state.get('verticals', {}).values() if item.get('stage') == current_stage]
        if stage_items and all(item.get('status') == 'completed' for item in stage_items) and config.get('auto_promote'):
            if current_stage == 'canary':
                config['stage'] = 'staged'
                atomic_json(CONFIG_PATH, config)
            elif current_stage == 'staged':
                config['stage'] = 'full'
                atomic_json(CONFIG_PATH, config)
        state['updated_at_sp'] = repair.iso_sp()
        atomic_json(STATE_PATH, state)
        atomic_json(repair.BANK_PATH, bank)
        return {'status': 'ok', 'checked': len(results), 'results': results, 'stage': config.get('stage')}
    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()


def status() -> dict:
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, default_state())
    return {
        'config': config,
        'state_updated_at_sp': state.get('updated_at_sp'),
        'verticals': state.get('verticals', {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['plan', 'stage', 'check', 'status'])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--notify', action='store_true')
    parser.add_argument('--vertical', default='')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    lock = acquire_lock()
    if lock is None:
        print(json.dumps({'status': 'skip', 'reason': 'another_instance_running'}))
        return 0
    try:
        if args.command == 'plan':
            result = asyncio.run(plan())
        elif args.command == 'stage':
            result = asyncio.run(stage(args.apply, args.notify, args.vertical))
        elif args.command == 'check':
            result = asyncio.run(check(args.notify))
        else:
            result = status()
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
