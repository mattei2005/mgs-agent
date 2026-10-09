"""Engine v3 activation phase for globally QA-approved PAUSED SHEIN batches.

Only status writes to persisted IDs. No create/copy/upload/rename/budget changes.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .planning import BundlePlan
from .prevalidation import validate_account_policy, verify_prevalidation
from .quota import QuotaBlocked
from .transport import BatchOperation


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    os.chmod(temp,0o600);os.replace(temp,path)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def normalize(payload):
    out=copy.deepcopy(payload);out.pop('prevalidation',None);out.pop('prevalidated',None)
    for campaign in out['campaigns']:campaign['status']='PAUSED'
    return out


def statuses(tree):
    return [tree['campaign']]+tree['adsets']['data']+tree['ads']['data']


def same_time(a,b):
    return datetime.fromisoformat(a).astimezone(timezone.utc)==datetime.fromisoformat(b).astimezone(timezone.utc)


def stable_story(value):
    """Exclude expiring renderer thumbnails, never CTA links or media/post IDs."""
    if isinstance(value, dict):
        return {k: stable_story(v) for k, v in value.items() if k not in {'image_url', 'picture', 'thumbnail_url'}}
    if isinstance(value, list):
        return [stable_story(v) for v in value]
    return value


def validate_live(live, expected, spec):
    campaign=live['campaign'];old=expected['campaign']
    for field in ['id','account_id','name','daily_budget','bid_strategy']:
        if str(campaign.get(field))!=str(old.get(field)):raise ValueError('activation campaign identity/budget/bid drift')
    if campaign.get('account_id')!=spec.account_id or campaign.get('name')!=spec.name or not same_time(campaign['start_time'],spec.start_time):
        raise ValueError('activation account/name/schedule drift')
    for kind in ['adsets','ads']:
        rows=live[kind].get('data') or [];before=expected[kind].get('data') or []
        if live[kind].get('paging',{}).get('next') or {x['id'] for x in rows}!={x['id'] for x in before} or len(rows)!=len(before):
            raise ValueError('activation child IDs/count drift')
        old_by_id={r['id']:r for r in before}
        for row in rows:
            original=old_by_id[row['id']]
            for field in ['name','adset_id','source_ad_id','promoted_object']:
                if row.get(field)!=original.get(field):raise ValueError('activation child ownership/lineage/identity drift')
            if row.get('issues_info'):raise ValueError('activation child has platform issues')
            if kind=='adsets':
                if not same_time(row['start_time'],spec.start_time):raise ValueError('activation adset schedule drift')
                for field in ['bid_amount','bid_constraints']:
                    if field in original:
                        observed = str(row.get(field) or '0') if field=='bid_amount' else row.get(field) or {}
                        previous = str(original[field] or '0') if field=='bid_amount' else original[field] or {}
                        if observed != previous:raise ValueError('activation adset bid drift')
                if spec.bid_override:
                    if (str(row.get('bid_amount') or '0') != spec.adset_updates['bid_amount']
                            or (row.get('bid_constraints') or {}) != spec.adset_updates['bid_constraints']):
                        raise ValueError('activation requested bid delta mismatch')
            if kind=='ads':
                cr=row.get('creative') or {};ocr=original.get('creative') or {}
                for field in ['id','object_story_id','effective_object_story_id','url_tags','contextual_multi_ads']:
                    if cr.get(field)!=ocr.get(field):raise ValueError('activation creative/post/copy/tracking drift')
                if stable_story(cr.get('asset_feed_spec')) != stable_story(ocr.get('asset_feed_spec')) or cr.get('instagram_user_id') != ocr.get('instagram_user_id'):
                    raise ValueError('activation flexible media/Instagram drift')
                if stable_story(cr.get('object_story_spec')) != stable_story(ocr.get('object_story_spec')):
                    raise ValueError('activation creative media/copy/destination drift')
    if any(n.get('configured_status',n.get('status')) not in {'PAUSED','ACTIVE'} for n in statuses(live)):
        raise ValueError('activation target has an unexpected configured status')


def read_tree(engine,bundle,transport,cid,stage):
    operations=[BatchOperation('campaign','GET',cid+'?fields=id,account_id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time',kind='readback'),
        BatchOperation('adsets','GET',cid+'/adsets?fields=id,name,bid_amount,bid_constraints,bid_strategy,status,configured_status,start_time,promoted_object,targeting,attribution_spec,billing_event,optimization_goal,is_dynamic_creative&limit=50',kind='readback'),
        BatchOperation('ads','GET',cid+'/ads?fields=id,name,status,configured_status,adset_id,source_ad_id,issues_info,creative{id,object_story_id,effective_object_story_id,object_story_spec,asset_feed_spec,instagram_user_id,contextual_multi_ads,url_tags}&limit=50',kind='readback')]
    rows=engine._batch(bundle,transport,operations,stage)
    if len(rows)!=3 or any(r.code!=200 for r in rows):raise ValueError('activation readback incomplete')
    for row in rows:
        headers={str(h.get('name','')).lower():h.get('value') for h in row.headers}
        if headers:engine.quota.observe_headers((bundle.app_key,bundle.account_id),headers)
    return {r.name:r.body for r in rows}


def activate(engine,target,creation,proof):
    if engine.config.get('enabled') is not True or engine.config.get('write_enabled') is not True:
        raise ValueError('activation write gate disabled')
    if target.operation!='SHEIN-US-DIRECT' or len(target.campaigns)<1 or any(c.status!='ACTIVE' for c in target.campaigns):
        raise ValueError('activation phase restricted to authorized multi-campaign SHEIN ACTIVE requests')
    if any(c.status!='PAUSED' for c in creation.campaigns) or normalize(target.raw)!=normalize(creation.raw):
        raise ValueError('creation and target manifests differ beyond approved status')
    if not verify_prevalidation(target.raw) or not verify_prevalidation(creation.raw):raise ValueError('activation manifest seal invalid')
    validate_account_policy(target,engine.config);validate_account_policy(creation,engine.config)
    if proof.get('verified') is not True or proof.get('request_id')!=target.request_id or proof.get('creation_digest')!=creation.digest or proof.get('target_digest')!=target.digest:
        raise ValueError('global QA barrier missing or not bound to immutable request')
    trees=proof.get('trees') or []
    if len(trees)!=len(target.campaigns):raise ValueError('global QA tree count mismatch')
    if (engine.config.get('shein_media_qa') or {}).get('enabled') is True:
        for tree in trees:
            media = (proof.get('media_qa') or {}).get(tree['campaign']['id']) or {}
            ads = tree['ads']['data']
            if media.get('verified') is not True or set(media.get('ad_ids') or []) != {a['id'] for a in ads} or set(media.get('creative_ids') or []) != {a['creative']['id'] for a in ads}:
                raise ValueError('rendered media QA proof missing or identity mismatch')
    if any(n.get('configured_status',n.get('status'))!='PAUSED' for tree in trees for n in statuses(tree)):
        raise ValueError('global creation QA proof must show every node PAUSED')
    accounts={c.account_id for c in target.campaigns}
    if len(accounts)!=1 or len({c.app_key for c in target.campaigns})!=1:raise ValueError('activation request must remain account-scoped')
    aid=target.campaigns[0].account_id;app=target.campaigns[0].app_key;rid=target.request_id
    safe=''.join(ch if ch.isalnum() or ch in '_.-' else '-' for ch in rid)[:120]
    creation_audit=engine.audit_root/(safe+'.json')
    audit=json.loads(creation_audit.read_text())
    ids=[t['campaign']['id'] for t in trees]
    if audit.get('manifest_digest')!=creation.digest or audit.get('status')!='COMPLETE_PAUSED' or audit.get('result',{}).get('campaign_ids')!=ids:
        raise ValueError('creation audit does not prove complete PAUSED batch provenance')
    state_path=Path(engine.config['state_root'])/'activation'/(safe+'-'+aid+'.json')
    state=json.loads(state_path.read_text()) if state_path.exists() else {'schema_version':1,'request_id':rid,'attempt':0,'completed_ids':[]}
    descriptor=digest(proof)
    if state.get('proof_digest') not in {None,descriptor}:raise ValueError('activation request/proof changed during resume')
    state.update(proof_digest=descriptor,target_digest=target.digest,creation_digest=creation.digest,campaign_ids=ids,phase='ACTIVATION_PENDING',attempt=int(state.get('attempt',0))+1)
    atomic(state_path,state)
    engine.writer_leases.claim(aid,rid,status='ACTIVATION_PENDING')
    engine.quota.seed_access_tier((app,aid),engine.config['accounts'][aid].get('marketing_api_access_tier'),source='engine_activation_account_config')
    transport=engine.transport_factory(aid)
    sla = engine.config.get('shein_execution_sla') or {}
    def deadline_exceeded():
        if sla.get('enabled') is not True or len(target.campaigns) != int(sla.get('quantity', 1)):
            return False
        origin = proof.get('execution_started_at')
        if not origin: raise ValueError('SLA clock missing from original request proof')
        return (datetime.now(timezone.utc) - datetime.fromisoformat(origin).astimezone(timezone.utc)).total_seconds() > int(sla['target_seconds'])
    def hold():
        state.update(phase='E2E_TARGET_EXCEEDED',stage='activation_held',reason='complete QA exceeded original request E2E target; no late activation')
        atomic(state_path,state);engine.writer_leases.mark(aid,rid,'ACTIVATION_PENDING')
        return {'status':'E2E_TARGET_EXCEEDED','request_id':rid,'campaign_ids':ids,'target_seconds':sla['target_seconds'],'new_creation_replay':False}
    try:
        if deadline_exceeded(): return hold()
        final_trees=[]
        for index,(spec,tree) in enumerate(zip(target.campaigns,trees),1):
            bundle=BundlePlan(aid,app,index,(spec,),(),0)
            key=f'{rid}:{aid}:activation:{state["attempt"]}:{index}'
            points=6+2*len(statuses(tree))
            try:engine.quota.reserve((app,aid),points,request_id=key)
            except QuotaBlocked as exc:
                state.update(phase='ACTIVATION_DEFERRED',retry_after_seconds=exc.detail.get('retry_after_seconds',300));atomic(state_path,state)
                engine.writer_leases.mark(aid,rid,'ACTIVATION_DEFERRED')
                return {'status':'ACTIVATION_DEFERRED','request_id':rid,'campaign_ids':ids,'retry_after_seconds':state['retry_after_seconds']}
            cid=tree['campaign']['id'];live=read_tree(engine,bundle,transport,cid,'activation_pre_read');validate_live(live,tree,spec)
            missing=[n for n in statuses(live) if n.get('configured_status',n.get('status'))!='ACTIVE']
            if missing and spec.start_intent != 'IMMEDIATE' and datetime.fromisoformat(spec.start_time).astimezone(timezone.utc)<=datetime.now(timezone.utc):
                raise ValueError('approved start time elapsed; no silent immediate activation or reschedule')
            if deadline_exceeded(): return hold()
            children=[n for n in missing if n['id']!=cid]
            if children:
                state.update(stage='children_status_in_flight',pending_ids=[n['id'] for n in children]);atomic(state_path,state)
                engine._batch(bundle,transport,[BatchOperation('activate_'+n['id'],'POST',n['id'],body={'status':'ACTIVE'},kind='activation_status') for n in children],'activation_children')
            if any(n['id']==cid for n in missing):
                if deadline_exceeded(): return hold()
                state.update(stage='campaign_status_in_flight',pending_ids=[cid]);atomic(state_path,state)
                engine._batch(bundle,transport,[BatchOperation('activate_campaign','POST',cid,body={'status':'ACTIVE'},kind='activation_status')],'activation_campaign')
            final=read_tree(engine,bundle,transport,cid,'activation_readback');validate_live(final,tree,spec)
            if any(n.get('configured_status',n.get('status'))!='ACTIVE' for n in statuses(final)):
                raise ValueError('activation final configured status mismatch')
            final_trees.append(final)
            if cid not in state['completed_ids']:state['completed_ids'].append(cid)
            state.update(stage='tree_readback_complete',pending_ids=[]);atomic(state_path,state)
            engine.quota.complete((app,aid),key)
        state.update(phase='COMPLETE_FUTURE_ACTIVE',retry_after_seconds=0,stage='readback_complete',pending_ids=[]);atomic(state_path,state)
        engine.writer_leases.release(aid,rid)
        return {'status':'COMPLETE_FUTURE_ACTIVE','request_id':rid,'campaign_ids':ids,'creation_digest':creation.digest,'target_digest':target.digest,'activation_state':str(state_path),'trees':final_trees}
    except Exception as exc:
        state.update(phase='ACTIVATION_PENDING',last_error_type=type(exc).__name__);atomic(state_path,state)
        engine.writer_leases.mark(aid,rid,'ACTIVATION_PENDING')
        raise
