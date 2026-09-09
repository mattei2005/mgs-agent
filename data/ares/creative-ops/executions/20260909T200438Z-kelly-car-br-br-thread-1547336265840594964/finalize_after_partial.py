#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import shutil
from collections import deque
from pathlib import Path
from typing import Any

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260909T200438Z-kelly-car-br-br-thread-1547336265840594964')
RUNNER = BASE / 'process_batch.py'
DRY = BASE / 'runtime/dry-run.json'
STATE = BASE / 'runtime/state.json'
OUT = BASE / 'independent-verification-readback.json'
ROOT_ID = '0AEwt4Ye690ocUk9PVA'
EXPECTED_EMAIL = 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT = 'mgs-core-prod'
THREAD_ID = '1547336265840594964'
FOLDER_MIME = 'application/vnd.google-apps.folder'

spec = importlib.util.spec_from_file_location('batch_runner_finalize', RUNNER)
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
dry = json.loads(DRY.read_text(encoding='utf-8'))
state = json.loads(STATE.read_text(encoding='utf-8'))
plan = dry['plan']
inventory_rows, by_source, _, _ = mod.load_inventory()
errors: list[str] = []
rows: list[dict[str, Any]] = []
source_ids: list[str] = []
destination_ids: list[str] = []
readback_dir = BASE / 'verification-readback'
readback_dir.mkdir(parents=True, exist_ok=True)

for item in plan:
    sid = item['source_drive_id']
    st = state.get('items', {}).get(sid) or {}
    did = st.get('destination_drive_id')
    if not did:
        errors.append(f'missing destination state: {item["source_filename"]}')
        continue
    src = mod.api_get(drive, sid)
    dst = mod.api_get(drive, did)
    src_ok = (
        src.get('name') == item['source_filename']
        and src.get('parents') == [legacy_id]
        and src.get('driveId') == ROOT_ID
        and not src.get('trashed')
    )
    dst_ok = (
        dst.get('name') == item['destination_filename']
        and dst.get('parents') == [ready_id]
        and dst.get('driveId') == ROOT_ID
        and not dst.get('trashed')
    )
    if not src_ok:
        errors.append(f'source readback mismatch: {item["source_filename"]}')
    if not dst_ok:
        errors.append(f'destination readback mismatch: {item["destination_filename"]}')
    rb = readback_dir / f'{item["index"]:02d}-{item["destination_filename"]}'
    drive.download(did, rb)
    actual_sha = mod.sha256_file(rb)
    sha_ok = actual_sha == item['clean_sha256']
    if not sha_ok:
        errors.append(f'destination SHA mismatch: {item["destination_filename"]}')
    metadata_ok = True
    try:
        mod.verify_clean(rb)
    except Exception as exc:
        metadata_ok = False
        errors.append(f'metadata verify failed: {item["destination_filename"]}: {exc}')
    inv = by_source.get(sid)
    inv_ok = bool(
        inv
        and inv.get('asset_drive_id') == did
        and inv.get('canonical_filename') == item['destination_filename']
        and inv.get('clean_checksum') == item['clean_sha256']
        and inv.get('metadata_clean') is True
        and inv.get('reservation_status') == 'RESERVADO_PELO_GESTOR'
        and inv.get('ares_eligible') is False
        and inv.get('thread_id') == THREAD_ID
    )
    if not inv_ok:
        errors.append(f'inventory mismatch: {item["source_filename"]}')
    source_ids.append(sid)
    destination_ids.append(did)
    rows.append({
        'index': item['index'], 'status': '01_READY', 'disposition': item['disposition'],
        'source_drive_id': sid, 'source_filename': item['source_filename'],
        'destination_drive_id': did, 'destination_filename': item['destination_filename'],
        'source_sha256': item['source_sha256'], 'clean_sha256': item['clean_sha256'],
        'drive_md5': dst.get('md5Checksum'), 'bytes_clean': int(dst.get('size') or 0),
        'metadata_clean': metadata_ok, 'drive_readback_verified': dst_ok,
        'sha256_readback_verified': sha_ok, 'vehicle_type': item['vehicle_type'],
        'person': item['person'], 'p_orient': item['p_orient'], 'angle': item['angle'],
        'variant': item['variant'], 'claim': item['claim'],
        'perceptual_fingerprint': item['perceptual_fingerprint'],
        'webViewLink': dst.get('webViewLink'), 'source_parent_verified': src_ok,
        'inventory_verified': inv_ok,
    })

pending: list[dict[str, Any]] = []
queue = deque([upload_id])
while queue:
    parent = queue.popleft()
    for child in mod.list_children(drive, parent):
        if child.get('mimeType') == FOLDER_MIME:
            queue.append(child['id'])
        else:
            pending.append(child)
scoped_names = set(mod.CLASSIFICATION)
scoped_pending = [item for item in pending if item.get('name') in scoped_names]
out_of_scope_pending = [item for item in pending if item.get('name') not in scoped_names]

if len(rows) != 20:
    errors.append(f'report row count mismatch: {len(rows)}')
if len(set(source_ids)) != 20:
    errors.append(f'unique source ID mismatch: {len(set(source_ids))}')
if len(set(destination_ids)) != 20:
    errors.append(f'unique destination ID mismatch: {len(set(destination_ids))}')
if scoped_pending:
    errors.append(f'scoped BR-CAR files still pending: {len(scoped_pending)}')

stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
csv_path = BASE / f'ready-execution-{stamp}.csv'
fields = ['index','status','disposition','source_drive_id','source_filename','destination_drive_id','destination_filename','source_sha256','clean_sha256','drive_md5','bytes_clean','metadata_clean','drive_readback_verified','sha256_readback_verified','vehicle_type','person','p_orient','angle','variant','claim','perceptual_fingerprint','webViewLink']
with csv_path.open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, '') for key in fields})

verification = {
    'verified_at_utc': mod.utcnow(), 'all_pass': not errors,
    'auth_mode': auth_mode, 'service_account_validated': True,
    'project_validated': True, 'shared_drive': shared.get('name'),
    'operation': 'CAR_BR_BR', 'source_lineages': len(rows),
    'unique_source_ids': len(set(source_ids)), 'unique_ready_assets': len(set(destination_ids)),
    'ready_destinations_downloaded_sha_verified_clean': sum(bool(row['metadata_clean'] and row['sha256_readback_verified']) for row in rows),
    'legacy_sources_verified': sum(bool(row['source_parent_verified']) for row in rows),
    'inventory_links_verified': sum(bool(row['inventory_verified']) for row in rows),
    'reservation_fail_closed_verified': sum(bool(row['inventory_verified']) for row in rows),
    'scoped_upload_manual_remaining_files': len(scoped_pending),
    'out_of_scope_upload_manual_remaining_files': len(out_of_scope_pending),
    'upload_manual_remaining_files_recursive': len(pending),
    'errors': errors,
    'items': [
        {
            'source_filename': row['source_filename'],
            'destination_filename': row['destination_filename'],
            'source_parent_verified': row['source_parent_verified'],
            'destination_parent_verified': row['drive_readback_verified'],
            'metadata_clean_verified': row['metadata_clean'],
            'sha256_readback_verified': row['sha256_readback_verified'],
            'inventory_verified': row['inventory_verified'],
        }
        for row in rows
    ],
}
OUT.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding='utf-8')
(BASE / 'independent-verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding='utf-8')
manifest = {
    'generated_at_utc': mod.utcnow(), 'operation': 'CAR_BR_BR',
    'requested_by': 'Kelly Nice', 'thread_id': THREAD_ID,
    'source_lineages': len(rows), 'unique_ready_assets': len(set(destination_ids)),
    'duplicate_sources': sum(row['disposition'] != 'UNIQUE_READY' for row in rows),
    'metadata_clean_verified': sum(bool(row['metadata_clean']) for row in rows),
    'raw_legacy_verified': sum(bool(row['source_parent_verified']) for row in rows),
    'scoped_upload_manual_remaining_files': len(scoped_pending),
    'out_of_scope_upload_manual_remaining_files': len(out_of_scope_pending),
    'upload_manual_remaining_files_recursive': len(pending),
    'reservation_status': 'RESERVADO_PELO_GESTOR', 'ares_eligible': False,
    'ready_parent_id': ready_id, 'legacy_parent_id': legacy_id,
    'report_csv': str(csv_path),
    'items': [
        {
            'source_filename': row['source_filename'],
            'destination_filename': row['destination_filename'],
            'disposition': row['disposition'], 'vehicle_type': row['vehicle_type'],
            'claim': row['claim'], 'angle': row['angle'],
            'person': row['person'], 'p_orient': row['p_orient'],
        }
        for row in rows
    ],
}
manifest_path = BASE / f'ready-execution-{stamp}.json'
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(BASE / 'ready-execution-latest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
if not errors:
    shutil.rmtree(readback_dir)
    work_dir = BASE / 'runtime/work'
    if work_dir.exists():
        shutil.rmtree(work_dir)
print(json.dumps({
    'done': not errors, 'source_lineages': len(rows),
    'unique_ready_assets': len(set(destination_ids)),
    'metadata_clean_verified': sum(bool(row['metadata_clean']) for row in rows),
    'legacy_sources_verified': sum(bool(row['source_parent_verified']) for row in rows),
    'inventory_links_verified': sum(bool(row['inventory_verified']) for row in rows),
    'scoped_upload_manual_remaining_files': len(scoped_pending),
    'out_of_scope_upload_manual_remaining_files': len(out_of_scope_pending),
    'errors': errors, 'manifest': str(manifest_path), 'verification': str(OUT),
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 2)
