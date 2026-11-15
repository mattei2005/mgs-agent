"""Read-only remote reconciliation; no CampaignEngine and no reservation/quota mutation."""
import copy,fcntl,hashlib,importlib.util,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_9700e988';sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
from ares_campaign_v3 import target_continuation as tc
from ares_campaign_v3.shein_channel_authority import _get
cfg=rev.load(R/'data/ares/meta-ads/engine-v3/config.json')
h=R/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937';q=rev.load(h/'request.json');rid=q['request_id'];aid=q['account_id']
original='7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba';ok='1571376388437577861'
with (h/'target-clone.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    context=rev.validate_local(h/'request.json',cfg,original,ok);assert context['last'] and not context['pending']
    spec=importlib.util.spec_from_file_location('maintenance_readonly_runtime',R/'scripts/ares-eggbev-target-clone.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    _,meta,_,token=runner.runtime()
    messages=[]
    def get(path):
        value=_get(path);messages.append(value);return value
    rev.live_authority(context,meta=meta,token=token,get_message=get)
    cp_path=Path(cfg['state_root'])/'checkpoints'/f'{rid}-{aid}.json';checkpoint=rev.load(cp_path);record=checkpoint['bundles'][0]
    manifest=rev.load(h/'manifest.json');c=manifest['campaigns'][0]
    confirmed=record['confirmed_objects'];cid=confirmed['campaign_create_1']['id'];sid=confirmed['adset_create_1']['id'];creative=confirmed['creative_create_1_1']['id']
    rows={}
    queries=[('campaign',cid,'id,account_id,name,status,effective_status,daily_budget'),('adset',sid,'id,account_id,campaign_id,name,status,start_time,promoted_object'),('creative',creative,'id,name,object_story_spec,asset_feed_spec,url_tags'),('ads',cid+'/ads','id,account_id,campaign_id,adset_id,name,status,creative{id}'),('adsets',cid+'/adsets','id,campaign_id,start_time,status'),('source',q['source_campaign_id_candidate'],'id,account_id,name,status')]
    for label,node,fields in queries:
        code,body,headers=meta.graph_get(node,token,{'fields':fields,'limit':100} if label in {'ads','adsets'} else {'fields':fields})
        assert code==200,(label,code,body.get('error'));rows[label]={'code':code,'body':body}
    campaign=rows['campaign']['body'];adset=rows['adset']['body'];creative_body=rows['creative']['body'];source=rows['source']['body'];source_old=rev.load(h/'source-live.json')['campaign']
    assert campaign['id']==cid and campaign['account_id']==aid and campaign['status']=='PAUSED' and campaign['daily_budget']==c['campaign_create']['daily_budget'] and campaign['name']==c['name']
    assert adset['id']==sid and adset['campaign_id']==cid and adset['status']=='ACTIVE' and datetime.fromisoformat(adset['start_time'])==datetime.fromisoformat(c['start_time']) and adset['promoted_object']['page_id']=='1355561690982225'
    assert creative_body['id']==creative and creative_body['object_story_spec']['page_id']=='1355561690982225' and creative_body['url_tags']==c['ads'][0]['creative_payload']['url_tags']
    assert not rows['ads']['body']['data'] and not rows['ads']['body'].get('paging',{}).get('next')
    assert [x['id'] for x in rows['adsets']['body']['data']]==[sid] and not rows['adsets']['body'].get('paging',{}).get('next')
    assert all(source[k]==source_old[k] for k in ['id','name','account_id','status'])
    for name in ['creative_create_1_2','creative_create_1_3']:
        from ares_campaign_v3.target_page_clone import _uncertain
        assert not _uncertain(record,name) and name not in confirmed
    lane=rev.load(Path(record['quota']['path']));now=time.time();events=[x for x in lane['events'] if float(x['at'])>now-lane['window_seconds']]
    quota={'observed_at':now,'tier':lane['ads_api_access_tier'],'window_seconds':lane['window_seconds'],'active_events':events,'current_points_computed':sum(x['points'] for x in events),'effective_limit':lane['hard_score'],'retry_after_original':checkpoint['deferred']['retry_after_seconds'],'mutation':False,'note':'Read-only local calculation; central execution must reserve again and honor current provider/quota gates.'}
    proof={'at':datetime.now(timezone.utc).isoformat(),'request_id':rid,'ids':{'campaign':cid,'adset':sid,'creative1':creative},'authority_messages':messages,'live':rows,'quota':quota,'meta_writes':0,'engine_calls':0}
    rev.atomic_json(M/'live-readback.json',proof)
    grant=context['grant'];tx=context['last'][1]
    receipt={'schema_version':2,'kind':'committed_asap_partial','request_id':rid,'account_id':aid,'request_path':str(h/'request.json'),'request_sha256':rev.file_digest(h/'request.json'),'manifest_digest':tc.digest(manifest),'account_identity':grant['account_identity'],'authorized_by':grant['authorized_by'],'approval_message_id':ok,'instruction_message_id':grant['instruction_message_id'],'original_approved_digest':original,'start_grant_binding':cfg['accounts'][aid]['target_page_replacement']['start_revisions'][rid],'temporal_revision_digest':rev.digest(tx),'revision_index':tx['index'],'start_time':tx['start_time'],'meta_actor_id':grant['meta_actor_id'],'messages':grant['messages'],'journal_prefix_count':len(record['write_journal']),'journal_prefix_digest':tc.digest(record['write_journal']),'confirmed_objects':copy.deepcopy(confirmed),'files':{name:rev.file_digest(h/name) for name in ['request.json','manifest.json','plan.json','summary.json','final-approval.json','selected-assets.json','source-live.json','target-page-live.json','prestage.json','media-visual-qa.json']},'maintenance_task':'t_9700e988','execution_owner_task':'t_bdfc754f','live_evidence_sha256':rev.file_digest(M/'live-readback.json')}
    rev.atomic_json(M/'continuation-candidate.json',receipt)
print(json.dumps({'live_verified':True,'campaign_paused':cid,'adset_same_start':sid,'creative1':creative,'ads':0,'quota':quota,'candidate_sha256':rev.file_digest(M/'continuation-candidate.json'),'no_engine_or_writes':True},ensure_ascii=False))
