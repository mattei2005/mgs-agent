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
backup_dir = root / 'backups/mgs-offer-quiz-20260921T113622-0400-v1.1'
backup_dir.mkdir(parents=True, exist_ok=True)
backup_path = backup_dir / 'infra-inventory.before-v1.1.json'
if not backup_path.exists():
    shutil.copy2(inventory_path, backup_path)

now = datetime.now(ZoneInfo('America/New_York')).isoformat()
with inventory_path.open(encoding='utf-8') as handle:
    inventory = json.load(handle)

artifact_id = 'zeus-mgs-offer-quiz-dicasfinancas-g001-g006-20260921'
matched = [item for item in inventory.get('runtime_artifacts', []) if item.get('id') == artifact_id]
if len(matched) != 1:
    raise SystemExit(f'expected one plugin artifact, got {len(matched)}')
artifact = matched[0]

route_hashes = [
    '0b13ef559692e17276f41306e5cfcc4e3175413a62da078e883dd56aeb4cc3c3',
    '0541e83c9422a3b8fb7310f880fa28d48bd68bd253b80247fefac81eaed6f32d',
    '0dd0a70274b12169f3d000bbdedf0f5941cecb857b9dbb389a90250ac3e0b74b',
    '7d4fa80a22d31feaf6193bf59f3c47a5f637fcf2dfea90ea4fc4241fd5627fd1',
    'e22172db7f127f67bbd2d5b908a718d3b1df7565da1fa63e138f900981a82736',
    'd7f73db1d7f58e7fbefab3a2c60773ffab86047e4342adea5f23c9757626ae82',
]
artifact['status'] = 'active_validated_with_editorial_target_pending'
artifact['correction_authorized_by'] = 'Rodolfo Mattei'
artifact['correction_source'] = 'discord:thread:1551602673441185934#1551615156017037333'
artifact['plugin'].update({
    'version': '1.1.0',
    'package_path': '/root/mgs-agent/work/mgs-offer-quiz-20260921T111124-0400/mgs-offer-quiz-1.1.0.zip',
    'package_sha256': 'ead6155ca4bbdd8692a677fdec298d624f978ce0d6e3d133a53c86c9066066ba',
    'manifest_sha256': {
        'mgs-offer-quiz.php': 'dd9cf108e01a75cbac54a4b4e00262badc5e1242a28e7a766dcd36702e815608',
        'includes/class-mgs-offer-quiz.php': '80ff262fb385ce21b78fe4869c7087b5fadc7ec65c4371f18b053be477f022f3',
        'templates/landing.php': 'f393d552fb4d77592f063dd10f890a8381a2fda66a8ae4553d77259920d1df53',
        'README.md': '5ad4f49f3fa6da8d7f99b3d798d81863a5a3d6c2a6edcf5db35a61188de1b9f7',
    },
    'source_production_manifest_match': True,
})
for index, route in enumerate(artifact['routes']):
    route['sha256'] = route_hashes[index]
    route['http_status'] = 200
    route['plugin_version'] = '1.1.0'
artifact['contract'].update({
    'visual_reference': 'https://solicitefacil.com/quiz/quiz01/',
    'visual_reference_viewport': '390x844',
    'visual_parity': 'measured geometry and side-by-side parity; only copy/domain and requested email-button removal differ',
    'secondary_email_button': False,
    'unverified_limit_claim': False,
    'unverified_approval_claim': False,
    'unverified_social_volume_claim': False,
})
artifact['validation'].update({
    'tests': '5/5 passed',
    'php_lint': '3/3 passed',
    'plugin_active_readback': True,
    'plugin_version': '1.1.0',
    'option_items': 6,
    'active_items': 6,
    'public_routes_http_200': '6/6',
    'static_marker': '6/6 plugin=1.1.0',
    'manager_binding': '6/6',
    'forms': 0,
    'inputs': 0,
    'secondary_email_button': False,
    'old_design_markers': False,
    'mobile_viewports': ['320x700', '360x800', '390x844', '430x932'],
    'mobile_horizontal_overflow': False,
    'chromium_real_clicks': '6/6',
    'query_params_exact_once': ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'custom_x'],
    'visual_side_by_side': 'PASS — equivalent geometry, colors, typography, spacing, borders, CTA, trust row, disclaimer and footer; no clipping or overflow',
    'visual_comparison_path': '/root/mgs-agent/work/mgs-offer-quiz-20260921T111124-0400/comparison-reference-vs-production.png',
    'source_production_manifest_match': True,
    'destination_http': 404,
    'destination_http_interpretation': 'expected until the redator publishes the requested article; route is intentionally preconfigured',
})
artifact['deployment'].update({
    'revision': 'v1.1.0 visual parity correction',
    'canary_intent': 'G001 first with G002-G006 static pages expected to remain v1.0.0 until validation',
    'canary_guard_result': 'guard detected G002 hash change after plugin lifecycle auto-synced all active routes; command exited fail-closed',
    'recovery': 'immediate readback showed v1.1.0 on all six routes; all six were then validated by HTTP, Chromium real click, responsive DOM checks and side-by-side visual review; no rollback required',
    'scope_impact': 'none beyond the six routes already authorized by Rodolfo',
})
artifact['backups']['remote_v1_1_pre'] = '/var/backups/mgs-offer-quiz/20260921T113622-0400-v1.1-pre'
artifact['backups']['remote_v1_1_files'] = [
    'mgs-offer-quiz-1.0.0-production.tar.gz',
    'static-g001-g006-before-v1.1.tar.gz',
    'option-before-v1.1.json',
    'option-final-v1.1.json',
    'static-final-v1.1.sha256',
    'mgs-offer-quiz-1.1.0-1551615156017037333.zip',
]
artifact['backups']['local_inventory_before_v1_1'] = str(backup_path)
artifact['updated_at'] = now

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
    'purpose': 'Procedimento operacional de quizzes WordPress, captura de leads, redirects, diagnóstico de frontend/cache e paridade visual medida com referências.',
    'validation': 'Runtime e mirror têm SHA-256 idêntico; adicionada regra de tratar “igual à referência” como paridade visual medida, com CSS/geometria, comparação lado a lado e DOM checks.',
    'updated_at': now,
    'source': 'discord:thread:1551602673441185934#1551615156017037333',
})

if isinstance(inventory.get('_meta'), dict):
    inventory['_meta']['updated_at'] = now
serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + '\n'
temp_path = inventory_path.with_name(inventory_path.name + '.mgs-offer-quiz-v1.1.tmp')
with temp_path.open('w', encoding='utf-8') as handle:
    handle.write(serialized)
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp_path, inventory_path)

with inventory_path.open(encoding='utf-8') as handle:
    readback = json.load(handle)
plugin_rb = [item for item in readback['runtime_artifacts'] if item.get('id') == artifact_id]
skill_rb = [item for item in readback['profile_skill_references'] if item.get('id') == skill_id]
if len(plugin_rb) != 1 or plugin_rb[0]['plugin']['version'] != '1.1.0' or len(plugin_rb[0]['routes']) != 6:
    raise SystemExit('plugin inventory readback failed')
if len(skill_rb) != 1 or skill_rb[0]['sha256'] != 'a421c0cb37c1f3354326c0483ac20e9021d01bedbb7c14e30ef5481eca73a289':
    raise SystemExit('skill inventory readback failed')

events = [
    {
        'ts': now,
        'event': 'wordpress_mgs_offer_quiz_visual_parity_revision_deployed',
        'actor': 'zeus',
        'requested_by': 'Rodolfo Mattei',
        'authorization_message_id': '1551615156017037333',
        'thread_id': '1551602673441185934',
        'site': 'dicasfinancas.info',
        'plugin': {'slug': 'mgs-offer-quiz', 'version': '1.1.0', 'status': 'active'},
        'routes': [route['url'] for route in artifact['routes']],
        'reference': artifact['contract']['visual_reference'],
        'validation': artifact['validation'],
        'backup': artifact['backups']['remote_v1_1_pre'],
        'status': 'success_with_expected_editorial_target_404',
    },
    {
        'ts': now,
        'event': 'wordpress_mgs_offer_quiz_canary_guard_recovered',
        'actor': 'zeus',
        'site': 'dicasfinancas.info',
        'intended_canary': 'G001',
        'detected': 'G002 static hash changed because plugin lifecycle auto-synced all active routes after version update',
        'guard': 'deployment command exited nonzero on mismatch',
        'scope': 'G001-G006 already authorized',
        'recovery_validation': '6/6 HTTP 200, 6/6 v1.1 marker, 6/6 Chromium clicks, four responsive viewports, side-by-side visual parity PASS',
        'rollback_required': False,
        'result': 'recovered_validated',
    },
    {
        'ts': now,
        'event': 'skill_updated',
        'actor': 'zeus',
        'skill': 'wp-quiz-lead-funnel',
        'path': str(skill_path),
        'mirror_path': str(mirror_path),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'change': 'Added measured visual-parity rule for requests to match a reference exactly.',
        'runtime_mirror_match': True,
        'source': 'discord:thread:1551602673441185934#1551615156017037333',
        'result': 'success',
    },
]
with audit_path.open('a', encoding='utf-8') as handle:
    for event in events:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())

print(json.dumps({'plugin_inventory': artifact_id, 'skill_inventory': skill_id, 'events': len(events), 'updated_at': now, 'readback': 'ok'}, ensure_ascii=False))
