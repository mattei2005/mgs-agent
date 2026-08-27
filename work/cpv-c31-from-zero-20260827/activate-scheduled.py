from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common

CAMPAIGN_ID = '120250952825350632'
ADSET_ID = '120250952825540632'
ACCOUNT_ID = '1046241194533786'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
EXPECTED_START = '2026-08-28T00:30:00-0300'
EXPECTED_BUDGET_MINOR = 2500
EXPECTED_AD_IDS = {
    '120250952830620632',
    '120250952830530632',
    '120250952830630632',
}
OPERATION = ROOT / 'data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json'
PREACTIVATE = WORK / 'preactivate-live.json'
AUDIT = WORK / 'activation-audit.json'


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


def batch_snapshot(common, token: str) -> dict:
    requests = [
        {
            'name': 'campaign',
            'path': CAMPAIGN_ID,
            'params': {'fields': 'id,name,status,configured_status,effective_status,daily_budget,bid_strategy,start_time,updated_time'},
        },
        {
            'name': 'adsets',
            'path': f'{CAMPAIGN_ID}/adsets',
            'params': {'fields': 'id,name,status,configured_status,effective_status,start_time,issues_info', 'limit': 20},
        },
        {
            'name': 'ads',
            'path': f'{CAMPAIGN_ID}/ads',
            'params': {'fields': 'id,name,status,configured_status,effective_status,issues_info', 'limit': 20},
        },
        {
            'name': 'insights',
            'path': f'{CAMPAIGN_ID}/insights',
            'params': {'fields': 'spend,impressions', 'date_preset': 'maximum', 'level': 'campaign', 'limit': 20},
        },
        {
            'name': 'campaigns_account',
            'path': f'act_{ACCOUNT_ID}/campaigns',
            'params': {'fields': 'id,name,status,configured_status,effective_status,daily_budget', 'limit': 500},
        },
    ]
    outer_status, rows, _ = common.graph_batch_get(token, requests)
    if outer_status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'activation batch readback failed http={outer_status}')
    errors = [row for row in rows if int(row.get('code') or 0) != 200]
    if errors:
        safe = [
            {'name': row.get('name'), 'code': row.get('code'), 'error': common.safe_meta_error(row.get('body') or {})}
            for row in errors
        ]
        raise RuntimeError(json.dumps(safe, ensure_ascii=False))
    body = {row['name']: row['body'] for row in rows}
    campaign = body['campaign']
    adsets = body['adsets'].get('data') or []
    ads = body['ads'].get('data') or []
    insights = body['insights'].get('data') or []
    active = [
        row for row in (body['campaigns_account'].get('data') or [])
        if str(row.get('configured_status') or row.get('status') or '').upper() == 'ACTIVE'
    ]
    return {
        'campaign': campaign,
        'adsets': adsets,
        'ads': ads,
        'spend_usd': sum(float(row.get('spend') or 0) for row in insights),
        'impressions': sum(int(row.get('impressions') or 0) for row in insights),
        'active_campaign_count': len(active),
        'active_budget_minor': sum(int(row.get('daily_budget') or 0) for row in active),
        'logical_calls': len(requests),
        'outer_calls': 1,
    }


def validate_structure(snapshot: dict, *, expected_status: str) -> dict:
    campaign = snapshot['campaign']
    adsets = snapshot['adsets']
    ads = snapshot['ads']
    checks = {
        'campaign_exact': str(campaign.get('id') or '') == CAMPAIGN_ID,
        'campaign_name_date': '31 - 28-08 - ' in str(campaign.get('name') or ''),
        'campaign_status': str(campaign.get('configured_status') or campaign.get('status') or '').upper() == expected_status,
        'campaign_budget_usd25': int(campaign.get('daily_budget') or 0) == EXPECTED_BUDGET_MINOR,
        'campaign_maxvol': campaign.get('bid_strategy') == 'LOWEST_COST_WITHOUT_CAP',
        'campaign_start_exact': str(campaign.get('start_time') or '') == EXPECTED_START,
        'one_adset_exact': len(adsets) == 1 and str(adsets[0].get('id') or '') == ADSET_ID,
        'adset_active': len(adsets) == 1 and str(adsets[0].get('configured_status') or adsets[0].get('status') or '').upper() == 'ACTIVE',
        'adset_start_exact': len(adsets) == 1 and str(adsets[0].get('start_time') or '') == EXPECTED_START,
        'adset_issues_clear': len(adsets) == 1 and not adsets[0].get('issues_info'),
        'three_ads_exact': {str(row.get('id') or '') for row in ads} == EXPECTED_AD_IDS,
        'ads_active': len(ads) == 3 and all(str(row.get('configured_status') or row.get('status') or '').upper() == 'ACTIVE' for row in ads),
        'ads_issues_clear': len(ads) == 3 and all(not row.get('issues_info') for row in ads),
        'zero_spend': float(snapshot['spend_usd']) == 0.0,
        'zero_impressions': int(snapshot['impressions']) == 0,
    }
    return checks


def main() -> int:
    now_sp = datetime.now(ZoneInfo('America/Sao_Paulo'))
    if now_sp >= datetime.fromisoformat('2026-08-28T00:30:00-03:00'):
        raise RuntimeError('activation correction is no longer before scheduled start')
    preactivate = json.loads(PREACTIVATE.read_text())
    operation = json.loads(OPERATION.read_text())
    allowed = (((operation.get('management_scope') or {}).get('autonomous_action_scope') or {}).get('allowed_campaigns') or {})
    if not isinstance(allowed, dict):
        raise RuntimeError('operation allowed_campaigns must be an object')
    if str((allowed.get('31') or {}).get('campaign_id') or '') != CAMPAIGN_ID:
        raise RuntimeError('operation allowlist does not point C31 to the replacement campaign')
    if str((allowed.get('31') or {}).get('cycle_start_date') or '') != '2026-08-28':
        raise RuntimeError('operation allowlist C31 cycle date mismatch')
    if int(preactivate.get('active_budget_minor_before') or 0) != 37234:
        raise RuntimeError('sealed preactivation budget baseline mismatch')

    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)
    before = batch_snapshot(common, token)
    before_checks = validate_structure(before, expected_status='PAUSED')
    if not all(before_checks.values()):
        raise RuntimeError(json.dumps({'before_checks': before_checks, 'before': before}, ensure_ascii=False))
    if int(before['active_budget_minor']) != int(preactivate['active_budget_minor_before']):
        raise RuntimeError('active account budget drifted after the sealed preactivation readback')

    audit = {
        'schema_version': 1,
        'request_id': 'cpv-c31-from-zero-20260827',
        'action': 'activate_future_scheduled_campaign',
        'authorized_by': 'Rodolfo Mattei',
        'authorization_source': 'discord:thread:1542573475104034936',
        'status': 'IN_FLIGHT',
        'started_at_sp': now_sp.isoformat(),
        'campaign_id': CAMPAIGN_ID,
        'target_configured_status': 'ACTIVE',
        'target_start_time_sp': '2026-08-28T00:30:00-03:00',
        'before': before,
        'before_checks': before_checks,
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'meta_write_attempts': 0,
    }
    atomic_json(AUDIT, audit)

    audit['meta_write_attempts'] = 1
    atomic_json(AUDIT, audit)
    write_http, write_payload, _ = common.graph_post_once(CAMPAIGN_ID, token, {'status': 'ACTIVE'})
    audit['write_http'] = write_http
    audit['write_response'] = {'success': bool((write_payload or {}).get('success'))} if isinstance(write_payload, dict) else {}
    atomic_json(AUDIT, audit)

    time.sleep(2)
    after = batch_snapshot(common, token)
    after_checks = validate_structure(after, expected_status='ACTIVE')
    after_checks['active_budget_exact'] = int(after['active_budget_minor']) == int(before['active_budget_minor']) + EXPECTED_BUDGET_MINOR
    audit['after'] = after
    audit['after_checks'] = after_checks
    audit['effective_envelope_minor'] = max(50000, int(after['active_budget_minor']))
    audit['remaining_within_envelope_minor'] = max(0, audit['effective_envelope_minor'] - int(after['active_budget_minor']))
    audit['finished_at_sp'] = datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
    audit['status'] = 'COMPLETE_VERIFIED' if all(after_checks.values()) else 'READBACK_MISMATCH'
    atomic_json(AUDIT, audit)
    if not all(after_checks.values()):
        raise RuntimeError(json.dumps({'write_http': write_http, 'write_error': common.safe_meta_error(write_payload if isinstance(write_payload, dict) else {}), 'after_checks': after_checks}, ensure_ascii=False))
    print(json.dumps({
        'status': 'C31_ACTIVE_SCHEDULED_VERIFIED',
        'campaign_id': CAMPAIGN_ID,
        'configured_status': after['campaign'].get('configured_status'),
        'effective_status': after['campaign'].get('effective_status'),
        'start_time': after['campaign'].get('start_time'),
        'adset_start_time': after['adsets'][0].get('start_time'),
        'ads': len(after['ads']),
        'spend_usd': after['spend_usd'],
        'active_budget_usd_after': int(after['active_budget_minor']) / 100,
        'effective_envelope_usd': audit['effective_envelope_minor'] / 100,
        'remaining_within_envelope_usd': audit['remaining_within_envelope_minor'] / 100,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
