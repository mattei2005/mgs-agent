#!/usr/bin/env python3
"""Same-ID stock/layout migration under approved whole-Drive authority.

No binary copy, DELETE, trash, permission write or credential change. Keeps the
existing upload ID and all stock IDs; staging remains temporary below intake.
"""
from __future__ import annotations
import argparse,fcntl,hashlib,json,time,urllib.request,urllib.parse,urllib.error
import ares_archive_bridge as b
import ares_archive_backfill as h
import ares_archive_locations as loc
import mgs_archive_owner_transport as t
import mgs_private_backup_transport as bt
import mgs_backup_automation as ba
import mgs_whole_drive_migration as whole
AUTH='1563192086025474101'
HOME=t.HOME/'stock-layout'
SNAPSHOT=HOME/'source-snapshot.json'
PROOF=HOME/'verification.json'
JOURNAL=HOME/'journal.json'
FIELDS='id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,version,createdTime,trashed,owners(emailAddress,permissionId),permissions(type,emailAddress,role),properties,appProperties,shortcutDetails(targetId)'

def all_shared(d):
    out=[];page=None
    while True:
        params={'corpora':'drive','driveId':b.SOURCE_DRIVE,'q':'trashed=false','supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':1000,'fields':'nextPageToken,files('+FIELDS+')'}
        if page:params['pageToken']=page
        value=d.api('GET','files',params);out.extend(value.get('files',[]));page=value.get('nextPageToken')
        if len(out)>30000:raise b.ArchiveError('LAYOUT_INVENTORY_BOUND')
        if not page:return out

def descendants(rows,root,exclude=()):
    selected={};frontier={root};excluded=set(exclude)
    while frontier:
        found={x['id']:x for x in rows if x['id'] not in selected and x['id'] not in excluded and len(x.get('parents',[]))==1 and x['parents'][0] in frontier}
        selected.update(found);frontier={k for k,x in found.items() if x.get('mimeType')==b.FOLDER}
    return selected

def native(d,fid):return d.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':FIELDS})

def owned_inventory(sa,parent_ids):
    # Only exact approved frozen parent IDs, never an account-wide owner scan.
    if not parent_ids:raise b.ArchiveError('LAYOUT_EXACT_PARENT_SCOPE_REQUIRED')
    current={};parents=sorted(set(parent_ids))
    for start in range(0,len(parents),30):
        query='trashed=false and ('+' or '.join("'"+fid+"' in parents" for fid in parents[start:start+30])+')';page=None
        while True:
            params={'q':query,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':1000,'fields':'nextPageToken,files('+FIELDS+')'}
            if page:params['pageToken']=page
            value=sa.api('GET','files',params);current.update({x['id']:x for x in value.get('files',[])});page=value.get('nextPageToken')
            if not page:break
    return current

def propagated_inventory(sa,expected_ids,max_seconds=1800,parent_ids=None):
    """Google can return a moved folder before its children change ownership.
    Observe the same IDs; never replay the folder move to cure propagation.
    """
    deadline=time.monotonic()+max_seconds;observations=[]
    while True:
        current=owned_inventory(sa,parent_ids)
        missing=[fid for fid in expected_ids if fid not in current or current[fid].get('driveId') or not any(o.get('emailAddress')==b.ACCOUNT and o.get('permissionId')==b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT] for o in current[fid].get('owners',[]))]
        observations.append({'at':b.now_iso(),'pending_native_ownership':len(missing),'expected_count':len(expected_ids)})
        b.atomic_json(HOME/'propagation-observations.json',observations)
        if not missing:return current
        if time.monotonic()>=deadline:raise b.ArchiveError('LAYOUT_DESCENDANT_PROPAGATION_PENDING:'+str(len(missing)))
        time.sleep(15)

def content_evidence(sa,objects,index):
    live=b.read_json(b.DATA/'archive-index.json',{}).get('mappings',{});out={}
    for fid,meta in objects.items():
        mime=meta['mimeType']
        if mime in [b.FOLDER,'application/vnd.google-apps.shortcut']:continue
        if meta.get('properties',{}).get('mgsArchiveKey')=='heartbeat:worker-v1' and meta.get('properties',{}).get('mgsArchiveType')=='heartbeat':
            b.require_publisher(sa.meta(fid),b.ACCOUNT)
            body=json.loads(sa.raw(fid))
            if body.get('schema')!='mgs.archive.heartbeat.v1' or body.get('deleteSource') is not False or body.get('triggerUid')!='2456112746912022528' or not body.get('workerSha256'):raise b.ArchiveError('LAYOUT_LEGACY_HEARTBEAT_SCOPE')
            out[fid]={'kind':'mutable_legacy_heartbeat','body_before':body};continue
        if mime=='application/vnd.google-apps.spreadsheet':
            out[fid]={'kind':'sheet','snapshot':whole.snapshot(sa,fid)[0],'grid':whole.sheets_get(sa,fid,params={'includeGridData':'true'})};continue
        if mime.startswith('application/vnd.google-apps.'):raise b.ArchiveError('LAYOUT_NATIVE_DOCUMENT_SNAPSHOT_REQUIRED:'+fid)
        entry=index.get('mappings',{}).get(fid) or live.get(fid)
        if entry:
            expected={k:entry[k] for k in ['size','md5','sha256']}
            if entry.get('verified') is not True or meta.get('size')!=expected['size'] or meta.get('md5Checksum')!=expected['md5'] or meta.get('sha256Checksum')!=expected['sha256']:raise b.ArchiveError('LAYOUT_PRIOR_FULL_BYTE_PROOF_DRIFT:'+fid)
            out[fid]={'kind':'prior_full_streams','hashes':expected,'job_id':entry.get('job_id') or entry.get('jobId')}
        else:
            hashes=sa.hashes(fid)
            if hashes['size']!=meta.get('size') or hashes['md5']!=meta.get('md5Checksum') or (meta.get('sha256Checksum') and hashes['sha256']!=meta['sha256Checksum']):raise b.ArchiveError('LAYOUT_AUXILIARY_BYTE_PROOF')
            out[fid]={'kind':'full_stream_required_after_move','hashes':hashes}
    return out

def unchanged(before,after,*,parent=None):
    fields=['id','name','mimeType','size','md5Checksum','sha256Checksum','createdTime','properties','appProperties','shortcutDetails']
    if any(before.get(k)!=after.get(k) for k in fields) or after.get('trashed') is not False:raise b.ArchiveError('LAYOUT_CONTENT_OR_ID_CHANGED:'+before['id'])
    if after.get('parents')!=(parent if parent is not None else before.get('parents')):raise b.ArchiveError('LAYOUT_PARENT_CHANGED:'+before['id'])
    if not str(after.get('version','')).isdigit() or int(after['version'])<int(before['version']):raise b.ArchiveError('LAYOUT_VERSION_CHANGED')
    return True

def move_once(owner,sa,journal,fid,old_parent,new_parent,*,name=None):
    key='move:'+fid;current=native(sa,fid);intent=journal.data['intents'].get(key)
    if intent:
        binding=intent['binding']
        if binding['old_parent']!=old_parent or binding['new_parent']!=new_parent or binding.get('new_name')!=name:raise b.ArchiveError('LAYOUT_INTENT_BINDING')
        if current.get('parents')==[new_parent] and (name is None or current.get('name')==name):return current
        raise b.ArchiveError('LAYOUT_MOVE_UNKNOWN_NO_REPLAY:'+fid)
    if current.get('parents')!=[old_parent] or current.get('trashed') is not False:raise b.ArchiveError('LAYOUT_SOURCE_CAS:'+fid)
    journal.intent(key,{'old_parent':old_parent,'new_parent':new_parent,'new_name':name,'metadata_before':current})
    payload={'name':name} if name is not None else {}
    url=owner.base+'files/'+fid+'?'+urllib.parse.urlencode({'supportsAllDrives':'true','addParents':new_parent,'removeParents':old_parent,'fields':'id'})
    request=urllib.request.Request(url,data=b.canonical(payload),headers={'Authorization':'Bearer '+owner.token,'Content-Type':'application/json'},method='PATCH')
    try:
        with urllib.request.urlopen(request,timeout=180) as response:json.load(response)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):pass
    actual=native(sa,fid)
    if actual.get('parents')!=[new_parent] or (name is not None and actual.get('name')!=name):raise b.ArchiveError('LAYOUT_MOVE_READBACK_FAILED:'+fid)
    journal.landed(key,fid);return actual

def prepare():
    HOME.mkdir(parents=True,exist_ok=True)
    with b.queue_lock():
        sa=b.Drive();owner=t.OwnerDrive();journal=t.Journal(JOURNAL)
        binding=b.read_json(loc.BINDING)
        if binding:loc.validate(binding);return binding
        key='folder:stock-layout:'+AUTH;fid=journal.known_id(key)
        if not fid:
            rows=[x for x in owner.listing(b.ARCHIVE_ROOT) if x.get('name')=='CRIATIVOS' and x.get('mimeType')==b.FOLDER]
            if len(rows)>1:raise b.ArchiveError('LAYOUT_STOCK_ROOT_AMBIGUOUS')
            if rows:fid=rows[0]['id']
            else:
                journal.allow_create(key);journal.intent(key,{'parent':b.ARCHIVE_ROOT,'name':'CRIATIVOS','authority':AUTH})
                fid=owner.api('POST','files',{'fields':'id'},{'name':'CRIATIVOS','mimeType':b.FOLDER,'parents':[b.ARCHIVE_ROOT],'properties':{'mgsArchiveKey':'stock-root:'+AUTH,'mgsArchiveType':'stock_root'}})['id'];journal.landed(key,fid)
        root=native(sa,fid)
        if root.get('parents')!=[b.ARCHIVE_ROOT] or root.get('driveId') or root.get('name')!='CRIATIVOS' or not any(x.get('emailAddress')==b.ACCOUNT for x in root.get('owners',[])):raise b.ArchiveError('LAYOUT_STOCK_ROOT_BINDING')
        binding={'schema':'mgs.archive.stock.layout.v1','approval_message_id':loc.APPROVAL,'execution_confirmation_message_id':AUTH,'source_drive_id':b.SOURCE_DRIVE,'staging_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'upload_root_id':loc.UPLOAD,'owner':b.ACCOUNT,'stock_root_id':fid,'active':False,'phase':'prepared','same_ids_verified':False,'consumer_canary_verified':False,'acceptance_proof':str(PROOF),'prepared_at':b.now_iso()}
        loc.validate(binding);b.atomic_json(loc.BINDING,binding);return binding

def verify_relocated(d,meta,asset):
    binding=loc.active()
    if not binding or not binding.get('same_ids_verified'):raise b.ArchiveError('LAYOUT_RELOCATION_NOT_ACTIVE')
    snapshot=b.read_json(SNAPSHOT,{});proof=b.read_json(PROOF,{})
    if snapshot.get('schema')!='mgs.archive.stock.snapshot.v1' or proof.get('status')!='same_ids_verified' or proof.get('snapshot_sha256')!=ba.sha(snapshot) or proof.get('stock_root_id')!=binding['stock_root_id']:raise b.ArchiveError('LAYOUT_RELOCATION_PROOF_BINDING')
    before=snapshot.get('objects',{}).get(asset['sourceId'])
    if not before or before.get('driveId')!=b.SOURCE_DRIVE or before.get('parents')!=[asset['sourceParentId']]:raise b.ArchiveError('LAYOUT_RELOCATION_MEMBERSHIP')
    for field,key in [('id','sourceId'),('name','name'),('size','size'),('mimeType','mimeType'),('md5Checksum','md5'),('sha256Checksum','sha256'),('createdTime','sourceCreatedTime')]:
        if str(before.get(field))!=str(asset.get(key)) or meta.get(field)!=before.get(field):raise b.ArchiveError('LAYOUT_RELOCATION_FROZEN_CONTENT')
    unchanged(before,meta)
    if not loc.stock_metadata_allowed(meta) or loc.stock_parent(d,meta['parents'][0])!=asset['relativeParent']:raise b.ArchiveError('LAYOUT_RELOCATION_NATIVE_SCOPE')
    # Independent SA native snapshot/receipt provenance remains required.
    fid=proof.get('native_snapshot_id');native_meta=d.meta(fid);b.require_publisher(native_meta,b.CANONICAL_SA)
    if not b.control_object_scope(native_meta,b.config_load()['control_folder_id']) or ba.sha(d.raw(fid))!=proof['snapshot_sha256']:raise b.ArchiveError('LAYOUT_RELOCATION_NATIVE_PROOF')
    return True

def apply():
    binding=prepare()
    with (b.DATA/'.intake-state.lock').open('a+') as intake_lock:
        fcntl.flock(intake_lock,fcntl.LOCK_EX)
        with (bt.HOME/'backup-lane.lock').open('a+') as backup_lock:
            fcntl.flock(backup_lock,fcntl.LOCK_EX)
            with b.queue_lock():
                manifest,stage=h.manifest_load();idx=b.read_json(h.location()/'backfill-index.json',{});historical=b.read_json(bt.HOME/'historical-manifest.json',{});bs=b.read_json(ba.STATE,{})
                if set(idx.get('mappings',{}))!={x['sourceId'] for x in manifest['assets']} or any(x.get('verified') is not True for x in idx.get('mappings',{}).values()):raise b.ArchiveError('LAYOUT_ALL_HISTORICAL_BYTES_REQUIRED')
                verified={x['body']['asset']['sourceId'] for x in bs.get('jobs',{}).values() if x.get('verified')}
                if not {x['sourceId'] for x in historical.get('assets',[])}<=verified:raise b.ArchiveError('LAYOUT_ALL_BACKUPS_REQUIRED')
                intake=b.read_json(b.DATA/'intake-state.json',{'claims':{}})
                if any(x.get('status')!='complete' for x in intake.get('claims',{}).values()):raise b.ArchiveError('LAYOUT_ACTIVE_INTAKE_CLAIM')
                sa=b.Drive(True);owner=t.OwnerDrive();journal=t.Journal(JOURNAL);c=b.config_load()
                snapshot=b.read_json(SNAPSHOT)
                if snapshot is None:
                    rows=all_shared(sa);objects=descendants(rows,b.SOURCE_ROOT,exclude=[loc.UPLOAD]);tops=[x for x in objects.values() if x.get('parents')==[b.SOURCE_ROOT]]
                    if any(x.get('mimeType')!=b.FOLDER for x in tops):raise b.ArchiveError('LAYOUT_TOP_BINARY_SCOPE')
                    snapshot={'schema':'mgs.archive.stock.snapshot.v1','approval_message_id':loc.APPROVAL,'execution_confirmation_message_id':AUTH,'frozen_at':b.now_iso(),'source_root':native(sa,b.SOURCE_ROOT),'stock_root_id':binding['stock_root_id'],'upload':native(sa,loc.UPLOAD),'objects':objects,'top_folders':tops,'old_root_children':[x for x in rows if x.get('parents')==[b.SOURCE_DRIVE]]}
                    snapshot['content_evidence']=content_evidence(sa,objects,idx)
                    fixtures={x['id']:x for x in snapshot['old_root_children'] if x['id'] not in [b.SOURCE_ROOT,ba.load()[0]['sourceRootId']]}
                    snapshot['root_fixture_content']=content_evidence(sa,fixtures,idx)
                    b.atomic_json(SNAPSHOT,snapshot)
                # Freeze native immutable SA proof before any folder moves.
                fid=sa.upload_once(c['control_folder_id'],'stock-layout-source-'+ba.sha(snapshot)+'.json',b.canonical(snapshot),'application/json','stock-layout-snapshot:'+ba.sha(snapshot),'stock_layout_snapshot')
                if sa.raw(fid)!=b.canonical(snapshot):raise b.ArchiveError('LAYOUT_NATIVE_SNAPSHOT_READBACK')
                b.require_publisher(sa.meta(fid),b.CANONICAL_SA)
                c.update(control_cutover_in_progress=True);b.atomic_json(b.CONFIG,c)
                transition={**binding,'phase':'transition','native_snapshot_id':fid};b.atomic_json(loc.BINDING,transition)
                for row in snapshot['top_folders']:move_once(owner,sa,journal,row['id'],b.SOURCE_ROOT,binding['stock_root_id'])
                move_once(owner,sa,journal,loc.UPLOAD,b.SOURCE_ROOT,b.SOURCE_DRIVE)
                move_once(owner,sa,journal,b.SOURCE_ROOT,b.SOURCE_DRIVE,loc.UPLOAD,name='_PROCESSAMENTO')
                # Empty backup staging stays transient below intake; direct
                # uploads already use archive-owned slots. Preserve tier IDs.
                p,_=ba.load();move_once(owner,sa,journal,p['sourceRootId'],b.SOURCE_DRIVE,loc.UPLOAD)
                for row in snapshot['old_root_children']:
                    if row['id'] in [b.SOURCE_ROOT,p['sourceRootId']]:continue
                    if row.get('properties',{}).get('validationOnly')!='true':raise b.ArchiveError('LAYOUT_UNEXPECTED_ROOT_OBJECT:'+row['id'])
                    move_once(owner,sa,journal,row['id'],b.SOURCE_DRIVE,p['corporateRootId'])
                # Full native listing joined by exact IDs, with bounded Google
                # ownership-propagation recovery. No repeated moves or copies.
                fixture_ids={x['id'] for x in snapshot['old_root_children'] if x['id'] not in [b.SOURCE_ROOT,p['sourceRootId']]}
                parent_scope={parent for x in snapshot['objects'].values() for parent in x.get('parents',[]) if parent!=b.SOURCE_ROOT}|{binding['stock_root_id'],p['corporateRootId']}
                current=propagated_inventory(sa,set(snapshot['objects'])|fixture_ids,parent_ids=parent_scope)
                writers=h.WRITERS|{b.CANONICAL_SA};verified_objects={}
                for key,before in snapshot['objects'].items():
                    after=current.get(key)
                    if not after:raise b.ArchiveError('LAYOUT_MISSING_SAME_ID:'+key)
                    new_parent=[binding['stock_root_id']] if before.get('parents')==[b.SOURCE_ROOT] else None
                    mutable=snapshot['content_evidence'].get(key,{}).get('kind')=='mutable_legacy_heartbeat'
                    if mutable:
                        if any(before.get(k)!=after.get(k) for k in ['id','name','mimeType','createdTime','properties']) or after.get('parents')!=(new_parent or before['parents']) or after.get('trashed') is not False:raise b.ArchiveError('LAYOUT_MUTABLE_HEARTBEAT_METADATA')
                        b.require_publisher(sa.meta(key),b.ACCOUNT);old_body=snapshot['content_evidence'][key]['body_before'];new_body=json.loads(sa.raw(key))
                        if any(new_body.get(k)!=old_body.get(k) for k in ['schema','workerSha256','triggerUid','deleteSource']) or new_body.get('deleteSource') is not False:raise b.ArchiveError('LAYOUT_MUTABLE_HEARTBEAT_PROTOCOL')
                    else:unchanged(before,after,parent=new_parent)
                    if after.get('driveId') or not any(x.get('emailAddress')==b.ACCOUNT for x in after.get('owners',[])) or any(x.get('type') in ['anyone','domain'] for x in after.get('permissions',[])) or not writers<={x.get('emailAddress') for x in after.get('permissions',[]) if x.get('role')=='writer'}:raise b.ArchiveError('LAYOUT_OWNER_OR_ACCESS:'+key)
                    verified_objects[key]={'id':key,'parents':after['parents'],'version':after['version'],'same_id':True,'content_unchanged':not mutable,'expected_legacy_heartbeat_transition':mutable,'human_sa_access_verified':True}
                for key,evidence in {**snapshot['content_evidence'],**snapshot['root_fixture_content']}.items():
                    if evidence['kind']=='full_stream_required_after_move' and sa.hashes(key)!=evidence['hashes']:raise b.ArchiveError('LAYOUT_AUXILIARY_POST_MOVE_BYTES:'+key)
                    if evidence['kind']=='sheet' and (whole.snapshot(sa,key)[0]!=evidence['snapshot'] or whole.sheets_get(sa,key,params={'includeGridData':'true'})!=evidence['grid']):raise b.ArchiveError('LAYOUT_SHEET_POST_MOVE_CONTENT:'+key)
                for row in snapshot['old_root_children']:
                    if row['id'] not in fixture_ids:continue
                    unchanged(row,current[row['id']],parent=[p['corporateRootId']])
                    cp,_=ba.corp.load_plan();ba.corp.check_acl(h.permissions(sa,row['id']),ba.corp.desired(cp))
                proof={'schema':'mgs.archive.stock.verification.v1','status':'same_ids_verified','snapshot_sha256':ba.sha(snapshot),'native_snapshot_id':fid,'stock_root_id':binding['stock_root_id'],'verified_at':b.now_iso(),'objects':verified_objects,'binary_copies_created':0,'files_deleted':0}
                b.atomic_json(PROOF,proof)
                accepted={**binding,'phase':'consumer_canary','same_ids_verified':True,'consumer_canary_verified':False,'acceptance_proof':str(PROOF),'active':True,'native_snapshot_id':fid,'snapshot_sha256':proof['snapshot_sha256']}
                # In-process canary context only. Other consumers fail closed;
                # never claim a consumer PASS before the actual read/download.
                b.atomic_json(loc.BINDING,accepted)
                try:
                    with loc.internal_canary():
                        loc.verify_stock_root(sa);loc.verify_staging_root(sa)
                        import ares_archive_storage as storage
                        candidates=[k for k,x in idx['mappings'].items() if x.get('relative_parent',[])[-1:] in [['01_READY'],['VID'],['IMG']]] or list(idx['mappings'])
                        source_id=candidates[0];record=storage.resolve_media(source_id,sa.token)
                        if not record or sa.hashes(record['provider_id'])!={k:idx['mappings'][source_id][k] for k in ['size','md5','sha256']}:raise b.ArchiveError('LAYOUT_CONSUMER_DOWNLOAD')
                        import ares_upload_context_layout as upload
                        context=b.read_json(b.DATA/'upload-context-layout.json');assert isinstance(context,dict)
                        for slot in context['slots']:upload.validate_slot(sa,context,slot)
                    tops=sa.listing(b.SOURCE_DRIVE)
                    if len(tops)!=1 or tops[0]['id']!=loc.UPLOAD:raise b.ArchiveError('LAYOUT_ROOT_NOT_UPLOAD_ONLY')
                    residual=all_shared(sa);intake_tree=descendants(residual,loc.UPLOAD)
                    if {x['id'] for x in residual}!={loc.UPLOAD}|set(intake_tree):raise b.ArchiveError('LAYOUT_ORPHAN_SHARED_OBJECT_OUTSIDE_INTAKE')
                    processed_ids=set(idx['mappings'])|set(b.read_json(b.DATA/'archive-index.json',{}).get('mappings',{}))
                    if processed_ids&set(intake_tree):raise b.ArchiveError('LAYOUT_PROCESSED_MEDIA_STILL_IN_OLD_DRIVE')
                    proof.update(consumer_canary={'source_id':source_id,'provider_id':record['provider_id'],'stock_file_id':record['stock_file_id'],'full_stream_verified':True,'upload_slots_verified':len(context['slots'])},root_only_upload_verified=True,all_residual_shared_objects_under_intake=True,residual_shared_object_count=len(residual),old_drive_processed_media_count=0)
                    b.atomic_json(PROOF,proof);accepted.update(phase='active',consumer_canary_verified=True,accepted_at=b.now_iso());b.atomic_json(loc.BINDING,accepted)
                    c.update(control_cutover_in_progress=False,whole_drive_layout_complete=True);b.atomic_json(b.CONFIG,c)
                    return {'status':'layout_active','stock_objects_verified':len(verified_objects),'upload_only':True,'proof':str(PROOF)}
                except Exception:
                    accepted.update(phase='transition',consumer_canary_verified=False);b.atomic_json(loc.BINDING,accepted);raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','apply']);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if args.action=='apply' and not args.apply:raise SystemExit('APPLY_REQUIRED')
    print(json.dumps(prepare() if args.action=='prepare' else apply(),ensure_ascii=False))
