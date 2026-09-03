#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

BACKUP = Path('/root/mgs-agent/backups/meta-app-b0014-to-b0015-cutover-20260903-114204')
BACKUP.mkdir(parents=True, exist_ok=False)
files = {
    'meta-app-registry.json.before': Path('/root/mgs-agent/data/meta-app-registry.json'),
    'meta-app-role-monitor-state.json.before': Path('/root/mgs-agent/data/meta-app-role-monitor-state.json'),
    'meta-app-role-identity-baseline.json.before': Path('/root/mgs-agent/data/meta-app-role-identity-baseline.json'),
    'meta-app-role-alert-pause.json.before': Path('/root/mgs-agent/data/meta-app-role-alert-pause.json'),
    'agent-checkpoints.json.before': Path('/root/mgs-agent/data/agent-checkpoints.json'),
    'knowledge-registry.json.before': Path('/root/mgs-agent/data/knowledge-registry.json'),
    'infra-inventory.json.before': Path('/root/mgs-agent/data/infra-inventory.json'),
    'route-pack-05.runtime.before': Path('/root/.hermes/profiles/zeus/skills/growth/meta-app-rate-limit-monitor/references/route-pack-05.md'),
    'route-pack-05.mirror.before': Path('/root/mgs-agent/profiles/zeus-skills/growth/meta-app-rate-limit-monitor/references/route-pack-05.md'),
    'meta-app-roles-watch.sh.before': Path('/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh'),
}
for dst, src in files.items():
    assert src.exists(), src
    shutil.copy2(src, BACKUP / dst)

registry = json.loads(files['meta-app-registry.json.before'].read_text(encoding='utf-8'))
rows = [row for row in registry['apps'] if row.get('app') == 'B001-4']
assert len(rows) == 1
assert not any(row.get('app') == 'B001-5' for row in registry['apps'])
rows[0].update({
    'app': 'B001-5',
    'channel_id': '1521251196294135858',
    'channel_name': 'b001-2-app-status',
    'admin': 'Debora Monteiro Lima',
    'onepassword_item_title': 'BOT B001-5 Token - Debora Monteiro Lima',
    'expected_sheet_roles': 14,
})
registry.update({
    'updated_by': 'zeus',
    'authorized_by': 'Rodolfo Mattei',
    'source_message_id': '1545088764530008135',
})
(BACKUP / 'meta-app-registry.canary.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

script = files['meta-app-roles-watch.sh.before'].read_text(encoding='utf-8')
old_registry = "REGISTRY_PATH = Path('/root/mgs-agent/data/meta-app-registry.json')"
new_registry = f"REGISTRY_PATH = Path('{BACKUP}/meta-app-registry.canary.json')"
assert script.count(old_registry) == 1
script = script.replace(old_registry, new_registry, 1)
old_lock = 'LOCK_FILE="/var/lock/meta-app-roles-watch.lock"'
assert script.count(old_lock) == 1
script = script.replace(old_lock, 'LOCK_FILE="/var/lock/meta-app-roles-watch-b0015-canary.lock"', 1)
(BACKUP / 'meta-app-roles-watch.canary.sh').write_text(script, encoding='utf-8')
(BACKUP / 'meta-app-role-monitor-state.canary.json').write_text('{"apps": {}}\n', encoding='utf-8')
pause = {
    'version': 4,
    'mode': 'manual',
    'apps': ['B001-5'],
    'monitor_apps': [],
    'timezone': 'America/New_York',
    'requested_by': 'Rodolfo Mattei',
    'source_message_id': '1545088764530008135',
    'reason': 'isolated B001-5 cutover canary alert containment',
}
(BACKUP / 'meta-app-role-alert-pause.canary.json').write_text(json.dumps(pause, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

manifest = []
for path in sorted(BACKUP.iterdir(), key=lambda p: p.name):
    if path.is_file() and path.name != 'SHA256SUMS':
        manifest.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
(BACKUP / 'SHA256SUMS').write_text('\n'.join(manifest) + '\n', encoding='utf-8')
print(json.dumps({'status': 'prepared', 'backup': str(BACKUP), 'files': len(files), 'canary_app': 'B001-5'}, ensure_ascii=False))
