
def assignments_for(ps,snapshot,selected,ids):
    byid={a['id']:a for a in snapshot['ads']};out=[]
    for i,asset in enumerate(selected,1):
        final=byid[ids[f'copied_ad_id_1_{i}']];pairs=[p for p in ps if p['slot']==i];vertical=next(p for p in pairs if p['variant']=='vertical')
        out.append({'asset_id':asset['asset_id'],'campaign_id':ids['campaign_id_1'],'adset_id':ids['adset_id_1'],'ad_id':final['id'],'creative_id':final['creative']['id'],'video_id':vertical['observed_video_id'],'effective_object_story_id':final['creative'].get('effective_object_story_id'),'media_lineage':[{k:p[k] for k in ['labels','expected_video_id','observed_video_id','variant']} for p in pairs]})
    return out

def write_assignments(runner,home,q,assignments):
    p=runner.INVENTORY
    with p.with_suffix(p.suffix+'.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);raw=p.read_bytes();rows=[json.loads(s) for s in raw.decode().splitlines() if s.strip()]
        for a in assignments:
            hits=[r for r in rows if r.get('asset_id')==a['asset_id']];require(len(hits)==1,'unique inventory asset');row=hits[0]
            require(row.get('reservation_request_id')==q['request_id'],'inventory reservation')
            fields={'used_by':a['campaign_id'],'ad_account_id':q['account_id'],'meta_adset_id':a['adset_id'],'meta_ad_id':a['ad_id'],'meta_creative_id':a['creative_id'],'meta_video_id':a['video_id'],'effective_object_story_id':a['effective_object_story_id'],'meta_video_lineage':a['media_lineage'],'campaign_owner':q['requested_by'],'status':'02_TESTING','reservation_status':'EM_USO','ares_eligible':False,'strategy':'BOT_MESSENGER'}
            if row.get('used_by') not in {None,'','ARES_IN_FLIGHT'}:
                require(all(row.get(k)==v for k,v in fields.items()),'existing final assignment differs')
            row.update(fields)
        b=home/'inventory-before-finalize.jsonl'
        if not b.exists():revision.atomic_bytes(b,raw)
        require(p.read_bytes()==raw,'inventory CAS');revision.atomic_bytes(p,(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)).encode())

def repair_partial_stock(standard,asset,assignment,q):
    """Only complete a controller intent whose same stock ID already moved.

    No retry of PATCH. Reuse mark_used's readback branch with the ORIGINAL
    source folder, under the same controller queue->inventory locks.
    """
    import ares_archive_storage as storage
    p=standard.b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
    key=sha(standard.b.canonical([q['request_id'],asset['asset_drive_id']]))
    receipt=standard.HOME/('use-'+key+'.json')
    if not receipt.exists():return
    old=load(receipt)
    with standard.b.queue_lock():
        with p.with_suffix(p.suffix+'.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);rows=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
            hits=[r for r in rows if r.get('asset_id')==asset['asset_id']];require(len(hits)==1,'stock asset ambiguity');row=hits[0]
            if row.get('manager_storage_state')=='used':return
            d=standard.b.Drive(True);record=storage.resolve_media(asset['asset_drive_id'],d.token);require(record is not None,'stock lineage missing')
            slot,state=standard.find_slot(asset['manager_media_folder_id'])
            if record['parents']==[asset['manager_media_folder_id']]:return
            require(record['parents']==[slot['used_id']] and record['stock_file_id']==old.get('stock_file_id') and record['sha256Checksum']==asset['clean_checksum'] and old.get('assignment')=={k:assignment[k] for k in ['campaign_id','adset_id','ad_id','creative_id']} and old.get('request_id')==q['request_id'],'partial stock move differs from intent')
            result=standard.mark_used(d,row,{'asset_drive_id':asset['asset_drive_id'],'ready_parent_id':asset['manager_media_folder_id'],'drive_md5':record['md5Checksum']},old['assignment'],q['request_id'])
            standard.apply_use_result(row,result);revision.atomic_bytes(p,(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)).encode())

def stock_receipt(standard,asset,a,q,result):
    require(result.get('status')=='verified' and result.get('asset_id')==asset['asset_id'] and result.get('same_ids') is True,'stock controller readback incomplete')
    key=sha(standard.b.canonical([q['request_id'],asset['asset_drive_id']]))
    p=standard.HOME/('use-'+key+'.json');v=load(p)
    require(v.get('schema')=='mgs.manager.standard.use.v1' and v.get('status')=='verified' and v.get('request_id')==q['request_id'] and v.get('asset_id')==asset['asset_id'] and v.get('logical_id')==asset['asset_drive_id'] and v.get('sha256')==asset['clean_checksum'] and v.get('stock_file_id') and v.get('folder_id')==result.get('destination') and v.get('assignment')=={k:a[k] for k in ['campaign_id','adset_id','ad_id','creative_id']},'same-stock receipt binding')
    return {'path':str(p),'sha256':file_sha(p),'stock_file_id':v['stock_file_id'],'asset_id':asset['asset_id'],'destination':v['folder_id']}

def finalize(path,runner,approved_digest,approval_message_id,*,runtime_factory=Runtime):
    from .coordination import AccountWriterLeaseStore
    import ares_manager_storage_standard as standard
    with request_lock(path):
        g,cfg,q,payload=local(path,runner,approved_digest,approval_message_id);home=Path(path).parent/'media-recovery'
        require((home/'verified.json').exists(),'independent recovery required; never replay Engine')
        link=load(home/'verified.json');receipt=validate_receipt(link,g,payload,path,allow_stale=True);fresh(receipt['fresh_at'],limit=MAX_ATTESTATION_AGE)
        leases=AccountWriterLeaseStore(cfg['state_root']);leases.claim(q['account_id'],q['request_id'],status='POSTPROCESS_PENDING')
        runtime=runtime_factory(runner,path,cfg,q,payload);runtime.g=g;runtime.authority();runtime.source_page()
        with continuation.admission(path,payload,cfg,meta=runtime.meta,token=runtime.token):
            selected=load(Path(path).parent/'selected-assets.json');snapshot=runtime.read();ps=semantic(payload,g['ids'],selected,snapshot,g['pairs'],'ACTIVE');rendered(g,g['ids'],ps)
            require(ps==receipt['pairs'],'receipt/live media lineage drift')
            assignments=assignments_for(ps,snapshot,selected,g['ids']);write_assignments(runner,home,q,assignments)
            movements=[]
            for asset,a in zip(selected,assignments):
                repair_partial_stock(standard,asset,a,q)
                result=standard.confirm_usage(asset['asset_id'],q['request_id'],apply=True)
                movements.append(stock_receipt(standard,asset,a,q,result))
            # Reconfirm all three stock IDs (including earlier partial successes)
            # and the hierarchy before committing the allocation.
            for asset,a in zip(selected,assignments):
                result=standard.confirm_usage(asset['asset_id'],q['request_id'],apply=True)
                stock_receipt(standard,asset,a,q,result)
            runtime.authority();runtime.source_page();semantic(payload,g['ids'],selected,runtime.read(),g['pairs'],'ACTIVE')
            ledger_path=runner.R/runner.naming.load_policy()['ledger_path']
            with ledger_path.with_suffix(ledger_path.suffix+'.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX);raw=ledger_path.read_bytes();ledger=json.loads(raw);allocation=ledger['allocations'][q['request_id']]
                require(allocation.get('account_id')==q['account_id'] and allocation.get('names')==[payload['campaigns'][0]['name']] and allocation.get('status') in {'RESERVED','IN_FLIGHT','COMMITTED'},'ledger owner/state')
                if allocation.get('status')=='COMMITTED':require(allocation.get('campaign_ids')==[g['ids']['campaign_id_1']],'committed ledger IDs')
                else:
                    b=home/'ledger-before-finalize.json'
                    if not b.exists():revision.atomic_bytes(b,raw)
                    allocation.update(status='COMMITTED',campaign_ids=[g['ids']['campaign_id_1']],completed_at=utc())
                    require(ledger_path.read_bytes()==raw,'ledger CAS');atomic(ledger_path,ledger)
            final={'phase':'COMPLETE','request_id':q['request_id'],'campaign_name':payload['campaigns'][0]['name'],'campaign_ids':[g['ids']['campaign_id_1']],'assignments':assignments,'manager_stock_readbacks':movements,'recovery_receipt':link,'original_engine_status':load(Path(path).parent/'engine-result.json')['status'],'independent_recovery':True,'source_unchanged':True,'configured_status':'ACTIVE','scheduled_start':payload['campaigns'][0]['start_time'],'daily_budget_minor':payload['campaigns'][0]['campaign_create']['daily_budget'],'final_ads':3,'technical_paused_seeds':3,'serving_verified':False}
            fp=Path(path).parent/'final.json';missing(fp,final)
            fl={'path':str(fp),'sha256':file_sha(fp),'phase':'COMPLETE_INDEPENDENT'}
            for p in [g['checkpoint_path'],g['audit_path'],str(Path(path).parent/'engine-result.json')]:cas_link(p,'independent_media_finalization',fl,home/'original'/Path(p).name)
            leases.release(q['account_id'],q['request_id']);return final
