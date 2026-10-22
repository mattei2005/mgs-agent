#!/usr/bin/env python3
"""Explicit logical-media catalogue over real Google metadata.

A catalogue record is NOT a Drive API response. provider_metadata and
stock_metadata retain the actual provider IDs; id is the unchanged business
lineage key. Shared-Drive shortcuts carry stock location; Gmail owns bytes.
No deletes, campaign writes, permission changes or primary-ID replacement.
"""
from __future__ import annotations
import sys,json,hashlib,urllib.parse,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
SHORTCUT='application/vnd.google-apps.shortcut'
class StorageError(b.ArchiveError):pass

def media_record(entry,physical,stock):
    if entry.get('verified') is not True or entry.get('owner')!=b.ACCOUNT:raise StorageError('ARCHIVE_MAPPING_NOT_VERIFIED')
    if physical.get('id')!=entry.get('archiveId') or physical.get('driveId') or physical.get('trashed') is not False or not any(o.get('emailAddress')==b.ACCOUNT for o in physical.get('owners',[])):raise StorageError('ARCHIVE_IDENTITY_OR_OWNER')
    if str(physical.get('size'))!=str(entry.get('size')) or physical.get('md5Checksum')!=entry.get('md5') or (physical.get('sha256Checksum') is not None and physical['sha256Checksum']!=entry['sha256']):raise StorageError('ARCHIVE_CONTENT_CHANGED')
    if len(physical.get('parents',[]))!=1 or (entry.get('archiveParentId') and physical['parents']!=[entry['archiveParentId']]):raise StorageError('ARCHIVE_PARENT_CHANGED')
    if any(p.get('type') in ['domain','anyone'] for p in physical.get('permissions',[])):raise StorageError('ARCHIVE_PUBLIC')
    if stock.get('id')!=entry.get('stockShortcutId') or stock.get('mimeType')!=SHORTCUT or stock.get('driveId')!=b.SOURCE_DRIVE or stock.get('trashed') is not False or len(stock.get('parents',[]))!=1 or stock.get('shortcutDetails',{}).get('targetId')!=physical['id'] or stock.get('properties',{}).get('mgsArchiveLogicalSource')!=entry['sourceId'] or stock.get('name')!=physical['name']:raise StorageError('STOCK_SHORTCUT_CHANGED')
    capabilities={**stock.get('capabilities',{}),'canDownload':physical.get('capabilities',{}).get('canDownload',False)}
    return {'record_kind':'mgs.logical.media.v1','storage_backend':'gmail_archive','id':entry['sourceId'],'logical_source_id':entry['sourceId'],'provider_id':physical['id'],'stock_file_id':stock['id'],'name':physical['name'],'mimeType':physical['mimeType'],'size':physical['size'],'md5Checksum':physical['md5Checksum'],'sha256Checksum':entry['sha256'],'driveId':stock['driveId'],'parents':list(stock['parents']),'trashed':False,'capabilities':capabilities,'provider_metadata':physical,'stock_metadata':stock,'archive_job_id':entry.get('jobId'),'lineage_id':entry['lineageId']}

def require_registered_mapping(entry,index):
    job=index.get('verified_jobs',{}).get(entry.get('jobId'))
    if not job or job.get('kind')!='lineage' or job.get('status')!='verified' or job.get('validationOnly') is True:raise StorageError('NO_PRODUCTION_JOB_PROOF')
    candidates=[a for a in job.get('assets',[]) if a.get('sourceId')==entry['sourceId']]
    if len(candidates)!=1 or any(candidates[0].get(k)!=entry.get(k) for k in ['archiveId','sha256','md5','size','lineageId','role']):raise StorageError('MAPPING_JOB_MISMATCH')
    return True

def dedupe_catalog(rows):
    out={};order=[]
    for row in rows:
        key=row.get('logical_source_id',row['id']);previous=out.get(key)
        if previous is None:out[key]=row;order.append(key)
        elif row.get('record_kind')=='mgs.logical.media.v1':
            if previous.get('record_kind')=='mgs.logical.media.v1' and previous['stock_file_id']!=row['stock_file_id']:raise StorageError('DUPLICATE_STOCK_ALIAS')
            out[key]=row
    return [out[k] for k in order]

def enabled():
    cfg=b.read_json(b.CONFIG,{})
    if cfg.get('prefer_archive_reads') is True:return True
    # Retirement is irreversible at the physical Google ID. Never route an
    # already-retired logical ID back to a missing staging binary on rollback.
    index=b.read_json(b.DATA/'archive-index.json',{'mappings':{}})
    return any(e.get('sourceRetirementReceipt') for e in index.get('mappings',{}).values())

def require_lineage_available(row):
    cfg=b.config_load()
    if not cfg.get('queue_enabled'):return True
    try:is_new=b.timestamp(row['first_seen_at'])>=b.timestamp(cfg['effective_after'])
    except (KeyError,b.ArchiveError):return True # Legacy unknown dates are never migrated implicitly.
    if not is_new:return True
    entry=mapping(row['asset_drive_id'])
    if not entry or not entry.get('stockShortcutId'):raise StorageError('ARCHIVE_PENDING_BEFORE_CAMPAIGN')
    intake=b.read_json(b.DATA/'intake-state.json',{'claims':{}})
    for claim in intake.get('claims',{}).values():
        if claim.get('status')!='complete' and any(s.get('source_id')==row.get('source_drive_id') for s in claim['batch']['sources']):raise StorageError('INTAKE_BATCH_NOT_RELEASED')
    return True

def drive(token=None,write=False):
    if token is None:return b.Drive(write)
    from mgs_google_workspace_auth import api_json
    d=b.Drive.__new__(b.Drive);d.token=token;d.api_json=api_json;d.base='https://www.googleapis.com/drive/v3/';return d

def meta(d,fid):
    return d.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':'id,name,mimeType,size,md5Checksum,sha256Checksum,version,createdTime,parents,driveId,trashed,owners(emailAddress),permissions(type,emailAddress,role),shortcutDetails(targetId),properties,lastModifyingUser(permissionId,emailAddress),capabilities(canEdit,canDownload,canMoveItemWithinDrive)'})

def mapping(source_id,index=None):
    index=index or b.read_json(b.DATA/'archive-index.json',{'mappings':{},'verified_jobs':{}});entry=index['mappings'].get(source_id)
    if entry:require_registered_mapping(entry,index)
    elif historical_enabled():entry=historical_mapping(source_id)
    return entry

def resolve_media(source_id,token=None):
    if not enabled():return None
    entry=mapping(source_id)
    if not entry:return None
    if entry.get('mapping_kind')=='historical_verified':
        d=drive(token);physical=meta(d,entry['archiveId']);stock=meta(d,entry.get('stockShortcutId') or source_id)
        require_historical_ack(d,entry)
        if d.relative_parent(physical['parents'][0],b.ARCHIVE_ROOT)!=entry['relativeParent']:raise StorageError('HISTORICAL_ARCHIVE_PATH_CHANGED')
        d.relative_parent(stock['parents'][0],b.SOURCE_ROOT)
        return historical_media_record(entry,physical,stock)
    if not entry.get('stockShortcutId'):raise StorageError('ARCHIVE_STOCK_ALIAS_NOT_READY')
    d=drive(token);physical=meta(d,entry['archiveId']);stock=meta(d,entry['stockShortcutId'])
    if d.relative_parent(physical['parents'][0],b.ARCHIVE_ROOT)!=entry['relativeParent']:raise StorageError('ARCHIVE_PATH_CHANGED')
    d.relative_parent(stock['parents'][0],b.SOURCE_ROOT)
    return media_record(entry,physical,stock)

def project_stock(rows,token=None):
    if not enabled():return rows
    index=b.read_json(b.DATA/'archive-index.json',{'mappings':{},'verified_jobs':{}});maps=index['mappings'];aliases={v.get('stockShortcutId'):k for k,v in maps.items() if v.get('stockShortcutId')};out=[]
    for row in rows:
        logical=aliases.get(row['id'])
        if logical:
            record=resolve_media(logical,token)
            if record is None:raise StorageError('CATALOGUE_READ_FLAG_CHANGED')
            extras={k:v for k,v in row.items() if k in ['kind','location','source_parent_id','status_parent_ids','ready_parent_id','testing_parent_id','tested_parent_id','winners_parent_id','rejected_parent_id']};out.append({**record,**extras})
        elif row['id'] in maps and maps[row['id']].get('stockShortcutId'):
            continue # Original retention bytes are not a second stock candidate.
        elif historical_enabled() and historical_mapping(row['id']):
            record=resolve_media(row['id'],token)
            if record is None:raise StorageError('HISTORICAL_READ_FLAG_CHANGED')
            extras={k:v for k,v in row.items() if k in ['kind','location','source_parent_id','status_parent_ids','ready_parent_id','testing_parent_id','tested_parent_id','winners_parent_id','rejected_parent_id']};out.append({**record,**extras})
        else:out.append(row)
    return dedupe_catalog(out)

def ensure_shortcuts(d,job_id):
    """After independent ACK only. Adds aliases, never removes retained sources."""
    index=b.read_json(b.DATA/'archive-index.json',{'mappings':{},'verified_jobs':{}});job=index['verified_jobs'].get(job_id)
    if not job or job.get('kind')!='lineage' or job.get('validationOnly') is True:return []
    frozen=b.read_json(b.DATA/'jobs'/('job-'+job_id+'.json'));assert isinstance(frozen,dict);made=[]
    ack=d.one(b.config_load()['requests_folder_id'],'ack:'+job_id)
    if not ack:raise StorageError('ACK_REQUIRED_BEFORE_ALIAS')
    b.require_publisher(d.meta(ack['id']),b.CANONICAL_SA)
    for asset in job['assets']:
        entry=index['mappings'][asset['sourceId']];require_registered_mapping(entry,index);expected=next(a for a in frozen['assets'] if a['sourceId']==entry['sourceId'])
        if entry.get('sourceRetirementReceipt'):
            import ares_archive_retirement as retirement
            retirement.verified_receipt(d,b.config_load(),frozen,expected,entry)
            if not entry.get('stockShortcutId'):raise StorageError('RETIRED_SOURCE_WITHOUT_STOCK_ALIAS')
            media_record(entry,meta(d,entry['archiveId']),meta(d,entry['stockShortcutId']));made.append(entry['stockShortcutId']);continue
        source=meta(d,entry['sourceId']);b.validate_source_metadata(source,expected,b.config_load())
        if d.relative_parent(source['parents'][0],b.SOURCE_ROOT)!=entry['relativeParent']:raise StorageError('SOURCE_MOVED_BEFORE_ALIAS')
        key='stock:'+entry['sourceId']+':'+entry['md5'];previous=d.one(source['parents'][0],key)
        if entry.get('stockShortcutId'):sid=entry['stockShortcutId']
        elif previous:sid=previous['id'];b.require_publisher(d.meta(sid),b.CANONICAL_SA)
        else:
            payload={'name':source['name'],'mimeType':SHORTCUT,'parents':list(source['parents']),'shortcutDetails':{'targetId':entry['archiveId']},'properties':{'mgsArchiveType':'stock_shortcut','mgsArchiveKey':key,'mgsArchiveLogicalSource':entry['sourceId'],'mgsArchiveJob':job_id}}
            intent=Path(b.DATA/'jobs'/('shortcut-intent-'+entry['sourceId']+'.json'))
            pending=b.read_json(intent,{})
            if pending.get('status')=='creating':raise StorageError('AMBIGUOUS_ALIAS_NO_REPLAY')
            b.atomic_json(intent,{'status':'creating','source_id':entry['sourceId'],'archive_id':entry['archiveId'],'parent':source['parents'][0],'at':b.now_iso()})
            try:sid=d.api('POST','files',{'supportsAllDrives':'true','fields':'id'},payload)['id']
            except Exception:
                landed=d.one(source['parents'][0],key)
                if not landed:raise
                sid=landed['id']
        stock=meta(d,sid);physical=meta(d,entry['archiveId']);candidate={**entry,'stockShortcutId':sid};media_record(candidate,physical,stock)
        if not entry.get('stockShortcutId') and stock['parents']!=source['parents']:raise StorageError('ALIAS_PARENT_READBACK')
        entry.update(stockShortcutId=sid,stockAliasVerifiedAt=b.now_iso());index['mappings'][entry['sourceId']]=entry
        b.atomic_json(b.DATA/'archive-index.json',index);b.atomic_json(b.DATA/'jobs'/('shortcut-intent-'+entry['sourceId']+'.json'),{'status':'verified','source_id':entry['sourceId'],'stock_shortcut_id':sid,'at':b.now_iso()});made.append(sid)
    return made

def _move_checked_entry(d,entry,target_parent_id,expected_parent_id,*,technical=False):
    physical=meta(d,entry['archiveId']);stock=meta(d,entry['stockShortcutId']);before=media_record(entry,physical,stock)
    if before['parents']!=[expected_parent_id]:raise StorageError('STOCK_PARENT_CAS')
    destination=meta(d,target_parent_id)
    if destination.get('driveId')!=b.SOURCE_DRIVE or destination.get('trashed') or destination.get('mimeType')!=b.FOLDER:raise StorageError('STOCK_DESTINATION_SCOPE')
    current_path=d.relative_parent(expected_parent_id,b.SOURCE_ROOT);new_path=d.relative_parent(target_parent_id,b.SOURCE_ROOT)
    if current_path[:-1]!=new_path[:-1] or new_path[-1] not in ['01_READY','02_TESTING','03_TESTED','04_WINNERS','05_REJECTED']:raise StorageError('STOCK_STATUS_SCOPE')
    if technical and current_path[:2]!=['00_ARQUIVO_CONTROLE','TEST_INPUTS_INTAKE_AUTOMATION']:raise StorageError('TECHNICAL_STOCK_SCOPE')
    params={'supportsAllDrives':'true','addParents':target_parent_id,'removeParents':expected_parent_id,'fields':'id,parents,driveId'};d.api('PATCH','files/'+entry['stockShortcutId'],params,{})
    after=media_record(entry,meta(d,entry['archiveId']),meta(d,entry['stockShortcutId']))
    if after['parents']!=[target_parent_id] or after['md5Checksum']!=before['md5Checksum'] or after['provider_metadata']['parents']!=physical['parents']:raise StorageError('STOCK_MOVE_READBACK')
    return after

def move_stock(record,target_parent_id,expected_parent_id,token=None):
    if record.get('record_kind')!='mgs.logical.media.v1':return None
    d=drive(token,True);entry=mapping(record['id']);assert entry
    if entry.get('mapping_kind')=='historical_verified' and record.get('stock_representation')=='retained_source':
        return move_historical_retained_stock(d,entry,target_parent_id,expected_parent_id)
    resolve_media(record['id'],token) # Recheck the immutable archive root/path proof.
    return _move_checked_entry(d,entry,target_parent_id,expected_parent_id)

def probe_stock_move(d,job_id,shortcut_id,source_id,target_parent_id,expected_parent_id):
    index=b.read_json(b.DATA/'archive-index.json');job=index['verified_jobs'].get(job_id)
    if not job or job.get('validationOnly') is not True or job.get('status')!='verified':raise StorageError('TECHNICAL_PROBE_SCOPE')
    entry=next(a for a in job['assets'] if a['sourceId']==source_id);candidate={**entry,'stockShortcutId':shortcut_id}
    stock=meta(d,shortcut_id);b.require_publisher(stock,b.CANONICAL_SA)
    if stock.get('properties',{}).get('mgsArchiveType')!='archive_test_shortcut':raise StorageError('TECHNICAL_ALIAS_MARKER')
    after=_move_checked_entry(d,candidate,target_parent_id,expected_parent_id,technical=True)
    return {'validation_only':True,'production_record_emitted':False,'logical_id_preserved':after['id']==source_id,'actual_stock_id':shortcut_id,'actual_provider_id':after['provider_id'],'stock_parent_verified':after['parents']==[target_parent_id],'archive_parent_unchanged':True}

def download_id(logical_id,token=None):
    record=resolve_media(logical_id,token)
    return record['provider_id'] if record else logical_id

def probe_verified_job(d,job_id,shortcut_id,source_id):
    """Engineering-only proof; never returns a production catalogue entry."""
    index=b.read_json(b.DATA/'archive-index.json');job=index['verified_jobs'].get(job_id)
    if not job or job.get('validationOnly') is not True or job.get('status')!='verified':raise StorageError('TECHNICAL_PROBE_SCOPE')
    entry=next(a for a in job['assets'] if a['sourceId']==source_id);candidate={**entry,'stockShortcutId':shortcut_id};record=media_record(candidate,meta(d,entry['archiveId']),meta(d,shortcut_id));h=d.hashes(record['provider_id'])
    if h!={k:entry[k] for k in ['size','md5','sha256']}:raise StorageError('TECHNICAL_PROBE_BINARY')
    return {'validation_only':True,'production_record_emitted':False,'logical_id_preserved':record['id']==source_id,'actual_provider_id':record['provider_id'],'actual_stock_id':record['stock_file_id'],'bytes_verified':True,'hashes':h}

def historical_enabled():
    return b.read_json(b.CONFIG,{}).get('historical_archive_reads_enabled') is True

def historical_mapping(source_id):
    import ares_archive_backfill as backfill
    index=b.read_json(backfill.location()/'backfill-index.json',{'mappings':{},'verified_jobs':{}});raw=index.get('mappings',{}).get(source_id)
    if not raw:return None
    proof=index.get('verified_jobs',{}).get(raw.get('job_id'),{})
    if raw.get('verified') is not True or raw.get('owner')!=b.ACCOUNT or proof.get('status')!='verified' or proof.get('schema')!='mgs.archive.backfill.verification.v1':raise StorageError('HISTORICAL_NO_VERIFIED_JOB')
    matches=[a for a in proof.get('assets',[]) if a.get('source_id')==source_id]
    if len(matches)!=1 or any(matches[0].get(k)!=raw.get(k) for k in ['source_id','archive_id','archive_parent_id','sha256','md5','size','relative_parent']):raise StorageError('HISTORICAL_MAPPING_JOB_MISMATCH')
    return {'mapping_kind':'historical_verified','sourceId':source_id,'archiveId':raw['archive_id'],'archiveParentId':raw['archive_parent_id'],'name':raw['name'],'mimeType':raw['mime_type'],'size':raw['size'],'md5':raw['md5'],'sha256':raw['sha256'],'owner':raw['owner'],'verified':True,'role':'historical','lineageId':None,'jobId':raw['job_id'],'relativeParent':raw['relative_parent'],'stockShortcutId':raw.get('stock_shortcut_id')}

def historical_media_record(entry,physical,stock):
    if entry.get('mapping_kind')!='historical_verified' or entry.get('verified') is not True or entry.get('owner')!=b.ACCOUNT:raise StorageError('HISTORICAL_MAPPING_NOT_VERIFIED')
    if physical.get('id')!=entry.get('archiveId') or physical.get('driveId') or physical.get('trashed') is not False or not any(o.get('emailAddress')==b.ACCOUNT for o in physical.get('owners',[])) or physical.get('parents')!=[entry['archiveParentId']]:raise StorageError('HISTORICAL_PROVIDER_IDENTITY')
    if str(physical.get('size'))!=str(entry['size']) or physical.get('md5Checksum')!=entry['md5'] or (physical.get('sha256Checksum') is not None and physical['sha256Checksum']!=entry['sha256']) or any(p.get('type') in ['anyone','domain'] for p in physical.get('permissions',[])):raise StorageError('HISTORICAL_PROVIDER_CONTENT_OR_PUBLIC')
    if entry.get('mimeType') and physical.get('mimeType')!=entry['mimeType']:raise StorageError('HISTORICAL_PROVIDER_MIME')
    alias=bool(entry.get('stockShortcutId'))
    if stock.get('id')!=(entry['stockShortcutId'] if alias else entry['sourceId']) or stock.get('trashed') is not False or stock.get('driveId')!=b.SOURCE_DRIVE or len(stock.get('parents',[]))!=1:raise StorageError('HISTORICAL_STOCK_IDENTITY')
    if alias:
        if stock.get('mimeType')!=SHORTCUT or stock.get('shortcutDetails',{}).get('targetId')!=physical['id'] or stock.get('properties',{}).get('mgsArchiveLogicalSource')!=entry['sourceId']:raise StorageError('HISTORICAL_ALIAS_TARGET')
    elif str(stock.get('size'))!=str(entry['size']) or stock.get('mimeType')!=physical.get('mimeType') or stock.get('md5Checksum')!=entry['md5'] or (stock.get('sha256Checksum') is not None and stock['sha256Checksum']!=entry['sha256']):raise StorageError('HISTORICAL_RETAINED_SOURCE_CONTENT')
    return {'record_kind':'mgs.logical.media.v1','storage_backend':'gmail_archive','mapping_kind':'historical_verified','stock_representation':'shortcut' if alias else 'retained_source','id':entry['sourceId'],'logical_source_id':entry['sourceId'],'provider_id':physical['id'],'stock_file_id':stock['id'],'name':stock['name'],'mimeType':physical['mimeType'],'size':physical['size'],'md5Checksum':physical['md5Checksum'],'sha256Checksum':entry['sha256'],'driveId':stock['driveId'],'parents':list(stock['parents']),'trashed':False,'capabilities':{**stock.get('capabilities',{}),'canDownload':physical.get('capabilities',{}).get('canDownload',False)},'provider_metadata':physical,'stock_metadata':stock,'archive_job_id':entry['jobId'],'lineage_id':entry.get('lineageId')}

def move_historical_retained_stock(d,entry,target_parent_id,expected_parent_id):
    physical=meta(d,entry['archiveId']);stock=meta(d,entry['sourceId']);before=historical_media_record(entry,physical,stock)
    if stock['parents']!=[expected_parent_id]:raise StorageError('HISTORICAL_STOCK_PARENT_CAS')
    destination=meta(d,target_parent_id);current=d.relative_parent(expected_parent_id,b.SOURCE_ROOT);target=d.relative_parent(target_parent_id,b.SOURCE_ROOT)
    if destination.get('driveId')!=b.SOURCE_DRIVE or destination.get('trashed') or destination.get('mimeType')!=b.FOLDER or current[:-1]!=target[:-1] or not target or target[-1] not in ['01_READY','02_TESTING','03_TESTED','04_WINNERS','05_REJECTED']:raise StorageError('HISTORICAL_STOCK_STATUS_SCOPE')
    d.api('PATCH','files/'+entry['sourceId'],{'supportsAllDrives':'true','addParents':target_parent_id,'removeParents':expected_parent_id,'fields':'id,parents,driveId'},{})
    after=historical_media_record(entry,meta(d,entry['archiveId']),meta(d,entry['sourceId']))
    if after['parents']!=[target_parent_id] or after['provider_metadata']['parents']!=physical['parents'] or after['md5Checksum']!=before['md5Checksum']:raise StorageError('HISTORICAL_STOCK_MOVE_READBACK')
    return after

def require_historical_ack(d,entry):
    c=b.config_load();found=d.one(c['requests_folder_id'],'backfill-ack:'+entry['jobId'])
    if not found:raise StorageError('HISTORICAL_NATIVE_ACK_REQUIRED')
    metadata=d.meta(found['id']);b.require_publisher(metadata,b.CANONICAL_SA);raw=d.raw(found['id']);ack=json.loads(raw)
    if metadata.get('parents')!=[c['requests_folder_id']] or metadata.get('driveId')!=b.SOURCE_DRIVE or metadata.get('properties',{}).get('mgsArchiveType')!='backfill_ack' or metadata.get('properties',{}).get('sha256')!=hashlib.sha256(raw).hexdigest() or ack.get('schema')!='mgs.archive.backfill.ack.v1' or ack.get('status')!='verified' or ack.get('deleteSource') is not False or ack.get('jobId')!=entry['jobId']:raise StorageError('HISTORICAL_NATIVE_ACK_SCOPE')
    matches=[a for a in ack.get('assets',[]) if a.get('source_id')==entry['sourceId']]
    if len(matches)!=1 or any(matches[0].get(k)!=entry[v] for k,v in [('archive_id','archiveId'),('size','size'),('md5','md5'),('sha256','sha256')]):raise StorageError('HISTORICAL_NATIVE_ACK_MAPPING')
    return True
