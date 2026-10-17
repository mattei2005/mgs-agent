"""Read-only, provenance-bound reconciliation of Meta NOW adset-copy time.

No generic tolerance, schedule writes, manifest mutation or SLA override.
Only an exact time recorded during the same completed native copy is accepted.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')


def _instant(value):
    result = datetime.fromisoformat(str(value))
    if result.tzinfo is None:
        raise ValueError('timezone required')
    return result.astimezone(timezone.utc)


def normalized_schedule_proof(state, checkpoint, *, request_id, account_id, campaign_id,
                              idempotency_key, expected, observed):
    """Pure validator; None means original exact schedule gate still fails."""
    try:
        request = state.get('request') or {}
        if request.get('request_id') != request_id or request.get('start_now') is not True:
            return None
        if str(checkpoint.get('account_id')) != str(account_id) or checkpoint.get('status') != 'COMPLETE':
            return None
        shells = [c for c in state['manifest']['campaigns'] if c.get('idempotency_key') == idempotency_key]
        targets = [c for c in state['target_manifest']['campaigns'] if c.get('idempotency_key') == idempotency_key]
        if len(shells) != 1 or len(targets) != 1:
            return None
        shell = shells[0]
        if (shell.get('start_intent') != 'IMMEDIATE' or str(shell.get('account_id')) != str(account_id)
                or _instant(shell['start_time']) != _instant(expected)
                or targets[0].get('start_intent') != 'IMMEDIATE'
                or _instant(targets[0]['start_time']) != _instant(expected)):
            return None
        bundles = [b for b in checkpoint['bundles'] if str(campaign_id) in b.get('campaign_ids', []) and b.get('status') == 'COMPLETE']
        if len(bundles) != 1:
            return None
        bundle = bundles[0]
        index = bundle['campaign_ids'].index(str(campaign_id))
        if bundle['idempotency_keys'][index] != idempotency_key:
            return None
        window = bundle['timings']['adset_copy']
        start, finish = _instant(window['started_at']), _instant(window['finished_at'])
        time = _instant(observed)
        if not (_instant(expected) < time and start.replace(microsecond=0) <= time <= finish and start <= finish):
            return None
        rows = {r['name']: r['body'] for r in bundle['readback_results'] if r.get('code') == 200}
        campaign = rows['readback_campaign_' + str(index + 1)]
        adsets = rows['readback_adsets_' + str(index + 1)]['data']
        if (str(campaign.get('id')) != str(campaign_id) or str(campaign.get('account_id')) != str(account_id)
                or _instant(campaign['start_time']) != time or len(adsets) != 1
                or str(adsets[0]['id']) not in bundle['adset_ids']
                or _instant(adsets[0]['start_time']) != time):
            return None
        return {'verified': True, 'request_id': request_id, 'campaign_id': str(campaign_id),
                'adset_id': str(adsets[0]['id']), 'expected_start_time': expected,
                'observed_start_time': observed, 'reason': 'META_NATIVE_NOW_COPY_WINDOW',
                'copy_window': window, 'schedule_writes': 0, 'manifest_mutations': 0}
    except (KeyError, ValueError, TypeError, IndexError):
        return None


def proven_now_copy_time(expected, observed, *, request_id, account_id, campaign_id, idempotency_key):
    """Load exact same-request provenance; fail closed if seals/evidence missing."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}', str(request_id)):
        return False
    if not all(re.fullmatch(r'[0-9]+', str(x)) for x in [account_id, campaign_id]):
        return False
    try:
        state_path = BASE/'data/ares/meta-ads/state/shein-campaigns/single-clone'/request_id/'state.json'
        checkpoint_path = BASE/'data/ares/meta-ads/engine-v3/state/checkpoints'/(request_id+'-'+account_id+'.json')
        state = json.loads(state_path.read_text())
        checkpoint = json.loads(checkpoint_path.read_text())
        from .prevalidation import verify_prevalidation
        if (state['manifest'].get('operation') != 'SHEIN-US-DIRECT'
                or state['manifest'].get('request_id') != request_id
                or state['target_manifest'].get('request_id') != request_id
                or not verify_prevalidation(state['manifest'])
                or not verify_prevalidation(state['target_manifest'])):
            return False
        proof = normalized_schedule_proof(state, checkpoint, request_id=request_id, account_id=account_id,
                                          campaign_id=campaign_id, idempotency_key=idempotency_key,
                                          expected=expected, observed=observed)
        if proof is None:
            return False
        # A separate receipt preserves normalization evidence, never rewriting seals.
        proof['creation_digest'] = hashlib.sha256(json.dumps(state['manifest'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        proof['target_digest'] = hashlib.sha256(json.dumps(state['target_manifest'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        from .activation import atomic
        receipt = state_path.parent/('schedule-normalization-'+campaign_id+'.json')
        atomic(receipt, proof)
        return True
    except (OSError, KeyError, ValueError, TypeError):
        return False
