"""Exact Eggbev01 -> 03 source-derived clone capability, not native cross-account copy.

External source IDs are audit references ONLY. Engine target_page_clone creates
source-derived target shells and PAUSED local seeds, then copies locally. Nothing
in this module grants credentials, Page access or publication from maintenance.
"""
from __future__ import annotations
import copy,fcntl,hashlib,json,re,os
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from contextlib import contextmanager
from contextvars import ContextVar
from .schema import ManifestError

ROOT=Path('/root/mgs-agent')
SOURCE='1034081997659047';TARGET='1481815942722118'
MODE='clone_cross_account_prestaged';OP='Eggbev-US-CC-EN-BOT'
AUTH='1571652369467445359';ACTOR='1055570806945620030';CEO='344196393512075265'
POLICY=ROOT/'data/ares/meta-ads/policies/eggbev01-to03-clone-authority.json'
APP='953171080682697';USER='122147293515218951'
CURRENT=ContextVar('eggbev_cross_account_final_approval',default=None)

def load(path):return json.loads(Path(path).read_text())
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def policy(request_id,*,path=None,installed=True):
    p=load(path or POLICY)
    if (p.get('authorized_by_discord_id')!=CEO or p.get('authority_message_id')!=AUTH
        or p.get('source_account_id')!=SOURCE or p.get('target_account_id')!=TARGET
        or request_id not in p.get('allowed_request_ids',[])
        or p.get('status') not in {'active','authorized_implementation_pending'}
        or (installed and (p.get('implementation_verified') is not True or p.get('status')!='active'))):
        raise ValueError('exact cross-account authority/capability unavailable')
    return p

def validate_shape(c):
    ref=c.cross_account_source
    if c.mode!=MODE:
        if ref:raise ManifestError('cross-account source cannot be attached to another mode')
        return
    keys={'account_id','campaign_id','adset_id','ad_ids','page_id','page_token','access','semantics','snapshot_sha256'}
    if (not isinstance(ref,dict) or set(ref)!=keys or ref['account_id']!=SOURCE or c.account_id!=TARGET
        or ref['campaign_id']!=c.source_campaign_id or ref['adset_id']!=c.source_adset_id
        or ref['access']!='READ_ONLY' or ref['semantics']!='source_derived_shell_local_seed_copy'
        or ref['page_token']!='pg_23187' or not re.fullmatch('[a-f0-9]{64}',str(ref['snapshot_sha256']))
        or not isinstance(ref['ad_ids'],list) or ref['ad_ids']!=[a.source_ad_id for a in c.ads]
        or len(set(ref['ad_ids']))!=len(c.ads)
        or any(re.fullmatch('[1-9][0-9]+',str(v)) is None for v in [ref['campaign_id'],ref['adset_id'],ref['page_id'],*ref['ad_ids']])
        or c.adset_create.get('promoted_object',{}).get('page_id')!=ref['page_id']):
        raise ManifestError('exact source/target/Page/lineage identity required for cross-account clone')

def validate_capability(manifest,config):
    cs=[c for c in manifest.campaigns if c.mode==MODE]
    if not cs:return
    try:p=policy(manifest.request_id)
    except ValueError as e:raise ManifestError(str(e)) from e
    a=config.get('accounts',{}).get(TARGET,{})
    cap=a.get('cross_account_clone') or {}
    if (manifest.operation!=OP or len(cs)!=len(manifest.campaigns) or len(cs)!=5
        or cap.get('enabled') is not True or cap.get('authority_message_id')!=AUTH
        or cap.get('source_account_id')!=SOURCE or cap.get('target_account_id')!=TARGET
        or cap.get('mode')!=MODE or cap.get('policy_source')!=str(POLICY.relative_to(ROOT))
        or a.get('meta_app_id')!=APP or a.get('app_key')!='mgs-meta-app-'+APP
        or a.get('token_user_id')!=USER or a.get('token_identity')!='Ana Cunha'
        or a.get('token_item')!=p['advertiser_binding']['token_item']):
        raise ManifestError('cross-account route/account advertiser not installed exactly')
    from .eggbev_create import messenger_welcome_message
    welcome=json.loads(messenger_welcome_message())
    for i,c in enumerate(cs,1):
        validate_shape(c)
        if (c.idempotency_key!=manifest.request_id+'-'+str(i) or len(c.ads)!=3
            or c.campaign_create['daily_budget']!='3500' or c.adset_name!='ADGROUP 01'
            or c.status!='ACTIVE' or c.start_intent!='SCHEDULED'):
            raise ManifestError('exact five-campaign request/order/budget required')
        for ad in c.ads:
            payload=ad.creative_payload;afs=payload.get('asset_feed_spec') or {}
            value=afs.get('additional_data',{}).get('page_welcome_message')
            try:value=json.loads(value) if isinstance(value,str) else value
            except ValueError:value=None
            if (value!=welcome or [t['text'] for t in afs.get('titles',[])]!=['APPLY NOW ✅','✔️ APPLY TODAY','CARD NOW✅']
                or [d['text'] for d in afs.get('descriptions',[])]!=['⭐️⭐️⭐️⭐️⭐️']
                or re.findall(r'(?:^|&)utm_campaign=([^&]*)',payload.get('url_tags',''))!=['pg_23187']):
                raise ManifestError('cross-account literal copy/JSON-AGT/Page tracking mismatch')

def primary_text(creative):
    afs=creative.get('asset_feed_spec') or {};story=creative.get('object_story_spec') or {};values=[]
    if 'bodies' in afs:
        bodies=afs['bodies']
        if not isinstance(bodies,list) or len(bodies)!=1 or not isinstance(bodies[0].get('text'),str):raise ValueError('source primary text ambiguous')
        values.append(bodies[0]['text'])
    for branch in ['video_data','link_data']:
        if 'message' in (story.get(branch) or {}):values.append(story[branch]['message'])
    if not values or any(not isinstance(v,str) or v!=values[0] for v in values):raise ValueError('source primary text missing/conflicting')
    return values[0]

def request_load(path):
    q=load(path);policy(q.get('request_id'))
    if (q.get('source_account_id')!=SOURCE or q.get('target_account_id')!=TARGET or q.get('operation_id')!='Eggbev-US-CC-EN-03-BOT'
        or q.get('source_thread_id')!='1565032671669919827' or q.get('source_channel_id')!='1539422731727147079'
        or q.get('requested_by_discord_id')!=ACTOR or q.get('duplicate_count')!=5
        or q.get('source_page_token_requested')!='pg_23187' or q.get('same_page_required') is not True
        or q.get('budget_usd_per_campaign')!='35' or q.get('start_intent')!='IMMEDIATE_EXPLICIT'
        or q.get('source_mutation_authorized') is not False
        or q.get('source_campaign_name')!='303 - Moorcroft Finances - ENG - US - (pg_23187) - C01'
        or [g.get('slot') for g in q.get('campaigns',[])]!=list(range(1,6))):raise ValueError('exact persisted request identity/intent required')
    files=[f for g in q['campaigns'] for f in g.get('media_filenames',[])]
    expected=[f'CC_US_EN_VID_AVAILABLE_LIMIT_PV_{n}.mp4' for n in range(172,187)]
    if files!=expected or any(len(g['media_filenames'])!=3 for g in q['campaigns']):raise ValueError('literal requested media slots/order changed')
    if q.get('copy')!={'headlines':['APPLY NOW ✅','✔️ APPLY TODAY','CARD NOW✅'],'description':'⭐️⭐️⭐️⭐️⭐️','primary_text':'PRESERVE_SOURCE','cta':'PRESERVE_SOURCE'}:raise ValueError('literal requested copy changed')
    return q

@contextmanager
def reader(account_id,config,request_id=None):
    """Shared canonical lease lock + under-lock gate; never release another lease."""
    from .coordination import reader_block_reason
    root=Path(config['state_root'])/'writer-leases';root.mkdir(parents=True,exist_ok=True)
    with (root/(account_id+'.lock')).open('a+') as stream:
        fcntl.flock(stream,fcntl.LOCK_SH|fcntl.LOCK_NB)
        reason=reader_block_reason(account_id,config['state_root'])
        if reason and (account_id==SOURCE or reason.get('request_id')!=request_id):raise ValueError('account reader excluded by active request')
        yield


def runtime(runner,config):
    common=runner.module('eggbev_cross_common',ROOT/'scripts/ares-eggbev-roas-common.py')
    account=load(ROOT/f'data/ares/meta-ads/accounts/{TARGET}.json')['accounts'][0]
    meta,sb,token,_=common.load_runtime_modules(account)
    return common,meta,sb,token


def verify_advertiser(meta,token):
    code,identity,_=meta.graph_get_credential_metadata(TARGET,token)
    dc,data,_=meta.graph_get_credential_metadata(TARGET,token,inspect_token=True)
    d=data.get('data') or {}
    if (code!=200 or dc!=200 or identity.get('id')!=USER or identity.get('name')!='Ana Cunha'
        or d.get('app_id')!=APP or d.get('user_id')!=USER or d.get('type')!='USER' or d.get('is_valid') is not True):raise ValueError('exact approved advertiser/app metadata unavailable')
    code,a,_=meta.graph_get('act_'+TARGET,token,{'fields':'id,name,account_status,currency,timezone_name,business,user_tasks'})
    if (code!=200 or a.get('id')!='act_'+TARGET or a.get('account_status')!=1 or a.get('currency')!='USD'
        or a.get('timezone_name')!='America/New_York' or a.get('business',{}).get('id')!='155263197283282'
        or not {'ANALYZE','ADVERTISE'}<=set(a.get('user_tasks') or [])):raise ValueError('target account task/business/currency readiness unavailable')
    return {'identity':{'id':identity['id'],'name':identity['name']},'app_id':d['app_id'],'account':a}


def live_request(q,common):
    op=load(ROOT/'data/ares/meta-ads/operations/Eggbev-US-CC-EN-03-BOT.json')
    users=load(ROOT/'data/authorized-users.json')['agents']['ares']
    if op['authority'].get('status')!='active' or op['authority'].get('authorized_manager_discord_id')!=ACTOR or ACTOR not in users['authorized_user_discord_ids']:raise ValueError('current commercial authority unavailable')
    code,t=common.discord_request('GET','/channels/'+q['source_thread_id'])
    if code!=200 or t.get('id')!=q['source_thread_id'] or t.get('parent_id')!=q['source_channel_id']:raise ValueError('exact request origin unavailable')
    code,m=common.discord_request('GET',f"/channels/{q['source_thread_id']}/messages/{q['source_message_id']}")
    if code!=200 or m.get('id')!=q['source_message_id'] or m.get('author',{}).get('id')!=ACTOR or m['author'].get('bot') or m.get('edited_timestamp'):raise ValueError('original human request changed/unavailable')
    # Persisted intent was authenticated at intake; compare its full live content hash
    # on first preparation and every replay rather than reinterpreting free text.
    return {'message_id':m['id'],'content_sha256':hashlib.sha256(m['content'].encode()).hexdigest(),'timestamp':m['timestamp']}


def source_read(q,runner,common,meta,token,config):
    with reader(SOURCE,config):
        rows=common.fetch_all_meta(meta,token,'act_'+SOURCE+'/campaigns',{'fields':'id,name,status','limit':200})
        matches=[r for r in rows if r.get('name')==q['source_campaign_name'] and r.get('status') not in {'DELETED','ARCHIVED'}]
        if len(matches)!=1:raise ValueError('exact source campaign missing/ambiguous')
        cid=str(matches[0]['id'])
        if q.get('source_campaign_id') and q['source_campaign_id']!=cid:raise ValueError('persisted source campaign ID changed')
        code,c,_=meta.graph_get(cid,token,{'fields':'id,account_id,name,status,objective,buying_type,bid_strategy,daily_budget,lifetime_budget,special_ad_categories,special_ad_category_country'})
        if code!=200 or c.get('account_id')!=SOURCE or c.get('name')!=q['source_campaign_name'] or c.get('id')!=cid or c.get('lifetime_budget') not in {None,'0',0} or not c.get('daily_budget'):raise ValueError('source identity/budget semantics mismatch')
        sets=common.fetch_all_meta(meta,token,cid+'/adsets',{'fields':'id,name,status,billing_event,optimization_goal,destination_type,targeting,promoted_object,attribution_spec,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities,bid_amount,bid_constraints,optimization_sub_event','limit':100})
        ads=common.fetch_all_meta(meta,token,cid+'/ads',{'fields':'id,name,status,adset_id,source_ad_id,creative{id,object_story_spec,asset_feed_spec,url_tags,degrees_of_freedom_spec,contextual_multi_ads}','limit':100})
        sub={**q,'source_campaign_id_candidate':cid,'media_filenames':q['campaigns'][0]['media_filenames']}
        proof=runner.source_seed_proof(sub)
        source=runner.classify_source(c,sets,ads,3,proof)
        runner.source_rematerialization(source)
        for ad in source['ads']:primary_text(ad['creative'])
        page_ids={str(ad['creative'].get('object_story_spec',{}).get('page_id') or '') for ad in source['ads']}
        page_ids.add(str(source['adset'].get('promoted_object',{}).get('page_id') or ''))
        if len(page_ids)!=1 or not next(iter(page_ids)).isdigit():raise ValueError('source Page ambiguous')
        if any(re.findall(r'(?:^|&)utm_campaign=([^&]*)',a['creative'].get('url_tags',''))!=['pg_23187'] for a in source['ads']):raise ValueError('source requested pg tracking mismatch')
        return source


def page_read(q,source,meta,sb,token,path,*,ensure_pbia=False):
    from .eggbev_page_identity import resolve
    p=resolve(meta,sb,token,TARGET,q['source_page_token_requested'],authority_path=POLICY,ensure_pbia=ensure_pbia,request_path=path)
    if p['id']!=str(source['adset']['promoted_object']['page_id']) or p['name']!='Moorcroft Finances':raise ValueError('requested/source/target Page divergence')
    return p


def build(q,source,page,selected,registry,allocation,runner,start_time):
    if len(selected)!=15 or len({a['asset_id'] for a in selected})!=15 or len(allocation['names'])!=5:raise ValueError('exact 15 ordered assets and five names required')
    if [a['canonical_filename'] for a in selected]!=[f for g in q['campaigns'] for f in g['media_filenames']]:raise ValueError('selected media order differs from request')
    if str(source['campaign']['account_id'])!=SOURCE or page['id']!=source['adset']['promoted_object']['page_id']:raise ValueError('source account/Page not preserved')
    campaigns=[]
    for i,g in enumerate(q['campaigns']):
        sub={'request_id':q['request_id']+'-slot-'+str(i+1),'operation':OP,'daily_budget_usd':q['budget_usd_per_campaign'],'start_time':start_time,'copy':q['copy']}
        c=runner.build(sub,source,page,selected[i*3:i*3+3],registry,{'names':[allocation['names'][i]]},account_id=TARGET,mode=MODE)['campaigns'][0]
        c['idempotency_key']=q['request_id']+'-'+str(i+1)
        c['cross_account_source']={'account_id':SOURCE,'campaign_id':source['campaign']['id'],'adset_id':source['adset']['id'],'ad_ids':[a['id'] for a in source['ads']],'page_id':page['id'],'page_token':page['page_token'],'access':'READ_ONLY','semantics':'source_derived_shell_local_seed_copy','snapshot_sha256':digest(source)}
        campaigns.append(c)
    return {'schema_version':3,'request_id':q['request_id'],'operation':OP,'graph_version':'v26.0','created_at':datetime.now(timezone.utc).isoformat(),'campaigns':campaigns}


def home_for(q):return ROOT/'data/ares/meta-ads/audit/eggbev/cross-account'/q['request_id']


def prepare(path,runner,confirm=False):
    if not confirm:raise ValueError('prepare requires --confirm-prepare; never publishes campaign')
    q=request_load(path);cfg=load(runner.CONFIG)
    # Gate before credentials, PBIA, reservation, downloads, or media writes.
    with reader(SOURCE,cfg):pass
    from .coordination import AccountWriterLeaseStore
    from request_serialization import request_lock
    home=home_for(q);home.mkdir(parents=True,exist_ok=True)
    with request_lock(home,q['request_id'],blocking=False):
        leases=AccountWriterLeaseStore(cfg['state_root']);leases.claim(TARGET,q['request_id'],status='PREFLIGHT_ACTIVE')
        try:
            common,meta,sb,token=runtime(runner,cfg);binding=verify_advertiser(meta,token);human=live_request(q,common)
            source=source_read(q,runner,common,meta,token,cfg);page=page_read(q,source,meta,sb,token,path)
            if (home/'summary.json').exists():
                from .prevalidation import verify_prevalidation
                sealed=load(home/'manifest.json');summary=load(home/'summary.json')
                if (not verify_prevalidation(sealed) or summary['digest']!=sealed['prevalidation']['content_digest']
                    or summary['request_sha256']!=digest(q) or load(home/'request-live.json')!=human
                    or runner.source_comparison(source)!=runner.source_comparison(load(home/'source-live.json'))):raise ValueError('prepared request/source/seal changed; no replay')
                return summary
            for name,value in [('source-live.json',source),('target-page-live.json',page),('advertiser-live.json',binding),('request-live.json',human)]:
                target=home/name
                if target.exists() and load(target)!=value:raise ValueError('preparation checkpoint drift before effects')
                if not target.exists():runner.save(target,value)
            selected,livefiles,drive_token,creation=select_media(q,runner,common,meta,token,home)
            from . import eggbev_creation_naming as naming
            # Every history GET is protected; no naming read bypasses source lease.
            from contextlib import ExitStack
            with ExitStack() as stack:
                for aid in sorted(naming.load_policy()['account_ids']):stack.enter_context(reader(aid,cfg,q['request_id']))
                history=naming.collect_history(meta,token)
            allocation=naming.reserve(q['request_id'],TARGET,page['naming_identity'],5,history)
            creation.reserve_inventory(selected,q['request_id'],q['requested_by'],home/'reservation.json')
            runner.save(home/'selected-assets.json',selected)
            prepare_media(q,selected,livefiles,drive_token,creation,runner,meta,token,home)
            from .media_registry import MediaRegistry
            from .prevalidation import prevalidate_payload,validate_account_policy
            from .schema import Manifest
            from .engine import CampaignEngine
            start=creation.immediate_execute_start();draft=build(q,source,page,selected,MediaRegistry(cfg['media_registry']),allocation,runner,start)
            sealed=prevalidate_payload(draft,MediaRegistry(cfg['media_registry']));manifest=Manifest.from_dict(sealed);validate_account_policy(manifest,cfg)
            runner.save(home/'manifest.json',sealed);plan=CampaignEngine(cfg,transport_factory=lambda a:None,read_only=True).dry_run(manifest);runner.save(home/'plan.json',plan)
            summary={'phase':'AWAITING_FINAL_APPROVAL','request_id':q['request_id'],'request_sha256':digest(q),'source_account_id':SOURCE,'target_account_id':TARGET,'source_campaign_id':source['campaign']['id'],'source_snapshot_sha256':digest(source),'mode':MODE,'semantics':'source_derived_shell_local_seed_copy','names':allocation['names'],'daily_budget_usd_per_campaign':'35','total_daily_budget_usd':'175','start_time':start,'start_intent':q['start_intent'],'page':page,'final_campaigns':5,'final_ads':15,'technical_paused_seeds':15,'media':[a['canonical_filename'] for a in selected],'copy':q['copy'],'json_messenger':'JSON-AGT incluído e conferido em todos os 15 anúncios','source_unchanged':True,'digest':sealed['prevalidation']['content_digest'],'campaign_writes':0,'final_ok_required':True}
            runner.save(home/'summary.json',summary);return summary
        finally:leases.release(TARGET,q['request_id'])


def select_media(q,runner,common,meta,token,home):
    import ares_manager_storage_standard as standard
    import ares_archive_storage as storage
    from .shein_media_handoff import _ops
    ops=_ops(ROOT);drive_token,_=ops.drive_runtime_token();folder=standard.destination('CC_US_EN','VID','g006','exclusive')
    standard.validate_folder(storage.drive(drive_token),folder,operation='CC_US_EN',fmt='VID',manager='g006',state='exclusive')
    inventory=[json.loads(x) for x in runner.INVENTORY.read_text().splitlines() if x.strip()];selected=[];livefiles={}
    for filename in [f for g in q['campaigns'] for f in g['media_filenames']]:
        matches=[x for x in inventory if x.get('canonical_filename')==filename and x.get('manager_media_folder_id')==folder]
        if len(matches)!=1:raise ValueError('exact requested manager inventory missing/ambiguous')
        row=matches[0];storage.require_lineage_available(row);live=ops.drive_file_readback(drive_token,row['asset_drive_id'])
        if ((row.get('operation'),row.get('vertical'),row.get('country'),row.get('language'),row.get('format'))!=('CC_US_EN','CC','US','EN','VID')
            or row.get('metadata_clean') is not True or live.get('parents')!=[folder] or live.get('name')!=filename
            or live.get('trashed') or live.get('md5Checksum')!=row.get('clean_md5') or '"reference_only": true' in json.dumps(live).lower()
            or (row.get('used_by') and not (row.get('used_by')=='ARES_IN_FLIGHT' and row.get('reservation_request_id')==q['request_id']))):raise ValueError('requested media identity/reservation/bytes mismatch')
        selected.append(row);livefiles[row['asset_id']]=live
    liveads=common.fetch_all_meta(meta,token,'act_'+TARGET+'/ads',{'fields':'id,name,status,creative{id,asset_feed_spec,object_story_spec}','limit':200})
    stems={Path(x['canonical_filename']).stem for x in selected}
    if any(any(s in a.get('name','') for s in stems) for a in liveads):raise ValueError('requested asset named Meta use requires reconciliation')
    # Reconcile actual media IDs against every account-scoped response, not names alone.
    from .media_registry import MediaRegistry
    registry=MediaRegistry(load(runner.CONFIG)['media_registry'])
    for asset in selected:
        try:record=registry.require_ready(TARGET,asset['asset_id'],asset['clean_checksum'])
        except Exception:continue
        vids={record['vertical_video_id'],record.get('square_video_id')}
        for ad in liveads:
            cr=ad.get('creative') or {};observed={v.get('video_id') for v in cr.get('asset_feed_spec',{}).get('videos',[])}|{cr.get('object_story_spec',{}).get('video_data',{}).get('video_id')}
            if (vids-{None})&observed:raise ValueError('requested media has prior account association use')
    return selected,livefiles,drive_token,runner.module('cross_creation_helpers',ROOT/'scripts/ares-eggbev-creation.py')


def prepare_media(q,selected,livefiles,drive_token,creation,runner,meta,token,home):
    from .media_registry import MediaRegistry
    from .prestage import PrestageService,OnDemandMediaPipeline
    import subprocess
    cfg=load(runner.CONFIG);work=Path('/root/.hermes/profiles/ares/cache/scratch')/q['request_id'];work.mkdir(parents=True,exist_ok=True)
    service=PrestageService(MediaRegistry(cfg['media_registry']),runner.TargetAccountUploader(common=meta,user_token=token,account_id=TARGET))
    def asset(row):
        vertical=work/(row['asset_id']+'-vertical.mp4');square=work/(row['asset_id']+'-square.mp4')
        if not vertical.exists():creation.download_drive(drive_token,livefiles[row['asset_id']],vertical)
        if creation.verify_clean(vertical)!=row['clean_checksum']:raise ValueError('download checksum changed')
        if not square.exists():
            raw=square.with_suffix('.raw.mp4');subprocess.run(['ffmpeg','-nostdin','-y','-i',str(vertical),'-vf','scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:black','-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-movflags','+faststart',str(raw)],check=True,capture_output=True,timeout=600)
            subprocess.run([str(ROOT/'scripts/clean-creative-metadata.sh'),'clean',str(raw),'--out',str(square),'--agent','ares','--json'],check=True,capture_output=True,timeout=180)
        creation.verify_clean(square)
        return {'vertical_path':str(vertical),'square_path':str(square),'square_policy':'full_frame_padding_no_text_crop'}
    result=OnDemandMediaPipeline(service,max_workers=3).run(account_id=TARGET,assets=selected,prepare_asset=asset)
    runner.save(home/'prestage.json',result)


def final_approval(q,summary,common,message_id,approved_digest):
    """A fresh, later human reply to the exact posted summary, never the intake OK."""
    from .prevalidation import verify_prevalidation
    home=home_for(q);payload=load(home/'manifest.json');receipt=load(home/'summary-delivery.json')
    if not verify_prevalidation(payload) or approved_digest!=summary['digest'] or approved_digest!=payload['prevalidation']['content_digest'] or receipt.get('digest')!=approved_digest or receipt.get('request_id')!=q['request_id']:raise ValueError('summary/manifest approved seal mismatch')
    if (summary.get('final_campaigns'),summary.get('final_ads'),summary.get('technical_paused_seeds'))!=(5,15,15) or summary.get('request_sha256')!=digest(q):raise ValueError('full final summary coverage mismatch')
    def get(mid):
        code,m=common.discord_request('GET',f"/channels/{q['source_thread_id']}/messages/{mid}")
        if code!=200 or m.get('id')!=mid or m.get('channel_id')!=q['source_thread_id'] or m.get('edited_timestamp'):raise ValueError('exact unedited final approval/summary unavailable')
        return m
    sent=get(receipt['message_id']);ok=get(message_id)
    required=[*summary.get('names',[]),'JSON-AGT','PAUSED','15','35','175']
    if any(value not in sent.get('content','') for value in required):raise ValueError('posted summary lacks sealed parameters or PAUSED seeds disclosure')
    if (hashlib.sha256(sent['content'].encode()).hexdigest()!=receipt.get('content_sha256')
        or sent.get('author',{}).get('id')!='1508864261504630925' or not sent['author'].get('bot')
        or ok.get('author',{}).get('id') not in {ACTOR,CEO} or ok['author'].get('bot')
        or ok.get('content','').strip().casefold() not in {'ok','sim','pode executar','pode publicar','aprovado'}
        or ok.get('message_reference',{}).get('message_id')!=sent['id']
        or datetime.fromisoformat(ok['timestamp'])<=datetime.fromisoformat(sent['timestamp'])
        or message_id in {q['source_message_id'],AUTH}):raise ValueError('subsequent explicit final summary OK missing')
    return payload


def readback_ops(ops):
    from dataclasses import replace
    from urllib.parse import urlsplit,parse_qs,urlencode
    result=[]
    for op in ops:
        path,query=op.relative_url.split('?',1);params=parse_qs(query)
        extra=[]
        if op.name.startswith('readback_campaign_'):extra=['objective','buying_type','special_ad_categories','special_ad_category_country']
        elif op.name.startswith('readback_adsets_'):extra=['destination_type','regional_regulated_categories','regional_regulation_identities','optimization_sub_event']
        if extra:params['fields']=[params['fields'][0]+','+','.join(extra)]
        result.append(replace(op,relative_url=path+'?'+urlencode({k:v[0] for k,v in params.items()})))
    return result


def verify_bundle(bundle,record):
    from .prevalidation import _require_subset
    rows={r['name']:r['body'] for r in record['readback_results']};ids=record['target_clone_ids']
    for ci,c in enumerate(bundle.campaigns,1):
        _require_subset(rows[f'readback_campaign_{ci}'],c.campaign_create,'source-derived campaign')
        _require_subset(rows[f'readback_adsets_{ci}']['data'][0],c.adset_create,'source-derived adset')
        ads={str(a['id']):a for a in rows[f'readback_ads_{ci}']['data']}
        for ai,a in enumerate(c.ads,1):
            for kind in ['seed_ad_id','copied_ad_id']:
                ad=ads[ids[f'{kind}_{ci}_{ai}']]
                if ad.get('adset_id')!=ids[f'adset_id_{ci}']:raise ValueError('cross-account target local hierarchy drift')
                creative=ad['creative'];wanted=a.creative_payload
                for key in ['contextual_multi_ads','degrees_of_freedom_spec']:
                    if creative.get(key)!=wanted.get(key):raise ValueError('cross-account individual creative features drift')
                actual=creative.get('asset_feed_spec') or {};expected=wanted['asset_feed_spec']
                for key in ['asset_customization_rules','call_to_actions','optimization_type']:
                    if actual.get(key)!=expected.get(key):raise ValueError('cross-account creative placement/CTA/rules drift')
                for key in ['videos','titles']:
                    if [v.get('adlabels') for v in actual.get(key,[])]!=[v.get('adlabels') for v in expected.get(key,[])]:raise ValueError('cross-account media/title slot labels drift')


def require_execution(manifest,config):
    if not any(c.mode==MODE for c in manifest.campaigns):return
    validate_capability(manifest,config)
    proof=CURRENT.get()
    if not proof or proof.get('request_id')!=manifest.request_id or proof.get('digest')!=manifest.digest:raise ValueError('cross-account Engine requires fresh final approval context')
    if config['accounts'][TARGET].get('write_enabled') is not True:raise ValueError('target campaign writes disabled')
    with reader(SOURCE,config):pass


def validate_compiled(payload,q,source,page,selected,registry,allocation,runner):
    starts={c['start_time'] for c in payload['campaigns']}
    if len(starts)!=1:raise ValueError('cross-account batch schedule mismatch')
    rebuilt=build(q,source,page,selected,registry,allocation,runner,next(iter(starts)))
    if rebuilt['campaigns']!=payload['campaigns']:raise ValueError('sealed payload differs from exact source-derived compilation')


def dispatch(args,runner):
    q=request_load(args.input)
    if args.command=='prepare':return prepare(args.input,runner,args.confirm_prepare)
    if args.command=='finalize':
        from .eggbev_cross_account_completion import finalize
        return finalize(args.input,runner,args.approved_digest,args.approval_message_id)
    if args.command!='execute':raise ValueError('cross-account command not admitted; preserve IDs and use exact central recovery')
    if not args.confirm_execute or not args.approval_message_id or not args.approved_digest:raise ValueError('final OK/digest/confirm required')
    from request_serialization import request_lock
    from .coordination import AccountWriterLeaseStore
    from .schema import Manifest
    from .prevalidation import validate_account_policy
    from .engine import CampaignEngine
    from .cli import real_transport_factory
    home=home_for(q);cfg=load(runner.CONFIG)
    with reader(SOURCE,cfg):pass
    with request_lock(home,q['request_id'],blocking=False):
        leases=AccountWriterLeaseStore(cfg['state_root']);leases.claim(TARGET,q['request_id'],status='PREFLIGHT_ACTIVE')
        try:
            common,meta,sb,token=runtime(runner,cfg);verify_advertiser(meta,token);human=live_request(q,common)
            if human!=load(home/'request-live.json'):raise ValueError('request changed since preparation')
            summary=load(home/'summary.json');payload=final_approval(q,summary,common,args.approval_message_id,args.approved_digest)
            current=source_read(q,runner,common,meta,token,cfg)
            if runner.source_comparison(current)!=runner.source_comparison(load(home/'source-live.json')):raise ValueError('source changed since summary; no campaign write')
            page=page_read(q,current,meta,sb,token,args.input)
            if page!=load(home/'target-page-live.json'):raise ValueError('Page identity changed since summary')
            from . import eggbev_creation_naming as naming
            from contextlib import ExitStack
            with ExitStack() as stack:
                for aid in sorted(naming.load_policy()['account_ids']):stack.enter_context(reader(aid,cfg,q['request_id']))
                naming.verify_live_reservation(q['request_id'],naming.collect_history(meta,token))
            rows={v['asset_id']:v for v in (json.loads(s) for s in runner.INVENTORY.read_text().splitlines() if s.strip())}
            from .media_registry import MediaRegistry
            from .prevalidation import prevalidate_payload
            registry=MediaRegistry(cfg['media_registry'])
            for a in load(home/'selected-assets.json'):
                if rows[a['asset_id']].get('reservation_request_id')!=q['request_id']:raise ValueError('asset reservation lost')
            # Revalidate every account03 registry/media association gate before Engine.
            check=prevalidate_payload(payload,registry)
            if check['prevalidation']['content_digest']!=args.approved_digest:raise ValueError('registry/manifest changed')
            manifest=Manifest.from_dict(payload);validate_account_policy(manifest,cfg)
            marker=CURRENT.set({'request_id':q['request_id'],'digest':manifest.digest})
            try:result=CampaignEngine(cfg,transport_factory=real_transport_factory(cfg,manifest)).execute(manifest)
            finally:CURRENT.reset(marker)
            runner.save(home/'engine-result.json',result)
            return {'phase':'POSTPROCESS_PENDING' if result['status'].startswith('COMPLETE') else result['status'],'engine_result':result,'technical_paused_seeds':15,'source_unchanged':True,'serving_verified':False}
        finally:
            checkpoint=Path(cfg['state_root'])/'checkpoints'/f"{q['request_id']}-{TARGET}.json"
            if not checkpoint.exists():leases.release(TARGET,q['request_id'])
