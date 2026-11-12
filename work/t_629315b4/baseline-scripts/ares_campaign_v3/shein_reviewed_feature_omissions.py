"""Read-only, exact CEO-reviewed feature omissions on six existing ads.
No creation/write/feature toggle or schedule change. Original defaults and all
other requests keep the strict comparator. Evidence is frozen, not inferred.
"""
from __future__ import annotations
import copy
from .shein_continuation import content_digest

BINDING_DIGEST='73dda80cf668888f45e529c847b9fda9a99f6d8e683f614f3c60699947d1c29c'
HUMAN='344196393512075265'
ARES='1508864261504630925'
ORIGIN='1558126806127611966'
PROMPT_ID='1567013827302662197'
REVIEW_ID='1567026734212190352'
OMISSIONS=frozenset({'product_browsing','video_auto_crop','video_filtering','video_uncrop'})
MESSAGE_DIGESTS={
 '1567026734212190352':'e7da5f5d20292456e2fea4dc19027088841d7be17c0099d36d6af1315196e39c',
 '1567026619749502988':'164e158c3e33a501d0be73a7907d63617e06fb48cccabd64ab13625a7b50d8d5',
 '1567026550845739100':'59530a5bcfee2df80db3ef1b76b0895ed53b5c8bb1f74e642e852da2dbb5bbc4',
 '1567026209118748725':'cff831b8c36d9dae706c8835184ad2686520195af10966d9c0db7895df69209c',
 '1567026095637663808':'6fbb1391e145f29e742e29c4636f34700a9b554087efaacafc5fad0c5b0fc22c',
 '1567025783346692228':'5c40708694ba90cf5a51caa9bdcf56e1265ec33a713bb86a7322c119dfac25c6',
 '1567025584616378430':'bae7003d8aa978704867db81902a576a3a2fe77e1ad0026158ca4a15f584c840',
 '1567025342080753747':'f58078a8590b3e7cbd6ba8a19c0e27aa02df52a72f0558d393e53b9b7a984020',
 '1567025138984165410':'4e1fc06175624f1407ae359da36937c46d5ea77b0bc28a3b2e93a462194bec82',
 '1567013827302662197':'8f06fc224f50f0596400d51dc0365b3ba264cee5486763b9fe627c9c3d00b1ca'}


def require_binding(state,checkpoint,bound):
    from .shein_reviewed_background_batch import ACCOUNT,REQUEST
    if not isinstance(bound,dict) or content_digest(bound)!=BINDING_DIGEST:
        raise ValueError('reviewed omissions exact binding required')
    base={k:v for k,v in bound.items() if k in {'slots','accepted_omissions'}}
    base.update(request_id=state['request']['request_id'],account_id=checkpoint['account_id'],
        request_digest=content_digest(state['request']),creation_digest=content_digest(state['manifest']),
        target_digest=content_digest(state['target_manifest']),source_digest=content_digest(state['source']),
        execution_started_at=state['execution_started_at'])
    if (base!=bound or base['request_id']!=REQUEST or base['account_id']!=ACCOUNT
            or checkpoint.get('status')!='COMPLETE' or len(bound['slots'])!=6
            or set(bound['accepted_omissions'])!=OMISSIONS):
        raise ValueError('reviewed omissions request/manifests/clock/IDs changed')
    specs={c['idempotency_key']:c for c in state['manifest']['campaigns']}
    expected_ads={s['ad_id'] for s in bound['slots']};expected_cr={s['creative_id'] for s in bound['slots']}
    records=checkpoint.get('bundles') or []
    if (not records or any(r.get('status')!='COMPLETE' for r in records)
            or {a for r in records for a in r.get('ad_ids',[])}!=expected_ads
            or {a for r in records for a in r.get('creative_ids',[])}!=expected_cr
            or len(expected_ads)!=6 or len(expected_cr)!=6):
        raise ValueError('reviewed omissions existing ad/creative identity mismatch')
    # Bind each ad/creative to its exact campaign + source lineage from the
    # completed central receipt, not just a loose set of six IDs.
    observed=[]
    for r in records:
        rows={row['name']:row['body'] for row in r.get('readback_results',[]) if row.get('code')==200}
        for i,key in enumerate(r.get('idempotency_keys',[]),1):
            if key not in specs:raise ValueError('reviewed omissions unknown slot')
            campaign=specs[key];slots={a['source_ad_id']:a for a in campaign['ads']}
            ads=rows.get('readback_ads_'+str(i)) or {}
            if not isinstance(ads.get('data'),list) or ads.get('paging',{}).get('next'):
                raise ValueError('reviewed omissions complete central ads receipt required')
            for ad in ads['data']:
                source=ad.get('source_ad_id')
                if source not in slots:raise ValueError('reviewed omissions source lineage changed')
                observed.append({'key':key,'campaign_id':r['campaign_ids'][i-1],
                    'adset_id':ad['adset_id'],'ad_id':ad['id'],'creative_id':ad['creative']['id'],
                    'source_ad_id':source,'expected_payload_digest':content_digest(slots[source]['creative_payload'])})
    if sorted(observed,key=lambda x:x['ad_id'])!=bound['slots']:
        raise ValueError('reviewed omissions exact central lineage/slot binding mismatch')
    return bound


def validate(bound,state,checkpoint,*,get_message):
    from .shein_reviewed_background_batch import _message_digest
    require_binding(state,checkpoint,bound)
    # One paginated history GET carries the exact preceding dialogue; fetching
    # every message separately needlessly exhausts Discord's per-route bucket.
    history=get_message('/channels/'+ORIGIN+'/messages?before='+REVIEW_ID+'&limit=100')
    review=get_message('/channels/'+ORIGIN+'/messages/'+REVIEW_ID)
    if not isinstance(history,list) or not any(m.get('id')==PROMPT_ID for m in history):
        raise ValueError('reviewed omissions explanation context unavailable')
    by_id={m.get('id'):m for m in history};by_id[REVIEW_ID]=review
    for mid,digest in MESSAGE_DIGESTS.items():
        if mid not in by_id or _message_digest(by_id[mid])!=digest:
            raise ValueError('reviewed omissions exact origin dialogue changed')
    # The CEO's order follows the complete, frozen explanation, including the
    # uncertainty between an absent API field and a disabled UI control.
    for message in history:
        mid=message.get('id','0')
        if int(mid)<int(PROMPT_ID):continue
        if mid in MESSAGE_DIGESTS:
            if _message_digest(message)!=MESSAGE_DIGESTS[mid]:raise ValueError('reviewed omissions dialogue drift')
        elif not ((message.get('author') or {}).get('id')==ARES
                and (message.get('author') or {}).get('bot')
                and (message.get('edited_timestamp') or message.get('content','').startswith('💾 Self-improvement review:'))):
            raise ValueError('reviewed omissions intervening decision ambiguity')
    from .shein_continuation import _authorize_late_reviewer
    authority=_authorize_late_reviewer({'account_id':bound['account_id'],'recovery_review_thread_id':ORIGIN},state['request'],HUMAN)
    return {'binding_digest':BINDING_DIGEST,'review_message_id':REVIEW_ID,'prompt_message_id':PROMPT_ID,
        'accepted_omissions':sorted(OMISSIONS),'authority':authority,'meta_writes':0,
        'schedule_changes':0,'creation_replay_allowed':False}


def _context():
    from .shein_reviewed_background_batch import active_context
    context=active_context()
    if context is None or 'reviewed_feature_omissions' not in context['descriptor']:return None
    proof=context['verified'].get('accepted_feature_omissions') or {}
    if proof.get('binding_digest')!=BINDING_DIGEST or proof.get('review_message_id')!=REVIEW_ID:
        raise ValueError('reviewed omissions verified authority missing')
    require_binding(context['state'],context['checkpoint'],context['descriptor']['reviewed_feature_omissions'])
    return context


def expected_degrees(actual,expected):
    """Only tolerate the four approved ABSENT fields on these creative IDs.
    Explicit OPT_OUT/OPT_IN values, a fifth omission or a new enabled feature
    still fail the ordinary individual-feature comparator.
    """
    context=_context()
    if context is None:return None
    bound=context['descriptor']['reviewed_feature_omissions']
    slots=[s for s in bound['slots'] if s['creative_id']==actual.get('id')
           and s['expected_payload_digest']==content_digest(expected)]
    if len(slots)!=1:raise ValueError('reviewed omissions creative/payload outside approved IDs')
    from .shein_reviewed_background_batch import effective
    desired=effective(expected)['degrees_of_freedom_spec']
    observed=(actual.get('degrees_of_freedom_spec') or {}).get('creative_features_spec') or {}
    # Keep the original strict comparison valid if the API later exposes all
    # four fields exactly as sent; only the exact missing quartet is reviewed.
    present=OMISSIONS.intersection(observed)
    if not present:
        desired=copy.deepcopy(desired)
        for key in OMISSIONS:
            if desired['creative_features_spec'].get(key)!={'enroll_status':'OPT_IN'}:
                raise ValueError('reviewed omissions source feature state changed')
            del desired['creative_features_spec'][key]
    elif present!=OMISSIONS:
        raise ValueError('reviewed omissions subset changed')
    return desired
