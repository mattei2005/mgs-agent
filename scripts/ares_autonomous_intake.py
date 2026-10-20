#!/usr/bin/env python3
"""Bounded contextual Drive inbox for Ares. No campaign, archive, ACL or deletion writes."""
from __future__ import annotations
import sys,json,hashlib,re,time,fcntl,contextlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as bridge
import ares_upload_context_layout as layout
DATA=bridge.DATA;STATE=DATA/'intake-state.json';CONFIG=DATA/'intake-config.json'
class IntakeError(RuntimeError):pass

PROTECTED=('asset_id','source_drive_id','asset_drive_id','canonical_filename','operation','original_checksum','clean_checksum','source_manager','ares_eligible','used_by','campaign_owner','reservation_status','reservation_request_id','meta_ad_id','meta_video_id','meta_creative_id')
def protected_fingerprint(row):return hashlib.sha256(bridge.canonical({k:row.get(k) for k in PROTECTED})).hexdigest()
def verify_reservation(row,baseline,batch):
    if row['asset_id'] in baseline:
        if protected_fingerprint(row) not in baseline[row['asset_id']]:raise IntakeError('EXISTING_RESERVATION_CHANGED')
    elif row.get('source_manager','').casefold()!=batch['manager_name'].casefold() or row.get('ares_eligible') is not False or row.get('used_by') or row.get('reservation_status') not in ['RESERVADO_PELO_GESTOR','RESERVED_BY_MANAGER']:raise IntakeError('NEW_LINEAGE_MANAGER_OR_RESERVATION')
    return True

def describe(row,slot):
    if not layout.OPERATION.fullmatch(slot.get('operation','')) or layout.MANAGERS.get(slot.get('manager_code'))!=slot.get('manager_name'):raise IntakeError('UNREGISTERED_CONTEXT')
    if row.get('parents')!=[slot['folder_id']] or row.get('trashed'):raise IntakeError('SOURCE_PARENT')
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,}',row.get('id','')) or not re.fullmatch(r'[a-f0-9]{32}',row.get('md5Checksum','')) or not re.fullmatch(r'[1-9][0-9]*',str(row.get('size',''))):raise IntakeError('UPLOAD_INCOMPLETE')
    return {'source_id':row['id'],'name':row['name'],'mime_type':row['mimeType'],'size':str(row['size']),'md5':row['md5Checksum'],'version':str(row['version']),'created_at':row['createdTime'],'source_parent_id':slot['folder_id'],'slot_id':slot.get('registered_slot_id',slot['folder_id']),'operation':slot['operation'],'manager_code':slot['manager_code'],'manager_name':slot['manager_name']}

def observe(state,descriptors,now):
    fingerprint=hashlib.sha256(bridge.canonical(sorted(descriptors,key=lambda d:d['source_id']))).hexdigest();old=state.get('observation',{})
    if old.get('fingerprint')==fingerprint:old['polls']+=1
    else:old={'fingerprint':fingerprint,'since':now,'polls':1}
    state['observation']=old
    return {'stable':bool(descriptors) and old['polls']>=3 and now-old['since']>=40,'fingerprint':fingerprint}

def make_batch(descriptors,excluded,limit=4):
    pending=sorted([d for d in descriptors if d['source_id'] not in excluded],key=lambda d:(d['created_at'],d['source_id']))
    if not pending:return None
    first=pending[0];selected=[d for d in pending if (d['operation'],d['manager_code'])==(first['operation'],first['manager_code'])][:limit]
    identity={'schema':'mgs.intake.batch.v1','operation':first['operation'],'manager_code':first['manager_code'],'manager_name':first['manager_name'],'sources':selected}
    identity['batch_id']=hashlib.sha256(bridge.canonical(identity)).hexdigest()[:32];identity['pending_total']=len(pending);return identity

def claim(state,batch,owner):
    if not isinstance(owner,str) or not owner:raise IntakeError('OWNER_REQUIRED')
    claims=state.setdefault('claims',{});ids={d['source_id'] for d in batch['sources']}
    for existing in claims.values():
        if existing.get('status')!='complete' and ids.intersection({d['source_id'] for d in existing['batch']['sources']}) and (existing['owner']!=owner or existing['batch']['batch_id']!=batch['batch_id']):raise IntakeError('PARALLEL_WRITER_BLOCKED')
    entry=claims.get(batch['batch_id'])
    if entry:
        if entry['owner']!=owner or entry['batch']['sources']!=batch['sources']:raise IntakeError('CLAIM_SCOPE_CHANGED')
        return entry
    entry={'owner':owner,'batch':batch,'status':'claimed','claimed_at':bridge.now_iso()};claims[batch['batch_id']]=entry;return entry

def complete(state,bid,owner,proofs):
    entry=state.get('claims',{}).get(bid)
    if not entry or entry['owner']!=owner:raise IntakeError('CLAIM_OWNER')
    expected={d['source_id'] for d in entry['batch']['sources']}
    if len(proofs)!=len(expected) or {p.get('source_id') for p in proofs}!=expected:raise IntakeError('INCOMPLETE_BATCH_PROOF')
    for p in proofs:
        if not all(p.get(k) is True for k in ['source_parent_verified','clean_verified','inventory_verified','reservation_preserved']) or not all(re.fullmatch(r'[a-f0-9]{64}',p.get(k,'')) for k in ['raw_sha256','clean_sha256']):raise IntakeError('MISSING_VERIFICATION')
    entry.update(status='complete',proofs=proofs,completed_at=bridge.now_iso());state.setdefault('completed',{}).update({pid:bid for pid in expected});return entry

@contextlib.contextmanager
def locked_state():
    with (DATA/'.intake-state.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);state=bridge.read_json(STATE,{'schema':'mgs.intake.state.v1','claims':{},'completed':{}})
        if not isinstance(state,dict) or state.get('schema')!='mgs.intake.state.v1' or not isinstance(state.get('claims'),dict):raise IntakeError('STATE_SCHEMA')
        yield state
        bridge.atomic_json(STATE,state)

def children_many(d,parents):
    rows=[]
    for start in range(0,len(parents),30):
        group=parents[start:start+30];query='trashed=false and ('+' or '.join("'"+p+"' in parents" for p in group)+')';page=None
        while True:
            params={'q':query,'corpora':'drive','driveId':bridge.SOURCE_DRIVE,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':1000,'fields':'nextPageToken,files(id,name,mimeType,parents,size,md5Checksum,version,createdTime,trashed)'}
            if page:params['pageToken']=page
            value=d.api('GET','files',params);rows+=value.get('files',[]);page=value.get('nextPageToken')
            if len(rows)>10000:raise IntakeError('BOUNDED_INTAKE_SCOPE')
            if not page:break
    return rows

def discover(d,manifest,cutoff):
    contexts={s['folder_id']:s for s in manifest['slots']};frontier=list(contexts);out=[];validated=set()
    for depth in range(12):
        if not frontier:return out
        next_ids=[]
        for row in children_many(d,frontier):
            if len(row.get('parents',[]))!=1:raise IntakeError('MULTIPARENT_SOURCE')
            parent=row['parents'][0];slot=contexts[parent]
            if row['mimeType']==layout.FOLDER:
                contexts[row['id']]={**slot,'registered_slot_id':slot.get('registered_slot_id',slot['folder_id']),'folder_id':row['id']};next_ids.append(row['id']);continue
            if bridge.timestamp(row['createdTime'])<bridge.timestamp(cutoff):continue
            rootid=slot.get('registered_slot_id',slot['folder_id'])
            if rootid not in validated:
                original=next(s for s in manifest['slots'] if s['folder_id']==rootid);layout.validate_slot(d,manifest,original);validated.add(rootid)
            out.append(describe(row,slot))
        frontier=next_ids
    raise IntakeError('CONTAINER_DEPTH')

def inventory_source_ids(rows):
    ids=set()
    for row in rows:
        for k in ['source_drive_id','asset_drive_id']:
            if row.get(k):ids.add(row[k])
        ids.update(row.get('duplicate_source_drive_ids') or [])
        for link in row.get('source_links') or row.get('duplicate_source_links') or []:
            if isinstance(link,dict) and link.get('source_drive_id'):ids.add(link['source_drive_id'])
    return ids

def monitor(polls=3,interval=20):
    cfg=bridge.read_json(CONFIG,{})
    if cfg.get('enabled') is not True:return {'status':'disabled','pending':0}
    if cfg.get('authority_message_id')!='1562188030205362227' or cfg.get('source_root_id')!=bridge.SOURCE_ROOT:raise IntakeError('AUTHORITY_SCOPE')
    manifest=bridge.read_json(DATA/'upload-context-layout.json');assert isinstance(manifest,dict)
    d=bridge.Drive();scope=bridge.config_load();layout.check_folder(d,manifest,manifest['upload_root_id'],bridge.SOURCE_ROOT,'UPLOAD MANUAL')
    with locked_state() as state:
        # Resume the same durable batch; never allocate a replacement on timeout.
        active=[x for x in state['claims'].values() if x['status']!='complete']
        if active:
            entry=sorted(active,key=lambda x:x['claimed_at'])[0];return {'status':'resume','batch_id':entry['batch']['batch_id'],'manifest':str(DATA/'intake-batches'/('batch-'+entry['batch']['batch_id']+'.json'))}
        rows=[json.loads(x) for x in (bridge.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if x.strip()];excluded=inventory_source_ids(rows)|set(state['completed'])
        for index in range(polls):
            descriptors=[r for r in discover(d,manifest,scope['effective_after']) if r['source_id'] not in excluded]
            if not descriptors:return {'status':'idle','pending':0}
            observation=observe(state,descriptors,time.time())
            if observation['stable']:
                batch=make_batch(descriptors,excluded,limit=cfg.get('batch_limit',4));assert batch is not None
                path=DATA/'intake-batches'/('batch-'+batch['batch_id']+'.json');existing=bridge.read_json(path)
                if existing and existing!=batch:raise IntakeError('IMMUTABLE_BATCH_CHANGED')
                if not existing:bridge.atomic_json(path,batch)
                return {'status':'pending','batch_id':batch['batch_id'],'manifest':str(path),'pending':batch['pending_total']}
            if index+1<polls:time.sleep(interval)
        return {'status':'uploading','pending':0}

def verify_completed(d,batch,baseline):
    rows=[json.loads(line) for line in (bridge.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()];proofs=[]
    for source in batch['sources']:
        matches=[r for r in rows if r.get('source_drive_id')==source['source_id'] or source['source_id'] in (r.get('duplicate_source_drive_ids') or [])]
        if len(matches)!=1:raise IntakeError('UNIQUE_LINEAGE_REQUIRED')
        row=matches[0];op=batch['operation'];kind=row.get('format')
        if row.get('operation')!=op or kind not in ['IMG','VID'] or row.get('metadata_clean') is not True:raise IntakeError('LINEAGE_CONTEXT_OR_ELIGIBILITY')
        verify_reservation(row,baseline,batch)
        raw=d.meta(source['source_id']);clean=d.meta(row['asset_drive_id'])
        if raw.get('name')!=source['name'] or d.relative_parent(raw['parents'][0],bridge.SOURCE_ROOT)!=[op,kind,'99_LEGACY'] or d.relative_parent(clean['parents'][0],bridge.SOURCE_ROOT)!=[op,kind,'01_READY']:raise IntakeError('FINAL_PARENT_SCOPE')
        if raw.get('driveId')!=bridge.SOURCE_DRIVE or clean.get('driveId')!=bridge.SOURCE_DRIVE or raw.get('trashed') or clean.get('trashed') or clean.get('name')!=row.get('canonical_filename'):raise IntakeError('FINAL_IDENTITY')
        hashes=d.hashes(source['source_id']);ch=d.hashes(clean['id'])
        allowed_raw={row['original_checksum'],row['clean_checksum']} if row['asset_id'] in baseline else {row['original_checksum']}
        if hashes['md5']!=source['md5'] or hashes['size']!=source['size'] or hashes['sha256'] not in allowed_raw or ch['sha256']!=row['clean_checksum'] or ch['md5']!=clean['md5Checksum'] or ch['size']!=clean['size']:raise IntakeError('FINAL_BINARY_PROOF')
        proofs.append({'source_id':source['source_id'],'clean_source_id':clean['id'],'raw_sha256':hashes['sha256'],'clean_sha256':ch['sha256'],'source_parent_verified':True,'clean_verified':True,'inventory_verified':True,'reservation_preserved':True})
    return proofs

def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['monitor','claim','complete']);ap.add_argument('--batch-id');ap.add_argument('--owner');args=ap.parse_args()
    try:
        if args.action=='monitor':result=monitor()
        else:
            cfg=bridge.read_json(CONFIG,{})
            if cfg.get('enabled') is not True or args.owner!=cfg.get('owner_job_id'):raise IntakeError('ACTIVE_NATIVE_OWNER_REQUIRED')
            if not re.fullmatch('[a-f0-9]{32}',args.batch_id or ''):raise IntakeError('BATCH_ID')
            batch=bridge.read_json(DATA/'intake-batches'/('batch-'+args.batch_id+'.json'));assert batch and batch['batch_id']==args.batch_id
            with locked_state() as state:
                if args.action=='claim':
                    result=claim(state,batch,args.owner)
                    if 'inventory_before' not in result:
                        baseline={}
                        for line in (bridge.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines():
                            if line.strip():
                                row=json.loads(line);baseline.setdefault(row['asset_id'],[]).append(protected_fingerprint(row))
                        result['inventory_before']=baseline
                else:
                    entry=state['claims'].get(args.batch_id)
                    if not entry or entry['owner']!=args.owner or not isinstance(entry.get('inventory_before'),dict):raise IntakeError('FROZEN_INVENTORY_BASELINE_REQUIRED')
                    result=complete(state,args.batch_id,args.owner,verify_completed(bridge.Drive(),batch,entry['inventory_before']))
        print(json.dumps(result,ensure_ascii=False));return 0
    except Exception as exc:
        error={'status':'blocked','reason':str(exc)[:220],'at':bridge.now_iso(),'scope':'intake_only','delete_source':False};bridge.atomic_json(DATA/'intake-last-error.json',error);print(json.dumps({k:v for k,v in error.items() if k!='at'}));return 2
if __name__=='__main__':raise SystemExit(main())
