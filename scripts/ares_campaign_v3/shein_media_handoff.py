"""Validated handoff of pre-staged new media; canonical inventory/Drive only.

Selection, sanitation and upload remain in Creative Ops/Engine pre-stage. This
handoff accepts only exact account-ready media reserved for the same request.
"""
from __future__ import annotations
import fcntl
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .media_registry import MediaRegistry


def _ops(base):
    spec = importlib.util.spec_from_file_location('ares_shein_canonical_drive_ops', base / 'scripts/ares-shein-campaigns.py')
    if spec is None or spec.loader is None:
        raise ValueError('canonical Creative Ops handoff unavailable')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _get(url, token):
    with urlopen(Request(url, headers={'Authorization': 'Bearer ' + token, 'User-Agent': 'MGS-Ares-SHEIN/3'}), timeout=60) as response:
        return json.load(response)


def ready_status(value):
    status = value.get('status') or value.get('video_status')
    if isinstance(status, dict):
        status = status.get('video_status')
    if isinstance(status, dict):
        status = status.get('status')
    return status == 'ready'


def load_ready_assets(request, profile, base, common, token):
    refs = request.get('asset_refs') or []
    if not refs or len({r['asset_id'] for r in refs}) != len(refs):
        raise ValueError('new media requires unique pre-staged asset references from Creative Ops')
    inventory = {r['asset_id']: r for r in (json.loads(line) for line in (base / 'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip())}
    registry = MediaRegistry(base / 'data/ares/meta-ads/engine-v3/media-registry.json')
    ops = _ops(base); drive_token, _ = ops.drive_runtime_token()
    rows = []
    for ref in refs:
        row = inventory.get(ref['asset_id']) or {}
        if row.get('reservation_request_id') != request['request_id']:
            raise ValueError('asset must be reserved by canonical Creative Ops for this exact request')
        if row.get('language') != profile['language'] or row.get('vertical') != 'SHEIN' or row.get('metadata_clean') is not True:
            raise ValueError('asset language, vertical or sanitized metadata mismatch')
        if row.get('status') not in {'01_READY', 'READY'} or not str(row.get('asset_path', '')).endswith('/01_READY'):
            raise ValueError('asset is not in the reconciled READY pool')
        if row.get('clean_checksum') != ref['checksum'] or row.get('used_by') or row.get('meta_ad_id'):
            raise ValueError('asset checksum or previous-use conflict')
        media = registry.require_ready(profile['account_id'], ref['asset_id'], ref['checksum'], required_variants=('vertical',))
        file = ops.drive_file_readback(drive_token, row['asset_drive_id'])
        if file.get('driveId') != '0AEwt4Ye690ocUk9PVA' or file.get('trashed') or file.get('name') != row['canonical_filename'] or len(file.get('parents') or []) != 1:
            raise ValueError('Drive identity/parent/name mismatch')
        ready = ops.drive_file_readback(drive_token, file['parents'][0])
        if ready.get('name') != '01_READY' or len(ready.get('parents') or []) != 1:
            raise ValueError('canonical READY folder identity mismatch')
        q = "'" + ready['parents'][0] + "' in parents and name = '02_TESTING' and trashed = false"
        siblings = _get('https://www.googleapis.com/drive/v3/files?' + urlencode({'q': q, 'fields': 'files(id,name,driveId)', 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true'}), drive_token)
        testing = siblings.get('files') or []
        if len(testing) != 1 or testing[0].get('driveId') != '0AEwt4Ye690ocUk9PVA':
            raise ValueError('canonical TESTING destination missing or ambiguous')
        h, video, _ = common.graph_get(media['vertical_video_id'], token, {'fields': 'id,title,status,thumbnails'})
        if h != 200 or not ready_status(video) or ref['asset_id'] not in str(video.get('title')) or ref['checksum'][:10] not in str(video.get('title')):
            raise ValueError('pre-staged video readiness/lineage title mismatch')
        thumbs = video.get('thumbnails', {}).get('data') or []
        if not thumbs:
            raise ValueError('pre-staged video thumbnail unavailable')
        rows.append({**media, 'language': row['language'], 'canonical_filename': row['canonical_filename'], 'asset_drive_id': row['asset_drive_id'],
                     'thumbnail_url': thumbs[0]['uri'], 'drive_md5': file.get('md5Checksum'), 'ready_parent_id': file['parents'][0], 'testing_parent_id': testing[0]['id']})
    # Association is checked on the exact target account, never by a Page video edge.
    h, library, _ = common.graph_get('act_' + profile['account_id'] + '/advideos', token, {'fields': 'id', 'limit': 500})
    if h != 200 or library.get('paging', {}).get('next'):
        raise ValueError('exact-account media association inventory incomplete')
    ids = {str(r['id']) for r in library.get('data', [])}
    if any(r['vertical_video_id'] not in ids for r in rows):
        raise ValueError('pre-staged media not associated with target account')
    return rows


def finalize_ready_assets(state, live, base, common, token):
    assets = state.get('new_media_assets') or []
    if not assets:
        raise ValueError('new-media postprocess has no inventory lineage')
    ops = _ops(base); drive_token, _ = ops.drive_runtime_token()
    desired = state['manifest']['campaigns'][0]
    actual = {a['name']: a for a in live['ads']['data']}
    assignments = {}
    for slot in desired['ads']:
        ad = actual[slot['name']]; cr = ad['creative']; vid = cr.get('object_story_spec', {}).get('video_data', {}).get('video_id')
        asset = next(r for r in assets if r['asset_id'] == slot['media']['asset_id'])
        h, video, _ = common.graph_get(vid, token, {'fields': 'id,title,status'})
        if h != 200 or not ready_status(video) or asset['asset_id'] not in str(video.get('title')) or asset['checksum'][:10] not in str(video.get('title')):
            raise ValueError('final Meta media lineage/readiness mismatch')
        assignments[asset['asset_id']] = {'campaign_id': live['campaign']['id'], 'adset_id': live['adsets']['data'][0]['id'], 'ad_id': ad['id'],
                                        'creative_id': cr['id'], 'video_id': vid, 'post_id': cr.get('effective_object_story_id')}
    # Moves are idempotent and retain the original media and pre-stage registry.
    for asset in assets:
        ops.move_asset_to_testing(drive_token, asset, ready_id=asset['ready_parent_id'], testing_id=asset['testing_parent_id'])
    inventory_path = base / 'data/ares/creative-ops/inventory/assets.jsonl'
    with inventory_path.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = [json.loads(line) for line in inventory_path.read_text().splitlines() if line.strip()]
        for row in rows:
            if row.get('asset_id') not in assignments:
                continue
            if row.get('reservation_request_id') != state['request']['request_id']:
                raise ValueError('inventory reservation changed during postprocess')
            a = assignments[row['asset_id']]
            row.update(status='02_TESTING', ares_eligible=False, used_by=a['campaign_id'], ad_account_id=desired['account_id'],
                       meta_ad_id=a['ad_id'], meta_creative_id=a['creative_id'], meta_video_id=a['video_id'], effective_object_story_id=a['post_id'])
            row['asset_path'] = row['asset_path'].removesuffix('/01_READY') + '/02_TESTING'
            history = row.setdefault('test_history', [])
            if not any(x.get('campaign_id') == a['campaign_id'] for x in history):
                history.append({**a, 'request_id': state['request']['request_id'], 'source': 'general_shein_engine_v3'})
        backup = base / 'data/ares/meta-ads/audit/shein/campaigns/single-clone' / (state['request']['request_id'] + '-inventory-before.jsonl')
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(inventory_path.read_bytes()); os.chmod(backup, 0o600)
        fd, temporary = tempfile.mkstemp(prefix='.shein-inventory-', dir=inventory_path.parent)
        with os.fdopen(fd, 'w') as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + '\n')
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, inventory_path)
        # Exact target lineage readback; do not infer success from atomic replace alone.
        after = {r['asset_id']: r for r in (json.loads(line) for line in inventory_path.read_text().splitlines() if line.strip())}
        if any(after[aid].get('meta_ad_id') != a['ad_id'] or after[aid].get('status') != '02_TESTING' for aid, a in assignments.items()):
            raise ValueError('inventory assignment readback mismatch')
    return assignments
