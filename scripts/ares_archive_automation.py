#!/usr/bin/env python3
"""Bounded archive automation. Same canonical SA; never deletes creative sources."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as bridge
import hashlib
import re


def lineage_fingerprint(row):
    fields=('asset_id','source_drive_id','asset_drive_id','original_checksum','clean_checksum')
    return hashlib.sha256(bridge.canonical({k:row.get(k) for k in fields})).hexdigest()


def select_inventory(rows,c):
    bridge.validate_config(c)
    seen=set();selected=[];excluded={}
    for row in rows:
        aid=row.get('asset_id')
        if not isinstance(aid,str) or not aid:
            excluded['invalid_id']=excluded.get('invalid_id',0)+1;continue
        if aid in seen:raise bridge.ArchiveError('DUPLICATE_INVENTORY_LINEAGE')
        seen.add(aid)
        reason=None
        try:
            bridge.validate_lineage(row,c)
        except (bridge.ArchiveError,KeyError,TypeError):reason='historical_or_not_clean'
        if any(row.get(k) for k in ('asset_trashed','source_trashed','asset_drive_trashed','source_drive_trashed','deleted_at','removed_at','superseded_by_asset_id')):reason='retired_or_superseded'
        if not all(isinstance(row.get(k),str) and re.fullmatch(r'[A-Za-z0-9_-]{8,}',row[k]) for k in ('source_drive_id','asset_drive_id')) or row.get('source_drive_id')==row.get('asset_drive_id'):reason='missing_or_same_source_pair'
        if not all(isinstance(row.get(k),str) and re.fullmatch('[a-f0-9]{64}',row[k]) for k in ('original_checksum','clean_checksum')):reason='missing_hash'
        if reason:excluded[reason]=excluded.get(reason,0)+1
        else:selected.append(row)
    return selected,excluded


def enqueue_ready(rows,c,state,apply,publish,limit=2):
    selected,excluded=select_inventory(rows,c)
    out={'queued':[],'planned':[],'blocked':[],'deferred':0,'excluded':excluded}
    if not c.get('queue_enabled'):return out
    previous=state.get('enqueued',{})
    for row in selected:
        aid=row['asset_id'];fingerprint=lineage_fingerprint(row);old=previous.get(aid)
        if old:
            if old['fingerprint']!=fingerprint:out['blocked'].append({'asset_id':aid,'reason':'ENQUEUED_LINEAGE_CHANGED'})
            continue
        if len(out['queued'])+len(out['planned'])>=limit:out['deferred']+=1;continue
        if not apply:out['planned'].append(aid);continue
        try:
            result=publish(row)
            if not result.get('jobId') or not result.get('requestFileId'):raise bridge.ArchiveError('PUBLISH_RESULT_INCOMPLETE')
            state.setdefault('enqueued',{})[aid]={'fingerprint':fingerprint,'job_id':result['jobId'],'request_file_id':result['requestFileId']}
            previous=state['enqueued'];out['queued'].append({'asset_id':aid,**result})
        except bridge.ArchiveError as exc:out['blocked'].append({'asset_id':aid,'reason':str(exc)[:200]})
    return out
