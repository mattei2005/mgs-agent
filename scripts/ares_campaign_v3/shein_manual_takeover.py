"""Request-scoped human takeover: retire coordination, NEVER certify QA.

An immutable receipt is the replay fence. A crash before lease retirement remains
blocked; recovery repeats this exact transaction, not release()/COMPLETE. No
Meta/Drive writer is imported or called here. Only this approved request is enabled.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
import fcntl
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

REQUEST = 'shein-1569456380065222707'
ACCOUNT = '937846586033361'
THREAD = '1558134703565967394'
CHANNEL = '1548150155184701440'
STATUS = 'MANUAL_TAKEOVER_COORDINATION_CLOSED'
APPROVALS = {
    '1569494300255985776': ('1055570806945620030', 'de5bcf84bda190552e872f019f2aa9aaba2ca8b1025e24ee12819c7c8c8a5930'),
    '1569530861022355457': ('344196393512075265', '8835004e628220e9a6ab79230cdead9b254e0e39ea764818508acba02a8c2859'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def path(base, rid):
    from .shein_request_queue import job_path, root
    job_path(base, rid)  # exact identifier validation, no normalization
    return root(base) / 'queue/manual-takeovers' / (rid + '.json')


def present(base, rid):
    return path(base, rid).exists()


def deny_replay(base, rid):
    # Invalid or incomplete receipts must also fence replay; never fall back to QA.
    if present(base, rid):
        raise ValueError('manual takeover forbids automatic request replay; coordination only, QA not certified')


def engine_base(state_root):
    root = Path(state_root)
    # Canonical config root, or isolated test roots retaining the same layout.
    suffix = ('data', 'ares', 'meta-ads', 'engine-v3', 'state')
    return root.parents[4] if root.parts[-5:] == suffix else None


def deny_engine_replay(state_root, rid):
    base = engine_base(state_root)
    if rid == REQUEST and base is None:
        raise ValueError('manual takeover requires canonical request state root; no alternate-root replay')
    if base is not None:
        deny_replay(base, rid)


def read(path):
    result = json.loads(Path(path).read_text())
    if not isinstance(result, dict):
        raise ValueError('manual takeover object required')
    return result


def verify_messages(messages, get=None):
    if {m['id'] for m in messages} != set(APPROVALS) or len(messages) != len(APPROVALS):
        raise ValueError('manual takeover exact approvals missing')
    for message in messages:
        author, digest = APPROVALS[message['id']]
        if (message.get('author_id') != author or message.get('channel_id') != THREAD
                or hashlib.sha256(message.get('content', '').encode()).hexdigest() != digest):
            raise ValueError('manual takeover approval identity/content mismatch')
        if get is not None:
            live = get('/channels/' + THREAD + '/messages/' + message['id'])
            if (live.get('id') != message['id'] or live.get('channel_id') != THREAD
                    or (live.get('author') or {}).get('id') != author
                    or (live.get('author') or {}).get('bot') or live.get('content') != message['content']):
                raise ValueError('manual takeover fresh approval GET mismatch')


def pinned_paths(base, rid, state_root):
    from .shein_request_queue import root
    directory = root(base) / 'single-clone' / rid
    paths = [directory / 'state.json', directory / 'manifest-sealed.json',
             Path(state_root) / 'checkpoints' / (rid + '-' + ACCOUNT + '.json'),
             Path(state_root) / 'activation' / (rid + '-' + ACCOUNT + '.json')]
    return paths


def validate(base, rid, *, get=None):
    from .shein_decision_wait import _engine_root
    from .shein_request_queue import state
    rec = read(path(base, rid))
    value = state(base, rid)
    req = value.get('request') or {}
    expected_paths = pinned_paths(base, rid, _engine_root(base))
    expected = {str(p.relative_to(base)): sha(p) for p in expected_paths}
    if (rid != REQUEST or rec.get('schema_version') != 1 or rec.get('classification') != STATUS
            or rec.get('request_id') != rid or rec.get('account_id') != ACCOUNT
            or req.get('request_id') != rid or req.get('account') != ACCOUNT
            or req.get('source_thread_id') != THREAD or req.get('source_channel_id') != CHANNEL
            or value.get('phase') != 'ACTIVATION_PENDING' or value.get('summary')
            or rec.get('pins') != expected or rec.get('qa_certified') is not False
            or rec.get('reservation_release') is not False or rec.get('campaign_writes') != 0
            or rec.get('drive_writes') != 0 or not rec.get('recorded_at')
            or rec.get('execution_started_at') != value.get('execution_started_at')
            or rec.get('request_sha256') != hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()):
        raise ValueError('manual takeover receipt/pins mismatch; dependency retained')
    verify_messages(rec.get('messages') or [], get)
    bindings = rec.get('campaigns') or []
    cp = read(expected_paths[2])
    expected_ads = {a for bundle in cp.get('bundles', []) for a in bundle.get('ad_ids', [])}
    expected_sets = {a for bundle in cp.get('bundles', []) for a in bundle.get('adset_ids', [])}
    if (len(bindings) != 9 or len({c['id'] for c in bindings}) != 9
            or {c['id'] for c in bindings} != set(value.get('engine_result', {}).get('campaign_ids') or [])
            or {a['id'] for c in bindings for a in c['ads']} != expected_ads
            or {a['id'] for c in bindings for a in c['adsets']} != expected_sets
            or any(not a.get('creative_id') or not a.get('primary_media') for c in bindings for a in c['ads'])):
        raise ValueError('manual takeover object coverage mismatch')
    return rec


def lease_idle(state_root, lease):
    if lease.get('status') == 'COMPLETE':
        return lease.get('blocks_readers') is False and bool(lease.get('released_at_utc'))
    if lease.get('status') != STATUS or lease.get('blocks_readers') is not False or not lease.get('released_at_utc'):
        return False
    base = engine_base(state_root)
    if base is None:
        return False
    try:
        rec = validate(base, lease.get('request_id'))
        return (lease.get('account_id') == rec['account_id']
                and lease.get('manual_takeover_receipt_sha256') == sha(path(base, rec['request_id'])))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def assert_available(base, account, resume_request=None):
    from .shein_decision_wait import _engine_root
    from .shein_request_queue import state, ACTIVE
    from .shein_source_media import same_resume_request
    engine = _engine_root(base)
    lease = read(engine / 'writer-leases' / (account + '.json'))
    own = False
    if resume_request is not None:
        resume = state(base, resume_request['request_id'])
        own = (lease.get('request_id') == resume_request['request_id'] and lease.get('blocks_readers') is True
               and lease.get('status') in {'IN_PROGRESS','DEFERRED_QUOTA','READBACK_DEFERRED','RECOVERY_PENDING','ACTIVATION_PENDING','ACTIVATION_DEFERRED'}
               and resume.get('phase') in ACTIVE and same_resume_request(base, resume.get('request'), resume_request))
    if lease.get('account_id') != account or not (lease_idle(engine, lease) or own):
        raise ValueError('manual takeover foreign or unretired writer lease')


def capture_live(base, rec, common, token):
    """GET-only identity/media/status projection; external deltas remain external."""
    from . import shein_single_clone as driver
    from .shein_source_media import primary_media
    queries = []
    for cid in rec['campaign_ids']:
        for kind, endpoint, fields in [
            ('campaign', cid, 'id,account_id,name,status,effective_status,daily_budget,bid_strategy,start_time'),
            ('adsets', cid+'/adsets', 'id,account_id,campaign_id,status,effective_status,bid_amount,start_time'),
            ('ads', cid+'/ads', 'id,account_id,campaign_id,adset_id,status,effective_status,issues_info,ad_review_feedback,creative{id,object_story_spec,asset_feed_spec}')]:
            queries.append({'name':cid+'_'+kind,'path':endpoint,'params':{'fields':fields,**({'limit':50} if kind!='campaign' else {})}})
    raw = driver._batch(common, token, queries)
    result = []
    for cid in rec['campaign_ids']:
        c = raw[cid+'_campaign']
        sets = driver._complete_edge(raw[cid+'_adsets']); ads = driver._complete_edge(raw[cid+'_ads'])
        if (c.get('id') != cid or c.get('account_id') != ACCOUNT or not sets or not ads
                or any(x.get('account_id') != ACCOUNT or x.get('campaign_id') != cid for x in sets+ads)
                or any(a.get('adset_id') not in {x['id'] for x in sets} for a in ads)):
            raise ValueError('manual takeover live account/parent coverage mismatch')
        result.append({k:c.get(k) for k in ['id','name','status','effective_status','daily_budget','bid_strategy','start_time']} | {
            'adsets':[{k:x.get(k) for k in ['id','status','effective_status','bid_amount','start_time']} for x in sorted(sets,key=lambda x:x['id'])],
            'ads':[{'id':x['id'],'adset_id':x['adset_id'],'creative_id':x['creative']['id'],
                    'status':x['status'],'effective_status':x.get('effective_status'),
                    'issue_codes':sorted({i['error_code'] for i in x.get('issues_info') or [] if i.get('error_code')}),
                    'ad_review_feedback':x.get('ad_review_feedback'),
                    'primary_media':[list(identity) for identity in sorted(primary_media(x['creative']))]} for x in sorted(ads,key=lambda x:x['id'])]})
    return sorted(result, key=lambda c:c['id'])


def scheduling_identity(campaigns):
    """Historical replay fence is not a freeze of external delivery/review state.

    Compare all pinned configuration, IDs and actual media. Preserve both live
    and baseline status/review facts separately; this is never a QA certificate.
    Deleted/archived objects or changed identity/configuration still fail closed.
    """
    result = copy.deepcopy(campaigns)
    for campaign in result:
        objects = [campaign] + campaign['adsets'] + campaign['ads']
        for obj in objects:
            if obj.get('status') not in {'ACTIVE', 'PAUSED'}:
                raise ValueError('manual takeover historical object no longer live')
            for key in ('status', 'effective_status', 'issue_codes', 'ad_review_feedback'):
                obj.pop(key, None)
    return result


def verify_live(base, rid, common, token):
    rec = validate(base, rid)
    current = capture_live(base, {'campaign_ids':[c['id'] for c in rec['campaigns']]}, common, token)
    if scheduling_identity(current) != scheduling_identity(rec['campaigns']):
        raise ValueError('manual takeover historical live facts changed; dependency retained')
    return {'classification':STATUS, 'state_sha256':rec['pins'][str(pinned_paths(base,rid,engine_root(base))[0].relative_to(base))],
            'record_sha256':sha(path(base,rid)),
            'checkpoint_sha256':rec['pins'][str(pinned_paths(base,rid,engine_root(base))[2].relative_to(base))],
            'campaign_ids':[c['id'] for c in current],
            'ad_ids':sorted(a['id'] for c in current for a in c['ads']),
            'adset_ids':sorted(a['id'] for c in current for a in c['adsets']),
            'identities':sorted({tuple(i) for c in current for a in c['ads'] for i in a['primary_media']})}


def engine_root(base):
    from .shein_decision_wait import _engine_root
    return _engine_root(base)


def reconcile(base, messages, *, expected_pins, expected_lease_sha256):
    """Lock all writers/dispatchers; preserve exact backups before replay fencing."""
    from . import shein_request_queue as q
    from request_serialization import request_lock
    root = engine_root(base)
    protected = q.job_path(base,'shein-1569495587005530205-c049')
    with ExitStack() as stack:
        for p in [protected.with_suffix('.dispatch.lock'), protected.with_suffix('.lock'),
                  q.root(base)/'single-clone'/('account-'+ACCOUNT+'.lock')]:
            h=stack.enter_context(p.open('a+'));fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stack.enter_context(request_lock(root/'request-locks',REQUEST,blocking=False))
        stack.enter_context(request_lock(root/'request-locks','shein-1569495587005530205-c049',blocking=False))
        job=read(protected)
        if (not job.get('maintenance_hold') or job.get('dispatch_owner')!='foreground'
                or job.get('delivery_owner')!='ares' or job.get('attempts')!=0
                or job.get('notification') is not None or job.get('status')!='WAITING'):
            raise ValueError('manual takeover new job must remain held/foreground/untouched')
        backup=base/'data/ares/meta-ads/audit/maintenance/t_27706e88/takeover-backup'
        backup.mkdir(parents=True,exist_ok=True)
        for source in pinned_paths(base,REQUEST,root)+[root/'writer-leases'/(ACCOUNT+'.json'),protected]:
            dest=backup/(source.parent.name+'-'+source.name)
            if not dest.exists():
                dest.write_bytes(source.read_bytes());os.chmod(dest,0o600)
        return _reconcile_locked(base,messages,expected_pins=expected_pins,expected_lease_sha256=expected_lease_sha256)


def _reconcile_locked(base, messages, *, expected_pins, expected_lease_sha256):
    """Caller holds maintenance/account/request/dispatch locks; lease method CASes.

    Persist replay fence first. If interrupted, repeat with identical pins/receipt;
    no caller may use release() to finish the transaction.
    """
    from . import shein_request_queue as q, shein_single_clone as driver
    from .shein_channel_authority import _get, verify
    from .coordination import AccountWriterLeaseStore
    if os.environ.get('HERMES_PROFILE') != 'ares':
        raise ValueError('manual takeover requires owning Ares profile')
    verify_messages(messages, _get)
    value = q.state(base, REQUEST)
    config = read(base/'data/ares/meta-ads/engine-v3/config.json')
    root = engine_root(base)
    pins = {str(p.relative_to(base)):sha(p) for p in pinned_paths(base,REQUEST,root)}
    if pins != expected_pins:
        raise ValueError('manual takeover CAS state/checkpoint changed')
    lease_path=root/'writer-leases'/(ACCOUNT+'.json')
    lease=read(lease_path)
    already_retired=present(base,REQUEST) and lease_idle(root,lease)
    if not already_retired and (sha(lease_path)!=expected_lease_sha256
            or lease.get('request_id')!=REQUEST or lease.get('account_id')!=ACCOUNT
            or lease.get('status')!='ACTIVATION_PENDING' or lease.get('blocks_readers') is not True):
        raise ValueError('manual takeover foreign/changed lease before receipt')
    request = value['request']
    q.authorize_queue_request(request,base)
    profiles = read(base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json')['profiles']
    verify({**request,'authorized_by':'344196393512075265'},profiles[ACCOUNT],force=True)
    common = driver._load_common()
    token, _ = common.get_token_from_1password(config['accounts'][ACCOUNT]['token_item'])
    campaigns = capture_live(base, {'campaign_ids':value['engine_result']['campaign_ids']}, common, token)
    record = {'schema_version':1,'classification':STATUS,'request_id':REQUEST,'account_id':ACCOUNT,
              'messages':copy.deepcopy(messages),'pins':pins,'campaigns':campaigns,
              'request_sha256':hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest(),
              'execution_started_at':value['execution_started_at'],'recorded_at':datetime.now(timezone.utc).isoformat(),
              'qa_certified':False,'reservation_release':False,'campaign_writes':0,'drive_writes':0,
              'activation_reported_by':'1055570806945620030','budget_change_author':'UNPROVEN',
              'maintenance_task_id':'t_27706e88'}
    target = path(base, REQUEST)
    if target.exists():
        previous = validate(base,REQUEST,get=_get)
        for key in ['pins','messages','campaigns','execution_started_at','request_sha256']:
            if previous[key] != record[key]:
                raise ValueError('manual takeover immutable replay mismatch')
    else:
        # Backup is durable before this function; atomic immutable replay fence.
        q.atomic(target,record)
    validate(base,REQUEST)
    AccountWriterLeaseStore(root).retire_manual(ACCOUNT,REQUEST,expected_sha256=expected_lease_sha256)
    lease = read(root/'writer-leases'/(ACCOUNT+'.json'))
    if not lease_idle(root,lease):
        raise ValueError('manual takeover lease readback failed')
    return {'status':STATUS,'request_id':REQUEST,'receipt_sha256':sha(target),
            'qa_certified':False,'campaign_writes':0,'drive_writes':0}
