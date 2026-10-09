"""Audited same-request NOW continuation; all Meta writes stay in Engine v3."""
from __future__ import annotations
import copy
import hashlib
import json
import re
from contextvars import ContextVar
from pathlib import Path

APPROVED_RESUME = ContextVar('shein_approved_same_id_resume', default=None)
BASE = Path('/root/mgs-agent')


def content_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_descriptor(descriptor, state, checkpoint, *, get_message=None):
    from .shein_channel_authority import _get
    get_message = get_message or _get
    original = state['request']
    pairs = [('continuation_of','request_id'),('account','account'),('authorized_by','authorized_by'),
             ('source_thread_id','source_thread_id'),('source_channel_id','source_channel_id'),
             ('source_campaign_number','source_number'),('budget_usd','budget_usd'),
             ('bid_strategy','bid_strategy'),('bid_usd','bid_usd'),('status','status')]
    if any(str(descriptor.get(a)) != str(original.get(b)) for a,b in pairs):
        raise ValueError('continuation changed immutable request scope')
    if descriptor.get('start_now') is not True or int(descriptor.get('quantity',0)) != int(original.get('quantity',1)) or int(descriptor['quantity']) != 1 or original['status'] != 'ACTIVE':
        raise ValueError('continuation requires explicit NOW for one existing ACTIVE-intent request')
    if state.get('phase') not in {'RECOVERY_PENDING','ENGINE_PENDING','POSTPROCESS_PENDING','ACTIVATION_PENDING','ACTIVATION_DEFERRED','GLOBAL_QA_COMPLETE','COMPLETE_FUTURE_ACTIVE'}:
        raise ValueError('continuation requires an existing recoverable checkpoint')
    bundles = checkpoint.get('bundles') or []
    cids = [str(cid) for b in bundles for cid in b.get('campaign_ids',[])]
    sids = [str(sid) for b in bundles for sid in b.get('adset_ids',[])]
    if cids != [str(descriptor.get('existing_campaign_id'))] or sids != [str(descriptor.get('existing_adset_id'))]:
        raise ValueError('continuation does not match existing confirmed shell IDs')
    mid = str(descriptor.get('source_message_id') or '')
    if not re.fullmatch(r'[0-9]{17,20}',mid) or not descriptor.get('source_message_content'):
        raise ValueError('continuation human message evidence is missing')
    message = get_message('/channels/'+descriptor['source_thread_id']+'/messages/'+mid)
    if (str(message.get('id')) != mid or str(message.get('channel_id')) != descriptor['source_thread_id']
        or str(message.get('author',{}).get('id')) != original['authorized_by'] or message.get('author',{}).get('bot')
        or message.get('content') != descriptor['source_message_content']):
        raise ValueError('continuation source message identity/content unconfirmed')
    late = descriptor.get('late_activation_authorized') is True
    if late:
        review_mid = str(descriptor.get('recovery_review_message_id') or '')
        review_thread = str(descriptor.get('recovery_review_thread_id') or '')
        if not all(re.fullmatch(r'[0-9]{17,20}',v) for v in [review_mid,review_thread]) or not descriptor.get('recovery_review_content'):
            raise ValueError('late recovery requires exact executive review evidence')
        review = get_message('/channels/'+review_thread+'/messages/'+review_mid)
        if (str(review.get('id')) != review_mid or str(review.get('channel_id')) != review_thread
            or str(review.get('author',{}).get('id')) != '344196393512075265' or review.get('author',{}).get('bot')
            or review.get('content') != descriptor['recovery_review_content']):
            raise ValueError('late recovery executive review unconfirmed')
    return {'verified':True,'request_id':original['request_id'],'account_id':str(descriptor['account_id']),
            'campaign_ids':cids,'adset_ids':sids,'source_message_id':mid,'source_thread_id':descriptor['source_thread_id'],
            'start_now':True,'late_activation_authorized':late,'original_execution_started_at':state.get('execution_started_at'),
            'creation_payload_digest':content_digest(state['manifest']),'target_payload_digest':content_digest(state['target_manifest']),
            'review_message_id':descriptor.get('recovery_review_message_id'),'descriptor_digest':content_digest(descriptor)}


def activation_authorization(target, creation, proof):
    context = APPROVED_RESUME.get()
    if context is None:
        return None
    verified = validate_descriptor(context['descriptor'],context['state'],context['checkpoint'])
    ids = [tree['campaign']['id'] for tree in proof.get('trees',[])]
    if (verified['request_id'] != target.request_id or verified['account_id'] != target.campaigns[0].account_id
        or verified['campaign_ids'] != ids or verified['creation_payload_digest'] != content_digest(creation.raw)
        or verified['target_payload_digest'] != content_digest(target.raw)):
        raise ValueError('continuation activation proof not bound to original manifests/IDs')
    return verified


def run(path, *, confirm_execute=False):
    from . import shein_single_clone as route
    descriptor=json.loads(Path(path).read_text());rid=str(descriptor.get('continuation_of') or '')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}',rid):raise ValueError('invalid continuation request ID')
    aid=str(descriptor.get('account_id') or '')
    if not aid.isdigit():raise ValueError('invalid continuation account ID')
    state_path=BASE/'data/ares/meta-ads/state/shein-campaigns/single-clone'/rid/'state.json'
    checkpoint_path=BASE/'data/ares/meta-ads/engine-v3/state/checkpoints'/(rid+'-'+aid+'.json')
    state=json.loads(state_path.read_text());checkpoint=json.loads(checkpoint_path.read_text())
    row=route.lookup_account(state['request']['account'])
    if row['account_id']!=aid:raise ValueError('continuation account binding mismatch')
    profile=copy.deepcopy(json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles'][aid])
    operation=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    profile['channel_authorization_policy']=operation.get('channel_authorization_policy') or {}
    from .shein_general import authorize
    authorize(state['request'],profile,force=True)
    verified=validate_descriptor(descriptor,state,checkpoint)
    route.atomic_json(state_path.parent/'continuation-authorization-verified.json',verified)
    marker=APPROVED_RESUME.set({'descriptor':descriptor,'state':state,'checkpoint':checkpoint})
    try:
        return route.run_request(state['request'],confirm_execute=confirm_execute)
    finally:
        APPROVED_RESUME.reset(marker)
