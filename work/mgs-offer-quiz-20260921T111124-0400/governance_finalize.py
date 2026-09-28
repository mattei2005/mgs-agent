#!/usr/bin/env python3
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

root = Path('/root/mgs-agent')
inventory_path = root / 'data/infra-inventory.json'
audit_path = root / 'logs/events-audit.jsonl'
backup_dir = root / 'backups/mgs-offer-quiz-20260921T111124-0400'
backup_dir.mkdir(parents=True, exist_ok=True)
backup_path = backup_dir / 'infra-inventory.before.json'
if not backup_path.exists():
    shutil.copy2(inventory_path, backup_path)

now = datetime.now(ZoneInfo('America/New_York')).isoformat()
with inventory_path.open(encoding='utf-8') as handle:
    inventory = json.load(handle)

artifact_id = 'zeus-mgs-offer-quiz-dicasfinancas-g001-g006-20260921'
artifacts = inventory.setdefault('runtime_artifacts', [])
if any(item.get('id') == artifact_id for item in artifacts):
    raise SystemExit(f'duplicate artifact id: {artifact_id}')

routes = [
    {
        'manager': f'G{number:03d}',
        'url': f'https://dicasfinancas.info/quiz/quiz-v1-g{number:03d}/',
        'http_status': 200,
        'sha256': sha256,
    }
    for number, sha256 in enumerate(
        [
            'c61e58a173e20aed7d4e21cbc5c722787f27f9a6f65bb1b3edf17ed30666ee37',
            '112d099c20e3d9641fec3edf7b4446accdac256b1ca43c5a63ab87b60ee7de33',
            '421951b71ac0624867d0a80cdd8589480e965bc820b48439dcf067f2b1a81ce5',
            '759163f913e05d8db0288028ddd6d61e6768e1606a57ec1db1ec0f4699faa6b7',
            '5d56a841d935ec082b73a3a9d64750cf56f8f4d758b65444b00fe635195fecf5',
            'b0e2a022585e9d3beed135d2259d732126e7daf225e5584606ddded1d6352cb8',
        ],
        start=1,
    )
]

artifact = {
    'id': artifact_id,
    'agent': 'zeus',
    'type': 'wordpress_custom_plugin',
    'owner': 'Rodolfo Mattei / Zeus',
    'status': 'active_validated_with_editorial_target_pending',
    'authorized_by': 'Rodolfo Mattei',
    'authorization_source': 'discord:thread:1551602673441185934#1551609844665028611',
    'site': 'dicasfinancas.info',
    'webroot': '/home/runcloud/webapps/dicasfinancas',
    'plugin': {
        'slug': 'mgs-offer-quiz',
        'version': '1.0.0',
        'source_path': '/root/mgs-agent/plugins/mgs-offer-quiz',
        'production_path': '/home/runcloud/webapps/dicasfinancas/wp-content/plugins/mgs-offer-quiz',
        'package_path': '/root/mgs-agent/work/mgs-offer-quiz-20260921T111124-0400/mgs-offer-quiz-1.0.0.zip',
        'package_sha256': 'b58b2f7638493cb08934d8ae6fcb880cadfeb843f89c64c263af4d9b7692cd2c',
        'manifest_sha256': {
            'mgs-offer-quiz.php': '7e714c7d64776c04e1a1c48ed843388c8a8cf2f5c2b07f676c7f2a5dae2754d5',
            'includes/class-mgs-offer-quiz.php': '58660d32408560dca44b8bcb463a269f9d8d7c6e46c9d8cc7a49fcbfa8d2a9a4',
            'templates/landing.php': 'a9901023836629cbeb28ccf67224e9d7ee1416ca4548520bfb9a81c20c8d01e9',
            'README.md': '86c504a78ca6c07c4baea1860b85fe86b24248940ee6ee4067dd9fa9df00fade',
        },
        'source_production_manifest_match': True,
    },
    'routes': routes,
    'contract': {
        'managers': ['G001', 'G002', 'G003', 'G004', 'G005', 'G006'],
        'slug_pattern': 'quiz-v1-g00{1..6}',
        'static_frontend': True,
        'wordpress_control_plane': True,
        'cta_count': 1,
        'target_url': 'https://dicasfinancas.info/rec-br-cc-br-cartao-de-credito-superdigital/',
        'query_passthrough': True,
        'lead_capture': False,
        'email_capture': False,
        'sms': False,
        'campaign_events': False,
        'noindex_follow': True,
    },
    'validation': {
        'tests': '5/5 passed',
        'php_lint': '3/3 passed',
        'plugin_active_readback': True,
        'plugin_version': '1.0.0',
        'option_items': 6,
        'active_items': 6,
        'public_routes_http_200': '6/6',
        'unknown_route_http_404': True,
        'static_marker': '6/6',
        'manager_binding': '6/6',
        'target_url_exact': '6/6',
        'forms': 0,
        'inputs': 0,
        'mixed_http_assets': 0,
        'mobile_viewports': ['320x700', '360x800', '390x844'],
        'mobile_horizontal_overflow': False,
        'cta_above_fold_all_viewports': True,
        'chromium_real_clicks': '6/6',
        'query_params_exact_once': ['utm_source', 'utm_medium', 'utm_campaign', 'utm_adgroup', 'fbclid', 'custom_x'],
        'visual_review': 'professional, intact, no overlap, crop or broken elements',
        'source_production_manifest_match': True,
        'destination_http': 404,
        'destination_http_interpretation': 'expected until the redator publishes the requested article; route is intentionally preconfigured',
    },
    'deployment': {
        'canary': 'G001 active first; G002-G006 remained inactive until canary validation',
        'expansion': 'G002-G006 activated only after canary HTTP, mobile, visual and click checks',
        'recovered_error': 'WP-CLI rejected tar.gz as an installable plugin; readback proved zero side effects, then ZIP install succeeded',
    },
    'backups': {
        'remote': '/var/backups/mgs-offer-quiz/20260921T110529-0400',
        'database_before_bytes': 20976123,
        'option_before': 'option-before.json',
        'option_canary': 'option-canary-g001.json',
        'packages_archived': [
            'mgs-offer-quiz-1.0.0-1551609844665028611.zip',
            'mgs-offer-quiz-1.0.0-1551609844665028611.tar.gz',
        ],
        'local_inventory_before': str(backup_path),
    },
    'knowledge_registry_id': 'DICASFINANCAS-SUPERDIGITAL-QUIZ-V1',
    'checkpoint_id': 'dicasfinancas-superdigital-quiz-g001-g006-20260921',
    'updated_at': now,
}
artifacts.append(artifact)
if isinstance(inventory.get('_meta'), dict):
    inventory['_meta']['updated_at'] = now

serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + '\n'
temp_path = inventory_path.with_name(inventory_path.name + '.mgs-offer-quiz.tmp')
with temp_path.open('w', encoding='utf-8') as handle:
    handle.write(serialized)
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp_path, inventory_path)

with inventory_path.open(encoding='utf-8') as handle:
    readback = json.load(handle)
matched = [item for item in readback['runtime_artifacts'] if item.get('id') == artifact_id]
if len(matched) != 1 or len(matched[0].get('routes', [])) != 6:
    raise SystemExit('inventory readback failed')

event = {
    'ts': now,
    'event': 'wordpress_mgs_offer_quiz_dicasfinancas_deployed',
    'actor': 'zeus',
    'requested_by': 'Rodolfo Mattei',
    'request_message_id': '1551608282408554526',
    'authorization_message_id': '1551609844665028611',
    'thread_id': '1551602673441185934',
    'site': 'dicasfinancas.info',
    'plugin': {'slug': 'mgs-offer-quiz', 'version': '1.0.0', 'status': 'active'},
    'routes': [item['url'] for item in routes],
    'target_url': artifact['contract']['target_url'],
    'validation': artifact['validation'],
    'backup': artifact['backups']['remote'],
    'knowledge_registry_id': artifact['knowledge_registry_id'],
    'status': 'success_with_expected_editorial_target_404',
}
with audit_path.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())

print(json.dumps({'inventory_id': artifact_id, 'routes': len(routes), 'audit_event': event['event'], 'updated_at': now, 'readback': 'ok'}, ensure_ascii=False))
