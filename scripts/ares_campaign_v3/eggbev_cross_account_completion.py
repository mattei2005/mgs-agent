"""Cross-account clone completion; immutable seals and fresh target-only reads.

No creation, status or clock mutation. Video-ID drift is never assumed equal.
Stock movement is delegated to the existing same-ID manager controller.
"""
from __future__ import annotations
import copy,json,fcntl,hashlib,os,time
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone

def completion_proof(q,payload,checkpoint,records,selected):
    from . import eggbev_cross_account as cross
    from .prevalidation import verify_prevalidation
    from .target_page_clone import verify
    if not verify_prevalidation(payload) or payload.get('request_id')!=q['request_id']:
        raise ValueError('completion requires original sealed request')
    campaigns=payload.get('campaigns') or []
    records=copy.deepcopy(records)
    if len(campaigns)!=5 or not records or sum(len(r.get('campaign_ids') or []) for r in records)!=5 or len(selected)!=15:
        raise ValueError('exact nonempty five-campaign completion required')
    expected_assets=[f for group in q['campaigns'] for f in group['media_filenames']]
    if [a['canonical_filename'] for a in selected]!=expected_assets:raise ValueError('completion asset order changed')
    if checkpoint.get('account_id')!=cross.TARGET or checkpoint.get('status') not in {'COMPLETE','COMPLETE_FUTURE_ACTIVE'}:
        raise ValueError('target checkpoint not terminal')
    assignments=[];campaign_ids=[];seed_ids=[];actual_start_times={};offset=0
    for record in records:
        n=len(record['campaign_ids']);raw=campaigns[offset:offset+n];offset+=n
        if record.get('status')!='COMPLETE' or any(r.get('code')!=200 for r in record.get('readback_results',[])):
            raise ValueError('fresh whole-bundle readback incomplete')
        specs=[SimpleNamespace(**{**c,'ads':[SimpleNamespace(**a) for a in c['ads']]}) for c in raw]
        verify(SimpleNamespace(campaigns=specs),record)
        rows={r['name']:r['body'] for r in record['readback_results']};ids=record['target_clone_ids']
        for ci,c in enumerate(raw,1):
            cid=ids[f'campaign_id_{ci}'];campaign_ids.append(cid)
            actual_start_times[cid]=rows[f'readback_adsets_{ci}']['data'][0]['start_time']
            if cid!=record['campaign_ids'][ci-1]:raise ValueError('campaign journal order mismatch')
            ads={str(a['id']):a for a in rows[f'readback_ads_{ci}']['data']}
            if any(a.get('issues_info') or a.get('failed_delivery_checks') or a.get('effective_status') in {'WITH_ISSUES','DISAPPROVED'} for a in ads.values()):
                raise ValueError('Meta child issue prevents stock completion')
            for ai,wanted in enumerate(c['ads'],1):
                ad_id=ids[f'copied_ad_id_{ci}_{ai}'];seed_id=ids[f'seed_ad_id_{ci}_{ai}'];seed_ids.append(seed_id)
                ad=ads[ad_id];asset=selected[len(assignments)];cr=ad['creative']
                if wanted['media']['asset_id']!=asset['asset_id']:raise ValueError('assignment slot identity mismatch')
                from .media_materialization import media_id
                assignments.append({'asset_id':asset['asset_id'],'campaign_id':cid,'adset_id':ids[f'adset_id_{ci}'],'ad_id':ad_id,'source_ad_id':seed_id,'creative_id':cr['id'],'video_id':media_id(record,wanted['media']['vertical_video_id']),'effective_object_story_id':cr.get('effective_object_story_id')})
    if (len(assignments)!=15 or len(set(campaign_ids))!=5 or len(set(seed_ids))!=15
            or len({a['ad_id'] for a in assignments})!=15 or set(seed_ids)&{a['ad_id'] for a in assignments}):
        raise ValueError('duplicate or missing completion identities')
    return {'campaign_ids':campaign_ids,'assignments':assignments,'technical_seed_ids':seed_ids,'actual_start_times':actual_start_times}

def finalize(path,runner,approved_digest,approval_message_id,*,adapter=None):
    from . import eggbev_cross_account as cross
    if adapter is not None:cross=adapter
    from request_serialization import request_lock
    from .coordination import AccountWriterLeaseStore
    from .engine import CampaignEngine
    from .transport import GraphBatchTransport
    from .media_registry import MediaRegistry
    from . import eggbev_creation_naming as naming
    q=cross.request_load(path);home=cross.home_for(q);cfg=cross.load(runner.CONFIG)
    with request_lock(home,q['request_id'],blocking=False):
        leases=AccountWriterLeaseStore(cfg['state_root']);leases.claim(cross.TARGET,q['request_id'],status='POSTPROCESS_PENDING')
        common,meta,sb,token=cross.runtime(runner,cfg);cross.verify_advertiser(meta,token);cross.live_request(q,common)
        summary=cross.load(home/'summary.json');payload=cross.final_approval(q,summary,common,approval_message_id,approved_digest)
        page=cross.page_read(q,cross.load(home/'source-live.json'),meta,sb,token,path)
        if page!=cross.load(home/'target-page-live.json'):raise ValueError('completion Page identity drift')
        result=cross.load(home/'engine-result.json')
        if result.get('status')!='COMPLETE_FUTURE_ACTIVE':raise ValueError('Engine still pending; no stock write')
        cp_path=Path(cfg['state_root'])/'checkpoints'/f"{q['request_id']}-{cross.TARGET}.json"
        checkpoint=cross.load(cp_path);records=copy.deepcopy([r for r in checkpoint['bundles'] if r.get('status')=='COMPLETE'])
        if not records:raise ValueError('completed target bundles absent')
        engine=CampaignEngine(cfg,transport_factory=lambda a:None)
        transport=GraphBatchTransport(cross.TARGET,payload['graph_version'],token)
        for record in records:
            ops=cross.readback_ops(engine._readback_ops(record['campaign_ids']))
            engine.quota.reserve((cfg['accounts'][cross.TARGET]['app_key'],cross.TARGET),len(ops),request_id=q['request_id']+'-finalize-'+str(record['index'])+'-'+str(time.time_ns()))
            rows=transport.execute(ops,'cross_completion_readback')
            record['readback_results']=[{'name':r.name,'code':r.code,'body':r.body} for r in rows]
        selected=cross.load(home/'selected-assets.json');proof=completion_proof(q,payload,checkpoint,records,selected)
        runner.save(home/'completion-readback.json',{'at':datetime.now(timezone.utc).isoformat(),'request_id':q['request_id'],'digest':approved_digest,'records':records,'proof':proof})
        inventory=runner.INVENTORY
        with inventory.with_suffix(inventory.suffix+'.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);rows=[json.loads(x) for x in inventory.read_text().splitlines() if x.strip()];byid={r['asset_id']:r for r in rows}
            for a in proof['assignments']:
                row=byid[a['asset_id']]
                if row.get('reservation_request_id')!=q['request_id']:raise ValueError('completion reservation changed')
                if row.get('meta_ad_id') and str(row['meta_ad_id'])!=a['ad_id']:raise ValueError('conflicting existing assignment')
                row.update({'used_by':a['campaign_id'],'ad_account_id':cross.TARGET,'meta_adset_id':a['adset_id'],'meta_ad_id':a['ad_id'],'meta_creative_id':a['creative_id'],'meta_video_id':a['video_id'],'effective_object_story_id':a['effective_object_story_id'],'campaign_owner':q['requested_by'],'status':'02_TESTING','reservation_status':'EM_USO','ares_eligible':False,'strategy':'BOT_MESSENGER','last_reconciled_at':datetime.now(timezone.utc).isoformat()})
            backup=home/'inventory-before-finalize.jsonl'
            if not backup.exists():backup.write_bytes(inventory.read_bytes())
            temp=inventory.with_name(inventory.name+'.cross-finalize.tmp');temp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));os.replace(temp,inventory)
        import ares_manager_storage_standard as standard
        movements=[standard.confirm_usage(a['asset_id'],q['request_id'],apply=True) for a in proof['assignments']]
        if (len(movements)!=15 or any(m.get('status')!='verified' or m.get('same_ids') is not True or m.get('asset_id')!=a['asset_id'] for m,a in zip(movements,proof['assignments']))):
            raise ValueError('same-ID stock receipt incomplete; resume finalize only')
        # Controller retries reconcile already-moved same-ID assets; this code
        # never creates a second creative lineage or replays campaign writes.
        ledger_path=cross.ROOT/naming.load_policy()['ledger_path']
        with ledger_path.with_suffix(ledger_path.suffix+'.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);ledger=cross.load(ledger_path);allocation=ledger['allocations'][q['request_id']]
            if allocation['account_id']!=cross.TARGET or allocation['names']!=summary['names']:raise ValueError('completion naming allocation changed')
            allocation.update(status='COMMITTED',campaign_ids=proof['campaign_ids'],completed_at=datetime.now(timezone.utc).isoformat());runner.save(ledger_path,ledger)
        final={'phase':'COMPLETE','request_id':q['request_id'],**proof,'final_campaigns':5,'final_ads':15,'technical_paused_seeds':15,'manager_stock_readbacks':movements,'configured_status':'ACTIVE','approved_plan_start':summary['start_time'],'daily_budget_minor':'3500','total_daily_budget_minor':'17500','source_unchanged':True,'serving_verified':False}
        runner.save(home/'final.json',final);leases.release(cross.TARGET,q['request_id']);return final
