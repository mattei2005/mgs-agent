#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
SOURCE_MESSAGE_ID = 'OOB-after-1546526071644626986-B0094'
now = datetime.now(ZoneInfo('America/New_York'))
stamp = now.strftime('%Y%m%d-%H%M%S')
backup = ROOT / 'backups' / f'meta-app-b0093-to-b0094-cutover-{stamp}'
backup.mkdir(parents=True, exist_ok=False)
files = {
    'meta-app-registry.json.before': ROOT / 'data/meta-app-registry.json',
    'meta-app-role-monitor-state.json.before': ROOT / 'data/meta-app-role-monitor-state.json',
    'meta-app-role-identity-baseline.json.before': ROOT / 'data/meta-app-role-identity-baseline.json',
    'meta-app-role-alert-pause.json.before': ROOT / 'data/meta-app-role-alert-pause.json',
    'agent-checkpoints.json.before': ROOT / 'data/agent-checkpoints.json',
    'knowledge-registry.json.before': ROOT / 'data/knowledge-registry.json',
    'knowledge-inbox.jsonl.before': ROOT / 'data/knowledge-inbox.jsonl',
    'infra-inventory.json.before': ROOT / 'data/infra-inventory.json',
    'route-pack-05.runtime.before': Path('/root/.hermes/profiles/zeus/skills/growth/meta-app-rate-limit-monitor/references/route-pack-05.md'),
    'route-pack-05.mirror.before': ROOT / 'profiles/zeus-skills/growth/meta-app-rate-limit-monitor/references/route-pack-05.md',
    'meta-app-roles-watch.sh.before': Path('/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh'),
}
for dst, src in files.items():
    if not src.exists():
        raise FileNotFoundError(src)
    shutil.copy2(src, backup / dst)
registry = json.loads(files['meta-app-registry.json.before'].read_text(encoding='utf-8'))
hits = [row for row in registry['apps'] if row.get('app') == 'B009-3']
if len(hits) != 1 or any(row.get('app') == 'B009-4' for row in registry['apps']):
    raise RuntimeError('unexpected B009 registry state')
hits[0].update({
    'app': 'B009-4',
    'channel_id': '1521252284623884288',
    'channel_name': 'b009-2-app-status',
    'admin': 'Ninin Ninin',
    'onepassword_item_title': 'BOT B009-4 Token - Ninin Ninin',
    'expected_sheet_roles': 16,
})
registry.update({'updated_at': now.isoformat(timespec='seconds'), 'updated_by': 'zeus', 'authorized_by': 'Rodolfo Mattei', 'source_message_id': SOURCE_MESSAGE_ID})
(backup / 'meta-app-registry.canary.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
script = files['meta-app-roles-watch.sh.before'].read_text(encoding='utf-8')
old_registry = "REGISTRY_PATH = Path('/root/mgs-agent/data/meta-app-registry.json')"
old_lock = 'LOCK_FILE="/var/lock/meta-app-roles-watch.lock"'
if script.count(old_registry) != 1 or script.count(old_lock) != 1:
    raise RuntimeError('unexpected monitor script anchors')
script = script.replace(old_registry, f"REGISTRY_PATH = Path('{backup}/meta-app-registry.canary.json')", 1)
script = script.replace(old_lock, 'LOCK_FILE="/var/lock/meta-app-roles-watch-b0094-canary.lock"', 1)
canary_script = backup / 'meta-app-roles-watch.canary.sh'
canary_script.write_text(script, encoding='utf-8'); canary_script.chmod(0o700)
(backup / 'meta-app-role-monitor-state.canary.json').write_text('{"apps": {}}\n', encoding='utf-8')
canary_pause = {'version': 4, 'mode': 'manual', 'apps': ['B009-4'], 'monitor_apps': [], 'timezone': 'America/New_York', 'requested_by': 'Rodolfo Mattei', 'source_message_id': SOURCE_MESSAGE_ID, 'reason': 'isolated B009-4 cutover canary alert containment'}
(backup / 'meta-app-role-alert-pause.canary.json').write_text(json.dumps(canary_pause, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
manifest = []
for path in sorted(backup.iterdir(), key=lambda p: p.name):
    if path.is_file() and path.name != 'SHA256SUMS':
        manifest.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}')
(backup / 'SHA256SUMS').write_text('\n'.join(manifest) + '\n', encoding='utf-8')
current = {'backup': str(backup), 'source_message_id': SOURCE_MESSAGE_ID, 'prepared_at': now.isoformat(timespec='seconds')}
(ROOT / 'work/meta-app-b0094-cutover-current.json').write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'prepared', 'backup': str(backup), 'files': len(files), 'canary_app': 'B009-4'}, ensure_ascii=False))
