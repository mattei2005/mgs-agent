"""Bounded pre-write budget supersession. No sealed-manifest editing or Meta write.

Keep original intake and manifests as history. Invalidate only PREPARED reuse;
normal central dry-run regenerates the new seals, with the original clock.
A persisted intent fences old USD45 inputs even across partial failures.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
from . import shein_manual_takeover as manual

PARENT = 'shein-1569495587005530205'
AMENDMENT = '1569505674847854603'
MESSAGE_SHA = '7f93b970e41c2c565639328dad1bd272a47150772468f73e06ce3b5ce086c315'


def effective_intake(base, rid):
    """All six frozen effective inputs; never dispatch the historical USD45 copy."""
    intake=base/'data/ares/meta-ads/audit/shein/campaigns/intake'/PARENT
    authority=intake/('budget-amendment-'+AMENDMENT+'.json')
    if not rid.startswith(PARENT+'-c') or not authority.exists():
        return None
    policy=manual.read(authority)
    rows=[r for r in policy.get('changes',[]) if r.get('request_id')==rid]
    if (policy.get('amendment_message_id')!=AMENDMENT or policy.get('authorized_by')!='1055570806945620030'
            or policy.get('effective_budget_usd')!='30' or len(rows)!=1):
        raise ValueError('pre-write amendment frozen intake authority mismatch')
    input_path=Path(rows[0]['effective_input_path'])
    if manual.sha(input_path)!=rows[0]['effective_input_sha256']:
        raise ValueError('pre-write amendment effective input changed')
    request=manual.read(input_path)
    if request.get('request_id')!=rid or request.get('budget_usd')!='30' or request.get('account')!=manual.ACCOUNT:
        raise ValueError('pre-write amendment effective request mismatch')
    return request


def record_path(base, rid):
    from .shein_request_queue import root, job_path
    job_path(base,rid)
    return root(base)/'queue/prewrite-amendments'/(rid+'.json')


def validate_record(base, rid):
    rec = manual.read(record_path(base,rid))
    before, after = rec['before_request'], rec['after_request']
    if (rid != PARENT+'-c049' or rec.get('schema_version') != 1
            or before.get('request_id') != rid or before.get('account') != manual.ACCOUNT
            or before.get('source_message_id') != '1569495587005530205'
            or before.get('budget_usd') != '45' or after != {**before,'budget_usd':'30'}
            or rec.get('message_id') != AMENDMENT or rec.get('message_sha256') != MESSAGE_SHA
            or rec.get('approved_by') != '1055570806945620030'
            or not rec.get('backup_pins') or not rec.get('execution_started_at')):
        raise ValueError('pre-write amendment receipt invalid')
    for rel, digest in rec['backup_pins'].items():
        p = Path(rel)
        if p.is_absolute() or '..' in p.parts or manual.sha(base/p) != digest:
            raise ValueError('pre-write amendment backup changed')
    return rec


def require_request(base, request):
    rid = request.get('request_id')
    if not rid:
        return
    expected=effective_intake(base,rid)
    if record_path(base,rid).exists():
        expected=validate_record(base,rid)['after_request']
    if expected is None:
        return
    from .shein_source_media import same_resume_request
    if not same_resume_request(base, request, expected):
        raise ValueError('superseded pre-write budget input rejected; use approved USD30 input')


def require_manifest(state_root, manifest):
    base = manual.engine_base(state_root)
    if base is None:
        return
    expected=effective_intake(base,manifest.request_id)
    if record_path(base,manifest.request_id).exists():
        expected=validate_record(base,manifest.request_id)['after_request']
    if expected is None:
        return
    if (len(manifest.campaigns) != expected['quantity']
            or any(c.account_id != manual.ACCOUNT
                   or int(c.campaign_updates.get('daily_budget') or c.campaign_create.get('daily_budget') or 0) != 3000
                   for c in manifest.campaigns)):
        raise ValueError('superseded pre-write manifest budget rejected')


def amend(base, revised_input):
    from . import shein_request_queue as q, shein_single_clone as driver
    from .shein_channel_authority import _get
    from request_serialization import request_lock
    if os.environ.get('HERMES_PROFILE') != 'ares':
        raise ValueError('pre-write amendment requires owning Ares profile')
    revised = manual.read(revised_input); rid = revised['request_id']
    if rid != PARENT+'-c049':
        raise ValueError('pre-write amendment not approved for this request')
    q.authorize_queue_request(revised,base)
    message = _get('/channels/'+manual.THREAD+'/messages/'+AMENDMENT)
    if (message.get('id') != AMENDMENT or message.get('channel_id') != manual.THREAD
            or message.get('author',{}).get('id') != '1055570806945620030'
            or message.get('author',{}).get('bot')
            or hashlib.sha256(message.get('content','').encode()).hexdigest() != MESSAGE_SHA):
        raise ValueError('pre-write amendment fresh authorization mismatch')
    engine = manual.engine_root(base)
    jobpath = q.job_path(base,rid)
    directory = q.root(base)/'single-clone'/rid
    sp = directory/'state.json'
    with ExitStack() as stack:
        for p in [jobpath.with_suffix('.dispatch.lock'),jobpath.with_suffix('.lock'),
                  directory.parent/('account-'+manual.ACCOUNT+'.lock')]:
            h=stack.enter_context(p.open('a+'));fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stack.enter_context(request_lock(engine/'request-locks',rid,blocking=False))
        # No persistent lease owned by this request and no core artifacts may exist.
        lease = manual.read(engine/'writer-leases'/(manual.ACCOUNT+'.json'))
        if lease.get('request_id') == rid and lease.get('blocks_readers'):
            raise ValueError('pre-write amendment request already owns active lease')
        config=manual.read(base/'data/ares/meta-ads/engine-v3/config.json')
        for directory_check in [engine/'checkpoints',engine/'activation',Path(config['audit_root'])]:
            if list(directory_check.glob(rid+'*.json')):
                raise ValueError('pre-write amendment core artifacts exist; sealed execution immutable')
        job_bytes=jobpath.read_bytes(); state_bytes=sp.read_bytes()
        job=json.loads(job_bytes); state=json.loads(state_bytes)
        if (not job.get('maintenance_hold') or job.get('dispatch_owner') != 'foreground'
                or job.get('delivery_owner') != 'ares' or job.get('attempts') != 0
                or job.get('notification') is not None or job.get('status') != 'WAITING'
                or job.get('execution_request') or state.get('phase') != 'PREPARED'
                or any(state.get(k) for k in ['engine_result','qa_proof','media_qa','activation_result','summary','new_media_assets'])):
            raise ValueError('pre-write amendment requires held, untouched PREPARED request')
        target=record_path(base,rid)
        if target.exists():
            rec=validate_record(base,rid)
            if revised != rec['after_request']:
                raise ValueError('pre-write amendment immutable revised input mismatch')
            before=rec['before_request']
        else:
            before=copy.deepcopy(job['request'])
            operation=manual.read(base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json')
            if revised != {**before,'budget_usd':'30'} or before.get('budget_usd') != '45':
                raise ValueError('pre-write amendment only approved budget delta allowed')
            if state['request'] != driver.apply_request_defaults(copy.deepcopy(before),operation):
                raise ValueError('pre-write amendment state/request mismatch')
            audit=base/'data/ares/meta-ads/audit/maintenance/t_27706e88/prewrite-backup'
            audit.mkdir(parents=True,exist_ok=True)
            pins={}
            for source,name in [(jobpath,'job.json'),(sp,'state.json'),(directory/'manifest-sealed.json','manifest-sealed.json')]:
                dest=audit/name
                if dest.exists() and dest.read_bytes()!=source.read_bytes():
                    raise ValueError('pre-write amendment backup collision')
                dest.write_bytes(source.read_bytes());os.chmod(dest,0o600)
                pins[str(dest.relative_to(base))]=manual.sha(dest)
            rec={'schema_version':1,'request_id':rid,'before_request':before,'after_request':revised,
                 'message_id':AMENDMENT,'message_sha256':MESSAGE_SHA,'approved_by':'1055570806945620030',
                 'execution_started_at':state['execution_started_at'],'backup_pins':pins,
                 'recorded_at':datetime.now(timezone.utc).isoformat(),'campaign_writes':0,'drive_writes':0}
            q.atomic(target,rec)  # intent first: old45 already denied during partial recovery
        operation=manual.read(base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json')
        old_state_req=driver.apply_request_defaults(copy.deepcopy(before),operation)
        new_state_req=driver.apply_request_defaults(copy.deepcopy(revised),operation)
        if job['request'] not in [before,revised] or state['request'] not in [old_state_req,new_state_req]:
            raise ValueError('pre-write amendment partial recovery mismatch')
        state['request']=new_state_req
        state['prewrite_amendment_pending']={'receipt_sha256':manual.sha(target),'required_budget_usd':'30',
                                            'reason':'Unexecuted snapshot superseded; central prepare must regenerate seals'}
        job['request']=copy.deepcopy(revised)
        job.setdefault('amendment_receipts',[])
        if str(target) not in job['amendment_receipts']:job['amendment_receipts'].append(str(target))
        if jobpath.read_bytes()!=job_bytes or sp.read_bytes()!=state_bytes:
            raise ValueError('pre-write amendment CAS failed')
        q.atomic(sp,state);q.atomic(jobpath,job)
        require_request(base,revised)
        if manual.read(sp)!=state or manual.read(jobpath)!=job:
            raise ValueError('pre-write amendment readback mismatch')
        return {'status':'PREWRITE_AMENDED_PREPARE_REQUIRED','request_id':rid,'budget_usd':'30',
                'execution_started_at':rec['execution_started_at'],'same_request_clock':True,
                'sealed_manifests_edited':False,'hold_preserved':True,'campaign_writes':0,'drive_writes':0}
