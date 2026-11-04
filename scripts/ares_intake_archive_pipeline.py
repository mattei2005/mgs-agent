#!/usr/bin/env python3
"""Deterministic mechanical continuation of one already-treated Ares batch.

Caller holds intake-state lock. Owner credentials remain isolated in the existing
bounded subprocesses; all publishers use the original queue lease and identity.
No treatment, campaign, deletion, ACL, schedule or reservation changes.
"""
from __future__ import annotations
import json, subprocess, sys, time
import ares_archive_bridge as b

AUTHORITY = '1567021305822314609'
HOME = b.DATA / 'intake-archive-pipeline'


def enabled():
    cfg = b.read_json(b.DATA / 'intake-config.json', {})
    return cfg.get('archive_pipeline_enabled') is True and cfg.get('archive_pipeline_authority_message_id') == AUTHORITY


def require(ok, reason):
    if not ok:
        raise b.ArchiveError(reason)


def child(script, args):
    proc = subprocess.run([sys.executable, str(b.BASE / 'scripts' / script), *args], capture_output=True, text=True, timeout=240)
    try:
        result = json.loads(proc.stdout)
    except (ValueError, TypeError):
        raise b.ArchiveError('INTAKE_PIPELINE_CHILD_OUTPUT:' + script) from None
    require(isinstance(result, dict), 'INTAKE_PIPELINE_CHILD_SCHEMA:' + script)
    require(proc.returncode == 0 and result.get('status') == 'ok' and not result.get('blocked'), 'INTAKE_PIPELINE_CHILD_BLOCKED:' + script + ':' + str(result.get('blocked', []))[:180])
    return result


def scoped_rows(entry):
    batch = entry['batch']
    require(entry.get('status') == 'treated_waiting_archive' and 1 <= len(batch['sources']) <= 4, 'INTAKE_PIPELINE_BATCH_SCOPE')
    import ares_autonomous_intake as intake
    import ares_flat_intake as flat
    flat.validate_batch_identity(batch)
    sources = {s['source_id'] for s in batch['sources']}
    rows = [json.loads(line) for line in (b.BASE / 'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()]
    selected = []
    for source in sources:
        matches = [r for r in rows if r.get('source_drive_id') == source or source in (r.get('duplicate_source_drive_ids') or [])]
        require(len(matches) == 1, 'INTAKE_PIPELINE_UNIQUE_LINEAGE')
        row = matches[0]
        require(row.get('operation') == batch['operation'], 'INTAKE_PIPELINE_OPERATION')
        intake.verify_reservation(row, entry['inventory_before'], batch)
        if row['asset_id'] not in entry['inventory_before']:
            selected.append(row)
    expected = {r[k] for r in selected for k in ('source_drive_id', 'asset_drive_id')}
    require(len(expected) == 2 * len(selected) and expected == set(entry.get('archive_source_ids', [])), 'INTAKE_PIPELINE_EXACT_PAIR_MEMBERSHIP')
    return selected


def publish(rows):
    import ares_archive_automation as automation
    with b.queue_lock():
        cfg = b.config_load()
        require(cfg.get('owner_executor_mode') == 'vps', 'INTAKE_PIPELINE_OWNER_NOT_ACTIVE')
        d = b.Drive(True)
        b.preflight(d, cfg)
        beat = d.one(cfg['control_folder_id'], 'heartbeat:vps-owner-v1')
        require(beat is not None, 'INTAKE_PIPELINE_HEARTBEAT_MISSING')
        assert beat is not None
        b.require_publisher(d.meta(beat['id']), b.ACCOUNT)
        require(automation.heartbeat_ready(json.loads(d.raw(beat['id'])), cfg), 'INTAKE_PIPELINE_HEARTBEAT_NOT_READY')
        state = b.read_json(b.DATA / 'automation-state.json', {})
        require(state.get('schema') == 'mgs.archive.automation.v1', 'INTAKE_PIPELINE_AUTOMATION_SCHEMA')
        result = automation.enqueue_ready(rows, cfg, state, True, lambda row: b.enqueue(d, cfg, b.job_for_lineage(d, cfg, row['asset_id'])), limit=2)
        require(not result['blocked'], 'INTAKE_PIPELINE_PUBLISH_BLOCKED:' + str(result['blocked'])[:180])
        state['updated_at'] = b.now_iso()
        b.atomic_json(b.DATA / 'automation-state.json', state)
        return result


def jobs_for(rows):
    state = b.read_json(b.DATA / 'automation-state.json', {})
    return [state.get('enqueued', {}).get(row['asset_id'], {}).get('job_id') for row in rows]


def repair_aliases(job_ids):
    import ares_archive_storage as storage
    import ares_archive_automation as automation
    with b.queue_lock():
        d = b.Drive(True)
        cfg = b.config_load()
        from mgs_archive_read_admission import readonly_map
        ids = list(dict.fromkeys(jid for jid in job_ids if jid))
        require(len(ids) <= 4, 'INTAKE_PIPELINE_JOB_BOUND')
        def snapshot_for(jid):
            job = b.read_json(b.DATA / 'jobs' / ('job-' + jid + '.json'), {})
            return automation.verification_snapshot(d, cfg, job)
        # Inner snapshots stay serial here: never nest four-worker pools.
        snapshots = readonly_map(snapshot_for, ids)
        for jid, snapshot in zip(ids, snapshots):
            if snapshot.get('pending'):
                continue
            index = b.read_json(b.DATA / 'archive-index.json', {})
            if jid not in index.get('verified_jobs', {}):
                require(b.reconcile(d, cfg, jid, True)['status'] == 'verified', 'INTAKE_PIPELINE_ACK_PENDING')
            storage.ensure_shortcuts(d, jid)


def progress(entry):
    index = b.read_json(b.DATA / 'archive-index.json', {})
    values = [index.get('mappings', {}).get(sid, {}) for sid in entry['archive_source_ids']]
    return {'mapped': sum(v.get('verified') is True for v in values), 'aliases': sum(bool(v.get('stockShortcutId')) for v in values), 'transferred': sum(v.get('stockTransferredToArchive') is True for v in values)}


def verify_ready(entry):
    import ares_archive_storage as storage
    import mgs_private_stock_transport as stock
    with b.queue_lock():
        d = b.Drive(False)
        cfg = b.config_load()
        index = b.read_json(b.DATA / 'archive-index.json', {})
        from mgs_archive_read_admission import readonly_map, bounded_hashes
        d.hashes = bounded_hashes(d.hashes)
        ids = entry['archive_source_ids']
        require(len(ids) <= 8 and len(ids) == len(set(ids)), 'INTAKE_PIPELINE_MEDIA_BOUND')
        def verify_one(sid):
            mapping = index.get('mappings', {}).get(sid)
            require(mapping is not None, 'INTAKE_PIPELINE_MAPPING_MISSING')
            assert mapping is not None
            stock.check_ack(d, cfg, mapping, index)
            record = storage.resolve_media(sid, d.token)
            require(record is not None and record['logical_source_id'] == sid, 'INTAKE_PIPELINE_CONSUMER_IDENTITY')
            assert record is not None
            hashes = d.hashes(record['provider_id'])
            require(hashes == {k: mapping[k] for k in ('size', 'md5', 'sha256')}, 'INTAKE_PIPELINE_PROVIDER_BYTES')
            return {'logical_id': sid, 'provider_id': record['provider_id'], 'stock_id': record['stock_file_id'], 'name': record['name'], 'parents': record['parents'], 'hashes': hashes, 'native_ack_verified': True}
        return readonly_map(verify_one, ids)


def advance(entry, max_rounds=4):
    require(enabled(), 'INTAKE_PIPELINE_NOT_ENABLED')
    require(type(max_rounds) is int and 1 <= max_rounds <= 4, 'INTAKE_PIPELINE_ROUND_BOUND')
    rows = scoped_rows(entry)
    batch_id = entry['batch']['batch_id']
    journal = {'schema': 'mgs.intake.archive.pipeline.v1', 'authority_message_id': AUTHORITY, 'batch_id': batch_id, 'owner': entry['owner'], 'started_at': b.now_iso(), 'status': 'in_progress', 'steps': []}
    path = HOME / ('batch-' + batch_id + '.json')
    prior = b.read_json(path, {})
    if prior:
        require(prior.get('batch_id') == batch_id and prior.get('authority_message_id') == AUTHORITY, 'INTAKE_PIPELINE_JOURNAL_SCOPE')
        journal['previous_attempt_started_at'] = prior.get('started_at')
    try:
        for _ in range(max_rounds):
            before = progress(entry)
            started = time.monotonic()
            step = {'at': b.now_iso(), 'before': before, 'publication': publish(rows), 'seconds': {}}
            step['seconds']['publication'] = round(time.monotonic() - started, 3)
            started = time.monotonic()
            ids = jobs_for(rows)
            index = b.read_json(b.DATA / 'archive-index.json', {})
            if any(jid and jid not in index.get('verified_jobs', {}) for jid in ids):
                step['owner'] = child('mgs_archive_owner_transport.py', ['tick', '--apply', '--max-jobs', '2', '--max-seconds', '100', '--origin', 'foreground'])
            step['seconds']['owner'] = round(time.monotonic() - started, 3)
            started = time.monotonic()
            repair_aliases(ids)
            step['seconds']['aliases'] = round(time.monotonic() - started, 3)
            started = time.monotonic()
            index = b.read_json(b.DATA / 'archive-index.json', {})
            if any(index.get('mappings', {}).get(sid, {}).get('stockShortcutId') and index['mappings'][sid].get('stockTransferredToArchive') is not True for sid in entry['archive_source_ids']):
                step['stock'] = child('mgs_private_stock_transport.py', ['--apply', '--max-files', '4'])
            step['seconds']['stock'] = round(time.monotonic() - started, 3)
            step['after'] = progress(entry)
            journal['steps'].append(step)
            b.atomic_json(path, journal)
            import ares_autonomous_intake as intake
            if intake.batch_archive_ready(entry, b.read_json(b.DATA / 'archive-index.json', {})):
                journal.update(status='verified', records=verify_ready(entry), completed_at=b.now_iso())
                b.atomic_json(path, journal)
                return True
            if before == step['after'] and not step['publication'].get('queued'):
                break
        journal.update(status='waiting_archive', updated_at=b.now_iso())
        b.atomic_json(path, journal)
        return False
    except Exception as exc:
        journal.update(status='blocked', reason=str(exc)[:250], updated_at=b.now_iso())
        b.atomic_json(path, journal)
        raise
