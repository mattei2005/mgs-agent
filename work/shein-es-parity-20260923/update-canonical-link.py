#!/usr/bin/env python3
import fcntl
import json
import os
import tempfile
from pathlib import Path

root = Path('/root/mgs-agent')
path = root / 'data/infra-inventory.json'
lock_path = root / 'data/.infra-inventory.lock'
artifact_id = 'zeus-shein-es-parity-mavroa-boostingecon-20260923'
canonical = {
    'source': 'context/acquisition.md',
    'registry_id': 'DIRECT-SHEIN-BOOSTINGECON-ES-1552343613126737930',
    'canonical_key': 'acquisition.direct_shein.boostingecon.landings',
    'status': 'active',
    'validation': 'knowledge-control validate PASS; regression 19/19 PASS',
}
with lock_path.open('a+') as lock:
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    data = json.loads(path.read_text())
    rows = [row for row in data['runtime_artifacts'] if row.get('id') == artifact_id]
    if len(rows) != 1:
        raise SystemExit(f'expected exactly one artifact, found {len(rows)}')
    rows[0]['canonical_knowledge'] = canonical
    rows[0]['report_infra_knowledge_pending'] = True
    previous_mode = path.stat().st_mode & 0o777
    fd, tmp_name = tempfile.mkstemp(prefix='.infra-inventory.', suffix='.json', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, previous_mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
print(json.dumps({'status': 'ok', 'artifact_id': artifact_id, 'registry_id': canonical['registry_id'], 'report_infra_knowledge_pending': True}))
