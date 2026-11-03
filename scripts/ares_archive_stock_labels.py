"""One explicitly approved shortcut display label, not a general rename bypass.

Immutable requests, ACKs, inventory names, paths and reservations stay intact.
The local binding pins a separate SA-authored native verification proof.
"""
from __future__ import annotations
import hashlib
import ares_archive_bridge as b

HOME = b.DATA / 'stock-label-reconciliation-1567008281648693330'
AUTHORITY = '1567008281648693330'
SOURCE = '1oG-JSqH0U_ay2A_fLiX-4QAR6yrHF4ks'
STOCK = '10PwEF0o8lkvFwjlvEb1bnSvaS78xbaTP'
PROVIDER = '1ZSq4VSySKvW1xMRjpV0NS8Jfd1-9iwPq'
JOB = '033040ce1fd58e55cec31a8aefef19d4'
FIELDS = ('sourceId', 'archiveId', 'stockShortcutId', 'jobId', 'lineageId', 'md5', 'sha256', 'size')


def identity(entry):
    return {k: entry.get(k) for k in FIELDS}


def record(entry=None):
    if entry is not None and entry.get('sourceId') != SOURCE:
        return None
    binding = b.read_json(HOME / 'binding.json', {})
    if not binding or binding.get('phase') != 'active':
        return None
    b_require = lambda ok, reason: _require(ok, reason)
    b_require(binding.get('schema') == 'mgs.archive.stock.label.binding.v1' and binding.get('authority_message_id') == AUTHORITY, 'STOCK_LABEL_AUTHORITY')
    proof = b.read_json(HOME / 'native-proof.json', {})
    b_require(hashlib.sha256(b.canonical(proof)).hexdigest() == binding.get('proof_sha256'), 'STOCK_LABEL_PROOF_DIGEST')
    b_require(proof.get('schema') == 'mgs.archive.stock.label.proof.v1' and proof.get('authority_message_id') == AUTHORITY and proof.get('native_verified') is True, 'STOCK_LABEL_PROOF')
    rec = proof['record']
    expected = {'sourceId': SOURCE, 'stockShortcutId': STOCK, 'archiveId': PROVIDER, 'jobId': JOB}
    b_require(all(rec['identity'].get(k) == v for k, v in expected.items()), 'STOCK_LABEL_SCOPE')
    b_require(rec.get('stock_name') == '03 - BABY TEES' and rec.get('provider_name') == 'SHEIN_US_EN_IMG_FREE_BABY_TEES_NV_003.jpg' and rec.get('catalogue_name') == rec['provider_name'], 'STOCK_LABEL_EXACT_NAMES')
    b_require(proof.get('provider_hashes') == {k: rec['identity'][k] for k in ('size', 'md5', 'sha256')} and proof.get('ack_verified') is True, 'STOCK_LABEL_BYTES_OR_ACK')
    if entry is not None:
        b_require(identity(entry) == rec['identity'], 'STOCK_LABEL_FROZEN_IDENTITY')
    return rec


def _require(ok, reason):
    if not ok:
        raise b.ArchiveError(reason)


def names_match(entry, physical, stock):
    rec = record(entry)
    if rec is None:
        return None
    return (physical.get('id') == PROVIDER and physical.get('name') == rec['provider_name']
            and physical.get('parents') == rec['provider_parents']
            and stock.get('id') == STOCK and stock.get('name') == rec['stock_name']
            and stock.get('shortcutDetails', {}).get('targetId') == PROVIDER
            and stock.get('properties', {}).get('mgsArchiveLogicalSource') == SOURCE)


def catalogue_name(entry, stock):
    rec = record(entry)
    if rec is None:
        return None
    _require(stock.get('id') == STOCK and stock.get('name') == rec['stock_name'], 'STOCK_LABEL_CHANGED_AGAIN')
    return rec['catalogue_name']


def native_stock_label(logical_id, stock_id, catalogue_label):
    if logical_id != SOURCE or stock_id != STOCK:
        return None
    rec = record()
    if rec is None:
        return None
    _require(catalogue_label == rec['catalogue_name'], 'STOCK_LABEL_CATALOGUE_CHANGED')
    return rec['stock_name']
