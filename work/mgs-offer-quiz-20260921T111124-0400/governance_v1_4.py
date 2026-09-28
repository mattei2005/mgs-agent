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
backup_dir = root / 'backups/mgs-offer-quiz-20260921T122415-0400-v1.4'
backup_dir.mkdir(parents=True, exist_ok=True)
backup_path = backup_dir / 'infra-inventory.before-v1.4.json'
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
    '539e9a07f5507c60c7a0dd980965bad89ec665c353dec38b5063302e5c5ad1e4',
    'cb8243bbb770e82db398f61fe0f1ab161b230d9715099e09be87293688e8d4df',
    '03b1bd50ec83086000653fe7adcc9daf0a5f842f2428a6a33a57a24bb65d9c43',
    'db6fc92d4f0d5722aee964be406b576fa2aad0732cb44d44ce3fe73481d0b664',
    'c73388c027503cb47438610dda4050e3acabe3cfce44fda921a5e38faea08f88',
    '85f9c3fa575e91089c10845b77d3f1a01cd788b88c7b4c5d3db5aa7632ebb9d0',
]
artifact['status'] = 'active_validated_with_editorial_target_pending'
artifact['correction_authorized_by'] = 'Rodolfo Mattei'
artifact['correction_sources'] = [
    'discord:thread:1551602673441185934#1551621312890282095',
    'discord:thread:1551602673441185934#1551623380678082711',
    'discord:thread:1551602673441185934#1551628631002841149',
]
artifact['plugin'].update({
    'version': '1.4.0',
    'package_path': '/root/mgs-agent/work/mgs-offer-quiz-20260921T111124-0400/mgs-offer-quiz-1.4.0.zip',
    'package_sha256': '9f2b350efc15aed5baf85d8bb10db58dd9ba58d2eeaaea6938df877fa051ae9b',
    'manifest_sha256': {
        'mgs-offer-quiz.php': '9e3cca21bc2715f127a8b7f6410f31791759a629be642a3d9ce085928f964b06',
        'includes/class-mgs-offer-quiz.php': 'd865adc57fa121fae99ee7cbe1b330a08e715e5b07a8864bdc8cd260bbf4d434',
        'templates/landing.php': '68493821627598849bf822e359c668cdb925b0c1ebed9851c7a8ea810573da60',
        'README.md': 'a0aee065203d0713cbe6677ff8eeecda963c4a8deb5a417a66c75d0261d00161',
    },
    'source_production_manifest_match': True,
})
for index, route in enumerate(artifact['routes']):
    route.update({'sha256': route_hashes[index], 'http_status': 200, 'plugin_version': '1.4.0'})
contract = artifact['contract']
contract.pop('social_proof_animation', None)
contract['daily_pageview_counter'] = {
    'requested_by': 'Rodolfo Mattei',
    'source_message_id': '1551628631002841149',
    'scope': 'shared across G001-G006',
    'baseline': 1892,
    'first_pageview_display': 1892,
    'subsequent_pageview_increment': 1,
    'formula': 'display_count = 1892 + views_today - 1',
    'reset': 'automatic by new date row',
    'timezone': 'America/Sao_Paulo',
    'endpoint': 'POST /wp-json/mgs-offer-quiz/v1/daily-view',
    'cache_control': 'no-store, no-cache, must-revalidate, max-age=0',
    'table': 'wp_mgs_offer_quiz_daily_views',
    'atomic_increment': 'INSERT ... ON DUPLICATE KEY UPDATE with LAST_INSERT_ID(view_count + 1)',
    'frontend_fallback': 1892,
    'random_timer': False,
}
artifact['validation'].update({
    'tests': '6/6 passed',
    'php_lint': '3/3 passed',
    'plugin_active_readback': True,
    'plugin_version': '1.4.0',
    'public_routes_http_200': '6/6',
    'static_marker': '6/6 plugin=1.4.0',
    'forms': 0,
    'inputs': 0,
    'secondary_email_button': False,
    'mobile_viewports': ['320x700', '360x800', '390x844', '430x932'],
    'mobile_horizontal_overflow': False,
    'chromium_real_clicks': '6/6',
    'query_params_exact_once': ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'custom_x'],
    'random_counter_removed': True,
    'endpoint_sequential': [
        {'views_today': 1, 'display_count': 1892},
        {'views_today': 2, 'display_count': 1893},
    ],
    'cross_manager_shared': 'G001 displayed 1.894, next G002 access displayed 1.895',
    'browser_sequence': ['1.896', '1.897', '1.898', '1.899', '1.900', '1.901'],
    'responsive_sequence': ['1.902', '1.903', '1.904', '1.905'],
    'concurrency_fixture': '20 parallel increments returned each integer 1..20 exactly once; stored view_count=20; display_count=1911',
    'new_date_fixture': 'first increment on 2099-12-30 returned display_count=1892',
    'fixture_cleanup': 'PASS — 2099-12-30 and 2099-12-31 rows removed',
    'qa_count_reconciliation': '14 expected QA pageviews exactly matched the sole production-day row',
    'qa_cleanup': '14 QA-only pageviews removed after reconciliation; table empty; next real display 1892',
    'invalid_slug': 'HTTP 400 mgs_oq_counter_slug',
    'counter_response_cache': 'no-store, no-cache, must-revalidate, max-age=0',
    'source_production_manifest_match': True,
    'destination_http': 404,
    'destination_http_interpretation': 'expected until the redator publishes the requested article; route is intentionally preconfigured',
})
artifact['deployment'].update({
    'revision': 'v1.4.0 real shared daily pageview counter',
    'v1_4_canary': 'in-place plugin update; database/table backup; G001 published; G002 hash unchanged; endpoint and first/second increments validated',
    'v1_4_expansion': 'G002-G006 published after G001 endpoint/browser validation',
    'scope_impact': 'only the six routes and one plugin-owned daily counter table authorized by Rodolfo',
})
artifact['backups']['remote_v1_4_pre'] = '/var/backups/mgs-offer-quiz/20260921T122415-0400-v1.4-pre'
artifact['backups']['remote_v1_4_database_before_bytes'] = 20985779
artifact['backups']['remote_v1_4_files'] = [
    'mgs-offer-quiz-1.3.0-production.tar.gz',
    'static-g001-g006-before-v1.4.tar.gz',
    'option-before-v1.4.json',
    'option-canary-v1.4.json',
    'option-final-v1.4.json',
    'static-final-v1.4.sha256',
    'counter-table-v1.4.txt',
    'database-before-v1.4.sql',
    'mgs-offer-quiz-1.4.0-1551628631002841149.zip',
]
artifact['backups']['local_inventory_before_v1_4'] = str(backup_path)
artifact['updated_at'] = now
for key in ('report_infra_discord_message_id', 'source_report', 'report_readback'):
    artifact.pop(key, None)

counter_id = 'zeus-mgs-offer-quiz-daily-views-dicasfinancas-20260921'
counter_matches = [item for item in inventory.get('runtime_artifacts', []) if item.get('id') == counter_id]
if len(counter_matches) > 1:
    raise SystemExit('duplicate counter artifact')
counter: dict = counter_matches[0] if counter_matches else {'id': counter_id}
counter.update({
    'agent': 'zeus',
    'type': 'wordpress_database_table',
    'owner': 'Rodolfo Mattei / Zeus',
    'status': 'active_validated_empty_after_qa',
    'authorized_by': 'Rodolfo Mattei',
    'authorization_source': 'discord:thread:1551602673441185934#1551628631002841149',
    'site': 'dicasfinancas.info',
    'table': 'wp_mgs_offer_quiz_daily_views',
    'schema_version': '1',
    'primary_key': 'view_date',
    'columns': {'view_date': 'date', 'view_count': 'bigint unsigned', 'updated_at': 'datetime'},
    'purpose': 'Atomic shared daily pageview counter for Superdigital offer quizzes G001-G006.',
    'baseline': 1892,
    'display_formula': '1892 + views_today - 1',
    'timezone': 'America/Sao_Paulo',
    'reset_model': 'new date creates a new row; no cron required',
    'write_path': 'POST /wp-json/mgs-offer-quiz/v1/daily-view',
    'validation': artifact['validation']['concurrency_fixture'] + '; ' + artifact['validation']['new_date_fixture'] + '; ' + artifact['validation']['qa_cleanup'],
    'backup': artifact['backups']['remote_v1_4_pre'] + '/database-before-v1.4.sql',
    'created_at': counter.get('created_at', now),
    'updated_at': now,
})
if not counter_matches:
    inventory['runtime_artifacts'].append(counter)

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
    'purpose': 'Procedimento operacional de quizzes WordPress, redirects, paridade visual e contadores reais de pageviews.',
    'validation': 'Runtime e mirror têm SHA-256 idêntico; regra distingue animação randômica de contador real e exige endpoint atômico, reset por data, concorrência e cleanup.',
    'updated_at': now,
    'source': 'discord:thread:1551602673441185934#1551628631002841149',
})
for key in ('report_infra_discord_message_id', 'source_report', 'report_readback'):
    skill.pop(key, None)

if isinstance(inventory.get('_meta'), dict):
    inventory['_meta']['updated_at'] = now
serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + '\n'
temp_path = inventory_path.with_name(inventory_path.name + '.mgs-offer-quiz-v1.4.tmp')
with temp_path.open('w', encoding='utf-8') as handle:
    handle.write(serialized)
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp_path, inventory_path)

with inventory_path.open(encoding='utf-8') as handle:
    readback = json.load(handle)
plugin_rb = [item for item in readback['runtime_artifacts'] if item.get('id') == artifact_id]
counter_rb = [item for item in readback['runtime_artifacts'] if item.get('id') == counter_id]
skill_rb = [item for item in readback['profile_skill_references'] if item.get('id') == skill_id]
if len(plugin_rb) != 1 or plugin_rb[0]['plugin']['version'] != '1.4.0' or len(plugin_rb[0]['routes']) != 6:
    raise SystemExit('plugin inventory readback failed')
if len(counter_rb) != 1 or counter_rb[0]['baseline'] != 1892:
    raise SystemExit('counter inventory readback failed')
if len(skill_rb) != 1 or skill_rb[0]['sha256'] != 'd1f8974f626b6724cff310e79aef7121aa6ba557bcf56235b080179793792539':
    raise SystemExit('skill inventory readback failed')

events = [
    {
        'ts': now,
        'event': 'wordpress_mgs_offer_quiz_daily_pageview_counter_deployed',
        'actor': 'zeus',
        'requested_by': 'Rodolfo Mattei',
        'authorization_message_id': '1551628631002841149',
        'thread_id': '1551602673441185934',
        'site': 'dicasfinancas.info',
        'plugin_version': '1.4.0',
        'scope': 'G001-G006 shared',
        'counter': contract['daily_pageview_counter'],
        'validation': artifact['validation'],
        'backup': artifact['backups']['remote_v1_4_pre'],
        'result': 'success',
    },
    {
        'ts': now,
        'event': 'wordpress_mgs_offer_quiz_counter_qa_rows_cleaned',
        'actor': 'zeus',
        'site': 'dicasfinancas.info',
        'expected_qa_views': 14,
        'actual_qa_views': 14,
        'fixture_dates_removed': ['2099-12-30', '2099-12-31'],
        'production_date_row_removed': '2026-09-21',
        'remaining_rows': 0,
        'next_real_display': 1892,
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
        'change': 'Added server-side atomic daily pageview counter workflow and prohibited random timers for real-view semantics.',
        'runtime_mirror_match': True,
        'source': 'discord:thread:1551602673441185934#1551628631002841149',
        'result': 'success',
    },
]
with audit_path.open('a', encoding='utf-8') as handle:
    for event in events:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())

print(json.dumps({'plugin_inventory': artifact_id, 'counter_inventory': counter_id, 'skill_inventory': skill_id, 'events': len(events), 'updated_at': now, 'readback': 'ok'}, ensure_ascii=False))
