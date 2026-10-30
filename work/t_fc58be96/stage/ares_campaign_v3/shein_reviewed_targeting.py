"""One human-reviewed device omission, bound to existing SHEIN 004/005 only.

No policy relaxation, Meta transport, state mutation or writer in this module.
The frozen digest is a maintenance seal, NOT a reusable approval mechanism.
"""
from __future__ import annotations
import copy
from .shein_continuation import content_digest

BINDING_DIGEST = '193a5d83ca684017367c5102458fb913c124da80f35557fc4ae790cf93c07403'
ARES = '1508864261504630925'
HUMAN = '1055570806945620030'
ORIGIN = '1558134703565967394'
ORIGINAL_ID = '1565261967260647536'
ORIGINAL = 'uplique 2 vezes as campanhas 1  e 3 \norcamento de 35 dolares e rodar para as 4 am.  10/29/2026'
NOW_ID = '1565337558236274759'
NOW = 'Pode manter o pedido original e colocar para ativar agora'
PROMPT_ID = '1565337945496358922'
PROMPT = ('Nicolas, mantive o pedido: **2 cópias da campanha 1 e 2 da campanha 3, US$35/dia cada**, com sua autorização para ativar agora.\n\n'
          'Revalidei na Meta: a diferença de segmentação por dispositivo continua nas **004 e 005**, que permanecem pausadas. As duas cópias da campanha 3 ainda estão pendentes.\n\n'
          'Sua autorização resolve o horário, mas preciso confirmar essa diferença: **você aceita que as cópias da campanha 1 sejam ativadas sem a opção de dispositivo que a Meta não preservou?** A original não será alterada.')
REVIEW_ID = '1565338124400336978'
REVIEW = 'Sim'


def binding(state, checkpoint):
    """Immutable projection; excludes mutable phase/QA, never manifests or clock."""
    source = state['source']
    slots = []
    for bundle in checkpoint['bundles']:
        if bundle['status'] != 'COMPLETE':
            raise ValueError('reviewed targeting requires completed existing copy provenance')
        rows = {r['name']: r['body'] for r in bundle['readback_results'] if r.get('code') == 200}
        for i, key in enumerate(bundle['idempotency_keys'], 1):
            ads = rows['readback_ads_' + str(i)]['data']
            slots.append({'key': key, 'campaign_id': bundle['campaign_ids'][i-1],
                          'adset_id': bundle['adset_ids'][i-1],
                          'ads': sorted([{'id': a['id'], 'source_ad_id': a['source_ad_id'],
                                          'adset_id': a['adset_id']} for a in ads], key=lambda a: a['id'])})
        if sorted(a['id'] for slot in slots[-len(bundle['idempotency_keys']):] for a in slot['ads']) != sorted(bundle['ad_ids']):
            raise ValueError('reviewed targeting ad receipt mismatch')
    return {'request_digest': content_digest(state['request']),
            'request_id': state['request']['request_id'], 'account_id': checkpoint['account_id'],
            'account': {k: state['account'].get(k) for k in ['id', 'currency', 'timezone_name']},
            'execution_started_at': state['execution_started_at'],
            'creation_digest': content_digest(state['manifest']),
            'target_digest': content_digest(state['target_manifest']),
            'creation_seal': state['manifest']['prevalidation']['content_digest'],
            'target_seal': state['target_manifest']['prevalidation']['content_digest'],
            'source_campaign_id': source['campaign']['id'], 'source_adset_id': source['adset']['id'],
            'source_adset_digest': content_digest(source['adset']),
            'source_targeting': copy.deepcopy(source['adset']['targeting']), 'slots': slots}


def require_binding(state, checkpoint, expected, *, kind=None):
    if kind is not None:
        from . import shein_reviewed_img as img
        if kind != img.KIND:
            raise ValueError('unknown reviewed targeting kind')
        return img.require_binding(state, checkpoint, expected)
    from .prevalidation import verify_prevalidation
    actual = binding(state, checkpoint)
    if (content_digest(actual) != BINDING_DIGEST or actual != expected
            or not all(verify_prevalidation(state[n]) for n in ['manifest', 'target_manifest'])
            or checkpoint.get('status') != 'COMPLETE'):
        raise ValueError('reviewed targeting immutable binding/seal mismatch')
    return actual


def validate_review(descriptor, state, checkpoint, *, get_message):
    accepted = descriptor.get('reviewed_targeting')
    if accepted is None:
        return None
    kind = descriptor.get('reviewed_targeting_kind')
    if kind is not None:
        from . import shein_reviewed_img as img
        if kind != img.KIND:
            raise ValueError('unknown reviewed targeting kind')
        return img.validate_review(descriptor, state, checkpoint, get_message=get_message)
    bound = require_binding(state, checkpoint, accepted)
    if (descriptor.get('source_message_id') != NOW_ID or descriptor.get('source_message_content') != NOW
            or descriptor.get('source_thread_id') != ORIGIN or descriptor.get('authorized_by') != HUMAN):
        raise ValueError('reviewed targeting requires exact original immediate activation approval')
    for mid, text, actor, bot in [(ORIGINAL_ID, ORIGINAL, HUMAN, False), (NOW_ID, NOW, HUMAN, False),
                                  (PROMPT_ID, PROMPT, ARES, True), (REVIEW_ID, REVIEW, HUMAN, False)]:
        message = get_message('/channels/' + ORIGIN + '/messages/' + mid)
        if (message.get('id') != mid or message.get('channel_id') != ORIGIN
                or (message.get('author') or {}).get('id') != actor
                or bool((message.get('author') or {}).get('bot')) != bot
                or message.get('content') != text or message.get('edited_timestamp')):
            raise ValueError('reviewed targeting exact Discord GET identity/content mismatch')
    previous = get_message('/channels/' + ORIGIN + '/messages?before=' + REVIEW_ID + '&limit=100')
    if (not isinstance(previous, list) or not any(m.get('id') == PROMPT_ID for m in previous)
            or any(int(m.get('id', 0)) > int(PROMPT_ID) and not (
                (m.get('author') or {}).get('id') == ARES and (m.get('author') or {}).get('bot')
                and m.get('content', '').startswith('💾 Self-improvement review:')) for m in previous)):
        raise ValueError('reviewed targeting affirmative answer context ambiguous')
    from .shein_continuation import _authorize_late_reviewer
    authority = _authorize_late_reviewer({**descriptor, 'recovery_review_thread_id': ORIGIN}, state['request'], HUMAN)
    return {'binding_digest': BINDING_DIGEST, 'prompt_message_id': PROMPT_ID, 'review_message_id': REVIEW_ID,
            'source_message_id': ORIGINAL_ID, 'immediate_message_id': NOW_ID,
            'authority': authority, 'meta_writes': 0, 'manifest_mutations': 0}


def active_context():
    from .shein_continuation import APPROVED_RESUME
    context = APPROVED_RESUME.get()
    if context is None or (context.get('verified') or {}).get('accepted_targeting') is None:
        return None
    verified = context['verified']
    kind = context['descriptor'].get('reviewed_targeting_kind')
    from . import shein_reviewed_img as img
    seal = img.BINDING_DIGEST if kind == img.KIND else BINDING_DIGEST
    if (verified.get('verified') is not True or verified['accepted_targeting']['binding_digest'] != seal
            or content_digest(context['descriptor']) != verified['descriptor_digest']):
        raise ValueError('reviewed targeting continuation proof invalid')
    require_binding(context['state'], context['checkpoint'], context['descriptor']['reviewed_targeting'], kind=kind)
    return context


def validate_tree(context, tree):
    """Used for semantic QA AND fresh activation pre-read/readback."""
    bound = context['descriptor']['reviewed_targeting']
    campaign = tree['campaign']
    slots = [s for s in bound['slots'] if s['campaign_id'] == campaign['id']]
    if len(slots) != 1 or campaign.get('account_id') != bound['account_id']:
        raise ValueError('reviewed targeting campaign/account mismatch')
    slot = slots[0]
    sets = tree['adsets'].get('data') or []
    ads = tree['ads'].get('data') or []
    if (tree['adsets'].get('paging', {}).get('next') or tree['ads'].get('paging', {}).get('next')
            or len(sets) != 1 or sets[0].get('id') != slot['adset_id']
            or sorted([{'id': a.get('id'), 'source_ad_id': a.get('source_ad_id'),
                         'adset_id': a.get('adset_id')} for a in ads], key=lambda a: str(a['id'])) != slot['ads']):
        raise ValueError('reviewed targeting exact child IDs/lineage mismatch')
    for node in sets + ads:
        if (node.get('account_id', bound['account_id']) != bound['account_id']
                or node.get('campaign_id', campaign['id']) != campaign['id']):
            raise ValueError('reviewed targeting parent/account mismatch')
    if context['descriptor'].get('reviewed_targeting_kind') is not None:
        from . import shein_reviewed_img as img
        if context['descriptor']['reviewed_targeting_kind'] != img.KIND:
            raise ValueError('unknown reviewed targeting kind')
        return img.validate_fields(context, tree, slot)
    expected = copy.deepcopy(bound['source_targeting'])
    if expected['targeting_automation'].pop('individual_setting') != {'age': 1, 'gender': 1, 'device': 1}:
        raise ValueError('reviewed targeting unexpected source flags')
    if sets[0].get('targeting') != expected:
        raise ValueError('reviewed targeting additional targeting drift')
    source_set = context['state']['source']['adset']
    for field in ['attribution_spec', 'promoted_object', 'billing_event', 'optimization_goal', 'is_dynamic_creative', 'bid_amount', 'bid_constraints']:
        if sets[0].get(field) != source_set.get(field):
            raise ValueError('reviewed targeting adset field/bid drift')


def allows(payload, source, tree):
    context = active_context()
    if context is None:
        return False
    state = context['state']
    if (source['campaign']['id'] != state['source']['campaign']['id']
            or content_digest(source['adset']) != content_digest(state['source']['adset'])):
        raise ValueError('reviewed targeting source mismatch')
    candidates = [{**state[n], 'campaigns': [c]} for n in ['manifest', 'target_manifest'] for c in state[n]['campaigns']]
    if payload not in candidates:
        raise ValueError('reviewed targeting manifest/slot mismatch')
    validate_tree(context, tree)
    key = payload['campaigns'][0]['idempotency_key']
    if not any(s['key'] == key and s['campaign_id'] == tree['campaign']['id'] for s in context['descriptor']['reviewed_targeting']['slots']):
        raise ValueError('reviewed targeting slot/campaign mismatch')
    return True


def validate_activation_tree(tree):
    context = active_context()
    if context is not None:
        validate_tree(context, tree)
