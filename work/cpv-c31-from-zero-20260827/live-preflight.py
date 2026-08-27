from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.daily_cpv import DailyPaths, LiveDailyBackend

REQUEST_ID = 'cpv-c31-from-zero-20260827'
ASSET_REFS = [
    {'asset_id': 'asset_5966c098f64de6d561ab', 'checksum': 'ad4c13b56dcac61201d577296fd1f2978f65fc0e491e17d9e2fcfe5f02536905', 'canonical_filename': 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_005.mp4'},
    {'asset_id': 'asset_dea92e6bba464578897b', 'checksum': 'b10f3b7ecbd09ea18e90dd29cb3066f3c4e786ac5252009263450cda1d871a75', 'canonical_filename': 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_006.mp4'},
    {'asset_id': 'asset_303bb59d1847ccd47afe', 'checksum': '6b9e8ef07c79e231e30433ccc8bd8684817a84c3be6659d57d6149f0c127f58a', 'canonical_filename': 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_007.mp4'},
]


def main() -> int:
    paths = DailyPaths()
    backend = LiveDailyBackend(paths)
    preflight = backend.meta_preflight()
    operation = json.loads(paths.operation.read_text())
    now_sp = datetime.now(ZoneInfo('America/Sao_Paulo'))
    source = backend.select_clone_sources(
        asset_refs=ASSET_REFS,
        campaign_count=1,
        meta_campaigns=preflight['campaigns'],
        target_date=now_sp.date().isoformat(),
        operation=operation,
        request_id=REQUEST_ID,
    )
    all_ads = backend._graph_pages(
        'act_1046241194533786/ads',
        {
            'fields': 'id,name,status,effective_status,configured_status,campaign{id,name,status,configured_status},adset{id,name},creative{id,name,effective_object_story_id,asset_feed_spec}',
            'limit': 500,
        },
    )
    advideos = backend._graph_pages(
        'act_1046241194533786/advideos',
        {'fields': 'id,title,video_status,created_time,length', 'limit': 500},
    )
    needles = {Path(item['canonical_filename']).stem for item in ASSET_REFS}
    ad_matches = []
    for ad in all_ads:
        text = json.dumps(ad, ensure_ascii=False)
        found = sorted(needle for needle in needles if needle in text)
        if found:
            ad_matches.append({
                'id': str(ad.get('id') or ''),
                'name': str(ad.get('name') or ''),
                'configured_status': str(ad.get('configured_status') or ad.get('status') or ''),
                'campaign': ad.get('campaign'),
                'matched_assets': found,
            })
    video_matches = []
    for video in advideos:
        title = str(video.get('title') or '')
        found = sorted(needle for needle in needles if needle in title)
        if found:
            video_matches.append({
                'id': str(video.get('id') or ''),
                'title': title,
                'video_status': video.get('video_status'),
                'created_time': video.get('created_time'),
                'matched_assets': found,
            })
    c31 = [
        {key: row.get(key) for key in ('id', 'name', 'status', 'effective_status', 'configured_status', 'daily_budget', 'start_time')}
        for row in preflight['campaigns']
        if 'b01fb13c31' in str(row.get('name') or '').lower()
    ]
    active_minor = sum(
        int(row.get('daily_budget') or 0)
        for row in preflight['campaigns']
        if str(row.get('configured_status') or row.get('status') or '').upper() == 'ACTIVE'
    )
    output = {
        'status': 'LIVE_PREFLIGHT_OK',
        'request_id': REQUEST_ID,
        'observed_at_sp': now_sp.isoformat(),
        'account': preflight['account'],
        'page': preflight['page'],
        'token_report': preflight['token_report'],
        'c31_campaigns': c31,
        'active_campaign_budget_minor': active_minor,
        'asset_ad_conflicts': ad_matches,
        'asset_advideo_conflicts': video_matches,
        'asset_conflict_free': not ad_matches and not video_matches,
        'source_snapshot': source,
    }
    out = ROOT / 'work/cpv-c31-from-zero-20260827/live-preflight.json'
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'status': output['status'],
        'asset_conflict_free': output['asset_conflict_free'],
        'c31_count': len(c31),
        'source_vehicle_types': source.get('campaign_vehicle_types'),
        'active_campaign_budget_minor': active_minor,
        'output': str(out),
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
