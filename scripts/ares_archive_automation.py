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
    from collections import Counter
    counts=Counter(row.get('asset_id') for row in rows)
    selected=[];excluded={}
    for row in rows:
        aid=row.get('asset_id')
        if not isinstance(aid,str) or not aid:
            excluded['invalid_id']=excluded.get('invalid_id',0)+1;continue

        reason=None
        try:
            bridge.validate_lineage(row,c)
        except (bridge.ArchiveError,KeyError,TypeError):reason='historical_or_not_clean'
        if any(row.get(k) for k in ('asset_trashed','source_trashed','asset_drive_trashed','source_drive_trashed','deleted_at','removed_at','superseded_by_asset_id')):reason='retired_or_superseded'
        if not all(isinstance(row.get(k),str) and re.fullmatch(r'[A-Za-z0-9_-]{8,}',row[k]) for k in ('source_drive_id','asset_drive_id')) or row.get('source_drive_id')==row.get('asset_drive_id'):reason='missing_or_same_source_pair'
        if not all(isinstance(row.get(k),str) and re.fullmatch('[a-f0-9]{64}',row[k]) for k in ('original_checksum','clean_checksum')):reason='missing_hash'
        if reason:excluded[reason]=excluded.get(reason,0)+1
        else:
            if counts[aid]>1:raise bridge.ArchiveError('DUPLICATE_INVENTORY_LINEAGE')
            selected.append(row)
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


def verification_snapshot(d,c,job):
    import json
    jid=job['jobId'];request=d.one(c['requests_folder_id'],'request:'+jid)
    if request is None:raise bridge.ArchiveError('REQUEST_MISSING')
    meta=d.meta(request['id']);bridge.require_publisher(meta,bridge.CANONICAL_SA,'REQUEST_AUTHOR')
    body=d.raw(request['id']);props=meta.get('properties',{})
    if meta.get('parents')!=[c['requests_folder_id']] or meta.get('driveId')!=c['source_drive_id'] or props.get('mgsArchiveType')!='request' or props.get('mgsArchiveKey')!='request:'+jid or body!=bridge.canonical(job) or hashlib.sha256(body).hexdigest()!=props.get('sha256'):
        raise bridge.ArchiveError('REQUEST_SCOPE_OR_BODY_CHANGED')
    rf=d.one(c['receipts_folder_id'],'receipt:'+jid)
    if rf is None:return {'pending':True}
    rm=d.meta(rf['id']);bridge.require_publisher(rm,bridge.ACCOUNT,'RECEIPT_AUTHOR')
    if rm.get('parents')!=[c['receipts_folder_id']] or rm.get('driveId')!=c['source_drive_id'] or rm.get('properties',{}).get('mgsArchiveType')!='receipt':raise bridge.ArchiveError('RECEIPT_SCOPE')
    receipt=json.loads(d.raw(rf['id']))
    if receipt.get('status')=='blocked':raise bridge.ArchiveError('OWNER_BLOCKED:'+str(receipt.get('reason','UNKNOWN'))[:160])
    bridge.validate_receipt(job,receipt)
    ackfile=d.one(c['requests_folder_id'],'ack:'+jid);ackmeta=None;ack=None
    if ackfile:
        ackmeta=d.meta(ackfile['id']);bridge.require_publisher(ackmeta,bridge.CANONICAL_SA,'ACK_AUTHOR');ack=json.loads(d.raw(ackfile['id']))
        if ackmeta.get('parents')!=[c['requests_folder_id']] or ackmeta.get('driveId')!=c['source_drive_id'] or ack.get('schema')!='mgs.archive.ack.v1' or ack.get('jobId')!=jid or ack.get('kind')!=job['kind'] or ack.get('status')!='verified' or ack.get('deleteSource') is not False:raise bridge.ArchiveError('ACK_SCOPE')
    media=[]
    for asset in job['assets']:
        copied=next(x for x in receipt['assets'] if x['sourceId']==asset['sourceId'] and x['role']==asset['role'])
        media.append({'source':d.meta(asset['sourceId']),'archive':d.meta(copied['archiveId'])})
    frozen={'request':meta,'receipt_meta':rm,'receipt':receipt,'ack_meta':ackmeta,'ack':ack,'media':media}
    return {'pending':False,'acked':bool(ack) and props.get('mgsArchiveState')=='verified','fingerprint':hashlib.sha256(bridge.canonical(frozen)).hexdigest()}


def reconcile_jobs(d,c,jobs,state,apply,verify=bridge.reconcile,limit=2):
    import json
    out={'verified':[],'cached':[],'pending':[],'planned':[],'blocked':[],'deferred':0}
    for job in jobs:
        jid=job['jobId']
        try:
            snapshot=verification_snapshot(d,c,job)
            if snapshot.get('pending'):out['pending'].append(jid);continue
            old=state.get('verified',{}).get(jid)
            if old and old.get('verified') is True and old.get('fingerprint')==snapshot['fingerprint'] and snapshot['acked']:
                out['cached'].append(jid);continue
            if len(out['verified'])+len(out['planned'])>=limit:out['deferred']+=1;continue
            if not apply:out['planned'].append(jid);continue
            result=verify(d,c,jid,apply=True)
            if result.get('status')!='verified' or result.get('jobId')!=jid:raise bridge.ArchiveError('VERIFIER_NOT_COMPLETE')
            after=verification_snapshot(d,c,job)
            if after.get('pending') or not after.get('acked'):raise bridge.ArchiveError('VERIFIED_ACK_READBACK_REQUIRED')
            state.setdefault('verified',{})[jid]={'verified':True,'fingerprint':after['fingerprint'],'verified_at':bridge.now_iso()}
            out['verified'].append(jid)
        except (bridge.ArchiveError,KeyError,ValueError,StopIteration) as exc:
            out['blocked'].append({'job_id':jid,'reason':str(exc)[:200]})
    return out


def heartbeat_ready(hb,c,now=None):
    try:age=(bridge.timestamp(now or bridge.now_iso())-bridge.timestamp(hb['executedAt'])).total_seconds()
    except (bridge.ArchiveError,KeyError,TypeError):return False
    return (hb.get('schema')=='mgs.archive.heartbeat.v1' and hb.get('workerSha256')==c.get('worker_sha256') and hb.get('deleteSource') is False and hb.get('status')=='ok' and not hb.get('blocked') and hb.get('canaryAcknowledged') is True and bool(hb.get('triggerUid')) and -60<=age<=1200)


def choose_jobs(jobs,state):
    pending=[j for j in jobs if j['jobId'] not in state.get('verified',{})]
    cached=[j for j in jobs if j['jobId'] in state.get('verified',{})]
    selected=[]
    for name,rows,limit in [('pending_cursor',pending,14),('audit_cursor',cached,2)]:
        if not rows:continue
        start=int(state.get(name,0))%len(rows);count=min(limit,len(rows))
        selected.extend(rows[(start+i)%len(rows)] for i in range(count));state[name]=(start+count)%len(rows)
    return selected


def run_cycle(apply=False,reconcile_only=False):
    import json
    c=bridge.config_load()
    with bridge.queue_lock():
        state=bridge.read_json(bridge.DATA/'automation-state.json',{'schema':'mgs.archive.automation.v1'})
        if state.get('schema')!='mgs.archive.automation.v1':raise bridge.ArchiveError('AUTOMATION_STATE_SCHEMA')
        d=bridge.Drive(apply);bridge.preflight(d,c)
        beat=d.one(c['control_folder_id'],'heartbeat:worker-v1');hb={}
        if beat:
            bridge.require_publisher(d.meta(beat['id']),bridge.ACCOUNT,'HEARTBEAT_AUTHOR');hb=json.loads(d.raw(beat['id']))
        healthy=heartbeat_ready(hb,c)
        jobs=[]
        for path in sorted((bridge.DATA/'jobs').glob('job-*.json')):
            job=bridge.read_json(path)
            if not isinstance(job,dict):raise bridge.ArchiveError('LOCAL_JOB_SCHEMA')
            if not re.fullmatch(r'[a-f0-9]{32}',job.get('jobId','')) or path.name!='job-'+job['jobId']+'.json':raise bridge.ArchiveError('LOCAL_JOB_ID_MISMATCH')
            jobs.append(job)
        selected=choose_jobs(jobs,state);reconciliation=reconcile_jobs(d,c,selected,state,apply)
        inv=bridge.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
        rows=[json.loads(line) for line in inv.read_text().splitlines() if line.strip()]
        producer_config=dict(c)
        if reconcile_only or not healthy:producer_config['queue_enabled']=False
        def publish(row):return bridge.enqueue(d,c,bridge.job_for_lineage(d,c,row['asset_id']))
        production=enqueue_ready(rows,producer_config,state,apply,publish)
        blocked=reconciliation['blocked']+production['blocked']
        result={'schema':'mgs.archive.automation.tick.v1','status':'ok' if healthy and not blocked else 'blocked','executed_at':bridge.now_iso(),'apply':apply,'worker_ready':healthy,'worker_executed_at':hb.get('executedAt'),'worker_trigger_uid':hb.get('triggerUid'),'inventory_rows':len(rows),'jobs_total':len(jobs),'jobs_scanned':len(selected),'reconciliation':reconciliation,'production':production,'queue_enabled':c['queue_enabled'],'delete_source':False,'prefer_archive_reads':c.get('prefer_archive_reads',False),'include_historical':c.get('include_historical',False)}
        if apply:
            state['updated_at']=result['executed_at'];bridge.atomic_json(bridge.DATA/'automation-state.json',state);bridge.atomic_json(bridge.DATA/'automation-last-tick.json',result)
        return result


def main():
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--reconcile-only',action='store_true');args=parser.parse_args()
    try:result=run_cycle(args.apply,args.reconcile_only)
    except (bridge.ArchiveError,ValueError,KeyError,OSError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)[:200],'delete_source':False}));return 2
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='ok' else 2

if __name__=='__main__':raise SystemExit(main())
