"""Exact reviewed background opt-out for a partial 2+1 SHEIN batch.
Maintenance adapter only: no transport of its own, no manifest/request mutations,
no new schedule authority, and no reusable approval for another request.
"""
from __future__ import annotations
import copy
import json
from contextvars import copy_context
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from .shein_continuation import content_digest

KIND='SHEIN_REVIEWED_BACKGROUND_BATCH_1567010220134105191'
BINDING_DIGEST='c342e5ebe1c4557d8302f72ad871a38b4c266e7406eebd1ae771a52888f03c98'
REQUEST='shein-1567008944717832223'
ACCOUNT='1414197490675732'
ARES='1508864261504630925'
HUMAN='321263240782807040'
ORIGIN='1558126806127611966'
PARENT='1548149300826079333'
ORIGINAL_ID='1567008944717832223'
ORIGINAL='Duplica 3 vezes a campanha 010, orçamento de $150, cost per result goal de $0.70'
PROMPT_ID='1567009511104057483'
REVIEW_ID='1567010220134105191'
FEATURE='image_background_gen'
MESSAGE_DIGESTS={ORIGINAL_ID:'e6ca5fe517be44749dcee3f3d7891738f79c3141b03a54894e0d0c6e1d5b4e14',
    PROMPT_ID:'fb2d2f756042ec309f9150b9fd24cbab3f26b922d19435430d5ae2bce78312b6',
    REVIEW_ID:'fc3922502033c48a184c22b2305d7574b90fa10d91df4bff4d23d85659c96671'}
CHECKPOINT=Path('/root/mgs-agent/data/ares/meta-ads/engine-v3/state/checkpoints')/(REQUEST+'-'+ACCOUNT+'.json')


def selected(descriptor):
    return descriptor.get('reviewed_creative_features_kind')==KIND


def selected_context():
    from .shein_continuation import APPROVED_RESUME
    context=APPROVED_RESUME.get()
    return context if context and selected(context['descriptor']) else None


def make_descriptor(state,bound):
    req=state['request']
    return {'continuation_of':req['request_id'],'account':req['account'],'account_id':ACCOUNT,
        'authorized_by':req['authorized_by'],'source_channel_id':req['source_channel_id'],
        'source_thread_id':req['source_thread_id'],'source_message_id':ORIGINAL_ID,
        'source_message_content':ORIGINAL,'source_campaign_number':req['source_number'],
        'quantity':req['quantity'],'budget_usd':req['budget_usd'],'bid_strategy':req['bid_strategy'],
        'bid_usd':req['bid_usd'],'status':req['status'],'start_time':state['manifest']['campaigns'][0]['start_time'],
        'start_now':False,'review_prompt_message_id':PROMPT_ID,'review_message_id':REVIEW_ID,
        'reviewed_creative_features_kind':KIND,'reviewed_creative_features':copy.deepcopy(bound)}


def _groups(state):
    from .schema import Manifest
    from .planning import Planner
    return Planner().build(Manifest.from_dict(state['manifest'])).lanes[ACCOUNT]


def _receipt(bound,keys):
    # New slots are planned in the original sealed manifest; the core, not this
    # adapter, creates their shells. Initial shells remain immutable.
    initial={key:(b['campaign_ids'][i],b['adset_ids'][i]) for b in bound['initial_shells']
             for i,key in enumerate(b['idempotency_keys'])}
    return {'kind':KIND,'binding_digest':BINDING_DIGEST,'review_message_id':REVIEW_ID,
        'feature':FEATURE,'from':'OPT_IN','to':'OPT_OUT','idempotency_keys':keys,
        'initial_shells':[{'key':key,'campaign_id':initial[key][0],'adset_id':initial[key][1]}
                          for key in keys if key in initial],
        'new_shell_keys':[key for key in keys if key not in initial]}


def require_binding(state,checkpoint,expected):
    from .prevalidation import verify_prevalidation
    if not isinstance(expected,dict) or content_digest(expected)!=BINDING_DIGEST:
        raise ValueError('reviewed batch immutable binding mismatch')
    actual={k:v for k,v in expected.items() if k=='initial_shells'}
    actual.update(request_digest=content_digest(state['request']),request_id=state['request']['request_id'],
        account_id=checkpoint['account_id'],
        account={k:state['account'].get(k) for k in ['id','currency','timezone_name']},
        execution_started_at=state['execution_started_at'],creation_digest=content_digest(state['manifest']),
        target_digest=content_digest(state['target_manifest']),source_digest=content_digest(state['source']),
        slots=[{'key':c['idempotency_key'],'creation_digest':content_digest(c),'target_digest':content_digest(t)}
               for c,t in zip(state['manifest']['campaigns'],state['target_manifest']['campaigns'])])
    if actual!=expected or not all(verify_prevalidation(state[k]) for k in ['manifest','target_manifest']):
        raise ValueError('reviewed batch request/source/clock/manifests changed')
    groups={g.index:[c.idempotency_key for c in g.campaigns] for g in _groups(state)}
    initial={b['index']:b for b in expected['initial_shells']}
    seen=set()
    for record in checkpoint.get('bundles',[]):
        index=record['index'];keys=record.get('idempotency_keys')
        if index in seen or index not in groups or keys!=groups[index]:
            raise ValueError('reviewed batch unexpected or duplicate bundle/slots')
        seen.add(index)
        cids=record.get('campaign_ids',[]);sids=record.get('adset_ids',[])
        if index in initial:
            if cids!=initial[index]['campaign_ids'] or sids!=initial[index]['adset_ids']:
                raise ValueError('reviewed batch original shell IDs changed')
        elif cids or sids:
            from .schema import Manifest
            if (len(cids)!=len(keys) or len(sids)!=len(keys)
                    or record.get('sealed_manifest_digest')!=Manifest.from_dict(state['manifest']).digest
                    or record.get('reviewed_creative_feature_resolution')!=_receipt(expected,keys)):
                raise ValueError('reviewed batch new shell lacks central sealed-slot provenance')
    if not set(initial).issubset(seen):raise ValueError('reviewed batch lost original shells')
    return expected


def _message_digest(message):
    return content_digest({'id':message.get('id'),'channel_id':message.get('channel_id'),
        'author_id':(message.get('author') or {}).get('id'),
        'bot':bool((message.get('author') or {}).get('bot')),'content':message.get('content'),
        'edited_timestamp':message.get('edited_timestamp')})


def validate_descriptor(descriptor,state,checkpoint,*,get_message):
    bound=require_binding(state,checkpoint,descriptor.get('reviewed_creative_features'))
    if descriptor!=make_descriptor(state,bound):raise ValueError('reviewed batch undeclared intent/review/schedule delta')
    if state.get('phase') not in {'RECOVERY_PENDING','ENGINE_PENDING','POSTPROCESS_PENDING','ACTIVATION_PENDING',
            'ACTIVATION_DEFERRED','GLOBAL_QA_COMPLETE','COMPLETE_FUTURE_ACTIVE'}:
        raise ValueError('reviewed batch requires recoverable state')
    for mid,digest in MESSAGE_DIGESTS.items():
        if _message_digest(get_message('/channels/'+ORIGIN+'/messages/'+mid))!=digest:
            raise ValueError('reviewed batch exact Discord evidence mismatch')
    previous=get_message('/channels/'+ORIGIN+'/messages?before='+REVIEW_ID+'&limit=100')
    if (not isinstance(previous,list) or not any(m.get('id')==PROMPT_ID for m in previous)
            or any(int(m.get('id',0))>int(PROMPT_ID) and not (
                (m.get('author') or {}).get('id')==ARES and (m.get('author') or {}).get('bot')
                and m.get('content','').startswith('💾 Self-improvement review:')) for m in previous)):
        raise ValueError('reviewed batch affirmative context ambiguous')
    from .shein_continuation import _authorize_late_reviewer
    authority=_authorize_late_reviewer({**descriptor,'recovery_review_thread_id':ORIGIN},state['request'],HUMAN)
    return {'verified':True,'request_id':REQUEST,'account_id':ACCOUNT,
        'accepted_schedule':None,'accepted_targeting':None,
        'accepted_creative_features':{'binding_digest':BINDING_DIGEST,'prompt_message_id':PROMPT_ID,
            'review_message_id':REVIEW_ID,'feature':FEATURE,'from':'OPT_IN','to':'OPT_OUT','authority':authority},
        'campaign_ids':[v for b in checkpoint['bundles'] for v in b.get('campaign_ids',[])],
        'adset_ids':[v for b in checkpoint['bundles'] for v in b.get('adset_ids',[])],
        'source_message_id':ORIGINAL_ID,'source_thread_id':ORIGIN,'start_now':False,
        'late_activation_authorized':False,'original_execution_started_at':state['execution_started_at'],
        'creation_payload_digest':content_digest(state['manifest']),
        'target_payload_digest':content_digest(state['target_manifest']),
        'review_message_id':REVIEW_ID,'review_authority':authority,'descriptor_digest':content_digest(descriptor)}


def active_context():
    context=selected_context()
    if context is None:return None
    verified=context.get('verified') or {}
    if (verified.get('verified') is not True
            or (verified.get('accepted_creative_features') or {}).get('binding_digest')!=BINDING_DIGEST
            or verified.get('descriptor_digest')!=content_digest(context['descriptor'])):
        raise ValueError('reviewed batch continuation proof invalid')
    require_binding(context['state'],context['checkpoint'],context['descriptor']['reviewed_creative_features'])
    return context


def _opt_out(payload):
    out=copy.deepcopy(payload)
    features=out.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{})
    if features.get(FEATURE)!={'enroll_status':'OPT_IN'}:
        raise ValueError('reviewed batch original feature state changed')
    features[FEATURE]={'enroll_status':'OPT_OUT'}
    return out


def _required_context():
    context=active_context()
    if context is None:raise ValueError('reviewed batch verified context required')
    return context


def effective(payload):
    context=active_context()
    if context is None:return payload
    for campaign in context['state']['manifest']['campaigns']:
        for ad in campaign['ads']:
            original=ad['creative_payload'];resolved=_opt_out(original)
            if payload==original or payload==resolved:return copy.deepcopy(resolved)
    raise ValueError('reviewed batch payload not in sealed approved slots')


def submit_lane(pool,fn,account,bundles,request_id,manifest_digest):
    from .schema import Manifest
    context=_required_context()
    if (account!=ACCOUNT or request_id!=REQUEST
            or manifest_digest!=Manifest.from_dict(context['state']['manifest']).digest):
        raise ValueError('reviewed batch lane/request mismatch')
    return pool.submit(copy_context().run,fn,account,bundles,request_id,manifest_digest)


def extra_points(record):
    active_context()
    return 3*len((record or {}).get('campaign_ids',[])) if not (record or {}).get('reviewed_creative_feature_resolution') else 0


def resolve_bundle(engine,bundle,transport,record):
    from . import progress
    from .schema import Manifest
    from .transport import BatchOperation
    context=_required_context();bound=context['descriptor']['reviewed_creative_features']
    groups={g.index:g for g in _groups(context['state'])}
    expected=groups.get(bundle.index)
    keys=[c.idempotency_key for c in bundle.campaigns]
    if (expected is None or bundle!=expected or record.get('idempotency_keys')!=keys
            or record.get('sealed_manifest_digest')!=Manifest.from_dict(context['state']['manifest']).digest):
        raise ValueError('reviewed batch shell/slot/manifest mismatch')
    current=progress.CURRENT.get()
    if current is None or current[0] is not record:raise ValueError('reviewed batch durable journal unavailable')
    receipt=_receipt(bound,keys);previous=record.get('reviewed_creative_feature_resolution')
    if previous is not None and previous!=receipt:raise ValueError('reviewed batch receipt changed')
    if previous is None:
        cids=record.get('campaign_ids',[]);sids=record.get('adset_ids',[])
        initial=receipt['initial_shells']
        if (cids!=[s['campaign_id'] for s in initial] or sids!=[s['adset_id'] for s in initial]):
            raise ValueError('reviewed batch unresolved or foreign existing shell')
        if cids:
            operations=[]
            for i,(cid,sid) in enumerate(zip(cids,sids),1):
                operations.extend([
                    BatchOperation('feature_campaign_'+str(i),'GET',cid+'?fields=id,account_id,status',kind='readback'),
                    BatchOperation('feature_adset_'+str(i),'GET',sid+'?fields=id,account_id,campaign_id,status',kind='readback'),
                    BatchOperation('feature_ads_'+str(i),'GET',cid+'/ads?fields=id&limit=50',kind='readback')])
            rows=engine._batch(bundle,transport,operations,'reviewed_batch_zero_ads_readback')
            if len(rows)!=len(operations) or any(r.code!=200 for r in rows):raise ValueError('reviewed batch pre-read incomplete')
            live={r.name:r.body for r in rows}
            if set(live)!={op.name for op in operations}:raise ValueError('reviewed batch pre-read aliases mismatch')
            for i,(cid,sid) in enumerate(zip(cids,sids),1):
                c=live['feature_campaign_'+str(i)];s=live['feature_adset_'+str(i)];a=live['feature_ads_'+str(i)]
                if (c.get('id')!=cid or c.get('account_id')!=ACCOUNT or c.get('status')!='PAUSED'
                        or s.get('id')!=sid or s.get('campaign_id')!=cid or s.get('account_id')!=ACCOUNT
                        or s.get('status')!='PAUSED' or a.get('data')!=[] or a.get('paging',{}).get('next')):
                    raise ValueError('reviewed batch requires exact PAUSED zero-ad shells')
        record['reviewed_creative_feature_original_error']=copy.deepcopy(record.get('error'))
        record['reviewed_creative_feature_resolution']=receipt
        current[1]()
    return replace(bundle,campaigns=tuple(replace(c,ads=tuple(
        replace(a,creative_payload=effective(a.creative_payload)) for a in c.ads)) for c in bundle.campaigns))


def verify_creative(actual,expected):
    from .shein_reference import verify_degrees
    verify_degrees(actual.get('degrees_of_freedom_spec'),effective(expected)['degrees_of_freedom_spec'])


def preserved_sourcing(actual,expected):
    """Exact source package, not a new-media recipe or a normalization waiver.
    The reviewed batch keeps the source's disabled uncrop + active smart crop.
    Every sourcing key/value (including crops/variant flags) must be identical.
    """
    if active_context() is None:return None
    try:approved=effective(expected)
    except ValueError:return None
    spec=approved.get('media_sourcing_spec')
    primary=((approved.get('object_story_spec') or {}).get('link_data') or {}).get('image_hash')
    if not primary or not isinstance(spec,dict) or not spec.get('images'):return None
    observed=((actual.get('object_story_spec') or {}).get('link_data') or {}).get('image_hash')
    return observed==primary and actual.get('media_sourcing_spec')==spec


def _final_slots(context):
    checkpoint=json.loads(CHECKPOINT.read_text())
    bound=context['descriptor']['reviewed_creative_features']
    require_binding(context['state'],checkpoint,bound)
    if checkpoint.get('status')!='COMPLETE':raise ValueError('reviewed batch central creation not complete')
    records={r['index']:r for r in checkpoint['bundles']}
    slots=[]
    for group in _groups(context['state']):
        r=records.get(group.index) or {};keys=[c.idempotency_key for c in group.campaigns]
        if (r.get('status')!='COMPLETE' or r.get('reviewed_creative_feature_resolution')!=_receipt(bound,keys)
                or len(r.get('campaign_ids',[]))!=len(keys) or len(r.get('adset_ids',[]))!=len(keys)):
            raise ValueError('reviewed batch central slot receipt incomplete')
        slots.extend((c.idempotency_key,r['campaign_ids'][i],r['adset_ids'][i]) for i,c in enumerate(group.campaigns))
    if len({s[1] for s in slots})!=3 or len({s[2] for s in slots})!=3:raise ValueError('reviewed batch duplicated shell IDs')
    return slots


def validate_activation_tree(tree):
    context=_required_context();cid=tree['campaign'].get('id')
    slots=[s for s in _final_slots(context) if s[1]==cid]
    if len(slots)!=1 or tree['campaign'].get('account_id')!=ACCOUNT:raise ValueError('reviewed batch activation ownership mismatch')
    key,_,sid=slots[0]
    desired=next(c for c in context['state']['manifest']['campaigns'] if c['idempotency_key']==key)
    expected={str(a['source_ad_id']):a for a in desired['ads']}
    sets=tree['adsets'].get('data');ads=tree['ads'].get('data')
    if (not isinstance(sets,list) or not isinstance(ads,list) or len(sets)!=1 or sets[0].get('id')!=sid
            or tree['adsets'].get('paging',{}).get('next') or tree['ads'].get('paging',{}).get('next')
            or len(ads)!=len(expected) or {str(a.get('source_ad_id')) for a in ads}!=set(expected)):
        raise ValueError('reviewed batch activation lineage/cardinality mismatch')
    for ad in ads:
        if ad.get('adset_id')!=sid:raise ValueError('reviewed batch activation ad parent mismatch')
        verify_creative(ad['creative'],expected[str(ad['source_ad_id'])]['creative_payload'])


def activation_authorization(target,creation,proof,*,get_message):
    context=_required_context()
    verified=validate_descriptor(context['descriptor'],context['state'],context['checkpoint'],get_message=get_message)
    slots=_final_slots(context);ids=[s[1] for s in slots]
    if (target.request_id!=REQUEST or any(c.account_id!=ACCOUNT for c in target.campaigns)
            or verified['creation_payload_digest']!=content_digest(creation.raw)
            or verified['target_payload_digest']!=content_digest(target.raw)
            or [t['campaign']['id'] for t in proof.get('trees',[])]!=ids
            or proof.get('execution_started_at')!=context['state']['execution_started_at']):
        raise ValueError('reviewed batch activation immutable proof mismatch')
    # Feature review does not authorize changing a future schedule into NOW.
    if any(datetime.fromisoformat(c.start_time).astimezone(timezone.utc)<=datetime.now(timezone.utc) for c in target.campaigns):
        raise ValueError('reviewed batch original schedule elapsed; no schedule delta approved')
    for tree in proof['trees']:validate_activation_tree(tree)
    return {**verified,'campaign_ids':ids,'adset_ids':[s[2] for s in slots]}
