from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
RUN = BASE / 'work/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01'
LIVE = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-preexecute-full.json'
OUT = RUN / 'execute-draft.json'
REQUEST_ID = 'eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01'
SOURCE_NAME = '163 - Aria Kensington - ENG - US - (pg_8348) C003'

live = json.loads(LIVE.read_text())
if live.get('source_exact_count_non_deleted') != 1:
    raise SystemExit('source is not unique')
if live.get('target_collision_count_non_deleted') != 0:
    raise SystemExit('target collision detected')
if live.get('source', {}).get('status') != 'ACTIVE':
    raise SystemExit('source is not ACTIVE')
if live.get('source', {}).get('daily_budget') != '4500':
    raise SystemExit('source budget drifted')
adsets = live.get('source_adsets') or []
ads = live.get('source_ads') or []
if len(adsets) != 1 or len(ads) != 3:
    raise SystemExit('source hierarchy is not 1x1x3')
if any(ad.get('status') != 'ACTIVE' for ad in ads):
    raise SystemExit('all source ads must be ACTIVE at seal time')

now_utc = datetime.now(timezone.utc)
start_et = (now_utc.astimezone(ZoneInfo('America/New_York')) + timedelta(minutes=6)).replace(second=0, microsecond=0)
creative_keys = ('name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'url_tags')
source_ads = []
for ad in sorted(ads, key=lambda row: str(row.get('name') or '')):
    creative = ad.get('creative') or {}
    creative_payload = {key: copy.deepcopy(creative[key]) for key in creative_keys if key in creative}
    if not creative_payload.get('object_story_spec') or not creative_payload.get('asset_feed_spec'):
        raise SystemExit(f'incomplete creative payload for ad {ad.get("id")}')
    if creative_payload.get('url_tags') != 'utm_campaign=pg_8348':
        raise SystemExit(f'url_tags drift for ad {ad.get("id")}')
    source_ads.append({
        'name': ad['name'],
        'source_ad_id': str(ad['id']),
        'creative_payload': creative_payload,
    })

campaigns = []
for duplicate_number in (1, 2):
    campaigns.append({
        'idempotency_key': f'{REQUEST_ID}-dup{duplicate_number:02d}',
        'app_key': 'mgs-meta-app-current',
        'account_id': '1034081997659047',
        'mode': 'pure_clone',
        'source_campaign_id': str(live['source']['id']),
        'source_adset_id': str(adsets[0]['id']),
        'name': f'{SOURCE_NAME} DUP{duplicate_number:02d}',
        'adset_name': str(adsets[0]['name']),
        'start_time': start_et.isoformat(),
        'status': 'ACTIVE',
        'campaign_updates': {'daily_budget': '4500'},
        'ads': copy.deepcopy(source_ads),
    })

payload = {
    'schema_version': 3,
    'request_id': REQUEST_ID,
    'operation': 'Eggbev-US-CC-EN-BOT',
    'graph_version': 'v26.0',
    'created_at': now_utc.isoformat(),
    'prevalidated': False,
    'authorization': {
        'requested_and_finally_approved_by': 'Nicolas Holanda',
        'standing_immediate_start_authority_granted_by': 'Rodolfo Mattei',
        'scope': 'two immediate pure clones at USD45/day without recurring schedule',
    },
    'preflight_source': str(LIVE.relative_to(BASE)),
    'campaigns': campaigns,
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({
    'status': 'EXECUTE_DRAFT_READY',
    'request_id': REQUEST_ID,
    'start_time_et': start_et.isoformat(),
    'campaigns': [campaign['name'] for campaign in campaigns],
    'budget_minor_each': '4500',
    'source_ads': [ad['source_ad_id'] for ad in source_ads],
}, ensure_ascii=False, indent=2))
