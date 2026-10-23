"""Audited same-request NOW continuation; all Meta writes stay in Engine v3."""
from __future__ import annotations
import copy
import hashlib
import json
import re
from contextvars import ContextVar
from pathlib import Path
from datetime import datetime, timezone

APPROVED_RESUME: ContextVar[dict | None] = ContextVar('shein_approved_same_id_resume', default=None)
BASE = Path('/root/mgs-agent')


def content_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def allows_elapsed_campaign(value):
    context=APPROVED_RESUME.get()
    if not context or (context.get('verified') or {}).get('verified') is not True:return False
    candidates=context['state']['target_manifest'].get('campaigns') or []
    return (context['descriptor'].get('start_now') is True
            and len(candidates)==int(context['descriptor'].get('quantity',0)) and value in candidates
            and value.get('account_id')==context['descriptor']['account_id'] and value.get('status')=='ACTIVE')


def schedule_matches(expected, observed):
    a=datetime.fromisoformat(str(expected)).astimezone(timezone.utc)
    b=datetime.fromisoformat(str(observed)).astimezone(timezone.utc)
    if a==b:return True
    context=APPROVED_RESUME.get()
    if not context or (context.get('verified') or {}).get('verified') is not True:return False
    accepted=context['verified'].get('accepted_schedule')
    if accepted:
        return (a == datetime.fromisoformat(accepted['expected']).astimezone(timezone.utc)
                and b == datetime.fromisoformat(accepted['observed']).astimezone(timezone.utc))
    preserved=context['descriptor'].get('preserved_start_time')
    approved=context['state']['manifest']['campaigns'][0]['start_time']
    return bool(preserved and str(expected)==approved and b==datetime.fromisoformat(preserved).astimezone(timezone.utc) and 0 <= (b-a).total_seconds() <= 1)


def reviewed_schedule_proof(descriptor, state, checkpoint, *, get_message):
    """Exact observed time explicitly reviewed in origin, never a tolerance."""
    from zoneinfo import ZoneInfo
    from .shein_copy_schedule import _instant
    if (descriptor.get('late_activation_authorized') is not True
            or descriptor.get('reviewed_observed_copy_time') is not True
            or descriptor.get('recovery_review_content', '').strip().lower() != 'sim'):
        raise ValueError('explicit exact schedule review required')
    aid=str(descriptor['account_id']);account=state.get('account') or {}
    if account.get('id') != 'act_'+aid or str(checkpoint.get('account_id')) != aid or checkpoint.get('status') != 'COMPLETE':
        raise ValueError('reviewed schedule account/copy provenance unavailable')
    expected=state['request']['start_time'];observed=descriptor['preserved_start_time']
    a,b=_instant(expected),_instant(observed);zone=ZoneInfo(account['timezone_name'])
    if not a < b or a.astimezone(zone).date() != b.astimezone(zone).date():
        raise ValueError('reviewed schedule outside original local day')
    shells=state['manifest']['campaigns'];targets=state['target_manifest']['campaigns']
    cids=[];sids=[];numbers=[]
    if not shells or len(shells) != len(targets):raise ValueError('reviewed schedule manifest coverage missing')
    for shell,target in zip(shells,targets):
        if any(str(x.get('account_id')) != aid or _instant(x['start_time']) != a for x in [shell,target]):
            raise ValueError('reviewed schedule manifest mismatch')
        key=shell['idempotency_key']
        if target['idempotency_key'] != key:raise ValueError('reviewed target slot mismatch')
        bundles=[v for v in checkpoint['bundles'] if key in v.get('idempotency_keys',[])]
        if len(bundles) != 1:raise ValueError('reviewed copy slot ambiguous')
        bundle=bundles[0];index=bundle['idempotency_keys'].index(key)
        window=bundle['timings']['adset_copy']
        if (bundle.get('status') != 'COMPLETE' or not _instant(window['started_at']).replace(microsecond=0) <= b <= _instant(window['finished_at'])):
            raise ValueError('reviewed time outside exact native copy window')
        rows={r['name']:r['body'] for r in bundle['readback_results'] if r.get('code')==200}
        campaign=rows['readback_campaign_'+str(index+1)];adsets=rows['readback_adsets_'+str(index+1)]['data']
        cid=str(bundle['campaign_ids'][index]);sid=str(bundle['adset_ids'][index])
        if (str(campaign.get('id')) != cid or str(campaign.get('account_id')) != aid
                or _instant(campaign['start_time']) != b or len(adsets) != 1
                or str(adsets[0]['id']) != sid or _instant(adsets[0]['start_time']) != b):
            raise ValueError('reviewed exact campaign/adset schedule provenance mismatch')
        cids.append(cid);sids.append(sid);numbers.append(str(int(shell['name'].split(' - ')[0])))
    prompt_id=str(descriptor.get('schedule_review_prompt_message_id') or '')
    review_id=str(descriptor.get('recovery_review_message_id') or '')
    if not all(re.fullmatch(r'[0-9]{17,20}',x) for x in [prompt_id,review_id]):raise ValueError('schedule review prompt missing')
    origin=descriptor['source_thread_id']
    prompt=get_message('/channels/'+origin+'/messages/'+prompt_id)
    previous=get_message('/channels/'+origin+'/messages?before='+review_id+'&limit=100')
    time_label=b.astimezone(zone).strftime('%Hh%Mmin%Ss')
    question='Você autoriza manter **'+time_label+'** nas '+ '/'.join(numbers)+' e concluir a ativação agora, sem recriá-las?'
    if (not isinstance(previous,list) or not any(str(x.get('id')) == prompt_id for x in previous)
            or any(int(x.get('id',0)) > int(prompt_id) and not (
                str((x.get('author') or {}).get('id')) == '1508864261504630925'
                and (x.get('author') or {}).get('bot')
                and x.get('content','').startswith('💾 Self-improvement review:')) for x in previous)
            or str(prompt.get('id')) != prompt_id or str(prompt.get('channel_id')) != origin
            or str((prompt.get('author') or {}).get('id')) != '1508864261504630925'
            or not (prompt.get('author') or {}).get('bot') or question not in prompt.get('content','')):
        raise ValueError('exact preceding Ares schedule question unconfirmed')
    return {'expected':expected,'observed':observed,'campaign_ids':cids,'adset_ids':sids,
            'prompt_message_id':prompt_id,'review_message_id':review_id,'schedule_writes':0,'manifest_mutations':0}


def _late_review_context(account_id):
    operation=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    profiles=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles']
    return operation, copy.deepcopy(profiles[str(account_id)])


def _authorize_late_reviewer(descriptor, original, reviewer):
    # CEO review remains valid; channel delegates use the same live authority as activation.
    if reviewer == '344196393512075265':
        return {'sender_id':reviewer,'source':'executive_review_message'}
    operation,profile=_late_review_context(descriptor['account_id'])
    policy=operation.get('channel_authorization_policy') or {}
    late_policy=policy.get('late_recovery_review') or {}
    if (operation.get('operation_id')!='SHEIN-US-DIRECT' or policy.get('enabled') is not True
            or policy.get('approved_by')!='344196393512075265' or late_policy.get('enabled') is not True
            or late_policy.get('approved_by')!='344196393512075265'
            or str(profile.get('account_id')) != str(descriptor['account_id'])
            or str(profile.get('channel_id')) not in policy.get('channel_ids',[])):
        raise ValueError('approved SHEIN late recovery authority unavailable')
    if str(descriptor['recovery_review_thread_id']) != str(original['source_thread_id']):
        raise ValueError('delegated late review must originate in the original account thread/channel')
    profile['channel_authorization_policy']=policy
    review_request={**original,'authorized_by':reviewer}
    from .shein_general import authorize
    authorize(review_request,profile,force=True)
    return {'sender_id':reviewer,'parent_channel_id':original['source_channel_id'],
            'origin_id':original['source_thread_id'],'source':'live_discord_effective_permissions'}


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
    quantity = int(original.get('quantity',1))
    if descriptor.get('start_now') is not True or int(descriptor.get('quantity',0)) != quantity or not 1 <= quantity <= 100 or original['status'] != 'ACTIVE':
        raise ValueError('continuation requires explicit NOW for exact existing ACTIVE-intent request quantity')
    if state.get('phase') not in {'RECOVERY_PENDING','ENGINE_PENDING','POSTPROCESS_PENDING','ACTIVATION_PENDING','ACTIVATION_DEFERRED','GLOBAL_QA_COMPLETE','COMPLETE_FUTURE_ACTIVE'}:
        raise ValueError('continuation requires an existing recoverable checkpoint')
    bundles = checkpoint.get('bundles') or []
    cids = [str(cid) for b in bundles for cid in b.get('campaign_ids',[])]
    sids = [str(sid) for b in bundles for sid in b.get('adset_ids',[])]
    wanted_cids = descriptor.get('existing_campaign_ids') if quantity > 1 else [descriptor.get('existing_campaign_id')]
    wanted_sids = descriptor.get('existing_adset_ids') if quantity > 1 else [descriptor.get('existing_adset_id')]
    if (not isinstance(wanted_cids,list) or not isinstance(wanted_sids,list)
        or len(cids)!=quantity or len(sids)!=quantity or len(set(cids))!=quantity or len(set(sids))!=quantity
        or any(not re.fullmatch(r'[0-9]+',x) for x in cids+sids)
        or cids != [str(x) for x in wanted_cids] or sids != [str(x) for x in wanted_sids]):
        raise ValueError('continuation does not match exact existing confirmed shell IDs and order')
    if quantity > 1 and (len(state['manifest'].get('campaigns') or [])!=quantity or len(state['target_manifest'].get('campaigns') or [])!=quantity):
        raise ValueError('continuation batch does not cover both sealed manifests')
    if descriptor.get('preserved_start_time') and descriptor.get('reviewed_observed_copy_time') is not True:
        expected=datetime.fromisoformat(state['manifest']['campaigns'][0]['start_time']).astimezone(timezone.utc)
        preserved=datetime.fromisoformat(descriptor['preserved_start_time']).astimezone(timezone.utc)
        if not 0 <= (preserved-expected).total_seconds() <= 1:
            raise ValueError('continuation schedule normalization exceeds original copy one-second bound')
    mid = str(descriptor.get('source_message_id') or '')
    if not re.fullmatch(r'[0-9]{17,20}',mid) or not descriptor.get('source_message_content'):
        raise ValueError('continuation human message evidence is missing')
    message = get_message('/channels/'+descriptor['source_thread_id']+'/messages/'+mid)
    if (str(message.get('id')) != mid or str(message.get('channel_id')) != descriptor['source_thread_id']
        or str(message.get('author',{}).get('id')) != original['authorized_by'] or message.get('author',{}).get('bot')
        or message.get('content') != descriptor['source_message_content']):
        raise ValueError('continuation source message identity/content unconfirmed')
    late = descriptor.get('late_activation_authorized') is True
    review_authority = None
    if late:
        review_mid = str(descriptor.get('recovery_review_message_id') or '')
        review_thread = str(descriptor.get('recovery_review_thread_id') or '')
        if not all(re.fullmatch(r'[0-9]{17,20}',v) for v in [review_mid,review_thread]) or not descriptor.get('recovery_review_content'):
            raise ValueError('late recovery requires exact authorized human review evidence')
        review = get_message('/channels/'+review_thread+'/messages/'+review_mid)
        reviewer = str(review.get('author',{}).get('id') or '')
        if (str(review.get('id')) != review_mid or str(review.get('channel_id')) != review_thread
            or not re.fullmatch(r'[0-9]{17,20}',reviewer) or review.get('author',{}).get('bot')
            or review.get('content') != descriptor['recovery_review_content']):
            raise ValueError('late recovery human review identity/content unconfirmed')
        review_authority = _authorize_late_reviewer(descriptor, original, reviewer)
    accepted_schedule = (reviewed_schedule_proof(descriptor, state, checkpoint, get_message=get_message)
                         if descriptor.get('reviewed_observed_copy_time') is True else None)
    return {'verified':True,'request_id':original['request_id'],'account_id':str(descriptor['account_id']),
            'accepted_schedule':accepted_schedule,
            'campaign_ids':cids,'adset_ids':sids,'source_message_id':mid,'source_thread_id':descriptor['source_thread_id'],
            'start_now':True,'late_activation_authorized':late,'original_execution_started_at':state.get('execution_started_at'),
            'creation_payload_digest':content_digest(state['manifest']),'target_payload_digest':content_digest(state['target_manifest']),
            'review_message_id':descriptor.get('recovery_review_message_id'),'review_authority':review_authority,
            'descriptor_digest':content_digest(descriptor)}


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
    marker=APPROVED_RESUME.set({'descriptor':descriptor,'state':state,'checkpoint':checkpoint,'verified':verified})
    try:
        return route.run_request(state['request'],confirm_execute=confirm_execute)
    finally:
        APPROVED_RESUME.reset(marker)
