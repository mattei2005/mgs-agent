"""PAUSED canary: source creative reference plus explicit target destination.

Not a production capability until live readback proves both feature and tracking
parity. Never updates a shared AdCreative node. Full expectations remain sealed.
"""
import copy
from decimal import Decimal
ROUTE='source_reference_destination_canary'
POLICY='source_reference_destination_canary'


def selected(request,source,account):
    p=account.get(POLICY) or {}
    if request.get('request_id') not in p.get('request_ids',[]):return False
    if (p.get('enabled') is not True or p.get('approved_by')!='344196393512075265'
            or request.get('authorized_by')!='344196393512075265'
            or request.get('status')!='PAUSED' or request.get('mode','pure_clone')!='pure_clone'
            or int(request.get('quantity',1))!=1 or account.get('operation')!='SHEIN-US-DIRECT'
            or source['campaign']['id']!=p.get('source_campaign_id')
            or source['adset']['id']!=p.get('source_adset_id')
            or {a['id'] for a in source['ads']}!=set(p.get('source_ad_ids',[]))
            or len(source['ads'])!=2
            or Decimal(str(request['budget_usd']))*100!=Decimal(str(source['campaign']['daily_budget']))):
        raise ValueError('source-reference destination canary intent/source mismatch')
    return True


def bind(shell,source):
    shell['creative_materialization_route']=ROUTE
    ads={a['id']:a for a in source['ads']}
    for slot in shell['ads']:
        slot['creative_payload']['creative_id']=str(ads[slot['source_ad_id']]['creative']['id'])


def require_shape(campaign):
    if campaign.creative_materialization_route!=ROUTE:return
    if campaign.mode!='pure_clone' or campaign.status!='PAUSED' or len(campaign.ads)!=2:
        raise ValueError('source-reference destination canary must remain two-ad PAUSED pure_clone')
    for ad in campaign.ads:
        p=ad.creative_payload
        if (not str(p.get('creative_id','')).isdigit() or p.get('object_story_id') or p.get('asset_feed_spec')
                or not p.get('object_story_spec',{}).get('video_data',{}).get('video_id')
                or 'url_tags' not in p or ad.media is not None
                or p.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{}).get('image_background_gen')!={'enroll_status':'OPT_IN'}):
            raise ValueError('reference canary requires source ID, video, tracking and complete OPT_IN expectation')


def validate(manifest,account):
    if not any(c.creative_materialization_route==ROUTE for c in manifest.campaigns):return False
    p=account.get(POLICY) or {}
    if (p.get('enabled') is not True or p.get('approved_by')!='344196393512075265'
            or manifest.operation!='SHEIN-US-DIRECT' or account.get('operation')!='SHEIN-US-DIRECT'
            or len(manifest.campaigns)!=1 or manifest.request_id not in p.get('request_ids',[])):
        raise ValueError('reference destination capability not approved for this manifest')
    c=manifest.campaigns[0];require_shape(c)
    if (c.idempotency_key!=manifest.request_id or c.source_campaign_id!=p['source_campaign_id']
            or c.source_adset_id!=p['source_adset_id']
            or {a.source_ad_id for a in c.ads}!=set(p['source_ad_ids'])
            or int(c.campaign_updates.get('daily_budget',0))!=p['budget_minor']):
        raise ValueError('reference destination manifest scope changed')
    if {a.creative_payload['creative_id'] for a in c.ads}!=set(p['source_creative_ids']):
        raise ValueError('reference source creative identity mismatch')
    return True


def parameters(campaign,ad):
    require_shape(campaign)
    out={k:copy.deepcopy(ad.creative_payload[k]) for k in ['name','object_story_spec','url_tags']}
    out['degrees_of_freedom_spec']={}
    return out


def update_body(campaign,ad):
    out={'name':ad.name,'status':campaign.status}
    if campaign.creative_materialization_route==ROUTE:
        require_shape(campaign)
        out['creative']={k:copy.deepcopy(ad.creative_payload[k]) for k in
                         ['creative_id','name','object_story_spec','url_tags']}
    return out
