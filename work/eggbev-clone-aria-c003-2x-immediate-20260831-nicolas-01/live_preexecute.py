from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
COMMON = BASE / 'scripts/ares-meta-common.py'
OUT = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-preexecute-full.json'
ACCOUNT_ID = '1034081997659047'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Carla Nunes - eggbev-us-cc-en-01 - G006'
SOURCE_ID = '120249812034090629'
SOURCE_NAME = '163 - Aria Kensington - ENG - US - (pg_8348) C003'
TARGET_NAMES = [f'{SOURCE_NAME} DUP01', f'{SOURCE_NAME} DUP02']

spec = importlib.util.spec_from_file_location('ares_meta_common_preexecute', COMMON)
if spec is None or spec.loader is None:
    raise SystemExit('common helper unavailable')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)

def graph_get(path: str, params: dict) -> dict:
    status, body, _ = common.graph_get(path, token, params)
    if status != 200:
        raise SystemExit(f'Graph GET failed path={path} http={status}')
    return body

def all_rows(path: str, fields: str, limit: int = 500) -> list[dict]:
    rows: list[dict] = []
    after = None
    seen = set()
    while True:
        params = {'fields': fields, 'limit': limit}
        if after:
            params['after'] = after
        body = graph_get(path, params)
        rows.extend(body.get('data') or [])
        paging = body.get('paging') or {}
        next_url = paging.get('next')
        new_after = (paging.get('cursors') or {}).get('after')
        if not next_url or not new_after or new_after in seen:
            break
        seen.add(new_after)
        after = new_after
    return rows

campaigns = all_rows(
    f'act_{ACCOUNT_ID}/campaigns',
    'id,name,status,effective_status,daily_budget,lifetime_budget,start_time,created_time,updated_time',
)
exact_source = [row for row in campaigns if row.get('name') == SOURCE_NAME and row.get('status') != 'DELETED']
target_collisions = [row for row in campaigns if row.get('name') in TARGET_NAMES and row.get('status') != 'DELETED']
base_variants = [row for row in campaigns if str(row.get('name') or '').startswith(SOURCE_NAME)]
source = graph_get(SOURCE_ID, {'fields': 'id,name,status,effective_status,daily_budget,lifetime_budget,start_time,objective,buying_type,bid_strategy,special_ad_categories,special_ad_category_country,created_time,updated_time'})
adsets = all_rows(SOURCE_ID + '/adsets', 'id,name,status,effective_status,start_time,end_time,billing_event,optimization_goal,destination_type,is_dynamic_creative,attribution_spec,targeting,promoted_object,regional_regulated_categories,regional_regulation_identities,created_time,updated_time', 100)
ads = all_rows(SOURCE_ID + '/ads', 'id,name,status,effective_status,source_ad_id,issues_info,creative{id,name,effective_object_story_id,object_story_spec,asset_feed_spec,url_tags},created_time,updated_time', 100)
payload = {
    'schema_version': 1,
    'request_id': 'eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01',
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'account_id': ACCOUNT_ID,
    'campaign_count': len(campaigns),
    'source_exact_count_non_deleted': len(exact_source),
    'target_collision_count_non_deleted': len(target_collisions),
    'target_names': TARGET_NAMES,
    'source': source,
    'source_adsets': adsets,
    'source_ads': ads,
    'base_variants': base_variants,
    'target_collisions': target_collisions,
    'token_provenance': {'item': TOKEN_ITEM, 'field': token_field, 'length_only': len(token)},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({
    'status': 'LIVE_PREFLIGHT_OK',
    'campaign_count': len(campaigns),
    'source_exact_count_non_deleted': len(exact_source),
    'target_collision_count_non_deleted': len(target_collisions),
    'source_status': source.get('status'),
    'source_effective_status': source.get('effective_status'),
    'source_budget_minor': source.get('daily_budget'),
    'source_adsets': len(adsets),
    'source_ads': len(ads),
    'source_ad_statuses': sorted({str(row.get('status')) for row in ads}),
    'base_variant_names': [row.get('name') for row in base_variants],
}, ensure_ascii=False, indent=2))
