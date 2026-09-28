#!/usr/bin/env python3
import fcntl
import json
import os
import tempfile
from pathlib import Path

root = Path('/root/mgs-agent')
path = root / 'data/infra-inventory.json'
lock_path = root / 'data/.infra-inventory.lock'
artifact_id = 'zeus-shein-es-v2-all-managers-20260923'
previous_id = 'zeus-shein-es-parity-mavroa-boostingecon-20260923'
artifact = {
    'id': artifact_id,
    'agent': 'zeus',
    'type': 'wordpress_static_landing_configuration_expansion',
    'owner': 'Rodolfo Mattei / Zeus',
    'status': 'active_validated',
    'authorized_by': 'Rodolfo Mattei',
    'authorization_message_id': '1552356152241819700',
    'thread_id': '1552151207542399069',
    'authorization_source': 'discord:thread:1552151207542399069#1552356152241819700',
    'scope': 'Expand the Spanish SHEIN V2 landing from G002 to G001-G006 on mavroa.com and boostingecon.com without changing V1, V3 or article content.',
    'server': 'MatteiInc03JBF (46.4.95.117)',
    'plugin': {'slug': 'mgs-direct-quiz', 'version': '1.2.1', 'code_changed': False, 'status': 'active'},
    'configuration': {
        'v2_routes_per_site': ['sh2-g001','sh2-g002','sh2-g003','sh2-g004','sh2-g005','sh2-g006'],
        'created_routes_per_site': ['sh2-g001','sh2-g003','sh2-g004','sh2-g005','sh2-g006'],
        'preserved_route': 'sh2-g002',
        'v2_title': 'Recibe productos gratis en tu hogar',
        'v2_question': '¿Te gustaría recibir productos gratis?',
        'language': 'es',
        'active': True,
    },
    'sites': [
        {
            'site': 'mavroa.com',
            'webroot': '/home/runcloud/webapps/mavroa',
            'configuration_items_before': 8,
            'configuration_items_after': 13,
            'existing_items_preserved_exactly': True,
            'post_id': 9001,
            'post_sha256': '9a6faad5cd2c7695df917a9cd42fc29736f6b5a2ade7f1a7acbe1119d70706f5',
            'post_unchanged': True,
            'backup': '/home/runcloud/backups/mavroa-shein-v2-all-20260923T162942Z',
            'rollback': '/home/runcloud/backups/mavroa-shein-v2-all-20260923T162942Z/rollback.sh',
            'backup_checksums_validated': True,
        },
        {
            'site': 'boostingecon.com',
            'webroot': '/home/runcloud/webapps/boostingecon',
            'configuration_items_before': 8,
            'configuration_items_after': 13,
            'existing_items_preserved_exactly': True,
            'post_id': 9001,
            'post_sha256': '8d4e005d31b7ed1751198195be4578a7acd9bf804af7f1c5a683803442e3e0bc',
            'post_unchanged': True,
            'backup': '/home/runcloud/backups/boostingecon-shein-v2-all-20260923T162942Z',
            'rollback': '/home/runcloud/backups/boostingecon-shein-v2-all-20260923T162942Z/rollback.sh',
            'backup_checksums_validated': True,
        },
    ],
    'validation': {
        'wordpress_readback': '13/13 configurations per site; 8 previous items exact; 5 new clones exact',
        'http_public': {'passed': 28, 'total': 28, 'detail': '13 active routes + one real 404 per site'},
        'browser_mobile': {'passed': 12, 'total': 12, 'viewports': ['320x700','360x800','390x844'], 'real_clicks': 12, 'query_params_exact_once': True, 'overflow': False},
        'article_hash_unchanged': True,
    },
    'canonical_knowledge': {
        'source': 'context/acquisition.md',
        'registry_ids': ['DIRECT-SHEIN-MAVROA-ES-V2-ALL-1552356152241819700','DIRECT-SHEIN-BOOSTINGECON-ES-V2-ALL-1552356152241819700'],
        'canonical_keys': ['acquisition.direct_shein.mavroa.landings','acquisition.direct_shein.boostingecon.landings'],
        'status': 'active',
        'validation': 'knowledge-control validate PASS; regression 19/19 PASS',
    },
    'evidence': '/root/mgs-agent/work/shein-es-v2-all-managers-20260923T162942Z/final-validation-summary.json',
    'updated_at': '2026-09-23T16:29:42Z',
    'report_infra_pending': True,
}
with lock_path.open('a+') as lock:
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    data = json.loads(path.read_text())
    rows = data.setdefault('runtime_artifacts', [])
    if any(row.get('id') == artifact_id for row in rows):
        raise SystemExit('artifact already exists')
    previous = [row for row in rows if row.get('id') == previous_id]
    if len(previous) != 1:
        raise SystemExit(f'expected one previous artifact, found {len(previous)}')
    previous[0]['status'] = 'superseded'
    previous[0]['superseded_by'] = artifact_id
    if isinstance(previous[0].get('canonical_knowledge'), dict):
        previous[0]['canonical_knowledge']['status'] = 'superseded'
        previous[0]['canonical_knowledge']['superseded_by'] = 'DIRECT-SHEIN-BOOSTINGECON-ES-V2-ALL-1552356152241819700'
    rows.append(artifact)
    if isinstance(data.get('_meta'), dict):
        data['_meta']['last_updated'] = '2026-09-23T16:29:42Z'
        data['_meta']['updated_by'] = 'zeus'
    mode = path.stat().st_mode & 0o777
    fd, tmp_name = tempfile.mkstemp(prefix='.infra-inventory.', suffix='.json', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
print(json.dumps({'status':'ok','artifact_id':artifact_id,'previous_status':'superseded','report_infra_pending':True}))
