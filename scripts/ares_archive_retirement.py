#!/usr/bin/env python3
"""Bounded, approved source retirement. Never delete archive bytes or test media.

Call under intake-state -> archive-queue -> inventory locks. The Google owner
worker remains copy-only. Missing source without a native verified receipt is
an error, never a success. No automatic replay of an ambiguous DELETE.
"""
from __future__ import annotations
import sys,json,hashlib,re,urllib.request,urllib.parse,urllib.error,time,fcntl,contextlib,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
CONFIRMATION='1562233890716786830'
WRITERS={'newnicolasholanda@gmail.com','criativosevo@gmail.com','iallynitasc@gmail.com','mattei2005@gmail.com','isliago89@gmail.com','support@matteiservicesinc.com','georgeicaro2307@gmail.com','geizianpereira@gmail.com','joewillams2009@gmail.com'}
class RetirementError(b.ArchiveError):pass
class NotReady(RetirementError):pass

def digest(value):return hashlib.sha256(b.canonical(value)).hexdigest()
def _object(path,default=None):
    value=b.read_json(path,default)
    if not isinstance(value,dict):raise RetirementError('RETIREMENT_JSON_OBJECT_REQUIRED:'+Path(path).name)
    return value
def authorization():
    p=b.DATA/('retirement-authorization-'+CONFIRMATION+'.json');a=_object(p,{})
    expected={'schema':'mgs.archive.retirement.authorization.v1','confirmation_message_id':CONFIRMATION,'confirmation_user_id':'344196393512075265','confirmation_thread_id':'1562078493498540042','source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'archive_owner':b.ACCOUNT,'retention_seconds':86400,'max_pairs_per_run':2,'include_historical':False,'exclude_validation_jobs':True,'permanent_source_deletion':True}
    if any(a.get(k)!=v for k,v in expected.items()):raise RetirementError('RETIREMENT_AUTHORITY_OR_SCOPE')
    return a

def validate_active_policy(c):
    a=authorization()
    if c.get('delete_source') is not True or c.get('include_historical') is not False or c.get('prefer_archive_reads') is not True or c.get('queue_enabled') is not True or c.get('source_cleanup_authorization_sha256')!=digest(a) or c.get('source_cleanup_confirmation_message_id')!=CONFIRMATION or c.get('effective_after')!=a['effective_after'] or not re.fullmatch(r'[A-Za-z0-9_-]{8,}',str(c.get('retirements_folder_id',''))):raise RetirementError('RETIREMENT_ACTIVATION_NOT_PINNED')
    return a

def candidate_ready(job,index,rows,state,c,now,ack_created):
    if job.get('kind')!='lineage' or job.get('validationOnly') is True or job.get('deleteSource') is not False:raise RetirementError('RETIREMENT_NOT_PRODUCTION_LINEAGE')
    assets=job.get('assets',[])
    if len(assets)!=2 or {a.get('role') for a in assets}!={'original','clean'} or len({a.get('sourceId') for a in assets})!=2:raise RetirementError('RETIREMENT_EXACT_PAIR_REQUIRED')
    verified=index.get('verified_jobs',{}).get(job['jobId'],{})
    if verified.get('status')!='verified' or verified.get('kind')!='lineage' or verified.get('validationOnly') is True:raise NotReady('RETIREMENT_AWAITING_VERIFIED_PAIR')
    matches=[r for r in rows if r.get('asset_id')==job['lineageId']]
    if len(matches)!=1:raise RetirementError('RETIREMENT_UNIQUE_INVENTORY_LINEAGE')
    row=matches[0]
    try:b.validate_lineage(row,c)
    except b.ArchiveError as exc:raise RetirementError(str(exc)) from exc
    for a in assets:
        try:b.validate_asset(a)
        except b.ArchiveError as exc:raise RetirementError(str(exc)) from exc
        relative=a['relativeParent'];status='99_LEGACY' if a['role']=='original' else '01_READY';sid=row.get('source_drive_id' if a['role']=='original' else 'asset_drive_id');sha=row.get('original_checksum' if a['role']=='original' else 'clean_checksum')
        if sid!=a['sourceId'] or sha!=a['sha256'] or relative!=[row.get('operation'),row.get('format'),status] or row.get('format') not in ['IMG','VID'] or not re.fullmatch(r'[A-Z0-9]+_[A-Z]{2}_[A-Z]{2}',str(row.get('operation',''))) or b.timestamp(a['sourceCreatedTime'])<b.timestamp(c['effective_after']):raise RetirementError('RETIREMENT_SOURCE_SCOPE_OR_INVENTORY')
        entry=index.get('mappings',{}).get(sid,{})
        if entry.get('verified') is not True or not entry.get('stockShortcutId'):raise NotReady('RETIREMENT_ALIAS_NOT_READY')
        if entry.get('archiveId')==sid or entry.get('jobId')!=job['jobId'] or entry.get('owner')!=b.ACCOUNT:raise RetirementError('RETIREMENT_MAPPING_IDENTITY')
    raw=next(a['sourceId'] for a in assets if a['role']=='original')
    releases=[e for e in state.get('claims',{}).values() if e.get('status')=='complete' and any(s.get('source_id')==raw for s in e.get('batch',{}).get('sources',[]))]
    if len(releases)!=1:raise NotReady('RETIREMENT_INTAKE_NOT_RELEASED')
    if any(e.get('status')!='complete' and any(s.get('source_id') in {a['sourceId'] for a in assets} for s in e.get('batch',{}).get('sources',[])) for e in state.get('claims',{}).values()):raise NotReady('RETIREMENT_ACTIVE_SOURCE_CLAIM')
    since=max(b.timestamp(ack_created),b.timestamp(releases[0]['completed_at']))
    if (b.timestamp(now)-since).total_seconds()<86400:raise NotReady('RETIREMENT_RETENTION_24H')
    return {'row':row,'released_at':releases[0]['completed_at'],'ack_created_at':ack_created}

def assert_delete_phase(intent):
    if intent.get('phase') in ['delete_started','rejected','ambiguous']:raise RetirementError('RETIREMENT_AMBIGUOUS_OR_REJECTED_NO_REPLAY')
    return True

def source_optional(d,sid):
    try:return d.meta(sid)
    except b.ArchiveError as exc:
        if str(exc)=='DRIVE_HTTP_404':return None
        raise

def control_scope(d,c):
    m=d.meta(c['retirements_folder_id'])
    if m.get('mimeType')!=b.FOLDER or m.get('driveId')!=b.SOURCE_DRIVE or m.get('parents')!=[c['control_folder_id']] or m.get('trashed'):raise RetirementError('RETIREMENT_CONTROL_FOLDER_SCOPE')

def verified_receipt(d,c,job,asset,entry):
    if job.get('kind')!='lineage' or job.get('validationOnly') is True:raise RetirementError('RETIREMENT_RECEIPT_NOT_PRODUCTION')
    fid=entry.get('sourceRetirementReceipt')
    if not fid:raise RetirementError('RETIREMENT_RECEIPT_MISSING')
    control_scope(d,c);m=d.meta(fid);b.require_publisher(m,b.CANONICAL_SA,'RETIREMENT_RECEIPT_AUTHOR');raw=d.raw(fid);r=json.loads(raw)
    if m.get('parents')!=[c['retirements_folder_id']] or m.get('driveId')!=b.SOURCE_DRIVE or m.get('properties',{}).get('mgsArchiveType')!='source_retirement_receipt' or hashlib.sha256(raw).hexdigest()!=m.get('properties',{}).get('sha256'):raise RetirementError('RETIREMENT_RECEIPT_SCOPE_OR_HASH')
    if r.get('schema')!='mgs.archive.retirement.receipt.v1' or r.get('status')!='deleted_verified' or r.get('authorization_sha256')!=digest(authorization()) or r.get('confirmation_message_id')!=CONFIRMATION or r.get('job_id')!=job['jobId'] or r.get('source_id')!=asset['sourceId'] or r.get('archive_id')!=entry.get('archiveId') or r.get('frozen_asset')!=asset or r.get('delete_http_status') not in (200,204) or r.get('source_readback_http')!=404 or r.get('request_sha256')!=digest(job):raise RetirementError('RETIREMENT_RECEIPT_BINDING')
    b.validate_source_metadata(r['source_before'],asset,c)
    if r.get('verified_hashes')!={k:asset[k] for k in ['size','md5','sha256']}:raise RetirementError('RETIREMENT_BINARY_PROOF')
    if source_optional(d,asset['sourceId']) is not None:raise RetirementError('RETIRED_SOURCE_REAPPEARED')
    return {'record_kind':'mgs.source.retirement.v1','source_id':asset['sourceId'],'archive_id':entry['archiveId'],'receipt_file_id':fid,'receipt_sha256':hashlib.sha256(raw).hexdigest(),'delete_http_status':r['delete_http_status'],'source_readback_http':404}

def source_state(d,c,job,asset):
    index=_object(b.DATA/'archive-index.json',{'mappings':{}}) or {'mappings':{}};entry=index.get('mappings',{}).get(asset['sourceId'],{})
    if entry.get('sourceRetirementReceipt'):return verified_receipt(d,c,job,asset,entry)
    source=source_optional(d,asset['sourceId'])
    if source is None:raise RetirementError('UNEXPLAINED_SOURCE_404_WITHOUT_RETIREMENT_RECEIPT')
    return source

def source_etag(d,asset):
    url='https://www.googleapis.com/drive/v2/files/'+asset['sourceId']+'?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':'id,etag,version,md5Checksum,fileSize'})
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+d.token}),timeout=40) as response:v=json.load(response)
    if v.get('id')!=asset['sourceId'] or v.get('md5Checksum')!=asset['md5'] or str(v.get('fileSize'))!=asset['size'] or not v.get('etag') or str(v['etag']).startswith('W/'):raise RetirementError('RETIREMENT_STRONG_ETAG_REQUIRED')
    return v

def delete_conditionally(d,sid,etag):
    # v2 exposes the strong resource ETag; canonical SA identity is unchanged.
    url='https://www.googleapis.com/drive/v2/files/'+sid+'?supportsAllDrives=true';request=urllib.request.Request(url,method='DELETE',headers={'Authorization':'Bearer '+d.token,'If-Match':etag})
    try:
        with urllib.request.urlopen(request,timeout=60) as response:return response.status
    except urllib.error.HTTPError as exc:return exc.code

def check_copy(d,asset,entry):
    import ares_archive_storage as storage
    record=storage.media_record(entry,storage.meta(d,entry['archiveId']),storage.meta(d,entry['stockShortcutId']))
    if record['name']!=asset['name'] or record['mimeType']!=asset['mimeType'] or d.relative_parent(record['provider_metadata']['parents'][0],b.ARCHIVE_ROOT)!=asset['relativeParent']:raise RetirementError('RETIREMENT_ARCHIVE_PATH')
    stock_path=d.relative_parent(record['stock_metadata']['parents'][0],b.SOURCE_ROOT)
    allowed_status=['99_LEGACY'] if asset['role']=='original' else ['01_READY','02_TESTING','03_TESTED','04_WINNERS','05_REJECTED']
    if len(stock_path)!=3 or stock_path[:2]!=asset['relativeParent'][:2] or stock_path[-1] not in allowed_status:raise RetirementError('RETIREMENT_STOCK_PATH')
    permissions=record['provider_metadata'].get('permissions',[]);writers={p.get('emailAddress') for p in permissions if p.get('role')=='writer'}
    if not WRITERS.issubset(writers) or b.CANONICAL_SA not in writers or not record['capabilities'].get('canDownload'):raise RetirementError('RETIREMENT_HUMAN_OR_SA_ACCESS')
    if d.hashes(entry['archiveId'])!={k:asset[k] for k in ['size','md5','sha256']}:raise RetirementError('RETIREMENT_ARCHIVE_BYTES')
    return record

def live_reference_guard(sids):
    """Block active hard-coded source endpoints; business logical keys are valid."""
    allowed={'asset_drive_id','source_drive_id','logical_source_id','source_id','drive_id','clean_source_id','duplicate_source_drive_ids','duplicate_source_links','source_links','duplicate_source_link'}
    def inspect(value,key='',tagged=False):
        if isinstance(value,dict):
            tagged=tagged or value.get('record_kind')=='mgs.logical.media.v1'
            return any(inspect(v,k,tagged) for k,v in value.items())
        if isinstance(value,list):return any(inspect(v,key,tagged) for v in value)
        if not isinstance(value,str):return False
        if any(s in value for s in sids) and ('drive.google.com/' in value or 'googleapis.com/drive/' in value):return True
        return value in sids and key not in allowed and not tagged
    for root in [b.BASE/'data/ares/meta-ads',b.BASE/'data/ares/creative-ops/inventory']:
        if not root.exists():continue
        for p in root.rglob('*.json'):
            if any(k in p.parts for k in ['audit','reports','logs','history','backups']):continue
            if p.stat().st_size>5000000:raise RetirementError('RETIREMENT_REFERENCE_SCAN_LIMIT')
            if inspect(b.read_json(p,{})):raise RetirementError('UNMEDIATED_SOURCE_REFERENCE:'+str(p.relative_to(b.BASE)))
    for root in [b.BASE/'scripts',Path('/root/.hermes/profiles/ares/scripts')]:
        for pattern in ['*.py','*.sh']:
            for p in root.rglob(pattern):
                if any(s in p.read_text(errors='replace') for s in sids):raise RetirementError('LITERAL_SOURCE_ID_IN_ACTIVE_SCRIPT:'+str(p))
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:raw=p.read_bytes()
        except (FileNotFoundError,ProcessLookupError,PermissionError):continue
        if any(s.encode() in raw for s in sids):raise NotReady('SOURCE_ID_IN_ACTIVE_PROCESS')
    return True

def current_row(lineage):
    p=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl';rows=[json.loads(line) for line in p.read_text().splitlines() if line.strip()];match=[r for r in rows if r.get('asset_id')==lineage]
    if len(match)!=1:raise RetirementError('RETIREMENT_ROW_NOT_UNIQUE')
    return match[0]

def publish_receipt(d,c,job,asset,intent,path):
    if intent.get('phase') not in ['delete_accepted','complete'] or intent.get('delete_http_status') not in (200,204):raise RetirementError('RETIREMENT_NO_ACCEPTED_DELETE')
    if source_optional(d,asset['sourceId']) is not None:raise RetirementError('RETIREMENT_SOURCE_NOT_ABSENT')
    index=_object(b.DATA/'archive-index.json');entry=index['mappings'][asset['sourceId']];check_copy(d,asset,entry)
    receipt={'schema':'mgs.archive.retirement.receipt.v1','status':'deleted_verified','job_id':job['jobId'],'source_id':asset['sourceId'],'archive_id':entry['archiveId'],'frozen_asset':asset,'source_before':intent['source_before'],'verified_hashes':intent['verified_hashes'],'request_sha256':digest(job),'authorization_sha256':digest(authorization()),'confirmation_message_id':CONFIRMATION,'delete_http_status':intent['delete_http_status'],'source_readback_http':404,'deleted_at':intent['delete_accepted_at'],'intent_file_id':intent['intent_file_id'],'source_physical_id_recoverable':False}
    fid=d.upload_once(c['retirements_folder_id'],'retired-'+asset['sourceId']+'.json',b.canonical(receipt),'application/json','retired:'+asset['sourceId']+':'+job['jobId'],'source_retirement_receipt')
    entry['sourceRetirementReceipt']=fid;index['mappings'][asset['sourceId']]=entry;b.atomic_json(b.DATA/'archive-index.json',index);verified_receipt(d,c,job,asset,entry)
    intent.update(phase='complete',receipt_file_id=fid,completed_at=b.now_iso());b.atomic_json(path,intent)
    with (b.BASE/'logs/events-audit.jsonl').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'ts':b.now_iso(),'agent':'zeus','event':'ares_source_retirement_verified','source_id':asset['sourceId'],'archive_id':entry['archiveId'],'receipt_file_id':fid,'authority_message_id':CONFIRMATION,'binary_bytes':int(asset['size']),'workspace_quota_delta_measured':False})+'\n');f.flush()
    return fid

def retire_asset(d,c,job,asset,row_fingerprint):
    validate_active_policy(c)
    import ares_archive_storage as storage
    folder=b.DATA/'retirements';folder.mkdir(exist_ok=True);path=folder/('source-'+asset['sourceId']+'.json');intent=_object(path,{})
    if intent:
        assert_delete_phase(intent)
        if intent.get('phase') in ['delete_accepted','complete']:return publish_receipt(d,c,job,asset,intent,path)
    index=_object(b.DATA/'archive-index.json');entry=index['mappings'][asset['sourceId']]
    if entry.get('sourceRetirementReceipt'):return verified_receipt(d,c,job,asset,entry)['receipt_file_id']
    source=storage.meta(d,asset['sourceId']);b.validate_source_metadata(source,asset,c)
    if d.relative_parent(source['parents'][0],b.SOURCE_ROOT)!=asset['relativeParent']:raise RetirementError('RETIREMENT_SOURCE_ANCESTRY_CHANGED')
    caps=d.api('GET','files/'+asset['sourceId'],{'supportsAllDrives':'true','fields':'id,capabilities(canDelete)'})
    if not caps.get('capabilities',{}).get('canDelete'):raise RetirementError('RETIREMENT_SOURCE_DELETE_CAPABILITY')
    expected={k:asset[k] for k in ['size','md5','sha256']};check_copy(d,asset,entry)
    if d.hashes(asset['sourceId'])!=expected:raise RetirementError('RETIREMENT_SOURCE_BYTES')
    etag=source_etag(d,asset);again=storage.meta(d,asset['sourceId']);b.validate_source_metadata(again,asset,c)
    if str(again['version'])!=str(etag['version']):raise RetirementError('RETIREMENT_SOURCE_CHANGED_BEFORE_INTENT')
    if digest(current_row(job['lineageId']))!=row_fingerprint:raise RetirementError('RETIREMENT_BUSINESS_ROW_CHANGED')
    if intent.get('phase')=='prepared':
        if intent.get('etag')!=etag['etag'] or intent.get('row_fingerprint')!=row_fingerprint or intent.get('verified_hashes')!=expected:raise RetirementError('RETIREMENT_PREPARED_INTENT_DRIFT')
    else:intent={'schema':'mgs.archive.retirement.intent.v1','phase':'prepared','job_id':job['jobId'],'source_id':asset['sourceId'],'archive_id':entry['archiveId'],'source_before':again,'verified_hashes':expected,'etag':etag['etag'],'authorization_sha256':digest(authorization()),'confirmation_message_id':CONFIRMATION,'row_fingerprint':row_fingerprint,'prepared_at':b.now_iso()}
    b.atomic_json(path,intent);payload=b.canonical(intent);iid=d.upload_once(c['retirements_folder_id'],'retirement-intent-'+asset['sourceId']+'.json',payload,'application/json','retirement-intent:'+asset['sourceId']+':'+job['jobId'],'source_retirement_intent');b.require_publisher(d.meta(iid),b.CANONICAL_SA)
    if d.raw(iid)!=payload:raise RetirementError('RETIREMENT_INTENT_READBACK')
    intent.update(phase='delete_started',intent_file_id=iid,delete_started_at=b.now_iso());b.atomic_json(path,intent)
    try:status=delete_conditionally(d,asset['sourceId'],etag['etag'])
    except Exception:
        intent.update(phase='ambiguous');b.atomic_json(path,intent);raise RetirementError('RETIREMENT_DELETE_RESPONSE_AMBIGUOUS_NO_REPLAY')
    intent['delete_http_status']=status
    if status not in (200,204):
        intent['phase']='rejected';b.atomic_json(path,intent);raise RetirementError('RETIREMENT_DELETE_HTTP_'+str(status))
    intent.update(phase='delete_accepted',delete_accepted_at=b.now_iso());b.atomic_json(path,intent)
    for attempt in range(3):
        if source_optional(d,asset['sourceId']) is None:break
        time.sleep(attempt+1)
    else:raise RetirementError('RETIREMENT_DELETE_ABSENCE_NOT_VERIFIED')
    return publish_receipt(d,c,job,asset,intent,path)

def recover_accepted(d,c):
    if not c.get('delete_source'):return []
    validate_active_policy(c);out=[]
    for path in sorted((b.DATA/'retirements').glob('source-*.json')):
        intent=_object(path);assert_delete_phase(intent)
        if intent.get('phase')=='delete_accepted':
            job=_object(b.DATA/'jobs'/('job-'+intent['job_id']+'.json'));asset=next(a for a in job['assets'] if a['sourceId']==intent['source_id']);out.append(publish_receipt(d,c,job,asset,intent,path))
    return out

def run_cycle(d,c,state,apply=False):
    result={'status':'disabled','enabled':False,'pairs_considered':0,'pairs_retired':0,'files_retired':0,'waiting':[],'blocked':[],'retention_seconds':86400,'max_pairs_per_run':2,'workspace_quota_delta_measured':False}
    if c.get('delete_source') is not True:return result
    validate_active_policy(c);control_scope(d,c);result.update(status='ok',enabled=True)
    index=_object(b.DATA/'archive-index.json',{'mappings':{},'verified_jobs':{}})
    for jid,verified in sorted(index['verified_jobs'].items(),key=lambda item:(item[1].get('verifiedAt',''),item[0])):
        if verified.get('kind')!='lineage' or verified.get('validationOnly') is True:continue
        job=_object(b.DATA/'jobs'/('job-'+jid+'.json'));entries=[index['mappings'].get(a['sourceId'],{}) for a in job['assets']]
        if entries and all(e.get('sourceRetirementReceipt') for e in entries):continue
        if result['pairs_considered']>=14 or result['pairs_retired']>=2:break
        result['pairs_considered']+=1
        try:
            ack=d.one(c['requests_folder_id'],'ack:'+jid)
            if not ack:raise NotReady('RETIREMENT_ACK_MISSING')
            am=d.meta(ack['id']);b.require_publisher(am,b.CANONICAL_SA)
            row=current_row(job['lineageId']);candidate_ready(job,index,[row],state,c,b.now_iso(),am['createdTime'])
            allowed={s['operation'] for s in _object(b.DATA/'upload-context-layout.json')['slots']}
            if row['operation'] not in allowed:raise RetirementError('RETIREMENT_OPERATION_NOT_REGISTERED')
            live_reference_guard({a['sourceId'] for a in job['assets']})
            if not apply:continue
            lock_path=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl.lock'
            with lock_path.open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX);before=digest(current_row(job['lineageId']));verified_now=b.reconcile(d,c,jid,apply=True)
                if verified_now.get('status')!='verified':raise RetirementError('RETIREMENT_PAIR_REVERIFY_FAILED')
                for asset in job['assets']:
                    old=_object(b.DATA/'archive-index.json')['mappings'][asset['sourceId']]
                    if old.get('sourceRetirementReceipt'):verified_receipt(d,c,job,asset,old);continue
                    retire_asset(d,c,job,asset,before);result['files_retired']+=1
                if digest(current_row(job['lineageId']))!=before:raise RetirementError('RETIREMENT_CHANGED_BUSINESS_ROW')
                result['pairs_retired']+=1
        except NotReady as exc:result['waiting'].append({'job_id':jid,'reason':str(exc)})
        except (b.ArchiveError,KeyError,ValueError,StopIteration) as exc:
            result['blocked'].append({'job_id':jid,'reason':str(exc)[:220]});break
    if result['blocked']:result['status']='blocked'
    if apply:b.atomic_json(b.DATA/'retirement-last-tick.json',{'executed_at':b.now_iso(),**result})
    return result
