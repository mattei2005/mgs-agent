"""Target-Page replacement clone, gated per account; central Engine adapter.

Uses source-derived explicit shells, a fresh target-Page adset and PAUSED target
seed ads, followed by same-Page copies. Never copies or mutates a foreign-Page
adset/ad, deletes seeds, or interprets source_ad_id as social-proof preservation.
All mutations use Engine._batch and its durable intent/confirmed-object journal.
"""
from __future__ import annotations
import copy
import hashlib
import json
from .schema import ManifestError
from .transport import BatchOperation
from .planning import StagePlan
from . import progress

MODE = 'clone_target_prestaged'


def validate_shape(c):
    if not c.source_campaign_id or not c.source_adset_id or not c.adset_name:
        raise ManifestError('target clone requires exact source campaign/adset and target adset name')
    if not c.campaign_create or not c.adset_create or c.campaign_updates or c.adset_updates:
        raise ManifestError('target clone uses explicit source-derived create payloads, never shell updates')
    reserved={'id','name','status','start_time','campaign_id','adset_id','source_ad_id'}
    if reserved.intersection(c.campaign_create) or reserved.intersection(c.adset_create):
        raise ManifestError('target clone create payload contains engine-owned fields')
    if not 1 <= len(c.ads) <= 5 or any(a.media is None or not a.source_ad_id for a in c.ads):
        raise ManifestError('target clone requires one through five media and source reference slots')
    if not {'objective','buying_type','daily_budget','bid_strategy','special_ad_categories','special_ad_category_country'} <= set(c.campaign_create):
        raise ManifestError('target clone source-derived campaign settings incomplete')
    if not {'billing_event','optimization_goal','destination_type','targeting','promoted_object','attribution_spec','is_dynamic_creative'} <= set(c.adset_create):
        raise ManifestError('target clone source-derived adset settings incomplete')
    page=str(c.adset_create.get('promoted_object',{}).get('page_id') or '')
    if not page.isdigit() or any(str(a.creative_payload.get('object_story_spec',{}).get('page_id') or '') != page for a in c.ads):
        raise ManifestError('target clone Page must match every creative and promoted object')
    if any(not a.creative_payload.get('object_story_spec',{}).get('instagram_user_id') for a in c.ads):
        raise ManifestError('target clone requires target Page-backed Instagram identity')
    if c.creative_materialization_route != 'inline_copy':
        raise ManifestError('target clone does not accept another materialization route')


def validate_capability(c, account, operation):
    cap=account.get('target_page_replacement') or {}
    if (operation != 'Eggbev-US-CC-EN-BOT' or cap.get('enabled') is not True
            or cap.get('authorized_by') != '344196393512075265'
            or cap.get('authority_message_id') != '1569927267633602693'
            or cap.get('account_id') != c.account_id):
        raise ManifestError('target Page replacement capability not explicitly authorized for account')
    from .eggbev_create import messenger_welcome_message
    wanted=json.loads(messenger_welcome_message())
    for ad in c.ads:
        actual=ad.creative_payload.get('asset_feed_spec',{}).get('additional_data',{}).get('page_welcome_message')
        try:actual=json.loads(actual) if isinstance(actual,str) else actual
        except ValueError:actual=None
        if actual != wanted:
            raise ManifestError('target clone canonical JSON-AGT template mismatch')


def seed_name(c, ad, ai):
    marker=hashlib.sha256(c.idempotency_key.encode()).hexdigest()[:12]
    return f'__ARES_SEED__ {marker} {ai:02d} {ad.name}'


def stages(campaigns):
    phases={k:[] for k in ['campaign_create','adset_create','creative_create','target_seed_create','target_same_page_copy','target_ad_normalize','campaign_finalize']}
    for ci,c in enumerate(campaigns,1):
        act='act_'+c.account_id
        phases['campaign_create'].append(BatchOperation(f'campaign_create_{ci}','POST',act+'/campaigns',{**c.campaign_create,'name':c.name,'status':'PAUSED'},kind='campaign_create'))
        phases['adset_create'].append(BatchOperation(f'adset_create_{ci}','POST',act+'/adsets',{**c.adset_create,'name':c.adset_name,'campaign_id':f'{{campaign_id_{ci}}}','start_time':c.start_time,'status':'ACTIVE'},kind='adset_create'))
        for ai,a in enumerate(c.ads,1):
            phases['creative_create'].append(BatchOperation(f'creative_create_{ci}_{ai}','POST',act+'/adcreatives',a.creative_payload,kind='creative_create'))
            phases['target_seed_create'].append(BatchOperation(f'target_seed_create_{ci}_{ai}','POST',act+'/ads',{'name':seed_name(c,a,ai),'adset_id':f'{{adset_id_{ci}}}','creative':{'creative_id':f'{{creative_id_{ci}_{ai}}}'},'status':'PAUSED'},kind='ad_create'))
            phases['target_same_page_copy'].append(BatchOperation(f'target_same_page_copy_{ci}_{ai}','POST',f'{{seed_ad_id_{ci}_{ai}}}/copies',{'adset_id':f'{{adset_id_{ci}}}','creative_parameters':a.creative_payload,'status_option':'PAUSED','rename_options':{'rename_strategy':'NO_RENAME'}},kind='ad_copy_with_creative'))
            phases['target_ad_normalize'].append(BatchOperation(f'target_ad_normalize_{ci}_{ai}','POST',f'{{copied_ad_id_{ci}_{ai}}}',{'name':a.name,'status':c.status},kind='ad_name_update'))
        phases['campaign_finalize'].append(BatchOperation(f'campaign_finalize_{ci}','POST',f'{{campaign_id_{ci}}}',{'status':c.status},kind='campaign_finalize'))
    return tuple(StagePlan(k,tuple(v)) for k,v in phases.items())


def _resolve(value, ids):
    if isinstance(value,dict):return {k:_resolve(v,ids) for k,v in value.items()}
    if isinstance(value,list):return [_resolve(v,ids) for v in value]
    if isinstance(value,str):
        for k,v in ids.items():value=value.replace('{'+k+'}',str(v))
    return value


def _result_id(row):
    import re
    values={str(row[key]) for key in ['copied_ad_id','id'] if row.get(key)}
    if len(values)==1:
        value=values.pop()
        if re.fullmatch(r'[1-9][0-9]+',value):return value
    raise ValueError('target clone object response missing exact ID')


def _save():
    current=progress.CURRENT.get()
    if current:current[1]()


def _inventory(engine,bundle,transport,path,fields,stage):
    from urllib.parse import urlencode
    rows=[];after=None;seen=set()
    for i in range(100):
        params={'fields':fields,'limit':200}
        if after:params['after']=after
        body=engine._batch(bundle,transport,[BatchOperation(f'target_inventory_{stage}_{i}','GET',path+'?'+urlencode(params),kind='readback')],stage)[0].body
        if not isinstance(body.get('data'),list):raise ValueError('target recovery inventory invalid')
        rows.extend(body['data']);paging=body.get('paging') or {}
        if not paging.get('next'):return rows
        after=paging.get('cursors',{}).get('after')
        if not after or after in seen:raise ValueError('target recovery pagination invalid')
        seen.add(after)
    raise ValueError('target recovery pagination bound exceeded')


def _uncertain(record,name):
    for entry in record.get('write_journal',[]):
        if not any(o.get('name')==name for o in entry.get('operations',[])):continue
        if entry.get('state')=='CONFIRMED':
            # HTTP success without a usable object ID is still an unknown POST.
            matches=[r for r in entry.get('confirmed',[]) if r.get('name')==name]
            if len(matches)!=1:return True
            try:_result_id(matches[0].get('ids') or {})
            except ValueError:return True
            continue
        if entry.get('state') not in {'IN_FLIGHT','PARTIAL_OR_UNCERTAIN'}:return True
        if entry.get('state')=='IN_FLIGHT':return True
        failed=entry.get('failed_children')
        legacy=record.get('target_clone_legacy_failure_receipt') or {}
        if failed is None and legacy.get('intent_digest')==hashlib.sha256(json.dumps(entry,sort_keys=True).encode()).hexdigest():failed=legacy.get('children')
        # Older checkpoints stored only the last BatchTransportError. Bind it
        # to the last exact stage/intent; never use it to dismiss earlier doubt.
        if failed is None and entry is record.get('write_journal',[])[-1] and entry.get('stage')==record.get('error',{}).get('stage'):
            failed=record.get('error',{}).get('detail',{}).get('children',[])
        rows=[row for row in failed or [] if row.get('name')==name]
        def has_id(value):
            if isinstance(value,dict):return any((k in {'id','copied_ad_id','copied_campaign_id','copied_adset_id','ad_object_ids','ids'} and bool(v)) or has_id(v) for k,v in value.items())
            if isinstance(value,list):return any(has_id(v) for v in value)
            return False
        # Only a known parameter rejection is proven side-effect free here.
        # HTTP 5xx, timeout, missing/malformed responses and success without ID
        # stay uncertain even when the API labels the error transient.
        if len(rows)!=1 or rows[0].get('code')!=400 or (rows[0].get('error') or {}).get('code')!=100 or (rows[0].get('error') or {}).get('is_transient') is not False or has_id(rows[0]):return True
    return False


def reconcile_existing(engine,bundle,transport,record,require_shells=False):
    """Read full scoped hierarchy before the first recovery write; no new shell."""
    ids=record.setdefault('target_clone_ids',{})
    for ci,c in enumerate(bundle.campaigns,1):
        for name,slot in [(f'campaign_create_{ci}',f'campaign_id_{ci}'),(f'adset_create_{ci}',f'adset_id_{ci}')]+[(f'{op}_{ci}_{ai}',f'{key}_{ci}_{ai}') for ai,_ in enumerate(c.ads,1) for op,key in [('creative_create','creative_id'),('target_seed_create','seed_ad_id'),('target_same_page_copy','copied_ad_id')]]:
            if name in record.get('confirmed_objects',{}):
                observed=_result_id(record['confirmed_objects'][name])
                if slot in ids and ids[slot]!=observed:raise ValueError('persisted target IDs conflict; no recreation')
                ids[slot]=observed
        cid=ids.get(f'campaign_id_{ci}');sid=ids.get(f'adset_id_{ci}')
        if not cid:
            if require_shells:raise ValueError('elapsed continuation missing campaign; no new shell')
            continue
        fields='id,account_id,name,status,daily_budget,bid_strategy,objective,buying_type,special_ad_categories,special_ad_category_country'
        live=engine._batch(bundle,transport,[BatchOperation(f'target_resume_campaign_{ci}','GET',cid+'?fields='+fields,kind='readback')],'target_resume_hierarchy')[0].body
        if str(live.get('id'))!=cid or str(live.get('account_id'))!=c.account_id or live.get('name')!=c.name or live.get('status') not in {'PAUSED',c.status}:raise ValueError('target recovery campaign identity/status mismatch')
        from .prevalidation import _require_subset
        _require_subset(live,c.campaign_create,'existing target campaign')
        sets=_inventory(engine,bundle,transport,cid+'/adsets','id,name,campaign_id,status,start_time,billing_event,optimization_goal,destination_type,targeting,promoted_object,attribution_spec,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities,bid_amount,bid_constraints,optimization_sub_event','resume_adsets')
        if not sid:
            if require_shells:raise ValueError('elapsed continuation missing adset; no new shell')
            # An uncertain POST will be adopted only by its unique exact match.
            if sets and not _uncertain(record,f'adset_create_{ci}'):raise ValueError('unexpected target adset before missing create')
        else:
            if len(sets)!=1:raise ValueError('target recovery adset cardinality mismatch')
            adset=sets[0]
            from datetime import datetime
            if str(adset.get('id'))!=sid or str(adset.get('campaign_id'))!=cid or adset.get('name')!=c.adset_name or adset.get('status')!='ACTIVE' or datetime.fromisoformat(adset['start_time'])!=datetime.fromisoformat(c.start_time):raise ValueError('target recovery adset hierarchy/schedule mismatch')
            _require_subset(adset,c.adset_create,'existing target adset')
        ads=_inventory(engine,bundle,transport,cid+'/ads','id,name,adset_id,status,source_ad_id,creative{id,object_story_spec,url_tags}','resume_ads')
        known={v for k,v in ids.items() if k.startswith((f'seed_ad_id_{ci}_',f'copied_ad_id_{ci}_'))}
        extras={str(a['id']) for a in ads}-known
        # Extra uncertain children remain adoptable by the existing exact
        # inventory path, never as permission for a blind create.
        if extras and not any(_uncertain(record,f'{op}_{ci}_{ai}') for ai,_ in enumerate(c.ads,1) for op in ['target_seed_create','target_same_page_copy']):raise ValueError('unexpected target ads; no missing-only mutation')
        if not known.issubset({str(a['id']) for a in ads}):raise ValueError('known target ad missing; no recreation')
        for ai,a in enumerate(c.ads,1):
            for slot,is_seed in [('seed_ad_id',True),('copied_ad_id',False)]:
                ident=ids.get(f'{slot}_{ci}_{ai}')
                if not ident:continue
                row=next(x for x in ads if str(x['id'])==ident)
                if str(row.get('adset_id'))!=sid or (is_seed and (row.get('status')!='PAUSED' or str(row.get('creative',{}).get('id'))!=ids.get(f'creative_id_{ci}_{ai}'))) or (not is_seed and str(row.get('source_ad_id'))!=ids.get(f'seed_ad_id_{ci}_{ai}')):raise ValueError('target recovery seed/final hierarchy mismatch')
            creative_id=ids.get(f'creative_id_{ci}_{ai}')
            if creative_id:
                body=engine._batch(bundle,transport,[BatchOperation(f'target_resume_creative_{ci}_{ai}','GET',creative_id+'?fields=id,object_story_spec,asset_feed_spec,url_tags,degrees_of_freedom_spec,contextual_multi_ads',kind='readback')],'target_resume_known_creative')[0].body
                wanted=a.creative_payload
                if str(body.get('id'))!=creative_id:raise ValueError('known creative ID missing')
                for key in ['object_story_spec','url_tags']:_require_subset(body.get(key),wanted.get(key),'existing creative '+key)
                actual=body.get('asset_feed_spec') or {};expected=wanted.get('asset_feed_spec') or {}
                for key in ['bodies','titles','descriptions']:
                    if [x.get('text') for x in actual.get(key,[])]!=[x.get('text') for x in expected.get(key,[])]:raise ValueError('known creative copy drift')
                if [str(x.get('video_id')) for x in actual.get('videos',[])]!=[str(x.get('video_id')) for x in expected.get('videos',[])]:
                    # This is reuse of an already confirmed object, not new
                    # media acceptance. Meta may rematerialize variants even on
                    # creative_create. Preserve the observation for lineage QA;
                    # verify() below still requires exact media or independently
                    # proven lineage and contains the parent PAUSED on mismatch.
                    expected_labels={l['name'] for v in expected.get('videos',[]) for l in v.get('adlabels',[])}
                    observed_labels=[l['name'] for v in actual.get('videos',[]) for l in v.get('adlabels',[])]
                    if not expected_labels or len(actual.get('videos',[]))!=len(expected.get('videos',[])) or set(observed_labels)!=expected_labels or len(observed_labels)!=len(expected_labels):raise ValueError('known creative variant slots drift')
                    record.setdefault('target_clone_known_media_observed',{})[creative_id]={'expected_video_ids':[str(x['video_id']) for x in expected['videos']],'observed_video_ids':[str(x['video_id']) for x in actual['videos']],'lineage_qa_required':True,'media_equivalence_verified':False}
                if actual.get('call_to_action_types')!=expected.get('call_to_action_types'):raise ValueError('known creative CTA drift')
                def parsed(v):return json.loads(v) if isinstance(v,str) else v
                if parsed(actual.get('additional_data',{}).get('page_welcome_message'))!=parsed(expected.get('additional_data',{}).get('page_welcome_message')):raise ValueError('known creative JSON drift')
    return dict(ids)


def _adopt_uncertain(engine,bundle,transport,op,record):
    """Unknown POST is never replayed; recover only a unique live exact object."""
    if op.kind=='campaign_create':path='act_'+bundle.account_id+'/campaigns';fields='id,name,account_id';pred=lambda x:x.get('name')==op.body['name']
    elif op.kind=='adset_create':path=op.body['campaign_id']+'/adsets';fields='id,name,campaign_id';pred=lambda x:x.get('name')==op.body['name'] and str(x.get('campaign_id'))==op.body['campaign_id']
    elif op.kind=='creative_create':path='act_'+bundle.account_id+'/adcreatives';fields='id,name,object_story_spec,url_tags';pred=lambda x:x.get('name')==op.body.get('name') and x.get('url_tags')==op.body.get('url_tags') and x.get('object_story_spec',{}).get('page_id')==op.body.get('object_story_spec',{}).get('page_id')
    elif op.kind=='ad_create':path=op.body['adset_id']+'/ads';fields='id,name,adset_id,creative{id}';pred=lambda x:x.get('name')==op.body['name'] and str(x.get('creative',{}).get('id'))==op.body['creative']['creative_id']
    elif op.kind=='ad_copy_with_creative':path=op.body['adset_id']+'/ads';fields='id,source_ad_id,adset_id';pred=lambda x:str(x.get('source_ad_id'))==op.relative_url.split('/')[0]
    else:return None
    matches=[x for x in _inventory(engine,bundle,transport,path,fields,'target_uncertain_reconciliation') if pred(x)]
    if len(matches)!=1:
        raise ValueError('uncertain target mutation unresolved; no POST replay; retain request for convergence/reconciliation')
    return str(matches[0]['id'])


def run(engine,bundle,transport,record):
    """Same runner for fresh execution and recovery; journal-bound missing-only."""
    from dataclasses import replace
    ids=record.setdefault('target_clone_ids',{})
    completed=record.setdefault('target_clone_completed_steps',[])
    confirmed=record.setdefault('confirmed_objects',{})
    if record.get('write_journal'):
        last=record['write_journal'][-1];error=record.get('error') or {}
        if 'failed_children' not in last and last.get('stage')==error.get('stage') and error.get('type')=='BatchTransportError':
            record.setdefault('target_clone_legacy_failure_receipt',{'intent_digest':hashlib.sha256(json.dumps(last,sort_keys=True).encode()).hexdigest(),'children':copy.deepcopy(error.get('detail',{}).get('children',[]))})
    mapping={}
    for ci,c in enumerate(bundle.campaigns,1):
        mapping[f'campaign_create_{ci}']=f'campaign_id_{ci}'
        mapping[f'adset_create_{ci}']=f'adset_id_{ci}'
        for ai,_ in enumerate(c.ads,1):
            mapping[f'creative_create_{ci}_{ai}']=f'creative_id_{ci}_{ai}'
            mapping[f'target_seed_create_{ci}_{ai}']=f'seed_ad_id_{ci}_{ai}'
            mapping[f'target_same_page_copy_{ci}_{ai}']=f'copied_ad_id_{ci}_{ai}'
    for name,slot in mapping.items():
        if name in confirmed:
            value=_result_id(confirmed[name])
            if slot in ids and ids[slot]!=value:raise ValueError('persisted target IDs conflict; no recreation')
            ids[slot]=value
    recovering=bool(ids or record.get('write_journal'))
    # The sealed start may have elapsed since a successful shell write. Prove
    # identity/account/parent/Page/settings/children remotely; never move start.
    from datetime import datetime,timezone
    elapsed=any(c.status=='ACTIVE' and datetime.fromisoformat(c.start_time)<=datetime.now(timezone.utc) for c in bundle.campaigns)
    if recovering or elapsed:
        reconcile_existing(engine,bundle,transport,record,require_shells=elapsed)
    for stage in stages(bundle.campaigns):
        operations=[]
        for template in stage.operations:
            if template.name in mapping and mapping[template.name] in ids:continue
            if template.name in completed:continue
            op=replace(template,relative_url=_resolve(template.relative_url,ids),body=_resolve(template.body,ids))
            if '{campaign_id_' in op.relative_url or '{seed_ad_id_' in op.relative_url:raise ValueError('unresolved target clone dependency')
            if _uncertain(record,op.name) and op.name in mapping:
                ids[mapping[op.name]]=_adopt_uncertain(engine,bundle,transport,op,record);_save();continue
            operations.append(op)
        # Newly adopted IDs might be needed by following operations only, never siblings.
        if operations:
            timing,started=engine._timed_start();record.setdefault('timings',{})[stage.name]=timing
            results=engine._batch(bundle,transport,operations,stage.name)
            for row in results:
                if row.name in mapping:ids[mapping[row.name]]=_result_id(row.body)
                if row.name not in completed:completed.append(row.name)
            engine._timed_finish(timing,started);record['stage']=stage.name+'_complete';_save()
    campaign_ids=[ids[f'campaign_id_{ci}'] for ci in range(1,len(bundle.campaigns)+1)]
    record['campaign_ids']=campaign_ids;record['adset_ids']=[ids[f'adset_id_{ci}'] for ci in range(1,len(bundle.campaigns)+1)]
    record['ad_ids']=[ids[f'copied_ad_id_{ci}_{ai}'] for ci,c in enumerate(bundle.campaigns,1) for ai in range(1,len(c.ads)+1)]
    record['seed_ad_ids']=[ids[f'seed_ad_id_{ci}_{ai}'] for ci,c in enumerate(bundle.campaigns,1) for ai in range(1,len(c.ads)+1)]
    record['creative_ids']=[ids[f'creative_id_{ci}_{ai}'] for ci,c in enumerate(bundle.campaigns,1) for ai in range(1,len(c.ads)+1)]
    record['created_children']=len(record['ad_ids']);record['stage']='children_created_readback_pending';_save()
    results=engine._batch(bundle,transport,engine._readback_ops(campaign_ids),'consolidated_readback')
    record['readback_results']=[{'name':x.name,'code':x.code,'body':x.body} for x in results]
    try:
        verify(bundle,record)
    except Exception:
        # A semantic failure must not leave an unsafe future ACTIVE parent.
        engine._batch(bundle,transport,[BatchOperation(f'target_qa_hold_{i}','POST',cid,{'status':'PAUSED'},kind='campaign_finalize') for i,cid in enumerate(campaign_ids,1)],'target_semantic_failure_hold')
        for ci in range(1,len(campaign_ids)+1):
            if f'campaign_finalize_{ci}' in completed:completed.remove(f'campaign_finalize_{ci}')
        held=engine._batch(bundle,transport,[BatchOperation(f'target_hold_readback_{i}','GET',cid+'?fields=id,status',kind='readback') for i,cid in enumerate(campaign_ids,1)],'target_semantic_failure_hold_readback')
        if any(row.body.get('status')!='PAUSED' for row in held):raise ValueError('target semantic failure: PAUSED containment unconfirmed')
        record['semantic_hold']='PAUSED_confirmed';_save();raise
    _save();return campaign_ids


def verify(bundle,record):
    from .eggbev_create import messenger_welcome_message
    rows={x['name']:x['body'] for x in record['readback_results']}
    ids=record['target_clone_ids']
    for ci,c in enumerate(bundle.campaigns,1):
        live=rows[f'readback_campaign_{ci}'];sets=rows[f'readback_adsets_{ci}'];ads=rows[f'readback_ads_{ci}']
        if str(live.get('account_id'))!=c.account_id or live.get('name')!=c.name or str(live.get('daily_budget'))!=str(c.campaign_create['daily_budget']) or live.get('status')!=c.status or live.get('bid_strategy')!=c.campaign_create['bid_strategy']:raise ValueError('target campaign readback mismatch')
        if sets.get('paging',{}).get('next') or len(sets.get('data',[]))!=1:raise ValueError('target adset cardinality mismatch')
        adset=sets['data'][0]
        if str(adset.get('id'))!=ids[f'adset_id_{ci}'] or adset.get('promoted_object',{}).get('page_id')!=c.adset_create['promoted_object']['page_id'] or adset.get('name')!=c.adset_name or adset.get('status')!='ACTIVE':raise ValueError('target adset Page/name/status mismatch')
        from .prevalidation import _require_subset
        for key in ['promoted_object','targeting','attribution_spec','billing_event','optimization_goal','is_dynamic_creative']:
            _require_subset(adset.get(key),c.adset_create.get(key),key)
        from datetime import datetime
        if datetime.fromisoformat(adset['start_time'])!=datetime.fromisoformat(c.start_time):raise ValueError('target schedule mismatch')
        if ads.get('paging',{}).get('next') or len(ads.get('data',[]))!=2*len(c.ads):raise ValueError('target final/seed cardinality mismatch')
        byid={str(x['id']):x for x in ads['data']}
        for ai,a in enumerate(c.ads,1):
            seed=byid[ids[f'seed_ad_id_{ci}_{ai}']];final=byid[ids[f'copied_ad_id_{ci}_{ai}']]
            if seed.get('status')!='PAUSED' or final.get('status')!=c.status or final.get('name')!=a.name or str(final.get('source_ad_id'))!=str(seed['id']):raise ValueError('target same-Page lineage or seed status mismatch')
            creative=final.get('creative') or {};wanted=a.creative_payload
            if creative.get('object_story_spec',{}).get('page_id')!=wanted['object_story_spec']['page_id'] or creative.get('url_tags')!=wanted['url_tags']:raise ValueError('target creative Page/tracking mismatch')
            actual=creative.get('asset_feed_spec') or {};expected=wanted.get('asset_feed_spec') or {}
            for key in ['bodies','titles','descriptions']:
                if [x.get('text') for x in actual.get(key,[])] != [x.get('text') for x in expected.get(key,[])]:raise ValueError('target literal copy readback mismatch')
            if actual.get('call_to_action_types')!=expected.get('call_to_action_types'):raise ValueError('target CTA mismatch')
            from .shein_reference import verify_degrees
            verify_degrees(creative.get('degrees_of_freedom_spec'),wanted.get('degrees_of_freedom_spec'))
            # Same-Page copies may rematerialize IDs; direct media bijection is a
            # separate postprocess gate, never silently passed as equality.
            if [x.get('video_id') for x in actual.get('videos',[])] != [x.get('video_id') for x in expected.get('videos',[])]:
                raise ValueError('target video IDs rematerialized; require lineage media reconciliation before completion')
            installed=actual.get('additional_data',{}).get('page_welcome_message')
            if (json.loads(installed) if isinstance(installed,str) else installed) != json.loads(messenger_welcome_message()):
                raise ValueError('target installed JSON-AGT differs from canonical file')
