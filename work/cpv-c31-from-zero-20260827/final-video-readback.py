from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common

TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
OUTPUT = WORK / 'final-video-readback.json'


def main() -> int:
    readback = json.loads((WORK / 'final-live-readback.json').read_text())
    manifest = json.loads((WORK / 'manifest-sealed.json').read_text())
    ads_by_creative = {str((row.get('creative') or {}).get('id') or ''): row for row in readback['ads']}
    creative_specs = {row['name']: row for row in manifest['campaigns'][0]['ads']}
    expected_by_video: dict[str, dict] = {}
    for creative in readback['creatives']:
        ad = ads_by_creative[str(creative['id'])]
        spec = creative_specs[ad['name']]
        media = spec['media']
        for video in (creative.get('asset_feed_spec') or {}).get('videos') or []:
            expected_by_video[str(video['video_id'])] = {
                'asset_id': media['asset_id'],
                'checksum_short': media['checksum'][:12],
                'ad_name': ad['name'],
                'creative_id': creative['id'],
            }
    if len(expected_by_video) != 6:
        raise RuntimeError('expected six distinct final video IDs')
    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)
    requests = [
        {'name': f'video_{index}', 'path': video_id, 'params': {'fields': 'id,title,status,length,created_time,updated_time'}}
        for index, video_id in enumerate(expected_by_video, start=1)
    ]
    status, rows, _ = common.graph_batch_get(token, requests)
    if status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'video readback outer failed http={status}')
    errors = [row for row in rows if int(row.get('code') or 0) != 200]
    if errors:
        raise RuntimeError(json.dumps([{'name': row.get('name'), 'code': row.get('code'), 'error': common.safe_meta_error(row.get('body') or {})} for row in errors], ensure_ascii=False))
    results = []
    for row in rows:
        video = row['body']
        expected = expected_by_video[str(video['id'])]
        status_text = json.dumps(video.get('status') or {}, ensure_ascii=False).upper()
        title = str(video.get('title') or '')
        checks = {
            'id_exact': str(video.get('id') or '') in expected_by_video,
            'asset_title_lineage': expected['asset_id'] in title,
            'orientation_title': title.startswith('V3 VERTICAL ') or title.startswith('V3 SQUARE '),
            'video_ready': 'COMPLETE' in status_text and not any(value in status_text for value in ('ERROR', 'FAILED')),
            'length_positive': float(video.get('length') or 0) > 0,
        }
        results.append({'video': video, 'expected': expected, 'checks': checks})
    if not all(all(item['checks'].values()) for item in results):
        raise RuntimeError(json.dumps(results, ensure_ascii=False))
    output = {
        'status': 'FINAL_DERIVED_VIDEOS_VERIFIED',
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'video_count': len(results),
        'results': results,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'video_count': output['video_count']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
