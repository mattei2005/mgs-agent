#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
INV = ROOT / 'data/infra-inventory.json'
B002_BACKUP = '/root/mgs-agent/backups/meta-app-b0023-to-b0024-cutover-20260907-103037'
B009_BACKUP = '/root/mgs-agent/backups/meta-app-b0093-to-b0094-cutover-20260907-104421'
NOW = datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')
REPORT = os.environ.get('MGS_CUTOVER_REPORT_REF', 'pending:#alerts-infra')
REPORT_READBACK = os.environ.get('MGS_CUTOVER_REPORT_READBACK', 'pending')

def file_meta(path: Path) -> dict:
    stat = path.stat()
    return {
        'size_bytes': stat.st_size,
        'modified_at': datetime.fromtimestamp(stat.st_mtime, ZoneInfo('America/New_York')).isoformat(timespec='seconds'),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }

def atomic_json(path: Path, payload: dict) -> None:
    mode = path.stat().st_mode & 0o777
    fd, raw = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
        os.chmod(temp, mode); os.replace(temp, path)
    finally:
        if temp.exists(): temp.unlink()

data = json.loads(INV.read_text(encoding='utf-8'))
registry = json.loads((ROOT / 'data/meta-app-registry.json').read_text(encoding='utf-8'))
pause = json.loads((ROOT / 'data/meta-app-role-alert-pause.json').read_text(encoding='utf-8'))
by_id = {}
for collection in data.values():
    if isinstance(collection, list):
        for row in collection:
            if isinstance(row, dict) and row.get('id'):
                by_id[row['id']] = row
backups = [B002_BACKUP, B009_BACKUP]

row = by_id['zeus-meta-app-registry']
row.update(file_meta(Path(row['path'])))
row.update({
    'scope': [x['app'] for x in registry.get('apps', [])],
    'description': 'Canonical current Meta app routing registry; B002-4 and B009-4 replace their restricted predecessors while preserving existing app-status channels.',
    'validation': 'Exact 1Password items/app_name; four Graph checks HTTP 200 per replacement; tokens valid and app-bound; returned roles resolved; canonical Sheet has 11 B002-4 rows and 16 B009-4 rows with zero predecessor rows; scoped production cycles zero errors.',
    'last_change': 'Replaced B002-3→B002-4 and B009-3→B009-4; expected Sheet roles are 11 and 16.',
    'updated_at': NOW,
    'requested_by': 'Rodolfo Mattei',
    'authorization_message_id': '1546526071644626986 + OOB-after-1546526071644626986-B0094',
    'source_report': REPORT,
    'report_readback': REPORT_READBACK,
    'backups': list(dict.fromkeys([*(row.get('backups') or []), *backups])),
})

row = by_id['zeus-meta-app-role-alert-pause-state']
row.update(file_meta(Path(row['path'])))
row.update({
    'scope': pause.get('apps') or [],
    'monitor_scope': pause.get('monitor_apps') or [],
    'mode': pause.get('mode'),
    'description': 'Canonical app pause state; both alert-only and full-route pause sets are empty after validated B002-4 and B009-4 replacement cutovers.',
    'validation': 'JSON PASS; B002-4 and B009-4 absent from both pause sets after isolated canary, contained production baselines, Sheet parity and clean unpaused scoped cycles.',
    'last_change': 'Reactivated B002-4 and B009-4; no app route remains paused.',
    'updated_at': NOW,
    'requested_by': 'Rodolfo Mattei',
    'authorization_message_id': '1546526071644626986 + OOB-after-1546526071644626986-B0094',
    'resume_condition': 'None; all confirmed replacement routes are active.',
    'source_report': REPORT,
    'report_readback': REPORT_READBACK,
    'backups': list(dict.fromkeys([*(row.get('backups') or []), *backups])),
})

row = by_id['zeus-meta-app-rate-limit-route-pack-05']
runtime = Path(row['path']); mirror = Path(row['versioned_path'])
row.update(file_meta(runtime))
row.update({
    'runtime_versioned_sha_match': runtime.read_bytes() == mirror.read_bytes(),
    'description': 'Production route pack for current B001-B013 app monitoring, including B002-4/B009-4 replacement cutovers and B013-5 dedicated DTR route.',
    'validation': 'Runtime/versioned SHA-256 parity; records exact B002-4/B009-4 items, channels, expected Sheet counts, fresh predecessor-free state, Sheet parity and pause-free activation.',
    'last_change': 'Added current B002-4 and B009-4 cutover procedures; demoted B002-3/B009-3 sections to historical and updated every active registry/channel list.',
    'updated_at': NOW,
    'source_report': REPORT,
    'report_readback': REPORT_READBACK,
    'backups': list(dict.fromkeys([*(row.get('backups') or []), *backups])),
})

# Refresh generic data-file metadata for every file changed by this cutover.
changed_paths = {
    str(ROOT / 'data/meta-app-registry.json'),
    str(ROOT / 'data/meta-app-role-alert-pause.json'),
    str(ROOT / 'data/meta-app-role-monitor-state.json'),
    str(ROOT / 'data/meta-app-role-identity-baseline.json'),
    str(ROOT / 'data/knowledge-registry.json'),
    str(ROOT / 'data/knowledge-inbox.jsonl'),
    str(ROOT / 'data/agent-checkpoints.json'),
}
for row in data.get('data_files', []):
    path_text = row.get('path')
    if path_text not in changed_paths:
        continue
    path = Path(path_text)
    stat = path.stat()
    row.update({
        'size_bytes': stat.st_size,
        'modified_at': datetime.fromtimestamp(stat.st_mtime, ZoneInfo('America/New_York')).isoformat(timespec='seconds'),
        'md5': hashlib.md5(path.read_bytes()).hexdigest(),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    })

data.setdefault('_meta', {})['updated_at'] = NOW
data['_meta']['generated_by'] = 'infra-discovery.sh + Zeus validated Meta app cutover update'
atomic_json(INV, data)
print(json.dumps({'status': 'inventory-updated', 'updated_at': NOW, 'scope': [x['app'] for x in registry.get('apps', [])], 'pause_apps': pause.get('apps'), 'monitor_apps': pause.get('monitor_apps'), 'runtime_versioned_sha_match': runtime.read_bytes() == mirror.read_bytes(), 'inventory_sha256': hashlib.sha256(INV.read_bytes()).hexdigest(), 'source_report': REPORT}, ensure_ascii=False))
