"""CEO copy-only policy. Resolve payloads, never mutate sources/sealed manifests.
Authority: context/meta-creative-copy-policy.md, message 1568722979569930414.
This is not request authorization, an enrollment omission waiver, or new-media policy.
"""
from __future__ import annotations
import copy
from dataclasses import replace
from .shein_continuation import content_digest

FEATURE='image_background_gen'
AUTHORITY='1568722979569930414'
CLONE_MODES=frozenset({'pure_clone','clone_prestaged','clone_page_switch'})


def effective(payload):
    out=copy.deepcopy(payload)
    features=out.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{})
    value=features.get(FEATURE)
    if value is None:return out
    if not isinstance(value,dict) or value.get('enroll_status') not in {'OPT_IN','OPT_OUT'}:
        raise ValueError('copy background policy requires known enrollment')
    if value['enroll_status']=='OPT_IN':
        features[FEATURE]={**value,'enroll_status':'OPT_OUT'}
    return out


def resolve_campaign(campaign):
    if campaign.mode not in CLONE_MODES:return campaign
    if not campaign.ads:
        raise ValueError('copy background policy requires explicit source creative slots; native deep-copy cannot prove feature preservation')
    return replace(campaign,ads=tuple(replace(ad,creative_payload=effective(ad.creative_payload)) for ad in campaign.ads))


def record_resolution(bundle,record):
    if bundle.campaigns[0].mode not in CLONE_MODES:return
    receipt={'policy':'meta-copy-image-background-opt-out','authority_message_id':AUTHORITY,
        'scope':'copy_only','feature':FEATURE,'enrollment':'OPT_OUT_if_present',
        'sealed_manifest_digest':record.get('sealed_manifest_digest'),
        'slots':[{'key':c.idempotency_key,'source_ad_id':a.source_ad_id,
                  'effective_payload_digest':content_digest(effective(a.creative_payload))}
                 for c in bundle.campaigns for a in c.ads]}
    previous=record.get('creative_copy_policy_resolution')
    if previous is not None and previous!=receipt:
        raise ValueError('copy background policy durable receipt changed')
    record['creative_copy_policy_resolution']=receipt


def verify_creative(actual,expected):
    from .shein_reference import verify_degrees
    wanted=effective(expected)
    # The permanent delta applies only when this resource is explicitly present.
    # Existing operation QA remains authoritative for payloads without it.
    if FEATURE in wanted.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{}):
        from .reviewed_copy_omissions import expected_degrees
        verify_degrees(actual.get('degrees_of_freedom_spec'),expected_degrees(actual,wanted))


def verify_record(bundle,record):
    if bundle.campaigns[0].mode not in CLONE_MODES:return
    rows={r['name']:r for r in record.get('readback_results',[])}
    for i,campaign in enumerate(bundle.campaigns,1):
        if not any(FEATURE in a.creative_payload.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{}) for a in campaign.ads):
            continue
        row=rows.get('readback_ads_'+str(i))
        if not row or row.get('code')!=200 or not isinstance(row.get('body'),dict):
            raise ValueError('copy policy missing exact ad readback')
        edge=row['body'];ads=edge.get('data')
        if not isinstance(ads,list) or len(ads)!=len(campaign.ads) or edge.get('paging',{}).get('next'):
            raise ValueError('copy policy ad readback cardinality/pagination mismatch')
        by_name={ad.get('name'):ad for ad in ads}
        if len(by_name)!=len(ads) or set(by_name)!={a.name for a in campaign.ads}:
            raise ValueError('copy policy ad slot identity mismatch')
        for expected in campaign.ads:
            actual=by_name[expected.name]
            if str(actual.get('source_ad_id'))!=str(expected.source_ad_id):
                raise ValueError('copy policy source lineage mismatch')
            verify_creative(actual.get('creative') or {},expected.creative_payload)
