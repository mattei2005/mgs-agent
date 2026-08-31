from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
COMMON = BASE / 'scripts/ares-meta-common.py'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Carla Nunes - eggbev-us-cc-en-01 - G006'
OUT = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-recovery-readback-before.json'
CAMPAIGNS = ['120249822420250629', '120249822420240629']
ADSETS = ['120249822420750629', '120249822420710629']

spec = importlib.util.spec_from_file_location('ares_meta_common_recovery_readback', COMMON)
if spec is None or spec.loader is None:
    raise SystemExit('common helper unavailable')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
token, _ = common.get_token_from_1password(item_name=TOKEN_ITEM)

def get(path: str, params: dict) -> dict:
    status, body, _ = common.graph_get(path, token, params)
    if status != 200:
        raise SystemExit(f'Graph GET failed path={path} http={status}')
    return body

campaigns = [get(value, {'fields': 'id,name,status,effective_status,configured_status,daily_budget,start_time,created_time,updated_time'}) for value in CAMPAIGNS]
adsets = [get(value, {'fields': 'id,name,campaign_id,status,effective_status,configured_status,start_time,destination_type,targeting,promoted_object,created_time,updated_time'}) for value in ADSETS]
ads = []
for campaign_id in CAMPAIGNS:
    body = get(campaign_id + '/ads', {'fields': 'id,name,status,effective_status,configured_status,adset_id,source_ad_id,issues_info,creative{id,name}', 'limit': 100})
    ads.extend(body.get('data') or [])
result = {
    'schema_version': 1,
    'request_id': 'eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01',
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'campaigns': campaigns,
    'adsets': adsets,
    'ads': ads,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({
    'status': 'RECOVERY_READBACK_OK',
    'campaigns': [{'id': row['id'], 'name': row['name'], 'status': row.get('status'), 'effective_status': row.get('effective_status'), 'budget_minor': row.get('daily_budget'), 'start_time': row.get('start_time')} for row in campaigns],
    'adsets': [{'id': row['id'], 'campaign_id': row.get('campaign_id'), 'name': row.get('name'), 'status': row.get('status'), 'effective_status': row.get('effective_status'), 'destination_type': row.get('destination_type'), 'page_id': (row.get('promoted_object') or {}).get('page_id')} for row in adsets],
    'ads_found': len(ads),
}, ensure_ascii=False, indent=2))
