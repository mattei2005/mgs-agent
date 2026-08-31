from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path('/root/mgs-agent')
COMMON = BASE / 'scripts/ares-meta-common.py'
LIVE = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-preexecute-full.json'
OUT = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-final-direct-readback.json'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Carla Nunes - eggbev-us-cc-en-01 - G006'
CAMPAIGNS = ['120249822420250629', '120249822420240629']
EXPECTED_NAMES = [
    '163 - Aria Kensington - ENG - US - (pg_8348) C003 DUP01',
    '163 - Aria Kensington - ENG - US - (pg_8348) C003 DUP02',
]
EXPECTED_PAGE = '804761166056807'
EXPECTED_UTM = 'utm_campaign=pg_8348'
EXPECTED_BUDGET = '4500'

spec = importlib.util.spec_from_file_location('ares_meta_common_final_readback', COMMON)
if spec is None or spec.loader is None:
    raise SystemExit('common helper unavailable')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
token, _ = common.get_token_from_1password(item_name=TOKEN_ITEM)
live = json.loads(LIVE.read_text())
source_ads = {row['name']: row for row in live['source_ads']}
source_ids = {str(row['id']) for row in live['source_ads']}

def batch(requests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    status, rows, _ = common.graph_batch_get(token, requests)
    if status != 200 or not isinstance(rows, list):
        raise SystemExit(f'outer Graph batch failed http={status}')
    result = {str(row['name']): row for row in rows}
    failures = [row for row in rows if int(row.get('code') or 0) != 200]
    if failures:
        safe = [{'name': row.get('name'), 'code': row.get('code'), 'error': common.safe_meta_error(row.get('body') or {})} for row in failures]
        raise SystemExit('child Graph batch failed: ' + json.dumps(safe, ensure_ascii=False))
    return result

requests = []
for index, campaign_id in enumerate(CAMPAIGNS, 1):
    requests.extend([
        {'name': f'campaign_{index}', 'path': campaign_id, 'params': {'fields': 'id,name,status,effective_status,configured_status,daily_budget,start_time,objective,buying_type,bid_strategy,special_ad_categories,special_ad_category_country,created_time,updated_time'}},
        {'name': f'adsets_{index}', 'path': campaign_id + '/adsets', 'params': {'fields': 'id,name,status,effective_status,configured_status,start_time,destination_type,targeting,promoted_object,attribution_spec,billing_event,optimization_goal,issues_info', 'limit': 20}},
        {'name': f'ads_{index}', 'path': campaign_id + '/ads', 'params': {'fields': 'id,name,status,effective_status,configured_status,adset_id,source_ad_id,issues_info,failed_delivery_checks,creative{id,name,effective_object_story_id,object_story_spec,asset_feed_spec,url_tags}', 'limit': 50}},
    ])
first = batch(requests)

video_ids: set[str] = set()
for row in source_ads.values():
    for video in ((row.get('creative') or {}).get('asset_feed_spec') or {}).get('videos') or []:
        if video.get('video_id'):
            video_ids.add(str(video['video_id']))
for index in (1, 2):
    for ad in (first[f'ads_{index}']['body'].get('data') or []):
        for video in (((ad.get('creative') or {}).get('asset_feed_spec') or {}).get('videos') or []):
            if video.get('video_id'):
                video_ids.add(str(video['video_id']))
second_requests = [
    {'name': f'video_{video_id}', 'path': video_id, 'params': {'fields': 'id,title,length,status,format'}}
    for video_id in sorted(video_ids)
]
for index, campaign_id in enumerate(CAMPAIGNS, 1):
    second_requests.append({'name': f'insights_{index}', 'path': campaign_id + '/insights', 'params': {'fields': 'spend,impressions,clicks', 'date_preset': 'today', 'level': 'campaign', 'limit': 10}})
second = batch(second_requests)
video_meta = {name.removeprefix('video_'): row['body'] for name, row in second.items() if name.startswith('video_')}

def text_values(rows: list[dict[str, Any]] | None, key: str) -> list[str]:
    return sorted(str(row.get(key) or '') for row in (rows or []))

def video_signature(video_id: str) -> dict[str, Any]:
    row = video_meta.get(video_id) or {}
    formats = row.get('format') or []
    dims = sorted({(item.get('width'), item.get('height')) for item in formats if isinstance(item, dict) and (item.get('width') or item.get('height'))})
    status = row.get('status')
    if isinstance(status, dict):
        normalized_status = status.get('video_status') or status.get('status')
        if isinstance(normalized_status, dict):
            normalized_status = normalized_status.get('status')
    else:
        normalized_status = status
    return {
        'id': video_id,
        'title': row.get('title'),
        'length': row.get('length'),
        'dimensions': dims,
        'status': normalized_status,
    }

def ad_semantics(ad: dict[str, Any]) -> dict[str, Any]:
    creative = ad.get('creative') or {}
    asset_feed = creative.get('asset_feed_spec') or {}
    additional = asset_feed.get('additional_data') or {}
    videos = [video_signature(str(row['video_id'])) for row in (asset_feed.get('videos') or []) if row.get('video_id')]
    return {
        'name': ad.get('name'),
        'source_ad_id': str(ad.get('source_ad_id') or ''),
        'status': ad.get('status') or ad.get('configured_status'),
        'effective_status': ad.get('effective_status'),
        'issues_info': ad.get('issues_info') or [],
        'page_id': (creative.get('object_story_spec') or {}).get('page_id'),
        'instagram_user_id': (creative.get('object_story_spec') or {}).get('instagram_user_id'),
        'url_tags': creative.get('url_tags'),
        'bodies': text_values(asset_feed.get('bodies'), 'text'),
        'titles': text_values(asset_feed.get('titles'), 'text'),
        'descriptions': text_values(asset_feed.get('descriptions'), 'description'),
        'link_urls': text_values(asset_feed.get('link_urls'), 'website_url'),
        'call_to_action_types': sorted(str(value) for value in (asset_feed.get('call_to_action_types') or [])),
        'page_welcome_message': additional.get('page_welcome_message'),
        'videos': videos,
    }

def media_identity(rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return sorted((row.get('title'), row.get('length'), tuple(tuple(dim) for dim in row.get('dimensions') or [])) for row in rows)

source_semantics = {name: ad_semantics(row) for name, row in source_ads.items()}
checks = []
campaign_rows = []
for index, (campaign_id, expected_name) in enumerate(zip(CAMPAIGNS, EXPECTED_NAMES), 1):
    campaign = first[f'campaign_{index}']['body']
    adsets = first[f'adsets_{index}']['body'].get('data') or []
    ads = first[f'ads_{index}']['body'].get('data') or []
    target_semantics = {row['name']: ad_semantics(row) for row in ads}
    ad_comparisons = []
    for name, source in sorted(source_semantics.items()):
        target = target_semantics.get(name) or {}
        ad_comparisons.append({
            'name': name,
            'present': bool(target),
            'source_ad_lineage_match': target.get('source_ad_id') == str(source_ads[name]['id']),
            'configured_active': target.get('status') == 'ACTIVE',
            'review_or_active': target.get('effective_status') in {'ACTIVE', 'PENDING_REVIEW', 'IN_PROCESS'},
            'issues_clear': not target.get('issues_info'),
            'page_match': target.get('page_id') == source.get('page_id') == EXPECTED_PAGE,
            'instagram_identity_match': target.get('instagram_user_id') == source.get('instagram_user_id'),
            'utm_match': target.get('url_tags') == source.get('url_tags') == EXPECTED_UTM,
            'copy_match': all(target.get(field) == source.get(field) for field in ('bodies', 'titles', 'descriptions', 'link_urls', 'call_to_action_types', 'page_welcome_message')),
            'media_identity_match': media_identity(target.get('videos') or []) == media_identity(source.get('videos') or []),
            'target': target,
        })
    insight_rows = second[f'insights_{index}']['body'].get('data') or []
    insight = insight_rows[0] if insight_rows else {'spend': '0', 'impressions': '0', 'clicks': '0'}
    campaign_check = {
        'campaign_id': campaign_id,
        'campaign_name': campaign.get('name'),
        'name_match': campaign.get('name') == expected_name,
        'active': campaign.get('status') == 'ACTIVE' and campaign.get('effective_status') == 'ACTIVE',
        'budget_match': str(campaign.get('daily_budget') or '') == EXPECTED_BUDGET,
        'start_time': campaign.get('start_time'),
        'adset_count': len(adsets),
        'adset_active': len(adsets) == 1 and adsets[0].get('status') == 'ACTIVE' and adsets[0].get('effective_status') == 'ACTIVE',
        'adset_destination_match': len(adsets) == 1 and adsets[0].get('destination_type') == 'MESSENGER',
        'adset_page_match': len(adsets) == 1 and (adsets[0].get('promoted_object') or {}).get('page_id') == EXPECTED_PAGE,
        'ad_count': len(ads),
        'ads': ad_comparisons,
        'insights_today': {key: insight.get(key, '0') for key in ('spend', 'impressions', 'clicks')},
    }
    campaign_check['all_verified'] = all([
        campaign_check['name_match'], campaign_check['active'], campaign_check['budget_match'],
        campaign_check['adset_count'] == 1, campaign_check['adset_active'],
        campaign_check['adset_destination_match'], campaign_check['adset_page_match'], campaign_check['ad_count'] == 3,
        all(all(row[key] for key in ('present', 'source_ad_lineage_match', 'configured_active', 'review_or_active', 'issues_clear', 'page_match', 'instagram_identity_match', 'utm_match', 'copy_match', 'media_identity_match')) for row in ad_comparisons),
    ])
    campaign_rows.append(campaign_check)
    checks.append(campaign_check['all_verified'])

result = {
    'schema_version': 1,
    'request_id': 'eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01',
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'source_campaign_id': live['source']['id'],
    'source_ad_ids': sorted(source_ids),
    'campaigns': campaign_rows,
    'all_verified': all(checks) and len(checks) == 2,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({
    'status': 'FINAL_DIRECT_READBACK_OK' if result['all_verified'] else 'FINAL_DIRECT_READBACK_FAILED',
    'all_verified': result['all_verified'],
    'campaigns': [{
        'name': row['campaign_name'],
        'active': row['active'],
        'budget_match': row['budget_match'],
        'start_time': row['start_time'],
        'adsets': row['adset_count'],
        'ads': row['ad_count'],
        'ads_verified': sum(1 for ad in row['ads'] if all(ad[key] for key in ('present', 'source_ad_lineage_match', 'configured_active', 'review_or_active', 'issues_clear', 'page_match', 'instagram_identity_match', 'utm_match', 'copy_match', 'media_identity_match'))),
        'ad_effective_statuses': [ad['target'].get('effective_status') for ad in row['ads']],
        'insights_today': row['insights_today'],
    } for row in campaign_rows],
}, ensure_ascii=False, indent=2))
if not result['all_verified']:
    raise SystemExit(2)
