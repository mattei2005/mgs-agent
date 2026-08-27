from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common

ACCOUNT_ID = '1046241194533786'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
OUTPUT = ROOT / 'work/cpv-c31-from-zero-20260827/prewrite-live.json'
ASSETS = [
    ('asset_5966c098f64de6d561ab', 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_005'),
    ('asset_dea92e6bba464578897b', 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_006'),
    ('asset_303bb59d1847ccd47afe', 'CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_007'),
]


def main() -> int:
    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)
    requests = [
        {'name': 'account', 'path': f'act_{ACCOUNT_ID}', 'params': {'fields': 'id,name,account_status,disable_reason,currency,timezone_name'}},
        {'name': 'campaigns', 'path': f'act_{ACCOUNT_ID}/campaigns', 'params': {'fields': 'id,name,status,configured_status,effective_status,daily_budget,bid_strategy,start_time,created_time,updated_time', 'limit': 500}},
    ]
    for asset_id, stem in ASSETS:
        requests.append({
            'name': f'ad_asset_{asset_id}',
            'path': f'act_{ACCOUNT_ID}/ads',
            'params': {
                'fields': 'id,name,status,configured_status,effective_status,campaign{id,name,status,configured_status},creative{id,name}',
                'filtering': [{'field': 'name', 'operator': 'CONTAIN', 'value': stem}],
                'limit': 100,
            },
        })
    status, rows, _ = common.graph_batch_get(token, requests)
    if status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'prewrite outer batch failed http={status}')
    errors = [row for row in rows if int(row.get('code') or 0) != 200]
    if errors:
        raise RuntimeError(json.dumps([{'name': row.get('name'), 'code': row.get('code'), 'error': common.safe_meta_error(row.get('body') or {})} for row in errors], ensure_ascii=False))
    body = {row['name']: row['body'] for row in rows}
    account = body['account']
    campaigns = body['campaigns'].get('data') or []
    if account.get('account_status') != 1 or account.get('disable_reason') != 0 or account.get('currency') != 'USD' or account.get('timezone_name') != 'America/Sao_Paulo':
        raise RuntimeError('account health/currency/timezone prewrite mismatch')
    active = [row for row in campaigns if str(row.get('configured_status') or row.get('status') or '').upper() == 'ACTIVE']
    active_budget_minor = sum(int(row.get('daily_budget') or 0) for row in active)
    c31_pattern = re.compile(r'(^|\D)31(\D|$)|b01fb13c31', re.I)
    c31_nondeleted = [row for row in campaigns if c31_pattern.search(str(row.get('name') or '')) and str(row.get('configured_status') or row.get('status') or '').upper() not in {'DELETED', 'ARCHIVED'}]
    conflicts = {asset_id: body[f'ad_asset_{asset_id}'].get('data') or [] for asset_id, _ in ASSETS}
    if c31_nondeleted:
        raise RuntimeError(f'nondeleted C31 collision: {[row.get("id") for row in c31_nondeleted]}')
    if any(conflicts.values()):
        raise RuntimeError('asset conflict detected immediately before write')
    request_minor = 2500
    projected_minor = active_budget_minor + request_minor
    envelope_minor = max(50000, projected_minor)
    output = {
        'status': 'PREWRITE_LIVE_OK',
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'account': account,
        'active_campaign_count': len(active),
        'active_budget_minor_before': active_budget_minor,
        'active_budget_usd_before': active_budget_minor / 100,
        'request_budget_minor': request_minor,
        'request_budget_usd': request_minor / 100,
        'projected_budget_if_activated_usd': projected_minor / 100,
        'effective_envelope_usd': envelope_minor / 100,
        'remaining_within_envelope_usd': (envelope_minor - projected_minor) / 100,
        'c31_nondeleted': c31_nondeleted,
        'asset_conflicts': conflicts,
        'logical_calls': len(requests),
        'outer_calls': 1,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: output[key] for key in ('status','active_campaign_count','active_budget_usd_before','request_budget_usd','projected_budget_if_activated_usd','effective_envelope_usd','remaining_within_envelope_usd','logical_calls')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
