#!/usr/bin/env python3
import csv
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260904T142558Z-kelly-shein-us-en-thread-1545439313246818334')
RUN = BASE / 'process_batch.py'
REPORT = BASE / 'ready-execution-latest.json'
OUT = BASE / 'independent-verification-readback.json'
EXPECTED_OPERATION_ID = '1yV7Uge_KFN_Sih-iuVd7FY68cpfCUrxi'

spec = importlib.util.spec_from_file_location('shein_intake_verify', RUN)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load run-local verification module')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ex = mod.load_executor()
ex.load_env()
sa = ex.service_account()
if sa.get('client_email') != mod.EXPECTED_EMAIL or sa.get('project_id') != mod.EXPECTED_PROJECT:
    raise RuntimeError('canonical service-account identity mismatch')
token, auth_mode = ex.build_access_token()
if auth_mode != 'service_account':
    raise RuntimeError('non-service-account auth refused')
drive = ex.Drive(token)
root = drive.preflight_destination(auth_mode)
shared = drive.request(f'https://www.googleapis.com/drive/v3/drives/{mod.ROOT_ID}?fields=id,name') or {}
report = json.loads(REPORT.read_text(encoding='utf-8'))
rows = list(csv.DictReader(open(report['report_csv'], encoding='utf-8')))
records, by_source, _, _ = mod.load_inventory()
errors = []
items = []
source_ids = []
dest_ids = []
readback_dir = BASE / 'independent-readback'
readback_dir.mkdir(parents=True, exist_ok=True)

operation_id = mod.resolve_existing_path(drive, ['CRIATIVOS', mod.OPERATION])
if operation_id != EXPECTED_OPERATION_ID:
    errors.append('canonical SHEIN_US_EN folder ID mismatch')
ready_id = mod.resolve_existing_path(drive, ['CRIATIVOS', mod.OPERATION, 'VID', '01_READY'])
legacy_id = mod.resolve_existing_path(drive, ['CRIATIVOS', mod.OPERATION, 'VID', '99_LEGACY'])
upload_id = mod.resolve_existing_path(drive, ['CRIATIVOS', 'UPLOAD MANUAL'])

for row in rows:
    sid = row['source_drive_id']
    did = row['destination_drive_id']
    source_ids.append(sid)
    dest_ids.append(did)
    src = mod.api_get(drive, sid)
    dst = mod.api_get(drive, did)
    source_ok = (
        src.get('driveId') == mod.ROOT_ID
        and src.get('parents') == [legacy_id]
        and src.get('name') == row['source_filename']
        and not src.get('trashed')
    )
    dest_ok = (
        dst.get('driveId') == mod.ROOT_ID
        and dst.get('parents') == [ready_id]
        and dst.get('name') == row['destination_filename']
        and int(dst.get('size') or 0) == int(row['bytes_clean'])
        and not dst.get('trashed')
    )
    rb = readback_dir / f"{int(row['index']):03d}.mp4"
    drive.download(did, rb)
    sha_ok = mod.sha256_file(rb) == row['clean_sha256']
    verify = subprocess.run(
        [str(mod.SANITIZER), 'verify', str(rb)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    clean_ok = verify.returncode == 0 and 'clean: true' in verify.stdout
    rb.unlink(missing_ok=True)
    inv = by_source.get(sid)
    inventory_ok = bool(
        inv
        and inv.get('asset_drive_id') == did
        and inv.get('canonical_filename') == row['destination_filename']
        and inv.get('vertical') == 'SHEIN'
        and inv.get('country') == 'US'
        and inv.get('language') == 'EN'
        and inv.get('strategy') == 'TRAFEGO_DIRETO'
        and inv.get('format') == 'VID'
        and inv.get('angle') == row['angle']
        and inv.get('product_type') == row['product_type']
        and inv.get('p_orient') == row['p_orient']
        and inv.get('metadata_clean') is True
        and inv.get('reservation_status') == 'RESERVADO_PELO_GESTOR'
        and inv.get('ares_eligible') is False
        and inv.get('thread_id') == mod.THREAD_ID
    )
    if not source_ok:
        errors.append(f"source readback mismatch: {row['source_filename']}")
    if not dest_ok:
        errors.append(f"destination readback mismatch: {row['destination_filename']}")
    if not sha_ok:
        errors.append(f"destination SHA mismatch: {row['destination_filename']}")
    if not clean_ok:
        errors.append(f"destination metadata not clean: {row['destination_filename']}")
    if not inventory_ok:
        errors.append(f"inventory mismatch: {row['source_filename']}")
    items.append({
        'source_filename': row['source_filename'],
        'destination_filename': row['destination_filename'],
        'source_parent_verified': source_ok,
        'destination_parent_verified': dest_ok,
        'sha256_readback_verified': sha_ok,
        'metadata_clean_verified': clean_ok,
        'inventory_verified': inventory_ok,
    })

pending_direct = [x for x in mod.list_children(drive, upload_id) if x.get('mimeType') != mod.FOLDER_MIME]
if pending_direct:
    errors.append(f'UPLOAD MANUAL pending direct media: {len(pending_direct)}')
if len(rows) != 25 or len(set(source_ids)) != 25 or len(set(dest_ids)) != 25:
    errors.append('lineage/destination uniqueness or count mismatch')
if root.get('driveId') != mod.ROOT_ID or shared.get('id') != mod.ROOT_ID or shared.get('name') != mod.EXPECTED_DRIVE:
    errors.append('Shared Drive identity readback mismatch')

result = {
    'verified_at_utc': mod.utcnow(),
    'all_pass': not errors,
    'auth_mode': auth_mode,
    'service_account_identity_verified': True,
    'shared_drive': shared.get('name'),
    'operation': mod.OPERATION,
    'operation_folder_id_verified': operation_id == EXPECTED_OPERATION_ID,
    'source_lineages': len(set(source_ids)),
    'unique_ready_assets': len(set(dest_ids)),
    'ready_download_sha_clean_verified': sum(x['destination_parent_verified'] and x['sha256_readback_verified'] and x['metadata_clean_verified'] for x in items),
    'legacy_sources_verified': sum(x['source_parent_verified'] for x in items),
    'inventory_rows_verified': sum(x['inventory_verified'] for x in items),
    'reservation_fail_closed_verified': sum(x['inventory_verified'] for x in items),
    'upload_manual_direct_remaining_files': len(pending_direct),
    'errors': errors,
    'items': items,
}
mod.jdump(OUT, result)
print(json.dumps({k: v for k, v in result.items() if k != 'items'}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 2)
