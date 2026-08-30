#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260830T213916Z-nicolas-cc-us-en')
RUN = BASE / 'run_intake.py'
PLAN = BASE / 'dry-run.json'
REPORT = BASE / 'ready-execution-latest.json'
REPORT_CSV = BASE / 'ready-execution.csv'
OUT = BASE / 'independent-verification.json'

spec = importlib.util.spec_from_file_location('run_intake', RUN)
if spec is None or spec.loader is None:
    raise RuntimeError('could not load independent verification module')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_, drive = mod.drive_client()
plan = json.loads(PLAN.read_text(encoding='utf-8'))
report = json.loads(REPORT.read_text(encoding='utf-8'))
records = mod.read_inventory()
by_source = {r.get('source_drive_id'): r for r in records}

errors = []
source_ids = []
dest_ids = []
items = []
for item in plan['items']:
    sid = item['source_drive_id']
    state = report.get('items', {}).get(sid, {})
    did = state.get('destination_drive_id') or item.get('destination_drive_id')
    if not did:
        errors.append(f"destination ID missing: {item['source_filename']}")
        continue
    source_ids.append(sid)
    dest_ids.append(did)
    src = mod.get_file(drive, sid)
    dst = mod.get_file(drive, did)
    if src.get('parents') != [plan['legacy_parent_id']] or src.get('name') != item['source_filename'] or src.get('trashed'):
        errors.append(f"source readback mismatch: {item['source_filename']}")
    if dst.get('parents') != [plan['ready_parent_id']] or dst.get('name') != item['destination_filename'] or dst.get('trashed'):
        errors.append(f"destination readback mismatch: {item['destination_filename']}")
    inv = by_source.get(sid)
    if not inv:
        errors.append(f"inventory missing: {item['source_filename']}")
    elif inv.get('asset_drive_id') != did or inv.get('canonical_filename') != item['destination_filename'] or inv.get('metadata_clean') is not True:
        errors.append(f"inventory mismatch: {item['source_filename']}")
    items.append({
        'source_drive_id': sid,
        'source_filename': item['source_filename'],
        'source_parent_verified': src.get('parents') == [plan['legacy_parent_id']],
        'destination_drive_id': did,
        'destination_filename': item['destination_filename'],
        'destination_parent_verified': dst.get('parents') == [plan['ready_parent_id']],
        'destination_size': int(dst.get('size') or 0),
        'destination_md5': dst.get('md5Checksum'),
        'inventory_verified': bool(inv and inv.get('asset_drive_id') == did and inv.get('metadata_clean') is True),
    })

pending = mod.list_children(drive, plan['upload_parent_id'], folders=False)
if pending:
    errors.append(f"UPLOAD MANUAL pending media: {len(pending)}")
if len(set(source_ids)) != 54:
    errors.append('source IDs are not unique')
if len(set(dest_ids)) != 54:
    errors.append('destination IDs are not unique')
if len(report.get('items', {})) != 54 or any(x.get('phase') != 'COMPLETE' for x in report.get('items', {}).values()):
    errors.append('execution report is not 54/54 COMPLETE')
rows = REPORT_CSV.read_text(encoding='utf-8').splitlines()
if len(rows) != 55:
    errors.append(f"execution CSV rows mismatch: {len(rows)-1}")

result = {
    'verified_at_utc': mod.now(),
    'drive_id': mod.ROOT_ID,
    'operation': mod.OPERATION,
    'source_count': len(source_ids),
    'unique_source_ids': len(set(source_ids)),
    'unique_destination_ids': len(set(dest_ids)),
    'ready_verified': sum(x['destination_parent_verified'] for x in items),
    'legacy_verified': sum(x['source_parent_verified'] for x in items),
    'inventory_verified': sum(x['inventory_verified'] for x in items),
    'upload_manual_remaining_files': len(pending),
    'report_complete_items': sum(x.get('phase') == 'COMPLETE' for x in report.get('items', {}).values()),
    'errors': errors,
    'items': items,
}
mod.atomic_json(OUT, result)
print(json.dumps({k: v for k, v in result.items() if k != 'items'}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 2)
