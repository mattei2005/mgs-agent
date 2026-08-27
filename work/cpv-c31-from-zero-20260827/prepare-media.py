from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.daily_cpv import DailyPaths, LiveDailyBackend, download_drive_file, make_square_clean, verify_clean

ASSETS = [
    {'asset_id': 'asset_5966c098f64de6d561ab', 'asset_drive_id': '16oxe4dhAVi9DECkr_NA6guV0bNKw01zT', 'checksum': 'ad4c13b56dcac61201d577296fd1f2978f65fc0e491e17d9e2fcfe5f02536905', 'canonical_filename': 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_005.mp4'},
    {'asset_id': 'asset_dea92e6bba464578897b', 'asset_drive_id': '1TAbOyxc3pgIJ6KJTidJ1DsYUAzjOBK7y', 'checksum': 'b10f3b7ecbd09ea18e90dd29cb3066f3c4e786ac5252009263450cda1d871a75', 'canonical_filename': 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_006.mp4'},
    {'asset_id': 'asset_303bb59d1847ccd47afe', 'asset_drive_id': '1dg9Vt-FjWoBNKnUhSUeZOjkKHiK0a7Sm', 'checksum': '6b9e8ef07c79e231e30433ccc8bd8684817a84c3be6659d57d6149f0c127f58a', 'canonical_filename': 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_007.mp4'},
]


def main() -> int:
    backend = LiveDailyBackend(DailyPaths())
    preflight = backend.drive_preflight()
    drive = preflight['drive']
    files = {str(row.get('id') or ''): row for row in drive.get('files') or []}
    output_assets = []
    media_root = ROOT / 'work/cpv-c31-from-zero-20260827/media'
    for asset in ASSETS:
        source = files.get(asset['asset_drive_id'])
        if not source:
            raise RuntimeError(f"Drive file missing: {asset['asset_id']}")
        if source.get('location') != '01_READY':
            raise RuntimeError(f"Drive file not in 01_READY: {asset['asset_id']}")
        item_root = media_root / asset['asset_id']
        vertical = item_root / 'vertical.mp4'
        square = item_root / 'square.mp4'
        if not vertical.exists():
            download_drive_file(backend.drive_token, source, vertical)
        vertical_check = verify_clean(vertical)
        if vertical_check['sha256'] != asset['checksum']:
            raise RuntimeError(f"clean checksum mismatch: {asset['asset_id']}")
        square_check = make_square_clean(vertical, square)
        if not square_check.get('clean'):
            raise RuntimeError(f"square is not clean: {asset['asset_id']}")
        output_assets.append({
            **asset,
            'vertical_file': str(vertical),
            'square_file': str(square),
            'vertical_readback': vertical_check,
            'square_readback': square_check,
            'drive_readback': {
                'id': source.get('id'),
                'name': source.get('name'),
                'driveId': source.get('driveId'),
                'parents': source.get('parents'),
                'location': source.get('location'),
                'size': source.get('size'),
                'md5Checksum': source.get('md5Checksum'),
            },
        })
    output = {
        'status': 'MEDIA_PREPARED_FROM_DRIVE',
        'service_account': preflight['service_account'],
        'project_id': preflight['project_id'],
        'drive_id': drive.get('drive_id') or drive.get('driveId'),
        'assets': output_assets,
    }
    out = ROOT / 'work/cpv-c31-from-zero-20260827/prepared-media.json'
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'assets': len(output_assets), 'output': str(out)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
