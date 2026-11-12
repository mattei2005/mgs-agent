"""Manual-equivalent existing-creative reference canary; no creative mutation."""
from __future__ import annotations
import json
from pathlib import Path


def attach_plan(source_ads, manual_ads, target_ads, adset_id, *, manual_campaign_paused=False):
    if not all(isinstance(rows,list) and len(rows)==2 for rows in [source_ads,manual_ads,target_ads]):
        raise ValueError('reference control requires exact two-ad trees')
    source={a['id']:a for a in source_ads}
    manual={a.get('source_ad_id'):a for a in manual_ads}
    target={a.get('source_ad_id'):a for a in target_ads}
    if len(source)!=2 or set(manual)!=set(source) or set(target)!=set(source):
        raise ValueError('reference control lineage coverage mismatch')
    result=[]
    for sid,s in source.items():
        m=manual[sid];t=target[sid]
        manual_status_ok = m.get('status')=='PAUSED' or (manual_campaign_paused is True and m.get('status')=='ACTIVE')
        if (not manual_status_ok or t.get('status')!='PAUSED' or t.get('adset_id')!=adset_id
                or s['creative']['id']!=m['creative']['id']
                or s['creative'].get('degrees_of_freedom_spec')!=m['creative'].get('degrees_of_freedom_spec')):
            raise ValueError('reference control baseline/ownership/status changed')
        if t['creative']['id']!=s['creative']['id']:
            result.append({'ad_id':t['id'],'source_ad_id':sid,'old_creative_id':t['creative']['id'],
                'source_creative_id':s['creative']['id'],
                'body':{'creative':{'creative_id':s['creative']['id']},'status':'PAUSED'}})
    return result


def run(engine, manifest, *, confirm_execute=False):
    from .engine import _atomic_json
    from .transport import BatchOperation
    from . import progress
    from .shein_single_clone import BASE
    from .shein_general import authorize
    from .prevalidation import verify_prevalidation
    if not confirm_execute or not engine.config.get('enabled') or not engine.config.get('write_enabled'):
        raise ValueError('reference control explicit execute gates required')
    if not verify_prevalidation(manifest.raw):
        raise ValueError('reference control requires original sealed manifest')
    if len(manifest.campaigns)!=1:
        raise ValueError('reference control is one canary only')
    spec=manifest.campaigns[0];aid=spec.account_id
    account=engine.config['accounts'][aid];policy=account.get('source_definition_native_inheritance') or {}
    if (policy.get('reference_probe_enabled') is not True or policy.get('approved_by')!='344196393512075265'
            or manifest.request_id not in policy.get('request_ids',[]) or spec.idempotency_key!=manifest.request_id
            or manifest.operation!='SHEIN-US-DIRECT' or account.get('operation')!='SHEIN-US-DIRECT'
            or spec.mode!='pure_clone' or spec.status!='PAUSED'
            or spec.source_campaign_id not in policy.get('source_campaign_ids',[])
            or spec.source_adset_id not in policy.get('source_adset_ids',[])
            or {a.source_ad_id for a in spec.ads}!=set(policy.get('source_ad_ids',[]))):
        raise ValueError('reference control exact canary authority unavailable')
    runner=json.loads((BASE/'data/ares/meta-ads/state/shein-campaigns/single-clone'/manifest.request_id/'state.json').read_text())
    profile=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles'][aid]
    operation=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    profile['channel_authorization_policy']=operation['channel_authorization_policy'];authorize(runner['request'],profile,force=True)
    checkpoint_path=Path(engine.config['state_root'])/'checkpoints'/(manifest.request_id+'-'+aid+'.json')
    checkpoint=json.loads(checkpoint_path.read_text());bundles=checkpoint.get('bundles') or []
    if checkpoint.get('status')!='COMPLETE' or len(bundles)!=1 or bundles[0].get('sealed_manifest_digest')!=manifest.digest:
        raise ValueError('reference control creation receipt missing')
    b=bundles[0];cid=policy['reference_target_campaign_id'];manual_id=policy['manual_reference_campaign_id']
    if b.get('campaign_ids')!=[cid] or len(b.get('adset_ids',[]))!=1 or len(b.get('ad_ids',[]))!=2:
        raise ValueError('reference control canary IDs changed')
    adset_id=b['adset_ids'][0];journal_path=checkpoint_path.with_name(manifest.request_id+'-'+aid+'-native-reference.json')
    journal=json.loads(journal_path.read_text()) if journal_path.exists() else {'request_id':manifest.request_id,'manifest_digest':manifest.digest,'campaign_id':cid,'manual_campaign_id':manual_id,'attempts':[]}
    if journal.get('manifest_digest')!=manifest.digest or journal.get('manual_campaign_id')!=manual_id:
        raise ValueError('reference control journal mismatch')
    bundle=engine.planner.build(manifest).lanes[aid][0];engine.writer_leases.claim(aid,manifest.request_id,status='IN_PROGRESS')
    try:
        engine.quota.reserve((bundle.app_key,aid),16,request_id=manifest.request_id+':native-reference')
        transport=engine.transport_factory(aid)
        def read():
            ops=[BatchOperation('target_campaign','GET',cid+'?fields=id,account_id,status,daily_budget',kind='readback'),
                 BatchOperation('manual_campaign','GET',manual_id+'?fields=id,account_id,status',kind='readback'),
                 BatchOperation('target_set','GET',adset_id+'?fields=id,account_id,campaign_id,status',kind='readback')]
            for name,campaign_id in [('source',spec.source_campaign_id),('manual',manual_id),('target',cid)]:
                ops.append(BatchOperation(name+'_ads','GET',campaign_id+'/ads?fields=id,status,adset_id,source_ad_id,creative{id,effective_object_story_id,degrees_of_freedom_spec}&limit=50',kind='readback'))
            rows=engine._batch(bundle,transport,ops,'native_reference_readback');data={r.name:r.body for r in rows if r.code==200}
            if set(data)!={o.name for o in ops}:raise ValueError('reference control readback incomplete')
            for name in ['target_campaign','manual_campaign']:
                if data[name].get('account_id')!=aid or data[name].get('status')!='PAUSED':raise ValueError('reference parent must stay PAUSED')
            if str(data['target_campaign'].get('daily_budget'))!='10000' or data['target_set'].get('id')!=adset_id or data['target_set'].get('account_id')!=aid or data['target_set'].get('campaign_id')!=cid or data['target_set'].get('status')!='PAUSED':
                raise ValueError('reference control parent/budget changed')
            for name in ['source_ads','manual_ads','target_ads']:
                if not isinstance(data[name].get('data'),list) or data[name].get('paging',{}).get('next'):raise ValueError('reference ad edge incomplete')
            if {a['id'] for a in data['target_ads']['data']}!=set(b['ad_ids']):raise ValueError('reference target ad IDs changed')
            return data
        live=read();planned=attach_plan(live['source_ads']['data'],live['manual_ads']['data'],live['target_ads']['data'],adset_id,manual_campaign_paused=live['manual_campaign']['status']=='PAUSED')
        journal['attempts'].append({'updates':planned,'status':'INTENT'});_atomic_json(journal_path,journal)
        marker=progress.CURRENT.set((journal,lambda:_atomic_json(journal_path,journal)))
        try:
            if planned:
                engine._batch(bundle,transport,[BatchOperation('reference_attach_'+str(i),'POST',p['ad_id'],body=p['body'],kind='existing_post_ad_attach') for i,p in enumerate(planned,1)],'native_reference_attach')
            final=read()
            if attach_plan(final['source_ads']['data'],final['manual_ads']['data'],final['target_ads']['data'],adset_id,manual_campaign_paused=final['manual_campaign']['status']=='PAUSED'):
                raise ValueError('reference attachment not confirmed; preserve PAUSED')
            journal.update(status='REFERENCE_EQUIVALENCE_VERIFIED_PAUSED',meta_updates_this_call=len(planned),tracking_rematerialized=False,
                target_ads=[{'id':a['id'],'source_ad_id':a['source_ad_id'],'creative_id':a['creative']['id'],
                    'post_id':a['creative'].get('effective_object_story_id'),'feature_count':len(a['creative'].get('degrees_of_freedom_spec',{}).get('creative_features_spec',{})),
                    'background':a['creative'].get('degrees_of_freedom_spec',{}).get('creative_features_spec',{}).get('image_background_gen')} for a in final['target_ads']['data']])
            journal['attempts'][-1]['status']='READBACK_VERIFIED';_atomic_json(journal_path,journal);return journal
        finally:progress.CURRENT.reset(marker)
    finally:engine.writer_leases.release(aid,manifest.request_id)
