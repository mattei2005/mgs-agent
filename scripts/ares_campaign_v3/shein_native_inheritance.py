"""Gated native inheritance experiment; central Engine remains the only writer.

The sealed expected payload stays complete. Only the Ad Copies override is
reduced: unsupplied top-level creative fields are inherited by the native API.
This is not a standalone-creative omission or an opt-out/QA waiver.
"""
from __future__ import annotations
import copy
from decimal import Decimal

ROUTE = 'source_definition_native_inherit'
POLICY = 'source_definition_native_inheritance'
APPROVER = '344196393512075265'


def _policy(account):
    p=account.get(POLICY) or {}
    if (p.get('enabled') is not True or p.get('stage')!='CANARY_PAUSED_ONLY'
            or p.get('approved_by')!=APPROVER or not str(p.get('source_message_id','')).isdigit()
            or p.get('max_campaigns')!=1 or p.get('max_ads')!=2 or p.get('budget_minor')!=10000
            or not isinstance(p.get('request_ids'),list) or len(p['request_ids'])!=1
            or not all(isinstance(p.get(k),list) and p[k] for k in
                       ['source_campaign_ids','source_adset_ids','source_ad_ids'])):
        raise ValueError('native inheritance canary policy unavailable or invalid')
    return p


def selected_request(request, source, account):
    raw=account.get(POLICY) or {}
    if request.get('request_id') not in raw.get('request_ids',[]):
        return False
    p=_policy(account)
    if (account.get('operation')!='SHEIN-US-DIRECT'
            or request.get('mode','pure_clone')!='pure_clone' or request.get('status')!='PAUSED'
            or int(request.get('quantity',1))!=1 or request.get('authorized_by')!=APPROVER
            or Decimal(str(request['budget_usd']))*100!=p['budget_minor']
            or str(source['campaign']['id']) not in p['source_campaign_ids']
            or str(source['adset']['id']) not in p['source_adset_ids']
            or len(source['ads'])!=2
            or {str(a['id']) for a in source['ads']}!=set(p['source_ad_ids'])
            or request.get('preserve_posts') is True):
        raise ValueError('native inheritance canary immutable intent/source mismatch')
    return True


def require_shape(campaign):
    if campaign.creative_materialization_route!=ROUTE:
        return
    if campaign.mode!='pure_clone' or campaign.status!='PAUSED' or len(campaign.ads)!=2:
        raise ValueError('native inheritance is a two-ad PAUSED pure_clone canary only')
    for ad in campaign.ads:
        p=ad.creative_payload
        if (ad.media is not None or not ad.source_ad_id or p.get('object_story_id')
                or p.get('asset_feed_spec') or not p.get('object_story_spec',{}).get('page_id')
                or not p['object_story_spec'].get('video_data',{}).get('video_id')
                or 'url_tags' not in p
                or p.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{}).get('image_background_gen')!={'enroll_status':'OPT_IN'}):
            raise ValueError('native inheritance requires complete source video definition and background OPT_IN')


def validate_manifest(manifest, account):
    selected=[c for c in manifest.campaigns if c.creative_materialization_route==ROUTE]
    if not selected:
        return False
    p=_policy(account)
    if (manifest.operation!='SHEIN-US-DIRECT' or account.get('operation')!='SHEIN-US-DIRECT'
            or len(manifest.campaigns)!=1 or manifest.request_id not in p['request_ids']):
        raise ValueError('native inheritance manifest outside exact canary')
    c=selected[0];require_shape(c)
    if (c.idempotency_key!=manifest.request_id
            or c.source_campaign_id not in p['source_campaign_ids']
            or c.source_adset_id not in p['source_adset_ids']
            or {a.source_ad_id for a in c.ads}!=set(p['source_ad_ids'])
            or int(c.campaign_updates.get('daily_budget',0))!=p['budget_minor']):
        raise ValueError('native inheritance canary source/budget/slot mismatch')
    return True


def parameters(campaign, ad):
    from .shein_reference_destination import ROUTE as reference_route, parameters as reference_parameters
    if campaign.creative_materialization_route == reference_route:
        return reference_parameters(campaign, ad)
    if campaign.creative_materialization_route!=ROUTE:
        return copy.deepcopy(ad.creative_payload)
    require_shape(campaign)
    if ad not in campaign.ads:
        raise ValueError('native inheritance ad is not in approved campaign')
    # Preserve complete expectation in the manifest and QA. The native source
    # supplies enrollment, sourcing and contextual_multi_ads without re-opting in.
    result = {k:copy.deepcopy(ad.creative_payload[k]) for k in
              ['name','object_story_spec','url_tags'] if k in ad.creative_payload}
    # The omitted block inherited deprecated standard_enhancements (3858504).
    # This canary probes an empty transport block; full enrollment expectations
    # remain sealed and a changed/defaulted feature MUST still fail strict QA.
    result['degrees_of_freedom_spec'] = {}
    return result


def unmodified_control_body(adset_id):
    if not str(adset_id).isdigit():
        raise ValueError('native control requires exact numeric parent')
    return {'adset_id':str(adset_id),'status_option':'PAUSED',
            'rename_options':{'rename_strategy':'ONLY_TOP_LEVEL_RENAME',
                              'rename_suffix':' - ARES_NATIVE_CONTROL'}}


def verify_features(actual, expected):
    from .shein_reference import verify_degrees
    verify_degrees(actual.get('degrees_of_freedom_spec'),expected.get('degrees_of_freedom_spec'))


def probe_unmodified(engine, manifest, *, confirm_execute=False):
    """One durable, PAUSED no-override control in the existing canary shell.

    Not a production route: original UTMs intentionally remain untouched. The
    extra comparison ad is recorded separately and never counted as a final slot.
    An uncertain intent is read-only on resume, never a second POST.
    """
    import json
    from pathlib import Path
    from .engine import _atomic_json
    from .transport import BatchOperation, BatchTransportError
    from . import progress
    from .shein_single_clone import BASE
    from .shein_general import authorize
    if not confirm_execute or engine.config.get('enabled') is not True or engine.config.get('write_enabled') is not True:
        raise ValueError('native control requires explicit execution gates')
    account=manifest.campaigns[0].account_id
    validate_manifest(manifest,engine.config['accounts'][account])
    runner=json.loads((BASE/'data/ares/meta-ads/state/shein-campaigns/single-clone'/manifest.request_id/'state.json').read_text())
    profile=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles'][account]
    policy=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    profile['channel_authorization_policy']=policy['channel_authorization_policy']
    authorize(runner['request'],profile,force=True)
    path=Path(engine.config['state_root'])/'checkpoints'/(manifest.request_id+'-'+account+'.json')
    checkpoint=json.loads(path.read_text());records=checkpoint.get('bundles') or []
    if checkpoint.get('status')!='COMPLETE' or len(records)!=1 or records[0].get('sealed_manifest_digest')!=manifest.digest:
        raise ValueError('native control needs original complete canary checkpoint')
    record=records[0]
    if len(record.get('campaign_ids',[]))!=1 or len(record.get('adset_ids',[]))!=1 or len(record.get('ad_ids',[]))!=2:
        raise ValueError('native control confirmed shells/slots incomplete')
    cid=record['campaign_ids'][0];sid=record['adset_ids'][0]
    journal_path=path.with_name(manifest.request_id+'-'+account+'-native-control.json')
    if journal_path.exists():
        previous=json.loads(journal_path.read_text())
        if previous.get('manifest_digest')!=manifest.digest:
            raise ValueError('native control journal binding changed')
        return {**previous,'replayed':False,'meta_writes_this_call':0}
    bundle=engine.planner.build(manifest).lanes[account][0]
    engine.writer_leases.claim(account,manifest.request_id,status='IN_PROGRESS')
    try:
        engine.quota.reserve((bundle.app_key,account),12,request_id=manifest.request_id+':native-control')
        transport=engine.transport_factory(account)
        rows=engine._batch(bundle,transport,[
            BatchOperation('control_campaign','GET',cid+'?fields=id,account_id,status,daily_budget',kind='readback'),
            BatchOperation('control_set','GET',sid+'?fields=id,account_id,campaign_id,status',kind='readback'),
            BatchOperation('control_ads','GET',cid+'/ads?fields=id,status,adset_id,source_ad_id&limit=50',kind='readback')], 'native_control_preread')
        by={r.name:r.body for r in rows if r.code==200}
        if set(by)!={'control_campaign','control_set','control_ads'}:
            raise ValueError('native control pre-read incomplete')
        c=by['control_campaign'];st=by['control_set'];edge=by['control_ads']
        if (c.get('id')!=cid or c.get('account_id')!=account or c.get('status')!='PAUSED'
                or str(c.get('daily_budget'))!='10000' or st.get('id')!=sid or st.get('status')!='PAUSED'
                or st.get('campaign_id')!=cid or st.get('account_id')!=account
                or not isinstance(edge.get('data'),list) or edge.get('paging',{}).get('next')
                or {a['id'] for a in edge['data']}!=set(record['ad_ids'])
                or any(a.get('status')!='PAUSED' or a.get('adset_id')!=sid for a in edge['data'])):
            raise ValueError('native control requires exact PAUSED existing canary')
        journal={'request_id':manifest.request_id,'manifest_digest':manifest.digest,'campaign_id':cid,
                 'adset_id':sid,'baseline_ad_ids':record['ad_ids'],'status':'INTENT',
                 'source_ad_id':manifest.campaigns[0].ads[0].source_ad_id,
                 'tracking_changes':False,'diagnostic_control_only':True}
        _atomic_json(journal_path,journal)
        marker=progress.CURRENT.set((journal,lambda:_atomic_json(journal_path,journal)))
        try:
            try:
                result=engine._batch(bundle,transport,[BatchOperation('native_unmodified_control','POST',
                    journal['source_ad_id']+'/copies',body=unmodified_control_body(sid),kind='existing_post_ad_copy')],
                    'native_unmodified_control')[0]
            except BatchTransportError as exc:
                journal['status']='REJECTED'
                journal['errors']=[{'http':v.get('code'),'code':(v.get('error') or {}).get('code'),
                    'subcode':(v.get('error') or {}).get('error_subcode'),
                    'title':(v.get('error') or {}).get('error_user_title')} for v in exc.detail.get('children',[])]
                _atomic_json(journal_path,journal)
                return journal
            journal['probe_ad_id']=str(result.body['copied_ad_id']);journal['status']='CREATED_READBACK_PENDING'
            _atomic_json(journal_path,journal)
            rows=engine._batch(bundle,transport,[BatchOperation('native_control_readback','GET',
                journal['probe_ad_id']+'?fields=id,account_id,adset_id,status,source_ad_id,creative{id,object_story_spec,url_tags,degrees_of_freedom_spec}',kind='readback')],
                'native_control_readback')
            row=rows[0].body
            if (row.get('id')!=journal['probe_ad_id'] or row.get('status')!='PAUSED'
                    or row.get('account_id')!=account or row.get('adset_id')!=sid
                    or row.get('source_ad_id')!=journal['source_ad_id']):
                raise ValueError('native control ownership/status/lineage readback failed')
            journal['readback']={'id':row['id'],'status':row['status'],'creative_id':row['creative']['id'],
                'degrees_of_freedom_spec':row['creative'].get('degrees_of_freedom_spec')}
            journal['status']='CONTROL_COMPLETE_PAUSED';_atomic_json(journal_path,journal)
            return journal
        finally:
            progress.CURRENT.reset(marker)
    finally:
        engine.writer_leases.release(account,manifest.request_id)
