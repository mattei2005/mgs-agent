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
    if campaign.creative_materialization_route!=ROUTE:
        return copy.deepcopy(ad.creative_payload)
    require_shape(campaign)
    if ad not in campaign.ads:
        raise ValueError('native inheritance ad is not in approved campaign')
    # Preserve complete expectation in the manifest and QA. The native source
    # supplies enrollment, sourcing and contextual_multi_ads without re-opting in.
    return {k:copy.deepcopy(ad.creative_payload[k]) for k in
            ['name','object_story_spec','url_tags'] if k in ad.creative_payload}
