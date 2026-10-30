"""Typed, sealed review of exactly SHEIN IMG 008–015. No writes/repair.

The constants below are generated from fresh Discord GETs and completed core
receipts during maintenance; they are not user-configurable approval policy.
"""
from __future__ import annotations
import copy
from .shein_continuation import content_digest

KIND = 'shein-img-008-015-reviewed-targeting-v1'
# Frozen constants are inserted here by the maintenance build.


def binding(state, checkpoint):
    from .shein_reviewed_targeting import binding as base_binding
    result = base_binding(state, checkpoint)
    native = []
    for bundle in checkpoint['bundles']:
        rows = {r['name']: r['body'] for r in bundle['readback_results'] if r.get('code') == 200}
        for index, key in enumerate(bundle['idempotency_keys'], 1):
            campaign = rows['readback_campaign_' + str(index)]
            sets = rows['readback_adsets_' + str(index)]['data']
            if len(sets) != 1:
                raise ValueError('reviewed IMG native copy receipt cardinality mismatch')
            native.append({'key': key, 'campaign_id': campaign['id'],
                           'campaign_start_time': campaign['start_time'],
                           'adset_id': sets[0]['id'], 'adset_start_time': sets[0]['start_time'],
                           'copy_window': copy.deepcopy(bundle['timings']['adset_copy'])})
    return {**result, 'kind': KIND, 'resolved_request_digest': content_digest(state['resolved_request']),
            'source_campaign_digest': content_digest(state['source']['campaign']),
            'native_copy_schedule': native}


def require_binding(state, checkpoint, expected):
    from .prevalidation import verify_prevalidation
    actual = binding(state, checkpoint)
    if (actual != expected or content_digest(actual) != BINDING_DIGEST
            or checkpoint.get('status') != 'COMPLETE'
            or not all(verify_prevalidation(state[n]) for n in ['manifest', 'target_manifest'])):
        raise ValueError('reviewed IMG immutable binding/seal mismatch')
    return actual


def validate_review(descriptor, state, checkpoint, *, get_message):
    bound = require_binding(state, checkpoint, descriptor['reviewed_targeting'])
    if (descriptor.get('reviewed_targeting_kind') != KIND
            or descriptor.get('source_message_id') != ORIGINAL_ID
            or descriptor.get('source_message_content') != ORIGINAL_CONTENT
            or descriptor.get('source_thread_id') != ORIGIN
            or descriptor.get('authorized_by') != HUMAN
            or descriptor.get('late_activation_authorized') is not True
            or descriptor.get('recovery_review_thread_id') != ORIGIN
            or descriptor.get('recovery_review_message_id') != REVIEW_ID
            or descriptor.get('recovery_review_content') != REVIEW_CONTENT
            or descriptor.get('preserved_start_time') is not None
            or descriptor.get('reviewed_observed_copy_time') is not None):
        raise ValueError('reviewed IMG exact original/review descriptor required')
    messages = []
    for mid in MESSAGE_IDS:
        message = get_message('/channels/' + ORIGIN + '/messages/' + mid)
        projected = {k: message.get(k) for k in ['id', 'channel_id', 'content', 'timestamp', 'edited_timestamp', 'message_reference']}
        projected['author'] = {k: (message.get('author') or {}).get(k) for k in ['id', 'bot']}
        messages.append(projected)
    if content_digest(messages) != MESSAGES_DIGEST:
        raise ValueError('reviewed IMG exact Discord GET identity/content/reply mismatch')
    # The seal covers original -> question -> explanation link -> CEO reply.
    # This is separate evidence; never replace source_message_id in the request.
    from .shein_continuation import _authorize_late_reviewer
    authority = _authorize_late_reviewer(descriptor, state['request'], RODOLFO)
    return {'binding_digest': content_digest(bound), 'kind': KIND,
            'prompt_message_id': MESSAGE_IDS[1], 'context_message_id': MESSAGE_IDS[2],
            'review_message_id': REVIEW_ID, 'source_message_id': ORIGINAL_ID,
            'authority': authority, 'meta_writes': 0, 'manifest_mutations': 0}


def validate_fields(context, tree, slot):
    state = context['state']
    bound = context['descriptor']['reviewed_targeting']
    source_set = state['source']['adset']
    expected = copy.deepcopy(bound['source_targeting'])
    if (expected.get('user_age_unknown') is not False
            or expected['targeting_automation'].pop('individual_setting') != {'device': 1}):
        raise ValueError('reviewed IMG unexpected source age/device flags')
    expected['user_age_unknown'] = True
    actual = tree['adsets']['data'][0]
    if actual.get('targeting') != expected:
        raise ValueError('reviewed IMG additional targeting drift')
    specs = [c for c in state['manifest']['campaigns'] if c['idempotency_key'] == slot['key']]
    if len(specs) != 1:
        raise ValueError('reviewed IMG manifest slot mismatch')
    spec = specs[0]
    for field in ['attribution_spec', 'promoted_object', 'billing_event', 'optimization_goal', 'is_dynamic_creative']:
        if actual.get(field) != source_set.get(field):
            raise ValueError('reviewed IMG adset field drift')
    if spec.get('bid_override') is not True:
        raise ValueError('reviewed IMG sealed bid override missing')
    for field in ['bid_amount', 'bid_constraints']:
        observed = actual.get(field)
        wanted = spec['adset_updates'][field]
        if (str(observed or '0') != str(wanted) if field == 'bid_amount' else (observed or {}) != wanted):
            raise ValueError('reviewed IMG manifest bid drift')
    campaign = tree['campaign']
    for field, value in spec['campaign_updates'].items():
        if str(campaign.get(field)) != str(value):
            raise ValueError('reviewed IMG manifest budget/strategy drift')
    from .shein_copy_schedule import normalized_schedule_proof, _instant
    for node in [campaign, actual]:
        observed = node.get('start_time')
        if _instant(observed) != _instant(spec['start_time']) and normalized_schedule_proof(
                state, context['checkpoint'], request_id=bound['request_id'], account_id=bound['account_id'],
                campaign_id=campaign['id'], idempotency_key=slot['key'],
                expected=spec['start_time'], observed=observed) is None:
            raise ValueError('reviewed IMG native copy clock drift')
