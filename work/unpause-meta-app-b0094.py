#!/usr/bin/env python3
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

path = Path('/root/mgs-agent/data/meta-app-role-alert-pause.json')
data = json.loads(path.read_text(encoding='utf-8'))
if data.get('mode') != 'manual': raise RuntimeError('unexpected pause mode')
apps = [str(x).strip().upper() for x in data.get('apps', [])]
monitor_apps = [str(x).strip().upper() for x in data.get('monitor_apps', [])]
if apps != ['B009-4'] or monitor_apps != []: raise RuntimeError(f'unexpected B009-4 containment state: {apps}/{monitor_apps}')
data.update({'apps': [], 'monitor_apps': [], 'requested_by': 'Rodolfo Mattei', 'source_message_id': 'OOB-after-1546526071644626986-B0094', 'source_message_ids': list(dict.fromkeys([*(data.get('source_message_ids') or []), 'OOB-after-1546526071644626986-B0094'])), 'updated_at': datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'), 'reason': 'B002-4 e B009-4 validados e reativados; nenhuma rota permanece pausada.'})
mode = path.stat().st_mode & 0o777; fd, raw = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent); temp = Path(raw)
try:
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    os.chmod(temp, mode); os.replace(temp, path)
finally:
    if temp.exists(): temp.unlink()
print(json.dumps({'status': 'B009-4-unpaused', 'apps': data['apps'], 'monitor_apps': data['monitor_apps'], 'updated_at': data['updated_at']}, ensure_ascii=False))
