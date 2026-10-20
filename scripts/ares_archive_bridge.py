#!/usr/bin/env python3
"""MGS copy-only archive queue. Canonical SA transport; no source deletion.

Default CLI operations are read-only. External writes require --apply.
The owner-executed Google worker is separate from agent authentication.
"""
from __future__ import annotations
import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid

BASE=Path('/root/mgs-agent')
DATA=BASE/'data/ares/creative-ops/30tb-archive'
CONFIG=DATA/'queue-config.json'
CANONICAL_SA='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
ACCOUNT='mgsdigitalcorp@gmail.com'
SOURCE_DRIVE='0AEwt4Ye690ocUk9PVA'
SOURCE_ROOT='1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa'
ARCHIVE_ROOT='1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J'
PILOT='1WDP1Mgwy4jTAowTDNy_k9RcuSieKOg9N'
PILOT_MD5='59065739912275ee5995bfee8d5ca9c7'
PILOT_SHA='11e123e5b495e5ed1a2ae5099b1cef94b6255a4c5f8302859b01a8b291793027'
FOLDER='application/vnd.google-apps.folder'

class ArchiveError(RuntimeError): pass

PUBLISHER_PERMISSION_IDS={CANONICAL_SA:'07414359829876449782',ACCOUNT:'03783617840924670288'}

def require_publisher(meta,email,reason='PUBLISHER'):
    # Native IDs remain authoritative when Google hides cross-principal email.
    user=meta.get('lastModifyingUser') if isinstance(meta,dict) else None
    expected=PUBLISHER_PERMISSION_IDS.get(email)
    if not expected or not isinstance(user,dict) or user.get('permissionId')!=expected or (user.get('emailAddress') is not None and user['emailAddress']!=email):
        raise ArchiveError(reason)
    return True

def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def now_iso(): return dt.datetime.now(dt.timezone.utc).isoformat()
def timestamp(value):
    try:
        parsed=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if parsed.tzinfo is None: raise ValueError('timezone required')
        return parsed.astimezone(dt.timezone.utc)
    except (ValueError,TypeError) as exc: raise ArchiveError('TIMESTAMP_REQUIRES_OFFSET') from exc

def validate_config(c):
    expected={'account':ACCOUNT,'source_drive_id':SOURCE_DRIVE,'source_root_id':SOURCE_ROOT,'archive_root_id':ARCHIVE_ROOT}
    if any(c.get(k)!=v for k,v in expected.items()) or c.get('delete_source') is not False: raise ArchiveError('CONFIG_SCOPE_OR_DELETION')
    timestamp(c['effective_after'])
    return c

def validate_lineage(row,c):
    validate_config(c)
    if row.get('metadata_clean') is not True: raise ArchiveError('LINEAGE_NOT_CLEAN')
    if timestamp(row.get('first_seen_at'))<timestamp(c['effective_after']): raise ArchiveError('HISTORICAL_LINEAGE_EXCLUDED')
    return True

def validate_asset(a):
    for key in ('sourceId','sourceParentId'):
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,}',str(a.get(key,''))): raise ArchiveError('ASSET_ID')
    if a.get('role') not in ('original','clean') or not re.match(r'^(image|video)/',a.get('mimeType','')): raise ArchiveError('ASSET_ROLE_OR_MEDIA')
    if not re.fullmatch(r'[1-9][0-9]*',str(a.get('size',''))) or not re.fullmatch(r'[a-f0-9]{32}',a.get('md5','')) or not re.fullmatch(r'[a-f0-9]{64}',a.get('sha256','')): raise ArchiveError('ASSET_CHECKSUM')
    if not isinstance(a.get('name'),str) or not a['name']: raise ArchiveError('ASSET_NAME')
    path=a.get('relativeParent')
    if not isinstance(path,list) or len(path)>12 or any(not isinstance(x,str) or not x or x in ('.','..') or any(t in x for t in ('/','\\','\x00')) for x in path): raise ArchiveError('ASSET_PATH')
    timestamp(a.get('sourceCreatedTime'))
    return a

def make_request(c,assets,*,kind,lineage_id,validation_only=False):
    validate_config(c)
    if type(validation_only) is not bool:raise ArchiveError('VALIDATION_FLAG')
    if not assets or len(assets)>2 or kind not in ('canary','lineage'): raise ArchiveError('JOB_SCOPE')
    for a in assets: validate_asset(a)
    if len({a['sourceId'] for a in assets})!=len(assets): raise ArchiveError('DUPLICATE_SOURCE')
    if kind=='canary':
        a=assets[0]
        if len(assets)!=1 or a['sourceId']!=PILOT or a['md5']!=PILOT_MD5 or a['sha256']!=PILOT_SHA or a['relativeParent']!=[]: raise ArchiveError('CANARY_SCOPE')
    else:
        if {a['role'] for a in assets}!={'original','clean'}: raise ArchiveError('LINEAGE_PAIR_REQUIRED')
        if any(timestamp(a['sourceCreatedTime'])<timestamp(c['effective_after']) for a in assets): raise ArchiveError('HISTORICAL_SOURCE_EXCLUDED')
    identity={'schema':'mgs.archive.request.v1','account':ACCOUNT,'sourceDriveId':SOURCE_DRIVE,'sourceRootId':SOURCE_ROOT,'archiveRootId':ARCHIVE_ROOT,'deleteSource':False,'kind':kind,'lineageId':str(lineage_id),'assets':assets}
    if validation_only:identity['validationOnly']=True
    identity['jobId']=hashlib.sha256(canonical(identity)).hexdigest()[:32]
    identity['createdAt']=now_iso()
    return identity

def validate_source_metadata(meta,a,c):
    expected={'id':a['sourceId'],'size':a['size'],'md5Checksum':a['md5'],'driveId':c['source_drive_id'],'name':a['name'],'mimeType':a['mimeType']}
    if a.get('sourceCreatedTime'):expected['createdTime']=a['sourceCreatedTime']
    if any(str(meta.get(k))!=str(v) for k,v in expected.items()) or meta.get('parents')!=[a['sourceParentId']] or meta.get('trashed') is not False: raise ArchiveError('SOURCE_CHANGED')
    native=meta.get('sha256Checksum');current=meta.get('version');frozen=a.get('version')
    if native is not None and native!=a['sha256']:raise ArchiveError('SOURCE_CONTENT_SHA_CHANGED')
    if not isinstance(current,str) or not isinstance(frozen,str) or not re.fullmatch(r'[0-9]+',current) or not re.fullmatch(r'[0-9]+',frozen) or int(current)<int(frozen):raise ArchiveError('SOURCE_VERSION_INVALID')
    # File.version covers every server-side change, not only payload revisions.
    # Never rewrite the request: forward metadata drift needs Google's exact
    # SHA-256, in addition to both full binary streams checked by reconcile().
    if current!=frozen and native!=a['sha256']:raise ArchiveError('SOURCE_VERSION_WITHOUT_CONTENT_PROOF')
    return True

def validate_receipt(job,r):
    if r.get('schema')!='mgs.archive.receipt.v1' or r.get('jobId')!=job['jobId'] or r.get('status')!='copied' or r.get('deleteSource') is not False: raise ArchiveError('RECEIPT_NOT_COPIED')
    expected={(a['role'],a['sourceId']) for a in job['assets']}
    got=[(a.get('role'),a.get('sourceId')) for a in r.get('assets',[])]
    if len(got)!=len(expected) or set(got)!=expected: raise ArchiveError('RECEIPT_ASSET_SET')
    return True

def record_verified_job(index,job,result):
    if result.get('status')!='verified' or result.get('jobId')!=job.get('jobId') or result.get('deleteSource') is not False:raise ArchiveError('UNVERIFIED_INDEX_RESULT')
    if 'validationOnly' in job and job['validationOnly'] is not True:raise ArchiveError('VALIDATION_FLAG')
    if job['kind']=='lineage' and job.get('validationOnly') is not True:
        for entry in result['assets']:
            prev=index['mappings'].get(entry['sourceId'])
            if prev and any(prev.get(k)!=entry[k] for k in ('archiveId','sha256','lineageId')):raise ArchiveError('MAPPING_CONFLICT')
        for entry in result['assets']:
            previous=index['mappings'].get(entry['sourceId'],{});stored=dict(entry)
            for key in ('stockShortcutId','stockAliasVerifiedAt','sourceRetirementReceipt'):
                if key in previous:stored[key]=previous[key]
            index['mappings'][entry['sourceId']]=stored
    index['verified_jobs'][job['jobId']]=result
    return index

def resolve_id(source_id,mappings,prefer=False):
    entry=mappings.get(source_id,{})
    if prefer and entry.get('verified') is True and entry.get('owner')==ACCOUNT and entry.get('archiveId'): return entry['archiveId']
    return source_id

def read_json(path,default=None):
    if not path.exists(): return default
    return json.loads(path.read_text())
def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    with os.fdopen(fd,'wb') as f: f.write(canonical(value)+b'\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
    if read_json(path)!=value: raise ArchiveError('LOCAL_READBACK')

@contextlib.contextmanager
def queue_lock():
    DATA.mkdir(parents=True,exist_ok=True)
    with (DATA/'.queue.lock').open('a+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);yield

class Drive:
    def __init__(self,write=False):
        sys.path.insert(0,str(BASE/'scripts'))
        from mgs_google_workspace_auth import load_env,service_account_access_token,api_json
        load_env();self.api_json=api_json
        self.token=service_account_access_token('https://www.googleapis.com/auth/drive' if write else 'https://www.googleapis.com/auth/drive.readonly')
        self.base='https://www.googleapis.com/drive/v3/'
    def api(self,method,path,params=None,payload=None):
        url=self.base+path+('?' + urllib.parse.urlencode(params) if params else '')
        status,data=self.api_json(method,url,self.token,payload)
        if status not in (200,201): raise ArchiveError('DRIVE_HTTP_'+str(status))
        return data
    def meta(self,fid):
        return self.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':'id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,version,trashed,createdTime,owners(emailAddress),lastModifyingUser(emailAddress,permissionId),properties,capabilities(canEdit,canAddChildren,canDownload),permissions(type,emailAddress,role)'})
    def listing(self,parent,*,key=None,kind=None):
        q="'"+parent+"' in parents and trashed=false"
        for name,value in [('mgsArchiveKey',key),('mgsArchiveType',kind)]:
            if value is not None:
                if "'" in value: raise ArchiveError('INVALID_PROPERTY_QUERY')
                q+=" and properties has { key='"+name+"' and value='"+value+"' }"
        out=[];page=None
        while True:
            p={'q':q,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':100,'fields':'nextPageToken,files(id,name,mimeType,parents,lastModifyingUser(emailAddress,permissionId),properties)'}
            if page:p['pageToken']=page
            d=self.api('GET','files',p);out+=d.get('files',[]);page=d.get('nextPageToken')
            if len(out)>10000: raise ArchiveError('QUEUE_LIST_LIMIT')
            if not page:return out
    def raw(self,fid):
        req=urllib.request.Request(self.base+'files/'+fid+'?alt=media&supportsAllDrives=true',headers={'Authorization':'Bearer '+self.token})
        with urllib.request.urlopen(req,timeout=60) as r:return r.read()
    def hashes(self,fid):
        req=urllib.request.Request(self.base+'files/'+fid+'?alt=media&supportsAllDrives=true',headers={'Authorization':'Bearer '+self.token})
        size=0;md5=hashlib.md5();sha=hashlib.sha256()
        with urllib.request.urlopen(req,timeout=60) as r:
            while True:
                data=r.read(1048576)
                if not data:break
                size+=len(data);md5.update(data);sha.update(data)
        return {'size':str(size),'md5':md5.hexdigest(),'sha256':sha.hexdigest()}
    def one(self,parent,key):
        matches=self.listing(parent,key=key)
        if len(matches)>1:raise ArchiveError('DUPLICATE_QUEUE_OBJECT')
        return matches[0] if matches else None
    def folder(self,parent,name,key):
        old=self.one(parent,key)
        if old:
            m=self.meta(old['id'])
            if m['mimeType']!=FOLDER or m['parents']!=[parent]:raise ArchiveError('FOLDER_SCOPE')
            return m['id']
        made=self.api('POST','files',{'supportsAllDrives':'true','fields':'id'}, {'name':name,'mimeType':FOLDER,'parents':[parent],'properties':{'mgsArchiveKey':key,'mgsArchiveType':'control'}})
        fid=made['id'];m=self.meta(fid)
        if m['parents']!=[parent] or m['mimeType']!=FOLDER:raise ArchiveError('FOLDER_READBACK')
        return fid
    def upload_once(self,parent,name,data,mime,key,kind):
        existing=self.one(parent,key)
        if existing:
            fid=existing['id']
            if self.raw(fid)!=data:raise ArchiveError('IMMUTABLE_QUEUE_CONTENT_CONFLICT')
            return fid
        boundary='mgs-'+uuid.uuid4().hex
        props={'mgsArchiveKey':key,'mgsArchiveType':kind,'sha256':hashlib.sha256(data).hexdigest()}
        if kind=='request':props['mgsArchiveState']='queued'
        meta={'name':name,'parents':[parent],'mimeType':mime,'properties':props}
        body=(('--'+boundary+'\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n').encode()+canonical(meta)+('\r\n--'+boundary+'\r\nContent-Type: '+mime+'\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode())
        url='https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id'
        req=urllib.request.Request(url,data=body,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/related; boundary='+boundary},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=90) as r:fid=json.loads(r.read())['id']
        except Exception as exc:
            landed=self.one(parent,key)
            if not landed:raise ArchiveError('UPLOAD_AMBIGUOUS_NO_REPLAY') from exc
            fid=landed['id']
        m=self.meta(fid)
        if m['parents']!=[parent] or self.raw(fid)!=data:raise ArchiveError('UPLOAD_READBACK')
        return fid
    def relative_parent(self,parent,root):
        out=[];seen=set();cur=parent
        for _ in range(30):
            if cur==root:return list(reversed(out))
            if cur in seen:raise ArchiveError('ANCESTRY_CYCLE')
            seen.add(cur);m=self.meta(cur)
            if m.get('trashed') or len(m.get('parents',[]))!=1:raise ArchiveError('ANCESTRY')
            out.append(m['name']);cur=m['parents'][0]
        raise ArchiveError('ANCESTRY_LIMIT')

def asset_snapshot(d,c,fid,role,canary=False):
    m=d.meta(fid)
    if m.get('trashed') or m.get('driveId')!=SOURCE_DRIVE or len(m.get('parents',[]))!=1:raise ArchiveError('SOURCE_SCOPE')
    relative=d.relative_parent(m['parents'][0],SOURCE_ROOT)
    h=d.hashes(fid)
    if h['size']!=m.get('size') or h['md5']!=m.get('md5Checksum'):raise ArchiveError('SOURCE_BINARY_READBACK')
    after=d.meta(fid)
    for k in ('id','parents','size','md5Checksum','version','trashed'):
        if after.get(k)!=m.get(k):raise ArchiveError('SOURCE_CHANGED_DURING_READ')
    return {'role':role,'sourceId':fid,'sourceParentId':m['parents'][0],'name':m['name'],'mimeType':m['mimeType'],'size':h['size'],'md5':h['md5'],'sha256':h['sha256'],'version':m['version'],'relativeParent':[] if canary else relative,'sourceCreatedTime':m['createdTime']}

def config_load():
    c=read_json(CONFIG)
    if not c:raise ArchiveError('CONFIG_NOT_INITIALIZED')
    return validate_config(c)
def preflight(d,c):
    src=d.meta(SOURCE_ROOT);dst=d.meta(ARCHIVE_ROOT)
    if src.get('driveId')!=SOURCE_DRIVE or src.get('trashed'):raise ArchiveError('SOURCE_ROOT')
    if dst.get('driveId') or dst.get('trashed') or not any(x.get('emailAddress')==ACCOUNT for x in dst.get('owners',[])):raise ArchiveError('ARCHIVE_OWNER')
    if not dst.get('capabilities',{}).get('canEdit'):raise ArchiveError('ARCHIVE_ACCESS')
    if any(x.get('type') in ('anyone','domain') for x in dst.get('permissions',[])):raise ArchiveError('ARCHIVE_PUBLIC')
    return {'status':'preflight_ok','archiveOwner':ACCOUNT,'deleteSource':False,'queueEnabled':c['queue_enabled']}

def initialize(d,c):
    preflight(d,c)
    control=d.folder(SOURCE_ROOT,'00_ARQUIVO_CONTROLE','mgs-archive-control-v1')
    c.update({'control_folder_id':control,'requests_folder_id':d.folder(control,'REQUESTS','mgs-archive-requests-v1'),'receipts_folder_id':d.folder(control,'RECEIPTS','mgs-archive-receipts-v1')})
    atomic_json(CONFIG,c);return {'status':'queue_folders_initialized','controlFolderId':control,'requestsFolderId':c['requests_folder_id'],'receiptsFolderId':c['receipts_folder_id']}

def publish_worker(d,c):
    source=(BASE/'integrations/creative-archive-30tb/Worker.js').read_bytes();sha=hashlib.sha256(source).hexdigest()
    fid=d.upload_once(c['control_folder_id'],'MGS-Archive-Worker-'+sha[:12]+'.js',source,'application/javascript','worker:'+sha,'worker')
    require_publisher(d.meta(fid),CANONICAL_SA,'WORKER_AUTHOR')
    c.update({'worker_file_id':fid,'worker_sha256':sha});atomic_json(CONFIG,c)
    return {'status':'worker_published_and_hash_verified','workerFileId':fid,'sha256':sha}

def enqueue(d,c,job):
    path=DATA/'jobs'/('job-'+job['jobId']+'.json');saved=read_json(path)
    if saved:
        for key in ('assets','kind','lineageId','archiveRootId'):
            if saved.get(key)!=job.get(key):raise ArchiveError('LOCAL_JOB_CONFLICT')
        job=saved
    else:atomic_json(path,job)
    payload=canonical(job)
    fid=d.upload_once(c['requests_folder_id'],'job-'+job['jobId']+'.json',payload,'application/json','request:'+job['jobId'],'request')
    request_meta=d.meta(fid)
    require_publisher(request_meta,CANONICAL_SA,'REQUEST_AUTHOR')
    state=request_meta.get('properties',{}).get('mgsArchiveState')
    return {'status':'already_verified' if state=='verified' else 'queued','jobId':job['jobId'],'requestFileId':fid,'kind':job['kind'],'deleteSource':False}

def job_for_lineage(d,c,asset_id):
    rows=[json.loads(line) for line in (BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()]
    matches=[x for x in rows if x.get('asset_id')==asset_id]
    if len(matches)!=1:raise ArchiveError('LINEAGE_ID_NOT_UNIQUE')
    row=matches[0];validate_lineage(row,c)
    assets=[asset_snapshot(d,c,row['source_drive_id'],'original'),asset_snapshot(d,c,row['asset_drive_id'],'clean')]
    if assets[0]['sha256']!=row.get('original_checksum') or assets[1]['sha256']!=row.get('clean_checksum'):raise ArchiveError('INVENTORY_CHECKSUM_MISMATCH')
    if not assets[0]['relativeParent'] or assets[0]['relativeParent'][-1]!='99_LEGACY':raise ArchiveError('RAW_NOT_IN_LEGACY')
    clean_parent=assets[1]['relativeParent']
    if (not clean_parent or clean_parent[-1]!='01_READY') and assets[1]['sourceParentId']!=row.get('manager_media_folder_id'):raise ArchiveError('CLEAN_FINAL_PARENT')
    return make_request(c,assets,kind='lineage',lineage_id=asset_id)

def reconcile(d,c,job_id,apply=False):
    job=read_json(DATA/'jobs'/('job-'+job_id+'.json'))
    if not job:raise ArchiveError('LOCAL_JOB_NOT_FOUND')
    rf=d.one(c['receipts_folder_id'],'receipt:'+job_id)
    if not rf:return {'status':'pending','jobId':job_id}
    rm=d.meta(rf['id'])
    require_publisher(rm,ACCOUNT,'RECEIPT_AUTHOR')
    r=json.loads(d.raw(rf['id']));validate_receipt(job,r);verified=[]
    for a in job['assets']:
        item=next(x for x in r['assets'] if x['sourceId']==a['sourceId'] and x['role']==a['role'])
        m=d.meta(item['archiveId'])
        if m.get('trashed') or m.get('driveId') or not any(x.get('emailAddress')==ACCOUNT for x in m.get('owners',[])):raise ArchiveError('COPIED_OWNER_OR_STATE')
        if m.get('size')!=a['size'] or m.get('md5Checksum')!=a['md5'] or m.get('name')!=a['name']:raise ArchiveError('COPIED_METADATA')
        if len(m.get('parents',[]))!=1 or d.relative_parent(m['parents'][0],ARCHIVE_ROOT)!=a['relativeParent']:raise ArchiveError('COPIED_PATH')
        if any(p.get('type') in ('anyone','domain') for p in m.get('permissions',[])):raise ArchiveError('COPIED_PUBLIC')
        validate_source_metadata(d.meta(a['sourceId']),a,c)
        expected={k:a[k] for k in ('size','md5','sha256')}
        if d.hashes(m['id'])!=expected or d.hashes(a['sourceId'])!=expected:raise ArchiveError('BINARY_INTEGRITY')
        validate_source_metadata(d.meta(a['sourceId']),a,c)
        verified.append({'sourceId':a['sourceId'],'archiveId':m['id'],'owner':ACCOUNT,'verified':True,'role':a['role'],'size':a['size'],'md5':a['md5'],'sha256':a['sha256'],'jobId':job_id,'lineageId':job['lineageId'],'relativeParent':a['relativeParent']})
    result={'status':'verified','kind':job['kind'],'jobId':job_id,'assets':verified,'verifiedAt':now_iso(),'deleteSource':False,'inventoryIdentifiersChanged':False}
    if apply:
        index=read_json(DATA/'archive-index.json',{'mappings':{},'verified_jobs':{}})
        if job.get('validationOnly') is True:result['validationOnly']=True
        record_verified_job(index,job,result)
        atomic_json(DATA/'archive-index.json',index);atomic_json(DATA/'jobs'/('verified-'+job_id+'.json'),result)
        ack={'schema':'mgs.archive.ack.v1','jobId':job_id,'kind':job['kind'],'status':'verified','deleteSource':False,'assets':verified}
        if job.get('validationOnly') is True:ack['validationOnly']=True
        # Stable ack bytes make retries replay-safe despite later local verification times.
        d.upload_once(c['requests_folder_id'],'ack-'+job_id+'.json',canonical(ack),'application/json','ack:'+job_id,'ack')
        request_file=d.one(c['requests_folder_id'],'request:'+job_id)
        if not request_file:raise ArchiveError('REQUEST_MISSING_AFTER_VERIFY')
        request_meta=d.meta(request_file['id'])
        require_publisher(request_meta,CANONICAL_SA,'REQUEST_PUBLISHER_CHANGED')
        properties=dict(request_meta.get('properties') or {})
        if properties.get('mgsArchiveState')!='verified':
            properties['mgsArchiveState']='verified'
            d.api('PATCH','files/'+request_file['id'],{'supportsAllDrives':'true','fields':'id,properties'},{'properties':properties})
            if d.meta(request_file['id']).get('properties',{}).get('mgsArchiveState')!='verified':raise ArchiveError('ACK_STATE_READBACK')
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=['preflight','init','publish-worker','enqueue-canary','enqueue-lineage','reconcile','status','resolve']);ap.add_argument('--apply',action='store_true');ap.add_argument('--asset-id');ap.add_argument('--job-id');ap.add_argument('--source-id');ap.add_argument('--use-verified',action='store_true');args=ap.parse_args()
    c=config_load()
    with queue_lock():
        if args.command=='resolve':
            if not args.source_id:raise ArchiveError('SOURCE_ID_REQUIRED')
            idx=read_json(DATA/'archive-index.json',{'mappings':{}});out={'sourceId':args.source_id,'resolvedId':resolve_id(args.source_id,idx['mappings'],args.use_verified or c.get('prefer_archive_reads') is True)}
        else:
            d=Drive(args.apply)
            if args.command=='preflight':out=preflight(d,c)
            elif args.command=='init':out=initialize(d,c) if args.apply else {'status':'dry_run','wouldCreate':'control/REQUESTS/RECEIPTS','deleteSource':False}
            elif args.command=='publish-worker':out=publish_worker(d,c) if args.apply else {'status':'dry_run','sha256':hashlib.sha256((BASE/'integrations/creative-archive-30tb/Worker.js').read_bytes()).hexdigest()}
            elif args.command in ('enqueue-canary','enqueue-lineage'):
                if args.command=='enqueue-canary':job=make_request(c,[asset_snapshot(d,c,PILOT,'clean',True)],kind='canary',lineage_id='PILOT-ONLY')
                else:
                    if not c.get('queue_enabled'):raise ArchiveError('PRODUCTION_QUEUE_NOT_ENABLED')
                    if not args.asset_id:raise ArchiveError('ASSET_ID_REQUIRED')
                    job=job_for_lineage(d,c,args.asset_id)
                out=enqueue(d,c,job) if args.apply else {'status':'dry_run','request':job,'deleteSource':False}
            elif args.command=='reconcile':
                ids=[args.job_id] if args.job_id else [p.stem[4:] for p in sorted((DATA/'jobs').glob('job-*.json'))]
                out={'results':[reconcile(d,c,j,args.apply) for j in ids]}
            else:
                heartbeat=None;beat=d.one(c['control_folder_id'],'heartbeat:worker-v1')
                if beat:
                    require_publisher(d.meta(beat['id']),ACCOUNT,'HEARTBEAT_AUTHOR')
                    heartbeat=json.loads(d.raw(beat['id']))
                    if heartbeat.get('schema')!='mgs.archive.heartbeat.v1' or heartbeat.get('workerSha256')!=c.get('worker_sha256'):raise ArchiveError('HEARTBEAT_CODE_VERSION')
                out={'queueEnabled':c['queue_enabled'],'deleteSource':False,'requests':len(d.listing(c['requests_folder_id'],kind='request')),'receipts':len(d.listing(c['receipts_folder_id'],kind='receipt')),'workerFileId':c.get('worker_file_id'),'heartbeat':heartbeat}
        print(json.dumps(out,ensure_ascii=False))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except ArchiveError as exc:print(json.dumps({'status':'blocked','reason':str(exc)}));raise SystemExit(2)
