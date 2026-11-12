"""Exact successor-scoped observation of externally managed commercial deltas.

Never approves or writes budgets/bids. Original manual takeover/replay fences,
QA, identity/media, reservations, locks and source disjointness remain intact.
An immutable receipt plus CAS-registered digest admits ONLY its exact successor.
"""
from __future__ import annotations
import copy
import fcntl
import hashlib
import json
import os
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

CLASSIFICATION = 'MANUAL_EXTERNAL_COMMERCIAL_OBSERVATION_V1'


def policy_path(base):
    return base / 'data/ares/meta-ads/policies/shein-manual-coordination-observations.json'


def receipt_path(base, request, historical_id):
    from . import shein_request_queue as q
    q.job_path(base, request['request_id']); q.job_path(base, historical_id)
    return q.root(base) / 'queue/manual-observations' / request['request_id'] / (historical_id + '.json')


def digest_request(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _commercial_projection(campaigns):
    from . import shein_manual_takeover as manual
    result = manual.scheduling_identity(campaigns)
    for campaign in result:
        budget = campaign.pop('daily_budget')
        if not isinstance(budget, str) or not budget.isdigit() or int(budget) <= 0:
            raise ValueError('manual observation invalid external budget')
        for adset in campaign['adsets']:
            bid = adset.pop('bid_amount')
            if type(bid) is not int or bid <= 0:
                raise ValueError('manual observation invalid external bid')
    return result


def commercial_deltas(before, current):
    """Only exact daily_budget/bid_amount changes; no strategy/time/media waiver."""
    if _commercial_projection(before) != _commercial_projection(current):
        raise ValueError('manual observation identity/configuration/media drift')
    changes = []
    for old, live in zip(before, current):
        if old['daily_budget'] != live['daily_budget']:
            changes.append({'kind': 'campaign', 'id': old['id'], 'field': 'daily_budget',
                            'before': old['daily_budget'], 'observed': live['daily_budget']})
        for left, right in zip(old['adsets'], live['adsets']):
            if left['bid_amount'] != right['bid_amount']:
                changes.append({'kind': 'adset', 'id': left['id'], 'field': 'bid_amount',
                                'before': left['bid_amount'], 'observed': right['bid_amount']})
    if not changes:
        raise ValueError('manual observation requires demonstrated commercial delta')
    return changes


def validate(base, request, historical_id):
    from . import shein_manual_takeover as manual
    policy = manual.read(policy_path(base))
    target = receipt_path(base, request, historical_id)
    rec = manual.read(target)
    parent = manual.validate(base, historical_id)
    grant = policy.get('grants', {}).get(request['request_id'], {}).get(historical_id, {})
    if (policy.get('schema_version') != 1 or grant.get('receipt_sha256') != manual.sha(target)
            or grant.get('request_sha256') != digest_request(request)
            or rec.get('classification') != CLASSIFICATION or rec.get('schema_version') != 1
            or rec.get('successor_request') != request
            or rec.get('historical_request_id') != historical_id
            or rec.get('account_id') != parent['account_id'] or request.get('account') != parent['account_id']
            or request.get('source_channel_id') != manual.CHANNEL or request.get('source_thread_id') != manual.THREAD
            or rec.get('historical_receipt_sha256') != manual.sha(manual.path(base, historical_id))
            or rec.get('qa_certified') is not False or rec.get('reservation_release') is not False
            or rec.get('campaign_writes') != 0 or rec.get('drive_writes') != 0
            or rec.get('external_change_author') != 'UNPROVEN'
            or not rec.get('observed_at') or not rec.get('maintenance_task_id')
            or rec.get('commercial_deltas') != commercial_deltas(parent['campaigns'], rec['campaigns'])):
        raise ValueError('manual observation binding/grant mismatch; dependency retained')
    return rec


def verify(base, request, historical_id, current):
    from . import shein_manual_takeover as manual
    rec = validate(base, request, historical_id)
    if manual.scheduling_identity(current) != manual.scheduling_identity(rec['campaigns']):
        raise ValueError('manual observation live facts changed; dependency retained')
    return manual.sha(receipt_path(base, request, historical_id))


def register(base, request, historical_id, *, expected_parent_sha256,
             expected_job_sha256, expected_lease_sha256, expected_policy_sha256,
             maintenance_task_id):
    """Maintenance-only GET + coordination transaction. No campaign executor."""
    from . import shein_manual_takeover as manual, shein_request_queue as q
    from . import shein_single_clone as driver
    from .shein_channel_authority import _get
    from .shein_source_media import same_resume_request
    from request_serialization import request_lock
    if os.environ.get('HERMES_PROFILE') != 'ares' or not maintenance_task_id:
        raise ValueError('manual observation requires owning maintenance profile/task')
    job_path = q.job_path(base, request['request_id'])
    engine = manual.engine_root(base)
    lease_path = engine / 'writer-leases' / (manual.ACCOUNT + '.json')
    policy_file = policy_path(base)
    policy_file.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        for path, mode in [(policy_file.with_suffix('.lock'), fcntl.LOCK_EX),
                (job_path.with_suffix('.dispatch.lock'), fcntl.LOCK_EX),
                (job_path.with_suffix('.lock'), fcntl.LOCK_EX),
                (q.root(base)/'single-clone'/('account-'+manual.ACCOUNT+'.lock'), fcntl.LOCK_EX),
                (lease_path.with_suffix('.lock'), fcntl.LOCK_SH)]:
            handle = stack.enter_context(path.open('a+'))
            fcntl.flock(handle, mode | fcntl.LOCK_NB)
        for rid in [historical_id, request['request_id']]:
            stack.enter_context(request_lock(engine/'request-locks', rid, blocking=False))
        actual_policy_sha = manual.sha(policy_file) if policy_file.exists() else None
        if (actual_policy_sha != expected_policy_sha256 or manual.sha(job_path) != expected_job_sha256
                or manual.sha(lease_path) != expected_lease_sha256
                or manual.sha(manual.path(base, historical_id)) != expected_parent_sha256):
            raise ValueError('manual observation CAS mismatch')
        job = manual.read(job_path)
        if (job.get('request') != request or job.get('status') != 'WAITING'
                or not job.get('maintenance_hold') or job.get('dispatch_owner') != 'foreground'
                or job.get('delivery_owner') != 'ares' or job.get('attempts') != 0
                or job.get('notification') is not None):
            raise ValueError('manual observation job must remain protected/untouched')
        state = q.state(base, request['request_id'])
        if not same_resume_request(base, state.get('request'), request):
            raise ValueError('manual observation exact resume binding required')
        parent = manual.validate(base, historical_id, get=_get)
        manual.assert_available(base, manual.ACCOUNT, request)
        account = q.authorize_queue_request(request, base)
        if account['account_id'] != manual.ACCOUNT:
            raise ValueError('manual observation account partition mismatch')
        common = driver._load_common()
        config = manual.read(base/'data/ares/meta-ads/engine-v3/config.json')
        token, _ = common.get_token_from_1password(config['accounts'][manual.ACCOUNT]['token_item'])
        current = manual.capture_live(base, {'campaign_ids':[c['id'] for c in parent['campaigns']]}, common, token)
        changes = commercial_deltas(parent['campaigns'], current)
        # Durable pre-images precede both coordination writes; never overwrite
        # first evidence during recovery, and preserve all unrelated policy grants.
        backup = receipt_path(base, request, historical_id).parent / 'registration-backup'
        backup.mkdir(parents=True, exist_ok=True)
        for source in [policy_file, job_path, lease_path, manual.path(base, historical_id)]:
            dest = backup / (source.parent.name + '-' + source.name)
            if source.exists() and not dest.exists():
                with dest.open('xb') as handle:
                    handle.write(source.read_bytes()); handle.flush(); os.fsync(handle.fileno())
                os.chmod(dest, 0o600)
        target = receipt_path(base, request, historical_id)
        record = {'schema_version':1, 'classification':CLASSIFICATION,
            'successor_request':copy.deepcopy(request), 'historical_request_id':historical_id,
            'account_id':manual.ACCOUNT, 'historical_receipt_sha256':expected_parent_sha256,
            'campaigns':current, 'commercial_deltas':changes,
            'observed_at':datetime.now(timezone.utc).isoformat(), 'maintenance_task_id':maintenance_task_id,
            'qa_certified':False, 'reservation_release':False, 'campaign_writes':0, 'drive_writes':0,
            'external_change_author':'UNPROVEN'}
        # Receipt first, then grant. A crash cannot make an unregistered file valid.
        if target.exists():
            previous = manual.read(target)
            for key in record.keys() - {'observed_at'}:
                if (manual.scheduling_identity(previous[key]) != manual.scheduling_identity(record[key])
                        if key == 'campaigns' else previous[key] != record[key]):
                    raise ValueError('manual observation immutable replay mismatch')
        else:
            q.atomic(target, record)
        policy = manual.read(policy_file) if policy_file.exists() else {'schema_version':1, 'grants':{}}
        if policy.get('schema_version') != 1:
            raise ValueError('manual observation unsupported policy schema')
        grants = policy.setdefault('grants', {}).setdefault(request['request_id'], {})
        grant = {'receipt_sha256':manual.sha(target), 'request_sha256':digest_request(request)}
        if historical_id in grants and grants[historical_id] != grant:
            raise ValueError('manual observation immutable grant mismatch')
        if historical_id not in grants:
            grants[historical_id] = grant
            q.atomic(policy_file, policy)
        validate(base, request, historical_id)
        return {'classification':CLASSIFICATION, 'receipt_sha256':manual.sha(target),
                'commercial_deltas':changes, 'campaign_writes':0, 'drive_writes':0,
                'qa_certified':False, 'request_id':request['request_id']}
