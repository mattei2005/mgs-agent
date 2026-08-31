from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
RUN = BASE / 'work/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01'
LIVE = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-preexecute-full.json'
SOURCE_MANIFEST = BASE / 'data/ares/meta-ads/audit/eggbev/creation/eggbev-12c-20260830-nicolas-pg_8348-00006-manifest.json'
OUT = RUN / 'recovery-draft.json'
REQUEST_ID = 'eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01'
SOURCE_NAME = '163 - Aria Kensington - ENG - US - (pg_8348) C003'

live = json.loads(LIVE.read_text())
source_manifest = json.loads(SOURCE_MANIFEST.read_text())
source_spec = next(row for row in source_manifest['campaigns'] if row['name'] == SOURCE_NAME)
old_by_name = {row['name']: row for row in source_spec['ads']}
live_ads = sorted(live['source_ads'], key=lambda row: str(row.get('name') or ''))
if len(live_ads) != 3 or set(old_by_name) != {row['name'] for row in live_ads}:
    raise SystemExit('source ad identity drift')

now_utc = datetime.now(timezone.utc)
start_et = (now_utc.astimezone(ZoneInfo('America/New_York')) + timedelta(minutes=8)).replace(second=0, microsecond=0)
corrected_ads = []
for live_ad in live_ads:
    name = live_ad['name']
    live_creative = live_ad.get('creative') or {}
    old_payload = old_by_name[name]['creative_payload']
    asset_feed = copy.deepcopy(live_creative.get('asset_feed_spec') or {})
    asset_feed.pop('reasons_to_shop', None)
    asset_feed.pop('shops_bundle', None)
    call_to_actions = copy.deepcopy((old_payload.get('asset_feed_spec') or {}).get('call_to_actions') or [])
    if not call_to_actions or any(((row.get('value') or {}).get('app_destination') != 'MESSENGER') for row in call_to_actions):
        raise SystemExit(f'canonical Messenger CTA missing for {name}')
    asset_feed['call_to_actions'] = call_to_actions
    payload = {
        'name': live_creative['name'],
        'object_story_spec': copy.deepcopy(live_creative['object_story_spec']),
        'asset_feed_spec': asset_feed,
        'degrees_of_freedom_spec': copy.deepcopy(old_payload.get('degrees_of_freedom_spec') or {}),
        'url_tags': live_creative['url_tags'],
    }
    if payload['url_tags'] != 'utm_campaign=pg_8348':
        raise SystemExit(f'UTM drift for {name}')
    corrected_ads.append({'name': name, 'source_ad_id': str(live_ad['id']), 'creative_payload': payload})

campaigns = []
for duplicate_number in (1, 2):
    campaigns.append({
        'idempotency_key': f'{REQUEST_ID}-dup{duplicate_number:02d}',
        'app_key': 'mgs-meta-app-current',
        'account_id': '1034081997659047',
        'mode': 'pure_clone',
        'source_campaign_id': str(live['source']['id']),
        'source_adset_id': str(live['source_adsets'][0]['id']),
        'name': f'{SOURCE_NAME} DUP{duplicate_number:02d}',
        'adset_name': str(live['source_adsets'][0]['name']),
        'start_time': start_et.isoformat(),
        'status': 'ACTIVE',
        'campaign_updates': {'daily_budget': '4500'},
        'ads': copy.deepcopy(corrected_ads),
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
        'scope': 'recover only the missing six Messenger ads in the two persisted clone shells',
    },
    'recovery': {
        'previous_stage': 'shells_normalized',
        'campaign_ids': ['120249822420250629', '120249822420240629'],
        'adset_ids': ['120249822420750629', '120249822420710629'],
        'previous_effect': 'two campaign shells and two adset shells; zero ads',
        'payload_correction': 'preserve live creative payload and restore canonical call_to_actions app_destination MESSENGER omitted by normalized Graph creative readback',
        'blind_replay_blocked': True,
    },
    'campaigns': campaigns,
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({
    'status': 'RECOVERY_DRAFT_READY',
    'request_id': REQUEST_ID,
    'start_time_et': start_et.isoformat(),
    'campaigns': [row['name'] for row in campaigns],
    'missing_ads_planned': sum(len(row['ads']) for row in campaigns),
    'campaign_shells_to_create': 0,
    'adset_shells_to_create': 0,
    'messenger_cta_restored': True,
}, ensure_ascii=False, indent=2))
