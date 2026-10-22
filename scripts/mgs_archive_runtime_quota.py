#!/usr/bin/env python3
"""Immutable owner quota revision, explicitly authorized; never edits live code in place."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import mgs_backup_automation as a
AUTH='1562815497794363423'
BASE_SHA='d66ce978164bd525fa40de37df2672fe469413fa8e9c907f7d5af1d6d31b4c0f'
SOURCE=b.BASE/'integrations/creative-archive-30tb/WorkerBackupArchive.js'
POLICY=b.BASE/'integrations/creative-archive-30tb/RuntimeQuotaPolicy.js'
TARGET=b.BASE/'integrations/creative-archive-30tb/WorkerBackupArchiveMaxQuota.js'
ROLLBACK=a.m.DATA/('runtime-quota-rollback-'+AUTH+'.json')

def digest(raw):return hashlib.sha256(raw).hexdigest()

def build(raw,policy):
    if digest(raw)!=BASE_SHA:raise b.ArchiveError('RUNTIME_QUOTA_BASE_CHANGED')
    text=raw.decode('utf-8')
    replacements=[('ledger.reduce(function(n,p){return n+p[1];},0)>=3600000)', 'ledger.reduce(function(n,p){return n+p[1];},0)>=mgsArchiveBulkRuntimeLimit())'),('Date.now(),3600000,350)', 'Date.now(),mgsArchiveBulkRuntimeLimit(),350)')]
    for old,new in replacements:
        if text.count(old)!=1:raise b.ArchiveError('RUNTIME_QUOTA_REPLACEMENT_COUNT')
        text=text.replace(old,new)
    return text.encode()+b'\n'+policy

def prepare():
    raw=build(SOURCE.read_bytes(),POLICY.read_bytes())
    if TARGET.exists() and TARGET.read_bytes()!=raw:raise b.ArchiveError('RUNTIME_QUOTA_IMMUTABLE_TARGET_CHANGED')
    TARGET.write_bytes(raw)
    subprocess.run(['node','--check',str(TARGET)],check=True,capture_output=True)
    return {'status':'prepared_not_google_deployed','worker_sha256':digest(raw),'worker_source_path':str(TARGET.relative_to(b.BASE)),'consumer_limit_ms':90*60*1000,'workspace_policy_limit_ms':6*60*60*1000,'active_account_type':'consumer','authorization_message_id':AUTH}

def publish():
    prepared=prepare()
    with b.queue_lock():
        p,s=a.load();whole=b.read_json(a.m.DATA/'stage.json',{});c=b.config_load();d=b.Drive(True)
        revision=s.get('runtime_quota_revision')
        if revision:
            if revision.get('authorization_message_id')!=AUTH or revision.get('worker_sha256')!=prepared['worker_sha256']:raise b.ArchiveError('RUNTIME_QUOTA_REVISION_CONFLICT')
            if s.get('worker_sha256')==prepared['worker_sha256']:
                fid=s['worker_file_id'];b.require_publisher(d.meta(fid),b.CANONICAL_SA)
                if d.raw(fid)!=TARGET.read_bytes():raise b.ArchiveError('RUNTIME_QUOTA_REMOTE_DRIFT')
                sync_whole(whole,s)
                return s
        if s.get('worker_sha256')!=BASE_SHA or s.get('owner_accepted') is not False or s.get('automatic_archive_enabled') is not False:raise b.ArchiveError('RUNTIME_QUOTA_STAGE_MOVED_REVIEW_REQUIRED')
        if c['worker_sha256']!=s['previous_active_worker_sha256']:raise b.ArchiveError('RUNTIME_QUOTA_ACTIVE_PIN_CHANGED')
        b.preflight(d,c)
        # Full rollback baseline precedes any new remote publication and never resets usage.
        if not ROLLBACK.exists():b.atomic_json(ROLLBACK,{'authorization_message_id':AUTH,'captured_at':b.now_iso(),'backup_stage':s,'whole_stage':whole,'active_config':c})
        else:
            rollback=b.read_json(ROLLBACK)
            if not isinstance(rollback,dict) or rollback.get('authorization_message_id')!=AUTH or rollback.get('backup_stage',{}).get('worker_sha256')!=BASE_SHA:raise b.ArchiveError('RUNTIME_QUOTA_ROLLBACK_CONFLICT')
        revision={**prepared,'previous_staged_worker_file_id':s['worker_file_id'],'previous_staged_worker_sha256':BASE_SHA,'rollback_path':str(ROLLBACK.relative_to(b.BASE))}
        s['runtime_quota_revision']=revision;b.atomic_json(a.STAGE,s)
        fid=a.staged_blob(d,s,c['control_folder_id'],'worker:'+prepared['worker_sha256'],'worker_source',TARGET.read_bytes(),'worker-backup-max-quota-'+prepared['worker_sha256']+'.js','application/javascript')
        b.require_publisher(d.meta(fid),b.CANONICAL_SA)
        if d.raw(fid)!=TARGET.read_bytes():raise b.ArchiveError('RUNTIME_QUOTA_PUBLISH_READBACK')
        s.update(worker_file_id=fid,worker_sha256=prepared['worker_sha256'],worker_source_path=prepared['worker_source_path'],status='owner_repin_required_backup_archive',heartbeat_samples=[],owner_accepted=False,automatic_archive_enabled=False,published_at=b.now_iso())
        s['runtime_quota_revision'].update(status='published_awaiting_owner_repin',worker_file_id=fid)
        b.atomic_json(a.STAGE,s);sync_whole(whole,s)
        if a.load()[1]!=s or b.config_load()!=c:raise b.ArchiveError('RUNTIME_QUOTA_STAGE_READBACK_OR_ACTIVE_CHANGED')
        return s

def sync_whole(whole,s):
    if whole.get('worker_sha256') not in [BASE_SHA,s['worker_sha256']]:raise b.ArchiveError('RUNTIME_QUOTA_WHOLE_STAGE_CONFLICT')
    whole.update(worker_file_id=s['worker_file_id'],worker_sha256=s['worker_sha256'],worker_source_path=s['worker_source_path'],status=s['status'],owner_repin_confirmed=False,bulk_runtime_limit_unchanged=False,runtime_quota_authorization_message_id=AUTH,runtime_quota_consumer_limit_ms=90*60*1000,runtime_quota_workspace_policy_limit_ms=6*60*60*1000)
    b.atomic_json(a.m.DATA/'stage.json',whole)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','publish']);args=parser.parse_args()
    print(json.dumps({'prepare':prepare,'publish':publish}[args.action](),ensure_ascii=False))
