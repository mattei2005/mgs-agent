#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import urllib.parse
from collections import deque
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260903T1752-kelly-car-br-br-thread-1545129145665593426')
RUNNER = BASE / 'process_batch.py'
REPORT_CSV = sorted(BASE.glob('ready-execution-*.csv'))[-1]
OUT = BASE / 'independent-verification-readback.json'
ROOT_ID = '0AEwt4Ye690ocUk9PVA'
EXPECTED_EMAIL = 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT = 'mgs-core-prod'
FOLDER_MIME = 'application/vnd.google-apps.folder'

spec = importlib.util.spec_from_file_location('batch_runner_verify', RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load batch runner')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ex = mod.load_executor()
ex.load_env()
sa = ex.service_account()
if sa.get('client_email') != EXPECTED_EMAIL or sa.get('project_id') != EXPECTED_PROJECT:
    raise RuntimeError('canonical service account identity mismatch')
token, auth_mode = ex.build_access_token()
if auth_mode != 'service_account':
    raise RuntimeError('non-service-account auth refused')
drive = ex.Drive(token)
root = drive.preflight_destination(auth_mode)
shared = drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
if root.get('driveId') != ROOT_ID or shared.get('name') != 'MGS-AGENTS':
    raise RuntimeError('canonical Shared Drive validation failed')

upload_id = mod.resolve_existing_path(drive, ['CRIATIVOS', 'UPLOAD MANUAL'])
ready_id = mod.resolve_existing_path(drive, ['CRIATIVOS', 'CAR_BR_BR', 'VID', '01_READY'])
legacy_id = mod.resolve_existing_path(drive, ['CRIATIVOS', 'CAR_BR_BR', 'VID', '99_LEGACY'])
rows = list(csv.DictReader(REPORT_CSV.open(encoding='utf-8')))
inventory_rows, by_source, _, _ = mod.load_inventory()
duplicate_owner = {}
for inv in inventory_rows:
    for sid in inv.get('duplicate_source_drive_ids') or []:
        duplicate_owner[sid] = inv

errors = []
items = []
source_ids = []
destination_ids = []
verified_destinations = set()
readback_dir = BASE / 'verification-readback'
readback_dir.mkdir(parents=True, exist_ok=True)
for idx, row in enumerate(rows, 1):
    sid = row['source_drive_id']
    did = row['destination_drive_id']
    source_ids.append(sid)
    destination_ids.append(did)
    src = mod.api_get(drive, sid)
    dst = mod.api_get(drive, did)
    src_ok = src.get('name') == row['source_filename'] and src.get('parents') == [legacy_id] and src.get('driveId') == ROOT_ID and not src.get('trashed')
    dst_ok = dst.get('name') == row['destination_filename'] and dst.get('parents') == [ready_id] and dst.get('driveId') == ROOT_ID and not dst.get('trashed')
    if not src_ok:
        errors.append(f'source readback mismatch: {row["source_filename"]}')
    if not dst_ok:
        errors.append(f'destination readback mismatch: {row["destination_filename"]}')
    if did not in verified_destinations:
        rb = readback_dir / f'{idx:02d}-{row["destination_filename"]}'
        drive.download(did, rb)
        actual_sha = mod.sha256_file(rb)
        if actual_sha != row['clean_sha256']:
            errors.append(f'destination SHA mismatch: {row["destination_filename"]}')
        try:
            mod.verify_clean(rb)
        except Exception as exc:
            errors.append(f'metadata verify failed: {row["destination_filename"]}: {exc}')
        verified_destinations.add(did)
    if row['disposition'] == 'UNIQUE_READY':
        inv = by_source.get(sid)
        inv_ok = bool(inv and inv.get('asset_drive_id') == did and inv.get('canonical_filename') == row['destination_filename'] and inv.get('metadata_clean') is True and inv.get('reservation_status') == 'RESERVADO_PELO_GESTOR' and inv.get('ares_eligible') is False and inv.get('thread_id') == '1545129145665593426')
    else:
        inv = duplicate_owner.get(sid)
        inv_ok = bool(inv and inv.get('asset_drive_id') == did and inv.get('canonical_filename') == row['destination_filename'] and inv.get('metadata_clean') is True and inv.get('reservation_status') == 'RESERVADO_PELO_GESTOR' and inv.get('ares_eligible') is False)
    if not inv_ok:
        errors.append(f'inventory mismatch: {row["source_filename"]}')
    items.append({'source_filename': row['source_filename'], 'destination_filename': row['destination_filename'], 'disposition': row['disposition'], 'source_parent_verified': src_ok, 'destination_parent_verified': dst_ok, 'inventory_verified': inv_ok})

pending = []
queue = deque([upload_id])
while queue:
    parent = queue.popleft()
    for child in mod.list_children(drive, parent):
        if child.get('mimeType') == FOLDER_MIME:
            queue.append(child['id'])
        else:
            pending.append(child)

if len(rows) != 24:
    errors.append(f'report row count mismatch: {len(rows)}')
if len(set(source_ids)) != 24:
    errors.append(f'unique source ID mismatch: {len(set(source_ids))}')
if len(set(destination_ids)) != 23:
    errors.append(f'unique destination ID mismatch: {len(set(destination_ids))}')
if pending:
    errors.append(f'UPLOAD MANUAL pending media recursively: {len(pending)}')

result = {
    'verified_at_utc': mod.utcnow(),
    'all_pass': not errors,
    'auth_mode': auth_mode,
    'service_account_validated': True,
    'project_validated': True,
    'shared_drive': shared.get('name'),
    'operation': 'CAR_BR_BR',
    'source_lineages': len(rows),
    'unique_source_ids': len(set(source_ids)),
    'unique_ready_assets': len(set(destination_ids)),
    'ready_destinations_downloaded_sha_verified_clean': len(verified_destinations),
    'legacy_sources_verified': sum(x['source_parent_verified'] for x in items),
    'inventory_links_verified': sum(x['inventory_verified'] for x in items),
    'reservation_fail_closed_verified': sum(x['inventory_verified'] for x in items),
    'upload_manual_remaining_files_recursive': len(pending),
    'errors': errors,
    'items': items,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
for p in readback_dir.glob('*'):
    p.unlink()
readback_dir.rmdir()
print(json.dumps({k: v for k, v in result.items() if k != 'items'}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 2)
