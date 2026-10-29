#!/usr/bin/env python3
"""Reconcile a verified explicit manual delivery into the existing intake state.

No media creation, deletion, permission, policy, scheduler or campaign writes.
--apply writes only the canonical intake completion and its local receipt.
"""
from __future__ import annotations
import argparse,copy,fcntl,hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import ares_autonomous_intake as intake
import ares_upload_context_layout as layout

EXECUTIONS=b.BASE/'data/ares/creative-ops/executions'
class CompletionError(RuntimeError):pass

def require(ok,reason):
    if not ok:raise CompletionError(reason)

def resolve_execution(value):
    p=Path(value).resolve()
    require(p.parent==EXECUTIONS.resolve() and re.fullmatch(r'intake-[0-9]{17,20}',p.name),'MANUAL_EXECUTION_SCOPE')
    return p

def make_manual_batch(plan,sources,execution,audit,requester):
    require(plan.get('schema')=='mgs.manual.intake.plan.v1','MANUAL_PLAN_SCHEMA')
    require(re.fullmatch(r'[0-9]{17,20}',str(plan.get('thread_id',''))) is not None and re.fullmatch(r'[0-9]{17,20}',requester) is not None,'MANUAL_REQUEST_IDENTITY')
    require(execution.get('phase')=='complete' and audit.get('status')=='complete','MANUAL_DELIVERY_NOT_COMPLETE')
    items=plan.get('items',[]);ids={r.get('id') for r in items}
    require(0<len(items)<=100 and len(ids)==len(items)==plan.get('expected_count')==audit.get('received_sources'),'MANUAL_EXACT_SOURCE_SET')
    require(len(sources)==len(items) and {r.get('id') for r in sources}==ids,'MANUAL_FROZEN_SOURCE_SET')
    require(audit.get('pending_scoped')==0 and audit.get('all_metadata_clean') is True and audit.get('all_reservations_preserved') is True,'MANUAL_AUDIT_INCOMPLETE')
    audit_proofs=audit.get('proofs',[])
    require(len(audit_proofs)==len(items) and {p.get('source_id') for p in audit_proofs}==ids,'MANUAL_AUDIT_SOURCE_SET')
    op=plan.get('operation');manager=plan.get('manager');codes=[k for k,v in layout.MANAGERS.items() if v==manager]
    require(layout.OPERATION.fullmatch(str(op)) is not None and len(codes)==1,'MANUAL_CONTEXT')
    descriptors=[];clean_ids=set()
    for r in items:
        raw=next(x for x in sources if x['id']==r['id']);entry=execution.get('items',{}).get(r['id'],{})
        require(all(raw.get(k)==r.get(k) for k in ['id','name','raw_sha256','md5Checksum','size','mimeType','createdTime','parents']),'MANUAL_SOURCE_SNAPSHOT_CHANGED')
        require(all(entry.get(k) is True for k in ['destination_verified','inventory_verified','legacy_verified']),'MANUAL_TREATMENT_PROOF_MISSING')
        clean=entry.get('dest_id');require(re.fullmatch(r'[A-Za-z0-9_-]{8,}',str(clean)) is not None and clean not in ids and clean not in clean_ids,'MANUAL_CLEAN_IDENTITY');clean_ids.add(clean)
        require(next(p for p in audit_proofs if p['source_id']==r['id']).get('dest_id')==clean,'MANUAL_AUDIT_CLEAN_IDENTITY')
        require(re.fullmatch(r'[a-f0-9]{64}',str(r.get('raw_sha256',''))) is not None and re.fullmatch(r'[a-f0-9]{64}',str(r.get('clean_sha256',''))) is not None,'MANUAL_HASH_FORMAT')
        descriptors.append({'source_id':r['id'],'clean_source_id':clean,'name':r['name'],'mime_type':r['mimeType'],'size':str(r['size']),'md5':r['md5Checksum'],'sha256':r['raw_sha256'],'created_at':r['createdTime'],'source_parent_id':plan['source_parent'],'operation':op,'manager_code':codes[0],'manager_name':manager})
    batch={'schema':'mgs.intake.batch.v1','scope_type':'explicit_manual_request','operation':op,'manager_code':codes[0],'manager_name':manager,'thread_id':plan['thread_id'],'request_message_id':plan['thread_id'],'requested_by_discord_id':requester,'sources':sorted(descriptors,key=lambda r:r['source_id'])}
    batch['batch_id']=hashlib.sha256(b.canonical(batch)).hexdigest()[:32]
    return batch

def record_completion(state,batch,proofs,evidence_sha,evidence_path):
    """Pure transactional transition, using the unchanged canonical completion gate."""
    candidate=copy.deepcopy(state);bid=batch['batch_id'];expected={s['source_id'] for s in batch['sources']}
    require(len(proofs)==len(expected) and {p.get('source_id') for p in proofs}==expected,'MANUAL_PROOF_MEMBERSHIP')
    for source in batch['sources']:
        proof=next(p for p in proofs if p['source_id']==source['source_id'])
        require(proof.get('clean_source_id')==source['clean_source_id'] and proof.get('raw_sha256')==source['sha256'],'MANUAL_PROOF_BINDING')
    old=candidate.get('claims',{}).get(bid)
    if old is not None:
        require(old.get('status')=='complete' and old.get('batch')==batch and old.get('completion_evidence_sha256')==evidence_sha and old.get('proofs')==proofs,'MANUAL_COMPLETION_REPLAY_CHANGED')
        require(all(candidate.get('completed',{}).get(sid)==bid for sid in expected),'MANUAL_COMPLETION_INDEX_CHANGED')
        return old
    for other in candidate.get('claims',{}).values():
        require(not expected.intersection({s['source_id'] for s in other.get('batch',{}).get('sources',[])}),'MANUAL_SOURCE_ALREADY_CLAIMED')
    require(not expected.intersection(candidate.get('completed',{})),'MANUAL_SOURCE_ALREADY_COMPLETED')
    owner='manual-request:'+batch['request_message_id'];entry=intake.claim(candidate,batch,owner)
    entry.update(archive_source_ids=[fid for s in batch['sources'] for fid in [s['source_id'],s['clean_source_id']]],completion_evidence=evidence_path,completion_evidence_sha256=evidence_sha,completion_mode='verified_manual_reconciliation')
    intake.complete(candidate,bid,owner,proofs)
    state.clear();state.update(candidate)
    return state['claims'][bid]

def verify_delivery(d,plan,batch,index,rows):
    """Native original/treated/archive bytes, ACK, stock, ACL and reservation checks."""
    import ares_archive_storage as storage
    import ares_archive_retirement as retirement
    source_ids={s['source_id'] for s in batch['sources']}
    selected=[r for r in rows if r.get('source_drive_id') in source_ids]
    require(len(selected)==len(source_ids),'MANUAL_UNIQUE_INVENTORY')
    proofs=intake.verify_completed(d,batch,{})
    for source in batch['sources']:
        row=next(r for r in selected if r['source_drive_id']==source['source_id']);item=next(r for r in plan['items'] if r['id']==source['source_id'])
        require(row.get('thread_id')==batch['thread_id'] and row.get('requested_by_discord_id')==batch['requested_by_discord_id'] and row.get('canonical_filename')==item['final_name'] and row.get('asset_drive_id')==source['clean_source_id'] and row.get('clean_checksum')==item['clean_sha256'],'MANUAL_INVENTORY_BINDING')
        proof=next(p for p in proofs if p['source_id']==source['source_id']);require(proof['clean_sha256']==item['clean_sha256'],'MANUAL_CLEAN_HASH_CHANGED')
        original=index['mappings'][source['source_id']];clean=index['mappings'][source['clean_source_id']]
        require(original['jobId']==clean['jobId'],'MANUAL_PAIR_JOB_CHANGED')
        job=b.read_json(b.DATA/'jobs'/('job-'+original['jobId']+'.json')) or {}
        require(job.get('lineageId')==row['asset_id'] and {a['sourceId'] for a in job['assets']}=={source['source_id'],source['clean_source_id']} and len(job['assets'])==2,'MANUAL_JOB_MEMBERSHIP')
        ack_file=d.one(b.config_load()['requests_folder_id'],'ack:'+job['jobId'])
        if not ack_file:raise CompletionError('MANUAL_ACK_MISSING')
        b.require_publisher(d.meta(ack_file['id']),b.CANONICAL_SA);ack=json.loads(d.raw(ack_file['id']))
        require(ack.get('schema')=='mgs.archive.ack.v1' and ack.get('kind')=='lineage' and ack.get('jobId')==job['jobId'] and ack.get('status')=='verified' and ack.get('validationOnly') is not True and len(ack.get('assets',[]))==2,'MANUAL_NATIVE_ACK_BINDING')
        for asset in job['assets']:
            entry=index['mappings'][asset['sourceId']];storage.require_registered_mapping(entry,index)
            require(entry.get('stockTransferredToArchive') is True,'MANUAL_STOCK_PENDING')
            require(len([a for a in ack['assets'] if a.get('sourceId')==asset['sourceId'] and a.get('archiveId')==entry['archiveId'] and a.get('sha256')==asset['sha256']])==1,'MANUAL_ACK_MEMBERSHIP')
            retirement.check_copy(d,asset,entry)
        with tempfile.TemporaryDirectory(prefix='manual-intake-metadata-') as tmp:
            path=Path(tmp)/('clean'+Path(item['final_name']).suffix);path.write_bytes(d.raw(source['clean_source_id']))
            result=subprocess.run([str(b.BASE/'scripts/clean-creative-metadata.sh'),'verify',str(path),'--json'],capture_output=True,text=True,timeout=60)
            require(result.returncode==0 and json.loads(result.stdout).get('clean') is True,'MANUAL_CLEAN_METADATA')
    return proofs

def run(execution_dir,requester,apply=False):
    root=resolve_execution(execution_dir)
    def perform(state):
        plan=b.read_json(root/'plan.json');sources=b.read_json(root/'sources.json');execution=b.read_json(root/'state.json');audit=b.read_json(root/'final-audit.json')
        batch=make_manual_batch(plan,sources,execution,audit,requester)
        require(root.name=='intake-'+batch['thread_id'],'MANUAL_EXECUTION_REQUEST_MISMATCH')
        evidence_sha=hashlib.sha256(b.canonical({'plan':plan,'sources':sources,'audit':audit,'clean_ids':{s['source_id']:s['clean_source_id'] for s in batch['sources']}})).hexdigest()
        old=state.get('claims',{}).get(batch['batch_id'])
        if old:
            record_completion(state,batch,old['proofs'],evidence_sha,str((root/'final-audit.json').relative_to(b.BASE)))
            return {'status':'already_complete','batch_id':batch['batch_id'],'sources':len(batch['sources']),'state_changed':False,'remote_writes':0,'media_deletes':0}
        with b.queue_lock():
            lockpath=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl.lock'
            with lockpath.open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                rows=[json.loads(x) for x in lockpath.with_suffix('').read_text().splitlines() if x.strip()]
                index=b.read_json(b.DATA/'archive-index.json') or {};proofs=verify_delivery(b.Drive(False),plan,batch,index,rows)
                # Preflight unchanged retirement gates before release; no delete here.
                candidate=copy.deepcopy(state);entry=record_completion(candidate,batch,proofs,evidence_sha,str((root/'final-audit.json').relative_to(b.BASE)))
                import ares_archive_retirement as retirement
                cfg=b.config_load()
                for source in batch['sources']:
                    job=b.read_json(b.DATA/'jobs'/('job-'+index['mappings'][source['source_id']]['jobId']+'.json')) or {}
                    retirement.candidate_ready(job,index,rows,candidate,cfg,b.now_iso(),entry['completed_at'])
                if apply:state.clear();state.update(candidate)
        return {'status':'complete' if apply else 'verified_dry_run','batch_id':batch['batch_id'],'sources':len(batch['sources']),'binary_ids':len(entry['archive_source_ids']),'state_changed':apply,'remote_writes':0,'media_deletes':0,'completion_evidence_sha256':evidence_sha,'completed_at':entry['completed_at']}
    if apply:
        with intake.locked_state() as state:result=perform(state)
        saved=b.read_json(intake.STATE);require(saved['claims'][result['batch_id']]['status']=='complete','MANUAL_COMPLETION_READBACK')
        b.atomic_json(root/'intake-completion.json',result)
        return result
    return perform(b.read_json(intake.STATE))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-dir',required=True);ap.add_argument('--requester-id',required=True);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    try:result=run(args.execution_dir,args.requester_id,args.apply)
    except (CompletionError,intake.IntakeError,b.ArchiveError,KeyError,ValueError,OSError,subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)[:220],'media_deletes':0}));return 2
    print(json.dumps(result,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
