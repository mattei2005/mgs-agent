"""Scoped immediate execution of approved source-derived clones.

Keep the original sealed plan and approval intact. Only a new adset gets a
Meta-safe start at its creation boundary; an existing/uncertain adset retains
its journaled start. No global elapsed-clock bypass and no remote mutation here.
"""
from __future__ import annotations
import copy,json,time,hashlib,re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo

CURRENT=ContextVar('cross_clone_immediate_admission',default=None)
MODE='clone_cross_account_prestaged'

def content_digest(raw):
    from .prevalidation import content_digest as canonical
    return canonical(raw)

@contextmanager
def admission(q,payload,config,proof):
    from . import eggbev_cross_account as cross
    from .prevalidation import verify_prevalidation
    cross.policy(q['request_id'])
    if not verify_prevalidation(payload):raise ValueError('original approved manifest seal invalid')
    account=config['accounts'].get(q['target_account_id'],{})
    if (q.get('start_intent')!='IMMEDIATE_EXPLICIT' or q.get('source_account_id')!=cross.SOURCE or q.get('target_account_id')!=cross.TARGET
        or q['request_id'] not in account.get('campaign_policy',{}).get('immediate_start_request_ids',[])
        or proof.get('request_id')!=q['request_id'] or proof.get('approved_digest')!=content_digest(payload)
        or proof.get('author_id') not in {cross.ACTOR,cross.CEO}
        or re.fullmatch('[0-9]{17,20}',str(proof.get('approval_message_id',''))) is None
        or re.fullmatch('[0-9]{17,20}',str(proof.get('summary_message_id',''))) is None
        or not 0<=time.monotonic()-proof.get('verified_at_monotonic',float('-inf'))<=120
        or any(c.get('mode')!=MODE or c.get('account_id')!=cross.TARGET for c in payload.get('campaigns',[]))):
        raise ValueError('fresh exact immediate final approval admission required')
    marker=CURRENT.set({'payload':copy.deepcopy(payload),'digest':content_digest(payload),'proof':copy.deepcopy(proof),'verified_at':time.monotonic()})
    try:yield
    finally:CURRENT.reset(marker)

def allows_campaign(value):
    current=CURRENT.get()
    return bool(current and time.monotonic()-current['verified_at']<=120 and value.get('mode')==MODE and value in current['payload']['campaigns'])

def require_manifest(raw):
    if not any(c.get('mode')==MODE for c in raw.get('campaigns',[])):return
    elapsed=any(datetime.fromisoformat(c['start_time'])<=datetime.now(timezone.utc) for c in raw['campaigns'] if c.get('mode')==MODE and c.get('status')=='ACTIVE')
    if not elapsed:return
    current=CURRENT.get()
    if not current or content_digest(raw)!=current['digest']:raise ValueError('elapsed cross-account manifest differs from exact approved admission')

def expected_start(c,record,ci):
    entry=record.get('cross_immediate_starts',{}).get(str(ci))
    if not entry:return c.start_time
    pure={k:v for k,v in entry.items() if k!='entry_sha256'}
    digest=hashlib.sha256(json.dumps(pure,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (entry.get('entry_sha256')!=digest or c.mode!=MODE or entry.get('idempotency_key')!=c.idempotency_key
        or entry.get('account_id')!=c.account_id or entry.get('approved_start_time')!=c.start_time
        or entry.get('request_id')!=c.idempotency_key.rsplit('-',1)[0]
        or re.fullmatch('[a-f0-9]{64}',str(entry.get('approved_digest',''))) is None
        or re.fullmatch('[0-9]{17,20}',str(entry.get('approval_message_id',''))) is None):
        raise ValueError('cross-account journaled start identity/tamper mismatch')
    start=datetime.fromisoformat(entry['effective_start_time']);at=datetime.fromisoformat(entry['recorded_at'])
    if start.tzinfo is None or at.tzinfo is None or not 240<=(start-at).total_seconds()<=360:
        raise ValueError('cross-account journaled immediate buffer invalid')
    return entry['effective_start_time']

def new_adset_start(engine,c,record,ci):
    existing=record.get('cross_immediate_starts',{}).get(str(ci))
    if existing:return expected_start(c,record,ci)
    if c.mode!=MODE:return c.start_time
    now=datetime.now(timezone.utc)
    if datetime.fromisoformat(c.start_time)>now:return c.start_time
    from . import eggbev_cross_account as cross
    proof=getattr(engine,'_cross_account_execution_authority',None)
    rid=c.idempotency_key.rsplit('-',1)[0]
    cross.policy(rid)
    if (not proof or proof.get('request_id')!=rid or rid not in engine.config['accounts'][c.account_id].get('campaign_policy',{}).get('immediate_start_request_ids',[])
        or re.fullmatch('[a-f0-9]{64}',str(proof.get('approved_digest',''))) is None
        or re.fullmatch('[0-9]{17,20}',str(proof.get('approval_message_id',''))) is None):
        raise ValueError('new elapsed adset lacks authenticated immediate execution context')
    # Never replace an existing or uncertain adset's schedule. A persisted entry
    # is written before its first POST and is reused by readback-first adoption.
    if record.get('target_clone_ids',{}).get(f'adset_id_{ci}') or f'adset_create_{ci}' in record.get('confirmed_objects',{}):
        raise ValueError('existing adset cannot acquire a new start')
    from .target_page_clone import _uncertain
    if _uncertain(record,f'adset_create_{ci}'):return c.start_time
    actual=(now.astimezone(ZoneInfo('America/New_York'))+timedelta(minutes=5)).replace(microsecond=0).isoformat()
    entry={'idempotency_key':c.idempotency_key,'account_id':c.account_id,'approved_start_time':c.start_time,'effective_start_time':actual,'recorded_at':now.isoformat(),'request_id':rid,'approved_digest':proof.get('approved_digest'),'approval_message_id':proof.get('approval_message_id'),'manifest_unchanged':True}
    entry['entry_sha256']=hashlib.sha256(json.dumps(entry,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    record.setdefault('cross_immediate_starts',{})[str(ci)]=entry
    return actual
