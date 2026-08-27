from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.daily_cpv import DailyPaths, LiveDailyBackend, atomic_inventory, stock_counts

ASSET_IDS = {
    'asset_5966c098f64de6d561ab',
    'asset_dea92e6bba464578897b',
    'asset_303bb59d1847ccd47afe',
}
ACCOUNT_ID = '1046241194533786'
CAMPAIGN_ID = '120250952825350632'
ADSET_ID = '120250952825540632'
INVENTORY = ROOT / 'data/ares/creative-ops/inventory/assets.jsonl'
AUDIT = ROOT / 'data/ares/creative-ops/audit/lifecycle/cpv-c31-from-zero-testing-20260827.json'
ENGINE_AUDIT = ROOT / 'data/ares/meta-ads/engine-v3/audit/cpv-c31-from-zero-20260827.json'
ACTIVATION_AUDIT = WORK / 'activation-audit.json'


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    directory_fd = os.open(str(path.parent), os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def load_inventory() -> list[dict]:
    return [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]


def main() -> int:
    prepared = json.loads((WORK / 'prepared-media.json').read_text())
    prestage = json.loads((WORK / 'prestage-readback.json').read_text())
    final_live = json.loads((WORK / 'final-live-readback.json').read_text())
    final_videos = json.loads((WORK / 'final-video-readback.json').read_text())
    activation = json.loads(ACTIVATION_AUDIT.read_text())
    engine = json.loads(ENGINE_AUDIT.read_text())

    if activation.get('status') != 'COMPLETE_VERIFIED' or str((activation.get('after') or {}).get('campaign', {}).get('configured_status') or '') != 'ACTIVE':
        raise RuntimeError('C31 activation is not verified ACTIVE')
    if engine.get('status') != 'COMPLETE_PAUSED' or CAMPAIGN_ID not in (engine.get('result') or {}).get('campaign_ids', []):
        raise RuntimeError('C31 engine audit is not complete for expected campaign')

    prepared_by_asset = {str(row['asset_id']): row for row in prepared['assets']}
    prestage_by_asset = {str(row['asset_id']): row for row in prestage['records']}
    if set(prepared_by_asset) != ASSET_IDS or set(prestage_by_asset) != ASSET_IDS:
        raise RuntimeError('asset identity mismatch across prepared media and prestage')

    ads_by_stem = {}
    for ad in final_live['ads']:
        name = str(ad.get('name') or '')
        asset = next((row for row in prepared['assets'] if row['canonical_filename'].removesuffix('.mp4') in name), None)
        if not asset:
            raise RuntimeError(f'ad cannot be mapped to canonical asset: {name}')
        ads_by_stem[str(asset['asset_id'])] = ad
    if set(ads_by_stem) != ASSET_IDS:
        raise RuntimeError('Meta ad assignment mapping incomplete')

    derived_by_asset: dict[str, dict[str, str]] = {}
    for item in final_videos['results']:
        asset_id = str((item.get('expected') or {}).get('asset_id') or '')
        title = str((item.get('video') or {}).get('title') or '')
        video_id = str((item.get('video') or {}).get('id') or '')
        if asset_id not in ASSET_IDS or not video_id:
            raise RuntimeError('derived video identity is invalid')
        orientation = 'vertical' if title.startswith('V3 VERTICAL ') else 'square' if title.startswith('V3 SQUARE ') else ''
        if not orientation:
            raise RuntimeError('derived video orientation is invalid')
        derived_by_asset.setdefault(asset_id, {})[orientation] = video_id
    if set(derived_by_asset) != ASSET_IDS or any(set(value) != {'vertical', 'square'} for value in derived_by_asset.values()):
        raise RuntimeError('derived dual-video mapping incomplete')

    rows = load_inventory()
    by_asset = {str(row.get('asset_id') or ''): row for row in rows if str(row.get('asset_id') or '') in ASSET_IDS}
    if set(by_asset) != ASSET_IDS:
        raise RuntimeError('inventory does not contain all C31 assets exactly once')
    for asset_id, row in by_asset.items():
        if row.get('status') not in {'01_READY', '02_TESTING'}:
            raise RuntimeError(f'unexpected inventory status before finalization: {asset_id}')
        if row.get('status') == '01_READY' and row.get('used_by') != 'ARES_V3_IN_FLIGHT':
            raise RuntimeError(f'asset is not reserved by the in-flight C31 request: {asset_id}')
        if str(row.get('reservation_request_id') or '') != 'cpv-c31-from-zero-20260827':
            raise RuntimeError(f'asset reservation request mismatch: {asset_id}')
        if str(row.get('asset_drive_id') or '') != str(prepared_by_asset[asset_id]['asset_drive_id']):
            raise RuntimeError(f'Drive ID mismatch in inventory: {asset_id}')
        if str(row.get('clean_checksum') or '') != str(prepared_by_asset[asset_id]['checksum']):
            raise RuntimeError(f'checksum mismatch in inventory: {asset_id}')

    backend = LiveDailyBackend(DailyPaths())
    drive_before = backend.drive_preflight()
    if drive_before.get('service_account') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com' or drive_before.get('project_id') != 'mgs-core-prod':
        raise RuntimeError('canonical Drive service account mismatch')
    live_before = {str(row.get('id') or ''): row for row in drive_before['drive']['files']}
    before_assets = {}
    for asset_id, row in by_asset.items():
        drive_id = str(row['asset_drive_id'])
        live = live_before.get(drive_id)
        if not live or live.get('driveId') != '0AEwt4Ye690ocUk9PVA' or live.get('location') not in {'01_READY', '02_TESTING'}:
            raise RuntimeError(f'live Drive asset is not in a movable canonical state: {asset_id}')
        before_assets[asset_id] = {
            'asset_drive_id': drive_id,
            'location': live.get('location'),
            'parents': live.get('parents'),
            'md5Checksum': live.get('md5Checksum'),
            'size': live.get('size'),
        }

    audit = {
        'schema_version': 1,
        'request_id': 'cpv-c31-from-zero-20260827',
        'status': 'IN_FLIGHT',
        'started_at_utc': now_utc(),
        'service_account': drive_before['service_account'],
        'project_id': drive_before['project_id'],
        'drive_id': '0AEwt4Ye690ocUk9PVA',
        'campaign_id': CAMPAIGN_ID,
        'adset_id': ADSET_ID,
        'asset_ids': sorted(ASSET_IDS),
        'before_assets': before_assets,
        'drive_moves': {},
        'inventory_written': False,
    }
    atomic_json(AUDIT, audit)

    for asset_id, row in by_asset.items():
        live = live_before[str(row['asset_drive_id'])]
        audit['drive_moves'][str(row['asset_drive_id'])] = backend.move_asset(live)
        atomic_json(AUDIT, audit)

    assigned_at = now_utc()
    for asset_id, row in by_asset.items():
        ad = ads_by_stem[asset_id]
        creative = ad.get('creative') or {}
        prestage_row = prestage_by_asset[asset_id]
        derived = derived_by_asset[asset_id]
        existing = next(
            (
                item for item in row.get('test_history') or []
                if str(item.get('campaign_id') or '') == CAMPAIGN_ID and str(item.get('ad_id') or '') == str(ad.get('id') or '')
            ),
            None,
        )
        attempt_number = int((existing or {}).get('attempt') or (int(row.get('test_attempt_count') or 0) + 1))
        if existing is None:
            row.setdefault('test_history', []).append({
                'attempt': attempt_number,
                'assigned_at_utc': assigned_at,
                'request_id': 'cpv-c31-from-zero-20260827',
                'execution_mode': 'from_zero_prestaged',
                'campaign_id': CAMPAIGN_ID,
                'adset_id': ADSET_ID,
                'ad_id': str(ad['id']),
                'creative_id': str(creative['id']),
                'source_ad_id': '0',
                'effective_object_story_id': str(creative.get('effective_object_story_id') or ''),
                'vertical_video_id': derived['vertical'],
                'square_video_id': derived['square'],
                'prestage_vertical_video_id': str(prestage_row['vertical_video_id']),
                'prestage_square_video_id': str(prestage_row['square_video_id']),
                'campaign_audit': str(ENGINE_AUDIT),
                'activation_audit': str(ACTIVATION_AUDIT),
            })
        move = audit['drive_moves'][str(row['asset_drive_id'])]
        row.update(
            status='02_TESTING',
            evaluation_status='EM_TESTE',
            retest_eligible=False,
            test_attempt_count=attempt_number,
            reservation_status='UTILIZADO_PELO_ARES',
            ares_eligible=False,
            used_by='ARES',
            campaign_owner='Ares',
            ad_account_id=ACCOUNT_ID,
            meta_campaign_id=CAMPAIGN_ID,
            meta_adset_id=ADSET_ID,
            meta_ad_id=str(ad['id']),
            meta_creative_id=str(creative['id']),
            meta_lineage_source_ad_id='0',
            effective_object_story_id=str(creative.get('effective_object_story_id') or ''),
            meta_video_id=derived['vertical'],
            meta_video_ids=[derived['vertical'], derived['square']],
            meta_prestage_video_ids=[str(prestage_row['vertical_video_id']), str(prestage_row['square_video_id'])],
            meta_video_materialization='from_zero_prestaged_derived',
            campaign_audit=str(ENGINE_AUDIT),
            activation_audit=str(ACTIVATION_AUDIT),
            drive_status_readback=move,
            asset_path='MGS-AGENTS/CRIATIVOS/CAR_BR_BR/VID/02_TESTING',
            last_reconciled_at=assigned_at,
        )
    atomic_inventory(INVENTORY, rows)
    audit['inventory_written'] = True
    atomic_json(AUDIT, audit)

    readback_rows = load_inventory()
    readback_by_asset = {str(row.get('asset_id') or ''): row for row in readback_rows if str(row.get('asset_id') or '') in ASSET_IDS}
    drive_after = backend.drive_preflight()
    live_after = {str(row.get('id') or ''): row for row in drive_after['drive']['files']}
    checks = {}
    for asset_id, row in readback_by_asset.items():
        live = live_after.get(str(row['asset_drive_id'])) or {}
        checks[asset_id] = {
            'inventory_testing': row.get('status') == '02_TESTING',
            'inventory_used': row.get('used_by') == 'ARES' and row.get('reservation_status') == 'UTILIZADO_PELO_ARES',
            'inventory_campaign': str(row.get('meta_campaign_id') or '') == CAMPAIGN_ID,
            'inventory_adset': str(row.get('meta_adset_id') or '') == ADSET_ID,
            'inventory_ad': bool(str(row.get('meta_ad_id') or '')),
            'inventory_creative': bool(str(row.get('meta_creative_id') or '')),
            'inventory_from_zero': str(row.get('meta_lineage_source_ad_id') or '') == '0' and row.get('meta_video_materialization') == 'from_zero_prestaged_derived',
            'drive_testing': live.get('location') == '02_TESTING',
            'drive_id': live.get('driveId') == '0AEwt4Ye690ocUk9PVA',
            'drive_checksum': str(live.get('md5Checksum') or '') == str(prepared_by_asset[asset_id]['drive_readback']['md5Checksum']),
        }
    if set(checks) != ASSET_IDS or not all(all(values.values()) for values in checks.values()):
        audit['status'] = 'READBACK_MISMATCH'
        audit['checks'] = checks
        atomic_json(AUDIT, audit)
        raise RuntimeError(json.dumps(checks, ensure_ascii=False))

    stock = stock_counts(readback_rows, drive_after['drive'])
    audit.update(
        status='COMPLETE_VERIFIED',
        completed_at_utc=now_utc(),
        checks=checks,
        stock_remaining=stock,
        after_assets={
            asset_id: {
                'status': readback_by_asset[asset_id].get('status'),
                'asset_drive_id': readback_by_asset[asset_id].get('asset_drive_id'),
                'meta_ad_id': readback_by_asset[asset_id].get('meta_ad_id'),
                'meta_creative_id': readback_by_asset[asset_id].get('meta_creative_id'),
                'meta_video_ids': readback_by_asset[asset_id].get('meta_video_ids'),
                'location': live_after[str(readback_by_asset[asset_id]['asset_drive_id'])].get('location'),
            }
            for asset_id in sorted(ASSET_IDS)
        },
    )
    atomic_json(AUDIT, audit)
    print(json.dumps({
        'status': 'C31_ASSETS_TESTING_VERIFIED',
        'assets': len(ASSET_IDS),
        'drive_location': '02_TESTING',
        'inventory_status': '02_TESTING',
        'ready_folder_vid_remaining': stock['ready_folder_vid'],
        'eligible_unique_creatives_remaining': stock['eligible_unique_creatives'],
        'retest_eligible_unique_creatives': stock['retest_eligible_unique_creatives'],
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
