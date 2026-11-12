"""Fail-closed elapsed target-clone admission, not a new scheduling policy.

A maintenance-installed, hash-pinned receipt binds the existing request, sealed
manifest and journal prefix. Live human NOW/seed approval and the unchanged Meta
identity are read again on every delivery attempt. The adapter independently
proves the full existing hierarchy before its first missing-only mutation.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

CURRENT = ContextVar('target_clone_elapsed_admission', default=None)
MODE = 'clone_target_prestaged'
OPERATION = 'Eggbev-US-CC-EN-BOT'

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def expired(payload):
    return any(c.get('status') == 'ACTIVE' and datetime.fromisoformat(c['start_time']) <= datetime.now(timezone.utc) for c in payload.get('campaigns', []))

def slots(campaigns):
    result = {}
    for ci, c in enumerate(campaigns, 1):
        result[f'campaign_create_{ci}'] = f'campaign_id_{ci}'
        result[f'adset_create_{ci}'] = f'adset_id_{ci}'
        for ai, _ in enumerate(c['ads'], 1):
            for operation, slot in [('creative_create','creative_id'), ('target_seed_create','seed_ad_id'), ('target_same_page_copy','copied_ad_id')]:
                result[f'{operation}_{ci}_{ai}'] = f'{slot}_{ci}_{ai}'
    return result

def validate_record(payload, record):
    """Every skip is backed by the exact sealed operation's durable receipt."""
    from .target_page_clone import stages, _resolve, _result_id
    from .schema import CampaignSpec
    mapping = slots(payload['campaigns'])
    # The shared journal also caches GET response IDs. Only creation receipts
    # can authorize skipping a mutation; readback IDs are not new write slots.
    confirmed = {k:v for k,v in record.get('confirmed_objects', {}).items() if k in mapping}
    ids = {mapping[name]: _result_id(row) for name, row in confirmed.items()}
    if any(re.fullmatch(r'[1-9][0-9]+', v) is None for v in ids.values()) or len(set(ids.values())) != len(ids):
        raise ValueError('continuation has invalid or duplicate IDs')
    if any(ids.get(k) != v for k, v in record.get('target_clone_ids', {}).items()):
        raise ValueError('continuation persisted IDs conflict with confirmed receipts')
    # Parsing happens only inside the narrow admission context, not via a
    # caller-supplied skip-future flag.
    candidates = tuple(CampaignSpec.from_dict(c) for c in payload['campaigns'])
    templates = {op.name: op for stage in stages(candidates) for op in stage.operations}
    for entry in record.get('write_journal', []):
        for row in entry.get('confirmed', []):
            name = row['name']
            if name in confirmed and row.get('ids') != confirmed[name]:
                raise ValueError('continuation conflicting object receipts')
        for operation in entry.get('operations', []):
            name = operation['name']
            # A QA containment status write is separate from the creation plan.
            if name.startswith('target_qa_hold_'):
                continue
            template = templates.get(name)
            if template is None:
                raise ValueError('continuation journal operation not in sealed plan')
            body = _resolve(template.body, ids)
            expected = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            if operation.get('method') != 'POST' or operation.get('path') != _resolve(template.relative_url, ids) or operation.get('body_digest') != expected:
                raise ValueError('continuation journal operation digest mismatch')
    for name in set(confirmed) | set(record.get('target_clone_completed_steps', [])):
        matching = [entry for entry in record.get('write_journal', []) if any(o.get('name') == name for o in entry.get('operations', []))]
        if not matching or not any((entry.get('state') == 'CONFIRMED' if name not in confirmed else any(r.get('name') == name and r.get('ids') == confirmed[name] for r in entry.get('confirmed', []))) for entry in matching):
            raise ValueError('continuation skipped operation lacks durable success receipt')
    if record.get('campaign_ids') != [ids.get('campaign_id_1')] or record.get('adset_ids') != [ids.get('adset_id_1')]:
        raise ValueError('continuation shell lists differ from confirmed IDs')
    return ids

def validate_local(path, payload, config):
    from .prevalidation import verify_prevalidation
    path = Path(path).resolve()
    q = load(path)
    rid, aid = q.get('request_id'), q.get('account_id')
    account = (config.get('accounts') or {}).get(aid) or {}
    capability = account.get('target_page_replacement') or {}
    binding = (capability.get('continuations') or {}).get(rid) or {}
    root = Path(config['state_root']).resolve()
    receipt_path = root / 'target-continuations' / f'{rid}-{aid}.json'
    if (not isinstance(rid, str) or re.fullmatch(r'[A-Za-z0-9_.-]{8,120}', rid) is None
            or not isinstance(aid, str) or re.fullmatch(r'[1-9][0-9]+', aid) is None
            or binding.get('receipt_path') != str(receipt_path)
            or not receipt_path.is_file() or binding.get('sha256') != file_digest(receipt_path)):
        raise ValueError('elapsed target request has no installed exact continuation receipt')
    receipt = load(receipt_path)
    if (capability.get('enabled') is not True or capability.get('account_id') != aid
            or capability.get('authorized_by') != '344196393512075265'
            or capability.get('authority_message_id') != '1569927267633602693'
            or MODE not in account.get('supported_modes', [])
            or rid not in account.get('campaign_policy', {}).get('immediate_start_request_ids', [])
            or receipt.get('request_id') != rid or receipt.get('account_id') != aid
            or receipt.get('request_path') != str(path) or receipt.get('request_sha256') != file_digest(path)
            or receipt.get('manifest_digest') != digest(payload) or not verify_prevalidation(payload)
            or payload.get('request_id') != rid or payload.get('operation') != OPERATION
            or q.get('operation') != OPERATION or account.get('operation') != OPERATION
            or receipt.get('authorized_by') != q.get('requested_by_discord_id')
            or receipt.get('authorized_by') not in {'1055570806945620030','344196393512075265'}
            or len(payload.get('campaigns', [])) != 1):
        raise ValueError('continuation identity, authority, allowlist or sealed digest mismatch')
    c = payload['campaigns'][0]
    if (c.get('mode') != MODE or c.get('account_id') != aid or c.get('status') != 'ACTIVE'
            or c.get('app_key') != account.get('app_key') or c.get('start_time') != q.get('start_time')
            or receipt.get('account_identity') != {k: account.get(k) for k in ['app_key','meta_app_id','token_item','token_identity']}
            or q.get('final_publication_approval', {}).get('immediate_requested') is not True
            or q.get('final_publication_approval', {}).get('technical_seeds_preserved') is not True):
        raise ValueError('continuation is not the approved existing NOW target intent')
    for name, expected in receipt.get('files', {}).items():
        if Path(name).name != name or file_digest(path.parent / name) != expected:
            raise ValueError('continuation original execution receipt changed')
    approval = load(path.parent / 'final-approval.json')
    if approval != {'message_id': receipt['approval_message_id'], 'approved_digest': payload['prevalidation']['content_digest']}:
        raise ValueError('continuation final digest approval mismatch')
    intent=q['final_publication_approval']
    if (receipt['approval_message_id']!=intent.get('message_id')
            or receipt.get('now_message_id')!=intent.get('schedule_change_message_id')
            or {m['id'] for m in receipt.get('messages',[])}!={receipt['approval_message_id'],receipt['now_message_id'],receipt['prompt_message_id']}
            or len(receipt['messages'])!=3):
        raise ValueError('continuation NOW/final/seed explanation coverage mismatch')
    checkpoint = load(root / 'checkpoints' / f'{rid}-{aid}.json')
    audit = load(Path(config['audit_root']) / f'{rid}.json')
    records = checkpoint.get('bundles', [])
    if (checkpoint.get('account_id') != aid or len(records) != 1
            or records[0].get('idempotency_keys') != [c['idempotency_key']]
            or records[0].get('sealed_manifest_digest') != digest(payload)
            or audit.get('request_id') != rid or audit.get('operation') != OPERATION
            or audit.get('manifest_digest') != digest(payload)):
        raise ValueError('continuation existing checkpoint/audit not bound to manifest')
    record = records[0]
    count = receipt['journal_prefix_count']
    if not count or digest(record.get('write_journal', [])[:count]) != receipt['journal_prefix_digest']:
        raise ValueError('continuation original journal changed')
    if any(record.get('confirmed_objects', {}).get(k) != v for k,v in receipt['confirmed_objects'].items()):
        raise ValueError('continuation original confirmed IDs changed')
    if not {'campaign_create_1', 'adset_create_1'} <= set(receipt['confirmed_objects']):
        raise ValueError('continuation requires both existing confirmed shells')
    return {'payload': copy.deepcopy(payload), 'receipt': receipt, 'record': record, 'config': config,
            'request': q, 'verified_at': time.monotonic()}

@contextmanager
def admission(path, payload, config, *, meta, token, get_message=None):
    context = validate_local(path, payload, config)
    receipt = context['receipt']; q = context['request']
    if get_message is None:
        from .shein_channel_authority import _get
        get_message = _get
    for evidence in receipt['messages']:
        message = get_message('/channels/' + q['source_thread_id'] + '/messages/' + evidence['id'])
        if (message.get('id') != evidence['id'] or message.get('channel_id') != q['source_thread_id']
                or message.get('author', {}).get('id') != evidence['author_id']
                or bool(message.get('author', {}).get('bot')) != evidence['bot']
                or evidence['author_id'] != ('1508864261504630925' if evidence['id']==receipt['prompt_message_id'] else receipt['authorized_by'])
                or evidence['bot'] != (evidence['id']==receipt['prompt_message_id'])
                or digest(message.get('content')) != evidence['content_digest']):
            raise ValueError('continuation live NOW/final approval changed or unavailable')
    code, identity, _ = meta.graph_get_credential_metadata(q['account_id'], token)
    issuer_code, issuer, _ = meta.graph_get_credential_metadata(q['account_id'], token, inspect_token=True)
    issuer = issuer.get('data') or {}
    if (code != 200 or identity.get('id') != receipt['meta_actor_id'] or issuer_code != 200
            or issuer.get('is_valid') is not True or str(issuer.get('user_id')) != receipt['meta_actor_id']
            or str(issuer.get('app_id')) != context['config']['accounts'][q['account_id']]['meta_app_id']):
        raise ValueError('continuation advertiser identity/app changed or unavailable')
    context['verified_at'] = time.monotonic()
    marker = CURRENT.set(context)
    try:
        context['ids'] = validate_record(payload, context['record'])
        yield context
    finally:
        CURRENT.reset(marker)

def allows_elapsed_campaign(value):
    context = CURRENT.get()
    return bool(context and time.monotonic() - context['verified_at'] <= 120
                and value in context['payload']['campaigns'])

def require_execution(manifest):
    if manifest.operation != OPERATION or not expired(manifest.raw):
        return
    if any(c.mode == MODE for c in manifest.campaigns):
        context = CURRENT.get()
        if not context or not all(allows_elapsed_campaign(c) for c in manifest.raw['campaigns']) or digest(manifest.raw) != context['receipt']['manifest_digest']:
            raise ValueError('elapsed target execute requires fresh exact verified continuation admission')
