#!/usr/bin/env python3
"""Approved same-ID consolidation of retained staging; no DELETE/copy/ACL writes.

The private maintenance caller owns intake -> queue leases. Frozen relocation
snapshots remain immutable; each consolidation adds an SA-published exact proof.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
from pathlib import Path
import ares_archive_bridge as b
import mgs_flat_layout as f
import mgs_flat_cutover as cut
import mgs_flat_source_compat as compat
import mgs_archive_owner_transport as transport

AUTHORITY = '1567557554018590782'
HOME = b.DATA / ('folder-consolidation-' + AUTHORITY)
BINDING = HOME / 'binding.json'
ROOT = '1mD8OlejKZ4XBEzPnANtJqyROo0apQo_J'
AUTHOR = '344196393512075265'
THREAD = '1562078493498540042'


def require(value, reason):
    if not value:
        raise b.ArchiveError('CONSOLIDATION_' + reason)


def sha(value):
    return hashlib.sha256(b.canonical(value)).hexdigest()


def authority():
    a = b.read_json(HOME / 'authority.json', {})
    require(a.get('message_id') == AUTHORITY and a.get('author_id') == AUTHOR
            and a.get('thread_id') == THREAD and a.get('native_verified') is True,
            'AUTHORITY')
    return a


def enabled():
    value = b.read_json(BINDING, {})
    return (value.get('phase') == 'active' and
            value.get('authority_message_id') == AUTHORITY and
            value.get('processing_root_id') == ROOT)


def owned(m):
    require(m.get('trashed') is False and not m.get('driveId') and
            any(o.get('emailAddress') == b.ACCOUNT for o in m.get('owners', [])),
            'NATIVE_OWNER')
    require(not any(p.get('type') in ('anyone', 'domain')
                    for p in m.get('permissions', [])), 'PUBLIC_ACCESS')


def metadata_equal(before, after, parent):
    for key in ('id', 'name', 'mimeType', 'size', 'md5Checksum',
                'sha256Checksum', 'createdTime', 'properties'):
        require(before.get(key) == after.get(key), 'CONTENT_CHANGED:' + key)
    require(after.get('parents') == [parent], 'PARENT_CHANGED')
    owned(after)


def read_proof(d, binding):
    key = binding['proof_sha256']
    with compat._PROOF_LOCK:
        cache = getattr(d, '_consolidation_proofs', {})
        if key in cache:
            return cache[key]
        native = d.meta(binding['proof_file_id'])
        raw = d.raw(binding['proof_file_id'])
        b.require_publisher(native, b.CANONICAL_SA, 'CONSOLIDATION_PUBLISHER')
        require(b.control_object_scope(native, f.CONTROL) and
                native.get('properties', {}).get('mgsArchiveType') == 'lineage_map'
                and hashlib.sha256(raw).hexdigest() == key, 'NATIVE_PROOF')
        proof = json.loads(raw)
        require(proof.get('schema') == 'mgs.flat.consolidation.proof.v1' and
                proof.get('authority_message_id') == AUTHORITY and
                proof.get('author_id') == AUTHOR and
                proof.get('processing_root_id') == ROOT and
                proof.get('status') == 'verified' and
                all(proof.get(k) == 0 for k in
                    ('delete_writes', 'copy_writes', 'acl_writes')), 'PROOF_AUTHORITY')
        require(sorted(proof['records']) == sorted(binding['source_ids']),
                'PROOF_MEMBERSHIP')
        cache[key] = proof
        d._consolidation_proofs = cache
        return proof


def verify(d, meta, asset, job, snapshot):
    """Additional exact relocation evidence, never a global ancestry bypass."""
    binding = b.read_json(BINDING, {})
    if binding.get('phase') != 'active':
        return False
    require(binding.get('authority_message_id') == AUTHORITY and
            binding.get('processing_root_id') == ROOT, 'BINDING_AUTHORITY')
    fid = asset.get('sourceId')
    matches = [x for x in binding.get('proofs', []) if fid in x['source_ids']]
    require(len(matches) <= 1, 'DUPLICATE_SOURCE')
    if not matches:
        return False
    proof = read_proof(d, matches[0])
    record = proof['records'][fid]
    if job is None:
        raise b.ArchiveError('CONSOLIDATION_JOB_REQUIRED')
    require(sha(snapshot) == record['snapshot_sha256'],
            'ORIGINAL_SNAPSHOT')
    pairs = record['jobs']
    require(pairs.get(job.get('jobId')) ==
            {'job_sha256': sha(job), 'asset_sha256': sha(asset)}, 'FROZEN_JOB')
    before = snapshot['objects'][fid]['metadata']
    require(before.get('parents') == [asset['sourceParentId']], 'ORIGINAL_PARENT')
    for native, key in [('id', 'sourceId'), ('name', 'name'),
                        ('mimeType', 'mimeType'), ('size', 'size'),
                        ('md5Checksum', 'md5'), ('sha256Checksum', 'sha256'),
                        ('createdTime', 'sourceCreatedTime')]:
        require(str(before.get(native)) == str(asset.get(key)) and
                meta.get(native) == before.get(native), 'FROZEN_BYTES:' + native)
    require(record.get('full_streams_verified') is True and
            record.get('hashes') == {k: asset[k] for k in ('size', 'md5', 'sha256')},
            'STREAM_EVIDENCE')
    metadata_equal(record['metadata_after'], meta, record['destination_parent'])
    require(str(meta.get('version', '')).isdigit() and
            int(meta['version']) >= int(before['version']), 'VERSION')
    parent = meta['parents'][0]
    chain = record['chain']
    require(len(chain) == 3, 'CHAIN_LENGTH')
    for expected in chain:
        require(parent == expected['id'], 'CHAIN_ID')
        current = d.meta(parent)
        owned(current)
        require(current.get('mimeType') == b.FOLDER and all(
            current.get(k) == expected[k] for k in ('id', 'name', 'parents')),
            'CHAIN_NATIVE')
        parent = current['parents'][0]
    require(parent == ROOT and list(reversed([x['name'] for x in chain])) ==
            asset['relativeParent'], 'CANONICAL_PATH')
    root = d.meta(ROOT)
    owned(root)
    require(root.get('mimeType') == b.FOLDER and root.get('parents') ==
            ['1u58O4XYH2hgd9zUlDMP_8huuTkAjH3_W'], 'ROOT_BINDING')
    return True


def native_tree(d, root):
    nodes = {root: d.meta(root)}
    front = [root]
    while front:
        parent = front.pop()
        for item in d.listing(parent):
            require(item['id'] not in nodes, 'TREE_CYCLE')
            nodes[item['id']] = d.meta(item['id'])
            if item['mimeType'] == b.FOLDER:
                front.append(item['id'])
    return nodes


def move_once(owner, sa, journal, fid, old_parent, new_parent, expected):
    require(old_parent != new_parent, 'NOOP_MOVE')
    current = sa.meta(fid)
    owned(current)
    key = 'consolidate:' + fid
    prior = journal.data['intents'].get(key)
    prior_binding = prior.get('binding', {}) if prior else None
    binding = {'source_parent': old_parent, 'destination_parent': new_parent,
               'metadata_before': expected, 'authority': AUTHORITY}
    if current.get('parents') == [new_parent]:
        require(prior is not None and prior_binding == binding,
                'UNJOURNALLED_MOVE')
        metadata_equal(expected, current, new_parent)
        if prior and prior.get('id') != fid:
            journal.landed(key, fid)
        return
    require(not prior and current.get('parents') == [old_parent] and
            current.get('version') == expected.get('version'), 'CAS_OR_AMBIGUOUS')
    metadata_equal(expected, current, old_parent)
    destination = sa.meta(new_parent)
    owned(destination)
    require(destination.get('mimeType') == b.FOLDER and
            f.same_access(f.permissions(sa, fid), f.permissions(sa, new_parent)),
            'DESTINATION_ACCESS')
    journal.intent(key, {'source_parent': old_parent,
                         'destination_parent': new_parent,
                         'metadata_before': expected, 'authority': AUTHORITY})
    error = None
    try:
        f.rpc_once(owner, 'PATCH', 'files/' + fid,
                   {'supportsAllDrives': 'true', 'addParents': new_parent,
                    'removeParents': old_parent, 'fields': 'id,parents'}, {})
    except Exception as exc:
        error = exc
    after = sa.meta(fid)
    if after.get('parents') != [new_parent]:
        if error:
            raise error
        require(False, 'MOVE_READBACK')
    metadata_equal(expected, after, new_parent)
    journal.landed(key, fid)


def canonical_folder(owner, sa, parent, name, journal):
    candidates = [x for x in sa.listing(parent)
                  if x['name'] == name and x['mimeType'] == b.FOLDER]
    require(len(candidates) <= 1, 'CANONICAL_DUPLICATES')
    if candidates:
        return candidates[0]['id']
    return cut.create_group(owner, sa, parent, name,
                            'consolidation:' + parent + ':' + name, journal)


def destination_for_path(listing, operation_id, path, allow_missing=False):
    """Read-only lookup; only the two standard media/status buckets may be absent."""
    require(len(path) == 2 and path[0] in ('IMG', 'VID') and
            path[1] in ('01_READY', '99_LEGACY'), 'PREFLIGHT_PATH')
    parent = operation_id
    for name, reason in zip(path, ('CANONICAL_FORMAT', 'CANONICAL_STATUS')):
        candidates = [x for x in listing(parent) if x['name'] == name]
        require(len(candidates) <= 1, reason)
        if not candidates:
            require(allow_missing, reason)
            return None
        require(candidates[0]['mimeType'] == b.FOLDER, reason)
        parent = candidates[0]['id']
    return parent


def preflight(sa, generation, allow_missing=False):
    authority()
    state = b.read_json(f.HOME / 'maintenance' / generation / 'receipt-state.json', {})
    require(state.get('status') == 'verified', 'RELOCATION_NOT_ACCEPTED')
    snapshot, receipt = compat.evidence(sa, state['media_ids'][0])
    nodes = native_tree(sa, generation)
    files = {i: m for i, m in nodes.items() if m['mimeType'] != b.FOLDER}
    require(set(files) == set(state['media_ids']), 'SOURCE_SET')
    jobs = {j: b.read_json(b.DATA / 'jobs' / ('job-' + j + '.json'))
            for j in snapshot['jobs']}
    index = b.read_json(b.DATA / 'archive-index.json', {}).get('mappings', {})
    completed = {}
    intake = b.read_json(b.DATA / 'intake-state.json', {})
    for claim in intake.get('claims', {}).values():
        if claim.get('status') == 'complete':
            for p in claim.get('proofs', []):
                completed[p['source_id']] = p['raw_sha256']
                completed[p['clean_source_id']] = p['clean_sha256']
    operation = snapshot['objects'][generation]['metadata']['name']
    require(operation in __import__('ares_flat_intake').registered_operations(),
            'OPERATION')
    canonical = [x for x in sa.listing(ROOT) if x['name'] == operation]
    require(len(canonical) == 1 and canonical[0]['mimeType'] == b.FOLDER,
            'CANONICAL_OPERATION_REQUIRED')
    operation_id = canonical[0]['id']
    records = {}
    listing_cache = {}
    acl_cache = {}
    def listing(parent):
        if parent not in listing_cache:
            listing_cache[parent] = sa.listing(parent)
        return listing_cache[parent]
    def target_acl(parent):
        if parent not in acl_cache:
            acl_cache[parent] = f.permissions(sa, parent)
        return acl_cache[parent]
    for fid, m in files.items():
        owned(m)
        before = snapshot['objects'][fid]['metadata']
        for key in ('id', 'name', 'mimeType', 'size', 'md5Checksum',
                    'sha256Checksum', 'createdTime', 'properties'):
            require(m.get(key) == before.get(key), 'PREFLIGHT_CONTENT:' + key)
        path = sa.relative_parent(m['parents'][0], generation)
        require(len(path) == 2 and path[0] in ('IMG', 'VID') and
                path[1] in ('01_READY', '99_LEGACY'), 'PREFLIGHT_PATH')
        # Missing standard buckets are planned read-only and provisioned only
        # by the existing private maintenance caller after full stream checks.
        target = destination_for_path(listing, operation_id, path, allow_missing)
        acl = f.permissions(sa, fid)
        require(f.same_access(acl, target_acl(target or operation_id)), 'PREFLIGHT_ACCESS')
        pairs = {}
        for jid, job in jobs.items():
            require(sha(job) == snapshot['jobs'][jid], 'PREFLIGHT_JOB')
            for asset in job['assets']:
                if asset['sourceId'] == fid:
                    pairs[jid] = {'job_sha256': sha(job), 'asset_sha256': sha(asset)}
        fixture = b.read_json(f.HOME / 'maintenance-canary-state.json', {})
        technical = (fid == fixture.get('media_id') and
                     m.get('sha256Checksum') == fixture.get('media_sha256') and
                     m.get('properties', {}).get('mgsArchiveType') ==
                     'flat_maintenance_canary')
        require(pairs or (completed.get(fid) == m.get('sha256Checksum')) or
                technical, 'UNREGISTERED_SOURCE')
        mapping = index.get(fid)
        if mapping:
            require(mapping.get('verified') is True and
                    mapping.get('stockTransferredToArchive') is True,
                    'UNVERIFIED_ARCHIVE')
            require(all(str(mapping.get(k)) == str(m.get(n)) for k, n in
                        [('size', 'size'), ('md5', 'md5Checksum'),
                         ('sha256', 'sha256Checksum')]), 'ARCHIVE_MAPPING_BYTES')
        records[fid] = {'metadata_before': m, 'permissions_before': acl,
                        'destination_parent': target, 'destination_path': path, 'jobs': pairs,
                        'snapshot_sha256': sha(snapshot),
                        'provider_id': mapping.get('archiveId') if mapping else None}
    return {'generation': generation, 'operation_id': operation_id,
            'operation': operation, 'records': records, 'nodes': nodes,
            'old_container_id': sa.meta(generation)['parents'][0],
            'state': state, 'created_at': b.now_iso()}


def streams(sa, fid, record):
    m = record['metadata_before']
    expected = {'size': m['size'], 'md5': m['md5Checksum'],
                'sha256': m['sha256Checksum']}
    require(sa.hashes(fid) == expected, 'SOURCE_STREAM')
    if record.get('provider_id'):
        require(sa.hashes(record['provider_id']) == expected, 'PROVIDER_STREAM')
    return expected


def expected_for_move(sa, journal, target_home, generation, fid, record):
    """Supplement a frozen plan only after exact bytes/ACL and stable native CAS.

    Original plans/snapshots are immutable. Each observed native version gets its
    own scoped proof; move_once still compares the exact observed version.
    """
    expected = record['metadata_before']
    old_parent = expected['parents'][0]
    new_parent = record['destination_parent']
    prior = journal.data['intents'].get('consolidate:' + fid)
    if prior:
        binding = prior.get('binding', {})
        frozen = binding.get('metadata_before')
        if frozen == expected:
            return expected
        require(isinstance(frozen, dict), 'REFRESH_INTENT_METADATA')
        proof = b.read_json(target_home / ('cas-' + fid + '-' +
                            str(frozen.get('version', '')) + '.json'), {})
        require(proof.get('authority') == AUTHORITY and
                proof.get('generation') == generation and
                proof.get('record_sha256') == sha(record) and
                proof.get('metadata_before') == frozen and
                proof.get('full_streams_verified') is True,
                'REFRESH_INTENT_PROOF')
        return frozen
    current = sa.meta(fid)
    if current.get('version') == expected.get('version') or current.get('parents') == [new_parent]:
        return expected
    metadata_equal(expected, current, old_parent)
    require(str(current.get('version', '')).isdigit() and
            str(expected.get('version', '')).isdigit() and
            int(current['version']) > int(expected['version']), 'REFRESH_VERSION')
    require(f.same_access(record['permissions_before'], f.permissions(sa, fid)),
            'REFRESH_ACCESS')
    hashes = {'size': expected['size'], 'md5': expected['md5Checksum'],
              'sha256': expected['sha256Checksum']}
    require(sa.hashes(fid) == hashes, 'REFRESH_STREAM')
    after = sa.meta(fid)
    require(after == current, 'REFRESH_NOT_STABLE')
    proof = {'schema': 'mgs.flat.consolidation.cas.v1', 'authority': AUTHORITY,
             'generation': generation, 'source_id': fid,
             'record_sha256': sha(record), 'metadata_before': current,
             'hashes': hashes, 'full_streams_verified': True,
             'access_preserved': True}
    path = target_home / ('cas-' + fid + '-' + str(current['version']) + '.json')
    saved = b.read_json(path)
    require(saved is None or saved == proof, 'REFRESH_PROOF_CHANGED')
    if saved is None:
        b.atomic_json(path, proof)
    return current


def consolidate(sa, owner, generation):
    authority()
    require(enabled(), 'NOT_ENABLED')
    target_home = HOME / generation
    target_home.mkdir(parents=True, exist_ok=True)
    if b.read_json(target_home / 'result.json', {}).get('status') == 'verified':
        return b.read_json(target_home / 'result.json')
    plan = b.read_json(target_home / 'plan.json')
    journal = transport.Journal(target_home / 'journal.json')
    if plan is None:
        candidate = preflight(sa, generation, allow_missing=True)
        missing = sorted({tuple(r['destination_path']) for r in candidate['records'].values()
                          if r['destination_parent'] is None})
        if missing:
            # Complete provenance, ACL and full-byte validation before creating
            # only standard empty buckets. No media/ACL/credential mutation.
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda pair: streams(sa, *pair), candidate['records'].items()))
            b.atomic_json(target_home / 'bucket-preflight.json', candidate)
            for format_name, status_name in missing:
                parent = canonical_folder(owner, sa, candidate['operation_id'], format_name, journal)
                canonical_folder(owner, sa, parent, status_name, journal)
        # Re-read strict destinations/access before freezing any source move.
        plan = preflight(sa, generation)
        b.atomic_json(target_home / 'plan.json', plan)
    records = plan['records']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda pair: streams(sa, *pair), records.items()))
    # Reject any new object before a production mutation.
    live = native_tree(sa, generation)
    expected_remaining = {i for i in records if
                          sa.meta(i)['parents'] == records[i]['metadata_before']['parents']}
    require({i for i, m in live.items() if m['mimeType'] != b.FOLDER} ==
            expected_remaining, 'NEW_SOURCE_OBJECT')
    for fid, rec in records.items():
        expected = expected_for_move(sa, journal, target_home, generation, fid, rec)
        move_once(owner, sa, journal, fid,
                  rec['metadata_before']['parents'][0], rec['destination_parent'],
                  expected)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        checked_hashes = dict(zip(records, pool.map(
            lambda pair: streams(sa, *pair), records.items())))
    proof_records = {}
    for fid, rec in records.items():
        after = sa.meta(fid)
        metadata_equal(rec['metadata_before'], after, rec['destination_parent'])
        require(f.same_access(rec['permissions_before'], f.permissions(sa, fid)),
                'ACCESS_AFTER')
        chain = []
        current = rec['destination_parent']
        for _ in range(3):
            m = sa.meta(current)
            owned(m)
            chain.append({k: m[k] for k in ('id', 'name', 'parents')})
            current = m['parents'][0]
        require(current == ROOT, 'FINAL_ROOT')
        proof_records[fid] = {'metadata_after': after, 'jobs': rec['jobs'],
                              'snapshot_sha256': rec['snapshot_sha256'],
                              'destination_parent': rec['destination_parent'],
                              'chain': chain, 'hashes': checked_hashes[fid],
                              'full_streams_verified': True}
    proof = b.read_json(target_home / 'proof.json') or {'schema': 'mgs.flat.consolidation.proof.v1', 'status': 'verified',
             'authority_message_id': AUTHORITY, 'author_id': AUTHOR,
             'processing_root_id': ROOT, 'generation': generation,
             'records': proof_records, 'delete_writes': 0, 'copy_writes': 0,
             'acl_writes': 0, 'verified_at': b.now_iso()}
    # Immutable native proof is published before activating its consumer binding.
    require(set(proof['records']) == set(records), 'REPLAY_PROOF_MEMBERSHIP')
    b.atomic_json(target_home / 'proof.json', proof)
    raw = b.canonical(proof)
    proof_id = sa.upload_once(f.CONTROL, 'consolidated-sources-' + generation + '.json',
                             raw, 'application/json',
                             'consolidated-sources:' + generation, 'lineage_map')
    native = sa.meta(proof_id)
    b.require_publisher(native, b.CANONICAL_SA, 'CONSOLIDATION_PUBLISHER')
    require(b.control_object_scope(native, f.CONTROL) and sa.raw(proof_id) == raw,
            'PUBLICATION_READBACK')
    pin = {'proof_file_id': proof_id, 'proof_sha256': sha(proof),
           'source_ids': sorted(records), 'generation': generation}
    binding = b.read_json(BINDING, {})
    overlap = [x for x in binding['proofs'] if set(records) & set(x['source_ids'])]
    require(not overlap or overlap == [pin], 'BINDING_OVERLAP')
    if not overlap:
        binding['proofs'].append(pin)
    b.atomic_json(BINDING, binding)
    b.atomic_json(target_home / 'proof.json', proof)
    # Preserve empty folder IDs for rollback; remove duplicate operation labels
    # from the processing surface without DELETE/trash or recreating media.
    require(not any(m['mimeType'] != b.FOLDER for m in
                    native_tree(sa, generation).values()), 'NONEMPTY_RETIRED_TREE')
    empty = canonical_folder(owner, sa, ROOT, '_ESTRUTURAS_VAZIAS', journal)
    container = sa.meta(plan['old_container_id'])
    require(container.get('parents') in ([ROOT], [empty]), 'CONTAINER_SCOPE')
    move_once(owner, sa, journal, container['id'], ROOT, empty, container)
    rename_key = 'retired-name:' + generation
    current = sa.meta(generation)
    target_name = 'REGISTRO_' + generation
    if current['name'] != target_name:
        require(not journal.data['intents'].get(rename_key), 'AMBIGUOUS_RENAME')
        journal.intent(rename_key, {'id': generation, 'name_before': current['name'],
                                   'name_after': target_name, 'authority': AUTHORITY})
        error = None
        try:
            f.rpc_once(owner, 'PATCH', 'files/' + generation,
                       {'supportsAllDrives': 'true', 'fields': 'id,name'},
                       {'name': target_name})
        except Exception as exc:
            error = exc
        if sa.meta(generation)['name'] != target_name:
            if error:
                raise error
            require(False, 'RENAME_READBACK')
        journal.landed(rename_key, generation)
    result = {'status': 'verified', 'generation': generation,
              'source_ids': sorted(records), 'files': len(records),
              'jobs': sorted({j for r in records.values() for j in r['jobs']}),
              'proof': pin, 'delete_writes': 0, 'copy_writes': 0, 'acl_writes': 0,
              'verified_at': b.now_iso()}
    b.atomic_json(target_home / 'result.json', result)
    return result
