#!/usr/bin/env python3
"""Confirmed owner-only 30TB backup retention: trash, never DELETE.

Original move plans/requests remain immutable. This separate policy protects
source/unverified backups, the pilot and latest actual PASS restore generation.
"""
from __future__ import annotations
import argparse,fcntl,json,urllib.request,urllib.parse,urllib.error
import ares_archive_bridge as b
import mgs_backup_automation as a
import mgs_backup_archive as backup
import mgs_archive_owner_transport as t
AUTH='1563192086025474101'
HOME=t.HOME/'backup-retention'
POLICY=HOME/'policy.json'
STATE=HOME/'state.json'
COUNTS={'hourly':48,'daily':14,'weekly':8,'monthly':12}

def validate_policy(value,p):
    expected={'schema':'mgs.archive.backup.retention.v1','confirmation_message_id':AUTH,'confirmation_user_id':'344196393512075265','confirmation_thread_id':'1562078493498540042','archive_root_id':p['archiveRootId'],'account':b.ACCOUNT,'retention_count':COUNTS,'action':'trash_only','permanent_delete':False,'protect_latest_pass_restore':True,'protect_pilot':True}
    if not isinstance(value,dict) or any(value.get(k)!=v for k,v in expected.items()):raise b.ArchiveError('RETENTION_POLICY_BINDING')
    if type(value.get('active')) is not bool:raise b.ArchiveError('RETENTION_ACTIVE_TYPE')
    return value

def protected(p):
    restore=b.read_json(backup.BACKUP_STATE,{}).get('last_restore_test',{})
    if restore.get('status')!='PASS' or not restore.get('remote_file_id') or not restore.get('download_sha256') or not restore.get('isolated_only'):raise b.ArchiveError('RETENTION_RESTORE_PROOF_REQUIRED')
    return {p['pilotId'],restore['remote_file_id']},restore

def select(rows,p,protected_ids):
    return a.retention_preview(rows,p,protected_ids)['archive_trash_candidates']

def inspect(sa,p):
    state=b.read_json(a.STATE,{});jobs=state.get('jobs',{})
    verified={j['body']['asset']['sourceId']:j for j in jobs.values() if j.get('verified') is True and j.get('ack_file_id')}
    protected_ids,restore=protected(p);rows=[];metas={}
    for tier in backup.TIERS:
        for location,parent in [('source',p['tiers'][tier]['sourceId']),('archive',p['tiers'][tier]['archiveId'])]:
            for meta in backup.children(sa,parent,managed=True):
                props=meta.get('appProperties',{})
                if props.get('tier')!=tier or props.get('mgs_dr')!='true' or props.get('sha256')!=meta.get('sha256Checksum') or meta.get('parents')!=[parent]:raise b.ArchiveError('RETENTION_MANAGED_INVENTORY')
                rows.append({'id':meta['id'],'tier':tier,'createdTime':meta['createdTime'],'location':location,'verified':meta['id'] in verified or meta['id']==p['pilotId']});metas[meta['id']]=meta
    candidates=select(rows,p,protected_ids)
    return {'rows':rows,'metadata':metas,'candidates':candidates,'protected_ids':sorted(protected_ids),'restore':restore,'jobs':verified}

def prepare(active=False):
    p,s=a.load();HOME.mkdir(parents=True,exist_ok=True)
    value=b.read_json(POLICY)
    if value is None:
        value={'schema':'mgs.archive.backup.retention.v1','confirmation_message_id':AUTH,'confirmation_user_id':'344196393512075265','confirmation_thread_id':'1562078493498540042','archive_root_id':p['archiveRootId'],'account':b.ACCOUNT,'retention_count':COUNTS,'action':'trash_only','permanent_delete':False,'protect_latest_pass_restore':True,'protect_pilot':True,'active':False,'confirmed_at_source':'discord:message:'+AUTH}
    validate_policy(value,p);protected(p)
    if active:value={**value,'active':True,'activated_at':value.get('activated_at') or b.now_iso()}
    b.atomic_json(POLICY,value)
    if b.read_json(POLICY)!=value:raise b.ArchiveError('RETENTION_POLICY_READBACK')
    return value

def trash_once(owner,fid,parent,expected):
    # No reusable general-purpose PATCH/DELETE route. Exact archived ciphertext
    # and current metadata gate are checked immediately before the single RPC.
    observed=backup.native_meta(owner,fid)
    for k in ['id','name','size','md5Checksum','sha256Checksum','parents','version','createdTime','trashed']:
        if observed.get(k)!=expected.get(k):raise b.ArchiveError('RETENTION_OWNER_CAS:'+k)
    if observed.get('parents')!=[parent] or observed.get('driveId') or observed.get('trashed') is not False or observed.get('mimeType')!='application/pgp-encrypted' or observed.get('capabilities',{}).get('canTrash') is not True or not any(o.get('emailAddress')==b.ACCOUNT for o in observed.get('owners',[])):raise b.ArchiveError('RETENTION_OWNER_SCOPE')
    url=owner.base+'files/'+fid+'?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':'id,trashed,parents'})
    req=urllib.request.Request(url,data=b.canonical({'trashed':True}),headers={'Authorization':'Bearer '+owner.token,'Content-Type':'application/json'},method='PATCH')
    try:
        with urllib.request.urlopen(req,timeout=90) as response:json.load(response)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):
        # The caller reconciles by exact ID; never retry an unknown mutation.
        pass
    return backup.native_meta(owner,fid)

def tick(apply=False,max_files=1):
    if not 1<=max_files<=2:raise b.ArchiveError('RETENTION_BATCH_BOUNDS')
    HOME.mkdir(parents=True,exist_ok=True)
    with (t.HOME/'backup-lane'/'backup-lane.lock').open('a+') as lane:
        fcntl.flock(lane,fcntl.LOCK_EX)
        with b.queue_lock():
            p,s=a.load();policy=b.read_json(POLICY);validate_policy(policy,p)
            sa=b.Drive();view=inspect(sa,p)
            out={'schema':'mgs.archive.backup.retention.tick.v1','executed_at':b.now_iso(),'status':'ok','active':policy['active'],'confirmation_message_id':AUTH,'action':'trash_only','permanent_delete':False,'candidates':view['candidates'],'protected_ids':view['protected_ids'],'trashed':[],'blocked':[]}
            if not apply:return out
            if not policy['active']:raise b.ArchiveError('RETENTION_NOT_ACTIVE')
            state=b.read_json(STATE,{'schema':'mgs.archive.backup.retention.state.v1','intents':{}})
            if state.get('schema')!='mgs.archive.backup.retention.state.v1':raise b.ArchiveError('RETENTION_STATE_SCHEMA')
            owner=t.OwnerDrive()
            # Reconcile previously landed intents, never resubmit them.
            for fid,intent in state['intents'].items():
                if intent.get('status')=='verified':continue
                actual=backup.native_meta(sa,fid)
                if actual.get('trashed') is not True:raise b.ArchiveError('RETENTION_AMBIGUOUS_NO_REPLAY:'+fid)
                intent.update(status='verified',verified_at=b.now_iso());b.atomic_json(STATE,state)
            for fid in view['candidates'][:max_files]:
                if fid in state['intents']:continue
                # Recompute policy and last restore immediately before mutation.
                fresh=inspect(sa,p)
                if fid not in fresh['candidates'] or fid in fresh['protected_ids']:raise b.ArchiveError('RETENTION_SELECTION_CHANGED')
                expected=fresh['metadata'][fid];job=fresh['jobs'][fid];asset=job['body']['asset']
                a.check_content(expected,asset)
                ack,ackmeta=a.queue_object(sa,b.config_load(),job['ack_file_id'],'backup-ack:'+job['jobId'],'backup_ack',b.CANONICAL_SA)
                if ack.get('status')!='verified' or ack.get('archiveId')!=fid or ack.get('sha256')!=asset['sha256'] or ack.get('requestSha256')!=a.sha(job['body']):raise b.ArchiveError('RETENTION_NATIVE_ACK_REQUIRED')
                state['intents'][fid]={'status':'intent','confirmation_message_id':AUTH,'metadata_before':expected,'job_id':job['jobId'],'ack_id':job['ack_file_id'],'protected_ids':fresh['protected_ids'],'started_at':b.now_iso()};b.atomic_json(STATE,state)
                actual=trash_once(owner,fid,asset['destinationParentId'],expected)
                reread=backup.native_meta(sa,fid)
                if actual.get('trashed') is not True or reread.get('trashed') is not True or reread.get('parents')!=expected.get('parents') or any(reread.get(k)!=expected.get(k) for k in ['id','size','md5Checksum','sha256Checksum','appProperties']):raise b.ArchiveError('RETENTION_TRASH_READBACK_FAILED')
                state['intents'][fid].update(status='verified',verified_at=b.now_iso(),metadata_after=reread);b.atomic_json(STATE,state);out['trashed'].append(fid)
                with (b.BASE/'logs/events-audit.jsonl').open('a') as log:
                    fcntl.flock(log,fcntl.LOCK_EX);log.write(json.dumps({'at':b.now_iso(),'actor':'zeus','action':'30tb_backup_retention_trash_verified','confirmation_message_id':AUTH,'file_id':fid,'job_id':job['jobId'],'permanent_delete':False})+'\n')
            b.atomic_json(HOME/'last-tick.json',out);return out

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','activate','preview','tick']);parser.add_argument('--apply',action='store_true');parser.add_argument('--max-files',type=int,default=1);args=parser.parse_args()
    if args.action in ['activate','tick'] and not args.apply:raise SystemExit('APPLY_REQUIRED')
    result=prepare(args.action=='activate') if args.action in ['prepare','activate'] else tick(args.action=='tick',args.max_files)
    print(json.dumps(result,ensure_ascii=False))
