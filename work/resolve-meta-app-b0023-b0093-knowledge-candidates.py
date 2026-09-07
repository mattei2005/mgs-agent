#!/usr/bin/env python3
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

root = Path('/root/mgs-agent')
path = root / 'data/knowledge-inbox.jsonl'
lock_path = root / 'data/.knowledge-control.lock'
updates = {
    'KCI-3859df8658a0e635': ('Promovido historicamente como B002-3 e supersedido pela decisão ativa B002-4.', 'registry:decision-meta-roles-b0024-20260907'),
    'KCI-ab355c5062526ec7': ('Promovido historicamente como B009-3 e supersedido pela decisão ativa B009-4.', 'registry:decision-meta-roles-b0094-20260907'),
}
with lock_path.open('a+', encoding='utf-8') as lock:
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    seen = set()
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    for row in rows:
        cid = row.get('candidate_id')
        if cid not in updates:
            continue
        seen.add(cid)
        resolution, source = updates[cid]
        row.update({'status': 'resolved', 'resolution': resolution, 'resolution_source': source, 'resolved_at': now})
    if seen != set(updates):
        raise RuntimeError(f'missing candidates: {sorted(set(updates)-seen)}')
    fd, raw = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
            handle.flush(); os.fsync(handle.fileno())
        os.chmod(temp, path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        if temp.exists(): temp.unlink()
print(json.dumps({'status': 'resolved', 'candidate_ids': sorted(seen)}, ensure_ascii=False))
