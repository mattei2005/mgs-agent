#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

root = Path('/root/mgs-agent')
inventory_path = root / 'data/infra-inventory.json'
audit_path = root / 'logs/events-audit.jsonl'
backup_dir = root / 'backups/mgs-offer-quiz-20260921T143832-0400-v1.4.1'
backup_dir.mkdir(parents=True, exist_ok=True)
backup_path = backup_dir / 'infra-inventory.before-v1.4.1.json'
if not backup_path.exists():
    shutil.copy2(inventory_path, backup_path)

now = datetime.now(ZoneInfo('America/New_York')).isoformat()
with inventory_path.open(encoding='utf-8') as handle:
    inventory = json.load(handle)

artifact_id = 'zeus-mgs-offer-quiz-dicasfinancas-g001-g006-20260921'
matches = [item for item in inventory.get('runtime_artifacts', []) if item.get('id') == artifact_id]
if len(matches) != 1:
    raise SystemExit(f'expected one plugin artifact, got {len(matches)}')
artifact = matches[0]
route_hashes = [
    '1012f9ef0c085650c6f2f478da49bc9ec72c409120760b490dc88fc0ea5ce53e',
    '9584028b762f04c8a0884ccb9c296aee109ceb62fa0ad6f42b95f1ff7e73a0ef',
    'b1586104af288c16e265952cb5f4bd4046cc2e4558b55c3242798cc798ae20a1',
    'cf3991505f17371b544b570dc155d09e4307023fb1bdbc9526b829feb52ebfe7',
    '2ac0314e243e6a9ac73067afb5f49643276ecdf31568106714e482ffa11f8eef',
    'b6e2b25cd4b62ed798efdefd235cde806ffdf55329d7234448218af321aa719d',
]
new_target = 'https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/'
old_target = 'https://dicasfinancas.info/rec-br-cc-br-cartao-de-credito-superdigital/'
artifact['status'] = 'active_validated'
artifact['correction_sources'] = list(dict.fromkeys(artifact.get('correction_sources', []) + [
    'discord:thread:1551602673441185934#1551662963591749692'
]))
artifact['plugin'].update({
    'version': '1.4.1',
    'package_path': '/root/mgs-agent/work/mgs-offer-quiz-20260921T111124-0400/mgs-offer-quiz-1.4.1.zip',
    'package_sha256': 'ce951a2ea00c09e3b969e42e5ee7c91af7b7c5007789c47f5b463f185f6d583c',
    'manifest_sha256': {
        'mgs-offer-quiz.php': '4ca795dc71e539f4d1ed3aba1807e484c858d7a6442e9b74af86b106663a8223',
        'includes/class-mgs-offer-quiz.php': '2cc0e45fa6d054f34f5c4bae1756c02a9bd935a39aabf4f9b17264ddb0e460c5',
        'templates/landing.php': '68493821627598849bf822e359c668cdb925b0c1ebed9851c7a8ea810573da60',
        'README.md': '4e9b5e163f63a81e08f84f794631d16dba3617530700a7b61f80b5272198a1fc',
    },
    'source_production_manifest_match': True,
})
for index, route in enumerate(artifact['routes']):
    route.update({'sha256': route_hashes[index], 'http_status': 200, 'plugin_version': '1.4.1'})
artifact['contract']['target_url'] = new_target
artifact['contract']['target_url_authority'] = 'discord:thread:1551602673441185934#1551662963591749692'
artifact['validation'].update({
    'tests': '6/6 passed',
    'php_lint': '3/3 passed',
    'plugin_active_readback': True,
    'plugin_version': '1.4.1',
    'public_routes_http_200': '6/6',
    'static_marker': '6/6 plugin=1.4.1',
    'target_url_exact': '6/6',
    'target_url': new_target,
    'old_target_absent': '6/6',
    'destination_http': 200,
    'destination_title': 'Cartão de Crédito Nubank - Dicas Finanças',
    'chromium_real_clicks': '6/6',
    'query_params_exact_once': ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'custom_x'],
    'forms': 0,
    'mobile_horizontal_overflow': False,
    'source_production_manifest_match': True,
    'counter_qa_isolation': 'PASS — daily-view endpoint blocked in QA Chromium; no HeadlessChrome endpoint requests appeared in nginx access log during v1.4.1 click matrix; live counter row was not reset or edited',
})
artifact['validation'].pop('destination_http_interpretation', None)
artifact['deployment'].update({
    'revision': 'v1.4.1 Nubank destination URL',
    'v1_4_1_canary': 'plugin updated in place; G001 option/static changed first; G002 remained v1.4.0 on the old target until G001 browser click and destination HTTP 200 passed',
    'v1_4_1_expansion': 'G002-G006 changed only after G001 validation; all six real clicks reached the exact Nubank URL with parameters preserved',
    'v1_4_1_recovered_backup_error': 'first deploy attempt stopped before mutation because shell glob expansion could not traverse the protected backup directory; readback proved plugin/static/options unchanged; chown was corrected to recursive directory scope and deployment retried successfully',
    'scope_impact': 'only the six CTA destination URLs, plugin source/defaults, tests/docs and governed operational records authorized by Rodolfo; counter semantics unchanged',
})
artifact['backups'].update({
    'remote_v1_4_1_pre': '/var/backups/mgs-offer-quiz/20260921T143832-0400-v1.4.1-pre',
    'remote_v1_4_1_database_before_bytes': 21962089,
    'remote_v1_4_1_files': [
        'mgs-offer-quiz-1.4.0-production.tar.gz',
        'static-g001-g006-before-v1.4.1.tar.gz',
        'option-before-v1.4.1.json',
        'static-version-before-v1.4.1.txt',
        'database-before-v1.4.1.sql',
        'mgs-offer-quiz-1.4.1-1551662963591749692.zip',
        'option-canary-v1.4.1.json',
        'option-final-v1.4.1.json',
        'static-final-v1.4.1.sha256',
    ],
    'local_inventory_before_v1_4_1': str(backup_path),
})
artifact['knowledge_registry_id'] = 'DICASFINANCAS-OFFER-QUIZ-V1'
artifact['updated_at'] = now
for key in ('report_infra_discord_message_id', 'source_report', 'report_readback'):
    artifact.pop(key, None)

# Keep canonical context and continuity data discoverable in inventory.
def upsert_data_file(path: Path):
    raw = path.read_bytes()
    entry = {
        'path': str(path),
        'size_bytes': len(raw),
        'md5': hashlib.md5(raw).hexdigest(),
        'modified_at': datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo('America/New_York')).isoformat(),
    }
    existing = [item for item in inventory.get('data_files', []) if item.get('path') == str(path)]
    if len(existing) > 1:
        raise SystemExit(f'duplicate data file inventory: {path}')
    if existing:
        existing[0].update(entry)
    else:
        inventory.setdefault('data_files', []).append(entry)

for path in (
    root / 'context/acquisition.md',
    root / 'context/knowledge-governance.md',
    root / 'data/knowledge-registry.json',
    root / 'data/agent-checkpoints.json',
):
    upsert_data_file(path)

if isinstance(inventory.get('_meta'), dict):
    inventory['_meta']['updated_at'] = now
serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + '\n'
temp_path = inventory_path.with_name(inventory_path.name + '.mgs-offer-quiz-v1.4.1.tmp')
with temp_path.open('w', encoding='utf-8') as handle:
    handle.write(serialized)
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp_path, inventory_path)

with inventory_path.open(encoding='utf-8') as handle:
    readback = json.load(handle)
rb = [item for item in readback['runtime_artifacts'] if item.get('id') == artifact_id]
if len(rb) != 1 or rb[0]['plugin']['version'] != '1.4.1' or rb[0]['contract']['target_url'] != new_target:
    raise SystemExit('plugin inventory readback failed')
if any(old_target in json.dumps(route, ensure_ascii=False) for route in rb[0]['routes']):
    raise SystemExit('old target remains in route inventory')
for path in (
    root / 'context/acquisition.md',
    root / 'context/knowledge-governance.md',
    root / 'data/knowledge-registry.json',
    root / 'data/agent-checkpoints.json',
):
    matches = [item for item in readback['data_files'] if item.get('path') == str(path)]
    if len(matches) != 1 or matches[0]['md5'] != hashlib.md5(path.read_bytes()).hexdigest():
        raise SystemExit(f'data file inventory readback failed: {path}')

events = [
    {
        'ts': now,
        'event': 'wordpress_mgs_offer_quiz_target_url_updated',
        'actor': 'zeus',
        'requested_by': 'Rodolfo Mattei',
        'authorization_message_id': '1551662963591749692',
        'thread_id': '1551602673441185934',
        'site': 'dicasfinancas.info',
        'plugin_version': '1.4.1',
        'old_target': old_target,
        'new_target': new_target,
        'routes': [route['url'] for route in artifact['routes']],
        'validation': {
            'http_200': '6/6',
            'chromium_clicks': '6/6',
            'destination_http': 200,
            'query_params': artifact['validation']['query_params_exact_once'],
            'old_target_absent': '6/6',
            'counter_qa_isolation': artifact['validation']['counter_qa_isolation'],
            'source_production_manifest_match': True,
        },
        'backup': artifact['backups']['remote_v1_4_1_pre'],
        'result': 'success',
    },
    {
        'ts': now,
        'event': 'operation_failure_recovered',
        'actor': 'zeus',
        'operation': 'mgs-offer-quiz v1.4.1 canary deploy backup ownership',
        'failure': 'shell wildcard could not expand inside protected backup directory',
        'side_effect_readback': 'plugin 1.4.0, static_version 1.4.0 and old target remained unchanged',
        'fix': 'replaced wildcard chown with recursive chown on the backup directory, retried and validated',
        'result': 'recovered',
    },
    {
        'ts': now,
        'event': 'knowledge_registry_superseded',
        'actor': 'zeus',
        'old_id': 'DICASFINANCAS-SUPERDIGITAL-QUIZ-V1',
        'new_id': 'DICASFINANCAS-OFFER-QUIZ-V1',
        'canonical_key': 'acquisition.dicasfinancas.superdigital-quiz',
        'source': 'context/acquisition.md',
        'validation': 'mgs-knowledge-control validate status=ok; one active entry for the preserved canonical_key',
        'recovered_errors': [
            'first register rejected because successor canonical_key differed',
            'register --supersedes then completed atomically; redundant supersede command returned entry-not-active and readback confirmed the desired final state',
        ],
        'result': 'success',
    },
    {
        'ts': now,
        'event': 'mgs_knowledge_governance_source_updated',
        'actor': 'zeus',
        'path': str(root / 'context/knowledge-governance.md'),
        'change': 'documented preserved canonical_key and atomic register --supersedes semantics plus mandatory readback after wrapper errors',
        'source': 'recovered registry supersession errors in this operation',
        'result': 'success',
    },
]
with audit_path.open('a', encoding='utf-8') as handle:
    for event in events:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())

print(json.dumps({'artifact': artifact_id, 'version': '1.4.1', 'target': new_target, 'events': len(events), 'data_files': 4, 'readback': 'ok'}, ensure_ascii=False))
