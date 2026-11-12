"""Read-only effective schedule receipt for a partially created explicit request.

No writer, resealing, NOW backdating, QA grant or tolerance. A maintenance-issued
exact-request grant is required in addition to live policy/authority and evidence.
"""
from __future__ import annotations
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .prevalidation import verify_prevalidation

BASE = Path('/root/mgs-agent')
KIND = 'SHEIN_EXPIRED_EXPLICIT_PARTIAL_V1'
POLICY_FILE = 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json'
GRANTS_FILE = 'data/ares/meta-ads/policies/shein-elapsed-continuations.json'
RECOVERABLE = {'POSTPROCESS_PENDING', 'GLOBAL_QA_COMPLETE', 'ACTIVATION_PENDING', 'ACTIVATION_DEFERRED'}
_AUTH_CACHE = {}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def instant(value):
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        raise ValueError('elapsed continuation requires timezone')
    return dt.astimezone(timezone.utc)


def message_projection(value):
    return {**{k: value.get(k) for k in ['id', 'channel_id', 'content', 'timestamp', 'edited_timestamp']},
            'author': {k: (value.get('author') or {}).get(k) for k in ['id', 'bot']}}


def require_policy(policy, requested):
    required = {'enabled': True, 'approved_by': '344196393512075265',
        'scope': 'explicit_start_same_account_day_only', 'when_elapsed': 'IMMEDIATE_AFTER_QA',
        'account_timezone': 'verified_ad_account_timezone', 'preserve_future_schedule': True,
        'preserve_explicit_paused': True, 'preserve_original_requested_time_in_audit': True,
        'implicit_next_day_rollover': False,
        'already_created_objects': 'readback-first continuation of same request and IDs, never a new copy or silent manifest rewrite'}
    if any(policy.get(k) != v for k, v in required.items()):
        raise ValueError('expired explicit continuation policy unavailable')
    mid = str(policy.get('source_message_id') or '')
    if not re.fullmatch(r'[0-9]{17,20}', mid):
        raise ValueError('policy message missing')
    effective = datetime.fromtimestamp(((int(mid) >> 22) + 1420070400000) / 1000, timezone.utc)
    if effective > requested:
        raise ValueError('future policy cannot authorize historical objects')


def binding(state, checkpoint, original, policy, profile, *, now):
    """Pure exact binding; no live calls, no changes to any input."""
    request = state['request']; rid = request['request_id']; aid = request['account']
    start = instant(request['start_time']); current = instant(now)
    require_policy(policy, start)
    if (state.get('phase') not in RECOVERABLE or state.get('summary')
            or request.get('status') != 'ACTIVE' or request.get('mode') != 'pure_clone'
            or request.get('start_now') or request.get('start_next_midnight')
            or state.get('resolved_request') != request):
        raise ValueError('not an explicit unmodified recoverable partial request')
    if (profile.get('account_id') != aid or state['account'].get('id') != 'act_' + aid
            or not profile.get('timezone') or profile['timezone'] != state['account'].get('timezone_name')
            or profile.get('channel_id') != request.get('source_channel_id')):
        raise ValueError('verified account/profile/timezone mismatch')
    zone = ZoneInfo(profile['timezone'])
    if not start <= current or start.astimezone(zone).date() != current.astimezone(zone).date():
        raise ValueError('explicit continuation outside original account day')
    creation, target = state['manifest'], state['target_manifest']
    for manifest, status in [(creation, 'PAUSED'), (target, 'ACTIVE')]:
        if (manifest.get('operation') != 'SHEIN-US-DIRECT' or manifest.get('request_id') != rid
                or not verify_prevalidation(manifest)
                or len(manifest['campaigns']) != request['quantity']):
            raise ValueError('sealed manifest identity/quantity mismatch')
        for c in manifest['campaigns']:
            if (c['account_id'] != aid or c['status'] != status
                    or c.get('start_intent') == 'IMMEDIATE' or instant(c['start_time']) != start):
                raise ValueError('sealed explicit schedule mismatch')
    from .activation import normalize
    if normalize(creation) != normalize(target):
        raise ValueError('manifests differ beyond staging status')
    clock = instant(state['execution_started_at']); prepared = instant(state['prepared_at'])
    if not clock <= prepared <= start <= current:
        raise ValueError('original E2E clock/preparation invalid')
    if (checkpoint.get('status') != 'COMPLETE' or checkpoint.get('account_id') != aid
            or original.get('request_id') != rid or original.get('account_id') != aid
            or original.get('engine_status') != 'COMPLETE' or original.get('phase') != 'POSTPROCESS_PENDING'):
        raise ValueError('first readback/core identity not complete')
    first_at = instant(original['readback_at'])
    if not start <= first_at <= current:
        raise ValueError('first live receipt time invalid')
    specs = creation['campaigns']; targets = target['campaigns']
    originals = original['campaigns']
    if len(originals) != len(specs):
        raise ValueError('first live readback missing trees')
    slots = []; all_c = []; all_s = []; all_a = []
    for bundle in checkpoint['bundles']:
        if bundle.get('status') != 'COMPLETE' or bundle.get('stage') not in {'readback_complete', 'readback_complete_recovered'}:
            raise ValueError('incomplete native bundle')
        rows = {r['name']: r['body'] for r in bundle['readback_results'] if r.get('code') == 200}
        n = len(bundle['campaign_ids'])
        if len(bundle['adset_ids']) != n or len(bundle['idempotency_keys']) != n:
            raise ValueError('native bundle cardinality')
        bundle_ads = []
        for i, cid in enumerate(bundle['campaign_ids'], 1):
            pos = len(slots); spec = specs[pos]; row = originals[pos]
            key = bundle['idempotency_keys'][i-1]; sid = bundle['adset_ids'][i-1]
            campaign = rows['readback_campaign_' + str(i)]
            sets_edge = rows['readback_adsets_' + str(i)]
            ads_edge = rows['readback_ads_' + str(i)]
            sets = sets_edge['data']; ads = ads_edge['data']
            if (sets_edge.get('paging', {}).get('next') or ads_edge.get('paging', {}).get('next')
                    or len(sets) != 1 or len(ads) != len(spec['ads'])
                    or spec['idempotency_key'] != key or targets[pos]['idempotency_key'] != key
                    or str(campaign['id']) != cid or campaign['account_id'] != aid
                    or sets[0]['id'] != sid or row['campaign_id'] != cid or row['account_id'] != aid
                    or [s['id'] for s in row['adsets']] != [sid]
                    or {a['id'] for a in row['ads']} != {a['id'] for a in ads}
                    or len(row['ads']) != len(ads)):
                raise ValueError('native/readback/manifest tree IDs mismatch')
            observed = instant(row['start_time'])
            if any(instant(x['start_time']) != observed for x in [campaign, sets[0], row['adsets'][0]]):
                raise ValueError('native versus first readback schedule mismatch')
            if any(x.get('status') != 'PAUSED' for x in [campaign, sets[0], *ads, row, *row['adsets'], *row['ads']]):
                raise ValueError('first proof must preserve PAUSED staging')
            if (str(row['budget_minor']) != str(spec['campaign_updates']['daily_budget'])
                    or row['bid_strategy'] != spec['campaign_updates']['bid_strategy']
                    or str(row['adsets'][0]['bid_amount']) != str(state['source']['adset']['bid_amount'])):
                raise ValueError('first proof commercial mismatch')
            ids = [a['id'] for a in ads]
            if any(a.get('adset_id') != sid for a in ads):
                raise ValueError('native ad hierarchy mismatch')
            if {a.get('source_ad_id') for a in ads} != {a['source_ad_id'] for a in spec['ads']}:
                raise ValueError('native ad lineage mismatch')
            window = bundle['timings']['adset_copy']
            w0, w1 = instant(window['started_at']), instant(window['finished_at'])
            if not prepared <= w0 <= w1 <= first_at:
                raise ValueError('copy window chronology mismatch')
            if observed != start and not (start < observed and w0 <= observed <= w1
                    and observed.astimezone(zone).date() == start.astimezone(zone).date()):
                raise ValueError('native second outside exact same-day copy window')
            slots.append({'idempotency_key': key, 'campaign_id': cid, 'adset_id': sid,
                          'ad_ids': ids, 'expected_start_time': spec['start_time'],
                          'observed_start_time': row['start_time'], 'copy_window': window,
                          'classification': 'EXACT_ORIGINAL' if observed == start else 'NATIVE_ELAPSED_COPY'})
            all_c.append(cid); all_s.append(sid); all_a.extend(ids); bundle_ads.extend(ids)
        if set(bundle_ads) != set(bundle['ad_ids']) or len(bundle_ads) != len(bundle['ad_ids']):
            raise ValueError('bundle ad identity mismatch')
    if (len(slots) != request['quantity'] or checkpoint['campaign_ids'] != all_c
            or any(len(v) != len(set(v)) for v in [all_c, all_s, all_a])
            or state['engine_result']['campaign_ids'] != all_c):
        raise ValueError('complete request ID coverage mismatch')
    if any(original['counts'].get(k) != v for k, v in {'campaigns': len(all_c), 'adsets': len(all_s), 'ads': len(all_a)}.items()):
        raise ValueError('first proof count mismatch')
    return {'kind': KIND, 'request_id': rid, 'account_id': aid,
            'request_digest': digest(request), 'resolved_request_digest': digest(state['resolved_request']),
            'creation_digest': digest(creation), 'target_digest': digest(target),
            'checkpoint_digest': digest(checkpoint), 'first_readback_digest': digest(original),
            'policy_digest': digest(policy), 'profile_digest': digest(profile),
            'execution_started_at': state['execution_started_at'], 'prepared_at': state['prepared_at'],
            'timezone': profile['timezone'], 'slots': slots}


def live_authority(request, profile, operation, policy, *, get=None):
    from .shein_channel_authority import _get, verify
    get = get or _get
    cp = operation.get('channel_authorization_policy') or {}
    if (cp.get('enabled') is not True or cp.get('approved_by') != '344196393512075265'
            or profile['channel_id'] not in cp.get('channel_ids', [])):
        raise ValueError('live channel policy unavailable')
    proof = verify(request, profile, force=True)
    if proof.get('verified') is not True:
        raise ValueError('live requester authority unavailable')
    source = message_projection(get('/channels/' + request['source_thread_id'] + '/messages/' + request['source_message_id']))
    policy_message = message_projection(get('/channels/' + policy['source_thread_id'] + '/messages/' + policy['source_message_id']))
    for msg, mid, channel, actor in [(source, request['source_message_id'], request['source_thread_id'], request['authorized_by']),
                                    (policy_message, policy['source_message_id'], policy['source_thread_id'], policy['approved_by'])]:
        if (msg['id'] != mid or msg['channel_id'] != channel or msg['author']['id'] != actor
                or msg['author'].get('bot') or not msg['content'] or msg['edited_timestamp']):
            raise ValueError('exact unedited human authority evidence unavailable')
    if instant(source['timestamp']) > instant(request['start_time']):
        raise ValueError('source chronology invalid')
    return {'request_message': source, 'policy_message': policy_message, 'permission': proof}


def paths(base, rid, aid):
    return (base / 'data/ares/meta-ads/state/shein-campaigns/single-clone' / rid / 'state.json',
            base / 'data/ares/meta-ads/engine-v3/state/checkpoints' / (rid + '-' + aid + '.json'),
            base / 'data/ares/meta-ads/audit/shein/campaigns/intake' / rid / 'continuation-live-readback.json',
            base / 'data/ares/meta-ads/state/shein-campaigns/elapsed-continuations' / (rid + '.json'))


def load(base, rid, aid):
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}', rid)
            or not re.fullmatch(r'[0-9]+', aid)):
        raise ValueError('invalid continuation identity')
    sp, cp, lp, rp = paths(base, rid, aid)
    state, checkpoint, original = [json.loads(p.read_text()) for p in [sp, cp, lp]]
    operation = json.loads((base / POLICY_FILE).read_text())
    policy = operation['request_defaults']['expired_explicit_start_policy']
    profile = json.loads((base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles'][aid]
    from .shein_manual_takeover import deny_replay
    deny_replay(base, rid)
    return state, checkpoint, original, operation, policy, profile, rp


def validate_receipt(receipt, state, checkpoint, original, policy, profile, *, now, authority):
    bound = binding(state, checkpoint, original, policy, profile, now=now)
    if receipt.get('binding') != bound or receipt.get('kind') != KIND:
        raise ValueError('immutable effective schedule receipt drift')
    if receipt.get('authority') != authority:
        raise ValueError('live authority/source evidence drift')
    if (instant(state['execution_started_at']) != instant(authority['request_message']['timestamp'])
            or instant(authority['policy_message']['timestamp']) > instant(state['request']['start_time'])
            or not instant(original['readback_at']) <= instant(receipt['issued_at']) <= instant(now)
            or instant(receipt['issued_at']).astimezone(ZoneInfo(profile['timezone'])).date()
               != instant(state['request']['start_time']).astimezone(ZoneInfo(profile['timezone'])).date()):
        raise ValueError('original clock or effective authority chronology drift')
    return bound


def proof(expected, observed, *, request_id, account_id, campaign_id, idempotency_key, base=None, now=None):
    """No file writes and no Meta/Drive calls. Missing/invalid proof fails closed."""
    base = Path(base or BASE); now = now or datetime.now(timezone.utc)
    try:
        grants = json.loads((base / GRANTS_FILE).read_text())
        grant = grants['grants'][request_id]
        if (grants.get('kind') != KIND or grant['account_id'] != account_id
                or grant.get('authority_message_id') != '1558142161659105342'):
            return None
        state, checkpoint, original, operation, policy, profile, rp = load(base, request_id, account_id)
        receipt = json.loads(rp.read_text())
        if digest(receipt) != grant['receipt_digest']:
            return None
        # Cache only live Discord GET/permissions, never state, seals, clock or policy.
        cache_key = (str(base), request_id, digest(operation), digest(profile), digest(receipt))
        cached = _AUTH_CACHE.get(cache_key)
        if cached and 0 <= time.monotonic() - cached[0] < 10:
            authority = cached[1]
        else:
            authority = live_authority(state['request'], profile, operation, policy)
            _AUTH_CACHE[cache_key] = (time.monotonic(), authority)
        bound = validate_receipt(receipt, state, checkpoint, original, policy, profile, now=now, authority=authority)
        slots = [s for s in bound['slots'] if s['campaign_id'] == campaign_id and s['idempotency_key'] == idempotency_key]
        if len(slots) != 1 or instant(expected) != instant(slots[0]['expected_start_time']) or instant(observed) != instant(slots[0]['observed_start_time']):
            return None
        return {'verified': True, 'kind': KIND, 'receipt_digest': digest(receipt),
                'request_id': request_id, 'account_id': account_id, **slots[0],
                'schedule_writes': 0, 'manifest_mutations': 0, 'qa_certified': False}
    except (OSError, KeyError, ValueError, TypeError, IndexError, OverflowError):
        return None
