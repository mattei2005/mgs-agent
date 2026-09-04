#!/usr/bin/env python3
import importlib.util
import json
import os
import urllib.parse
from pathlib import Path

EXECUTOR = Path('/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py')
INVENTORY = Path('/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl')
OUT = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260904T142558Z-kelly-shein-us-en-thread-1545439313246818334/remove-14-independent-verification.json')
ROOT_ID = '0AEwt4Ye690ocUk9PVA'
SOURCE_ID = '12IozwwVP2S__G6e_lPUhACmvqY7f1LHt'
ASSET_ID = '1_QhBvQ70-5CR0iWL-MiHkMUHX2Qk7T8b'
ASSET_LINEAGE_ID = 'asset_0157a7e248987f847f25'
FOLDER_MIME = 'application/vnd.google-apps.folder'

spec = importlib.util.spec_from_file_location('ares_drive_verify', EXECUTOR)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load Drive executor')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.load_env()
sa = mod.service_account()
if sa.get('client_email') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com' or sa.get('project_id') != 'mgs-core-prod':
    raise RuntimeError('service-account identity mismatch')
token, mode = mod.build_access_token()
if mode != 'service_account':
    raise RuntimeError('wrong Drive auth mode')
drive = mod.Drive(token)

fields = 'id,name,parents,driveId,trashed,size,md5Checksum'
def get_file(file_id):
    return drive.request(f'https://www.googleapis.com/drive/v3/files/{file_id}?' + urllib.parse.urlencode({'supportsAllDrives':'true','fields':fields})) or {}

def list_ids(parent_id):
    q = f"'{parent_id}' in parents and trashed=false"
    params = {'q':q,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':'1000','fields':'files(id,name,mimeType)'}
    data = drive.request('https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode(params)) or {}
    return {row['id'] for row in data.get('files', [])}

ready_id = drive.ensure_path('MGS-AGENTS/CRIATIVOS/SHEIN_US_EN/VID/01_READY')
legacy_id = drive.ensure_path('MGS-AGENTS/CRIATIVOS/SHEIN_US_EN/VID/99_LEGACY')
meta = {'RAW_LEGACY': get_file(SOURCE_ID), 'CLEAN_READY': get_file(ASSET_ID)}
ready_ids = list_ids(ready_id)
legacy_ids = list_ids(legacy_id)
rows = [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]
inv = [row for row in rows if row.get('asset_id') == ASSET_LINEAGE_ID]
all_pass = (
    all(row.get('trashed') is True and row.get('driveId') == ROOT_ID for row in meta.values())
    and ASSET_ID not in ready_ids
    and SOURCE_ID not in legacy_ids
    and len(inv) == 1
    and inv[0].get('status') == 'TRASHED_BY_MANAGER_REQUEST'
    and inv[0].get('reservation_status') == 'REMOVIDO_PELO_GESTOR'
    and inv[0].get('ares_eligible') is False
)
result = {
    'all_pass': all_pass,
    'auth_mode': mode,
    'drive_readback': {key:{'name':row.get('name'),'trashed':row.get('trashed'),'drive_id_ok':row.get('driveId') == ROOT_ID} for key,row in meta.items()},
    'absent_from_live_ready': ASSET_ID not in ready_ids,
    'absent_from_live_legacy': SOURCE_ID not in legacy_ids,
    'inventory_rows': len(inv),
    'inventory_status': inv[0].get('status') if inv else None,
    'reservation_status': inv[0].get('reservation_status') if inv else None,
    'ares_eligible': inv[0].get('ares_eligible') if inv else None,
}
tmp = OUT.with_suffix('.json.tmp')
tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
os.replace(tmp, OUT)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if all_pass else 2)
