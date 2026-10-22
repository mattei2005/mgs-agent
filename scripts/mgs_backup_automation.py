#!/usr/bin/env python3
"""Future-only backup archive producer/reconciler; retention is PREVIEW ONLY.

Canonical SA publishes exact immutable requests. Only the deliberately pinned
owner worker can perform native moves. No delete/trash, new cron, credential or
source-uploader change is implemented here.
"""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import ares_archive_backfill as historical
import mgs_whole_drive_migration as m
import mgs_corporate_archive as corp
import mgs_backup_archive as backup
TIERS=backup.TIERS
AUTH='1562688137472249867'
BASE_SHA='bf9801376e8b0479271c41f7608661a21ae6edba47a6c9e7d32282466f9d3108'
PLAN=m.DATA/'backup-automation-plan.json'
STAGE=m.DATA/'backup-automation-stage.json'
STATE=m.DATA/'backup-automation-state.json'

def sha(value):return hashlib.sha256(value if isinstance(value,bytes) else b.canonical(value)).hexdigest()
def load():
 p=b.read_json(PLAN,{});s=b.read_json(STAGE,{})
 if p.get('schema')!='mgs.backup.archive.plan.v1' or p.get('authorizationMessageId')!=AUTH or p.get('migrationAuthorizationMessageId')!=m.AUTH or p.get('account')!=b.ACCOUNT or p.get('sourceDriveId')!=b.SOURCE_DRIVE or p.get('deleteSource') is not False or p.get('archiveTrashEnabled') is not False or p.get('retentionCount')!={'hourly':48,'daily':14,'weekly':8,'monthly':12} or sha(p)!=s.get('plan_sha256'):raise b.ArchiveError('BACKUP_AUTOMATION_PLAN_BINDING')
 if backup.load_binding()['source_root_id']!=p['sourceRootId']:raise b.ArchiveError('BACKUP_STAGING_BINDING_CHANGED')
 return p,s

def backup_asset(meta,p,tier):
 props=meta.get('appProperties') or {};mode='quick' if tier=='hourly' else 'full'
 if tier not in TIERS or meta.get('driveId')!=p['sourceDriveId'] or meta.get('parents')!=[p['tiers'][tier]['sourceId']] or meta.get('trashed') is not False or meta.get('mimeType')!='application/pgp-encrypted' or props.get('mgs_dr')!='true' or props.get('tier')!=tier or props.get('mode')!=mode or props.get('sha256')!=meta.get('sha256Checksum') or not re.fullmatch('[a-f0-9]{64}',meta.get('sha256Checksum','')) or not re.fullmatch('[a-f0-9]{32}',meta.get('md5Checksum','')) or not re.fullmatch('[1-9][0-9]*',str(meta.get('size',''))) or not re.fullmatch('[1-9][0-9]*',str(meta.get('version',''))) or not re.fullmatch('mgs-dr-'+tier+'-[0-9]{8}T[0-9]{6}Z\\.zip\\.gpg',meta.get('name','')):raise b.ArchiveError('BACKUP_SOURCE_MANAGED_CONTENT')
 if b.timestamp(meta.get('createdTime'))<b.timestamp(p['futureCreatedNotBefore']):raise b.ArchiveError('BACKUP_HISTORICAL_NOT_IN_FUTURE_LANE')
 return {'sourceId':meta['id'],'sourceParentId':meta['parents'][0],'name':meta['name'],'mimeType':meta['mimeType'],'sourceCreatedTime':meta['createdTime'],'version':meta['version'],'size':meta['size'],'md5':meta['md5Checksum'],'sha256':meta['sha256Checksum'],'tier':tier,'mode':mode,'destinationParentId':p['tiers'][tier]['archiveId'],'managedProperties':{k:props[k] for k in ['mgs_dr','tier','mode','sha256']}}

def check_content(meta,a):
 for k,v in [('id','sourceId'),('name','name'),('mimeType','mimeType'),('createdTime','sourceCreatedTime'),('size','size'),('md5Checksum','md5'),('sha256Checksum','sha256')]:
  if str(meta.get(k))!=str(a[v]):raise b.ArchiveError('BACKUP_FROZEN_CONTENT_CHANGED:'+k)
 if meta.get('trashed') is not False or not re.fullmatch('[1-9][0-9]*',str(meta.get('version',''))) or int(meta['version'])<int(a['version']):raise b.ArchiveError('BACKUP_FROZEN_VERSION_CHANGED')

def job_id(p,a):return sha([p['bindingSha256'],a['sourceId'],a['sourceParentId'],a['sha256']])[:32]

def retention_preview(rows,p,protected_ids):
 seen=set();candidates=[];sources=[];protected=[];unknown=[]
 for row in rows:
  if row['id'] in seen:raise b.ArchiveError('BACKUP_RETENTION_DUPLICATE_ID')
  seen.add(row['id'])
  if row['tier'] not in TIERS or row['location'] not in ['source','archive']:raise b.ArchiveError('BACKUP_RETENTION_SCOPE')
  b.timestamp(row['createdTime'])
 for tier in TIERS:
  ordered=sorted([x for x in rows if x['tier']==tier],key=lambda x:(b.timestamp(x['createdTime']),x['id']),reverse=True)
  for row in ordered[p['retentionCount'][tier]:]:
   if row['id'] in protected_ids:protected.append(row['id'])
   elif row['location']=='source':sources.append(row['id'])
   elif row.get('verified') is not True:unknown.append(row['id'])
   else:candidates.append(row['id'])
 return {'schema':'mgs.backup.retention.preview.v1','policy':p['retentionCount'],'archive_trash_candidates':candidates,'source_expired_preserved':sources,'protected_expired':protected,'unverified_expired':unknown,'deletion_enabled':False,'approval_required_before_any_trash':True,'scope_count':len(rows)}

def queue_object(d,c,fid,key,kind,author):
 meta=d.meta(fid);b.require_publisher(meta,author)
 if meta.get('driveId')!=b.SOURCE_DRIVE or meta.get('parents') not in [[c['requests_folder_id']],[c['receipts_folder_id']],[c['control_folder_id']]] or meta.get('properties',{}).get('mgsArchiveKey')!=key or meta.get('properties',{}).get('mgsArchiveType')!=kind:raise b.ArchiveError('BACKUP_QUEUE_OBJECT_SCOPE')
 raw=d.raw(fid)
 if sha(raw)!=meta.get('properties',{}).get('sha256'):raise b.ArchiveError('BACKUP_QUEUE_OBJECT_DIGEST')
 return json.loads(raw),meta

def immutable(d,parent,key,kind,body,state):
 """Crash-safe publication journal. An unresolved create never gets replayed."""
 entry=state.setdefault('publications',{}).get(key)
 raw=b.canonical(body)
 if entry and entry['sha256']!=sha(raw):raise b.ArchiveError('BACKUP_IMMUTABLE_BODY_CHANGED')
 if entry:
  found={'id':entry['file_id']} if entry.get('file_id') else d.one(parent,key)
  if not found:raise b.ArchiveError('BACKUP_PUBLICATION_UNCERTAIN_NO_REPLAY:'+key)
  fid=found['id']
  if d.raw(fid)!=raw:raise b.ArchiveError('BACKUP_IMMUTABLE_READBACK')
 else:
  state['publications'][key]={'sha256':sha(raw),'status':'intent'};b.atomic_json(STATE,state)
  fid=d.upload_once(parent,key+'.json',raw,'application/json',key,kind)
 meta=d.meta(fid);b.require_publisher(meta,b.CANONICAL_SA)
 if meta.get('parents')!=[parent] or d.raw(fid)!=raw:raise b.ArchiveError('BACKUP_PUBLICATION_READBACK')
 state['publications'][key].update(status='published',file_id=fid);b.atomic_json(STATE,state);return fid

def prepare():
 with b.queue_lock():
  if PLAN.exists():return load()[1]
  binding=backup.load_binding();cp,cs=corp.load_plan();d=b.Drive(False);c=b.config_load();setup=corp.verify_setup(d,c)
  if setup['status']!='corporate_setup_verified':raise b.ArchiveError('BACKUP_CORPORATE_SETUP_REQUIRED')
  result=backup.verify_pilot(d)
  if result['status']!='verified':raise b.ArchiveError('BACKUP_PILOT_RESTORE_REQUIRED')
  p={'schema':'mgs.backup.archive.plan.v1','authorizationMessageId':AUTH,'migrationAuthorizationMessageId':m.AUTH,'sharingConfirmationMessageId':corp.APPROVAL,'account':b.ACCOUNT,'ownerPermissionId':cp['ownerPermissionId'],'saPermissionId':'07414359829876449782','sourceDriveId':b.SOURCE_DRIVE,'sourceRootId':binding['source_root_id'],'corporateRootId':binding['corporate_root_id'],'archiveRootId':binding['archive_root_id'],'tiers':{t:{'sourceId':binding['tiers'][t]['source_id'],'archiveId':binding['tiers'][t]['archive_id']} for t in TIERS},'bindingSha256':sha(binding),'futureCreatedNotBefore':b.now_iso(),'retentionCount':binding['retention_count'],'principals':cp['principals'],'setupReceiptId':cs['setup_receipt_id'],'pilotId':result['file_id'],'pilotSha256':result['metadata']['sha256Checksum'],'pilotParentId':result['metadata']['parents'][0],'deleteSource':False,'archiveTrashEnabled':False,'maxMovesPerTick':1}
  s={'schema':'mgs.backup.archive.stage.v1','status':'prepared_not_published','plan_sha256':sha(p),'automatic_archive_enabled':False,'owner_accepted':False,'archive_trash_enabled':False,'heartbeat_samples':[],'created_at':b.now_iso()};b.atomic_json(PLAN,p);b.atomic_json(STAGE,s);b.atomic_json(STATE,{'schema':'mgs.backup.archive.state.v1','jobs':{},'publications':{}});return s

def publish():
 with b.queue_lock():
  p,s=load();d=b.Drive(True);c=b.config_load();b.preflight(d,c)
  base=b.BASE/'integrations/creative-archive-30tb/WorkerWholeDriveCorporateReceiptRecovery.js'
  if sha(base.read_bytes())!=BASE_SHA:raise b.ArchiveError('BACKUP_BASE_WORKER_CHANGED')
  fid=d.upload_once(c['control_folder_id'],'backup-automation-plan-'+s['plan_sha256']+'.json',b.canonical(p),'application/json','backup-plan:'+s['plan_sha256'],'backup_plan');b.require_publisher(d.meta(fid),b.CANONICAL_SA)
  raw=base.read_bytes()+b'\nvar MGS_BACKUP_PINS='+b.canonical({'planFileId':fid,'planSha256':s['plan_sha256']})+b';\n'+(b.BASE/'integrations/creative-archive-30tb/BackupArchiveExtension.js').read_bytes()
  source=b.BASE/'integrations/creative-archive-30tb/WorkerBackupArchive.js';source.write_bytes(raw)
  import subprocess
  check=subprocess.run(['node','--check',str(source)],capture_output=True,text=True)
  if check.returncode:raise b.ArchiveError('BACKUP_COMPOSITE_SYNTAX')
  digest=sha(raw);wf=d.upload_once(c['control_folder_id'],'worker-backup-archive-'+digest+'.js',raw,'application/javascript','worker:'+digest,'worker_source');meta=d.meta(wf);b.require_publisher(meta,b.CANONICAL_SA)
  if sha(d.raw(wf))!=digest or d.raw(fid)!=b.canonical(p):raise b.ArchiveError('BACKUP_NATIVE_SOURCE_READBACK')
  s.update(status='owner_repin_required_backup_archive',worker_file_id=wf,worker_sha256=digest,worker_source_path=str(source.relative_to(b.BASE)),plan_file_id=fid,previous_active_worker_file_id=c['worker_file_id'],previous_active_worker_sha256=c['worker_sha256'],published_at=b.now_iso());b.atomic_json(STAGE,s)
  whole=b.read_json(m.DATA/'stage.json');whole.update(worker_file_id=wf,worker_sha256=digest,worker_source_path=s['worker_source_path'],previous_active_worker_file_id=c['worker_file_id'],previous_active_worker_sha256=c['worker_sha256'],status=s['status'],owner_repin_confirmed=False,backup_archive_stage_path=str(STAGE.relative_to(b.BASE)));b.atomic_json(m.DATA/'stage.json',whole)
  return s

def heartbeat(d,c):
 f=d.one(c['control_folder_id'],'heartbeat:worker-v1')
 if not f:return None
 meta=d.meta(f['id']);b.require_publisher(meta,b.ACCOUNT)
 if meta.get('driveId')!=b.SOURCE_DRIVE or meta.get('parents')!=[c['control_folder_id']]:raise b.ArchiveError('BACKUP_HEARTBEAT_SCOPE')
 return json.loads(d.raw(f['id']))

def owner_ready(hb,s,p):
 if not hb:return False
 age=(b.timestamp(b.now_iso())-b.timestamp(hb.get('executedAt'))).total_seconds()
 bk=hb.get('backupArchive',{});probe=bk.get('probe',{})
 return hb.get('workerSha256')==s.get('worker_sha256') and hb.get('triggerUid')=='2456112746912022528' and hb.get('status')=='ok' and not hb.get('blocked') and hb.get('deleteSource') is False and hb.get('canaryAcknowledged') is True and -60<=age<=1200 and bk.get('planSha256')==s['plan_sha256'] and bk.get('archiveTrashEnabled') is False and probe.get('status')=='verified' and probe.get('pilotId')==p['pilotId'] and probe.get('pilotSha256')==p['pilotSha256'] and probe.get('ownerCanTrashPilot') is True

def resume_acceptance():
 if not STAGE.exists():return {'status':'not_prepared'}
 with b.queue_lock():
  p,s=load()
  if not s.get('worker_sha256'):return {'status':'not_published'}
  d=b.Drive(False);c=b.config_load();hb=heartbeat(d,c)
  if not owner_ready(hb,s,p):return {'status':'awaiting_healthy_new_owner_schedule','archive_trash_enabled':False}
  samples=s.setdefault('heartbeat_samples',[])
  if not any(x['executedAt']==hb['executedAt'] for x in samples):samples.append({k:hb[k] for k in ['executedAt','triggerUid','workerSha256']})
  s['heartbeat_samples']=samples[-2:];b.atomic_json(STAGE,s)
  if len(samples)<2:return {'status':'awaiting_second_scheduled_backup_heartbeat','archive_trash_enabled':False}
  accepted=s.get('owner_accepted') is True
 if not accepted:
  m.accept_owner()  # Existing complete verifier/promoter; acquires its own lock.
 with b.queue_lock():
  p,s=load();d=b.Drive(True);c=b.config_load();hb=heartbeat(d,c)
  if not owner_ready(hb,s,p) or c['worker_sha256']!=s['worker_sha256']:raise b.ArchiveError('BACKUP_ACCEPTANCE_CHANGED')
  state=b.read_json(STATE);activation={'schema':'mgs.backup.archive.activation.v1','authorizationMessageId':AUTH,'migrationAuthorizationMessageId':m.AUTH,'planSha256':s['plan_sha256'],'bindingSha256':p['bindingSha256'],'workerSha256':s['worker_sha256'],'archiveMovesEnabled':True,'archiveTrashEnabled':False,'deleteSource':False}
  fid=immutable(d,c['requests_folder_id'],'backup-activation:'+s['plan_sha256'],'backup_activation',activation,state)
  s.update(owner_accepted=True,automatic_archive_enabled=True,status='automatic_future_archive_enabled_awaiting_first_eligible',activation_file_id=fid,accepted_at=s.get('accepted_at') or b.now_iso());b.atomic_json(STAGE,s)
  return {'status':'accepted_backup_future_archive','archive_trash_enabled':False}

def reconcile(d,c,p,s,state,job):
 a=job['body']['asset'];rid=job['body']['receiptFileId'];meta=d.meta(rid)
 if (meta.get('lastModifyingUser') or {}).get('permissionId')=='07414359829876449782':return 'awaiting_owner'
 body,_=queue_object(d,c,rid,'backup-receipt:'+job['jobId'],'backup_move_receipt',b.ACCOUNT)
 if body.get('schema')!='mgs.backup.move.receipt.v1' or body.get('status')!='moved' or body.get('jobId')!=job['jobId'] or body.get('requestSha256')!=sha(job['body']) or body.get('planSha256')!=s['plan_sha256'] or body.get('sourceId')!=a['sourceId'] or body.get('archiveId')!=a['sourceId'] or body.get('destinationParentId')!=a['destinationParentId'] or body.get('deleteSource') is not False or body.get('archiveTrashEnabled') is not False:raise b.ArchiveError('BACKUP_OWNER_RECEIPT_BINDING')
 actual=backup.native_meta(d,a['sourceId']);check_content(actual,a);cp,cs=corp.load_plan()
 if actual.get('driveId') or actual.get('parents')!=[a['destinationParentId']] or not any(x.get('permissionId')==p['ownerPermissionId'] and x.get('emailAddress')==p['account'] for x in actual.get('owners',[])) or actual.get('appProperties')!=a['managedProperties']:raise b.ArchiveError('BACKUP_ARCHIVE_NATIVE_BINDING')
 corp.check_acl(corp.h.permissions(d,actual['id']),corp.desired(cp));fingerprint=sha({'metadata':actual,'receipt':body,'request':job['body']})
 if job.get('verified') and job.get('fingerprint')==fingerprint:return 'cached'
 hashes=d.hashes(actual['id'])
 if hashes!={'size':a['size'],'md5':a['md5'],'sha256':a['sha256']}:raise b.ArchiveError('BACKUP_ARCHIVE_STREAM_BYTES')
 after=backup.native_meta(d,a['sourceId'])
 if after!=actual:raise b.ArchiveError('BACKUP_CHANGED_DURING_STREAM')
 ack={'schema':'mgs.backup.archive.ack.v1','status':'verified','jobId':job['jobId'],'requestSha256':sha(job['body']),'archiveId':a['sourceId'],'sha256':a['sha256'],'size':a['size'],'archiveTrashEnabled':False,'deleteSource':False}
 ack_id=immutable(d,c['requests_folder_id'],'backup-ack:'+job['jobId'],'backup_ack',ack,state)
 d.api('PATCH','files/'+job['request_file_id'],{'supportsAllDrives':'true','fields':'id,properties'},{'properties':{'mgsArchiveState':'verified'}})
 if d.meta(job['request_file_id']).get('properties',{}).get('mgsArchiveState')!='verified':raise b.ArchiveError('BACKUP_REQUEST_VERIFY_MARKER')
 job.update(verified=True,fingerprint=fingerprint,ack_file_id=ack_id,verified_at=b.now_iso());b.atomic_json(STATE,state);return 'verified'

def enqueue(d,c,p,s,state,meta,tier):
 a=backup_asset(meta,p,tier);jid=job_id(p,a);job=state.setdefault('jobs',{}).get(jid)
 if job and job.get('request_file_id'):return jid
 b.require_publisher(d.meta(a['sourceId']),b.CANONICAL_SA)
 cp,_=corp.load_plan();corp.check_acl(corp.h.permissions(d,a['sourceId']),corp.desired(cp,True))
 slot={'schema':'mgs.backup.move.receipt.slot.v1','jobId':jid,'status':'awaiting_owner','planSha256':s['plan_sha256'],'sourceId':a['sourceId'],'deleteSource':False,'archiveTrashEnabled':False}
 slotid=immutable(d,c['receipts_folder_id'],'backup-receipt:'+jid,'backup_receipt_slot',slot,state)
 body={'schema':'mgs.backup.move.request.v1','jobId':jid,'authorizationMessageId':AUTH,'migrationAuthorizationMessageId':m.AUTH,'planSha256':s['plan_sha256'],'bindingSha256':p['bindingSha256'],'asset':a,'receiptFileId':slotid,'deleteSource':False,'archiveTrashEnabled':False}
 state['jobs'][jid]={'jobId':jid,'body':body,'verified':False};b.atomic_json(STATE,state)
 fid=immutable(d,c['requests_folder_id'],'backup-move:'+jid,'backup_move_request',body,state);state['jobs'][jid]['request_file_id']=fid;b.atomic_json(STATE,state)
 d.api('PATCH','files/'+fid,{'supportsAllDrives':'true','fields':'id,properties'},{'properties':{'mgsArchiveState':'queued'}})
 if d.meta(fid).get('properties',{}).get('mgsArchiveState')!='queued':raise b.ArchiveError('BACKUP_QUEUE_MARKER_READBACK')
 return jid

def cycle(apply=True):
 if not STAGE.exists():return {'status':'not_prepared','blocked':[],'archive_trash_enabled':False}
 acceptance=resume_acceptance() if apply else {'status':'dry_run'}
 with b.queue_lock():
  p,s=load();d=b.Drive(apply);c=b.config_load();state=b.read_json(STATE,{})
  if state.get('schema')!='mgs.backup.archive.state.v1':raise b.ArchiveError('BACKUP_AUTOMATION_STATE_SCHEMA')
  out={'status':s['status'],'acceptance':acceptance['status'],'queued':[],'verified':[],'pending':[],'blocked':[],'archive_trash_enabled':False,'delete_source':False,'retention_preview_only':True}
  jobs=state.get('jobs',{});pending=[j for j in jobs.values() if not j.get('verified')];audit=[j for j in jobs.values() if j.get('verified')][-1:]
  if apply:
   for job in (pending[:1]+audit):
    if not job.get('request_file_id'):continue
    try:
     status=reconcile(d,c,p,s,state,job);out['verified' if status in ['verified','cached'] else 'pending'].append(job['jobId'])
    except b.ArchiveError as error:out['blocked'].append({'job_id':job['jobId'],'reason':str(error)[:180]})
  rows=[];future=[]
  for tier in TIERS:
   for loc,parent in [('source',p['tiers'][tier]['sourceId']),('archive',p['tiers'][tier]['archiveId'])]:
    for meta in backup.children(d,parent,managed=True):
     props=meta.get('appProperties') or {}
     if props.get('tier')!=tier or props.get('sha256')!=meta.get('sha256Checksum'):raise b.ArchiveError('BACKUP_MANAGED_INVENTORY_CONFLICT')
     known=next((j for j in jobs.values() if j['body']['asset']['sourceId']==meta['id']),None)
     rows.append({'id':meta['id'],'tier':tier,'createdTime':meta['createdTime'],'location':loc,'verified':bool(known and known.get('verified')) or meta['id']==p['pilotId']})
     if loc=='source' and b.timestamp(meta['createdTime'])>=b.timestamp(p['futureCreatedNotBefore']):future.append((meta,tier))
  if apply and s.get('automatic_archive_enabled') and not out['blocked']:
   for meta,tier in sorted(future,key=lambda x:x[0]['createdTime']):
    a=backup_asset(meta,p,tier);jid=job_id(p,a)
    if jid in jobs and jobs[jid].get('request_file_id'):continue
    out['queued'].append(enqueue(d,c,p,s,state,meta,tier));break
  protected={p['pilotId']};last=b.read_json(backup.BACKUP_STATE,{}).get('last_restore_test',{}).get('remote_file_id')
  if last:protected.add(last)
  preview=retention_preview(rows,p,protected);out['retention_preview_counts']={k:len(preview[k]) for k in ['archive_trash_candidates','source_expired_preserved','protected_expired','unverified_expired']};out['future_source_backlog']=len(future)
  if out['blocked']:out['status']='blocked'
  if apply:
   b.atomic_json(m.DATA/'backup-retention-preview.json',preview);b.atomic_json(m.DATA/'backup-automation-last-tick.json',{'executed_at':b.now_iso(),**out});b.atomic_json(STATE,state)
  return out

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','publish','tick','preview']);args=parser.parse_args()
 out={'prepare':prepare,'publish':publish,'tick':lambda:cycle(True),'preview':lambda:cycle(False)}[args.action]();print(json.dumps(out));return 2 if out.get('status')=='blocked' else 0
if __name__=='__main__':raise SystemExit(main())
