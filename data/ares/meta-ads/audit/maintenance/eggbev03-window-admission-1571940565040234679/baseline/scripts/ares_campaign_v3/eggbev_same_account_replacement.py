"""Account-scoped same-account replacement intake; central Engine is the only writer.

Request-only authority is data, never a disguised cross-account request. Existing
media, naming, JSON and completion primitives are reused without source01 calls.
"""
from __future__ import annotations
import copy, hashlib, json, os, re, sys, time
from pathlib import Path
from datetime import datetime, timezone
from contextvars import ContextVar
from contextlib import ExitStack

ROOT = Path('/root/mgs-agent')
MODE = 'clone_target_prestaged'
OP = 'Eggbev-US-CC-EN-BOT'
CEO = '344196393512075265'
TARGET = '1481815942722118'
POLICY = ROOT/'data/ares/meta-ads/policies/eggbev03-same-account-replacement.json'
CURRENT = ContextVar('eggbev_same_account_replacement_approval', default=None)
SPEC_FIELDS = ('request_id','operation_id','source_thread_id','source_channel_id',
               'requested_by_discord_id','source_account_id','target_account_id',
               'source_campaign_id','source_campaign_name','target_page_name',
               'target_page_token','duplicate_count','budget_usd_per_campaign',
               'currency','timezone','campaigns','copy')


def load(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def spec(q):
    return {k:q[k] for k in SPEC_FIELDS}


def home_for(q):
    return ROOT/'data/ares/meta-ads/audit/eggbev/same-account'/q['request_id']/'execution'


def admit(q, config=None, policy_path=None):
    cfg = config if config is not None else load(ROOT/'data/ares/meta-ads/engine-v3/config.json')
    cap = cfg.get('accounts',{}).get(q.get('account_id'),{}).get('target_page_replacement',{})
    p = load(policy_path or POLICY)
    grant = p.get('requests',{}).get(q.get('request_id'),{})
    if (p.get('status')!='active' or p.get('implementation_verified') is not True
        or p.get('authorized_by_discord_id')!=CEO or p.get('mode')!=MODE
        or not grant or grant.get('spec_sha256')!=digest(spec(q))
        or q.get('request_classification')!='NEW_INDEPENDENT_REQUEST'
        or q.get('request_dependencies')!=[] or q.get('cross_account_execution') is not False
        or q.get('account_id')!=TARGET or q.get('source_account_id')!=TARGET
        or q.get('target_account_id')!=TARGET or q.get('requested_by_discord_id')!=CEO
        or q.get('duplicate_count')!=5 or len(q.get('campaigns',[]))!=5
        or [g.get('slot') for g in q['campaigns']]!=list(range(1,6))
        or any(len(g.get('media_filenames',[]))!=3 for g in q['campaigns'])
        or len({f for g in q['campaigns'] for f in g['media_filenames']})!=15
        or q.get('budget_usd_per_campaign')!='35'
        or q.get('currency')!='USD' or q.get('timezone')!='America/New_York'
        or cap.get('enabled') is not True or cap.get('account_id')!=TARGET
        or cap.get('authorized_by')!=CEO or cap.get('authority_message_id')!=p.get('authority_message_id')
        or cap.get('policy_source')!='data/ares/meta-ads/policies/eggbev03-same-account-replacement.json'
        or q['request_id'] not in cap.get('allowed_request_ids',[])
        or MODE not in cfg['accounts'][TARGET].get('supported_modes',[])):
        raise ValueError('same-account replacement request/capability is not admitted')
    if q.get('phase') in {'CANCELLED_BY_OPERATOR','SUPERSEDED_BY_OPERATOR'}:
        raise ValueError('cancelled request cannot execute')
    return p, grant


def validate_campaign_capability(c, account):
    cap = account.get('target_page_replacement',{})
    p = load(POLICY)
    matches = [(rid,g) for rid,g in p.get('requests',{}).items()
               if c.idempotency_key in {rid+'-'+str(i) for i in range(1,6)}]
    if len(matches)!=1:
        raise ValueError('campaign outside exact same-account request')
    rid,g = matches[0]
    q = load(ROOT/'data/ares/meta-ads/requests'/(rid+'.json'))
    admit(q, {'accounts':{TARGET:account}})
    if (c.account_id!=TARGET or c.source_campaign_id!=q['source_campaign_id']
        or len(c.ads)!=3 or c.campaign_create.get('daily_budget')!='3500'
        or str(c.adset_create.get('promoted_object',{}).get('page_id'))!=g['target_page_id']
        or [a.source_ad_id for a in c.ads]!=g['template_ad_ids']):
        raise ValueError('same-account source/Page/budget/slot scope changed')


def request_load(path):
    q = load(path)
    admit(q)
    return q


def runtime(runner, config):
    common = runner.module('same_account_replacement_common', ROOT/'scripts/ares-eggbev-roas-common.py')
    account = load(ROOT/f'data/ares/meta-ads/accounts/{TARGET}.json')['accounts'][0]
    meta,sb,token,_ = common.load_runtime_modules(account)
    return common,meta,sb,token


def discord_get(common,path):
    """Bounded retry of idempotent authority reads; never replay a mutation."""
    for attempt in range(4):
        code,body=common.discord_request('GET',path)
        if code not in {429,500,502,503,504} or attempt==3:return code,body
        delay=float(2**(attempt+1))
        if isinstance(body,dict) and 'retry_after' in body:
            try:delay=float(body['retry_after'])
            except (ValueError,TypeError):return code,body
            if not 0<=delay<=30:return code,body
            delay=max(0.05,delay)
        time.sleep(delay)
    raise AssertionError('unreachable GET retry state')


def live_request(q, common):
    from .eggbev_cross_account import verify_advertiser  # target03 credential check only
    p,g = admit(q)
    code,thread = discord_get(common,'/channels/'+q['source_thread_id'])
    if code!=200 or thread.get('parent_id')!=q['source_channel_id']:
        raise ValueError('independent request origin mismatch')
    observed={}
    mids=[q['source_message_id'],q['specification_message_id'],
          q['request_independence_authority_message_id'],q['standards_confirmation_message_id'],
          q['source_selection_authority_message_id'],p['authority_message_id']]
    for mid in mids:
        code,m=discord_get(common,f"/channels/{q['source_thread_id']}/messages/{mid}")
        if (code!=200 or m.get('id')!=mid or m.get('author',{}).get('id')!=CEO
            or m['author'].get('bot') or m.get('edited_timestamp')):
            raise ValueError('fresh request/technical authority unavailable')
        observed[mid]={'content_sha256':hashlib.sha256(m['content'].encode()).hexdigest(),'timestamp':m['timestamp']}
    if observed[p['authority_message_id']]['content_sha256']!=p['authority_content_sha256']:
        raise ValueError('technical authorization content changed')
    return observed


def fetch_all(meta, token, path, params):
    result=[];seen=set();after=None
    for _ in range(100):
        q=dict(params)
        if after:q['after']=after
        code,body,_=meta.graph_get(path,token,q)
        if code!=200 or not isinstance(body.get('data'),list):
            raise ValueError('scoped same-account read incomplete')
        result.extend(body['data']);paging=body.get('paging') or {}
        if not paging.get('next'):return result
        after=(paging.get('cursors') or {}).get('after')
        if not after or after in seen:raise ValueError('scoped pagination cursor invalid')
        seen.add(after)
    raise ValueError('scoped pagination bound exceeded')


def source_read(q,runner,common,meta,token,config):
    _,grant=admit(q,config)
    cid=q['source_campaign_id']
    code,c,_=meta.graph_get(cid,token,{'fields':'id,account_id,name,status,objective,buying_type,bid_strategy,daily_budget,lifetime_budget,special_ad_categories,special_ad_category_country'})
    if (code!=200 or c.get('account_id')!=TARGET or c.get('id')!=cid
        or c.get('name')!=q['source_campaign_name'] or c.get('status') in {'DELETED','ARCHIVED'}
        or c.get('lifetime_budget') not in {None,0,'0'}):
        raise ValueError('same-account source identity mismatch')
    sets=fetch_all(meta,token,cid+'/adsets',{'fields':'id,name,status,billing_event,optimization_goal,destination_type,targeting,promoted_object,attribution_spec,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities,bid_amount,bid_constraints,optimization_sub_event','limit':100})
    ads=fetch_all(meta,token,cid+'/ads',{'fields':'id,name,status,adset_id,source_ad_id,creative{id,object_story_spec,asset_feed_spec,url_tags,degrees_of_freedom_spec,contextual_multi_ads}','limit':100})
    if len(sets)!=1 or not ads or len({a['id'] for a in ads})!=len(ads) or any(a['adset_id']!=sets[0]['id'] for a in ads):
        raise ValueError('source hierarchy changed')
    byid={a['id']:a for a in ads};mapping=grant['template_ad_ids']
    if len(mapping)!=3 or not set(mapping)<=set(byid):raise ValueError('explicit source slot map unavailable')
    selected=[copy.deepcopy(byid[i]) for i in mapping]
    source={'campaign':copy.deepcopy(c),'adset':copy.deepcopy(sets[0]),'ads':selected,
            'all_ads':copy.deepcopy(ads),'technical_seed_ads':[],
            'source_selection':{'template_ad_ids':mapping,'output_count':3,'source_count':len(ads),
                                'mapping_authority':p_authority(q), 'source_objects_excluded_from_mutation':True}}
    runner.source_rematerialization(source,require_tracking=False)
    from .eggbev_cross_account import primary_text
    for ad in selected:primary_text(ad['creative'])
    return source


def p_authority(q):
    return admit(q)[0]['authority_message_id']


def page_read(q,source,meta,sb,token,path,**kwargs):
    from .eggbev_page_identity import resolve
    page=resolve(meta,sb,token,TARGET,q['target_page_token'],authority_path=POLICY,
                 ensure_pbia=False,request_path=path)
    _,grant=admit(q)
    if page['id']!=grant['target_page_id'] or page['name']!=q['target_page_name']:
        raise ValueError('requested target Page identity changed')
    return page


def naming_history(meta,token,cfg,q):
    from . import eggbev_creation_naming as naming
    from .eggbev_cross_account import reader
    with ExitStack() as stack:
        for aid in sorted(naming.load_policy()['account_ids']):stack.enter_context(reader(aid,cfg,q['request_id']))
        return naming.collect_history(meta,token)


def reconcile_target_media(q,home,selected,meta,token):
    from .eggbev_cross_account import MEDIA_RECONCILIATION_FIELDS
    identity=digest([{k:a.get(k) for k in ['asset_id','canonical_filename','clean_checksum','clean_md5','manager_media_folder_id']} for a in selected])
    path=home/'target-media-use-reconciliation.json'
    evidence=load(path) if path.exists() else {}
    if evidence and (evidence.get('request_id')!=q['request_id'] or evidence.get('selected_identity_sha256')!=identity):
        raise ValueError('media reconciliation identity drift')
    if evidence and (evidence.get('account_id')!=TARGET or evidence.get('fields')!=MEDIA_RECONCILIATION_FIELDS
                     or evidence.get('data_sha256')!=digest(evidence.get('data'))
                     or len({r['id'] for r in evidence['data']})!=len(evidence['data'])):
        raise ValueError('media reconciliation receipt integrity mismatch')
    if evidence.get('complete'):
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(evidence['completed_at'])).total_seconds()
        if 0<=age<=600 and evidence.get('data_sha256')==digest(evidence['data']):return evidence['data']
        evidence={}
    rows=evidence.get('data',[]);after=evidence.get('after');seen={r['id'] for r in rows}
    for _ in range(100):
        params={'fields':MEDIA_RECONCILIATION_FIELDS,'limit':100}
        if after:params['after']=after
        code,body,_=meta.graph_get('act_'+TARGET+'/ads',token,params)
        if code!=200:raise ValueError('media reconciliation deferred; saved cursor preserved, no upload/reservation replay')
        page=body.get('data')
        if not isinstance(page,list) or any(r.get('id') in seen for r in page):raise ValueError('media reconciliation pagination overlap')
        rows.extend(page);seen.update(r['id'] for r in page)
        pg=body.get('paging') or {};nxt=(pg.get('cursors') or {}).get('after') if pg.get('next') else None
        if pg.get('next') and (not nxt or nxt==after):raise ValueError('media reconciliation cursor invalid')
        after=nxt
        evidence={'request_id':q['request_id'],'account_id':TARGET,'selected_identity_sha256':identity,
                  'fields':MEDIA_RECONCILIATION_FIELDS,'data':rows,'after':after,'complete':not bool(after),
                  'data_sha256':digest(rows),'completed_at':datetime.now(timezone.utc).isoformat() if not after else None}
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
        if not after:return rows
    raise ValueError('media reconciliation pagination bound')


def select_media(q,runner,common,meta,token,home):
    import ares_manager_storage_standard as standard
    import ares_archive_storage as storage
    from .shein_media_handoff import _ops

    ops=_ops(ROOT);dt,_=ops.drive_runtime_token();folder=standard.destination('CC_US_EN','VID','g006','exclusive')
    standard.validate_folder(storage.drive(dt),folder,operation='CC_US_EN',fmt='VID',manager='g006',state='exclusive')
    inventory=[json.loads(s) for s in runner.INVENTORY.read_text().splitlines() if s.strip()]
    selected=[];files={}
    for name in [f for g in q['campaigns'] for f in g['media_filenames']]:
        matches=[r for r in inventory if r.get('canonical_filename')==name and r.get('manager_media_folder_id')==folder]
        if len(matches)!=1:raise ValueError('requested manager media missing or ambiguous')
        r=matches[0];storage.require_lineage_available(r);f=ops.drive_file_readback(dt,r['asset_drive_id'])
        if ((r.get('operation'),r.get('vertical'),r.get('country'),r.get('language'),r.get('format'))!=('CC_US_EN','CC','US','EN','VID')
            or r.get('metadata_clean') is not True or f.get('parents')!=[folder] or f.get('name')!=name
            or f.get('trashed') or f.get('md5Checksum')!=r.get('clean_md5')
            or '"reference_only": true' in json.dumps(f).lower()):raise ValueError('requested media bytes/lineage mismatch')
        if r.get('used_by') and r.get('used_by')!='ARES_IN_FLIGHT':raise ValueError('asset already used')
        previous=r.get('reservation_request_id')
        if previous and previous!=q['request_id']:
            record=load(ROOT/'data/ares/meta-ads/requests'/(previous+'.json'))
            from .operator_suspension import deny_replay
            if record.get('phase')!='CANCELLED_BY_OPERATOR':raise ValueError('another active reservation owns media')
            try:deny_replay(load(runner.CONFIG)['state_root'],TARGET,previous)
            except ValueError:pass
            else:raise ValueError('cancelled reservation is not fenced')
        selected.append(r);files[r['asset_id']]=f
    rows=reconcile_target_media(q,home,selected,meta,token)
    stems={Path(a['canonical_filename']).stem for a in selected}
    from .media_registry import MediaRegistry
    registry=MediaRegistry(load(runner.CONFIG)['media_registry'])
    for r in selected:
        vids=set()
        try:
            m=registry.require_ready(TARGET,r['asset_id'],r['clean_checksum'])
            vids={m.get('vertical_video_id'),m.get('square_video_id')}-{None}
        except ValueError:pass
        for a in rows:
            cr=a.get('creative') or {};observed={v.get('video_id') for v in (cr.get('asset_feed_spec') or {}).get('videos',[])}|{((cr.get('object_story_spec') or {}).get('video_data') or {}).get('video_id')}
            if any(st in a.get('name','') for st in stems) or vids&observed:
                raise ValueError('requested media has actual account ad use')
    return selected,files,dt,runner.module('same_replacement_creation',ROOT/'scripts/ares-eggbev-creation.py')


def reserve_media(selected,q,creation,runner,home):
    """Scoped reservation reassignment only after complete remote non-use proof."""
    from request_serialization import request_lock
    inventory=runner.INVENTORY
    with request_lock(inventory.parent/'inventory-locks',str(inventory.resolve())):
        rows=[json.loads(s) for s in inventory.read_text().splitlines() if s.strip()]
        byid={r['asset_id']:r for r in rows};changes=[]
        for expected in selected:
            r=byid[expected['asset_id']]
            for k in ['asset_drive_id','clean_checksum','used_by','reservation_request_id']:
                if r.get(k)!=expected.get(k):raise ValueError('reservation CAS drift')
            changes.append({'asset_id':r['asset_id'],'previous_request_id':r.get('reservation_request_id'),'request_id':q['request_id']})
        backup=home/'inventory-before-reserve.jsonl'
        if not backup.exists():backup.write_bytes(inventory.read_bytes())
        runner.save(home/'reservation-intent.json',{'request_id':q['request_id'],'changes':changes,'global_release':False})
        for change in changes:
            r=byid[change['asset_id']]
            r.update(reservation_status='RESERVADO_PELO_ARES_REQUEST',ares_eligible=False,
                     used_by='ARES_IN_FLIGHT',campaign_owner='Ares',reservation_request_id=q['request_id'],
                     reservation_authorized_by=q['requested_by'],reservation_audit=str(home/'reservation-intent.json'),
                     last_reconciled_at=datetime.now(timezone.utc).isoformat())
        creation.atomic_inventory(rows)
        runner.save(home/'reservation.json',{'request_id':q['request_id'],'changes':changes,'verified':True})


def build(q,source,page,selected,registry,allocation,runner,start):
    campaigns=[]
    if len(selected)!=15 or len(allocation['names'])!=5:raise ValueError('exact batch cardinality required')
    for i,g in enumerate(q['campaigns']):
        assets=selected[i*3:i*3+3]
        if [a['canonical_filename'] for a in assets]!=g['media_filenames']:raise ValueError('media order changed')
        sub={'request_id':q['request_id']+'-slot-'+str(i+1),'operation':OP,
             'daily_budget_usd':q['budget_usd_per_campaign'],'start_time':start,'copy':q['copy']}
        raw=runner.build(sub,source,page,assets,registry,{'names':[allocation['names'][i]]},
                         account_id=TARGET,mode=MODE,standard_tracking=True)['campaigns'][0]
        raw['idempotency_key']=q['request_id']+'-'+str(i+1);campaigns.append(raw)
    return {'schema_version':3,'request_id':q['request_id'],'operation':OP,'graph_version':'v26.0',
            'created_at':datetime.now(timezone.utc).isoformat(),'campaigns':campaigns}


def require_source_consistency(q,original,current,runner,home,approved_digest=None):
    if runner.source_comparison(original)==runner.source_comparison(current):return
    from . import native_thumbnail_equivalence as native
    context={'request_id':q['request_id'],'account_id':TARGET,'source_campaign_id':q['source_campaign_id']}
    if approved_digest:
        context['approved_digest']=approved_digest
        proof=native.compare(original,current,context=context,normalize=runner.source_comparison)
    else:
        context['preparation_snapshot_sha256']=native.digest(original)
        proof=native.compare_preparation(original,current,context=context,normalize=runner.source_comparison)
    runner.save(home/('source-current-'+digest(current)+'.json'),current)
    runner.save(home/('thumbnail-equivalence-'+digest(proof)+'.json'),proof)


def prepare(path,runner,confirm):
    if not confirm:raise ValueError('explicit prepare confirmation required')
    q=request_load(path);cfg=load(runner.CONFIG);home=home_for(q);home.mkdir(parents=True,exist_ok=True)
    from request_serialization import request_lock
    from .coordination import AccountWriterLeaseStore
    from .eggbev_cross_account import verify_advertiser,prepare_media
    from . import eggbev_creation_naming as naming
    from .media_registry import MediaRegistry
    from .prevalidation import prevalidate_payload,validate_account_policy,verify_prevalidation
    from .schema import Manifest
    from .engine import CampaignEngine
    with request_lock(Path(cfg['state_root'])/'request-locks',q['request_id'],blocking=False):
        leases=AccountWriterLeaseStore(cfg['state_root']);leases.claim(TARGET,q['request_id'],status='PREFLIGHT_ACTIVE')
        try:
            common,meta,sb,token=runtime(runner,cfg);binding=verify_advertiser(meta,token);human=live_request(q,common)
            source=source_read(q,runner,common,meta,token,cfg);page=page_read(q,source,meta,sb,token,path)
            if (home/'source-live.json').exists():
                original=load(home/'source-live.json');require_source_consistency(q,original,source,runner,home);source=original
            if (home/'summary.json').exists():
                summary=load(home/'summary.json');sealed=load(home/'manifest.json')
                if not verify_prevalidation(sealed) or summary['digest']!=sealed['prevalidation']['content_digest'] or summary['spec_sha256']!=digest(spec(q)):
                    raise ValueError('existing prepared seal changed')
                return summary
            runner.save(home/'source-live.json',source);runner.save(home/'target-page-live.json',page)
            runner.save(home/'advertiser-live.json',binding);runner.save(home/'request-live.json',human)
            selected,files,dt,creation=select_media(q,runner,common,meta,token,home)
            # Standard global naming reads are metadata-only, never campaign-source dependencies.
            history=naming_history(meta,token,cfg,q)
            allocation=naming.reserve(q['request_id'],TARGET,page['naming_identity'],5,history)
            reserve_media(selected,q,creation,runner,home);runner.save(home/'selected-assets.json',selected)
            prepare_media(q,selected,files,dt,creation,runner,meta,token,home)
            registry=MediaRegistry(cfg['media_registry']);start=creation.immediate_execute_start()
            draft=build(q,source,page,selected,registry,allocation,runner,start)
            sealed=prevalidate_payload(draft,registry);manifest=Manifest.from_dict(sealed);validate_account_policy(manifest,cfg)
            runner.save(home/'manifest.json',sealed)
            plan=CampaignEngine(cfg,transport_factory=lambda a:None,read_only=True).dry_run(manifest);runner.save(home/'plan.json',plan)
            summary={'phase':'AWAITING_FINAL_APPROVAL','request_id':q['request_id'],'spec_sha256':digest(spec(q)),
                     'source_account_id':TARGET,'target_account_id':TARGET,'source_campaign_id':q['source_campaign_id'],
                     'names':allocation['names'],'page':page,'start_time':start,'daily_budget_usd_per_campaign':'35',
                     'total_daily_budget_usd':'175','final_campaigns':5,'final_ads':15,'technical_paused_seeds':15,
                     'media':[a['canonical_filename'] for a in selected],'copy':q['copy'],
                     'json_messenger':'JSON-AGT incluído e conferido em todos os 15 anúncios',
                     'digest':sealed['prevalidation']['content_digest'],'campaign_writes':0,'source_unchanged':True,'final_ok_required':True}
            runner.save(home/'summary.json',summary);return summary
        finally:leases.release(TARGET,q['request_id'])


def authorized_final_approver(q, user_id):
    if user_id==CEO:return True
    op=load(ROOT/'data/ares/meta-ads/operations/Eggbev-US-CC-EN-03-BOT.json')
    authority=op.get('authority') or {}
    users=load(ROOT/'data/authorized-users.json').get('agents',{}).get('ares',{})
    return bool(q.get('account_id')==TARGET and authority.get('status')=='active'
                and authority.get('account_id')==TARGET
                and authority.get('source_thread_id')==q.get('source_thread_id')
                and authority.get('authorized_by_discord_id')==CEO
                and user_id==authority.get('authorized_manager_discord_id')
                and user_id in users.get('authorized_user_discord_ids',[])
                and {'campaign creation, clone and duplication requests',
                     'per-request campaign activation including explicit immediate start'}<=set(authority.get('scope',[])))


def final_approval(q,summary,common,message_id,approved_digest,*,return_proof=False):
    from .prevalidation import verify_prevalidation
    home=home_for(q);payload=load(home/'manifest.json');delivery=load(home/'summary-delivery.json')
    if (not verify_prevalidation(payload) or approved_digest!=summary['digest']
        or approved_digest!=payload['prevalidation']['content_digest'] or delivery.get('digest')!=approved_digest
        or summary.get('spec_sha256')!=digest(spec(q))):raise ValueError('final summary seal mismatch')
    def get(mid):
        code,m=discord_get(common,f"/channels/{q['source_thread_id']}/messages/{mid}")
        if code!=200 or m.get('id')!=mid or m.get('edited_timestamp'):raise ValueError('final summary/approval unavailable')
        return m
    sent=get(delivery['message_id']);ok=get(message_id)
    if (not sent.get('author',{}).get('bot') or sent['author'].get('id')!='1508864261504630925'
        or digest(sent.get('content',''))!=delivery.get('content_digest')
        or any(v not in sent.get('content','') for v in [*summary['names'],'JSON-AGT','PAUSED','15','35','175'])
        or not authorized_final_approver(q,ok.get('author',{}).get('id')) or ok['author'].get('bot')
        or ok.get('content','').strip().casefold() not in {'sim','ok','aprovado','pode executar','pode publicar'}
        or datetime.fromisoformat(ok['timestamp'])<=datetime.fromisoformat(sent['timestamp'])):
        raise ValueError('subsequent final summary approval required')
    ref=(ok.get('message_reference') or {}).get('message_id')
    if ref!=sent['id']:
        code,prior=discord_get(common,f"/channels/{q['source_thread_id']}/messages?before={message_id}&limit=1")
        if ref or code!=200 or len(prior)!=1 or prior[0].get('id')!=sent['id']:
            raise ValueError('approval is not linked to exact summary')
    proof={'request_id':q['request_id'],'digest':approved_digest,'approval_message_id':message_id,
           'verified_at_monotonic':time.monotonic()}
    effective=home/'effective-manifest.json'
    if effective.exists():
        derived=load(effective);compare_start_only(payload,derived)
        payload=derived
    return (payload,proof) if return_proof else payload


def compare_start_only(original,derived):
    from .prevalidation import verify_prevalidation
    if not verify_prevalidation(original) or not verify_prevalidation(derived):
        raise ValueError('start revision seal invalid')
    left=copy.deepcopy(original);right=copy.deepcopy(derived)
    for value in [left,right]:
        value.pop('prevalidation',None);value.pop('prevalidated',None)
        for c in value['campaigns']:c.pop('start_time',None)
    if left!=right:raise ValueError('start revision changed non-time fields')


def allows_elapsed_campaign(value):
    proof=CURRENT.get()
    return bool(proof and time.monotonic()-proof.get('verified_at_monotonic',0)<=120
                and value.get('account_id')==TARGET and value.get('mode')==MODE
                and digest(value) in proof.get('elapsed_campaign_digests',[]))


def require_execution(manifest,config):
    relevant=[c for c in manifest.campaigns if c.account_id==TARGET and c.mode==MODE]
    if not relevant:return
    q=load(ROOT/'data/ares/meta-ads/requests'/(manifest.request_id+'.json'));admit(q,config)
    proof=CURRENT.get()
    if not proof or proof.get('request_id')!=manifest.request_id or proof.get('digest')!=manifest.digest:
        raise ValueError('same-account Engine requires fresh exact final-approval context')
    if time.monotonic()-proof['verified_at_monotonic']>120:raise ValueError('final approval context expired')


def dispatch(args,runner):
    q=request_load(args.input)
    if args.command=='prepare':return prepare(args.input,runner,args.confirm_prepare)
    if args.command=='finalize':
        from .eggbev_cross_account_completion import finalize
        return finalize(args.input,runner,args.approved_digest,args.approval_message_id,adapter=sys.modules[__name__])
    if args.command!='execute' or not args.confirm_execute:raise ValueError('same-account command not admitted')
    cfg=load(runner.CONFIG);home=home_for(q)
    from request_serialization import request_lock
    from .coordination import AccountWriterLeaseStore
    from .eggbev_cross_account import verify_advertiser
    from .schema import Manifest
    from .prevalidation import validate_account_policy
    from .engine import CampaignEngine
    with request_lock(home,q['request_id'],blocking=False):
        leases=AccountWriterLeaseStore(cfg['state_root']);leases.claim(TARGET,q['request_id'],status='PREFLIGHT_ACTIVE')
        common,meta,sb,token=runtime(runner,cfg);verify_advertiser(meta,token);live_request(q,common)
        summary=load(home/'summary.json');payload,proof=final_approval(q,summary,common,args.approval_message_id,args.approved_digest,return_proof=True)
        current=source_read(q,runner,common,meta,token,cfg);original=load(home/'source-live.json')
        require_source_consistency(q,original,current,runner,home,args.approved_digest)
        page=page_read(q,current,meta,sb,token,args.input)
        if page!=load(home/'target-page-live.json'):raise ValueError('Page identity drift')
        from .media_registry import MediaRegistry
        from . import eggbev_creation_naming as naming
        selected=load(home/'selected-assets.json');allocation=naming.allocation(q['request_id'])
        starts={c['start_time'] for c in payload['campaigns']}
        if len(starts)!=1:raise ValueError('batch start mismatch')
        rebuilt=build(q,original,page,selected,MediaRegistry(cfg['media_registry']),allocation,runner,next(iter(starts)))
        if rebuilt['campaigns']!=payload['campaigns']:raise ValueError('compiled payload differs from approved source')
        naming.verify_live_reservation(q['request_id'],naming_history(meta,token,cfg,q))
        # Revalidate approval after reads. New starts are permitted only before any Engine state;
        # partial continuation keeps existing starts and receives an exact, ephemeral parse proof.
        payload,proof=final_approval(q,summary,common,args.approval_message_id,args.approved_digest,return_proof=True)
        checkpoint=Path(cfg['state_root'])/'checkpoints'/f"{q['request_id']}-{TARGET}.json"
        audit=Path(cfg['audit_root'])/(q['request_id']+'.json')
        if datetime.fromisoformat(payload['campaigns'][0]['start_time'])<=datetime.now(timezone.utc) and not checkpoint.exists() and not audit.exists():
            creation=runner.module('same_start_helpers',ROOT/'scripts/ares-eggbev-creation.py')
            original_payload=load(home/'manifest.json');new_payload=copy.deepcopy(payload)
            fresh_start=creation.immediate_execute_start()
            for c in new_payload['campaigns']:c['start_time']=fresh_start
            from .prevalidation import prevalidate_payload
            new_payload=prevalidate_payload(new_payload,MediaRegistry(cfg['media_registry']))
            compare_start_only(original_payload,new_payload)
            previous=home/'effective-manifest.json'
            if previous.exists():runner.save(home/('start-revision-'+digest(load(previous))+'.json'),load(previous))
            runner.save(previous,new_payload);payload=new_payload
        proof['elapsed_campaign_digests']=[digest(c) for c in payload['campaigns']]
        marker=CURRENT.set(proof)
        try:
            manifest=Manifest.from_dict(payload);validate_account_policy(manifest,cfg)
            proof['digest']=manifest.digest;CURRENT.set(proof)
            engine=CampaignEngine(cfg,transport_factory=runner.real_transport_factory(cfg,manifest))
            result=engine.execute(manifest);runner.save(home/'engine-result.json',result)
            return result
        finally:
            CURRENT.reset(marker)
            if not checkpoint.exists():leases.release(TARGET,q['request_id'])


# Shared readback primitives operate on target03 objects only, not source01.
from .eggbev_cross_account import readback_ops, verify_bundle, verify_advertiser
