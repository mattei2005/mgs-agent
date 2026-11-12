"""Sealed, request-scoped acceptance of exact observed SHEIN targeting deltas.

No Meta writer, targeting mutation, manifest change or reusable account waiver.
Legacy reviews remain independent. Every review requires live channel authority.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from .shein_continuation import content_digest

KIND = 'shein-reviewed-copy-targeting-v1'
BASE = Path('/root/mgs-agent/data/ares/meta-ads')
POLICY_INDEX = BASE / 'policies/reviewed-copy-targeting.json'


def binding(state, checkpoint):
    from .shein_reviewed_targeting import binding as base_binding
    from .reviewed_copy_omissions import binding as media_binding
    return {**base_binding(state, checkpoint), 'kind': KIND,
            'media': media_binding(state, checkpoint)}


def require_binding(state, checkpoint, expected):
    from .prevalidation import verify_prevalidation
    actual = binding(state, checkpoint)
    if (actual != expected or checkpoint.get('status') != 'COMPLETE'
            or not all(verify_prevalidation(state[n]) for n in ['manifest', 'target_manifest'])):
        raise ValueError('reviewed copy targeting immutable binding/seal mismatch')
    return actual


def delta(source, observed):
    """Only explicit false->true unknown age and absent known suggestion flags."""
    a, b = copy.deepcopy(source), copy.deepcopy(observed)
    paths = []
    if a.get('user_age_unknown') is False and b.get('user_age_unknown') is True:
        paths.append('user_age_unknown')
        a['user_age_unknown'] = True
    af = a.get('targeting_automation', {}).get('individual_setting')
    bf = b.get('targeting_automation', {}).get('individual_setting')
    if isinstance(af, dict) and af and bf is None:
        if any(k not in {'age', 'gender', 'device'} or type(v) is not int or v != 1 for k, v in af.items()):
            raise ValueError('review unsupported suggestion delta')
        paths.extend('targeting_automation.individual_setting.' + k for k in sorted(af))
        del a['targeting_automation']['individual_setting']
    if a != b or not paths:
        raise ValueError('review unsupported or absent targeting delta')
    return sorted(paths)


def message_digest(message):
    from .reviewed_copy_omissions import message_digest as digest
    return digest(message)


def validate_review(descriptor, state, checkpoint, *, get_message):
    receipt = descriptor.get('targeting_review_receipt') or {}
    grant = json.loads(POLICY_INDEX.read_text()).get('requests', {}).get(state['request']['request_id'], {})
    if (descriptor.get('reviewed_targeting_kind') != KIND
            or grant.get('receipt_digest') != content_digest(receipt)
            or grant.get('approved_by') != receipt.get('approved_by')
            or grant.get('approval_id') != receipt.get('approval_id')
            or grant.get('account_id') != checkpoint.get('account_id')
            or grant.get('review_authority') != 'SHEIN_CHANNEL_POLICY'):
        raise ValueError('targeting review exact registered grant required')
    if (set(receipt) != {'schema_version', 'binding', 'approved_by', 'approval_id',
                         'prompt_id', 'dialogue', 'targeting_by_adset', 'accepted_paths'}
            or receipt.get('schema_version') != 1
            or receipt['binding'] != descriptor.get('reviewed_targeting')):
        raise ValueError('targeting review receipt fields invalid')
    bound = require_binding(state, checkpoint, receipt['binding'])
    original = state['request']
    if (state['manifest'].get('operation') != 'SHEIN-US-DIRECT'
            or receipt['approved_by'] != original['authorized_by']
            or descriptor.get('recovery_review_message_id') != receipt['approval_id']
            or descriptor.get('recovery_review_thread_id') != original['source_thread_id']
            or descriptor.get('late_activation_authorized') is not True):
        raise ValueError('targeting review exact original requester and origin required')
    ids = {s['adset_id'] for s in bound['slots']}
    if set(receipt['targeting_by_adset']) != ids:
        raise ValueError('targeting review exact adset coverage required')
    source = bound['source_targeting']
    for observed in receipt['targeting_by_adset'].values():
        if delta(source, observed) != receipt['accepted_paths']:
            raise ValueError('targeting review accepted delta set changed')
    from .shein_channel_authority import verify
    profiles = json.loads((BASE / 'operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles']
    profile = profiles[checkpoint['account_id']]
    if str(profile.get('account_id')) != str(checkpoint['account_id']):
        raise ValueError('targeting review profile account mismatch')
    if verify(original, profile, force=True).get('verified') is not True:
        raise ValueError('targeting review live channel authority unavailable')
    dialogue = receipt['dialogue']
    mids = [row.get('id') for row in dialogue]
    if (len(mids) != len(set(mids)) or not {receipt['prompt_id'], receipt['approval_id'], original['source_message_id']} <= set(mids)):
        raise ValueError('targeting review dialogue identity missing')
    origin = original['source_thread_id']
    approval = get_message('/channels/' + origin + '/messages/' + receipt['approval_id'])
    messages = {receipt['approval_id']: approval}
    history = []
    cursor = receipt['approval_id']
    needed = set(mids) - {receipt['approval_id']}
    for _ in range(20):
        page = get_message('/channels/' + origin + '/messages?before=' + cursor + '&limit=100')
        if not isinstance(page, list) or not page:
            raise ValueError('targeting review dialogue history incomplete')
        history.extend(page)
        for message in page:
            if message.get('id') in needed:
                messages[message['id']] = message
        if needed <= set(messages):
            break
        next_cursor = str(min(int(message['id']) for message in page))
        if int(next_cursor) >= int(cursor):
            raise ValueError('targeting review history cursor repeated')
        cursor = next_cursor
    else:
        raise ValueError('targeting review dialogue pagination bound exceeded')
    for row in dialogue:
        message = messages[row['id']]
        if (message.get('id') != row['id'] or message.get('channel_id') != origin
                or message.get('edited_timestamp') or message_digest(message) != row.get('digest')):
            raise ValueError('targeting review exact dialogue changed')
    prompt = messages[receipt['prompt_id']]
    if ((prompt.get('author') or {}).get('id') != '1508864261504630925'
            or not (prompt.get('author') or {}).get('bot')
            or (approval.get('author') or {}).get('id') != receipt['approved_by']
            or (approval.get('author') or {}).get('bot')
            or approval.get('content') != descriptor.get('recovery_review_content')
            or int(receipt['approval_id']) <= int(receipt['prompt_id'])):
        raise ValueError('targeting review prompt/approval identity invalid')
    if not isinstance(history, list) or not any(m.get('id') == receipt['prompt_id'] for m in history):
        raise ValueError('targeting review prompt history unavailable')
    if any(int(m['id']) > int(receipt['prompt_id']) and not (m.get('author') or {}).get('bot') for m in history):
        raise ValueError('targeting review intervening human decision ambiguous')
    return {'kind': KIND, 'binding_digest': content_digest(bound), 'receipt_digest': content_digest(receipt),
            'prompt_message_id': receipt['prompt_id'], 'review_message_id': receipt['approval_id'],
            'meta_writes': 0, 'manifest_mutations': 0}


def validate_fields(context, tree, slot):
    receipt = context['descriptor']['targeting_review_receipt']
    bound = receipt['binding']
    actual = tree['adsets']['data'][0]
    if actual.get('targeting') != receipt['targeting_by_adset'].get(slot['adset_id']):
        raise ValueError('targeting review additional targeting drift')
    state = context['state']
    source = state['source']['adset']
    specs = [c for c in state['manifest']['campaigns'] if c['idempotency_key'] == slot['key']]
    if len(specs) != 1:
        raise ValueError('targeting review exact manifest slot required')
    spec = specs[0]
    for field in ['attribution_spec', 'promoted_object', 'billing_event', 'optimization_goal', 'is_dynamic_creative']:
        if actual.get(field) != source.get(field):
            raise ValueError('targeting review non-targeting adset field drift')
    bids = spec.get('adset_updates') if spec.get('bid_override') is True else source
    for field in ['bid_amount', 'bid_constraints']:
        if field in bids:
            a, b = actual.get(field), bids[field]
            equal = str(a or '0') == str(b) if field == 'bid_amount' else (a or {}) == b
            if not equal:
                raise ValueError('targeting review bid drift')
    for field, expected in spec.get('campaign_updates', {}).items():
        if str(tree['campaign'].get(field)) != str(expected):
            raise ValueError('targeting review campaign budget/strategy drift')
    media = bound['media']['slots']
    by_id = {s['ad_id']: s for s in media if s['campaign_id'] == tree['campaign']['id']}
    ads = tree['ads']['data']
    if {a['id'] for a in ads} != set(by_id) or any((a.get('creative') or {}).get('id') != by_id[a['id']]['creative_id'] for a in ads):
        raise ValueError('targeting review exact creative identity drift')
