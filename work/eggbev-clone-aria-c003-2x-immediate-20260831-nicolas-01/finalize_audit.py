from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
REQUEST_ID = 'eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01'
CHECKPOINT = BASE / f'data/ares/meta-ads/engine-v3/state/checkpoints/{REQUEST_ID}-1034081997659047.json'
ENGINE_AUDIT = BASE / f'data/ares/meta-ads/engine-v3/audit/{REQUEST_ID}.json'
FINAL = BASE / f'data/ares/meta-ads/audit/eggbev/clone/{REQUEST_ID}-final-direct-readback.json'
OUT = BASE / f'data/ares/meta-ads/audit/eggbev/clone/{REQUEST_ID}-recovery-summary.json'

checkpoint = json.loads(CHECKPOINT.read_text())
engine_audit = json.loads(ENGINE_AUDIT.read_text())
final = json.loads(FINAL.read_text())
if checkpoint.get('status') != 'COMPLETE':
    raise SystemExit('checkpoint is not COMPLETE')
if not final.get('all_verified'):
    raise SystemExit('final direct readback is not verified')
bundle = (checkpoint.get('bundles') or [None])[0]
if not bundle or bundle.get('status') != 'COMPLETE':
    raise SystemExit('bundle is not COMPLETE')
result = {
    'schema_version': 1,
    'request_id': REQUEST_ID,
    'completed_at_utc': datetime.now(timezone.utc).isoformat(),
    'authority': {
        'requested_and_finally_approved_by': 'Nicolas Holanda',
        'standing_immediate_start_authority_granted_by': 'Rodolfo Mattei',
        'scope': 'two pure clones at USD45/day, immediate, no recurring schedule',
    },
    'initial_effect': {
        'campaign_ids': bundle.get('campaign_ids'),
        'adset_ids': bundle.get('adset_ids'),
        'ads': 0,
        'error_code': 100,
        'error_subcode': 1815675,
        'cause': 'normalized Graph creative readback omitted canonical asset_feed_spec.call_to_actions for Messenger',
    },
    'recovery': {
        'same_request': True,
        'blind_replay_blocked': True,
        'campaign_shells_replayed': 0,
        'adset_shells_replayed': 0,
        'missing_ads_created': 6,
        'ad_ids': bundle.get('ad_ids'),
        'payload_correction': 'preserved live video/title/label/Page/UTM/JSON payload, removed output-only fields and restored canonical MESSENGER call_to_actions',
        'quota_readback_error_subcode': 2446079,
        'final_recovery_mode': (bundle.get('recovery') or {}).get('mode'),
    },
    'engine': {
        'status': engine_audit.get('status'),
        'manifest_digest': engine_audit.get('manifest_digest'),
        'checkpoint_status': checkpoint.get('status'),
        'bundle_status': bundle.get('status'),
        'write_replay_blocked': True,
    },
    'direct_readback': {
        'source': str(FINAL.relative_to(BASE)),
        'all_verified': True,
        'campaigns': [
            {
                'campaign_id': row['campaign_id'],
                'campaign_name': row['campaign_name'],
                'start_time': row['start_time'],
                'active': row['active'],
                'budget_match': row['budget_match'],
                'adset_count': row['adset_count'],
                'ad_count': row['ad_count'],
                'insights_today': row['insights_today'],
            }
            for row in final['campaigns']
        ],
    },
    'skills_updated': [
        'eggbev-us-cc-en-bot-operations',
        'meta-campaign-engine-v3',
    ],
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'RECOVERY_SUMMARY_WRITTEN', 'request_id': REQUEST_ID, 'campaigns': len(result['direct_readback']['campaigns']), 'ads': len(bundle.get('ad_ids') or []), 'all_verified': True}))
