#!/usr/bin/env python3
"""Remove {{first_name}} from every MGS SmartBidding Broadcast Template message.

Scope is always fail-closed to digital-trust + digital-trust-2. The operation:
- scans every row, including unlinked/test/NAO-USAR templates;
- changes only message string fields containing the exact placeholder;
- preserves message IDs, links, CTA/media and message counts;
- backs up each full row before POST;
- validates an all-gray immutable-content readback after each write;
- starts Approval only for linked templates;
- performs a final full-scope zero-placeholder readback.
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
import tempfile
from collections import Counter
from copy import deepcopy

BASE = pathlib.Path('/root/mgs-agent')
TOKEN = '{{first_name}}'
BACKUP_ROOT = BASE / 'backups/sb-remove-first-name'
LOG_ROOT = BASE / 'logs'
LOCK_PATH = pathlib.Path('/tmp/sb-remove-first-name.lock')

spec = importlib.util.spec_from_file_location('repair', BASE / 'scripts/sb-broadcast-template-repair.py')
assert spec and spec.loader
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def atomic_json(path: pathlib.Path, value) -> None:
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


def token_count(value) -> int:
    if isinstance(value, str):
        return value.count(TOKEN)
    if isinstance(value, list):
        return sum(token_count(item) for item in value)
    if isinstance(value, dict):
        return sum(token_count(item) for item in value.values())
    return 0


def sanitize_string(value: str) -> str:
    if TOKEN not in value:
        return value
    # Keep punctuation natural for the observed forms:
    # "Congratulations, {{first_name}}!" -> "Congratulations!"
    # "— {{first_name}}, your..." -> "— your..."
    out = re.sub(r',\s*\{\{first_name\}\}\s*!', '!', value)
    out = re.sub(r'\{\{first_name\}\}\s*,\s*', '', out)
    out = out.replace(TOKEN, '')
    out = re.sub(r'[ \t]+([,!?;:])', r'\1', out)
    out = re.sub(r'([ \t]){2,}', ' ', out)
    out = '\n'.join(line.rstrip() for line in out.split('\n'))
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out.strip()


def sanitize_message(message: dict) -> tuple[dict, list[str]]:
    changed = []
    result = deepcopy(message)
    for key, value in list(result.items()):
        if isinstance(value, str) and TOKEN in value:
            result[key] = sanitize_string(value)
            changed.append(key)
    return result, changed


def duplicate_excess(messages: list[dict]) -> int:
    counts = Counter(repair.normalized(str(item.get('TEXT') or '')) for item in messages)
    return sum(max(0, count - 1) for text, count in counts.items() if text)


def prepare_row(row: dict) -> dict | None:
    before = repair.parse_messages(row)
    if not token_count(before):
        return None
    after_with_status = []
    changed_slots = []
    changed_fields = Counter()
    for message in before:
        clean, fields = sanitize_message(message)
        after_with_status.append(clean)
        if fields:
            changed_slots.append(int(message.get('MESSAGE_ID') or 0))
            changed_fields.update(fields)
    after = [repair.strip_status(message) for message in after_with_status]
    if len(after) != len(before):
        raise RuntimeError('message_count_preflight_mismatch')
    if [int(item.get('MESSAGE_ID') or 0) for item in after] != [int(item.get('MESSAGE_ID') or 0) for item in before]:
        raise RuntimeError('message_id_preflight_mismatch')
    if repair.link_map(after) != repair.link_map(before):
        raise RuntimeError('link_preflight_mismatch')
    if token_count(after):
        raise RuntimeError('placeholder_remains_after_preflight')
    if any(not str(item.get('TEXT') or '').strip() for item in after):
        raise RuntimeError('empty_text_after_preflight')
    if duplicate_excess(after) > duplicate_excess(before):
        raise RuntimeError('new_visible_text_duplicate_after_preflight')
    return {
        'before_messages': before,
        'after_messages': after,
        'changed_slots': changed_slots,
        'changed_fields': dict(changed_fields),
        'tokens_removed': token_count(before),
        'content_hash_before': repair.content_hash(before),
        'content_hash_after': repair.content_hash(after),
        'links_before': repair.link_map(before),
        'before_counts': repair.counts_for(before),
    }


def row_by_id(rows: list[dict], template_id: str) -> dict | None:
    return next((row for row in rows if repair.row_id(row) == template_id), None)


async def converged_row(ctx, headers, page, template_id: str, expected_hash: str, expected_count: int):
    for delay_ms in (1000, 2000, 4000, 7000):
        await page.wait_for_timeout(delay_ms)
        rows = await repair.fetch_rows(ctx, headers)
        row = row_by_id(rows, template_id)
        if not row:
            continue
        messages = repair.parse_messages(row)
        if len(messages) != expected_count:
            continue
        if repair.content_hash(messages) != expected_hash:
            continue
        if token_count(messages):
            continue
        return row
    return None


def pending_state_item(row: dict, plan: dict, started: dt.datetime, config: dict, previous: dict) -> dict:
    pages = repair.pages_for(row)
    due = repair.deadline_for(pages, started, int(config.get('margin_minutes') or 60))
    return {
        'template_id': repair.row_id(row),
        'template': row.get('NAME'),
        'vertical': repair.parse_vertical(str(row.get('NAME') or '')),
        'pages': pages,
        'cycle': int(previous.get('cycle') or 0) + 1,
        'stage': config.get('stage'),
        'before': plan['before_counts'],
        'action': 'remove_first_name_placeholder',
        'replaced_slots': plan['changed_slots'],
        'content_hash_before': plan['content_hash_before'],
        'content_hash_after': plan['content_hash_after'],
        'approval_started_at_sp': repair.iso_sp(started),
        'due_at_sp': repair.iso_sp(due),
        'no_progress_cycles': int(previous.get('no_progress_cycles') or 0),
        'action_label': f"{{{{first_name}}}} removido de {len(plan['changed_slots'])} mensagens; Run Approval iniciado",
        'next_step': f"Aguardar ETA; readback automático após {due.strftime('%H:%M')} SP.",
        'status': 'pending',
        'last_started_date': started.date().isoformat(),
    }


async def run(apply: bool, only_template: str | None) -> dict:
    p = browser = None
    stamp = repair.now_sp().strftime('%Y%m%d-%H%M%S')
    backup_dir = BACKUP_ROOT / stamp
    config = repair.load_json(repair.CONFIG_PATH, repair.default_config())
    state = repair.load_json(repair.STATE_PATH, repair.default_state())
    summary = {
        'at_sp': repair.iso_sp(), 'mode': 'apply' if apply else 'audit',
        'scope_companies': sorted(repair.ALLOWED_COMPANIES), 'rows_received': 0,
        'affected_templates': 0, 'affected_messages': 0, 'tokens_found': 0,
        'changed_templates': 0, 'changed_messages': 0, 'tokens_removed': 0,
        'approvals_started': 0, 'templates': [], 'errors': [],
    }
    try:
        p, browser, ctx, page, captured_rows, headers, post_url = await repair.capture_live()
        rows = [row for row in captured_rows if str(row.get('COMPANY') or '').strip().lower() in repair.ALLOWED_COMPANIES]
        summary['rows_received'] = len(rows)
        targets = []
        for row in rows:
            if only_template and repair.row_id(row) != only_template and str(row.get('NAME') or '') != only_template:
                continue
            try:
                plan = prepare_row(row)
            except Exception as exc:
                summary['errors'].append({'template': row.get('NAME'), 'error': f'preflight:{type(exc).__name__}:{exc}'})
                continue
            if plan:
                targets.append((row, plan))
                summary['affected_messages'] += len(plan['changed_slots'])
                summary['tokens_found'] += int(plan['tokens_removed'])
        summary['affected_templates'] = len(targets)
        if summary['errors']:
            raise RuntimeError('preflight_failed')
        if not apply:
            summary['templates'] = [{
                'id': repair.row_id(row), 'name': row.get('NAME'), 'company': row.get('COMPANY'),
                'pages': repair.pages_for(row), 'messages': len(plan['before_messages']),
                'changed_messages': len(plan['changed_slots']), 'tokens': plan['tokens_removed'],
                'changed_fields': plan['changed_fields'],
            } for row, plan in targets]
            return summary

        for captured_row, captured_plan in targets:
            template_id = repair.row_id(captured_row)
            name = str(captured_row.get('NAME') or '')
            try:
                fresh_rows = await repair.fetch_rows(ctx, headers)
                fresh_row = row_by_id(fresh_rows, template_id)
                if not fresh_row:
                    raise RuntimeError('template_missing_before_write')
                fresh_plan = prepare_row(fresh_row)
                if not fresh_plan:
                    summary['templates'].append({'id': template_id, 'name': name, 'status': 'already_clean'})
                    continue
                if fresh_plan['content_hash_before'] != captured_plan['content_hash_before']:
                    raise RuntimeError('concurrent_content_change_before_write')
                backup_path = backup_dir / f'{repair.safe_backup_name(name)}-before.json'
                atomic_json(backup_path, fresh_row)
                payload = deepcopy(fresh_row)
                payload['MESSAGES'] = json.dumps(fresh_plan['after_messages'], ensure_ascii=False, separators=(',', ':'))
                response = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
                if response.status >= 300:
                    reconciled = await converged_row(ctx, headers, page, template_id, fresh_plan['content_hash_after'], len(fresh_plan['after_messages']))
                    if not reconciled and 500 <= response.status < 600:
                        response = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
                    if response.status >= 300 and not reconciled:
                        raise RuntimeError(f'post_failed_http_{response.status}')
                readback = await converged_row(ctx, headers, page, template_id, fresh_plan['content_hash_after'], len(fresh_plan['after_messages']))
                if not readback:
                    raise RuntimeError('post_readback_not_converged')
                readback_messages = repair.parse_messages(readback)
                if repair.link_map(readback_messages) != fresh_plan['links_before']:
                    raise RuntimeError('post_readback_link_mismatch')
                reset_counts = repair.counts_for(readback_messages)
                if reset_counts.get('cinza') != len(readback_messages):
                    raise RuntimeError(f'post_readback_not_all_gray:{reset_counts}')
                approval_started = False
                pages = repair.pages_for(readback)
                if pages > 0:
                    await repair.approve(ctx, headers, template_id)
                    approval_started = True
                    summary['approvals_started'] += 1
                if repair.active_production(readback, exact_30=True) and approval_started:
                    started = repair.now_sp()
                    previous = state.setdefault('templates', {}).get(template_id, {})
                    item = pending_state_item(readback, fresh_plan, started, config, previous)
                    item['backup_path'] = str(backup_path)
                    item['reset_counts'] = reset_counts
                    state['templates'][template_id] = item
                    state['updated_at_sp'] = repair.iso_sp()
                    repair.atomic_json(repair.STATE_PATH, state)
                summary['changed_templates'] += 1
                summary['changed_messages'] += len(fresh_plan['changed_slots'])
                summary['tokens_removed'] += int(fresh_plan['tokens_removed'])
                summary['templates'].append({
                    'id': template_id, 'name': name, 'company': readback.get('COMPANY'),
                    'pages': pages, 'messages': len(readback_messages),
                    'changed_messages': len(fresh_plan['changed_slots']),
                    'tokens_removed': fresh_plan['tokens_removed'],
                    'approval_started': approval_started, 'reset_counts': reset_counts,
                    'backup': str(backup_path), 'status': 'validated',
                })
            except Exception as exc:
                summary['errors'].append({'id': template_id, 'template': name, 'error': f'{type(exc).__name__}:{exc}'})
                break

        final_rows = await repair.fetch_rows(ctx, headers)
        remaining = []
        global_remaining = []
        verified_rows = 0
        for row in final_rows:
            if str(row.get('COMPANY') or '').strip().lower() not in repair.ALLOWED_COMPANIES:
                continue
            count = token_count(repair.parse_messages(row))
            if count:
                entry = {'id': repair.row_id(row), 'name': row.get('NAME'), 'tokens': count}
                global_remaining.append(entry)
                if not only_template or repair.row_id(row) == only_template or str(row.get('NAME') or '') == only_template:
                    remaining.append(entry)
            if not only_template or repair.row_id(row) == only_template or str(row.get('NAME') or '') == only_template:
                verified_rows += 1
        summary['final_rows_verified'] = verified_rows
        summary['remaining_templates'] = remaining
        summary['remaining_tokens'] = sum(item['tokens'] for item in remaining)
        if only_template:
            summary['global_remaining_templates'] = len(global_remaining)
            summary['global_remaining_tokens'] = sum(item['tokens'] for item in global_remaining)
        summary['status'] = 'ok' if not summary['errors'] and not remaining else 'partial'
        return summary
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass
        if p:
            try: await p.stop()
            except Exception: pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['audit', 'apply'])
    parser.add_argument('--template', help='Canary: exact template ID or name')
    args = parser.parse_args()
    lock = acquire_lock()
    if lock is None:
        print(json.dumps({'status': 'skip', 'reason': 'another_instance_running'}))
        return 0
    result = asyncio.run(run(apply=args.command == 'apply', only_template=args.template))
    log_path = LOG_ROOT / f'sb-remove-first-name-{repair.now_sp().strftime("%Y%m%d-%H%M%S")}.json'
    atomic_json(log_path, result)
    result['log'] = str(log_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get('status') not in {'partial'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
