"""Same-slot two-phase recovery after explicit Meta story-spec rejection.
All operations pass through the central engine journal/transport and quota.
"""
from __future__ import annotations
import re
from .transport import BatchOperation
from .creative_media import creative_body, matches

def rejected_slots(record):
    result=set(record.get('prestaged_two_phase_slots') or [])
    for child in ((record.get('error') or {}).get('detail') or {}).get('children',[]):
        error=child.get('error') or {}
        m=re.fullmatch(r'(?:recovery_)?ad_copy_(\d+)_(\d+)',child.get('name') or '')
        if m and error.get('code')==100 and error.get('error_subcode')==1443048:
            result.add(m[1]+'.'+m[2])
    return result

def materialize(engine,bundle,transport,record,entries):
    if not entries:return {}
    record['prestaged_two_phase_slots']=sorted(set(record.get('prestaged_two_phase_slots') or [])|{f'{ci}.{ai}' for ci,ai,_,_,_ in entries})
    slots=record.get('confirmed_objects') or {};operations=[];resolved={};creatives={}
    for ci,ai,ad,setid,live in entries:
        key=f'{ci}.{ai}';creative_name=f'prestaged_fallback_creative_{ci}_{ai}'
        creative_id=(slots.get(creative_name) or {}).get('id')
        if creative_id:creatives[key]=str(creative_id)
        else:operations.append(BatchOperation(creative_name,'POST',f'act_{bundle.account_id}/adcreatives',body=creative_body(ad.creative_payload),kind='creative_create'))
        if live:resolved[(ci,ai)]=str(live['id'])
        else:
            # No creative override: copy lineage only; attach verified definition later.
            body={'adset_id':setid,'status_option':'PAUSED','rename_options':{'rename_strategy':'NO_RENAME'}}
            if ad.creative_payload.get('degrees_of_freedom_spec'):
                body['creative_parameters']={'degrees_of_freedom_spec':ad.creative_payload['degrees_of_freedom_spec']}
            operations.append(BatchOperation(f'recovery_ad_copy_{ci}_{ai}','POST',f'{ad.source_ad_id}/copies',body=body,kind='ad_copy_with_creative'))
    if operations:
        results=engine._batch(bundle,transport,operations,'prestaged_two_phase_materialize')
        for row in results:
            m=re.fullmatch(r'prestaged_fallback_creative_(\d+)_(\d+)',row.name)
            if m:creatives[m[1]+'.'+m[2]]=str(row.body['id'])
            else:
                m=re.fullmatch(r'recovery_ad_copy_(\d+)_(\d+)',row.name)
                if not m:raise ValueError('unrecognized prestaged two-phase child')
                resolved[(int(m[1]),int(m[2]))]=str(row.body['copied_ad_id'])
    checks=[BatchOperation(f'fallback_read_{ci}_{ai}','GET',creatives[f'{ci}.{ai}']+'?fields=id,account_id,name,object_story_spec,asset_feed_spec,url_tags,instagram_user_id,contextual_multi_ads',kind='readback') for ci,ai,_,_,_ in entries]
    observed=engine._batch(bundle,transport,checks,'prestaged_two_phase_creative_readback')
    byname={x.name:x.body for x in observed}
    for ci,ai,ad,_,_ in entries:
        row=byname[f'fallback_read_{ci}_{ai}']
        if str(row.get('account_id'))!=str(bundle.account_id) or not matches(row,ad.creative_payload):
            raise ValueError('prestaged fallback creative definition/account mismatch')
    attaches=[BatchOperation(f'prestaged_fallback_attach_{ci}_{ai}','POST',resolved[(ci,ai)],body={'creative':{'creative_id':creatives[f'{ci}.{ai}']},'name':ad.name,'status':'PAUSED'},kind='ad_update') for ci,ai,ad,_,_ in entries]
    engine._batch(bundle,transport,attaches,'prestaged_two_phase_attach')
    return resolved
