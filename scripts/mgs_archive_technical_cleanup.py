#!/usr/bin/env python3
"""One confirmed technical cleanup; exact frozen 30 IDs, trash only, no generic mutation API."""
from __future__ import annotations
import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any, cast
import ares_archive_bridge as b
import mgs_archive_owner_transport as t

HOME=b.BASE/'data/ares/creative-ops/30tb-archive/legacy-cleanup-1566643959458168864'
DIGEST='3835baf8f8af312267ad2a4c3e9856544278b92479f55857152dca60c73a7a0b'
CONFIRM='1566800073071788244'
QUESTION='1566646147366264864'
USER='344196393512075265'
CANARY_JOB='526d7a2a007c1fed4b2a9147f92d62b4'
FIELDS='id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,version,trashed,createdTime,owners(emailAddress,permissionId),permissions(type,emailAddress,role),properties,shortcutDetails(targetId),capabilities(canTrash,canDownload)'
INVENTORY=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
class CleanupError(b.ArchiveError):pass

def require(ok,code):
    if not ok:raise CleanupError(code)

def sha(value):return hashlib.sha256(b.canonical(value)).hexdigest()

def validate_plan(p):
    require(sha(p)==DIGEST,'FROZEN_PLAN_DIGEST')
    require(p.get('action')=='move_exact_objects_to_trash_no_permanent_delete','TRASH_ONLY')
    ids={x['id'] for x in p['targets']}
    require(len(ids)==len(p['targets'])==30 and p['folder_count']==29 and p['pilot_file_count']==1,'TARGET_SET')
    protected=set(p['protected_empty_compatibility_folders']+p['protected_remaining_media']+[p['protected_upload_id']])
    require(not ids & protected,'PROTECTED_TARGET_COLLISION')
    return p

def load_plan():return validate_plan(b.read_json(HOME/'cleanup-plan.json'))

def validate_confirmation(v):
    require(all(v.get(k)==x for k,x in {'confirmation_message_id':CONFIRM,'question_message_id':QUESTION,'user_id':USER,'plan_sha256':DIGEST}.items()),'EXACT_CRITICAL_CONFIRMATION')
    return True

def native_meta(d,fid):return d.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':FIELDS})

def check_metadata(actual,expected,after=False,version=True,owner_scope=True):
    keys=['id','name','mimeType','parents','driveId','size','md5Checksum','sha256Checksum','createdTime','properties','shortcutDetails']
    for k in keys:
        if k in expected:require(actual.get(k)==expected[k],'NATIVE_CAS:'+k+':'+expected['id'])
    for k in ['owners','permissions']:
        if k in expected:require(sorted(b.canonical(x) for x in actual.get(k,[]))==sorted(b.canonical(x) for x in expected[k]),'NATIVE_CAS:'+k+':'+expected['id'])
    require(actual.get('trashed') is after,'TRASH_STATE:'+expected['id'])
    if version and not after:require(actual.get('version')==expected.get('version'),'NATIVE_CAS:version:'+expected['id'])
    if owner_scope:require(not actual.get('driveId') and any(o.get('emailAddress')==b.ACCOUNT and o.get('permissionId')==b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT] for o in actual.get('owners',[])),'NATIVE_OWNER_SCOPE')
    return True

def children(d,fid):
    out=[];page=None
    while True:
        params={'q':"'"+fid+"' in parents and trashed=false",'pageSize':1000,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','fields':'files(id),nextPageToken'}
        if page:params['pageToken']=page
        r=d.api('GET','files',params);out.extend(r.get('files',[]));page=r.get('nextPageToken')
        if not page:return out

def check_children(rows,allowed):
    require(all(x['id'] in allowed for x in rows),'UNAPPROVED_CHILD_BLOCKS_FOLDER')
    return True

def bottom_up(rows):
    by={x['id']:x for x in rows}
    def depth(x,seen=None):
        seen=set() if seen is None else seen
        require(x['id'] not in seen,'TARGET_PARENT_CYCLE');seen.add(x['id'])
        parent=x.get('parents',[None])[0]
        return 1+depth(by[parent],seen) if parent in by else 0
    return sorted(rows,key=lambda x:(-depth(x),x['mimeType']==b.FOLDER,x['id']))

def read_many(d,ids):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        return dict(zip(ids,ex.map(lambda fid:native_meta(d,fid),ids)))

def reader_proof(sa,proof,include_pilot):
    import ares_archive_storage as storage
    record=storage.resolve_media(proof['logical_source_id'],sa.token)
    require(record is not None and record['provider_id']==proof['permanent_provider_id'],'PERMANENT_LOGICAL_READER')
    expected=proof['pilot_and_permanent_full_hashes'];ids=[proof['permanent_provider_id']]
    if include_pilot:ids.append(proof['pilot_id'])
    hashes={}
    for fid in ids:
        raw=sa.raw(fid);v={'size':str(len(raw)),'md5':hashlib.md5(raw).hexdigest(),'sha256':hashlib.sha256(raw).hexdigest()}
        require(v==expected,'FULL_BINARY_HASH:'+fid);hashes[fid]=v
    return {'logical_source_id':proof['logical_source_id'],'record':record,'full_streams':hashes,'verified_at':b.now_iso()}

def business_hashes():
    files=[INVENTORY,b.DATA/'archive-index.json',b.DATA/'manager-storage-standard.json']
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()}

def retired_canary_proof(d,job,receipt,ack):
    """An intentionally retired validation copy is history, never active media.

    Do not infer deletion of its old logical source or change immutable ACKs.
    This branch cannot accept a production lineage or any other canary.
    """
    if job.get('kind')!='canary' or job.get('jobId')!=CANARY_JOB:return None
    require(isinstance(ack,dict) and ack.get('jobId')==CANARY_JOB and ack.get('status')=='verified' and ack.get('kind')=='canary' and ack.get('deleteSource') is False,'RETIRED_CANARY_NATIVE_ACK')
    plan=load_plan();validate_confirmation(b.read_json(HOME/'confirmation.json',{}))
    final=b.read_json(HOME/'final-verification.json',{});state=b.read_json(HOME/'execution-state.json',{});proof=b.read_json(HOME/'pilot-duplicate-and-reference-proof.json',{})
    require(final.get('status')=='completed_verified' and final.get('plan_sha256')==DIGEST and final.get('confirmation_message_id')==CONFIRM and set(final.get('trashed_ids',[]))=={x['id'] for x in plan['targets']},'RETIRED_CANARY_COMPLETED_DISPOSITION')
    require(sha({k:v for k,v in job.items() if k not in ['jobId','createdAt']})[:32]==CANARY_JOB and len(job.get('assets',[]))==1 and job['assets'][0]['sourceId']==proof['logical_source_id'],'RETIRED_CANARY_REQUEST_BINDING')
    b.validate_receipt(job,receipt)
    copied=receipt['assets'][0];expected_hashes=proof['pilot_and_permanent_full_hashes']
    require(copied['archiveId']==proof['pilot_id'] and all(str(job['assets'][0][k])==str(v) for k,v in expected_hashes.items()),'RETIRED_CANARY_MEDIA_BINDING')
    require(len(ack.get('assets',[]))==1 and ack['assets'][0].get('archiveId')==proof['pilot_id'] and all(str(ack['assets'][0].get(k))==str(v) for k,v in expected_hashes.items()),'RETIRED_CANARY_ACK_BYTES')
    intent=state.get('intents',{}).get(proof['pilot_id'],{})
    require(intent.get('status')=='verified' and intent.get('confirmation_message_id')==CONFIRM,'RETIRED_CANARY_DISPOSITION_INTENT')
    actual=native_meta(d,proof['pilot_id']);check_metadata(actual,intent['metadata_before'],after=True)
    import ares_archive_storage as storage
    record=storage.resolve_media(proof['logical_source_id'],d.token)
    require(record is not None and record['provider_id']==proof['permanent_provider_id'] and record['md5Checksum']==expected_hashes['md5'] and record['sha256Checksum']==expected_hashes['sha256'] and record['size']==expected_hashes['size'],'RETIRED_CANARY_PERMANENT_READER')
    return {'record_kind':'mgs.retired.validation.v1','job_id':CANARY_JOB,'pilot_id':proof['pilot_id'],'plan_sha256':DIGEST,'confirmation_message_id':CONFIRM,'permanent_provider_id':proof['permanent_provider_id'],'pilot_trashed':True,'permanent_delete':False,'active_production_media':False}

def trash_once(owner,fid,expected,plan,state):
    # Dedicated owner operation, patterned after private backup retention. Generic
    # OwnerDrive.api PATCH/DELETE stays forbidden; no arbitrary ID or payload input.
    validate_plan(plan);validate_confirmation(b.read_json(HOME/'confirmation.json',{}))
    allowed={x['id'] for x in plan['targets']}
    require(fid in allowed and expected.get('id')==fid,'TRASH_EXACT_TARGET_ONLY')
    intent=state.get('intents',{}).get(fid,{})
    require(intent.get('status')=='prepared' and intent.get('plan_sha256')==DIGEST,'PERSISTED_INTENT_REQUIRED')
    current=native_meta(owner,fid);check_metadata(current,expected)
    require(current.get('capabilities',{}).get('canTrash') is True,'OWNER_CAN_TRASH_REQUIRED')
    if current['mimeType']==b.FOLDER:require(not children(owner,fid),'FOLDER_NOT_EMPTY')
    # Mark submitted before the RPC. Unknown results are reconciled, never replayed.
    intent.update(status='submitted',submitted_at=b.now_iso());b.atomic_json(HOME/'execution-state.json',state)
    url=owner.base+'files/'+fid+'?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':'id,trashed'})
    req=urllib.request.Request(url,data=b.canonical({'trashed':True}),headers={'Authorization':'Bearer '+owner.token,'Content-Type':'application/json','User-Agent':'MGS-Private-Exact-Cleanup/1'},method='PATCH')
    with urllib.request.urlopen(req,timeout=90) as response:json.load(response)


def run(apply=False):
    plan=load_plan();validate_confirmation(b.read_json(HOME/'confirmation.json',{}))
    frozen=cast(dict[str,Any],b.read_json(HOME/'native-inventory.json'));proof=cast(dict[str,Any],b.read_json(HOME/'pilot-duplicate-and-reference-proof.json'))
    target_map={x['id']:x for x in plan['targets']};target_ids=set(target_map)
    ids=sorted({x['id'] for x in frozen['records']}|set(frozen['roots'])|target_ids|{plan['protected_upload_id'],proof['permanent_provider_id']})
    with b.queue_lock():
        with INVENTORY.with_suffix(INVENTORY.suffix+'.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            sa=b.Drive(False);owner=t.OwnerDrive() if apply else None
            state=cast(dict[str,Any],b.read_json(HOME/'execution-state.json',{'schema':'mgs.technical.cleanup.state.v1','plan_sha256':DIGEST,'confirmation_message_id':CONFIRM,'intents':{}}))
            require(state.get('plan_sha256')==DIGEST and state.get('confirmation_message_id')==CONFIRM and set(state['intents'])<=target_ids,'JOURNAL_BINDING')
            # Reconcile exact native effects before any retry or new write.
            for fid,intent in state['intents'].items():
                if intent['status']=='prepared':continue
                actual=native_meta(sa,fid)
                check_metadata(actual,intent['metadata_before'],after=True)
                intent.update(status='verified',metadata_after=actual,verified_at=b.now_iso())
            if state['intents']:b.atomic_json(HOME/'execution-state.json',state)
            prior=b.read_json(HOME/'execution-before.json')
            before=read_many(sa,ids)
            for fid,expected in target_map.items():
                if state['intents'].get(fid,{}).get('status')=='verified':check_metadata(before[fid],expected,after=True)
                else:check_metadata(before[fid],expected)
            for x in frozen['records']:
                if x['id'] not in target_ids:check_metadata(before[x['id']],x,version=False)
            for fid,x in before.items():
                if x['mimeType']==b.FOLDER and not x['trashed'] and fid!=plan['protected_upload_id']:
                    rows=children(sa,fid)
                    if fid in target_ids:check_children(rows,target_ids)
                    elif fid in frozen['roots']:check_children(rows,{a['id'] for a in frozen['records']})
            preserved=business_hashes()
            if prior:
                require(prior['business_hashes']==preserved,'BUSINESS_INVARIANTS_CHANGED')
            else:
                require(not state['intents'],'ORIGINAL_SNAPSHOT_REQUIRED')
                prior={'observed_at':b.now_iso(),'metadata':before,'business_hashes':preserved,'reader':reader_proof(sa,proof,True)}
                b.atomic_json(HOME/'execution-before.json',prior)
            out={'status':'preflight_verified','plan_sha256':DIGEST,'confirmation_message_id':CONFIRM,'target_count':len(target_ids),'apply':apply,'permanent_delete':False,'observed_at':b.now_iso()}
            if not apply:
                b.atomic_json(HOME/'live-preflight.json',out);return out
            for expected in bottom_up(plan['targets']):
                fid=expected['id']
                if state['intents'].get(fid,{}).get('status')=='verified':continue
                current=native_meta(sa,fid);check_metadata(current,expected)
                if fid not in state['intents']:
                    state['intents'][fid]={'status':'prepared','plan_sha256':DIGEST,'confirmation_message_id':CONFIRM,'metadata_before':current,'prepared_at':b.now_iso()}
                    b.atomic_json(HOME/'execution-state.json',state)
                # Bind the owner CAS to the exact frozen metadata, not SA capability fields.
                try:trash_once(owner,fid,expected,plan,state)
                except Exception as error:
                    # Reconcile by exact ID; no repeat of the mutation even after network error.
                    actual=native_meta(sa,fid)
                    if actual.get('trashed') is not True:
                        state['intents'][fid]['error_class']=type(error).__name__;b.atomic_json(HOME/'execution-state.json',state);raise
                actual=native_meta(sa,fid);owner_actual=native_meta(owner,fid)
                check_metadata(actual,expected,after=True);check_metadata(owner_actual,expected,after=True)
                state['intents'][fid].update(status='verified',metadata_after=actual,verified_at=b.now_iso());b.atomic_json(HOME/'execution-state.json',state)
            after=read_many(sa,ids)
            for fid in ids:
                check_metadata(after[fid],prior['metadata'][fid],after=fid in target_ids,version=fid not in target_ids and prior['metadata'][fid]['mimeType']!=b.FOLDER,owner_scope=fid!=plan['protected_upload_id'])
            require(business_hashes()==preserved,'BUSINESS_INVARIANTS_AFTER')
            out.update(status='completed_verified',trashed_ids=sorted(target_ids),folder_count=29,pilot_file_count=1,protected_object_count=len(ids)-len(target_ids),metadata_after=after,business_hashes=preserved,reader_after=reader_proof(sa,proof,False),verified_at=b.now_iso())
            b.atomic_json(HOME/'final-verification.json',out)
            return {k:v for k,v in out.items() if k not in ['metadata_after','reader_after','business_hashes','trashed_ids']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(run(args.apply),ensure_ascii=False))
