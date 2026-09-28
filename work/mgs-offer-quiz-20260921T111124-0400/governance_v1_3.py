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
backup_dir = root / 'backups/mgs-offer-quiz-20260921T115959-0400-v1.3'
backup_dir.mkdir(parents=True, exist_ok=True)
backup_path = backup_dir / 'infra-inventory.before-v1.3.json'
if not backup_path.exists():
    shutil.copy2(inventory_path, backup_path)

now = datetime.now(ZoneInfo('America/New_York')).isoformat()
with inventory_path.open(encoding='utf-8') as handle:
    inventory = json.load(handle)

artifact_id = 'zeus-mgs-offer-quiz-dicasfinancas-g001-g006-20260921'
plugin_matches = [item for item in inventory.get('runtime_artifacts', []) if item.get('id') == artifact_id]
if len(plugin_matches) != 1:
    raise SystemExit(f'expected one plugin artifact, got {len(plugin_matches)}')
artifact = plugin_matches[0]

route_hashes = [
    'c14f5986dda93dcd18733384741eec82768c0cfcdce4684c0f010cd2660ccca0',
    '0ff28c490e97cd516d71cf62b88179bd2eccde2c19297ad1595a3fcd5dcb380e',
    '015bf15109982c1c3005db9a33214c60bc8fbb17c1e94c74706df5b0a348bb71',
    '5c3107ce53fc5fe36bee0b912c6c918ca40e0bc68503085c857d27cacc867ba5',
    '4665eed35343d91fd3ff8aa1ddc996fe88430801418e6a0ce61e86c98ad9725b',
    '959f8a573dfe6ca5ee207e72fe25db7d0144ad3250ee5ad196337b9464c55eb3',
]
artifact['status'] = 'active_validated_with_editorial_target_pending'
artifact['correction_authorized_by'] = 'Rodolfo Mattei'
artifact['correction_sources'] = [
    'discord:thread:1551602673441185934#1551621312890282095',
    'discord:thread:1551602673441185934#1551623380678082711',
]
artifact.pop('correction_source', None)
artifact['plugin'].update({
    'version': '1.3.0',
    'package_path': '/root/mgs-agent/work/mgs-offer-quiz-20260921T111124-0400/mgs-offer-quiz-1.3.0.zip',
    'package_sha256': '421422d43575bd4b18ff63f333aa268708b43e7d378efcd60574fc2b8973b8aa',
    'manifest_sha256': {
        'mgs-offer-quiz.php': '5ba49f1ff6cea64fd2d063f82c4d3423defdfcc9f81783194cc235d8e9ddf8f2',
        'includes/class-mgs-offer-quiz.php': '1721b3b1083ec713a8e098fd126f5c9fe2c4d03fe90d4ce2331c8572c75fd622',
        'templates/landing.php': 'b99c89743597df2ee039d58be905a54f2a2a746d90fa48c48b7b8ee1cc5b6bbd',
        'README.md': '86a9f8a7619daf0795d6bedae90efd0dd396421682be7f970b90355dfb4c848f',
    },
    'source_production_manifest_match': True,
})
for index, route in enumerate(artifact['routes']):
    route.update({'sha256': route_hashes[index], 'http_status': 200, 'plugin_version': '1.3.0'})
contract = artifact['contract']
for stale in ('unverified_limit_claim', 'unverified_approval_claim', 'unverified_social_volume_claim'):
    contract.pop(stale, None)
contract.update({
    'visual_reference': 'https://solicitefacil.com/quiz/quiz01/',
    'visual_reference_viewport': '390x844',
    'visual_parity': 'measured geometry and literal marked-copy parity; only domain, live timer and requested email-button removal differ',
    'literal_copy_source': 'Rodolfo-marked reference images in Discord message 1551621312890282095',
    'hero_copy': ['até', 'R$5.000', 'aprovados na hora'],
    'benefit_copy': ['Sem consulta SPC/Serasa', 'Sem anuidade', 'Sem taxa escondida'],
    'cta_copy': 'Ver ofertas agora',
    'secondary_email_button': False,
    'social_proof_animation': {
        'requested_by': 'Rodolfo Mattei',
        'source_message_id': '1551623380678082711',
        'initial_display': '2.481 pessoas',
        'direction': 'monotonic_increase',
        'random_increment_range': [1, 3],
        'random_interval_ms_range': [4000, 9000],
        'implementation': 'client-side presentation animation',
        'telemetry': False,
    },
})
artifact['validation'].update({
    'tests': '5/5 passed',
    'php_lint': '3/3 passed',
    'plugin_active_readback': True,
    'plugin_version': '1.3.0',
    'option_items': 6,
    'active_items': 6,
    'public_routes_http_200': '6/6',
    'static_marker': '6/6 plugin=1.3.0',
    'manager_binding': '6/6',
    'literal_copy_match': '6/6 hero, benefits, CTA and initial proof row',
    'forms': 0,
    'inputs': 0,
    'secondary_email_button': False,
    'mobile_viewports': ['320x700', '360x800', '390x844', '430x932'],
    'mobile_horizontal_overflow': False,
    'chromium_real_clicks': '6/6',
    'query_params_exact_once': ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'custom_x'],
    'random_counter_preview': ['2.481', '2.482', '2.483', '2.484'],
    'random_counter_production_g001': ['2.481', '2.484', '2.486', '2.489'],
    'random_counter_production_g006': ['2.481', '2.484'],
    'random_counter_monotonic': True,
    'random_counter_not_telemetry': True,
    'visual_side_by_side': 'PASS — literal reference parity except allowed domain/timer/email-button differences; no clipping or overflow',
    'visual_comparison_path': '/root/mgs-agent/work/mgs-offer-quiz-20260921T111124-0400/comparison-reference-vs-production-v1.2.png',
    'source_production_manifest_match': True,
    'destination_http': 404,
    'destination_http_interpretation': 'expected until the redator publishes the requested article; route is intentionally preconfigured',
})
artifact['deployment'].update({
    'revision': 'v1.3.0 literal parity plus randomized proof counter',
    'v1_2_canary': 'G001 published by in-place plugin update; G002 hash unchanged; side-by-side visual comparison PASS before expansion',
    'v1_2_expansion': 'G002-G006 published and runtime configuration read back with exact literal copy',
    'v1_3_canary': 'G001 published by in-place plugin update; G002 hash unchanged; counter changed monotonically in production before expansion',
    'v1_3_expansion': 'G002-G006 published after G001 counter and click validation',
    'scope_impact': 'only the six routes authorized by Rodolfo',
})
artifact['backups']['remote_v1_2_pre'] = '/var/backups/mgs-offer-quiz/20260921T115421-0400-v1.2-pre'
artifact['backups']['remote_v1_3_pre'] = '/var/backups/mgs-offer-quiz/20260921T115959-0400-v1.3-pre'
artifact['backups']['remote_v1_3_files'] = [
    'mgs-offer-quiz-1.2.0-production.tar.gz',
    'static-g001-g006-before-v1.3.tar.gz',
    'option-before-v1.3.json',
    'option-canary-v1.3.json',
    'option-final-v1.3.json',
    'static-final-v1.3.sha256',
    'mgs-offer-quiz-1.3.0-1551623380678082711.zip',
]
artifact['backups']['local_inventory_before_v1_3'] = str(backup_path)
artifact['updated_at'] = now
artifact.pop('report_infra_discord_message_id', None)
artifact.pop('source_report', None)
artifact.pop('report_readback', None)

skill_id = 'zeus-wp-quiz-lead-funnel-skill'
skill_matches = [item for item in inventory.get('profile_skill_references', []) if item.get('id') == skill_id]
if len(skill_matches) != 1:
    raise SystemExit(f'expected one skill artifact, got {len(skill_matches)}')
skill = skill_matches[0]
skill_path = Path('/root/.hermes/profiles/zeus/skills/ops/wp-quiz-lead-funnel/SKILL.md')
mirror_path = root / 'profiles/zeus-skills/ops/wp-quiz-lead-funnel/SKILL.md'
raw = skill_path.read_bytes()
if raw != mirror_path.read_bytes():
    raise SystemExit('skill runtime/mirror mismatch')
skill.update({
    'size_bytes': len(raw),
    'modified_at': datetime.fromtimestamp(skill_path.stat().st_mtime, ZoneInfo('America/New_York')).isoformat(),
    'sha256': hashlib.sha256(raw).hexdigest(),
    'runtime_versioned_sha_match': True,
    'purpose': 'Procedimento operacional de quizzes WordPress, redirects, diagnóstico e paridade visual/textual medida com referências.',
    'validation': 'Runtime e mirror têm SHA-256 idêntico; regra agora exige paridade de copy marcada e registra contador promocional randômico como apresentação, nunca telemetria.',
    'updated_at': now,
    'source': 'discord:thread:1551602673441185934#1551623380678082711',
})
skill.pop('report_infra_discord_message_id', None)
skill.pop('source_report', None)
skill.pop('report_readback', None)

if isinstance(inventory.get('_meta'), dict):
    inventory['_meta']['updated_at'] = now
serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + '\n'
temp_path = inventory_path.with_name(inventory_path.name + '.mgs-offer-quiz-v1.3.tmp')
with temp_path.open('w', encoding='utf-8') as handle:
    handle.write(serialized)
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp_path, inventory_path)

with inventory_path.open(encoding='utf-8') as handle:
    readback = json.load(handle)
plugin_rb = [item for item in readback['runtime_artifacts'] if item.get('id') == artifact_id]
skill_rb = [item for item in readback['profile_skill_references'] if item.get('id') == skill_id]
if len(plugin_rb) != 1 or plugin_rb[0]['plugin']['version'] != '1.3.0' or len(plugin_rb[0]['routes']) != 6:
    raise SystemExit('plugin inventory readback failed')
if len(skill_rb) != 1 or skill_rb[0]['sha256'] != 'b6d67143d27df7ed9d655b075faa14aecf8010d1c96c74ccfbe89bb06ad114db':
    raise SystemExit('skill inventory readback failed')

events = [
    {
        'ts': now,
        'event': 'wordpress_mgs_offer_quiz_literal_copy_parity_deployed',
        'actor': 'zeus',
        'requested_by': 'Rodolfo Mattei',
        'authorization_message_id': '1551621312890282095',
        'thread_id': '1551602673441185934',
        'site': 'dicasfinancas.info',
        'plugin_version': '1.2.0',
        'scope': 'G001-G006',
        'copy': {'hero': contract['hero_copy'], 'benefits': contract['benefit_copy'], 'cta': contract['cta_copy'], 'proof_initial': '2.481 pessoas viram ofertas hoje'},
        'email_button': False,
        'validation': 'G001 canary PASS; G002-G006 expansion readback PASS; side-by-side visual parity PASS',
        'backup': artifact['backups']['remote_v1_2_pre'],
        'result': 'success',
    },
    {
        'ts': now,
        'event': 'wordpress_mgs_offer_quiz_random_counter_deployed',
        'actor': 'zeus',
        'requested_by': 'Rodolfo Mattei',
        'authorization_message_id': '1551623380678082711',
        'thread_id': '1551602673441185934',
        'site': 'dicasfinancas.info',
        'plugin_version': '1.3.0',
        'scope': 'G001-G006',
        'counter': contract['social_proof_animation'],
        'validation': 'G001 canary changed 2.481→2.484→2.486→2.489; G006 changed 2.481→2.484; 6/6 routes and clicks PASS',
        'backup': artifact['backups']['remote_v1_3_pre'],
        'result': 'success',
    },
    {
        'ts': now,
        'event': 'skill_updated',
        'actor': 'zeus',
        'skill': 'wp-quiz-lead-funnel',
        'path': str(skill_path),
        'mirror_path': str(mirror_path),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'change': 'Exact-reference rule now requires marked-copy parity and provenance for randomized promotional counters.',
        'runtime_mirror_match': True,
        'source': 'discord:thread:1551602673441185934#1551623380678082711',
        'result': 'success',
    },
]
with audit_path.open('a', encoding='utf-8') as handle:
    for event in events:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())

print(json.dumps({'plugin_inventory': artifact_id, 'skill_inventory': skill_id, 'events': len(events), 'updated_at': now, 'readback': 'ok'}, ensure_ascii=False))
