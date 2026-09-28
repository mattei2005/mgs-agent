#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

root = Path('/root/mgs-agent')
inventory_path = root / 'data/infra-inventory.json'
audit_path = root / 'logs/events-audit.jsonl'
artifact_id = 'zeus-mgs-offer-quiz-dicasfinancas-g001-g006-20260921'
message_id = '1551668240638287918'
channel_id = '1498132022634483894'
now = datetime.now(ZoneInfo('America/New_York')).isoformat()
with inventory_path.open(encoding='utf-8') as handle:
    inventory = json.load(handle)
matches = [item for item in inventory.get('runtime_artifacts', []) if item.get('id') == artifact_id]
if len(matches) != 1:
    raise SystemExit(f'expected one artifact, got {len(matches)}')
artifact = matches[0]
artifact['report_infra_discord_message_id'] = message_id
artifact['source_report'] = f'discord:channel:{channel_id}#{message_id}'
artifact['report_readback'] = {
    'http': 200,
    'content_empty': True,
    'author_id': '1496296175014252634',
    'message_id': message_id,
    'validated_at': now,
}
artifact['updated_at'] = now
if isinstance(inventory.get('_meta'), dict):
    inventory['_meta']['updated_at'] = now
temp = inventory_path.with_name(inventory_path.name + '.report-v1.4.1.tmp')
with temp.open('w', encoding='utf-8') as handle:
    json.dump(inventory, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp, inventory_path)
with inventory_path.open(encoding='utf-8') as handle:
    readback = json.load(handle)
rb = [item for item in readback['runtime_artifacts'] if item.get('id') == artifact_id]
if len(rb) != 1 or rb[0].get('report_infra_discord_message_id') != message_id:
    raise SystemExit('report inventory readback failed')
event = {
    'ts': now,
    'event': 'report_infra_readback',
    'actor': 'zeus',
    'channel_id': channel_id,
    'message_id': message_id,
    'http': 200,
    'content_empty': True,
    'author_id': '1496296175014252634',
    'artifacts': [artifact_id],
    'paths': [
        'plugins/mgs-offer-quiz',
        'context/acquisition.md',
        'context/knowledge-governance.md',
        'data/knowledge-registry.json',
        'data/infra-inventory.json',
        'data/agent-checkpoints.json',
        'logs/events-audit.jsonl',
    ],
    'result': 'ok',
}
with audit_path.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())
print(json.dumps({'message_id': message_id, 'artifact': artifact_id, 'audit': 'ok', 'readback': 'ok'}, ensure_ascii=False))
