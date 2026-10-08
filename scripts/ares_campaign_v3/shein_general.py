"""SHEIN account-scoped manifest compiler. No API mutations and no new writer."""
from __future__ import annotations
import copy
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse
from zoneinfo import ZoneInfo
from .shein import _individual_dof, _campaign_create, _adset_create


def authorize(request, profile):
    actor = str(request.get('authorized_by') or '')
    if actor == '344196393512075265':
        return
    if actor != str(profile.get('manager_discord_id')):
        raise ValueError('requester is not the account-bound manager')
    if str(request.get('source_channel_id') or '') != str(profile.get('channel_id')):
        raise ValueError('manager request must originate in its canonical parent channel')


def build(request, source, number, account_config):
    p = account_config['shein_profile']
    authorize(request, p)
    aid = str(p['account_id'])
    if request['account'] not in {aid, p['account_name']} or source['campaign'].get('account_id') != aid:
        raise ValueError('account/source binding mismatch')
    mode = request.get('mode', 'pure_clone')
    if mode not in {'pure_clone', 'clone_prestaged', 'from_zero_prestaged'}:
        raise ValueError('unsupported SHEIN mode')
    if source['campaign'].get('objective') != 'OUTCOME_SALES' or source['adset'].get('optimization_goal') != 'OFFSITE_CONVERSIONS' or source['adset'].get('promoted_object', {}).get('custom_event_type') != 'ADD_TO_WISHLIST':
        raise ValueError('source fixed SHEIN event mismatch')
    if request.get('status') not in {'PAUSED', 'ACTIVE'}:
        raise ValueError('explicit delivery status required')
    start = datetime.fromisoformat(request['start_time']).astimezone(ZoneInfo(p['timezone']))
    sn = int(request['source_number'])
    old = p['tracking_prefix'] + f'c{sn:03d}'
    new = p['tracking_prefix'] + f'c{number:03d}'
    campaign = source['campaign']
    if not re.match(r'^' + str(sn) + r'\s*-', campaign['name']) or '(' + old + ')' not in campaign['name']:
        raise ValueError('source numbering/tracking prefix mismatch')
    if 'US-' + p['language'] not in campaign['name']:
        raise ValueError('source language differs from account')
    if old + 'g01' not in source['adset']['name']:
        raise ValueError('source adset token mismatch')
    name = re.sub(r'\s+COPY\s+C\d+\s*$', '', campaign['name'])
    name = re.sub(r'^' + str(sn) + r'\b', str(number), name).replace(old, new)
    name = re.sub(r'\s+\d{2}/\d{2}(?=\s|$)', '', name)
    name = name.replace('(' + new + ')', '(' + new + ') ' + start.strftime('%d/%m'))
    if mode == 'pure_clone':
        name += f' COPY C{sn}'
    elif request.get('product_label'):
        name = f'{number} - {request["product_label"]} - US-{p["language"]} ({new}) {start:%d/%m} event_add_to_wishlist'
    source_ads = sorted(source['ads'], key=lambda a: str(a.get('name', '')))
    if not 1 <= len(source_ads) <= 5:
        raise ValueError('source requires 1..5 ads')
    source_data = []
    for ad in source_ads:
        cr = ad.get('creative') or {}
        story = cr.get('object_story_spec') or ad.get('_reference_story') or {}
        media = story.get('video_data') or story.get('link_data') or {}
        link = (media.get('call_to_action') or {}).get('value', {}).get('link') or media.get('link')
        if not link or link.split('?')[0] != p['destination_base']:
            raise ValueError('source destination differs from approved account profile')
        params = dict(parse_qsl(urlparse(link).query)); params.update(dict(parse_qsl(cr.get('url_tags') or '')))
        if params.get('utm_medium') != p['utm_medium'] or params.get('utm_campaign') != old or params.get('utm_adgroup') != old + 'g01':
            raise ValueError('source effective tracking mismatch')
        if story.get('page_id') != p['page_id'] or not cr.get('effective_object_story_id', '').startswith(p['page_id'] + '_') or ad.get('adset_id') != source['adset']['id']:
            raise ValueError('Page/adset/post lineage mismatch')
        tags = dict(parse_qsl(cr.get('url_tags') or ''))
        tags.update(utm_source='facebook', utm_medium=p['utm_medium'], utm_campaign=new, utm_adgroup=new + 'g01')
        source_data.append((ad, cr, story, media, urlencode(tags)))
    ads = []
    if mode == 'pure_clone':
        for ad, cr, story, media, tags in source_data:
            ads.append({'name': ad['name'], 'source_ad_id': str(ad['id']), 'creative_payload': {
                'name': f'SHEIN {p["manager_code"]} C{number} {ad["name"]} COPY C{sn}',
                'object_story_id': cr['effective_object_story_id'], 'url_tags': tags,
                'degrees_of_freedom_spec': _individual_dof(cr)}})
    else:
        assets = request.get('_resolved_assets') or []
        if (mode == 'from_zero_prestaged' and len(assets) != 3) or not 1 <= len(assets) <= 5:
            raise ValueError('from-zero needs three assets; new-media clone needs 1..5')
        if len({a['asset_id'] for a in assets}) != len(assets):
            raise ValueError('duplicate asset lineage')
        for index, asset in enumerate(assets):
            ad, cr, story, media, tags = source_data[index % len(source_data)]
            if asset.get('language') != p['language'] or not asset.get('association_verified') or not asset.get('ready'):
                raise ValueError('asset language/readiness mismatch')
            if not asset.get('thumbnail_url') or not asset.get('vertical_video_id'):
                raise ValueError('asset thumbnail/media incomplete')
            cta = copy.deepcopy(media['call_to_action']); cta.setdefault('value', {})['link'] = p['destination_base'] + '?' + tags
            vd = {'video_id': asset['vertical_video_id'], 'title': media.get('title') or media.get('name'),
                  'message': media['message'], 'call_to_action': cta, 'image_url': asset['thumbnail_url']}
            if not vd['title']:
                raise ValueError('copy headline missing')
            if media.get('link_description') or media.get('description'):
                vd['link_description'] = media.get('link_description') or media['description']
            creative = {'name': f'SHEIN {p["manager_code"]} C{number} {asset["canonical_filename"]}',
                        'object_story_spec': {'page_id': p['page_id'], 'video_data': vd},
                        'degrees_of_freedom_spec': _individual_dof(cr), 'url_tags': tags}
            if story.get('instagram_user_id'):
                creative['object_story_spec']['instagram_user_id'] = story['instagram_user_id']
            if mode == 'clone_prestaged':
                creative['media_sourcing_spec'] = {'titles': [{'text': vd['title']}], 'bodies': [{'text': vd['message']}], 'videos': [{
                    'video_id': asset['vertical_video_id'], 'original_video_id': asset['vertical_video_id'], 'source': 'multi_media',
                    'opt_in_status': 'opt_in', 'thumbnail_source': 'generated_default', 'thumbnail_url': asset['thumbnail_url']}]}
            slot = {'name': f'AD {index+1:02d} - {asset["canonical_filename"].rsplit(".",1)[0]}',
                    'source_ad_id': str(ad['id']), 'creative_payload': creative,
                    'media': {k: asset[k] for k in ['asset_id', 'checksum', 'vertical_video_id', 'ready', 'upload_edge', 'association_verified']}}
            ads.append(slot)
    from decimal import Decimal
    budget = Decimal(str(request['budget_usd'])) * 100
    if budget <= 0 or budget != budget.to_integral_value():
        raise ValueError('exact positive cent budget required')
    shell = {'idempotency_key': request['request_id'], 'app_key': account_config['app_key'], 'account_id': aid,
             'mode': mode, 'name': name, 'adset_name': source['adset']['name'].replace(old, new),
             'start_time': start.isoformat(), 'status': request['status'], 'ads': ads}
    if mode == 'from_zero_prestaged':
        shell['campaign_create'] = _campaign_create(campaign, int(budget))
        shell['adset_create'] = _adset_create(source['adset'])
        shell['adset_create']['promoted_object'] = copy.deepcopy(source['adset']['promoted_object'])
        for field in ['bid_amount', 'bid_constraints']:
            if source['adset'].get(field) is not None:
                shell['adset_create'][field] = copy.deepcopy(source['adset'][field])
    else:
        shell.update(source_campaign_id=campaign['id'], source_adset_id=source['adset']['id'],
                     campaign_updates={'daily_budget': str(int(budget)), 'bid_strategy': campaign['bid_strategy']})
        if mode == 'pure_clone':
            shell['creative_materialization_route'] = 'existing_post_two_phase'
    return {'schema_version': 3, 'request_id': request['request_id'], 'operation': 'SHEIN-US-DIRECT', 'graph_version': 'v26.0',
            'created_at': datetime.now(timezone.utc).isoformat(), 'prevalidated': False, 'execution_mode': mode, 'campaigns': [shell]}
