"""Exact human-reviewed image-background opt-out for one existing SHEIN request.
No transport, global defaults, credential changes or sealed-manifest mutations.
The maintenance seal is NOT reusable authority for any other request.
"""
from __future__ import annotations
import copy
from contextvars import copy_context
from dataclasses import replace
from .shein_continuation import content_digest

KIND='SHEIN_EXISTING_IMAGE_BACKGROUND_OPT_OUT_V1'
BINDING_DIGEST='05d5bac6d2ac797e75a00ae2d956520b20d0a8125c67e8e3b7b1521c692dc224'
ARES='1508864261504630925'
HUMAN='321263240782807040'
ORIGIN='1558126806127611966'
ORIGINAL_ID='1566520095373525165'
ORIGINAL='Duplicar a campanha 011, com Cost per result goal $0,80  orçamento de $100, data 01/11 iniciar de imediato'
PROMPT_ID='1566520609687474239'
PROMPT=('A **012 — cópia da 011** foi criada na **Mavroa Conta 02**, com:\n'
        '- **Orçamento:** US$ 100/dia.\n- **Cost per result goal:** US$ 0,80.\n'
        '- **Status:** pausada, ainda sem anúncios publicados.\n\n'
        'A Meta rejeitou os dois anúncios porque a opção herdada **“Geração de plano de fundo da imagem”** exige um catálogo selecionado.\n\n'
        '**Autoriza desativar somente essa opção na cópia e concluir a publicação com início imediato?** A campanha 011 não será alterada.')
REVIEW_ID='1566522041530843238'
REVIEW='Sim, autorizo'
FEATURE='image_background_gen'


def binding(state,checkpoint):
    source=state['source']
    return {'request_digest':content_digest(state['request']),'request_id':state['request']['request_id'],
        'account_id':checkpoint['account_id'],
        'account':{k:state['account'].get(k) for k in ['id','currency','timezone_name']},
        'execution_started_at':state['execution_started_at'],
        'creation_digest':content_digest(state['manifest']),'target_digest':content_digest(state['target_manifest']),
        'source_campaign_id':source['campaign']['id'],'source_adset_id':source['adset']['id'],
        'source_ads':[{'id':a['id'],'creative_digest':content_digest(a['creative'])} for a in source['ads']],
        'shells':[{'campaign_ids':b['campaign_ids'],'adset_ids':b['adset_ids'],
                   'idempotency_keys':b['idempotency_keys']} for b in checkpoint['bundles']]}


def require_binding(state,checkpoint,expected):
    from .prevalidation import verify_prevalidation
    actual=binding(state,checkpoint)
    if (actual!=expected or content_digest(actual)!=BINDING_DIGEST
            or not all(verify_prevalidation(state[k]) for k in ['manifest','target_manifest'])):
        raise ValueError('reviewed creative feature immutable scope/seal mismatch')
    return actual


def validate_review(descriptor,state,checkpoint,*,get_message):
    accepted=descriptor.get('reviewed_creative_features')
    kind=descriptor.get('reviewed_creative_features_kind')
    if accepted is None:
        if kind is not None:raise ValueError('reviewed creative feature binding missing')
        return None
    if kind!=KIND:raise ValueError('unknown reviewed creative feature kind')
    require_binding(state,checkpoint,accepted)
    if (descriptor.get('source_message_id')!=ORIGINAL_ID or descriptor.get('source_message_content')!=ORIGINAL
            or descriptor.get('source_thread_id')!=ORIGIN or descriptor.get('authorized_by')!=HUMAN):
        raise ValueError('reviewed creative feature original message mismatch')
    for mid,text,actor,bot in [(ORIGINAL_ID,ORIGINAL,HUMAN,False),(PROMPT_ID,PROMPT,ARES,True),(REVIEW_ID,REVIEW,HUMAN,False)]:
        message=get_message('/channels/'+ORIGIN+'/messages/'+mid)
        if (message.get('id')!=mid or message.get('channel_id')!=ORIGIN
                or (message.get('author') or {}).get('id')!=actor
                or bool((message.get('author') or {}).get('bot'))!=bot
                or message.get('content')!=text or message.get('edited_timestamp')):
            raise ValueError('reviewed creative feature exact Discord evidence mismatch')
    previous=get_message('/channels/'+ORIGIN+'/messages?before='+REVIEW_ID+'&limit=100')
    if (not isinstance(previous,list) or not any(m.get('id')==PROMPT_ID for m in previous)
            or any(int(m.get('id',0))>int(PROMPT_ID) and not (
                (m.get('author') or {}).get('id')==ARES and (m.get('author') or {}).get('bot')
                and m.get('content','').startswith('💾 Self-improvement review:')) for m in previous)):
        raise ValueError('reviewed creative feature affirmative answer context ambiguous')
    from .shein_continuation import _authorize_late_reviewer
    authority=_authorize_late_reviewer({**descriptor,'recovery_review_thread_id':ORIGIN},state['request'],HUMAN)
    return {'binding_digest':BINDING_DIGEST,'prompt_message_id':PROMPT_ID,'review_message_id':REVIEW_ID,
            'feature':FEATURE,'from':'OPT_IN','to':'OPT_OUT','authority':authority,
            'meta_writes':0,'manifest_mutations':0}


def active_context():
    from .shein_continuation import APPROVED_RESUME
    context=APPROVED_RESUME.get()
    if context is None or (context.get('verified') or {}).get('accepted_creative_features') is None:return None
    verified=context['verified']
    if (verified.get('verified') is not True
            or verified['accepted_creative_features']['binding_digest']!=BINDING_DIGEST
            or content_digest(context['descriptor'])!=verified['descriptor_digest']
            or context['descriptor'].get('reviewed_creative_features_kind')!=KIND):
        raise ValueError('reviewed creative feature continuation context invalid')
    require_binding(context['state'],context['checkpoint'],context['descriptor']['reviewed_creative_features'])
    return context


def _opt_out(payload):
    result=copy.deepcopy(payload)
    features=result.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{})
    if features.get(FEATURE)!={'enroll_status':'OPT_IN'}:
        raise ValueError('reviewed creative feature original state changed')
    features[FEATURE]={'enroll_status':'OPT_OUT'}
    return result


def effective(payload):
    context=active_context()
    if context is None:return payload
    originals=[ad['creative_payload'] for c in context['state']['manifest']['campaigns'] for ad in c['ads']]
    for cp in originals:
        resolved=_opt_out(cp)
        if payload==cp or payload==resolved:return copy.deepcopy(resolved)
    raise ValueError('reviewed creative feature payload is not an approved sealed slot')


def submit_lane(pool,fn,account,bundles,request_id,manifest_digest):
    # ContextVars do not cross ThreadPoolExecutor by default. Propagate only
    # this verified account-scoped continuation, never introduce global state.
    context=active_context()
    if context is None:return pool.submit(fn,account,bundles,request_id,manifest_digest)
    bound=context['descriptor']['reviewed_creative_features']
    from .schema import Manifest
    if account!=bound['account_id'] or request_id!=bound['request_id'] or manifest_digest!=Manifest.from_dict(context['state']['manifest']).digest:
        raise ValueError('reviewed creative feature lane/request mismatch')
    return pool.submit(copy_context().run,fn,account,bundles,request_id,manifest_digest)


def extra_points(record):
    return 3 if active_context() is not None and not (record or {}).get('reviewed_creative_feature_resolution') else 0


def resolve_bundle(engine,bundle,transport,record):
    context=active_context()
    if context is None:return bundle
    from . import progress
    from .transport import BatchOperation
    from .schema import Manifest
    bound=context['descriptor']['reviewed_creative_features'];shells=bound['shells']
    if (bundle.account_id!=bound['account_id'] or len(bundle.campaigns)!=1 or len(shells)!=1
            or [c.idempotency_key for c in bundle.campaigns]!=shells[0]['idempotency_keys']
            or record.get('campaign_ids')!=shells[0]['campaign_ids'] or record.get('adset_ids')!=shells[0]['adset_ids']
            or record.get('sealed_manifest_digest')!=Manifest.from_dict(context['state']['manifest']).digest
            or any(c.mode!='pure_clone' or c.status!='PAUSED' for c in bundle.campaigns)):
        raise ValueError('reviewed creative feature recovery shell/slot mismatch')
    current=progress.CURRENT.get()
    if current is None or current[0] is not record:raise ValueError('reviewed creative feature durable journal missing')
    receipt={'kind':KIND,'binding_digest':BINDING_DIGEST,'review_message_id':REVIEW_ID,
             'feature':FEATURE,'from':'OPT_IN','to':'OPT_OUT','campaign_ids':record['campaign_ids'],
             'adset_ids':record['adset_ids'],'manifest_digest':record['sealed_manifest_digest']}
    previous=record.get('reviewed_creative_feature_resolution')
    if previous is not None and previous!=receipt:raise ValueError('reviewed creative feature receipt changed')
    if previous is None:
        cid=record['campaign_ids'][0];sid=record['adset_ids'][0]
        rows=engine._batch(bundle,transport,[
            BatchOperation('feature_campaign','GET',cid+'?fields=id,account_id,status',kind='readback'),
            BatchOperation('feature_adset','GET',sid+'?fields=id,account_id,campaign_id,status',kind='readback'),
            BatchOperation('feature_ads','GET',cid+'/ads?fields=id&limit=50',kind='readback')],
            'reviewed_feature_zero_ads_readback')
        if len(rows)!=3 or any(r.code!=200 for r in rows):raise ValueError('reviewed creative feature pre-read incomplete')
        live={r.name:r.body for r in rows};c=live['feature_campaign'];s=live['feature_adset'];a=live['feature_ads']
        if (c.get('id')!=cid or c.get('account_id')!=bundle.account_id or c.get('status')!='PAUSED'
                or s.get('id')!=sid or s.get('campaign_id')!=cid or s.get('account_id')!=bundle.account_id
                or s.get('status')!='PAUSED' or a.get('data')!=[] or a.get('paging',{}).get('next')):
            raise ValueError('reviewed creative feature requires fresh exact PAUSED zero-ad shells')
        record['reviewed_creative_feature_original_error']=copy.deepcopy(record.get('error'))
        record['reviewed_creative_feature_resolution']=receipt
        current[1]()  # durable receipt BEFORE any resolved operation
    campaigns=[]
    for campaign in bundle.campaigns:
        ads=tuple(replace(ad,creative_payload=effective(ad.creative_payload)) for ad in campaign.ads)
        campaigns.append(replace(campaign,ads=ads))
    return replace(bundle,campaigns=tuple(campaigns))


def verify_creative(actual,expected):
    if active_context() is None:return
    from .shein_reference import verify_degrees
    resolved=effective(expected)
    verify_degrees(actual.get('degrees_of_freedom_spec'),resolved['degrees_of_freedom_spec'])


def validate_activation_tree(tree):
    context=active_context()
    if context is None:return
    bound=context['descriptor']['reviewed_creative_features'];shell=bound['shells'][0]
    if tree['campaign'].get('id')!=shell['campaign_ids'][0] or tree['campaign'].get('account_id')!=bound['account_id']:
        raise ValueError('reviewed creative feature activation ownership mismatch')
    sets=tree['adsets'].get('data') or [];ads=tree['ads'].get('data') or []
    slots={str(a['source_ad_id']):a for a in context['state']['manifest']['campaigns'][0]['ads']}
    if (len(sets)!=1 or sets[0].get('id')!=shell['adset_ids'][0]
            or tree['adsets'].get('paging',{}).get('next') or tree['ads'].get('paging',{}).get('next')
            or len(ads)!=len(slots) or {str(a.get('source_ad_id')) for a in ads}!=set(slots)):
        raise ValueError('reviewed creative feature activation lineage/count mismatch')
    for ad in ads:
        if str(ad.get('adset_id'))!=shell['adset_ids'][0]:raise ValueError('reviewed creative feature ad parent mismatch')
        verify_creative(ad['creative'],slots[str(ad['source_ad_id'])]['creative_payload'])
