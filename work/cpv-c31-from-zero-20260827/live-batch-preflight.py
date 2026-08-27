from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common


ACCOUNT_ID = '1046241194533786'
REFERENCE_CAMPAIGN_ID = '120250925458300632'
REFERENCE_ADSET_ID = '120250925458440632'
OLD_C31_ID = '120250951557410632'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
OUTPUT = ROOT / 'work/cpv-c31-from-zero-20260827/live-batch-preflight.json'
ASSETS = [
    ('asset_5966c098f64de6d561ab', 'ad4c13b56dca', 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_005'),
    ('asset_dea92e6bba464578897b', 'b10f3b7ecbd0', 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_006'),
    ('asset_303bb59d1847ccd47afe', '6b9e8ef07c79', 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_007'),
]


def op(kind: str, endpoint: str, params: dict) -> dict:
    return {'name': kind, 'path': endpoint, 'params': params}


def main() -> int:
    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)
    ops = [
        op('account', f'act_{ACCOUNT_ID}', {'fields': 'id,name,account_status,disable_reason,currency,timezone_name,timezone_offset_hours_utc,amount_spent,balance,spend_cap,business'}),
        op('campaign_reference', REFERENCE_CAMPAIGN_ID, {'fields': 'id,name,status,configured_status,effective_status,objective,buying_type,daily_budget,bid_strategy,special_ad_categories,special_ad_category_country,start_time,created_time,updated_time'}),
        op('adset_reference', REFERENCE_ADSET_ID, {'fields': 'id,name,status,configured_status,effective_status,campaign_id,start_time,end_time,billing_event,optimization_goal,bid_amount,bid_constraints,targeting,promoted_object,attribution_spec,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities,dsa_beneficiary,dsa_payor,destination_type,created_time,updated_time'}),
        op('ads_reference', f'{REFERENCE_CAMPAIGN_ID}/ads', {'fields': 'id,name,status,configured_status,effective_status,source_ad_id,issues_info,adset_id,creative{id,name,object_story_spec,asset_feed_spec,degrees_of_freedom_spec,effective_object_story_id}', 'limit': 20}),
        op('campaigns_account', f'act_{ACCOUNT_ID}/campaigns', {'fields': 'id,name,status,configured_status,effective_status,daily_budget,bid_strategy,start_time,created_time,updated_time', 'limit': 500}),
        op('old_c31', OLD_C31_ID, {'fields': 'id,name,status,configured_status,effective_status,daily_budget,bid_strategy,start_time,created_time,updated_time'}),
        op('videos_recent', f'act_{ACCOUNT_ID}/advideos', {'fields': 'id,title,video_status,created_time,updated_time,length', 'limit': 500}),
        op('page_preflight', 'me/accounts', {'fields': 'id,name,tasks', 'limit': 200}),
    ]
    for asset_id, checksum_short, stem in ASSETS:
        ops.append(op(f'ad_asset_{asset_id}', f'act_{ACCOUNT_ID}/ads', {
            'fields': 'id,name,status,configured_status,effective_status,source_ad_id,campaign{id,name,status,configured_status},adset{id,name},creative{id,name,effective_object_story_id}',
            'filtering': [{'field': 'name', 'operator': 'CONTAIN', 'value': stem}],
            'limit': 100,
        }))
    outer_status, rows, _ = common.graph_batch_get(token, ops)
    if outer_status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'batch outer failed http={outer_status}')
    child_errors = [row for row in rows if int(row.get('code') or 0) != 200]
    if child_errors:
        safe = [{'name': row.get('name'), 'code': row.get('code'), 'error': common.safe_meta_error(row.get('body') or {})} for row in child_errors]
        raise RuntimeError(f'batch child errors: {json.dumps(safe, ensure_ascii=False)}')
    by_kind = {row['name']: row['body'] for row in rows}
    campaigns = (by_kind['campaigns_account'].get('data') or [])
    c31_pattern = re.compile(r'(^|\D)31(\D|$)|b01fb13c31', re.I)
    c31_candidates = [row for row in campaigns if c31_pattern.search(str(row.get('name') or ''))]
    asset_conflicts = {}
    for asset_id, _, _ in ASSETS:
        asset_conflicts[asset_id] = by_kind[f'ad_asset_{asset_id}'].get('data') or []
    videos = by_kind['videos_recent'].get('data') or []
    video_matches = []
    for row in videos:
        title = str(row.get('title') or '')
        if any(asset_id in title or checksum_short in title for asset_id, checksum_short, _ in ASSETS):
            video_matches.append(row)
    page = next((row for row in (by_kind['page_preflight'].get('data') or []) if str(row.get('id') or '') == '621037101089579'), None)
    output = {
        'status': 'LIVE_BATCH_PREFLIGHT_OK',
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'logical_calls': len(ops),
        'outer_calls': 1,
        'account': by_kind['account'],
        'reference_campaign': by_kind['campaign_reference'],
        'reference_adset': by_kind['adset_reference'],
        'reference_ads': by_kind['ads_reference'].get('data') or [],
        'old_c31': by_kind['old_c31'],
        'c31_account_candidates': c31_candidates,
        'asset_conflicts': asset_conflicts,
        'video_matches': video_matches,
        'page_preflight': page,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'status': output['status'],
        'logical_calls': output['logical_calls'],
        'c31_candidates': len(c31_candidates),
        'asset_conflict_ads': sum(len(rows) for rows in asset_conflicts.values()),
        'video_matches': len(video_matches),
        'output': str(OUTPUT),
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
