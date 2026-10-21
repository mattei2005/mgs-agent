#!/usr/bin/env python3
"""Exact frozen-acervo copy phase. Never deletes sources or changes business IDs.
Owner runs the pinned WorkerBackfill; canonical SA enqueues/verifies/ACKs. The
historical deletion gate remains closed until ALL copies and consumers pass.
"""
from __future__ import annotations
import sys,json,hashlib,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
MIGRATION='1562256530454220851';CONFIRMATION='1562268909686497422'
WRITERS={'newnicolasholanda@gmail.com','criativosevo@gmail.com','iallynitasc@gmail.com','mattei2005@gmail.com','isliago89@gmail.com','support@matteiservicesinc.com','georgeicaro2307@gmail.com','geizianpereira@gmail.com','joewillams2009@gmail.com'}
class BackfillError(b.ArchiveError):pass
def location():return b.DATA/('historical-migration-'+MIGRATION)
def obj(path,default=None):
 v=b.read_json(path,default)
 if not isinstance(v,dict):raise BackfillError('BACKFILL_JSON_OBJECT:'+Path(path).name)
 return v

def manifest_load():
 p=location();stage=obj(p/'stage.json');m=obj(p/'manifest.json');auth=obj(p/'authorization.json')
 if stage['manifest_sha256']!=hashlib.sha256(b.canonical(m)).hexdigest() or m.get('migrationId')!=MIGRATION or m.get('authorizationMessageId')!=CONFIRMATION or m.get('deleteSource') is not False or auth.get('historical_retirement_confirmation_message_id')!=CONFIRMATION or auth.get('confirmed_by_user_id')!='344196393512075265' or m.get('sourceRootId')!=b.SOURCE_ROOT or m.get('sourceDriveId')!=b.SOURCE_DRIVE or m.get('archiveRootId')!=b.ARCHIVE_ROOT or m.get('account')!=b.ACCOUNT:raise BackfillError('BACKFILL_MANIFEST_AUTHORITY')
 if len(m['assets'])!=5860 or len({a['sourceId'] for a in m['assets']})!=5860 or len(m['folderPaths'])!=844 or len(m['shortcuts'])!=1002:raise BackfillError('BACKFILL_MANIFEST_SET')
 return m,stage

def make_job(assets,c,stage):
 if not 1<=len(assets)<=8 or len({a['sourceId'] for a in assets})!=len(assets):raise BackfillError('BACKFILL_EXACT_BATCH_BOUND')
 identity={'schema':'mgs.archive.request.v1','kind':'backfill','account':c['account'],'sourceDriveId':c['source_drive_id'],'sourceRootId':c['source_root_id'],'archiveRootId':c['archive_root_id'],'deleteSource':False,'migrationId':stage['migration_id'],'manifestFileId':stage['manifest_file_id'],'manifestSha256':stage['manifest_sha256'],'assets':json.loads(b.canonical(assets))}
 identity['jobId']=hashlib.sha256(b.canonical(identity)).hexdigest()[:32];identity['createdAt']=b.now_iso();return identity

def permissions(d,fid):
 out=[];page=None
 while True:
  params={'supportsAllDrives':'true','fields':'nextPageToken,permissions(id,type,emailAddress,role)','pageSize':100}
  if page:params['pageToken']=page
  value=d.api('GET','files/'+fid+'/permissions',params);out.extend(value.get('permissions',[]));page=value.get('nextPageToken')
  if len(out)>1000:raise BackfillError('BACKFILL_PERMISSION_SCOPE_LIMIT')
  if not page:return out

def source_access(d,a,c):
 m=d.meta(a['sourceId']);b.validate_source_metadata(m,a,c)
 if d.relative_parent(m['parents'][0],b.SOURCE_ROOT)!=a['relativeParent']:raise BackfillError('BACKFILL_SOURCE_PATH_CHANGED')
 # files.get omits permissions for Shared-Drive files. The exact paginated
 # permissions endpoint is the access gate, not an empty metadata projection.
 humans={p.get('emailAddress') for p in permissions(d,a['sourceId']) if p.get('role') in ['reader','writer','owner','organizer','fileOrganizer']}
 if not WRITERS<=humans:raise BackfillError('BACKFILL_SOURCE_HUMAN_ACL_NOT_PARITY')
 return m

def enqueue(d,c,job):
 p=location();(p/'jobs').mkdir(exist_ok=True);path=p/'jobs'/('job-'+job['jobId']+'.json');old=b.read_json(path)
 if old:
  if any(old.get(k)!=job.get(k) for k in ['assets','manifestSha256','migrationId','kind']):raise BackfillError('BACKFILL_IMMUTABLE_JOB_CONFLICT')
  job=old
 else:b.atomic_json(path,job)
 fid=d.upload_once(c['requests_folder_id'],'backfill-'+job['jobId']+'.json',b.canonical(job),'application/json','request:'+job['jobId'],'backfill_request');meta=d.meta(fid);b.require_publisher(meta,b.CANONICAL_SA)
 if meta.get('properties',{}).get('mgsArchiveType')!='backfill_request' or d.raw(fid)!=b.canonical(job):raise BackfillError('BACKFILL_QUEUE_READBACK')
 if meta['properties'].get('mgsArchiveState')!='verified':
  props={**meta['properties'],'mgsArchiveState':'queued'};d.api('PATCH','files/'+fid,{'supportsAllDrives':'true','fields':'id,properties'},{'properties':props})
  if d.meta(fid)['properties'].get('mgsArchiveState')!='queued':raise BackfillError('BACKFILL_QUEUE_STATE_READBACK')
 return {'job_id':job['jobId'],'request_file_id':fid,'asset_count':len(job['assets']),'old_worker_cannot_consume':True}

def prepare_first():
 m,stage=manifest_load()
 with b.queue_lock():
  d=b.Drive(True);c=b.config_load();b.preflight(d,c)
  # First legitimate historical batch, not a synthetic production candidate.
  order=sorted(m['assets'],key=lambda a:(a['sourceCreatedTime'],a['sourceId']));chosen=order[:8]
  for a in chosen:source_access(d,a,c)
  result=enqueue(d,c,make_job(chosen,c,stage));stage['prepared_first_job']=result;stage['status']='owner_repin_required_hidden_first_batch_ready';b.atomic_json(location()/'stage.json',stage)
 return result

def verify_job(d,c,job,apply=False):
 req=d.one(c['requests_folder_id'],'request:'+job['jobId'])
 if not req:raise BackfillError('BACKFILL_REQUEST_MISSING')
 qm=d.meta(req['id']);b.require_publisher(qm,b.CANONICAL_SA)
 if qm.get('parents')!=[c['requests_folder_id']] or qm.get('properties',{}).get('mgsArchiveType')!='backfill_request' or d.raw(req['id'])!=b.canonical(job):raise BackfillError('BACKFILL_REQUEST_CHANGED')
 found=d.one(c['receipts_folder_id'],'receipt:'+job['jobId'])
 if not found:return {'status':'pending','job_id':job['jobId']}
 rm=d.meta(found['id']);b.require_publisher(rm,b.ACCOUNT)
 if rm.get('parents')!=[c['receipts_folder_id']]:raise BackfillError('BACKFILL_RECEIPT_PARENT')
 receipt=json.loads(d.raw(found['id']));b.validate_receipt(job,receipt);verified=[]
 for a in job['assets']:
  target=next(x for x in receipt['assets'] if x['sourceId']==a['sourceId'] and x['role']=='historical');meta=d.meta(target['archiveId']);source_access(d,a,c)
  if meta.get('trashed') or meta.get('driveId') or meta.get('name')!=a['name'] or meta.get('mimeType')!=a['mimeType'] or str(meta.get('size'))!=a['size'] or meta.get('md5Checksum')!=a['md5'] or not any(x.get('emailAddress')==b.ACCOUNT for x in meta.get('owners',[])) or len(meta.get('parents',[]))!=1 or d.relative_parent(meta['parents'][0],b.ARCHIVE_ROOT)!=a['relativeParent']:raise BackfillError('BACKFILL_COPY_IDENTITY_OR_PATH')
  if any(x.get('type') in ['anyone','domain'] for x in meta.get('permissions',[])):raise BackfillError('BACKFILL_COPY_PUBLIC')
  native_permissions=permissions(d,meta['id'])
  if any(x.get('type') in ['anyone','domain'] for x in native_permissions):raise BackfillError('BACKFILL_COPY_PUBLIC')
  writers={x.get('emailAddress') for x in native_permissions if x.get('role')=='writer'}
  if not WRITERS<=writers or b.CANONICAL_SA not in writers:raise BackfillError('BACKFILL_COPY_HUMAN_ACCESS')
  expected={k:a[k] for k in ['size','md5','sha256']}
  if d.hashes(a['sourceId'])!=expected or d.hashes(meta['id'])!=expected:raise BackfillError('BACKFILL_BINARY_MISMATCH')
  source_access(d,a,c);verified.append({'source_id':a['sourceId'],'archive_id':meta['id'],'archive_parent_id':meta['parents'][0],'name':a['name'],'mime_type':a['mimeType'],'relative_parent':a['relativeParent'],'size':a['size'],'md5':a['md5'],'sha256':a['sha256'],'owner':b.ACCOUNT,'verified':True,'job_id':job['jobId']})
 result={'schema':'mgs.archive.backfill.verification.v1','status':'verified','job_id':job['jobId'],'assets':verified,'primary_identifiers_changed':False,'source_deleted':False,'verified_at':b.now_iso()}
 if apply:
  p=location();idx=obj(p/'backfill-index.json',{'mappings':{},'verified_jobs':{}})
  for entry in verified:
   prior=idx['mappings'].get(entry['source_id'])
   if prior and any(prior[k]!=entry[k] for k in ['archive_id','sha256']):raise BackfillError('BACKFILL_MAPPING_CONFLICT')
   idx['mappings'][entry['source_id']]=entry
  idx['verified_jobs'][job['jobId']]=result;b.atomic_json(p/'backfill-index.json',idx);(p/'verified').mkdir(exist_ok=True);b.atomic_json(p/'verified'/('verified-'+job['jobId']+'.json'),result)
  ack={'schema':'mgs.archive.backfill.ack.v1','migrationId':MIGRATION,'jobId':job['jobId'],'status':'verified','deleteSource':False,'assets':verified};d.upload_once(c['requests_folder_id'],'backfill-ack-'+job['jobId']+'.json',b.canonical(ack),'application/json','backfill-ack:'+job['jobId'],'backfill_ack')
  properties={**qm['properties'],'mgsArchiveState':'verified'};d.api('PATCH','files/'+req['id'],{'supportsAllDrives':'true','fields':'id,properties'},{'properties':properties})
  if d.meta(req['id'])['properties'].get('mgsArchiveState')!='verified':raise BackfillError('BACKFILL_VERIFIED_STATE_READBACK')
 return result

def cycle_locked(d,c,apply=False):
 m,stage=manifest_load();p=location();idx=obj(p/'backfill-index.json',{'mappings':{},'verified_jobs':{}});result={'status':'awaiting_owner_repin','migration_id':MIGRATION,'owner_ready':False,'verified_files':len(idx['mappings']),'total_files':len(m['assets']),'queued_jobs':[],'verified_jobs':[],'pending_jobs':[],'blocked':[],'historical_cleanup_enabled':False}
 beat=d.one(c['control_folder_id'],'heartbeat:worker-v1')
 if not beat:return result
 b.require_publisher(d.meta(beat['id']),b.ACCOUNT);hb=json.loads(d.raw(beat['id']));expected=stage.get('worker_sha256')
 if not expected or hb.get('workerSha256')!=expected:return result
 if not hb.get('triggerUid') or hb.get('status')!='ok' or hb.get('blocked'):raise BackfillError('BACKFILL_OWNER_HEARTBEAT_NOT_READY')
 age=(b.timestamp(b.now_iso())-b.timestamp(hb['executedAt'])).total_seconds()
 if not -60<=age<=1200:raise BackfillError('BACKFILL_OWNER_STALE')
 result.update(owner_ready=True,status='copying')
 localjobs=[obj(path) for path in sorted((p/'jobs').glob('job-*.json'))];pending=[j for j in localjobs if j['jobId'] not in idx['verified_jobs']]
 for job in pending[:4]:
  try:
   verdict=verify_job(d,c,job,apply)
   if verdict['status']=='verified':result['verified_jobs'].append(job['jobId'])
   else:result['pending_jobs'].append(job['jobId'])
  except b.ArchiveError as exc:result['blocked'].append({'job_id':job['jobId'],'reason':str(exc)[:220]})
 if apply and not result['blocked']:
  idx=obj(p/'backfill-index.json',{'mappings':{},'verified_jobs':{}});already={a['sourceId'] for j in localjobs for a in j['assets']};left=[a for a in m['assets'] if a['sourceId'] not in already];open_count=sum(j['jobId'] not in idx['verified_jobs'] for j in localjobs)
  for start in range(0,min(len(left),max(0,min(4,12-open_count))*8),8):
   chunk=left[start:start+8]
   try:
    for asset in chunk:source_access(d,asset,c)
    result['queued_jobs'].append(enqueue(d,c,make_job(chunk,c,stage)))
   except b.ArchiveError as exc:result['blocked'].append({'source_ids':[a['sourceId'] for a in chunk],'reason':str(exc)[:220]});break
  result['verified_files']=len(idx['mappings'])
 if result['blocked']:result['status']='blocked'
 if result['verified_files']==len(m['assets']):result['status']='all_bytes_verified_consumer_cutover_pending'
 if apply:b.atomic_json(p/'last-tick.json',{'executed_at':b.now_iso(),**result})
 return result

def accept_owner():
 m,stage=manifest_load()
 with b.queue_lock():
  d=b.Drive(True);c=b.config_load();proof=cycle_locked(d,c,apply=False)
  if not proof['owner_ready']:raise BackfillError('BACKFILL_NEW_OWNER_PIN_NOT_LIVE')
  first=stage.get('prepared_first_job',{}).get('job_id')
  if first not in proof['verified_jobs']:raise BackfillError('BACKFILL_FIRST_REAL_BATCH_VERIFICATION_REQUIRED')
  verify_job(d,c,obj(location()/'jobs'/('job-'+first+'.json')),apply=True)
  c.update(worker_file_id=stage['worker_file_id'],worker_sha256=stage['worker_sha256'],active_worker_source_path='integrations/creative-archive-30tb/WorkerBackfill.js');b.atomic_json(b.CONFIG,c);stage.update(copy_enabled=True,status='copying');b.atomic_json(location()/'stage.json',stage)
  if b.config_load()!=c:raise BackfillError('BACKFILL_ACTIVE_CONFIG_READBACK')
 return proof

def main():
 import argparse
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['status','prepare-first','cycle','accept-owner']);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 if args.action=='prepare-first':result=prepare_first()
 elif args.action=='accept-owner':result=accept_owner()
 else:
  with b.queue_lock():result=cycle_locked(b.Drive(args.apply),b.config_load(),args.apply if args.action=='cycle' else False)
 print(json.dumps(result,ensure_ascii=False));return 0 if result.get('status')!='blocked' else 2
if __name__=='__main__':raise SystemExit(main())
