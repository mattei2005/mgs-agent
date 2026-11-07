"""Request-scoped human acceptance of absent API enrollments, never toggles.
No Meta transport, creation, schedule mutation, source mutation or global waiver.
The runner and activate_verified keep ownership, media, tracking and ID checks.
"""
from __future__ import annotations
import copy,json,re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from .shein_continuation import content_digest

CURRENT: ContextVar[dict | None]=ContextVar('reviewed_copy_feature_omissions',default=None)
BASE=Path('/root/mgs-agent/data/ares/meta-ads')
POLICY_INDEX=BASE/'policies/reviewed-copy-feature-omissions.json'


def message_digest(m):
    return content_digest({**{k:m.get(k) for k in ['id','channel_id','content','edited_timestamp']},
        'author_id':(m.get('author') or {}).get('id'),'bot':bool((m.get('author') or {}).get('bot'))})


def binding(state,checkpoint):
    slots=[];specs={c['idempotency_key']:c for c in state['manifest']['campaigns']}
    for b in checkpoint.get('bundles',[]):
        if b.get('status')!='COMPLETE':raise ValueError('review requires complete creation checkpoint')
        rows={x['name']:x['body'] for x in b.get('readback_results',[]) if x.get('code')==200}
        for i,key in enumerate(b['idempotency_keys'],1):
            expected={x['source_ad_id']:x for x in specs[key]['ads']}
            edge=rows['readback_ads_'+str(i)]
            if not isinstance(edge.get('data'),list) or edge.get('paging',{}).get('next') or len(edge['data'])!=len(expected):
                raise ValueError('review requires full existing ad slot proof')
            from .creative_copy_policy import effective
            for ad in edge['data']:
                slot=expected[ad['source_ad_id']]
                slots.append({'key':key,'campaign_id':b['campaign_ids'][i-1],
                    'adset_id':ad['adset_id'],'ad_id':ad['id'],'creative_id':ad['creative']['id'],
                    'source_ad_id':ad['source_ad_id'],'effective_payload_digest':content_digest(effective(slot['creative_payload']))})
    if not slots or len({x['ad_id'] for x in slots})!=len(slots) or len({x['creative_id'] for x in slots})!=len(slots):
        raise ValueError('review exact existing identities ambiguous')
    return {'request_id':state['request']['request_id'],'request_digest':content_digest(state['request']),
        'account_id':checkpoint['account_id'],'creation_digest':content_digest(state['manifest']),
        'target_digest':content_digest(state['target_manifest']),'source_digest':content_digest(state['source']),
        'execution_started_at':state['execution_started_at'],'slots':sorted(slots,key=lambda x:x['ad_id'])}


def validate(receipt,state,checkpoint,*,get_message):
    index=json.loads(POLICY_INDEX.read_text()).get('requests',{})
    grant=index.get(state['request']['request_id']) or {}
    if (grant.get('receipt_digest')!=content_digest(receipt) or grant.get('approval_id')!=receipt.get('approval_id')
            or grant.get('account_id')!=checkpoint.get('account_id') or grant.get('approved_by')!='344196393512075265'):
        raise ValueError('review receipt not registered for this exact request/account/approval')
    if set(receipt)!={'schema_version','binding','accepted_omissions','prompt_id','approval_id','prompt_digest','approval_digest','approved_by','origin_id'} or receipt['schema_version']!=1:
        raise ValueError('review receipt fields invalid')
    if receipt['binding']!=binding(state,checkpoint):raise ValueError('review request/seals/IDs/source/clock changed')
    keys=receipt['accepted_omissions']
    if not isinstance(keys,list) or not keys or len(set(keys))!=len(keys) or 'image_background_gen' in keys:
        raise ValueError('review omissions must be exact distinct non-background fields')
    for c in state['manifest']['campaigns']:
        for ad in c['ads']:
            f=ad['creative_payload'].get('degrees_of_freedom_spec',{}).get('creative_features_spec',{})
            if any(f.get(k)!={'enroll_status':'OPT_IN'} for k in keys):raise ValueError('review source enrollment scope changed')
    origin=state['request']['source_thread_id']
    if receipt['origin_id']!=origin or receipt['approved_by']!='344196393512075265':raise ValueError('review exact CEO/origin required')
    prompt=get_message('/channels/'+origin+'/messages/'+receipt['prompt_id'])
    approval=get_message('/channels/'+origin+'/messages/'+receipt['approval_id'])
    if (prompt.get('channel_id')!=origin or approval.get('channel_id')!=origin
            or (prompt.get('author') or {}).get('id') not in {'1496296175014252634','1508864261504630925'}
            or not (prompt.get('author') or {}).get('bot')
            or (approval.get('author') or {}).get('id')!=receipt['approved_by']
            or (approval.get('author') or {}).get('bot') or approval.get('edited_timestamp')
            or prompt.get('edited_timestamp') or message_digest(prompt)!=receipt['prompt_digest']
            or message_digest(approval)!=receipt['approval_digest']):raise ValueError('review exact dialogue changed')
    history=get_message('/channels/'+origin+'/messages?before='+receipt['approval_id']+'&limit=100')
    if not isinstance(history,list) or not any(m.get('id')==receipt['prompt_id'] for m in history):raise ValueError('review prompt history unavailable')
    if any(int(m['id'])>int(receipt['prompt_id']) and not (m.get('author') or {}).get('bot') for m in history):
        raise ValueError('review intervening human decision ambiguous')
    return {'receipt':copy.deepcopy(receipt),'verified':True,'digest':content_digest(receipt)}


@contextmanager
def review_context(request):
    rid=str(request.get('request_id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}',rid):raise ValueError('review request identity invalid')
    directory=BASE/'state/shein-campaigns/single-clone'/rid
    path=directory/'reviewed-feature-omissions.json'
    if not path.exists():yield;return
    receipt=json.loads(path.read_text());state=json.loads((directory/'state.json').read_text())
    checkpoint=json.loads((BASE/'engine-v3/state/checkpoints'/(rid+'-'+receipt['binding']['account_id']+'.json')).read_text())
    from .shein_channel_authority import _get
    proof=validate(receipt,state,checkpoint,get_message=_get)
    marker=CURRENT.set(proof)
    try:yield
    finally:CURRENT.reset(marker)


def expected_degrees(actual,expected):
    proof=CURRENT.get()
    if proof is None:return expected.get('degrees_of_freedom_spec')
    receipt=proof['receipt']
    if proof.get('verified') is not True or proof['digest']!=content_digest(receipt):raise ValueError('review context invalid')
    matches=[s for s in receipt['binding']['slots'] if s['creative_id']==actual.get('id') and s['effective_payload_digest']==content_digest(expected)]
    if len(matches)!=1:raise ValueError('review creative/payload not in approved existing slots')
    desired=copy.deepcopy(expected.get('degrees_of_freedom_spec') or {})
    observed=(actual.get('degrees_of_freedom_spec') or {}).get('creative_features_spec') or {}
    wanted=desired.get('creative_features_spec') or {};accepted=set(receipt['accepted_omissions'])
    missing=set(wanted)-set(observed)
    if missing and missing!=accepted:raise ValueError('review omission set changed')
    for key in missing:
        if wanted[key]!={'enroll_status':'OPT_IN'}:raise ValueError('review cannot accept explicit enrollment change')
        del wanted[key]
    return desired


def warning():
    return ('CEO accepted unconfirmed API preservation only for the exact reviewed absent feature fields on these existing creative IDs; not literal feature fidelity and no extra opt-out applied' if CURRENT.get() else None)
