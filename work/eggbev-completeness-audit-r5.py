#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import re
import time
from pathlib import Path
from typing import Any

ROOT = Path('/root/mgs-agent')
PARENT_ID = '1539422731727147079'
GUILD_ID = '1185714635991679006'
ARES_ID = '1508864261504630925'
HUMAN_IDS = {'344196393512075265': 'Rodolfo Mattei', '1055570806945620030': 'Nicolas Holanda'}
IMPORT_DIR = ROOT / 'data/discord-thread-imports'
OUT_DIR = ROOT / 'data/ares/audits/eggbev/completeness-r5-20260902'
THREAD_ID_RE = re.compile(r'(?<!\d)(\d{15,25})(?!\d)')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


importer = load_module('discord_importer_r5', ROOT / 'scripts/import-discord-thread.py')
reconcile = load_module('discord_reconcile_r5', ROOT / 'scripts/ares-eggbev-thread-reconcile.py')
token = reconcile.load_token()


def api(method: str, path: str) -> tuple[int, Any]:
    return reconcile.request(token, method, path)


def archived(kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    before: str | None = None
    for _ in range(10):
        suffix = '?limit=100'
        if before:
            from urllib.parse import quote
            suffix += '&before=' + quote(before)
        status, body = api('GET', f'/channels/{PARENT_ID}/threads/archived/{kind}{suffix}')
        if status in {403, 404}:
            return rows
        if status != 200 or not isinstance(body, dict):
            raise RuntimeError(f'archived {kind} failed http={status}')
        page = body.get('threads') or []
        rows.extend(x for x in page if isinstance(x, dict))
        if not body.get('has_more') or not page:
            break
        before = str((page[-1].get('thread_metadata') or {}).get('archive_timestamp') or '')
        if not before:
            break
        time.sleep(0.25)
    return rows


status, active_body = api('GET', f'/guilds/{GUILD_ID}/threads/active')
if status != 200 or not isinstance(active_body, dict):
    raise RuntimeError(f'active threads failed http={status}')
active = [x for x in (active_body.get('threads') or []) if str(x.get('parent_id') or '') == PARENT_ID]
public = archived('public')
private = archived('private')

by_id: dict[str, dict[str, Any]] = {}
for source, rows in [('active', active), ('archived_public', public), ('archived_private', private)]:
    for row in rows:
        if str(row.get('parent_id') or '') != PARENT_ID:
            continue
        tid = str(row.get('id') or '')
        if not tid:
            continue
        by_id.setdefault(tid, dict(row))['_inventory_source'] = source

# Preserve recoverability if an API archived listing omits an accessible known thread.
for p in IMPORT_DIR.glob('*.json'):
    try:
        old = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    ch = old.get('channel') or {}
    if str(ch.get('parent_id') or '') == PARENT_ID and str(ch.get('id') or ''):
        by_id.setdefault(str(ch['id']), dict(ch))['_inventory_source'] = 'prior_import_reconciled'

OUT_DIR.mkdir(parents=True, exist_ok=True)
IMPORT_DIR.mkdir(parents=True, exist_ok=True)
thread_payloads: dict[str, dict[str, Any]] = {}
import_errors: list[dict[str, Any]] = []


def import_thread(tid: str, relationship: str) -> dict[str, Any] | None:
    try:
        channel = importer.api_get(f'/channels/{tid}', token)
        messages = importer.fetch_all_messages(tid, token, None)
    except SystemExit as exc:
        import_errors.append({'thread_id': tid, 'relationship': relationship, 'error': str(exc)[:300]})
        return None
    payload = {
        'source': tid,
        'imported_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'channel': channel,
        'message_count': len(messages),
        'messages': messages,
    }
    (IMPORT_DIR / f'{tid}.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (IMPORT_DIR / f'{tid}.md').write_text(importer.render_markdown(channel, messages, tid), encoding='utf-8')
    thread_payloads[tid] = payload
    return payload

for idx, tid in enumerate(sorted(by_id, key=int), 1):
    import_thread(tid, 'eggbev_parent')
    if idx % 10 == 0:
        time.sleep(0.5)

# Gather explicit cross-thread references from Rodolfo/Nicolas, including starter references.
def iter_human_messages(payload: dict[str, Any]):
    for message in payload.get('messages') or []:
        author_id = str((message.get('author') or {}).get('id') or '')
        if author_id in HUMAN_IDS:
            yield message, 'message'
        referenced = message.get('referenced_message')
        if isinstance(referenced, dict):
            ref_author = str((referenced.get('author') or {}).get('id') or '')
            if ref_author in HUMAN_IDS:
                yield referenced, 'referenced_starter'

candidates: set[str] = set()
for payload in list(thread_payloads.values()):
    for message, _ in iter_human_messages(payload):
        text = str(message.get('content') or '')
        candidates.update(THREAD_ID_RE.findall(text))

external_ids: set[str] = set()
for candidate in sorted(candidates, key=int):
    if candidate in thread_payloads or candidate in {PARENT_ID, GUILD_ID}:
        continue
    status, channel = api('GET', f'/channels/{candidate}')
    if status == 200 and isinstance(channel, dict) and int(channel.get('type') or -1) in {10, 11, 12}:
        external_ids.add(candidate)

for tid in sorted(external_ids, key=int):
    import_thread(tid, 'explicit_human_reference')

# Build deduplicated human corpus, starter-aware.
human_by_id: dict[str, dict[str, Any]] = {}
attachments: list[dict[str, Any]] = []
for tid, payload in thread_payloads.items():
    channel = payload.get('channel') or {}
    relation = 'eggbev_parent' if str(channel.get('parent_id') or '') == PARENT_ID else 'explicit_human_reference'
    for message, source_kind in iter_human_messages(payload):
        mid = str(message.get('id') or '')
        if not mid:
            continue
        author = message.get('author') or {}
        row = {
            'message_id': mid,
            'thread_id': tid,
            'thread_name': channel.get('name'),
            'thread_parent_id': str(channel.get('parent_id') or ''),
            'relationship': relation,
            'source_kind': source_kind,
            'author_id': str(author.get('id') or ''),
            'author_name': author.get('global_name') or author.get('username'),
            'timestamp': message.get('timestamp'),
            'content': str(message.get('content') or ''),
            'attachments': [],
        }
        for att in message.get('attachments') or []:
            a = {
                'attachment_id': str(att.get('id') or ''),
                'message_id': mid,
                'thread_id': tid,
                'author_id': row['author_id'],
                'timestamp': row['timestamp'],
                'filename': att.get('filename'),
                'content_type': att.get('content_type'),
                'size': att.get('size'),
                'width': att.get('width'),
                'height': att.get('height'),
                'url': att.get('url'),
            }
            row['attachments'].append(a)
            attachments.append(a)
        human_by_id.setdefault(mid, row)

human_rows = sorted(human_by_id.values(), key=lambda x: int(x['message_id']))
attachments_by_id = {x['attachment_id']: x for x in attachments if x['attachment_id']}
attachments = sorted(attachments_by_id.values(), key=lambda x: int(x['attachment_id']))

thread_manifest = []
total_messages = 0
for tid, payload in sorted(thread_payloads.items(), key=lambda kv: int(kv[0])):
    raw = json.dumps(payload.get('messages') or [], ensure_ascii=False, sort_keys=True).encode('utf-8')
    channel = payload.get('channel') or {}
    human_count = sum(1 for row in human_rows if row['thread_id'] == tid)
    total_messages += int(payload.get('message_count') or 0)
    thread_manifest.append({
        'thread_id': tid,
        'name': channel.get('name'),
        'parent_id': str(channel.get('parent_id') or ''),
        'relationship': 'eggbev_parent' if str(channel.get('parent_id') or '') == PARENT_ID else 'explicit_human_reference',
        'archived': bool((channel.get('thread_metadata') or {}).get('archived')),
        'message_count': int(payload.get('message_count') or 0),
        'human_message_or_starter_count': human_count,
        'messages_sha256': hashlib.sha256(raw).hexdigest(),
        'last_message_id': str(channel.get('last_message_id') or ''),
    })

first_nicolas = next((row for row in human_rows if row['author_id'] == '1055570806945620030'), None)
summary = {
    'audit_id': 'ARES-EGGBEV-COMPLETENESS-R5-20260902',
    'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'parent_channel_id': PARENT_ID,
    'inventory': {
        'active_threads': len(active),
        'archived_public_threads': len(public),
        'archived_private_threads': len(private),
        'eggbev_parent_threads_unique': sum(1 for x in thread_manifest if x['relationship'] == 'eggbev_parent'),
        'explicit_external_threads_imported': sum(1 for x in thread_manifest if x['relationship'] == 'explicit_human_reference'),
        'threads_total_imported': len(thread_manifest),
        'messages_total': total_messages,
        'human_messages_or_referenced_starters_unique': len(human_rows),
        'rodolfo_messages': sum(1 for x in human_rows if x['author_id'] == '344196393512075265'),
        'nicolas_messages': sum(1 for x in human_rows if x['author_id'] == '1055570806945620030'),
        'human_attachments': len(attachments),
        'import_errors': len(import_errors),
    },
    'first_nicolas_message': first_nicolas,
    'external_thread_ids': sorted(external_ids, key=int),
    'import_errors': import_errors,
}

(OUT_DIR / 'inventory-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT_DIR / 'thread-manifest.json').write_text(json.dumps(thread_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
with (OUT_DIR / 'human-messages.jsonl').open('w', encoding='utf-8') as fh:
    for row in human_rows:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
(OUT_DIR / 'human-attachments.json').write_text(json.dumps(attachments, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary['inventory'], ensure_ascii=False))
print(f"OUT_DIR={OUT_DIR}")
