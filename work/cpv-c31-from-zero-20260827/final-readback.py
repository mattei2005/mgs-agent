from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common

ACCOUNT_ID = '1046241194533786'
CAMPAIGN_ID = '120250952825350632'
OLD_C31_ID = '120250951557410632'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
OUTPUT = WORK / 'final-live-readback.json'


def main() -> int:
    audit = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/audit/cpv-c31-from-zero-20260827.json').read_text())
    manifest = json.loads((WORK / 'manifest-sealed.json').read_text())
    bundle = audit['lanes'][ACCOUNT_ID]['bundles'][0]
    creative_ids = [str(value) for value in bundle['creative_ids']]
    token_common = load_common()
    token, token_field = token_common.get_token_from_1password(item_name=TOKEN_ITEM)
    requests = [
        {'name': 'account', 'path': f'act_{ACCOUNT_ID}', 'params': {'fields': 'id,name,account_status,disable_reason,currency,timezone_name'}},
        {'name': 'campaign', 'path': CAMPAIGN_ID, 'params': {'fields': 'id,name,status,configured_status,effective_status,objective,buying_type,daily_budget,bid_strategy,special_ad_categories,special_ad_category_country,start_time,created_time,updated_time'}},
        {'name': 'adsets', 'path': f'{CAMPAIGN_ID}/adsets', 'params': {'fields': 'id,name,status,configured_status,effective_status,campaign_id,start_time,billing_event,optimization_goal,bid_amount,bid_constraints,targeting,promoted_object,attribution_spec,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities,issues_info,created_time,updated_time', 'limit': 20}},
        {'name': 'ads', 'path': f'{CAMPAIGN_ID}/ads', 'params': {'fields': 'id,name,status,configured_status,effective_status,source_ad_id,adset_id,issues_info,creative{id,name,effective_object_story_id}', 'limit': 20}},
        {'name': 'campaigns_account', 'path': f'act_{ACCOUNT_ID}/campaigns', 'params': {'fields': 'id,name,status,configured_status,effective_status,daily_budget', 'limit': 500}},
        {'name': 'old_c31', 'path': OLD_C31_ID, 'params': {'fields': 'id,name,status,configured_status,effective_status,daily_budget,start_time'}},
        {'name': 'asset_ads_account', 'path': f'act_{ACCOUNT_ID}/ads', 'params': {'fields': 'id,name,status,configured_status,effective_status,source_ad_id,campaign{id,name,status,configured_status},creative{id,name}', 'filtering': [{'field': 'name', 'operator': 'CONTAIN', 'value': 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA'}], 'limit': 200}},
        {'name': 'adcreatives_account', 'path': f'act_{ACCOUNT_ID}/adcreatives', 'params': {'fields': 'id,name,status', 'limit': 1000}},
    ]
    for index, creative_id in enumerate(creative_ids, start=1):
        requests.append({'name': f'creative_{index}', 'path': creative_id, 'params': {'fields': 'id,name,object_story_spec,asset_feed_spec,degrees_of_freedom_spec,effective_object_story_id,status'}})

    outer_status, rows, _ = token_common.graph_batch_get(token, requests)
    if outer_status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'final readback outer batch failed http={outer_status}')
    errors = [row for row in rows if int(row.get('code') or 0) != 200]
    if errors:
        safe = [{'name': row.get('name'), 'code': row.get('code'), 'error': token_common.safe_meta_error(row.get('body') or {})} for row in errors]
        raise RuntimeError(json.dumps(safe, ensure_ascii=False))
    body = {row['name']: row['body'] for row in rows}
    active = [row for row in (body['campaigns_account'].get('data') or []) if str(row.get('configured_status') or row.get('status') or '').upper() == 'ACTIVE']
    active_budget_minor = sum(int(row.get('daily_budget') or 0) for row in active)
    expected_creative_names = {ad['creative_payload']['name'] for ad in manifest['campaigns'][0]['ads']}
    account_creatives = [row for row in (body['adcreatives_account'].get('data') or []) if str(row.get('name') or '') in expected_creative_names]
    account_creatives = list({str(row.get('id')): row for row in account_creatives}.values())
    bound_ids = set(creative_ids)
    orphan_candidates = [row for row in account_creatives if str(row.get('id') or '') not in bound_ids]
    output = {
        'status': 'FINAL_LIVE_READBACK_COLLECTED',
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'request_id': manifest['request_id'],
        'execution_mode': manifest['execution_mode'],
        'account': body['account'],
        'campaign': body['campaign'],
        'adsets': body['adsets'].get('data') or [],
        'ads': body['ads'].get('data') or [],
        'creatives': [body[f'creative_{index}'] for index in range(1, len(creative_ids) + 1)],
        'old_c31': body['old_c31'],
        'asset_ads_account': body['asset_ads_account'].get('data') or [],
        'c31_creatives_account': account_creatives,
        'adcreatives_page_has_more': bool((body['adcreatives_account'].get('paging') or {}).get('next')),
        'orphan_creative_candidates': orphan_candidates,
        'active_campaign_count_after': len(active),
        'active_budget_minor_after': active_budget_minor,
        'active_budget_usd_after': active_budget_minor / 100,
        'logical_calls': len(requests),
        'outer_calls': 1,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'status': output['status'],
        'campaign_status': output['campaign'].get('configured_status'),
        'adsets': len(output['adsets']),
        'ads': len(output['ads']),
        'creatives': len(output['creatives']),
        'asset_ads_account': len(output['asset_ads_account']),
        'orphan_creative_candidates': len(output['orphan_creative_candidates']),
        'active_budget_usd_after': output['active_budget_usd_after'],
        'logical_calls': output['logical_calls'],
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
