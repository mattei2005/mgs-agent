"""Approved missing-only ad recreation for an inherited immutable ad schedule.
No transport of its own; no source, manifest, schedule or QA mutation.
Default paths remain native copies. Approval is request/account/slot-bound.
"""
from __future__ import annotations
import copy
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from .shein_continuation import content_digest
from .reviewed_copy_omissions import message_digest
from .transport import BatchOperation

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
CURRENT = ContextVar('reviewed_ad_schedule_recreation', default=None)


def binding(state, initial_objects):
    return {
        'request_id': state['request']['request_id'],
        'account_id': str(state['request']['account']),
        'request_digest': content_digest(state['request']),
        'creation_digest': content_digest(state['manifest']),
        'target_digest': content_digest(state['target_manifest']),
        'source_digest': content_digest(state['source']),
        'execution_started_at': state['execution_started_at'],
        'initial_objects': copy.deepcopy(initial_objects),
    }


def validate(receipt, state, checkpoint, *, get_message, verify_authority):
    if set(receipt) != {'schema_version', 'binding', 'source_ad_ids', 'review'} or receipt['schema_version'] != 1:
        raise ValueError('ad schedule review schema invalid')
    bound = receipt['binding']
    if bound != binding(state, bound['initial_objects']):
        raise ValueError('ad schedule review request/source/seals/clock changed')
    if checkpoint.get('account_id') != bound['account_id']:
        raise ValueError('ad schedule review account changed')
    from .prevalidation import verify_prevalidation
    if not all(verify_prevalidation(state[k]) for k in ('manifest', 'target_manifest')):
        raise ValueError('ad schedule review requires sealed manifests')
    if state['manifest']['operation'] != 'SHEIN-US-DIRECT':
        raise ValueError('ad schedule review operation invalid')
    wanted = receipt['source_ad_ids']
    source_ids = {a['id'] for a in state['source']['ads']}
    if not isinstance(wanted, list) or not wanted or len(set(wanted)) != len(wanted) or not set(wanted) <= source_ids:
        raise ValueError('ad schedule review source identity invalid')
    for field in ('campaign_ids', 'adset_ids'):
        current = {v for b in checkpoint.get('bundles', []) for v in b.get(field, [])}
        if not set(bound['initial_objects'].get(field, [])) <= current:
            raise ValueError('ad schedule review lost initial shells')
    confirmed = {str(v) for b in checkpoint.get('bundles', []) for ids in b.get('confirmed_objects', {}).values() for v in ids.values() if isinstance(v, (str, int))}
    if not set(bound['initial_objects'].get('ad_ids', [])) <= confirmed:
        raise ValueError('ad schedule review lost confirmed ads')
    for creation, target in zip(state['manifest']['campaigns'], state['target_manifest']['campaigns']):
        if creation['mode'] != 'pure_clone' or creation['status'] != 'PAUSED' or target['status'] != 'ACTIVE':
            raise ValueError('ad schedule recreation requires paused pure clone and approved activation')
        if creation['idempotency_key'] != target['idempotency_key']:
            raise ValueError('ad schedule review slot changed')
    review = receipt['review']
    req = state['request']
    if review['approved_by'] != req['authorized_by'] or review['origin_id'] != req['source_thread_id']:
        raise ValueError('ad schedule review origin/actor invalid')
    prompt = get_message('/channels/' + review['origin_id'] + '/messages/' + review['prompt_id'])
    approval = get_message('/channels/' + review['origin_id'] + '/messages/' + review['approval_id'])
    if (prompt.get('channel_id') != review['origin_id'] or approval.get('channel_id') != review['origin_id']
            or (prompt.get('author') or {}).get('id') != '1508864261504630925'
            or not (prompt.get('author') or {}).get('bot')
            or (approval.get('author') or {}).get('id') != review['approved_by']
            or (approval.get('author') or {}).get('bot') or prompt.get('edited_timestamp') or approval.get('edited_timestamp')
            or message_digest(prompt) != review['prompt_digest'] or message_digest(approval) != review['approval_digest']
            or approval.get('content', '').strip().casefold() not in {'autorizo', 'sim', 'pode continuar', 'pode seguir'}):
        raise ValueError('ad schedule exact review dialogue changed')
    history = get_message('/channels/' + review['origin_id'] + '/messages?before=' + review['approval_id'] + '&limit=100')
    if not isinstance(history, list) or not any(x.get('id') == review['prompt_id'] for x in history):
        raise ValueError('ad schedule review history unavailable')
    if any(int(x['id']) > int(review['prompt_id']) and not (x.get('author') or {}).get('bot') for x in history):
        raise ValueError('ad schedule review intervening decision ambiguous')
    if verify_authority(req).get('verified') is not True:
        raise ValueError('ad schedule review live authority unavailable')
    return {'verified': True, 'receipt': copy.deepcopy(receipt), 'state': state, 'checkpoint': checkpoint}


@contextmanager
def lane_context(request_id, account_id, manifest_digest):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', request_id):
        raise ValueError('ad schedule review request ID invalid')
    directory = BASE / 'state/shein-campaigns/single-clone' / request_id
    path = directory / 'reviewed-ad-schedule-recreation.json'
    if not path.exists():
        yield
        return
    receipt = json.loads(path.read_text())
    state = json.loads((directory / 'state.json').read_text())
    checkpoint = json.loads((BASE / 'engine-v3/state/checkpoints' / (request_id + '-' + account_id + '.json')).read_text())
    from .schema import Manifest
    if receipt['binding']['account_id'] != account_id or Manifest.from_dict(state['manifest']).digest != manifest_digest:
        raise ValueError('ad schedule lane identity changed')
    from .shein_channel_authority import _get, verify
    profiles = json.loads((BASE / 'operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles']
    proof = validate(receipt, state, checkpoint, get_message=_get,
                     verify_authority=lambda req: verify(req, profiles[account_id], force=True))
    marker = CURRENT.set(proof)
    try:
        yield
    finally:
        CURRENT.reset(marker)


def prepare(bundle, operations, stage):
    proof = CURRENT.get()
    if proof is None or stage not in {'existing_post_copy_and_creative', 'existing_post_recovery_materialize'}:
        return operations
    if proof.get('verified') is not True or bundle.account_id != proof['receipt']['binding']['account_id']:
        raise ValueError('ad schedule recreation context invalid')
    definitions = {c['idempotency_key']: c for c in proof['state']['manifest']['campaigns']}
    for campaign in bundle.campaigns:
        if campaign.idempotency_key not in definitions or campaign.status != 'PAUSED':
            raise ValueError('ad schedule recreation unapproved campaign')
    from . import progress
    current = progress.CURRENT.get()
    if current is None:
        raise ValueError('ad schedule recreation requires durable central journal')
    record = current[0]
    result = []
    remaining = list(operations)
    while remaining:
        op = remaining.pop(0)
        match = re.fullmatch(r'existing_post_(?:recovery_)?ad_copy_(\d+)_(\d+)', op.name)
        if match is None:
            result.append(op)
            continue
        ci, ai = map(int, match.groups())
        campaign = bundle.campaigns[ci-1]
        ad = campaign.ads[ai-1]
        if ad.source_ad_id not in proof['receipt']['source_ad_ids']:
            result.append(op)
            continue
        expected = definitions[campaign.idempotency_key]['ads'][ai-1]
        from .creative_copy_policy import effective
        if (op.relative_url != ad.source_ad_id + '/copies' or op.method != 'POST'
                or op.body.get('status_option') != 'PAUSED'
                or content_digest(ad.creative_payload) != content_digest(effective(expected['creative_payload']))):
            raise ValueError('ad schedule recreation operation/payload changed')
        creative_id = (record.get('existing_post_creative_ids') or {}).get(f'{ci}.{ai}')
        depends_on = None
        if not creative_id:
            names = {f'existing_post_creative_{ci}_{ai}', f'existing_post_recovery_creative_{ci}_{ai}'}
            matches = [x for x in remaining if x.name in names and x.kind == 'creative_create']
            if len(matches) != 1:
                raise ValueError('ad schedule recreation lacks unique approved creative')
            creative_op = matches[0]
            remaining.remove(creative_op)
            result.append(creative_op)
            creative_id = '{result=' + creative_op.name + ':$.id}'
            depends_on = creative_op.name
        result.append(BatchOperation(op.name, 'POST', 'act_' + bundle.account_id + '/ads',
            body={'name': ad.name, 'adset_id': op.body['adset_id'], 'source_ad_id': ad.source_ad_id,
                  'creative': {'creative_id': creative_id}, 'status': 'PAUSED'},
            depends_on=depends_on, kind='ad_create'))
    return result


def verify_results(bundle, rows):
    proof = CURRENT.get()
    if proof is None:
        return
    for row in rows:
        if not re.fullmatch(r'readback_ads_\d+', row.name):
            continue
        edge = row.body
        if not isinstance(edge.get('data'), list) or edge.get('paging', {}).get('next'):
            raise ValueError('ad schedule final edge incomplete')
        for ad in edge['data']:
            if ad.get('source_ad_id') in proof['receipt']['source_ad_ids']:
                if ad.get('ad_schedule_start_time') or ad.get('ad_schedule_end_time'):
                    raise ValueError('recreated ad retained individual schedule')
