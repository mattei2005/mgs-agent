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

def validate_selftest_identity(test,raw,clean,raw_sha):
    import ares_intake_selftest as checks
    try:return checks.validate_selftest_identity(test,raw,clean,raw_sha)
    except checks.SelftestError as exc:raise IntakeError(str(exc)) from exc

PROTECTED=('asset_id','source_drive_id','asset_drive_id','canonical_filename','operation','original_checksum','clean_checksum','source_manager','ares_eligible','used_by','campaign_owner','reservation_status','reservation_request_id','meta_ad_id','meta_video_id','meta_creative_id','status','asset_path','manager_media_folder_id','metadata_clean')
def protected_fingerprint(row):return hashlib.sha256(bridge.canonical({k:row.get(k) for k in PROTECTED})).hexdigest()
def verify_reservation(row,baseline,batch):
    if row['asset_id'] in baseline:
        if protected_fingerprint(row) not in baseline[row['asset_id']]:raise IntakeError('EXISTING_RESERVATION_CHANGED')
    elif row.get('source_manager','').casefold()!=batch['manager_name'].casefold() or row.get('ares_eligible') is not False or row.get('used_by') or row.get('reservation_status') not in ['RESERVADO_PELO_GESTOR','RESERVED_BY_MANAGER']:raise IntakeError('NEW_LINEAGE_MANAGER_OR_RESERVATION')
    return True

def describe(row,slot):
    if not layout.OPERATION.fullmatch(slot.get('operation','')) or layout.MANAGERS.get(slot.get('manager_code'))!=slot.get('manager_name'):raise IntakeError('UNREGISTERED_CONTEXT')
    if not str(row.get('mimeType','')).startswith(('image/','video/')):raise IntakeError('UNSUPPORTED_CREATIVE_MIME')
    if row.get('parents')!=[slot['folder_id']] or row.get('trashed'):raise IntakeError('SOURCE_PARENT')
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,}',row.get('id','')) or not re.fullmatch(r'[a-f0-9]{32}',row.get('md5Checksum','')) or not re.fullmatch(r'[1-9][0-9]*',str(row.get('size',''))):raise IntakeError('UPLOAD_INCOMPLETE')
    return {'source_id':row['id'],'name':row['name'],'mime_type':row['mimeType'],'size':str(row['size']),'md5':row['md5Checksum'],'sha256':row.get('sha256Checksum'),'version':str(row['version']),'created_at':row['createdTime'],'source_parent_id':slot['folder_id'],'slot_id':slot.get('registered_slot_id',slot['folder_id']),'operation':slot['operation'],'manager_code':slot['manager_code'],'manager_name':slot['manager_name']}

def validate_new_batch(d,batch,manifest):
    """Fresh ID ancestry/content checks before the first durable writer claim."""
    for source in batch['sources']:
        slots=[s for s in manifest['slots'] if s['folder_id']==source['slot_id']]
        if len(slots)!=1:raise IntakeError('UNREGISTERED_SLOT_ID')
        slot=slots[0];layout.validate_slot(d,manifest,slot)
        if any(slot[k]!=batch[k] or source[k]!=batch[k] for k in ['operation','manager_code','manager_name']):raise IntakeError('BATCH_CONTEXT_CHANGED')
        raw=d.meta(source['source_id'])
        if raw.get('parents')!=[source['source_parent_id']] or raw.get('driveId')!=bridge.SOURCE_DRIVE or raw.get('trashed'):raise IntakeError('SOURCE_MOVED_BEFORE_CLAIM')
        if any(str(raw.get(k))!=str(source[v]) for k,v in [('name','name'),('mimeType','mime_type'),('size','size'),('md5Checksum','md5'),('createdTime','created_at')]):raise IntakeError('SOURCE_CONTENT_CHANGED_BEFORE_CLAIM')
        if str(raw.get('version'))!=source['version']:
            if not source.get('sha256') or raw.get('sha256Checksum')!=source['sha256'] or not re.fullmatch(r'[0-9]+',str(raw.get('version',''))) or not re.fullmatch(r'[0-9]+',source['version']) or int(raw['version'])<int(source['version']):raise IntakeError('SOURCE_VERSION_CHANGED_WITHOUT_CONTENT_PROOF')
        parent=source['source_parent_id']
        for _ in range(12):
            if parent==source['slot_id']:break
            folder=d.meta(parent)
            if folder.get('driveId')!=bridge.SOURCE_DRIVE or folder.get('trashed') or folder.get('mimeType')!=bridge.FOLDER or len(folder.get('parents',[]))!=1:raise IntakeError('SOURCE_CONTAINER_SCOPE')
            parent=folder['parents'][0]
        else:raise IntakeError('SOURCE_NO_LONGER_IN_REGISTERED_SLOT')
    return True

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

def assert_source_writer(source_id,batch_id=None):
    state=bridge.read_json(STATE,{'claims':{}})
    for bid,entry in state.get('claims',{}).items():
        if entry.get('status')!='complete' and any(s['source_id']==source_id for s in entry['batch']['sources']) and bid!=batch_id:raise IntakeError('SOURCE_ALREADY_OWNED_BY_AUTONOMOUS_INTAKE')
    return True

def complete(state,bid,owner,proofs):
    entry=state.get('claims',{}).get(bid)
    if not entry or entry['owner']!=owner:raise IntakeError('CLAIM_OWNER')
    expected={d['source_id'] for d in entry['batch']['sources']}
    if len(proofs)!=len(expected) or {p.get('source_id') for p in proofs}!=expected:raise IntakeError('INCOMPLETE_BATCH_PROOF')
    for p in proofs:
        if not all(p.get(k) is True for k in ['source_parent_verified','clean_verified','inventory_verified','reservation_preserved']) or not all(re.fullmatch(r'[a-f0-9]{64}',p.get(k,'')) for k in ['raw_sha256','clean_sha256']):raise IntakeError('MISSING_VERIFICATION')
    entry.update(status='complete',proofs=proofs,completed_at=bridge.now_iso());state.setdefault('completed',{}).update({pid:bid for pid in expected});return entry

def batch_archive_ready(entry,index):
    ids=entry.get('archive_source_ids')
    return isinstance(ids,list) and all(index.get('mappings',{}).get(sid,{}).get('verified') is True and bool(index['mappings'][sid].get('stockShortcutId')) for sid in ids)

def health(now=None):
    cfg=bridge.read_json(CONFIG,{})
    if cfg.get('live_treatment_enabled') is not True:return {'status':'disabled'}
    tick=bridge.read_json(DATA/'intake-monitor-last-tick.json',{})
    try:age=(bridge.timestamp(now or bridge.now_iso())-bridge.timestamp(tick['at'])).total_seconds()
    except (KeyError,bridge.ArchiveError):return {'status':'blocked','reason':'INTAKE_MONITOR_MISSING'}
    if tick.get('owner_job_id')!=cfg['owner_job_id'] or not -60<=age<=2700:return {'status':'blocked','reason':'INTAKE_MONITOR_STALE_OR_WRONG_OWNER'}
    error=bridge.read_json(DATA/'intake-last-error.json',{})
    if error.get('status')=='blocked':return {'status':'blocked','reason':'INTAKE_EXECUTION_ERROR','diagnostic':'intake-last-error.json'}
    if tick.get('result',{}).get('status')=='blocked':return {'status':'blocked','reason':'INTAKE_MONITOR_BLOCKED'}
    return {'status':'ok'}

def finish_with_archive(state,batch,owner):
    entry=state['claims'][batch['batch_id']]
    if entry['owner']!=owner:raise IntakeError('CLAIM_OWNER')
    if entry.get('status')!='treated_waiting_archive':
        proofs=verify_completed(bridge.Drive(),batch,entry['inventory_before'])
        rows=[json.loads(l) for l in (bridge.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if l.strip()]
        sources={p['source_id'] for p in proofs};new=[r for r in rows if r.get('source_drive_id') in sources and r['asset_id'] not in entry['inventory_before']]
        entry.update(status='treated_waiting_archive',proofs=proofs,archive_source_ids=[r[k] for r in new for k in ['source_drive_id','asset_drive_id']],treated_at=bridge.now_iso())
        bridge.atomic_json(STATE,state) # Persist complete treatment before publishing transport.
    import ares_archive_automation as transport
    cycle=transport.run_cycle(apply=True)
    if cycle['reconciliation']['blocked'] or cycle['production']['blocked']:raise IntakeError('ARCHIVE_TRANSPORT_BLOCKED')
    index=bridge.read_json(DATA/'archive-index.json',{'mappings':{}})
    if not batch_archive_ready(entry,index):return {'status':'waiting_archive','batch_id':batch['batch_id'],'treated_verified':True,'source_count':len(batch['sources'])}
    return complete(state,batch['batch_id'],owner,entry['proofs'])

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
            params={'q':query,'corpora':'drive','driveId':bridge.SOURCE_DRIVE,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':1000,'fields':'nextPageToken,files(id,name,mimeType,parents,size,md5Checksum,sha256Checksum,version,createdTime,trashed)'}
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
    test=bridge.read_json(DATA/'intake-selftest-1562188030205362227.json',{})
    if test.get('status')=='pending':return {'status':'selftest','manifest':str(DATA/'intake-selftest-1562188030205362227.json'),'run_id':'1562188030205362227'}
    if cfg.get('live_treatment_enabled') is not True:return {'status':'live_treatment_disabled','pending':0}
    manifest=bridge.read_json(DATA/'upload-context-layout.json');assert isinstance(manifest,dict)
    d=bridge.Drive();scope=bridge.config_load();layout.check_folder(d,manifest,manifest['upload_root_id'],bridge.SOURCE_ROOT,'UPLOAD MANUAL')
    with locked_state() as state:
        # Resume the same durable batch; never allocate a replacement on timeout.
        active=[x for x in state['claims'].values() if x['status']!='complete']
        if active:
            entry=sorted(active,key=lambda x:x['claimed_at'])[0];status='resume'
            if entry.get('status')=='treated_waiting_archive':
                ready=batch_archive_ready(entry,bridge.read_json(DATA/'archive-index.json',{'mappings':{}}));status='archive_ready' if ready else 'waiting_archive'
                if not ready and (bridge.timestamp(bridge.now_iso())-bridge.timestamp(entry['treated_at'])).total_seconds()>2700:status='blocked'
            return {'status':status,'batch_id':entry['batch']['batch_id'],'manifest':str(DATA/'intake-batches'/('batch-'+entry['batch']['batch_id']+'.json'))}
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
        expected_clean=[op,kind,'01_READY']
        if row['asset_id'] in baseline:
            parts=row.get('asset_path','').split('/')
            if parts[:2]!=['MGS-AGENTS','CRIATIVOS'] or parts[-1]!=row['canonical_filename']:raise IntakeError('EXISTING_DESTINATION_PATH')
            expected_clean=parts[2:-1]
        if raw.get('name')!=source['name'] or d.relative_parent(raw['parents'][0],bridge.SOURCE_ROOT)!=[op,kind,'99_LEGACY'] or d.relative_parent(clean['parents'][0],bridge.SOURCE_ROOT)!=expected_clean:raise IntakeError('FINAL_PARENT_SCOPE')
        if raw.get('driveId')!=bridge.SOURCE_DRIVE or clean.get('driveId')!=bridge.SOURCE_DRIVE or raw.get('trashed') or clean.get('trashed') or clean.get('name')!=row.get('canonical_filename'):raise IntakeError('FINAL_IDENTITY')
        hashes=d.hashes(source['source_id']);ch=d.hashes(clean['id'])
        allowed_raw={row['original_checksum'],row['clean_checksum']} if row['asset_id'] in baseline else {row['original_checksum']}
        if hashes['md5']!=source['md5'] or hashes['size']!=source['size'] or hashes['sha256'] not in allowed_raw or ch['sha256']!=row['clean_checksum'] or ch['md5']!=clean['md5Checksum'] or ch['size']!=clean['size']:raise IntakeError('FINAL_BINARY_PROOF')
        proofs.append({'source_id':source['source_id'],'clean_source_id':clean['id'],'raw_sha256':hashes['sha256'],'clean_sha256':ch['sha256'],'source_parent_verified':True,'clean_verified':True,'inventory_verified':True,'reservation_preserved':True})
    return proofs

def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['monitor','claim','complete','selftest-complete']);ap.add_argument('--batch-id');ap.add_argument('--owner');ap.add_argument('--clean-id');args=ap.parse_args()
    try:
        if args.action=='monitor':result=monitor()
        elif args.action=='selftest-complete':
            cfg=bridge.read_json(CONFIG,{})
            if cfg.get('enabled') is not True or args.owner!=cfg.get('owner_job_id') or not re.fullmatch(r'[A-Za-z0-9_-]{8,}',args.clean_id or ''):raise IntakeError('SELFTEST_NATIVE_OWNER')
            from ares_intake_selftest import finish
            result=finish(bridge.Drive(True),args.clean_id)
        else:
            cfg=bridge.read_json(CONFIG,{})
            if cfg.get('enabled') is not True or args.owner!=cfg.get('owner_job_id'):raise IntakeError('ACTIVE_NATIVE_OWNER_REQUIRED')
            if not re.fullmatch('[a-f0-9]{32}',args.batch_id or ''):raise IntakeError('BATCH_ID')
            batch=bridge.read_json(DATA/'intake-batches'/('batch-'+args.batch_id+'.json'));assert batch and batch['batch_id']==args.batch_id
            with locked_state() as state:
                if args.action=='claim':
                    if args.batch_id not in state['claims']:validate_new_batch(bridge.Drive(),batch,bridge.read_json(DATA/'upload-context-layout.json'))
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
                    result=finish_with_archive(state,batch,args.owner)
        if isinstance(result,dict) and 'inventory_before' in result:result={k:v for k,v in result.items() if k!='inventory_before'}
        if args.action in ['complete','selftest-complete']:
            previous=bridge.read_json(DATA/'intake-last-error.json',{})
            if previous.get('status')=='blocked':bridge.atomic_json(DATA/'intake-last-error.json',{'status':'recovered','at':bridge.now_iso(),'previous_error':previous,'recovered_action':args.action,'batch_id':args.batch_id})
        print(json.dumps(result,ensure_ascii=False));return 0
    except Exception as exc:
        error={'status':'blocked','reason':str(exc)[:220],'at':bridge.now_iso(),'scope':'intake_only','delete_source':False};bridge.atomic_json(DATA/'intake-last-error.json',error);print(json.dumps({k:v for k,v in error.items() if k!='at'}));return 2
if __name__=='__main__':raise SystemExit(main())
