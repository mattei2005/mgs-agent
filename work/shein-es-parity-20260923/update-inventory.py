#!/usr/bin/env python3
import fcntl
import json
import os
import tempfile
from pathlib import Path

root = Path('/root/mgs-agent')
path = root / 'data/infra-inventory.json'
lock_path = root / 'data/.infra-inventory.lock'
summary_path = root / 'work/shein-es-parity-20260923/final-validation-summary.json'
summary = json.loads(summary_path.read_text())
artifact_id = 'zeus-shein-es-parity-mavroa-boostingecon-20260923'
artifact = {
    'id': artifact_id,
    'agent': 'zeus',
    'type': 'wordpress_static_landing_media_copy_and_rec_quiz_style_update',
    'owner': 'Rodolfo Mattei / Zeus',
    'status': 'active_validated',
    'authorized_by': 'Rodolfo Mattei',
    'authorization_message_id': '1552343613126737930',
    'thread_id': '1552151207542399069',
    'authorization_source': summary['authorization_source'],
    'scope': 'Bring the Spanish SHEIN V2/V3 landings and REC quiz cards on mavroa.com and boostingecon.com to the validated Yolokfx visual/copy parity, localized to Spanish.',
    'server': 'MatteiInc03JBF (46.4.95.117)',
    'plugin': {
        'slug': 'mgs-direct-quiz',
        'version': '1.2.1',
        'code_changed': False,
        'status': 'active',
        'manifest_files': 15,
        'source_production_manifest_match': True,
    },
    'configuration': {
        'v2_routes_per_site': ['sh2-g002'],
        'v3_routes_per_site': ['sh3-g001', 'sh3-g002', 'sh3-g003', 'sh3-g004', 'sh3-g005', 'sh3-g006'],
        'v2_title': summary['changes']['v2']['title'],
        'v2_question': summary['changes']['v2']['question'],
        'v3_title': summary['changes']['v3']['title'],
        'v3_categories': summary['changes']['v3']['categories'],
        'article_quiz_button_background': '#16C45A',
        'article_quiz_button_border': '#11AC51',
        'article_quiz_button_text': '#FFFFFF',
        'article_quiz_order': summary['changes']['article']['order'],
    },
    'sites': [],
    'validation': summary['validation'],
    'procedural_source': {
        'skill': 'landing-page-shein',
        'version': '1.3.3',
        'live_path': '/root/.hermes/profiles/zeus/skills/ops/landing-page-shein/SKILL.md',
        'versioned_path': '/root/mgs-agent/profiles/zeus-skills/ops/landing-page-shein/SKILL.md',
        'sha256': '0a6287fe9f02534c4cc1155b1f8a61391ccee999c4d1022e07556f4cbbb0a5f2',
        'mirror_match': True,
    },
    'evidence': str(summary_path),
    'updated_at': summary['completed_at'],
    'report_infra_pending': True,
}
for key, domain, webroot in (
    ('mavroa', 'mavroa.com', '/home/runcloud/webapps/mavroa'),
    ('boostingecon', 'boostingecon.com', '/home/runcloud/webapps/boostingecon'),
):
    site = summary['sites'][key]
    artifact['sites'].append({
        'site': domain,
        'webroot': webroot,
        'configuration_items': site['configuration_items'],
        'expected_field_changes': site['expected_field_changes'],
        'unexpected_configuration_changes': site['unexpected_configuration_changes'],
        'post_id': site['post_id'],
        'post_sha256': site['post_sha256'],
        'media': site['media'],
        'backup': site['backup'],
        'rollback': site['rollback'],
        'backup_checksums_validated': site['backup_checksums_validated'],
        'browser': site['browser'],
    })

lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open('a+') as lock:
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    data = json.loads(path.read_text())
    rows = data.setdefault('runtime_artifacts', [])
    matches = [i for i, row in enumerate(rows) if row.get('id') == artifact_id]
    if len(matches) > 1:
        raise SystemExit(f'duplicate artifact id: {artifact_id}')
    result = 'created'
    if matches:
        rows[matches[0]] = artifact
        result = 'updated'
    else:
        rows.append(artifact)
    data['_meta']['updated_at'] = summary['completed_at']
    previous_mode = path.stat().st_mode & 0o777
    fd, tmp_name = tempfile.mkstemp(prefix='.infra-inventory.', suffix='.json', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, previous_mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
print(json.dumps({'status': 'ok', 'result': result, 'artifact_id': artifact_id, 'runtime_artifacts': len(data['runtime_artifacts'])}))
