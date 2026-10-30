"""SHEIN static sourcing, including audited effective-payload recovery.
Never rewrites a sealed manifest/digest. Uses only the central journal/transport.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
from dataclasses import replace
from . import progress
from .transport import BatchOperation

RECIPE = 'shein-static-image-sourcing-v1'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def sourcing(payload):
    story = payload.get('object_story_spec') or {}
    ld = story.get('link_data') or {}
    if (not ld.get('image_hash') or story.get('video_data') or payload.get('asset_feed_spec')
            or payload.get('object_story_id')):
        raise ValueError('static sourcing requires an unambiguous image definition')
    result = {'images': [{'hash': ld['image_hash'], 'source': 'multi_media', 'opt_in_status': 'opt_in'}],
              'titles': [{'text': ld['name']}], 'bodies': [{'text': ld['message']}]}
    if ld.get('description'):
        result['descriptions'] = [{'text': ld['description']}]
    return result

def valid_observed(actual, expected):
    """Reject inherited video/related/extra images and copy substitutions."""
    spec = actual.get('media_sourcing_spec')
    if spec is None:
        return expected.get('media_sourcing_spec') is None
    # A pure clone may preserve a legacy text-only sourcing definition.
    # Do not impose the new-media image recipe on an unchanged source;
    # require the entire approved text package verbatim, with no extra media.
    expected_spec = expected.get('media_sourcing_spec')
    if (isinstance(expected_spec, dict) and expected_spec
            and set(expected_spec) <= {'titles', 'bodies', 'descriptions'}):
        return spec == expected_spec
    wanted = sourcing(expected)
    if not isinstance(spec, dict) or set(spec) - set(wanted):
        return False
    images = spec.get('images')
    if not isinstance(images, list) or len(images) != 1:
        return False
    row = images[0]
    if not isinstance(row, dict) or row.get('hash') != wanted['images'][0]['hash']:
        return False
    if row.get('source') != 'multi_media' or row.get('opt_in_status') != 'opt_in':
        return False
    # Unrequested customization can override literal text, destination or crops.
    if set(row) - {'hash','source','opt_in_status','id'}:
        return False
    return all(spec.get(k) == v for k,v in wanted.items() if k != 'images')

def effective(payload):
    out = copy.deepcopy(payload)
    wanted = sourcing(out)
    if 'media_sourcing_spec' in out and out['media_sourcing_spec'] != wanted:
        raise ValueError('static sourcing is not exactly the approved single-image definition')
    out['media_sourcing_spec'] = wanted
    return out

def legacy_count(campaign):
    return sum(ad.media is not None and ad.media.media_type == 'image'
               and 'media_sourcing_spec' not in ad.creative_payload for ad in campaign.ads)

def resolve_operations(engine, bundle, transport, record, operations):
    """Add missing sourcing only after fresh zero-ad readback, sealed slot binding
    and durable immutable resolution receipt. Never edits existing live ads.
    """
    operation = (engine.config.get('accounts', {}).get(bundle.account_id) or {}).get('operation')
    if operation != 'SHEIN-US-DIRECT':
        return operations
    changes=[]
    for index,op in enumerate(operations):
        payload = (op.body or {}).get('creative_parameters') or {}
        if not ((payload.get('object_story_spec') or {}).get('link_data') or {}).get('image_hash'):
            continue
        m = re.fullmatch(r'(?:recovery_)?ad_copy_(\d+)_(\d+)', op.name)
        if not m:
            raise ValueError('unbound image sourcing operation')
        ci,ai = map(int,m.groups())
        if not 1 <= ci <= len(bundle.campaigns) or not 1 <= ai <= len(bundle.campaigns[ci-1].ads):
            raise ValueError('image sourcing slot out of range')
        campaign=bundle.campaigns[ci-1];ad=campaign.ads[ai-1]
        if (campaign.mode != 'clone_prestaged' or campaign.status != 'PAUSED'
                or campaign.account_id != bundle.account_id or ad.media is None
                or ad.media.media_type != 'image' or ad.media.image_hash != payload['object_story_spec']['link_data']['image_hash']
                or payload != ad.creative_payload or op.method != 'POST'
                or op.relative_url != f'{ad.source_ad_id}/copies'):
            raise ValueError('image sourcing scope/media/payload mismatch')
        resolved=effective(payload)
        if resolved == payload:
            continue
        changes.append((index,op,ci,ai,campaign,ad,resolved))
    if not changes:
        return operations
    current=progress.CURRENT.get()
    if current is None or current[0] is not record:
        raise ValueError('image sourcing requires the durable central bundle journal')
    cids=record.get('campaign_ids') or [];sids=record.get('adset_ids') or []
    if len(cids)!=len(bundle.campaigns) or len(sids)!=len(bundle.campaigns):
        raise ValueError('image sourcing shell IDs missing')
    if (not re.fullmatch('[0-9a-f]{64}', record.get('sealed_manifest_digest') or '')
            or record.get('idempotency_keys') != [c.idempotency_key for c in bundle.campaigns]):
        raise ValueError('image sourcing sealed manifest/slot identity missing')
    for _,op,ci,_,_,_,_ in changes:
        if str(op.body.get('adset_id')) != str(sids[ci-1]) or op.body.get('status_option') != 'PAUSED':
            raise ValueError('image sourcing mutation parent/status mismatch')
    affected=sorted({x[2] for x in changes});reads=[]
    for ci in affected:
        cid,sid=str(cids[ci-1]),str(sids[ci-1])
        reads.extend([
            BatchOperation(f'image_sourcing_campaign_{ci}','GET',cid+'?fields=id,account_id,status',kind='readback'),
            BatchOperation(f'image_sourcing_adset_{ci}','GET',sid+'?fields=id,account_id,campaign_id,status',kind='readback'),
            BatchOperation(f'image_sourcing_ads_{ci}','GET',cid+'/ads?fields=id,adset_id,status&limit=50',kind='readback')])
    rows=engine._batch(bundle,transport,reads,'image_sourcing_zero_ads_readback')
    if len(rows)!=len(reads) or len({r.name for r in rows})!=len(reads) or any(r.code!=200 for r in rows):
        raise ValueError('image sourcing readback incomplete')
    observed={r.name:r.body for r in rows};proof={}
    for ci in affected:
        c=observed[f'image_sourcing_campaign_{ci}'];s=observed[f'image_sourcing_adset_{ci}'];a=observed[f'image_sourcing_ads_{ci}']
        if (str(c.get('id'))!=str(cids[ci-1]) or str(c.get('account_id'))!=bundle.account_id or c.get('status')!='PAUSED'
                or str(s.get('id'))!=str(sids[ci-1]) or str(s.get('campaign_id'))!=str(cids[ci-1])
                or str(s.get('account_id'))!=bundle.account_id or s.get('status')!='PAUSED'
                or a.get('data') != [] or a.get('paging',{}).get('next')):
            raise ValueError('image sourcing requires exact PAUSED shells and complete zero ads')
        proof[ci]=digest({'campaign':c,'adset':s,'ads':{'data':[]}})
    output=list(operations);pending={}
    for index,op,ci,ai,campaign,ad,resolved in changes:
        key=f'{ci}.{ai}'
        receipt={'recipe':RECIPE,'account_id':bundle.account_id,'bundle_index':bundle.index,
                 'sealed_manifest_digest':record['sealed_manifest_digest'],
                 'idempotency_key':campaign.idempotency_key,'campaign_id':str(cids[ci-1]),
                 'adset_id':str(sids[ci-1]),'source_ad_id':str(ad.source_ad_id),'slot':key,
                 'asset_id':ad.media.asset_id,'checksum':ad.media.checksum,'image_hash':ad.media.image_hash,
                 'sealed_creative_digest':digest(ad.creative_payload),'effective_creative_digest':digest(resolved),
                 'sourcing':resolved['media_sourcing_spec'],'zero_ads_proof_digest':proof[ci]}
        previous=(record.get('image_sourcing_resolutions') or {}).get(key)
        if previous is not None and previous != receipt:
            raise ValueError('immutable image sourcing resolution changed')
        pending[key]=receipt
        output[index]=replace(op,body={**op.body,'creative_parameters':resolved})
    record.setdefault('image_sourcing_resolutions',{}).update(pending)
    if record.get('error'):
        record.setdefault('image_sourcing_original_error',copy.deepcopy(record['error']))
    current[1]() # fsync checkpoint BEFORE any modified mutation enters transport
    return output
