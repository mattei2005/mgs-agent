#!/usr/bin/env python3
"""Eggbev target-Page/media/copy replacement intake; writes only via Engine v3.

Prepare is explicitly gated and may reserve/prestage but never publish. Execute
requires the sealed digest and a fresh explicit final approval after its summary.
"""
from __future__ import annotations
import argparse,copy,fcntl,hashlib,importlib.util,json,os,re,subprocess,sys
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ares_campaign_v3 import eggbev_creation_naming as naming
from ares_campaign_v3.eggbev_page_identity import resolve as resolve_page
from ares_campaign_v3.eggbev_create import _creative_payload
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prestage import AdAccountVideoUploader,PrestageService,OnDemandMediaPipeline
from ares_campaign_v3.prevalidation import prevalidate_payload,validate_account_policy,verify_prevalidation
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.cli import real_transport_factory
from ares_campaign_v3.coordination import reader_block_reason,AccountWriterLeaseStore
R=Path('/root/mgs-agent');CONFIG=R/'data/ares/meta-ads/engine-v3/config.json';INVENTORY=R/'data/ares/creative-ops/inventory/assets.jsonl'
ACCOUNT='1034081997659047';MODE='clone_target_prestaged'


class TargetAccountUploader(AdAccountVideoUploader):
    """Prove fresh account provenance before direct ready GETs, once per batch."""
    def wait_ready(self,video_ids):
        proof=super().verify_association(video_ids)
        if any(not row.get('associated') for row in proof.values()) or set(proof)!=set(video_ids):
            raise ValueError('uploaded target media association unconfirmed; no ready GET or upload replay')
        self._target_association=proof
        return super().wait_ready(video_ids)
    def verify_association(self,video_ids):
        cached=getattr(self,'_target_association',{})
        return cached if set(cached)==set(video_ids) else super().verify_association(video_ids)


def load(path):return json.loads(Path(path).read_text())
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.new');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise ValueError('canonical module unavailable')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def request_load(path):
    q=load(path)
    if q.get('account_id')!=ACCOUNT or q.get('operation')!='Eggbev-US-CC-EN-BOT' or q.get('duplicate_count')!=1:
        raise ValueError('this intake requires one exact Eggbev01 replacement request; use independent requests for batches')
    if re.fullmatch(r'[A-Za-z0-9_.-]{8,120}',q.get('request_id','')) is None:raise ValueError('safe exact request_id required')
    if not q.get('commercial_ok_message_id') or not q.get('media_filenames') or len(q['media_filenames']) not in {1,2,3,4,5} or len(set(q['media_filenames']))!=len(q['media_filenames']):raise ValueError('approved exact unique request/media missing')
    if datetime.fromisoformat(q['start_time'])<=datetime.now(timezone.utc):
        from ares_campaign_v3.target_continuation import validate_local
        validate_local(path,load(Path(path).parent/'manifest.json'),load(CONFIG))
    for value in [ACCOUNT,*naming.load_policy()['account_ids']]:
        out=subprocess.run(['python3',str(R/'scripts/mgs-ares-asset-scope.py'),'check-account',value,'--json'],capture_output=True,text=True,check=True)
        if not json.loads(out.stdout)['allowed']:raise ValueError('account scope rejected')
    subprocess.run(['python3',str(R/'scripts/mgs-domain-scope.py'),'check','--agent','ares','eggbev.com'],capture_output=True,check=True)
    return q

def runtime():
    common=module('target_clone_common',R/'scripts/ares-eggbev-roas-common.py');account=load(R/f'data/ares/meta-ads/accounts/{ACCOUNT}.json');account=(account.get('accounts')or[account])[0]
    meta,sb,token,_=common.load_runtime_modules(account)
    return common,meta,sb,token

def source_seed_proof(q):
    """Resolve only committed engine IDs, never infer seeds from names/status."""
    sid=q['source_campaign_id_candidate']
    ledger_path=R/naming.load_policy()['ledger_path']
    matches=[v for v in load(ledger_path)['allocations'].values() if sid in v.get('campaign_ids',[])]
    if not matches:return None
    if len(matches)!=1:raise ValueError('ambiguous source allocation')
    allocation=matches[0];request_id=allocation.get('request_id','')
    if re.fullmatch(r'[A-Za-z0-9_.-]{8,120}',request_id) is None:raise ValueError('unsafe source request identity')
    if allocation.get('status')!='COMMITTED' or allocation.get('account_id')!=ACCOUNT or allocation.get('campaign_ids')!=[sid] or allocation.get('names')!=[q['source_campaign_name']]:raise ValueError('source allocation identity/state mismatch')
    checkpoint_path=Path(load(CONFIG)['state_root'])/'checkpoints'/f'{request_id}-{ACCOUNT}.json'
    checkpoint=load(checkpoint_path)
    records=[b for b in checkpoint['bundles'] if sid in b.get('campaign_ids',[])]
    if len(records)!=1:raise ValueError('source checkpoint ambiguous or missing')
    record=records[0];ids=record.get('target_clone_ids')
    if not ids:return None  # Ordinary sources retain the exact cardinality gate.
    if checkpoint.get('account_id')!=ACCOUNT or checkpoint.get('status')!='COMPLETE' or record.get('status')!='COMPLETE':raise ValueError('source target clone checkpoint incomplete')
    n=len(q['media_filenames']);pairs=[[ids.get(f'copied_ad_id_1_{i}'),ids.get(f'seed_ad_id_1_{i}')] for i in range(1,n+1)]
    expected={'campaign_id_1','adset_id_1'}|{f'{key}_1_{i}' for i in range(1,n+1) for key in ['copied_ad_id','seed_ad_id','creative_id']}
    if set(ids)!=expected or any(not isinstance(v,str) or not v.isdigit() or int(v)==0 for v in ids.values()):raise ValueError('source checkpoint slots missing or extra')
    finals=[a for a,_ in pairs];seeds=[a for _,a in pairs]
    if len(set(finals+seeds))!=2*n or ids['campaign_id_1']!=sid or checkpoint.get('campaign_ids')!=[sid] or record.get('campaign_ids')!=[sid] or record.get('adset_ids')!=[ids['adset_id_1']] or len(record.get('ad_ids',[]))!=n or set(record.get('ad_ids',[]))!=set(finals):raise ValueError('source checkpoint IDs inconsistent')
    evidence={'request_id':request_id,'checkpoint_path':str(checkpoint_path),'checkpoint_sha256':hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),'adset_id':ids['adset_id_1'],'pairs':pairs}
    # Independent recovery is terminal only with its exact COMPLETE receipt.
    if checkpoint.get('recovery_result'):
        final_path=Path(checkpoint['recovery_result']).resolve()
        if not final_path.is_relative_to((R/'data/ares/meta-ads/audit/eggbev').resolve()) or final_path.name!='final.json':raise ValueError('source completion receipt outside canonical audit')
        final=load(final_path);assignments=final.get('assignments',[])
        if final.get('phase')!='COMPLETE' or final.get('request_id')!=request_id or final.get('campaign_ids')!=[sid] or final.get('final_ads')!=n or final.get('technical_paused_seeds')!=n or len(assignments)!=n or {a.get('ad_id') for a in assignments}!=set(finals) or any(a.get('campaign_id')!=sid or a.get('adset_id')!=ids['adset_id_1'] for a in assignments):raise ValueError('source completion receipt mismatch')
        manifest=load(final_path.parent/'manifest.json')
        if not verify_prevalidation(manifest) or manifest.get('request_id')!=request_id or manifest.get('operation')!='Eggbev-US-CC-EN-BOT' or len(manifest.get('campaigns',[]))!=1 or manifest['campaigns'][0].get('account_id')!=ACCOUNT or manifest['campaigns'][0].get('mode')!=MODE or len(manifest['campaigns'][0].get('ads',[]))!=n:raise ValueError('source sealed target mode proof mismatch')
        evidence.update({'completion_path':str(final_path),'completion_sha256':hashlib.sha256(final_path.read_bytes()).hexdigest()})
    return evidence


def classify_source(campaign,sets,ads,count,proof=None):
    """Keep the whole snapshot; expose only proven final slots to build()."""
    if len(sets)!=1 or not ads or any(x.get('adset_id')!=sets[0]['id'] for x in ads):raise ValueError('source hierarchy does not match requested structure')
    byid={x.get('id'):x for x in ads}
    if None in byid or len(byid)!=len(ads):raise ValueError('source ad IDs missing or duplicated')
    if proof is None:
        if len(ads)!=count:raise ValueError('source hierarchy does not match requested structure; unproven extra ads')
        selected=ads;seeds=[]
    else:
        pairs=proof['pairs'];final_ids=[a for a,_ in pairs];seed_ids=[a for _,a in pairs]
        if len(pairs)!=count or len(set(final_ids+seed_ids))!=2*count or set(byid)!=set(final_ids+seed_ids) or proof['adset_id']!=sets[0]['id']:raise ValueError('source final/seed identity or cardinality drift')
        if any(byid[seed].get('status')!='PAUSED' or byid[final].get('status')!='ACTIVE' or byid[final].get('source_ad_id')!=seed or byid[seed].get('source_ad_id') not in {None,'0'} for final,seed in pairs):raise ValueError('source final/seed status or lineage drift')
        selected=[byid[a] for a in final_ids];seeds=[byid[a] for a in seed_ids]
    return copy.deepcopy({'campaign':campaign,'adset':sets[0],'ads':selected,'all_ads':ads,'technical_seed_ads':seeds,'source_selection':{'final_count':len(selected),'seed_count':len(seeds),'total_count':len(ads),'proof':proof}})


def source_read(q,common,meta,token):
    sid=q['source_campaign_id_candidate'];code,campaign,_=meta.graph_get(sid,token,{'fields':'id,account_id,name,status,objective,buying_type,bid_strategy,special_ad_categories,special_ad_category_country'})
    if code!=200 or campaign.get('id')!=sid or campaign.get('account_id')!=ACCOUNT or campaign.get('name')!=q['source_campaign_name']:raise ValueError('source identity mismatch')
    sets=common.fetch_all_meta(meta,token,sid+'/adsets',{'fields':'id,name,status,billing_event,optimization_goal,destination_type,targeting,promoted_object,attribution_spec,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities,bid_amount,bid_constraints,optimization_sub_event','limit':100})
    ads=common.fetch_all_meta(meta,token,sid+'/ads',{'fields':'id,name,status,adset_id,source_ad_id,creative{id,object_story_spec,asset_feed_spec,url_tags,degrees_of_freedom_spec,contextual_multi_ads}','limit':100})
    return classify_source(campaign,sets,ads,len(q['media_filenames']),source_seed_proof(q))


def source_comparison(snapshot):
    """Ignore only signed delivery metadata on the same video thumbnail file."""
    from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
    value=copy.deepcopy(snapshot)
    for edge in ['ads','all_ads','technical_seed_ads']:
        for ad in value.get(edge,[]):
            videos=ad.get('creative',{}).get('asset_feed_spec',{}).get('videos',[])
            for video in videos:
                url=video.get('thumbnail_url')
                if not isinstance(url,str):continue
                parts=urlsplit(url)
                if parts.scheme!='https' or not re.fullmatch(r'scontent-[a-z0-9-]+\.xx\.fbcdn\.net',parts.netloc):continue
                query=[(k,v) for k,v in parse_qsl(parts.query,keep_blank_values=True) if not k.startswith('_nc_') and k not in {'oh','oe','ccb'}]
                video['thumbnail_url']=urlunsplit(('https','scontent.xx.fbcdn.net',parts.path,urlencode(sorted(query)),parts.fragment))
        # Graph edge order is not a commercial property; slot order in ads is.
        if edge!='ads' and edge in value:value[edge].sort(key=lambda x:x['id'])
    return value

def build(q,source,page,selected,registry,allocation):
    campaign={k:copy.deepcopy(source['campaign'][k]) for k in ['objective','buying_type','bid_strategy','special_ad_categories','special_ad_category_country']}
    minor=Decimal(q['daily_budget_usd'])*100
    if minor!=minor.to_integral_value() or minor<=0:raise ValueError('exact positive budget required')
    campaign['daily_budget']=str(int(minor))
    source_set=source['adset'];keys=['billing_event','optimization_goal','destination_type','targeting','promoted_object','attribution_spec','is_dynamic_creative','regional_regulated_categories','regional_regulation_identities','bid_amount','bid_constraints','optimization_sub_event']
    adset={k:copy.deepcopy(source_set[k]) for k in keys if k in source_set};adset['promoted_object']['page_id']=page['id']
    ads=[]
    for i,(asset,original) in enumerate(zip(selected,source['ads']),1):
        media=registry.require_ready(ACCOUNT,asset['asset_id'],asset['clean_checksum'])
        observed_ctas=original.get('creative',{}).get('asset_feed_spec',{}).get('call_to_action_types')
        if not isinstance(observed_ctas,list) or len(observed_ctas)!=1:raise ValueError('source CTA must be read exactly before rematerialization')
        cta=observed_ctas[0]
        prefix=hashlib.sha256((q['request_id']+str(i)).encode()).hexdigest()[:14]
        payload=_creative_payload(media=media,page_id=page['id'],instagram_user_id=page['instagram_user_id'],page_token=page['page_token'],label_prefix='target_'+prefix,primary_text=q['copy']['primary_text'],headlines=[q['copy']['headline']],description=q['copy']['description'],cta=cta)
        from ares_campaign_v3.creative_copy_policy import effective
        source_creative=effective(original['creative'])
        for key in ['degrees_of_freedom_spec','contextual_multi_ads']:
            if key in source_creative:payload[key]=copy.deepcopy(source_creative[key])
            else:payload.pop(key,None)
        source_tags=source_creative.get('url_tags') or ''
        if len(re.findall(r'(?:^|&)utm_campaign=pg_[0-9]+(?:&|$)',source_tags))!=1:raise ValueError('source Page tracking missing or ambiguous')
        payload['url_tags']=re.sub(r'(^|&)utm_campaign=pg_[0-9]+(?=&|$)',lambda match:match.group(1)+'utm_campaign='+page['page_token'],source_tags,count=1)
        ads.append({'name':f'AD {i:02d} - {Path(asset["canonical_filename"]).stem}','source_ad_id':original['id'],'media':{k:media[k] for k in ['asset_id','checksum','vertical_video_id','square_video_id','ready','upload_edge','association_verified']},'creative_payload':payload})
    return {'schema_version':3,'request_id':q['request_id'],'operation':q['operation'],'graph_version':'v26.0','created_at':datetime.now(timezone.utc).isoformat(),'campaigns':[{'idempotency_key':q['request_id']+'-1','app_key':'mgs-meta-app-1299247318762949','account_id':ACCOUNT,'mode':MODE,'source_campaign_id':source['campaign']['id'],'source_adset_id':source_set['id'],'campaign_create':campaign,'adset_create':adset,'adset_name':'ADGROUP 01','name':allocation['names'][0],'start_time':q['start_time'],'status':'ACTIVE','ads':ads}]}

def prepare(path,confirm=False):
    if not confirm:raise ValueError('prepare requires --confirm-prepare')
    q=request_load(path);home=Path(path).parent;cfg=load(CONFIG)
    if (home/'summary.json').exists() and (home/'manifest.json').exists():
        existing=load(home/'manifest.json');summary=load(home/'summary.json')
        if verify_prevalidation(existing) and summary.get('digest')==existing['prevalidation']['content_digest']:
            return summary
    if MODE not in cfg['accounts'][ACCOUNT]['supported_modes']:raise ValueError('validated target clone mode not released in exact account')
    conflict=reader_block_reason(ACCOUNT,cfg['state_root'])
    if conflict and conflict.get('request_id')!=q['request_id']:raise ValueError('another request owns account; no media writes')
    common,meta,sb,token=runtime();source=source_read(q,common,meta,token)
    page=resolve_page(meta,sb,token,ACCOUNT,q['target_page_token'],ensure_pbia=True,request_path=path)
    save(home/'source-live.json',source);save(home/'target-page-live.json',page)
    import ares_manager_storage_standard as standard
    from ares_campaign_v3.shein_media_handoff import _ops
    import ares_archive_storage as storage
    ops=_ops(R);drive_token,_=ops.drive_runtime_token();folder=standard.destination('CC_US_EN','VID','g006','exclusive');standard.validate_folder(storage.drive(drive_token),folder,operation='CC_US_EN',fmt='VID',manager='g006',state='exclusive')
    inventory=[json.loads(x) for x in INVENTORY.read_text().splitlines() if x.strip()];selected=[];livefiles={}
    for filename in q['media_filenames']:
        matches=[x for x in inventory if x.get('canonical_filename')==filename and x.get('manager_media_folder_id')==folder]
        if len(matches)!=1:raise ValueError('exact requested inventory filename missing or ambiguous')
        row=matches[0];live=ops.drive_file_readback(drive_token,row['asset_drive_id']);storage.require_lineage_available(row)
        if (row.get('operation'),row.get('vertical'),row.get('country'),row.get('language'),row.get('format'))!=('CC_US_EN','CC','US','EN','VID'):raise ValueError('manager media operation/language/format mismatch')
        if row.get('metadata_clean') is not True or live.get('parents')!=[folder] or live.get('name')!=filename or live.get('trashed') or live.get('md5Checksum')!=row.get('clean_md5'):raise ValueError('exact manager media identity/bytes drift')
        def reference_only(x):
            if isinstance(x,dict):return any((k=='reference_only' and str(v).lower()=='true') or reference_only(v) for k,v in x.items())
            if isinstance(x,list):return any(reference_only(v) for v in x)
            return False
        if reference_only(live):raise ValueError('reference-only media is not final approved creative')
        if row.get('used_by') and not (row.get('used_by')=='ARES_IN_FLIGHT' and row.get('reservation_request_id')==q['request_id']):raise ValueError('requested asset has prior/conflicting use')
        selected.append(row);livefiles[row['asset_id']]=live
    # A named manager selection is scoped, never a global eligibility release.
    liveads=common.fetch_all_meta(meta,token,'act_'+ACCOUNT+'/ads',{'fields':'id,name,status,creative{id,asset_feed_spec,object_story_spec}','limit':200})
    stems={Path(x['canonical_filename']).stem for x in selected}
    if any(any(stem in ad.get('name','') for stem in stems) for ad in liveads):raise ValueError('requested media has a live/historical named Meta use; reconcile before reservation')
    history=naming.collect_history(meta,token);ledger=load(R/naming.load_policy()['ledger_path']);nums,seq=naming.plan_numbers(q['target_page_token'],1,history,ledger)
    allocation=naming.allocation(q['request_id'])
    proposed=allocation['names'][0] if allocation else naming.format_name(nums[0],page['name'],page['page_token'],seq[0])
    if q.get('approved_name_preview') and proposed!=q['approved_name_preview']:raise ValueError('preview name changed; preserve approval and ask for exact new name')
    allocation=naming.reserve(q['request_id'],ACCOUNT,page['naming_identity'],1,history)
    creation=module('target_creation_helpers',R/'scripts/ares-eggbev-creation.py');creation.reserve_inventory(selected,q['request_id'],q['requested_by'],home/'reservation.json')
    save(home/'selected-assets.json',selected);save(home/'media-live-readback.json',list(livefiles.values()))
    work=Path('/root/.hermes/profiles/ares/cache/scratch')/q['request_id'];work.mkdir(exist_ok=True)
    registry=MediaRegistry(R/'data/ares/meta-ads/engine-v3/media-registry.json');service=PrestageService(registry,TargetAccountUploader(common=meta,user_token=token,account_id=ACCOUNT))
    def prepare_asset(row):
        vertical=work/(row['asset_id']+'-vertical.mp4');square=work/(row['asset_id']+'-square.mp4')
        if not vertical.exists():creation.download_drive(drive_token,livefiles[row['asset_id']],vertical)
        if creation.verify_clean(vertical)!=row['clean_checksum']:raise ValueError('download checksum changed')
        if not square.exists():
            raw=square.with_suffix('.raw.mp4');subprocess.run(['ffmpeg','-nostdin','-y','-i',str(vertical),'-vf','scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:black','-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-movflags','+faststart',str(raw)],capture_output=True,check=True,timeout=600)
            subprocess.run([str(R/'scripts/clean-creative-metadata.sh'),'clean',str(raw),'--out',str(square),'--agent','ares','--json'],capture_output=True,check=True,timeout=180)
        creation.verify_clean(square)
        return {'vertical_path':str(vertical),'square_path':str(square),'square_policy':'full_frame_padding_no_text_crop'}
    result=OnDemandMediaPipeline(service,max_workers=3).run(account_id=ACCOUNT,assets=selected,prepare_asset=prepare_asset)
    save(home/'prestage.json',result);draft=build(q,source,page,selected,registry,allocation);sealed=prevalidate_payload(draft,registry);manifest=Manifest.from_dict(sealed);validate_account_policy(manifest,cfg)
    save(home/'manifest.json',sealed);plan=CampaignEngine(cfg,transport_factory=lambda account:None).dry_run(manifest);save(home/'plan.json',plan)
    summary={'phase':'AWAITING_FINAL_APPROVAL','request_id':q['request_id'],'name':proposed,'budget_usd':q['daily_budget_usd'],'start_time':q['start_time'],'page_name':page['name'],'page_token':page['page_token'],'structure':f'1 campaign / 1 target adset / {len(selected)} final ads; {len(selected)} PAUSED technical seeds preserved without deletion','media':q['media_filenames'],'copy':q['copy'],'source_unchanged':True,'digest':sealed['prevalidation']['content_digest'],'campaign_writes':0}
    save(home/'summary.json',summary);return summary


def execute(path,confirm=False,approved_digest=None,approval_message_id=None,check_only=False):
    if not confirm or not approval_message_id:raise ValueError('execute requires explicit final OK, digest and --confirm-execute')
    q=request_load(path);home=Path(path).parent;payload=load(home/'manifest.json')
    gate_config=load(CONFIG);conflict=reader_block_reason(ACCOUNT,gate_config['state_root'])
    if conflict and conflict.get('request_id')!=q['request_id']:raise ValueError('another request owns account; approved request remains resumable')
    if approved_digest!=payload.get('prevalidation',{}).get('content_digest') or not verify_prevalidation(payload):raise ValueError('approved manifest digest mismatch')
    # A pre-intake commercial OK is not a later manifest/technical-seed approval.
    if approval_message_id==q.get('commercial_ok_message_id'):raise ValueError('final summary requires a subsequent explicit OK message')
    common,meta,sb,token=runtime();current=source_read(q,common,meta,token);original=load(home/'source-live.json')
    if not check_only:
        target=home/'source-current-before-execute.json'
        if target.exists():target=home/('source-current-before-resume-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        save(target,current)
    if source_comparison(current)!=source_comparison(original):raise ValueError('source snapshot changed; reconcile before write')
    page=resolve_page(meta,sb,token,ACCOUNT,q['target_page_token'])
    if page['instagram_user_id']!=load(home/'target-page-live.json')['instagram_user_id']:raise ValueError('target Page/PBIA changed')
    naming.verify_live_reservation(q['request_id'],naming.collect_history(meta,token))
    inventory={x['asset_id']:x for x in (json.loads(s) for s in INVENTORY.read_text().splitlines() if s.strip())}
    for row in load(home/'selected-assets.json'):
        if inventory[row['asset_id']].get('reservation_request_id')!=q['request_id']:raise ValueError('asset reservation changed')
    from contextlib import nullcontext
    from ares_campaign_v3.target_continuation import admission,expired
    cfg=load(CONFIG)
    scope=admission(path,payload,cfg,meta=meta,token=token) if expired(payload) else nullcontext(None)
    with scope as continuation:
        manifest=Manifest.from_dict(payload);validate_account_policy(manifest,cfg)
        if continuation and approval_message_id!=continuation['receipt']['approval_message_id']:raise ValueError('continuation final approval ID mismatch')
        engine=CampaignEngine(cfg,transport_factory=real_transport_factory(cfg,manifest))
        if check_only:
            if not continuation:raise ValueError('check-continuation requires existing elapsed NOW proof')
            from ares_campaign_v3.target_page_clone import reconcile_existing
            bundle=engine.planner.build(manifest).lanes[ACCOUNT][0]
            checked_record=copy.deepcopy(continuation['record'])
            proof=reconcile_existing(engine,bundle,engine.transport_factory(ACCOUNT),checked_record,require_shells=True)
            return {'phase':'CONTINUATION_VERIFIED_READ_ONLY','request_id':q['request_id'],'manifest_digest':manifest.digest,'confirmed_ids':proof,'known_media_observations':checked_record.get('target_clone_known_media_observed',{}),'media_qa_bypass':False,'meta_writes':0,'drive_writes':0}
        if not continuation:save(home/'final-approval.json',{'message_id':approval_message_id,'approved_digest':approved_digest})
        result=engine.execute(manifest)
    save(home/'engine-result.json',result)
    # Exact assignment finalization is resumed independently if any readback or
    # manager-stock movement cannot be certified; never replay a completed Engine.
    if result['status'] in {'COMPLETE_FUTURE_ACTIVE','COMPLETE_PAUSED'}:
        return {'phase':'POSTPROCESS_PENDING','engine_result':result,'next_step':'Verify rendered media/lineage and persist exact asset assignments, then confirm-use by the existing manager-stock controller. Do not replay campaign creation.'}
    return result


def finalize(path):
    q=load(path);home=Path(path).parent;cfg=load(CONFIG)
    result=load(home/'engine-result.json')
    if result.get('status') not in {'COMPLETE_FUTURE_ACTIVE','COMPLETE_PAUSED'}:raise ValueError('Engine not complete; no stock finalization')
    checkpoint=load(Path(cfg['state_root'])/'checkpoints'/f"{q['request_id']}-{ACCOUNT}.json")
    records=[x for x in checkpoint['bundles'] if x.get('status')=='COMPLETE']
    if len(records)!=1:raise ValueError('one exact completed bundle required')
    record=records[0];ids=record['target_clone_ids'];selected=load(home/'selected-assets.json');manifest=load(home/'manifest.json')['campaigns'][0]
    if not selected or len(selected)!=len(manifest['ads']) or len(selected)!=len(q['media_filenames']):raise ValueError('nonempty exact asset/manifest cardinality required')
    _,meta,_,token=runtime();assignments=[]
    for ai,(asset,expected) in enumerate(zip(selected,manifest['ads']),1):
        ad_id=ids[f'copied_ad_id_1_{ai}'];code,ad,_=meta.graph_get(ad_id,token,{'fields':'id,account_id,name,campaign_id,adset_id,status,source_ad_id,creative{id,object_story_spec,asset_feed_spec,url_tags,effective_object_story_id}'})
        creative=ad.get('creative') or {};videos={str(x['video_id']) for x in creative.get('asset_feed_spec',{}).get('videos',[])}
        if code!=200 or ad.get('account_id')!=ACCOUNT or ad.get('name')!=expected['name'] or ad.get('campaign_id')!=ids['campaign_id_1'] or ad.get('adset_id')!=ids['adset_id_1'] or ad.get('status')!=manifest['status'] or str(ad.get('source_ad_id'))!=ids[f'seed_ad_id_1_{ai}']:raise ValueError('final exact assignment readback mismatch')
        if {expected['media']['vertical_video_id'],expected['media']['square_video_id']}!=videos or creative.get('url_tags')!=expected['creative_payload']['url_tags'] or creative.get('object_story_spec',{}).get('page_id')!=q['target_page_id_sb']:raise ValueError('final media/Page/tracking mismatch')
        assignments.append({'asset_id':asset['asset_id'],'campaign_id':ad['campaign_id'],'adset_id':ad['adset_id'],'ad_id':ad_id,'creative_id':creative['id'],'video_id':expected['media']['vertical_video_id'],'effective_object_story_id':creative.get('effective_object_story_id')})
    with INVENTORY.with_suffix(INVENTORY.suffix+'.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);rows=[json.loads(x) for x in INVENTORY.read_text().splitlines() if x.strip()];byid={x['asset_id']:x for x in rows}
        for a in assignments:
            row=byid[a['asset_id']]
            if row.get('reservation_request_id')!=q['request_id']:raise ValueError('final inventory reservation changed')
            row.update({'used_by':a['campaign_id'],'ad_account_id':ACCOUNT,'meta_adset_id':a['adset_id'],'meta_ad_id':a['ad_id'],'meta_creative_id':a['creative_id'],'meta_video_id':a['video_id'],'effective_object_story_id':a['effective_object_story_id'],'campaign_owner':q['requested_by'],'status':'02_TESTING','reservation_status':'EM_USO','ares_eligible':False,'strategy':'BOT_MESSENGER','last_reconciled_at':datetime.now(timezone.utc).isoformat()})
        backup=home/'inventory-before-finalize.jsonl'
        if not backup.exists():backup.write_bytes(INVENTORY.read_bytes())
        temp=INVENTORY.with_suffix('.target-clone.new');temp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows));os.replace(temp,INVENTORY)
    import ares_manager_storage_standard as standard
    movements=[standard.confirm_usage(a['asset_id'],q['request_id'],apply=True) for a in assignments]
    ledger_path=R/naming.load_policy()['ledger_path']
    with ledger_path.with_suffix(ledger_path.suffix+'.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);ledger=load(ledger_path);allocation=ledger['allocations'][q['request_id']];allocation.update({'status':'COMMITTED','campaign_ids':result['campaign_ids'],'completed_at':datetime.now(timezone.utc).isoformat()});save(ledger_path,ledger)
    final={'phase':'COMPLETE','request_id':q['request_id'],'campaign_name':manifest['name'],'campaign_ids':result['campaign_ids'],'assignments':assignments,'manager_stock_readbacks':movements,'source_unchanged':True,'configured_status':manifest['status'],'scheduled_start':manifest['start_time'],'daily_budget_minor':manifest['campaign_create']['daily_budget'],'serving_verified':False}
    save(home/'final.json',final);return final


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','execute','finalize','check-continuation']);p.add_argument('--input',required=True,type=Path);p.add_argument('--confirm-prepare',action='store_true');p.add_argument('--confirm-execute',action='store_true');p.add_argument('--approved-digest');p.add_argument('--approval-message-id');a=p.parse_args()
    # One foreground/request owner across preparation and engine invocation.
    q=load(a.input);lock=Path(a.input).parent/'target-clone.lock'
    with lock.open('a+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.command=='prepare':
            request_load(a.input)
            leases=AccountWriterLeaseStore(load(CONFIG)['state_root']);leases.claim(ACCOUNT,q['request_id'],status='PREFLIGHT_ACTIVE')
            try:value=prepare(a.input,a.confirm_prepare)
            finally:leases.release(ACCOUNT,q['request_id'])
        else:value=finalize(a.input) if a.command=='finalize' else execute(a.input,a.confirm_execute or a.command=='check-continuation',a.approved_digest,a.approval_message_id,check_only=a.command=='check-continuation')
    print(json.dumps(value,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
