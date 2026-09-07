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
SOURCE_MESSAGE_ID = 'OOB-after-1546526071644626986-B0094'
BACKUP = Path(json.loads((ROOT / 'work/meta-app-b0094-cutover-current.json').read_text(encoding='utf-8'))['backup'])
REGISTRY = ROOT / 'data/meta-app-registry.json'
STATE = ROOT / 'data/meta-app-role-monitor-state.json'
BASELINE = ROOT / 'data/meta-app-role-identity-baseline.json'
PAUSE = ROOT / 'data/meta-app-role-alert-pause.json'
NOW = datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')

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

registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
hits = [row for row in registry.get('apps', []) if row.get('app') == 'B009-3']
if len(hits) != 1 or any(row.get('app') == 'B009-4' for row in registry.get('apps', [])):
    raise RuntimeError('unexpected live registry state for B009 cutover')
hits[0].update({'app': 'B009-4', 'channel_id': '1521252284623884288', 'channel_name': 'b009-2-app-status', 'admin': 'Ninin Ninin', 'onepassword_item_title': 'BOT B009-4 Token - Ninin Ninin', 'expected_sheet_roles': 16})
registry.update({'updated_at': NOW, 'updated_by': 'zeus', 'authorized_by': 'Rodolfo Mattei', 'source_message_id': SOURCE_MESSAGE_ID, 'source_message_ids': list(dict.fromkeys([*(registry.get('source_message_ids') or []), SOURCE_MESSAGE_ID]))})
state = json.loads(STATE.read_text(encoding='utf-8')); apps = state.setdefault('apps', {})
if 'B009-4' in apps: raise RuntimeError('B009-4 unexpectedly exists in live state')
old_state = apps.pop('B009-3', None)
if old_state is None: raise RuntimeError('B009-3 missing from live state')
state.setdefault('_retired_apps', {})['B009-3'] = {'retired_at': NOW, 'replaced_by': 'B009-4', 'source_message_id': SOURCE_MESSAGE_ID, 'last_ok_at': old_state.get('last_ok_at'), 'last_known_role_count': old_state.get('current_count', old_state.get('roles_count', len(old_state.get('roles') or []))), 'last_error': old_state.get('last_error'), 'backup': str(BACKUP / 'meta-app-role-monitor-state.json.before')}
prior = state.get('_cutover_reset')
if prior:
    history = state.setdefault('_cutover_reset_history', [])
    if prior not in history: history.append(prior)
state['_cutover_reset'] = {'at': NOW, 'apps': ['B009-4'], 'retired': ['B009-3'], 'backup': str(BACKUP / 'meta-app-role-monitor-state.json.before'), 'source_message_id': SOURCE_MESSAGE_ID}
baseline = json.loads(BASELINE.read_text(encoding='utf-8')); baseline_apps = baseline.setdefault('apps', {})
if 'B009-4' in baseline_apps: raise RuntimeError('B009-4 unexpectedly exists in baseline')
old_baseline = baseline_apps.pop('B009-3', None)
if old_baseline is not None: baseline.setdefault('retired_apps', {})['B009-3'] = {**old_baseline, 'retired_at': NOW, 'replaced_by': 'B009-4', 'source_message_id': SOURCE_MESSAGE_ID}
baseline['generated_at'] = NOW; baseline['source'] = 'active role identity baselines; B009-3 retired after B009-4 replacement cutover'
pause = json.loads(PAUSE.read_text(encoding='utf-8'))
if pause.get('mode') != 'manual': raise RuntimeError('unexpected pause mode')
alert_apps = [str(x).strip().upper() for x in pause.get('apps', [])]; monitor_apps = [str(x).strip().upper() for x in pause.get('monitor_apps', [])]
if alert_apps != ['B009-3'] or monitor_apps != ['B009-3']: raise RuntimeError(f'unexpected pause state: {alert_apps}/{monitor_apps}')
pause.update({'apps': ['B009-4'], 'monitor_apps': [], 'requested_by': 'Rodolfo Mattei', 'source_message_id': SOURCE_MESSAGE_ID, 'source_message_ids': list(dict.fromkeys([*(pause.get('source_message_ids') or []), SOURCE_MESSAGE_ID])), 'updated_at': NOW, 'reason': 'B009-4 em baseline de produção com alerta temporariamente contido; nenhuma rota completa permanece pausada.'})
for path, payload in ((REGISTRY, registry), (STATE, state), (BASELINE, baseline), (PAUSE, pause)): atomic_json(path, payload)
result = {'status': 'applied_phase1', 'at': NOW, 'registry_app': 'B009-4', 'state_retired': 'B009-3', 'state_fresh_absent': 'B009-4' not in apps, 'baseline_retired': 'B009-3' in baseline.get('retired_apps', {}), 'pause_apps': pause['apps'], 'monitor_apps': pause['monitor_apps'], 'hashes': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (REGISTRY, STATE, BASELINE, PAUSE)}}
(BACKUP / 'cutover-apply-phase1-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
