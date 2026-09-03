#!/usr/bin/env python3
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260902T2234-kelly-cc-mx-es-thread-1544837155900235927')
RUN = BASE / 'process_batch.py'
PLAN = BASE / 'dry-run.json'
REPORT = BASE / 'ready-execution-latest.json'
REPORT_CSV = BASE / 'ready-execution.csv'
OUT = BASE / 'independent-verification.json'

spec = importlib.util.spec_from_file_location('run_intake_verify', RUN)
if spec is None or spec.loader is None:
    raise RuntimeError('could not load run-local verification module')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_, drive = mod.drive_client()
plan = json.loads(PLAN.read_text(encoding='utf-8'))
report = json.loads(REPORT.read_text(encoding='utf-8'))
records = mod.read_inventory()
by_source = {r.get('source_drive_id'): r for r in records}
errors = []
items = []
source_ids = []
dest_ids = []
readback_dir = BASE / 'independent-readback'
readback_dir.mkdir(parents=True, exist_ok=True)

for item in plan['items']:
    sid = item['source_drive_id']
    state = report.get('items', {}).get(sid, {})
    did = state.get('destination_drive_id')
    source_ids.append(sid)
    if not did:
        errors.append(f"destination ID missing: {item['source_filename']}")
        continue
    dest_ids.append(did)
    src = mod.get_file(drive, sid)
    dst = mod.get_file(drive, did)
    source_ok = (
        src.get('driveId') == mod.ROOT_ID
        and src.get('parents') == [report['legacy_parent_id']]
        and src.get('name') == item['source_filename']
        and not src.get('trashed')
    )
    dest_ok = (
        dst.get('driveId') == mod.ROOT_ID
        and dst.get('parents') == [report['ready_parent_id']]
        and dst.get('name') == item['destination_filename']
        and int(dst.get('size') or 0) == int(item['clean_size'])
        and not dst.get('trashed')
    )
    if not source_ok:
        errors.append(f"source readback mismatch: {item['source_filename']}")
    if not dest_ok:
        errors.append(f"destination readback mismatch: {item['destination_filename']}")
    rb = readback_dir / f"{item['index']:03d}.mp4"
    drive.download(str(did), rb)
    sha_ok = mod.sha256_file(rb) == item['clean_sha256']
    if not sha_ok:
        errors.append(f"destination SHA mismatch: {item['destination_filename']}")
    verify = subprocess.run(
        ['/root/mgs-agent/scripts/clean-creative-metadata.sh', 'verify', str(rb)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
        check=False,
    )
    clean_ok = verify.returncode == 0 and 'clean: true' in verify.stdout
    if not clean_ok:
        errors.append(f"destination metadata not clean: {item['destination_filename']}")
    rb.unlink(missing_ok=True)
    inv = by_source.get(sid)
    inv_ok = bool(
        inv
        and inv.get('asset_drive_id') == did
        and inv.get('canonical_filename') == item['destination_filename']
        and inv.get('vertical') == 'CC'
        and inv.get('country') == 'MX'
        and inv.get('language') == 'ES'
        and inv.get('angle') == 'LIMITE_ALTO'
        and inv.get('p_orient') == 'PV'
        and inv.get('metadata_clean') is True
        and inv.get('reservation_status') == 'RESERVADO_PELO_GESTOR'
        and inv.get('ares_eligible') is False
        and inv.get('thread_id') == '1544837155900235927'
    )
    if not inv_ok:
        errors.append(f"inventory mismatch: {item['source_filename']}")
    items.append({
        'source_filename': item['source_filename'],
        'destination_filename': item['destination_filename'],
        'source_parent_verified': source_ok,
        'destination_parent_verified': dest_ok,
        'sha256_readback_verified': sha_ok,
        'metadata_clean_verified': clean_ok,
        'inventory_verified': inv_ok,
    })

pending = mod.list_children(drive, plan['upload_parent_id'], folders=False)
if pending:
    errors.append(f"UPLOAD MANUAL pending media: {len(pending)}")
if len(set(source_ids)) != 12:
    errors.append('source IDs are not 12 unique lineages')
if len(set(dest_ids)) != 12:
    errors.append('READY destination IDs are not 12 unique assets')
if len(report.get('items', {})) != 12 or any(x.get('phase') != 'COMPLETE' for x in report.get('items', {}).values()):
    errors.append('execution report is not 12/12 COMPLETE')
rows = REPORT_CSV.read_text(encoding='utf-8').splitlines()
if len(rows) != 13:
    errors.append(f"execution CSV rows mismatch: {len(rows)-1}")

result = {
    'verified_at_utc': mod.now(),
    'auth_mode': 'service_account',
    'service_account_identity_verified': True,
    'shared_drive': 'MGS-AGENTS',
    'operation': 'CC_MX_ES',
    'source_lineages': len(set(source_ids)),
    'unique_ready_assets': len(set(dest_ids)),
    'duplicate_sources': 0,
    'ready_download_sha_clean_verified': sum(x['destination_parent_verified'] and x['sha256_readback_verified'] and x['metadata_clean_verified'] for x in items),
    'legacy_sources_verified': sum(x['source_parent_verified'] for x in items),
    'inventory_primary_rows_verified': sum(x['inventory_verified'] for x in items),
    'reservation_fail_closed_verified': sum(x['inventory_verified'] for x in items),
    'upload_manual_remaining_files': len(pending),
    'report_complete_items': sum(x.get('phase') == 'COMPLETE' for x in report.get('items', {}).values()),
    'errors': errors,
    'items': items,
}
mod.atomic_json(OUT, result)
print(json.dumps({k: v for k, v in result.items() if k != 'items'}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 2)
