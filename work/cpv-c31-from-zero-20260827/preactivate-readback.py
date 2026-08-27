from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common

CAMPAIGN_ID = '120250952825350632'
ACCOUNT_ID = '1046241194533786'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
EXPECTED_START = '2026-08-28T00:30:00-0300'
OUTPUT = WORK / 'preactivate-live.json'


def main() -> int:
    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)
    requests = [
        {
            'name': 'campaign',
            'path': CAMPAIGN_ID,
            'params': {
                'fields': 'id,name,status,configured_status,effective_status,daily_budget,bid_strategy,start_time,updated_time',
            },
        },
        {
            'name': 'adsets',
            'path': f'{CAMPAIGN_ID}/adsets',
            'params': {
                'fields': 'id,name,status,configured_status,effective_status,start_time,issues_info',
                'limit': 20,
            },
        },
        {
            'name': 'ads',
            'path': f'{CAMPAIGN_ID}/ads',
            'params': {
                'fields': 'id,name,status,configured_status,effective_status,issues_info,creative{id,name,effective_object_story_id}',
                'limit': 20,
            },
        },
        {
            'name': 'insights',
            'path': f'{CAMPAIGN_ID}/insights',
            'params': {
                'fields': 'spend,impressions',
                'date_preset': 'maximum',
                'level': 'campaign',
                'limit': 20,
            },
        },
        {
            'name': 'campaigns_account',
            'path': f'act_{ACCOUNT_ID}/campaigns',
            'params': {
                'fields': 'id,name,status,configured_status,effective_status,daily_budget',
                'limit': 500,
            },
        },
    ]
    outer_status, rows, _ = common.graph_batch_get(token, requests)
    if outer_status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'preactivate batch failed http={outer_status}')
    errors = [row for row in rows if int(row.get('code') or 0) != 200]
    if errors:
        safe = [
            {
                'name': row.get('name'),
                'code': row.get('code'),
                'error': common.safe_meta_error(row.get('body') or {}),
            }
            for row in errors
        ]
        raise RuntimeError(json.dumps(safe, ensure_ascii=False))
    body = {row['name']: row['body'] for row in rows}
    campaign = body['campaign']
    adsets = body['adsets'].get('data') or []
    ads = body['ads'].get('data') or []
    insights = body['insights'].get('data') or []
    spend = sum(float(row.get('spend') or 0) for row in insights)
    impressions = sum(int(row.get('impressions') or 0) for row in insights)
    active = [
        row
        for row in (body['campaigns_account'].get('data') or [])
        if str(row.get('configured_status') or row.get('status') or '').upper() == 'ACTIVE'
    ]
    active_budget_minor = sum(int(row.get('daily_budget') or 0) for row in active)
    now_sp = datetime.now(ZoneInfo('America/Sao_Paulo'))
    checks = {
        'before_start': now_sp.isoformat() < '2026-08-28T00:30:00-03:00',
        'campaign_id': str(campaign.get('id') or '') == CAMPAIGN_ID,
        'campaign_name_date': '31 - 28-08 - ' in str(campaign.get('name') or ''),
        'campaign_paused_before_correction': str(campaign.get('configured_status') or campaign.get('status') or '').upper() == 'PAUSED',
        'campaign_budget_usd25': str(campaign.get('daily_budget') or '') == '2500',
        'campaign_maxvol': campaign.get('bid_strategy') == 'LOWEST_COST_WITHOUT_CAP',
        'campaign_start_exact': str(campaign.get('start_time') or '') == EXPECTED_START,
        'one_adset': len(adsets) == 1,
        'adset_active': len(adsets) == 1 and str(adsets[0].get('configured_status') or adsets[0].get('status') or '').upper() == 'ACTIVE',
        'adset_start_exact': len(adsets) == 1 and str(adsets[0].get('start_time') or '') == EXPECTED_START,
        'adset_issues_clear': len(adsets) == 1 and not adsets[0].get('issues_info'),
        'three_ads': len(ads) == 3,
        'ads_active': len(ads) == 3 and all(str(row.get('configured_status') or row.get('status') or '').upper() == 'ACTIVE' for row in ads),
        'ads_issues_clear': len(ads) == 3 and all(not row.get('issues_info') for row in ads),
        'zero_spend': spend == 0.0,
        'zero_impressions': impressions == 0,
    }
    if not all(checks.values()):
        raise RuntimeError(json.dumps({'checks': checks, 'campaign': campaign, 'adsets': adsets, 'ads': ads, 'spend': spend, 'impressions': impressions}, ensure_ascii=False))
    output = {
        'status': 'C31_PREACTIVATE_VERIFIED',
        'collected_at_sp': now_sp.isoformat(),
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'campaign': campaign,
        'adsets': adsets,
        'ads': ads,
        'spend_usd': spend,
        'impressions': impressions,
        'active_campaign_count_before': len(active),
        'active_budget_minor_before': active_budget_minor,
        'active_budget_usd_before': active_budget_minor / 100,
        'projected_active_budget_usd_after': active_budget_minor / 100 + 25.0,
        'checks': checks,
        'logical_calls': len(requests),
        'outer_calls': 1,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'status': output['status'],
        'campaign_status': campaign.get('configured_status'),
        'campaign_start': campaign.get('start_time'),
        'adset_start': adsets[0].get('start_time'),
        'ads': len(ads),
        'spend_usd': spend,
        'active_budget_usd_before': output['active_budget_usd_before'],
        'projected_active_budget_usd_after': output['projected_active_budget_usd_after'],
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
