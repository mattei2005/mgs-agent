#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

root = Path('/root/mgs-agent')
inventory_path = root / 'data/infra-inventory.json'
audit_path = root / 'logs/events-audit.jsonl'
message_id = '1551635428057292891'
channel_id = '1498132022634483894'
now = datetime.now(ZoneInfo('America/New_York')).isoformat()
with inventory_path.open(encoding='utf-8') as handle:
    inventory = json.load(handle)

ids = {
    'zeus-mgs-offer-quiz-dicasfinancas-g001-g006-20260921': inventory.get('runtime_artifacts', []),
    'zeus-mgs-offer-quiz-daily-views-dicasfinancas-20260921': inventory.get('runtime_artifacts', []),
    'zeus-wp-quiz-lead-funnel-skill': inventory.get('profile_skill_references', []),
}
for artifact_id, group in ids.items():
    matches = [item for item in group if item.get('id') == artifact_id]
    if len(matches) != 1:
        raise SystemExit(f'expected one artifact {artifact_id}, got {len(matches)}')
    matches[0]['report_infra_discord_message_id'] = message_id
    matches[0]['source_report'] = f'discord:channel:{channel_id}#{message_id}'
    matches[0]['report_readback'] = {
        'http': 200,
        'content_empty': True,
        'author_id': '1496296175014252634',
        'message_id': message_id,
        'validated_at': now,
    }
    matches[0]['updated_at'] = now
if isinstance(inventory.get('_meta'), dict):
    inventory['_meta']['updated_at'] = now

temp = inventory_path.with_name(inventory_path.name + '.report-v1.4.tmp')
with temp.open('w', encoding='utf-8') as handle:
    json.dump(inventory, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp, inventory_path)

with inventory_path.open(encoding='utf-8') as handle:
    readback = json.load(handle)
for artifact_id, group_name in (
    ('zeus-mgs-offer-quiz-dicasfinancas-g001-g006-20260921', 'runtime_artifacts'),
    ('zeus-mgs-offer-quiz-daily-views-dicasfinancas-20260921', 'runtime_artifacts'),
    ('zeus-wp-quiz-lead-funnel-skill', 'profile_skill_references'),
):
    matches = [item for item in readback[group_name] if item.get('id') == artifact_id]
    if len(matches) != 1 or matches[0].get('report_infra_discord_message_id') != message_id:
        raise SystemExit(f'report readback failed for {artifact_id}')

event = {
    'ts': now,
    'event': 'report_infra_readback',
    'actor': 'zeus',
    'channel_id': channel_id,
    'message_id': message_id,
    'http': 200,
    'content_empty': True,
    'author_id': '1496296175014252634',
    'artifacts': list(ids),
    'result': 'ok',
}
with audit_path.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())
print(json.dumps({'message_id': message_id, 'inventory_artifacts': list(ids), 'audit': 'ok', 'readback': 'ok'}, ensure_ascii=False))
