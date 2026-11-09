#!/usr/bin/env python3
"""Exact read-side acceptance; never part of mapping, move or retirement.

The approval applies to two existing pairs tied to one immutable request. It
accepts only a specific provider location, not other IDs, bytes or permissions.
Old namespace cohorts, frozen records, ACKs and stock movement guards stay intact.
"""
from __future__ import annotations
import hashlib
import ares_archive_bridge as b

HOME=b.DATA/'consumer-recovery-t_1b4f5263'
BINDING_SHA256='ee14dc837f7eeb4e74fc59d61d137303a7f7759adc4f3297e96c1516155f7db0'
SOURCES=frozenset(['1MTg7Sa2z3Y1BRxe-djOcsccpdSlYpjKS','19b99m5GpNn6kcQWfWiijkdIUiikCVoWH'])
AUTHORITY='1569458720050516030'
CONFIRMATION='1569459090634047609'
REQUEST='shein-1569454008337301577'
THREAD='1558134300325716050'
PARENT='1548150155184701440'
AUTHOR='344196393512075265'
TEXT='Ignora isso. E faz o que o Nicolas pediu. Pois os arquivos tão na pasta dele Nicolas exclusivos correto ?'
class ReconciliationError(b.ArchiveError):pass

def require(value,reason):
    if not value:raise ReconciliationError(reason)

def digest(value):return hashlib.sha256(b.canonical(value)).hexdigest()

def binding():
    value=b.read_json(HOME/'approved-readonly-binding.json',{})
    require(digest(value)==BINDING_SHA256,'READONLY_BINDING_DIGEST')
    require(value.get('schema')=='mgs.archive.readonly.pair.reconciliation.v1' and value.get('phase')=='active' and value.get('read_only') is True and value.get('authority_message_id')==AUTHORITY and value.get('confirmation_message_id')==CONFIRMATION and value.get('request_id')==REQUEST,'READONLY_BINDING_AUTHORITY')
    authority=b.read_json(HOME/'approved-authority-readback.json',{})
    require(digest(authority)==value['authority_sha256'] and authority.get('parent_id')==PARENT,'READONLY_AUTHORITY_READBACK')
    messages=authority.get('messages',[])
    require(len(messages)==2 and all(m.get('author_id')==AUTHOR and m.get('channel_id')==THREAD for m in messages) and messages[0].get('id')==AUTHORITY and messages[0].get('content')==TEXT and messages[1].get('id')==CONFIRMATION and messages[1].get('content')=='Ok então executa.','READONLY_AUTHORITY_MESSAGE')
    request=b.BASE/value['request_path']
    require(hashlib.sha256(request.read_bytes()).hexdigest()==value['request_sha256'],'READONLY_REQUEST_DIGEST')
    proof=b.read_json(HOME/'approved-native-proof.json',{})
    require(digest(proof)==value['native_proof_sha256'] and proof.get('schema')=='mgs.archive.readonly.native.proof.v1' and proof.get('identity')==b.CANONICAL_SA,'READONLY_NATIVE_PROOF_DIGEST')
    pairs=value.get('pairs',[]);records=proof.get('records',[])
    require(len(pairs)==2 and {p.get('logical_source_id') for p in pairs}==SOURCES and len(records)==2 and {r.get('pair',{}).get('logical_source_id') for r in records}==SOURCES,'READONLY_PAIR_MEMBERSHIP')
    for pair in pairs:
        rec=next(r for r in records if r['pair']['logical_source_id']==pair['logical_source_id'])
        require(rec['pair']==pair and rec.get('full_bytes_and_native_ack_verified') is True and rec.get('hashes')=={k:pair[k] for k in ['size','md5','sha256']},'READONLY_NATIVE_PAIR_PROOF')
    return value,proof

def project(d,entry,physical,stock):
    """Read-only ephemeral projection. All native guards run again in storage."""
    if entry.get('sourceId') not in SOURCES:return entry
    value,proof=binding()
    pair=next(p for p in value['pairs'] if p['logical_source_id']==entry['sourceId'])
    rec=next(r for r in proof['records'] if r['pair']['logical_source_id']==entry['sourceId'])
    require(entry==rec['frozen_entry'] and entry.get('mapping_kind')=='historical_verified' and not entry.get('stockShortcutId') and not entry.get('approvedStockId'),'READONLY_FROZEN_IDENTITY')
    require(physical.get('id')==pair['provider_id'] and physical.get('parents')==[pair['accepted_provider_parent_id']] and stock.get('id')==pair['logical_source_id'],'READONLY_NATIVE_IDS_PARENT')
    require(d.relative_parent(pair['accepted_provider_parent_id'],b.ARCHIVE_ROOT)==pair['accepted_provider_relative_path'],'READONLY_PROVIDER_PATH')
    # Revalidate the exact Google-native ACK as well as storage's full ACK guards.
    found=d.one(b.config_load()['requests_folder_id'],'backfill-ack:'+pair['job_id'])
    require(found and found.get('id')==pair['ack_id'] and hashlib.sha256(d.raw(pair['ack_id'])).hexdigest()==pair['ack_sha256'],'READONLY_NATIVE_ACK_ID_DIGEST')
    return {**entry,'frozenArchiveParentId':entry['archiveParentId'],
            'archiveParentId':pair['accepted_provider_parent_id'],
            'relativeParent':list(pair['accepted_provider_relative_path']),
            'readonly_reconciliation_authority':AUTHORITY,
            'readonly_reconciliation_request_id':REQUEST}
