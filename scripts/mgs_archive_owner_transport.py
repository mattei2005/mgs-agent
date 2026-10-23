#!/usr/bin/env python3
"""Isolated owner-authorized VPS archive transport. Copy-only, no agent fallback.
Native SA requests/ACKs and independent full binary verification remain canonical.
"""
from __future__ import annotations
import argparse,contextlib,datetime,fcntl,hashlib,json,os,re,sys,time,threading,urllib.request,urllib.parse,urllib.error,uuid
from pathlib import Path
from typing import Any
import ares_archive_bridge as b
import ares_archive_backfill as h
import mgs_archive_owner_auth as auth
REQUEST_TYPE='vps_backfill_request'
HEARTBEAT_KEY='heartbeat:vps-owner-v1'
HOME=auth.HOME
CONTRACT=HOME/'executor-contract.json'
STATE=HOME/'executor-state.json'
DRAIN_SECONDS=420
ASSET_KEYS=['role','sourceId','sourceParentId','name','mimeType','size','md5','sha256','version','relativeParent','sourceCreatedTime']
class TransportError(b.ArchiveError):pass

def validate_path(names):
 if not isinstance(names,list) or len(names)>12 or any(not isinstance(n,str) or not n or n in ['.','..'] or any(c in n for c in '/\\\x00') for n in names):raise TransportError('PATH_SCOPE')
 return True

def validate_job(j,c,manifest,stage):
 if j.get('kind')=='lineage':
  expected=b.make_request(c,j.get('assets',[]),kind='lineage',lineage_id=j.get('lineageId'),validation_only=j.get('validationOnly',False))
  if {k:v for k,v in expected.items() if k!='createdAt'}!={k:v for k,v in j.items() if k!='createdAt'}:raise TransportError('JOB_DIGEST_OR_LINEAGE_SCOPE')
  return True
 for k,v in {'schema':'mgs.archive.request.v1','kind':'backfill','account':c['account'],'sourceDriveId':c['source_drive_id'],'sourceRootId':c['source_root_id'],'archiveRootId':c['archive_root_id'],'deleteSource':False,'migrationId':stage['migration_id'],'manifestFileId':stage['manifest_file_id'],'manifestSha256':stage['manifest_sha256']}.items():
  if j.get(k)!=v or (k=='deleteSource' and j.get(k) is not False):raise TransportError('JOB_SCOPE:'+k)
 assets=j.get('assets');allowed={a['sourceId']:a for a in manifest['assets']}
 if not isinstance(assets,list) or not 1<=len(assets)<=8 or len({a.get('sourceId') for a in assets})!=len(assets):raise TransportError('JOB_ASSET_SET')
 for a in assets:
  expected=allowed.get(a.get('sourceId'))
  if not expected or any(a.get(k)!=expected.get(k) for k in ASSET_KEYS):raise TransportError('ASSET_NOT_FROZEN')
  validate_path(a['relativeParent'])
  if a['role']!='historical' or str(a['size']).isdigit() is False or int(a['size'])<0 or not re.fullmatch('[a-f0-9]{32}',a['md5']) or not re.fullmatch('[a-f0-9]{64}',a['sha256']):raise TransportError('ASSET_FIELDS')
  if a['mimeType'].startswith('application/vnd.google-apps/'):raise TransportError('NATIVE_DOCUMENT_EXCLUDED')
 if any(a['sourceId'] in stage.get('metadata_reconciled_ids',[]) for a in assets) and j.get('metadataReconciliationSha256')!=stage.get('metadata_reconciliation_sha256'):raise TransportError('JOB_METADATA_RECONCILIATION_BINDING')
 identity={k:v for k,v in j.items() if k not in ['jobId','createdAt']}
 if hashlib.sha256(b.canonical(identity)).hexdigest()[:32]!=j.get('jobId'):raise TransportError('JOB_DIGEST')
 return True

def validate_copy(m,a,parent,c):
 expected={'name':a['name'],'mimeType':a['mimeType'],'size':str(a['size']),'md5Checksum':a['md5']}
 if m.get('id')==a['sourceId'] or m.get('trashed') is not False or m.get('driveId') or m.get('parents')!=[parent] or any(str(m.get(k))!=v for k,v in expected.items()):raise TransportError('COPY_SCOPE_OR_METADATA')
 if m.get('sha256Checksum') is not None and m['sha256Checksum']!=a['sha256']:raise TransportError('COPY_NATIVE_SHA')
 if not any(o.get('emailAddress')==c['account'] and o.get('permissionId')==b.PUBLISHER_PERMISSION_IDS[c['account']] for o in m.get('owners',[])):raise TransportError('COPY_NATIVE_OWNER')
 if any(p.get('type') in ['anyone','domain'] for p in m.get('permissions',[])):raise TransportError('COPY_PUBLIC')
 return True

def drain_elapsed(proof,now=None):
 return proof.get('phase')=='draining' and (b.timestamp(now or b.now_iso())-b.timestamp(proof['reserved_at'])).total_seconds()>=DRAIN_SECONDS

def select_canary(assets,queued,mapped,processed):
 eligible=[a for a in assets if a['sourceId'] in processed and a['sourceId'] not in queued|mapped and int(a['size'])>0]
 if not eligible:raise TransportError('NO_ISOLATED_PENDING_PROCESSED_ASSET')
 return min(eligible,key=lambda a:(int(a['size']),a['sourceId']))

class Journal:
 def __init__(self,path=STATE):
  self._lock=threading.RLock();self.path=path;self.data:dict[str,Any]=b.read_json(path,{'schema':'mgs.owner.archive.journal.v1','intents':{}})
  if not isinstance(self.data,dict) or not isinstance(self.data.get('intents'),dict):raise TransportError('JOURNAL_SCHEMA')
 def save(self):
  with self._lock:b.atomic_json(self.path,self.data)
 def known_id(self,key):
  with self._lock:return self.data['intents'].get(key,{}).get('id')
 def allow_create(self,key):
  with self._lock:
   if key in self.data['intents']:raise TransportError('AMBIGUOUS_CREATE_NO_REPLAY:'+key)
 def intent(self,key,binding):
  with self._lock:
   old=self.data['intents'].get(key)
   if old and old['binding']!=binding:raise TransportError('INTENT_BINDING')
   if not old:self.data['intents'][key]={'binding':binding,'started_at':b.now_iso()};self.save()
 def landed(self,key,fid):
  with self._lock:
   old=self.data['intents'][key]
   if old.get('id') and old['id']!=fid:raise TransportError('LANDED_ID_CONFLICT')
   old.update(id=fid);self.save()

class OwnerDrive(b.Drive):
 def __init__(self):
  self.cfg=auth.init();v=auth.Vault(self.cfg);f=auth.OwnerAuthorization(self.cfg,v,auth.Google()).client();p=b.read_json(auth.PROOF)
  if not p or p.get('approval_message_id')!=auth.APPROVAL or p.get('refresh_grant_verified') is not True or not f.get('refresh_token'):raise TransportError('OWNER_GRANT_NOT_READY')
  self._auth_lock=threading.RLock();self.google=auth.Google();self.credentials=f;self.base='https://www.googleapis.com/drive/v3/';self.sources=set();self.parents={b.ARCHIVE_ROOT};self.refresh()
  root=self.meta(b.ARCHIVE_ROOT)
  if root.get('mimeType')!=b.FOLDER or root.get('driveId') or root.get('trashed') is not False or root.get('capabilities',{}).get('canAddChildren') is not True or not any(o.get('emailAddress')==b.ACCOUNT and o.get('permissionId')==b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT] for o in root.get('owners',[])) or any(p.get('type') in ['anyone','domain'] for p in root.get('permissions',[])):raise TransportError('ROOT_NATIVE_BINDING')
 def refresh(self):
  t=self.google.refresh(self.credentials,self.credentials['refresh_token'])
  if not t.get('access_token') or (t.get('scope') and set(t['scope'].split())!={auth.DRIVE_SCOPE}):raise TransportError('OWNER_SCOPE')
  self.token=t['access_token'];self.expiry=time.monotonic()+max(60,int(t.get('expires_in',3600))-120)
  user=self.google.identity(self.token)
  if user.get('emailAddress')!=b.ACCOUNT or user.get('permissionId')!=b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT]:raise TransportError('OWNER_BINDING')
 def api(self,method,path,params=None,payload=None)->dict[str,Any]:
  if method not in ['GET','POST']:raise TransportError('OWNER_MUTATION_METHOD_FORBIDDEN')
  if method=='POST':
   copy_match=re.fullmatch(r'files/([A-Za-z0-9_-]+)/copy',path)
   if copy_match:
    if copy_match[1] not in self.sources or not payload or len(payload.get('parents',[]))!=1 or payload['parents'][0] not in self.parents:raise TransportError('COPY_MUTATION_SCOPE')
   elif path=='files':
    if not payload or payload.get('mimeType')!=b.FOLDER or len(payload.get('parents',[]))!=1 or payload['parents'][0] not in self.parents:raise TransportError('FOLDER_MUTATION_SCOPE')
   else:raise TransportError('OWNER_POST_FORBIDDEN')
  if time.monotonic()>self.expiry:
   with self._auth_lock:
    if time.monotonic()>self.expiry:self.refresh()
  url=self.base+path+('?' + urllib.parse.urlencode(params) if params else '')
  body=b.canonical(payload) if payload is not None else None
  for attempt in range(3):
   try:
    req=urllib.request.Request(url,data=body,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json','User-Agent':'MGS-Private-Archive/1'},method=method)
    with urllib.request.urlopen(req,timeout=90) as r:
     result=json.load(r)
     if not isinstance(result,dict):raise TransportError('OWNER_RESPONSE_NOT_OBJECT')
     return result
   except urllib.error.HTTPError as e:
    code=e.code;e.read()
    if method=='GET' and code in [429,500,502,503,504] and attempt<2:time.sleep(min(30,int(e.headers.get('Retry-After','0') or 0)) or 2**attempt);continue
    raise TransportError('OWNER_DRIVE_HTTP_'+str(code)) from None
   except (urllib.error.URLError,TimeoutError):
    if method=='GET' and attempt<2:time.sleep(2**attempt);continue
    raise TransportError('OWNER_DRIVE_NETWORK_AMBIGUOUS' if method!='GET' else 'OWNER_DRIVE_NETWORK') from None
   except ValueError:raise TransportError('OWNER_RESPONSE_INVALID') from None
  raise TransportError('OWNER_READ_ATTEMPTS_EXHAUSTED')
 def meta(self,fid):
  return self.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':'id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,version,trashed,createdTime,owners(emailAddress,permissionId),lastModifyingUser(emailAddress,permissionId),properties,capabilities(canCopy,canAddChildren,canDownload),permissions(type,emailAddress,role)'})
 def write_json(self,parent,key,kind,value,journal):
  c=b.config_load()
  if parent not in [c['control_folder_id'],c['receipts_folder_id']]:raise TransportError('JSON_PARENT_SCOPE')
  old=self.one(parent,key);data=b.canonical(value);identity='json:'+parent+':'+key
  fid=journal.known_id(identity)
  if old:
   if fid and old['id']!=fid:raise TransportError('JSON_ID_CONFLICT')
   fid=old['id'];meta=self.meta(fid);b.require_publisher(meta,b.ACCOUNT)
   if meta.get('parents')!=[parent] or meta.get('properties',{}).get('mgsArchiveType')!=kind:raise TransportError('JSON_EXISTING_SCOPE')
   prior=json.loads(self.raw(fid))
   if prior==value:return fid
   if kind=='receipt' and prior.get('status')=='copied':raise TransportError('COMPLETED_RECEIPT_IMMUTABLE')
  if not fid:
   journal.allow_create(identity);journal.intent(identity,{'parent':parent,'key':key,'kind':kind})
  boundary='mgs-'+uuid.uuid4().hex;metadata={'name':key.replace(':','-')+'.json','mimeType':'application/json','properties':{'mgsArchiveKey':key,'mgsArchiveType':kind}}
  if not fid:metadata['parents']=[parent]
  blob=(('--'+boundary+'\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n').encode()+b.canonical(metadata)+('\r\n--'+boundary+'\r\nContent-Type: application/json\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode())
  url='https://www.googleapis.com/upload/drive/v3/files'+('/'+fid if fid else '')+'?uploadType=multipart&supportsAllDrives=true&fields=id'
  request=urllib.request.Request(url,data=blob,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/related; boundary='+boundary,'User-Agent':'MGS-Private-Archive/1'},method='PATCH' if fid else 'POST')
  try:
   with urllib.request.urlopen(request,timeout=90) as response:landed=json.load(response)['id']
  except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):
   found=self.one(parent,key)
   if not found:raise TransportError('JSON_PUBLICATION_AMBIGUOUS_NO_REPLAY') from None
   landed=found['id']
   if self.raw(landed)!=data:raise TransportError('JSON_PUBLICATION_UNCERTAIN') from None
  if not journal.known_id(identity):
   if identity not in journal.data['intents']:journal.intent(identity,{'parent':parent,'key':key,'kind':kind})
   journal.landed(identity,landed)
  if self.raw(landed)!=data:raise TransportError('JSON_READBACK')
  b.require_publisher(self.meta(landed),b.ACCOUNT);return landed

class Engine:
 def __init__(self,owner,c,manifest,stage,journal=None):
  self.owner=owner;self.c=c;self.manifest=manifest;self.stage=stage;self.journal=journal or Journal();self.folder_cache={};self.deadline:float|None=None;self.folder_lock=threading.RLock();self.stop=threading.Event();self.created_ids=[]
  if stage and stage.get('metadata_reconciliation_sha256'):
   fid=stage['metadata_reconciliation_file_id'];meta=owner.meta(fid);b.require_publisher(meta,b.CANONICAL_SA);raw=owner.raw(fid)
   if meta.get('parents')!=[c['control_folder_id']] or meta.get('driveId')!=b.SOURCE_DRIVE or meta.get('properties',{}).get('mgsArchiveType')!='backfill_metadata_reconciliation' or hashlib.sha256(raw).hexdigest()!=stage['metadata_reconciliation_sha256']:raise TransportError('NATIVE_METADATA_RECONCILIATION_PROVENANCE')
 def check_running(self):
  if self.stop.is_set():raise TransportError('BATCH_STOPPED_ON_FIRST_FAILURE')
  if self.deadline is not None and time.monotonic()>self.deadline:raise TransportError('COOPERATIVE_YIELD')
 def check_folder(self,fid,parent,name):
  m=self.owner.meta(fid)
  if m.get('trashed') is not False or m.get('driveId') or m.get('mimeType')!=b.FOLDER or m.get('name')!=name or m.get('parents')!=[parent] or not any(o.get('permissionId')==b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT] and o.get('emailAddress')==b.ACCOUNT for o in m.get('owners',[])) or any(p.get('type') in ['anyone','domain'] for p in m.get('permissions',[])):raise TransportError('DEST_FOLDER_SCOPE')
  self.owner.parents.add(fid);return fid
 def ensure_path(self,names):
  with self.folder_lock:
   self.check_running();return self._ensure_path(names)
 def _ensure_path(self,names):
  validate_path(names);parent=b.ARCHIVE_ROOT
  for name in names:
   cache=(parent,name)
   if cache in self.folder_cache:
    fid=self.folder_cache[cache];self.check_folder(fid,parent,name);parent=fid;continue
   key='folder:'+hashlib.sha256(b.canonical([parent,name])).hexdigest();fid=self.journal.known_id(key)
   if not fid:
    q="'"+parent+"' in parents and trashed=false and mimeType='"+b.FOLDER+"' and name='"+name.replace('\\','\\\\').replace("'","\\'")+"'"
    rows=self.owner.api('GET','files',{'q':q,'pageSize':2,'fields':'files(id),nextPageToken'})
    if rows.get('nextPageToken') or len(rows.get('files',[]))>1:raise TransportError('DUPLICATE_DEST_FOLDER')
    if rows.get('files'):fid=rows['files'][0]['id']
    else:
     self.check_running();self.journal.allow_create(key);self.journal.intent(key,{'parent':parent,'name':name})
     try:fid=self.owner.api('POST','files',{'fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent]})['id'];self.journal.landed(key,fid)
     except b.ArchiveError:
      rows=self.owner.api('GET','files',{'q':q,'pageSize':2,'fields':'files(id),nextPageToken'})
      if len(rows.get('files',[]))!=1 or rows.get('nextPageToken'):raise TransportError('FOLDER_AMBIGUOUS_NO_REPLAY') from None
      fid=rows['files'][0]['id'];self.journal.landed(key,fid)
   self.check_folder(fid,parent,name);self.folder_cache[cache]=fid;parent=fid
  return parent
 def copy_asset(self,a,j):
  self.check_running()
  m=self.owner.meta(a['sourceId']);b.validate_source_metadata(m,a,self.c)
  if self.owner.relative_parent(a['sourceParentId'],b.SOURCE_ROOT)!=a['relativeParent']:raise TransportError('SOURCE_PATH')
  indexed=b.read_json(h.location()/'backfill-index.json',{}).get('mappings',{}).get(a['sourceId'])
  live=b.read_json(b.DATA/'archive-index.json',{}).get('mappings',{}).get(a['sourceId'])
  if indexed and live and indexed.get('archive_id')!=live.get('archiveId'):raise TransportError('EXISTING_MAPPING_CONFLICT')
  if indexed or live:
   entry=indexed or {'archive_id':live['archiveId'],'sha256':live['sha256'],'md5':live['md5'],'size':live['size'],'verified':live['verified']}
   if entry.get('verified') is not True or any(str(entry.get(k))!=str(a[k]) for k in ['size','md5','sha256']):raise TransportError('EXISTING_MAPPING_CONTENT')
   target=self.owner.meta(entry['archive_id']);parents=target.get('parents',[])
   if len(parents)!=1 or self.owner.relative_parent(parents[0],b.ARCHIVE_ROOT)!=a['relativeParent']:raise TransportError('EXISTING_MAPPING_PATH')
   validate_copy(target,a,parents[0],self.c)
   return {'role':a['role'],'sourceId':a['sourceId'],'archiveId':target['id'],'archiveParentId':parents[0],'size':a['size'],'md5':a['md5'],'owner':b.ACCOUNT,'createdByVps':False,'adoptedMapping':True}
  if m.get('capabilities',{}).get('canCopy') is not True:raise TransportError('SOURCE_COPY_PERMISSION')
  parent=self.ensure_path(a['relativeParent']);marker=a['sourceId']+'_'+a['md5'];key='copy:'+hashlib.sha256(b.canonical([parent,marker])).hexdigest();fid=self.journal.known_id(key);created=False
  if not fid:
   q="'"+parent+"' in parents and trashed=false and properties has { key='mgsArchivePilot' and value='"+marker+"' }"
   rows=self.owner.api('GET','files',{'q':q,'pageSize':2,'fields':'files(id),nextPageToken'})
   if rows.get('nextPageToken') or len(rows.get('files',[]))>1:raise TransportError('DUPLICATE_COPIES')
   if rows.get('files'):fid=rows['files'][0]['id']
   else:
    handoff=b.read_json(HOME/'exclusive-handoff.json',{})
    legacy=next((x for x in handoff.get('legacy_pending',[]) if x['job_id']==j['jobId']),None)
    if legacy:
     previous=legacy.get('receipt_after_drain') or legacy.get('receipt_before') or {};reason=previous.get('reason','')
     if previous.get('status')!='blocked' or not (reason=='REQUEST_CHANGED' or reason.startswith('API call to drive.files.create failed with error:')):raise TransportError('LEGACY_COPY_INTENT_UNKNOWN_NO_REPLAY')
    self.check_running();self.journal.allow_create(key);self.journal.intent(key,{'source':a['sourceId'],'parent':parent,'sha256':a['sha256'],'job_id':j['jobId']});self.owner.sources.add(a['sourceId'])
    try:
     fid=self.owner.api('POST','files/'+a['sourceId']+'/copy',{'supportsAllDrives':'true','fields':'id'},{'name':a['name'],'parents':[parent],'properties':{'mgsArchivePilot':marker,'mgsArchiveJob':j['jobId'],'mgsArchiveExecutor':'private-vps-v1'}})['id'];self.journal.landed(key,fid);self.created_ids.append(fid);created=True
    except b.ArchiveError:
     rows=self.owner.api('GET','files',{'q':q,'pageSize':2,'fields':'files(id),nextPageToken'})
     if len(rows.get('files',[]))!=1 or rows.get('nextPageToken'):raise TransportError('COPY_AMBIGUOUS_NO_REPLAY') from None
     fid=rows['files'][0]['id'];self.journal.landed(key,fid)
  validate_copy(self.owner.meta(fid),a,parent,self.c);b.validate_source_metadata(self.owner.meta(a['sourceId']),a,self.c)
  return {'role':a['role'],'sourceId':a['sourceId'],'archiveId':fid,'archiveParentId':parent,'size':a['size'],'md5':a['md5'],'owner':b.ACCOUNT,'createdByVps':created}
 def copy_assets_bounded(self,j):
  # One canonical process/queue lease; at most four RPCs within its frozen job.
  # No second executor or writer can claim work while this lease is held.
  from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
  self.stop.clear();assets=j['assets'];results=[None]*len(assets);next_index=0
  if not 1<=len(assets)<=8:raise TransportError('BOUNDED_BATCH_ASSET_SET')
  with ThreadPoolExecutor(max_workers=min(4,len(assets)),thread_name_prefix='mgs-one-owner-lease') as pool:
   pending={}
   while next_index<min(4,len(assets)):
    pending[pool.submit(self.copy_asset,assets[next_index],j)]=next_index;next_index+=1
   while pending:
    done,_=wait(pending,return_when=FIRST_COMPLETED)
    try:
     for future in done:results[pending.pop(future)]=future.result()
    except Exception:
     self.stop.set()
     for future in pending:future.cancel()
     raise
    while len(pending)<4 and next_index<len(assets):
     pending[pool.submit(self.copy_asset,assets[next_index],j)]=next_index;next_index+=1
  return results
 def process(self,j,request_id):
  validate_job(j,self.c,self.manifest,self.stage)
  req=self.owner.meta(request_id);b.require_publisher(req,b.CANONICAL_SA);raw=self.owner.raw(request_id);props=req.get('properties',{})
  if req.get('parents')!=[self.c['requests_folder_id']] or props.get('mgsArchiveType')!=(REQUEST_TYPE if j['kind']=='backfill' else 'vps_request') or props.get('mgsArchiveKey')!='request:'+j['jobId'] or props.get('sha256')!=hashlib.sha256(raw).hexdigest() or raw!=b.canonical(j):raise TransportError('REQUEST_NATIVE_BINDING')
  old=self.owner.one(self.c['receipts_folder_id'],'receipt:'+j['jobId'])
  if old:
   b.require_publisher(self.owner.meta(old['id']),b.ACCOUNT);receipt=json.loads(self.owner.raw(old['id']))
   if receipt.get('status')=='copied':b.validate_receipt(j,receipt);return receipt
  assets=self.copy_assets_bounded(j)
  if self.owner.raw(request_id)!=raw:raise TransportError('REQUEST_CHANGED')
  receipt={'schema':'mgs.archive.receipt.v1','jobId':j['jobId'],'kind':j['kind'],'status':'copied','assets':assets,'deleteSource':False,'completedAt':b.now_iso(),'executor':'private-vps-v1'}
  self.owner.write_json(self.c['receipts_folder_id'],'receipt:'+j['jobId'],'receipt',receipt,self.journal);return receipt

def enqueue(sa,c,job):
 p=h.location()/'jobs'/('job-'+job['jobId']+'.json');old=b.read_json(p)
 if old:
  if any(old.get(k)!=job.get(k) for k in ['assets','manifestSha256','migrationId','kind']):raise TransportError('IMMUTABLE_JOB')
  job=old
 else:b.atomic_json(p,job)
 fid=sa.upload_once(c['requests_folder_id'],'vps-backfill-'+job['jobId']+'.json',b.canonical(job),'application/json','request:'+job['jobId'],REQUEST_TYPE);meta=sa.meta(fid);b.require_publisher(meta,b.CANONICAL_SA)
 if meta.get('properties',{}).get('mgsArchiveType')!=REQUEST_TYPE or sa.raw(fid)!=b.canonical(job):raise TransportError('REQUEST_READBACK')
 if meta['properties'].get('mgsArchiveState')!='verified':sa.api('PATCH','files/'+fid,{'supportsAllDrives':'true','fields':'id,properties'},{'properties':{**meta['properties'],'mgsArchiveState':'queued'}})
 return {'job_id':job['jobId'],'request_id':fid,'job':job}

def prepare_canary():
 manifest,stage=h.manifest_load();c=b.config_load()
 with b.queue_lock():
  existing=b.read_json(CONTRACT)
  if existing:
   if existing.get('approval_message_id')!=auth.APPROVAL:raise TransportError('CONTRACT_AUTHORITY')
   return existing
  jobs=[b.read_json(p) for p in list((h.location()/'jobs').glob('job-*.json'))+list((b.DATA/'jobs').glob('job-*.json'))];queued={a['sourceId'] for j in jobs for a in j['assets']};mapped=set(b.read_json(h.location()/'backfill-index.json',{}).get('mappings',{}))
  catalogue=[json.loads(line) for line in (b.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line];processed={r.get('asset_drive_id') for r in catalogue if r.get('metadata_clean') is True and r.get('status') not in ['TRASHED','DELETED','DELETED_BY_MANAGER_REQUEST','TRASHED_BY_MANAGER_REQUEST']}
  asset=select_canary(manifest['assets'],queued,mapped,processed);sa=b.Drive(True);h.source_access(sa,asset,c)
  prepared=enqueue(sa,c,h.make_job([asset],c,stage));contract={'schema':'mgs.private.archive.executor.v1','approval_message_id':auth.APPROVAL,'deadline_request_message_id':'1562940597411512364','phase':'canary_prepared','production_enabled':False,'canary_job_id':prepared['job_id'],'canary_request_id':prepared['request_id'],'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'request_type':REQUEST_TYPE,'prepared_at':b.now_iso()};b.atomic_json(CONTRACT,contract);return contract

def run_canary():
 with b.queue_lock():
  contract=b.read_json(CONTRACT)
  if not contract or contract.get('approval_message_id')!=auth.APPROVAL or contract.get('production_enabled') is not False:raise TransportError('CANARY_CONTRACT')
  c=b.config_load();manifest,stage=h.manifest_load();job=b.read_json(h.location()/'jobs'/('job-'+contract['canary_job_id']+'.json'));owner=OwnerDrive();engine=Engine(owner,c,manifest,stage);receipt=engine.process(job,contract['canary_request_id']);sa=b.Drive(True);verified=h.verify_job(sa,c,job,apply=True,request_type=REQUEST_TYPE)
  if verified['status']!='verified':raise TransportError('CANARY_SA_VERIFICATION')
  proof={'schema':'mgs.private.archive.transport.canary.v1','executed_at':b.now_iso(),'job_id':job['jobId'],'request_id':contract['canary_request_id'],'receipt':receipt,'sa_verification':verified,'engine_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'delete_source':False,'production_enabled':False,'legacy_writer_cannot_consume_request_type':True};b.atomic_json(HOME/'transport-canary-proof.json',proof);contract.update(phase='canary_verified',canary_verified_at=proof['executed_at'],engine_sha256=proof['engine_sha256']);b.atomic_json(CONTRACT,contract);return proof

def code_hash():return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
def object_file(path):
 value=b.read_json(path)
 if not isinstance(value,dict):raise TransportError('MISSING_OR_INVALID_EXECUTOR_STATE:'+Path(path).name)
 return value

def heartbeat(owner,c,journal,*,run_id,origin,completed,blocked,yielded=False):
 proof=b.read_json(HOME/'transport-canary-proof.json',{})
 if proof.get('sa_verification',{}).get('status')!='verified':raise TransportError('CANARY_SA_PROOF_MISSING')
 value={'schema':'mgs.archive.private.owner.heartbeat.v1','executor':'private-vps-v1','workerSha256':code_hash(),'executorRunId':run_id,'origin':origin,'executedAt':b.now_iso(),'status':'blocked' if blocked else 'ok','blocked':blocked,'completedJobs':completed,'yielded':yielded,'canaryAcknowledged':True,'deleteSource':False,'scope':'creative_media_only','legacy_backup_lanes_preserved':True}
 fid=owner.write_json(c['control_folder_id'],HEARTBEAT_KEY,'vps_heartbeat',value,journal)
 b.atomic_json(HOME/'last-native-heartbeat.json',{'file_id':fid,'body':value})
 return value

def activate():
 with b.queue_lock():
  c=b.config_load();contract=object_file(CONTRACT);handoff=object_file(HOME/'exclusive-handoff.json');proof=object_file(HOME/'transport-canary-proof.json')
  if c.get('owner_executor_mode')!='vps_handoff' or not drain_elapsed(handoff) or contract.get('approval_message_id')!=auth.APPROVAL or proof.get('engine_sha256')!=code_hash() or proof.get('sa_verification',{}).get('status')!='verified':raise TransportError('EXCLUSIVE_HANDOFF_GATES')
  sa=b.Drive(True);manifest,stage=h.manifest_load()
  for x in handoff['legacy_pending']:
   meta=sa.meta(x['id']);b.require_publisher(meta,b.CANONICAL_SA)
   expected_type=REQUEST_TYPE if x['properties_before']['mgsArchiveType']=='backfill_request' else 'vps_request'
   if (meta['properties']['mgsArchiveState'],meta['properties']['mgsArchiveType']) not in [('vps_reserved',x['properties_before']['mgsArchiveType']),('queued',expected_type)] or hashlib.sha256(sa.raw(x['id'])).hexdigest()!=x['job_sha256']:raise TransportError('RESERVATION_CHANGED')
   found=sa.one(c['receipts_folder_id'],'receipt:'+x['job_id'])
   if found:b.require_publisher(sa.meta(found['id']),b.ACCOUNT);x['receipt_after_drain']=json.loads(sa.raw(found['id']))
   x['properties_after_drain']=meta['properties']
  for row in sa.listing(c['requests_folder_id']):
   p=row.get('properties',{})
   if p.get('mgsArchiveType') in ['request','backfill_request'] and p.get('mgsArchiveState')=='queued':raise TransportError('LEGACY_PRODUCER_NOT_QUIESCENT')
  for x in handoff['legacy_pending']:
   old=x['properties_after_drain'];new_type=REQUEST_TYPE if x['properties_before']['mgsArchiveType']=='backfill_request' else 'vps_request'
   sa.api('PATCH','files/'+x['id'],{'supportsAllDrives':'true','fields':'id,properties'},{'properties':{**old,'mgsArchiveType':new_type,'mgsArchiveState':'queued'}})
   after=sa.meta(x['id']);b.require_publisher(after,b.CANONICAL_SA)
   if after['properties'].get('mgsArchiveType')!=new_type or after['properties'].get('mgsArchiveState')!='queued' or hashlib.sha256(sa.raw(x['id'])).hexdigest()!=x['job_sha256']:raise TransportError('HANDOFF_NATIVE_READBACK')
  handoff.update(phase='exclusive',exclusive_at=b.now_iso(),engine_sha256=code_hash());b.atomic_json(HOME/'exclusive-handoff.json',handoff)
  owner=OwnerDrive();heartbeat(owner,c,Journal(),run_id=uuid.uuid4().hex,origin='exclusive_activation',completed=[],blocked=[])
  c.update(owner_executor_mode='vps',owner_executor_sha256=code_hash(),owner_executor_contract=str(CONTRACT),owner_executor_scheduler_job_id='83b148017b4d');b.validate_config(c);b.atomic_json(b.CONFIG,c)
  contract.update(phase='active',production_enabled=True,engine_sha256=code_hash(),activated_at=b.now_iso());b.atomic_json(CONTRACT,contract)
  if b.config_load()!=c:raise TransportError('ACTIVE_CONFIG_READBACK')
  event={'timestamp':b.now_iso(),'agent':'zeus','action':'archive_private_owner_exclusive_handoff','approval_message_id':auth.APPROVAL,'source_message_id':'1562940597411512364','legacy_transferred':len(handoff['legacy_pending']),'legacy_drain_seconds':DRAIN_SECONDS,'engine_sha256':code_hash(),'source_deleted':False,'unrelated_lanes_preserved':True}
  with (b.BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
  return event

def run_tick(max_jobs=4,max_seconds=210,origin='foreground',produce=True):
 if not 1<=max_jobs<=4 or not 30<=max_seconds<=300:raise TransportError('TICK_BOUNDS')
 start=time.monotonic();summary={'schema':'mgs.archive.private.owner.tick.v1','run_id':uuid.uuid4().hex,'started_at':b.now_iso(),'status':'ok','copied_jobs':[],'verified_jobs':[],'blocked':[],'source_deleted':False,'origin':origin}
 with b.queue_lock():
  execution_start=time.monotonic();summary['queue_wait_seconds']=round(execution_start-start,3)
  c=b.config_load();contract=object_file(CONTRACT);handoff=object_file(HOME/'exclusive-handoff.json')
  if c.get('owner_executor_mode')!='vps' or c.get('owner_executor_sha256')!=code_hash() or not contract or contract.get('production_enabled') is not True or contract.get('engine_sha256')!=code_hash() or handoff.get('phase')!='exclusive' or contract.get('approval_message_id')!=auth.APPROVAL:raise TransportError('OWNER_EXECUTION_NOT_ACTIVE_OR_CODE_DRIFT')
  owner=OwnerDrive();sa=b.Drive(True);manifest,stage=h.manifest_load();engine=Engine(owner,c,manifest,stage);engine.deadline=execution_start+max_seconds;rows=owner.listing(c['requests_folder_id']);jobs=[]
  for row in rows:
   p=row.get('properties',{})
   if p.get('mgsArchiveState')!='queued':continue
   if p.get('mgsArchiveType') in ['request','backfill_request']:raise TransportError('LEGACY_QUEUED_REQUEST_AFTER_HANDOFF')
   if p.get('mgsArchiveType') not in [REQUEST_TYPE,'vps_request']:continue
   j=json.loads(owner.raw(row['id']));validate_job(j,c,manifest,stage);jobs.append((j,row['id']))
  jobs.sort(key=lambda x:(0 if x[0]['kind']=='lineage' else 1,x[0]['createdAt'],x[0]['jobId']));yielded=False
  for j,fid in jobs[:max_jobs]:
   if time.monotonic()>engine.deadline:yielded=True;break
   try:
    before_created=len(engine.created_ids);receipt=engine.process(j,fid);summary['copied_jobs'].append({'job_id':j['jobId'],'assets':len(receipt['assets']),'new_copies':len(engine.created_ids)-before_created})
    if j['kind']=='backfill':verdict=h.verify_job(sa,c,j,True,request_type=REQUEST_TYPE)
    else:
     import ares_archive_automation as automation
     automation.verification_snapshot(sa,c,j);verdict=b.reconcile(sa,c,j['jobId'],True)
    if verdict['status']!='verified':raise TransportError('INDEPENDENT_SA_VERIFY_NOT_COMPLETE')
    summary['verified_jobs'].append(j['jobId'])
   except b.ArchiveError as e:
    if str(e)=='COOPERATIVE_YIELD':yielded=True;break
    summary['blocked'].append({'job_id':j['jobId'],'reason':str(e)[:220]});break
  if summary['blocked']:summary['status']='blocked'
  heartbeat(owner,c,engine.journal,run_id=summary['run_id'],origin=origin,completed=summary['verified_jobs'],blocked=summary['blocked'],yielded=yielded)
  if produce and not summary['blocked'] and time.monotonic()<engine.deadline:
   summary['historical_producer']=h.cycle_locked(sa,c,True)
   if summary['historical_producer'].get('blocked'):
    summary['blocked'].extend(summary['historical_producer']['blocked']);summary['status']='blocked'
    heartbeat(owner,c,engine.journal,run_id=summary['run_id'],origin=origin,completed=summary['verified_jobs'],blocked=summary['blocked'],yielded=yielded)
  summary.update(completed_at=b.now_iso(),elapsed_seconds=round(time.monotonic()-start,3),execution_seconds=round(time.monotonic()-execution_start,3),yielded=yielded);b.atomic_json(HOME/'last-owner-tick.json',summary)
  history=HOME/'run-history';history.mkdir(exist_ok=True);b.atomic_json(history/(summary['run_id']+'.json'),summary)
 return summary

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare-canary','run-canary','activate','tick']);p.add_argument('--apply',action='store_true');p.add_argument('--max-jobs',type=int,default=4);p.add_argument('--max-seconds',type=int,default=210);p.add_argument('--origin',choices=['foreground','archive_monitor'],default='foreground');args=p.parse_args()
 if not args.apply:raise TransportError('APPLY_REQUIRED')
 if args.action=='prepare-canary':result=prepare_canary()
 elif args.action=='run-canary':result=run_canary()
 elif args.action=='activate':result=activate()
 else:result=run_tick(max_jobs=args.max_jobs,max_seconds=args.max_seconds,origin=args.origin)
 print(json.dumps(result,ensure_ascii=False));return 2 if result.get('status')=='blocked' else 0
if __name__=='__main__':raise SystemExit(main())
