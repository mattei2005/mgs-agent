"""Scheduling-only evidence for an inert human review. Never a QA/approval waiver.

An explicit record pins the unmodified runner state and completed engine receipt.
Missing, changed or ambiguous evidence keeps the original account dependency.
Reservations and writer/account locks remain authoritative and are never released.
"""
from __future__ import annotations
import fcntl
import hashlib
import json
import re
from pathlib import Path

MEDIA_KEYS = {'asset_id', 'canonical_filename', 'checksum', 'clean_checksum',
              'clean_md5', 'asset_drive_id', 'drive_file_id', 'video_id',
              'vertical_video_id', 'square_video_id', 'image_hash', 'original_video_id'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_path(base, rid):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,150}', str(rid)):
        raise ValueError('invalid decision-wait request ID')
    return base / 'data/ares/meta-ads/state/shein-campaigns/queue/decision-waits' / (rid + '.json')


def _read(path):
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError('decision-wait evidence must be an object')
    return value


def _engine_root(base):
    config = _read(base / 'data/ares/meta-ads/engine-v3/config.json')
    path = Path(config['state_root'])
    return path if path.is_absolute() else base / path


def _media(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in MEDIA_KEYS and isinstance(item, str) and item:
                found.add((key if key in {'asset_id', 'canonical_filename'} else 'identity', item))
            found.update(_media(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_media(item))
    return found


def _unlocked(path):
    # Read-only probe; do not create missing files or unlink another owner's lock.
    with path.open('rb') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle, fcntl.LOCK_UN)
    return True


def evidence(base, value):
    """Validate only local pinned facts. No provider call or resource mutation."""
    request = value['request']; rid = request['request_id']; account = str(request['account'])
    rec = _read(record_path(base, rid))
    state_path = base / 'data/ares/meta-ads/state/shein-campaigns/single-clone' / rid / 'state.json'
    engine_root = _engine_root(base)
    checkpoint_path = engine_root / 'checkpoints' / (rid + '-' + account + '.json')
    checkpoint = _read(checkpoint_path)
    ids = value.get('engine_result', {}).get('campaign_ids') or []
    review = rec.get('review') or {}
    snapshots = rec.get('campaign_readback') or []
    if (rec.get('schema_version') != 1 or rec.get('classification') != 'WAITING_HUMAN_DECISION'
            or rec.get('request_id') != rid or rec.get('account_id') != account
            or rec.get('state_sha256') != digest(state_path)
            or rec.get('checkpoint_sha256') != digest(checkpoint_path)
            or value.get('phase') != 'POSTPROCESS_PENDING'
            or value.get('engine_result', {}).get('status') != 'COMPLETE_PAUSED'
            or value.get('engine_result', {}).get('request_id') != rid
            or value.get('summary') or value.get('qa_proof') or value.get('activation_result')
            or value.get('media_qa') or not ids or len(ids) != len(set(ids))
            or checkpoint.get('account_id') != account or checkpoint.get('status') != 'COMPLETE'
            or checkpoint.get('manual_reconciliation_required') is not False
            or set(checkpoint.get('campaign_ids') or []) != set(ids)
            or review.get('thread_id') != request.get('source_thread_id')
            or review.get('channel_id') != request.get('source_channel_id')
            or review.get('author_id') != '1508864261504630925'
            or not re.fullmatch(r'[0-9]{17,20}', str(review.get('message_id') or ''))
            or review.get('decision') != 'UNANSWERED'
            or review.get('material_difference') is not True
            or not rec.get('verified_at') or not rec.get('maintenance_task_id')
            or not rec.get('evidence_source')
            or len(snapshots) != len(ids) or {x.get('id') for x in snapshots} != set(ids)
            or any(x.get('account_id') != account or x.get('status') != 'PAUSED' for x in snapshots)):
        raise ValueError('decision-wait evidence mismatch; dependency retained')
    lease = _read(engine_root / 'writer-leases' / (account + '.json'))
    # A new writer, even a different owner, prevents exemption. Never release it.
    if (lease.get('account_id') != account or lease.get('status') != 'COMPLETE'
            or lease.get('blocks_readers') is not False or not lease.get('released_at_utc')):
        raise ValueError('decision-wait account writer lease is not released')
    return rec


def inert_for(request, value, selected_rows, base, *, held_accounts=frozenset()):
    """True only for an explicitly evidenced, disjoint-media, idle human wait."""
    try:
        evidence(base, value)
        origin = value['request']; account = str(origin['account']); owner = origin['request_id']
        if (request.get('source_channel_id') != origin.get('source_channel_id')
                or not selected_rows):
            return False
        lock = base / 'data/ares/meta-ads/state/shein-campaigns/single-clone' / ('account-' + account + '.lock')
        if account not in held_accounts and not _unlocked(lock):
            return False
        # Engine's persistent lease is checked above; its update lock must be idle too.
        if not _unlocked(_engine_root(base) / 'writer-leases' / (account + '.lock')):
            return False
        historical = _media(value)
        inventory = base / 'data/ares/creative-ops/inventory/assets.jsonl'
        campaign_ids = set(value['engine_result']['campaign_ids'])
        for line in inventory.read_text().splitlines():
            row = json.loads(line)
            if row.get('reservation_request_id') == owner or row.get('meta_campaign_id') in campaign_ids:
                historical.update(_media(row))
        if not historical:
            return False
        # Reservation guards in dependencies are independent; shared identity also blocks
        # when lineage differs or a historical reservation is no longer present.
        return not bool(historical & _media(selected_rows))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def pending(base, rid):
    """A pinned review must not be automatically retried as campaign execution."""
    path = record_path(base, rid)
    if not path.exists():
        return False
    # Any record, including stale/invalid evidence, is a fail-closed automatic hold.
    return True
