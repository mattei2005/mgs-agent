#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt
import fcntl
import importlib.util
import json
import os
import shutil
import urllib.parse
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260904T142558Z-kelly-shein-us-en-thread-1545439313246818334')
PROCESS = BASE / 'process_batch.py'
INVENTORY = Path('/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl')
BACKUPS = Path('/root/mgs-agent/backups/ares-creative-ops')
SOURCE_ID = '12IozwwVP2S__G6e_lPUhACmvqY7f1LHt'
ASSET_ID = '1_QhBvQ70-5CR0iWL-MiHkMUHX2Qk7T8b'
ASSET_LINEAGE_ID = 'asset_0157a7e248987f847f25'
ORIGINAL = '14_12 US_SHEIN_EN_03-09  - CARREGADOR - Story (INGLES) .mp4'
CANONICAL = 'SHEIN_US_EN_VID_FREE_CLOTHES_PRESSER_PV_006.mp4'
REQUEST_THREAD_ID = '1545439313246818334'

spec = importlib.util.spec_from_file_location('shein_delete_lineage', PROCESS)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load canonical Drive helper')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ex = mod.load_executor()
ex.load_env()
sa = ex.service_account()
if sa.get('client_email') != mod.EXPECTED_EMAIL or sa.get('project_id') != mod.EXPECTED_PROJECT:
    raise RuntimeError('canonical service-account identity mismatch')
token, mode = ex.build_access_token()
if mode != 'service_account':
    raise RuntimeError('non-service-account auth refused')
drive = ex.Drive(token)
root = drive.preflight_destination(mode)
shared = drive.request(f'https://www.googleapis.com/drive/v3/drives/{mod.ROOT_ID}?fields=id,name') or {}
if root.get('driveId') != mod.ROOT_ID or shared.get('id') != mod.ROOT_ID or shared.get('name') != mod.EXPECTED_DRIVE:
    raise RuntimeError('Shared Drive identity mismatch')

expected = {
    SOURCE_ID: {'name': ORIGINAL, 'parent': '1smyYJhxxRPpzRgFiBxnZUwvO1mhvFdF5', 'role': 'RAW_LEGACY'},
    ASSET_ID: {'name': CANONICAL, 'parent': '1SsVMXYGHxFimtN8nSaoYOer0Do-zawfH', 'role': 'CLEAN_READY'},
}
preflight = {}
for fid, exp in expected.items():
    row = mod.api_get(drive, fid)
    caps = row.get('capabilities') or {}
    if row.get('driveId') != mod.ROOT_ID or row.get('name') != exp['name'] or row.get('parents') != [exp['parent']]:
        raise RuntimeError(f"preflight identity/parent mismatch for {exp['role']}")
    if not row.get('trashed') and not caps.get('canTrash'):
        raise RuntimeError(f"canTrash missing for {exp['role']}")
    preflight[exp['role']] = {
        'id': fid, 'name': row.get('name'), 'parent': row.get('parents'),
        'trashed': bool(row.get('trashed')), 'size': row.get('size'), 'md5Checksum': row.get('md5Checksum'),
        'canTrash': bool(caps.get('canTrash')),
    }

lock_path = INVENTORY.with_suffix(INVENTORY.suffix + '.lock')
with lock_path.open('a+') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    for fid, exp in expected.items():
        current = mod.api_get(drive, fid)
        if not current.get('trashed'):
            params = urllib.parse.urlencode({
                'supportsAllDrives': 'true',
                'fields': 'id,name,parents,driveId,trashed,size,md5Checksum',
            })
            drive.request(
                f'https://www.googleapis.com/drive/v3/files/{fid}?{params}',
                method='PATCH',
                data=json.dumps({'trashed': True}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
            )
        after = mod.api_get(drive, fid)
        if after.get('driveId') != mod.ROOT_ID or after.get('name') != exp['name'] or not after.get('trashed'):
            raise RuntimeError(f"trash readback failed for {exp['role']}")

    rows = [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]
    matches = [row for row in rows if row.get('asset_id') == ASSET_LINEAGE_ID]
    if len(matches) != 1:
        raise RuntimeError(f'inventory lineage match count={len(matches)}')
    target = matches[0]
    if target.get('source_drive_id') != SOURCE_ID or target.get('asset_drive_id') != ASSET_ID:
        raise RuntimeError('inventory Drive identity mismatch')
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
    backup = BACKUPS / f'assets-before-kelly-shein-remove-14-{stamp}.jsonl'
    shutil.copy2(INVENTORY, backup)
    removed_at = dt.datetime.now(dt.UTC).isoformat()
    target.setdefault('status_before_removal', target.get('status'))
    target['status'] = 'TRASHED_BY_MANAGER_REQUEST'
    target['reservation_status'] = 'REMOVIDO_PELO_GESTOR'
    target['ares_eligible'] = False
    target['removed_by'] = 'Kelly Nice'
    target['removed_at'] = removed_at
    target['removal_mode'] = 'TRASH_REVERSIBLE'
    target['removal_request_thread_id'] = REQUEST_THREAD_ID
    target['source_trashed'] = True
    target['asset_trashed'] = True
    target['last_reconciled_at'] = removed_at
    note = ' Linhagem completa removida da operação por pedido da Kelly; versão limpa e original enviados à lixeira reversível do Shared Drive.'
    if note.strip() not in str(target.get('notes') or ''):
        target['notes'] = str(target.get('notes') or '').rstrip() + note
    tmp = INVENTORY.with_suffix(INVENTORY.suffix + '.tmp')
    tmp.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')
    os.replace(tmp, INVENTORY)

post = {}
for fid, exp in expected.items():
    row = mod.api_get(drive, fid)
    post[exp['role']] = {'id': fid, 'name': row.get('name'), 'trashed': bool(row.get('trashed')), 'driveId': row.get('driveId')}
rows = [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]
inv = [row for row in rows if row.get('asset_id') == ASSET_LINEAGE_ID]
inventory_ok = len(inv) == 1 and inv[0].get('status') == 'TRASHED_BY_MANAGER_REQUEST' and inv[0].get('reservation_status') == 'REMOVIDO_PELO_GESTOR' and inv[0].get('ares_eligible') is False and inv[0].get('source_trashed') is True and inv[0].get('asset_trashed') is True
result = {
    'completed_at_utc': dt.datetime.now(dt.UTC).isoformat(),
    'auth_mode': mode,
    'shared_drive': shared.get('name'),
    'operation': mod.OPERATION,
    'asset_id': ASSET_LINEAGE_ID,
    'removal_mode': 'TRASH_REVERSIBLE',
    'preflight': preflight,
    'post_readback': post,
    'inventory_verified': inventory_ok,
    'inventory_backup': str(backup),
    'all_pass': all(x['trashed'] and x['driveId'] == mod.ROOT_ID for x in post.values()) and inventory_ok,
}
mod.jdump(BASE / 'remove-14-lineage-result.json', result)
print(json.dumps({k: v for k, v in result.items() if k != 'preflight'}, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['all_pass'] else 2)
