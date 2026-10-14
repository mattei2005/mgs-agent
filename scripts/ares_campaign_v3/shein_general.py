"""SHEIN account-scoped manifest compiler. No API mutations and no new writer."""
from __future__ import annotations
import copy
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse
from zoneinfo import ZoneInfo
from .shein import _individual_dof, _campaign_create, _adset_create
from .creative_media import source_links, full_creative, definition_creative


def authorize(request, profile, *, force=False):
    actor = str(request.get('authorized_by') or '')
    if actor == '344196393512075265':
        return
    policy = profile.get('channel_authorization_policy') or {}
    if policy.get('enabled') is True:
        if (policy.get('approved_by') != '344196393512075265'
                or str(profile.get('channel_id')) not in policy.get('channel_ids', [])):
            raise ValueError('approved channel authorization policy unavailable')
        if str(request.get('source_channel_id') or '') != str(profile.get('channel_id')):
            raise ValueError('request must originate in the account canonical parent channel')
        from .shein_channel_authority import verify
        if verify(request, profile, force=force).get('verified') is not True:
            raise ValueError('live channel authorization unconfirmed')
        return
    if actor != str(profile.get('manager_discord_id')):
        raise ValueError('requester is not the account-bound manager')
    if str(request.get('source_channel_id') or '') != str(profile.get('channel_id')):
        raise ValueError('manager request must originate in its canonical parent channel')


def bid_delta(request, source):
    from decimal import Decimal, InvalidOperation
    from .shein_naming import BIDS
    alias = request.get('bid_strategy')
    explicit = 'bid_strategy' in request or 'bid_usd' in request
    if not explicit:
        return source['campaign']['bid_strategy'], None
    if 'bid_strategy' in request:
        if alias not in BIDS.values():
            raise ValueError('bid strategy must be the exact MAXVOL, COCAP or BIDCAP alias')
        strategy = next(k for k,v in BIDS.items() if v == alias)
    else:
        strategy = source['campaign']['bid_strategy']
    if strategy == 'LOWEST_COST_WITHOUT_CAP':
        if 'bid_usd' in request:
            raise ValueError('MAXVOL does not accept a cap amount')
        amount = '0'
    elif strategy in {'COST_CAP','LOWEST_COST_WITH_BID_CAP'}:
        try:
            cents = Decimal(str(request.get('bid_usd'))) * 100
            if not cents.is_finite() or cents <= 0 or cents != cents.to_integral_value():
                raise ValueError()
            amount = str(int(cents))
        except (InvalidOperation, ValueError, TypeError, OverflowError):
            raise ValueError('COCAP/BIDCAP require an exact positive USD cent cap') from None
    else:
        raise ValueError('unsupported source bid strategy')
    source_set = source.get('adset') or {}
    if strategy == source['campaign']['bid_strategy'] and str(source_set.get('bid_amount') or '0') == amount and not source_set.get('bid_constraints'):
        return strategy, None
    return strategy, {'bid_amount': amount, 'bid_constraints': {}}


def build(request, source, number, account_config):
    if not re.fullmatch(r'[1-9][0-9]*', str(request.get('quantity', 1))) or not 1 <= int(request.get('quantity', 1)) <= 100:
        raise ValueError('quantity must be an exact integer from 1 to 100')
    quantity = int(request.get('quantity', 1))
    assets = request.get('_resolved_assets') or []
    groups = request.get('campaign_groups')
    if groups is not None:
        from .shein_grouped_media import validate_groups
        validate_groups(request)
        by_filename = {a['canonical_filename']: a for a in assets}
        filenames = [f for group in groups for f in group['files']]
        if len(by_filename) != len(assets) or set(by_filename) != set(filenames):
            raise ValueError('resolved assets do not match exact requested groups')
        payload = None; campaigns = []
        for offset, group in enumerate(groups):
            child = copy.deepcopy(request)
            child.pop('campaign_groups')
            child['quantity'] = 1
            child['request_id'] = request['request_id'] + f'-c{number+offset}'
            child['_resolved_assets'] = [by_filename[f] for f in group['files']]
            child['product_label'] = group['product_label']
            child['_primary_text'] = group['primary_text']
            one = _build_one(child, source, number+offset, account_config)
            payload = payload or one; campaigns.extend(one['campaigns'])
        payload['request_id'] = request['request_id']; payload['campaigns'] = campaigns
        return payload
    if quantity == 1:
        return _build_one(request, source, number, account_config)
    mode = request.get('mode', 'pure_clone')
    per_campaign = len(assets) // quantity if mode != 'pure_clone' else 0
    if mode != 'pure_clone' and (len(assets) % quantity or not 1 <= per_campaign <= 5):
        raise ValueError('asset count must match exact campaign quantity')
    payload = None; campaigns = []
    for offset in range(quantity):
        child = copy.deepcopy(request); child['request_id'] = request['request_id'] + f'-c{number+offset}'
        if mode != 'pure_clone':
            child['_resolved_assets'] = assets[offset*per_campaign:(offset+1)*per_campaign]
        one = _build_one(child, source, number+offset, account_config)
        payload = payload or one; campaigns.extend(one['campaigns'])
    assert payload is not None
    payload['request_id'] = request['request_id']; payload['campaigns'] = campaigns
    return payload


def _build_one(request, source, number, account_config):
    p = account_config['shein_profile']
    authorize(request, p)
    aid = str(p['account_id'])
    reference = account_config.get('shein_reference_profile') if request.get('source_account') else None
    if reference:
        from .shein_reference import require_binding
        require_binding(request, source, p, reference)
    sp = reference or p
    if request['account'] not in {aid, p['account_name']} or source['campaign'].get('account_id') != sp['account_id']:
        raise ValueError('account/source binding mismatch')
    if 'preserve_posts' in request and not isinstance(request['preserve_posts'], bool):
        raise ValueError('preserve_posts must be an explicit boolean')
    mode = request.get('mode', 'pure_clone')
    if mode not in {'pure_clone', 'clone_prestaged', 'from_zero_prestaged'}:
        raise ValueError('unsupported SHEIN mode')
    if source['campaign'].get('objective') != 'OUTCOME_SALES' or source['adset'].get('optimization_goal') != 'OFFSITE_CONVERSIONS' or source['adset'].get('promoted_object', {}).get('custom_event_type') != 'ADD_TO_WISHLIST':
        raise ValueError('source fixed SHEIN event mismatch')
    if request.get('status') not in {'PAUSED', 'ACTIVE'}:
        raise ValueError('explicit delivery status required')
    start = datetime.fromisoformat(request['start_time']).astimezone(ZoneInfo(p['timezone']))
    sn = int(request['source_number'])
    literal = re.search(r'\((' + re.escape(sp['tracking_prefix']) + r'c[0-9]+)\)', source['campaign']['name'])
    if not literal or int(literal.group(1).split('c')[-1]) != sn:
        raise ValueError('source literal tracking token/number mismatch')
    old = literal.group(1)
    new = p['tracking_prefix'] + f'c{number:03d}'
    if reference:
        new = p['reference_target_token']
        if int(new.split('c')[-1]) != number:
            raise ValueError('literal tracking does not identify the next free target number')
    campaign = copy.deepcopy(source['campaign'])
    campaign['bid_strategy'], bid_updates = bid_delta(request, source)
    label_number = re.match(r'^([0-9]+)\s*-', campaign['name'])
    if not label_number or int(label_number.group(1)) != sn or '(' + old + ')' not in campaign['name']:
        raise ValueError('source numbering/tracking prefix mismatch')
    if old + 'g01' not in source['adset']['name']:
        raise ValueError('source adset token mismatch')
    # Source tokens and labels remain literal in provenance. Only new target naming
    # is canonicalized; historic 01/c01 and c0101 are never rewritten in the source.
    product = campaign['name'].split('(' + old + ')', 1)[0]
    product = re.sub(r'^[0-9]+\s*-\s*', '', product)
    product = re.sub(r'\[?[0-9]{2}/[0-9]{2}\]?', '', product)
    product = re.sub(r'\s*(?:-\s*)?US-(?:EN|ES)\b', '', product)
    product = re.sub(r'\s*-\s*-\s*', ' - ', product).strip(' -')
    product = re.sub(r'\s+', ' ', product)
    if not product:
        raise ValueError('source product label unavailable')
    name = f'{number} - {product} - US-{p["language"]} ({new}) {start:%d/%m} event_add_to_wishlist'
    if mode == 'pure_clone':
        name += f' COPY C{sn}'
    elif request.get('product_label'):
        name = f'{number} - {request["product_label"]} - US-{p["language"]} ({new}) {start:%d/%m} event_add_to_wishlist'
    naming = account_config.get('shein_naming') or {}
    if naming.get('enabled') is True:
        from .shein_naming import product_label, campaign_name
        chosen_product = request.get('product_label') if mode != 'pure_clone' and request.get('product_label') else product_label(campaign['name'])
        name = campaign_name(number, start.isoformat(), p['timezone'], p['destination_base'], chosen_product, campaign['bid_strategy'], new, naming, copy_source_number=sn if mode in {'pure_clone','clone_prestaged'} else None)
    source_ads = sorted(source['ads'], key=lambda a: str(a.get('name', '')))
    if not 1 <= len(source_ads) <= 5:
        raise ValueError('source requires 1..5 ads')
    source_data = []
    for ad in source_ads:
        cr = ad.get('creative') or {}
        if account_config.get('require_source_contextual_multi_ads') is True and (cr.get('contextual_multi_ads') or {}).get('enroll_status') not in {'OPT_IN','OPT_OUT'}:
            raise ValueError('source Multi-advertiser ads state unconfirmed; no default assumption')
        story = cr.get('object_story_spec') or ad.get('_reference_story') or {}
        media = story.get('video_data') or story.get('link_data') or {}
        links = source_links(cr, story)
        link = links[0]
        if any(x.split('?')[0] != sp['destination_base'] for x in links):
            raise ValueError('source destination differs from approved account profile')
        params = dict(parse_qsl(urlparse(link).query)); params.update(dict(parse_qsl(cr.get('url_tags') or '')))
        for destination in links:
            params = dict(parse_qsl(urlparse(destination).query)); params.update(dict(parse_qsl(cr.get('url_tags') or '')))
            if params.get('utm_medium') != sp['utm_medium'] or params.get('utm_campaign') != old or params.get('utm_adgroup') != old + 'g01':
                raise ValueError('source effective tracking mismatch')
        if story.get('page_id') != sp['page_id'] or not cr.get('effective_object_story_id', '').startswith(sp['page_id'] + '_') or ad.get('adset_id') != source['adset']['id']:
            raise ValueError('Page/adset/post lineage mismatch')
        tags = dict(parse_qsl(cr.get('url_tags') or ''))
        tags.update(utm_source='facebook', utm_medium=p['utm_medium'], utm_campaign=new, utm_adgroup=new + 'g01')
        if mode != 'pure_clone' and cr.get('asset_feed_spec'):
            feed = cr['asset_feed_spec']
            def single_text(key):
                values = {x.get('text') for x in feed.get(key, [])}
                if len(values) != 1: raise ValueError('flexible reference copy is ambiguous for new-media slots')
                return next(iter(values))
            ctas = feed.get('call_to_action_types') or []
            if len(ctas) != 1: raise ValueError('flexible reference CTA is ambiguous')
            media = {'title': single_text('titles'), 'message': single_text('bodies'),
                     'call_to_action': {'type': ctas[0], 'value': {'link': link}}}
            if feed.get('descriptions'): media['link_description'] = single_text('descriptions')
        source_data.append((ad, cr, story, media, urlencode(tags)))
    ads = []
    if mode == 'pure_clone':
        for ad, cr, story, media, tags in source_data:
            if cr.get('asset_feed_spec') and request.get('preserve_posts') is True:
                raise ValueError('flexible media needs new posts; explicit post-preservation request cannot be silently changed')
            cname = f'SHEIN {p["manager_code"]} C{number} {ad["name"]} COPY C{sn}'
            preserve_definition = account_config.get('pure_clone_setup_policy') == 'PRESERVE_SOURCE_DEFINITION'
            if preserve_definition and cr.get('object_story_spec') and not cr.get('object_story_id'):
                if request.get('preserve_posts') is True:
                    raise ValueError('Create ad with new website tracking cannot silently preserve an immutable post')
                cp = definition_creative(cr, story, tags, cname)
            else:
                cp = full_creative(cr, story, tags, cname, _individual_dof(cr)) if cr.get('asset_feed_spec') else {
                'name': cname, 'object_story_id': cr['effective_object_story_id'], 'url_tags': tags,
                'degrees_of_freedom_spec': _individual_dof(cr)}
            if cr.get('contextual_multi_ads') is not None:
                cp['contextual_multi_ads'] = copy.deepcopy(cr['contextual_multi_ads'])
            ads.append({'name': ad['name'], 'source_ad_id': str(ad['id']), 'creative_payload': cp})
    else:
        assets = request.get('_resolved_assets') or []
        if (mode == 'from_zero_prestaged' and not reference and len(assets) != 3) or not 1 <= len(assets) <= 5:
            raise ValueError('from-zero needs three assets; new-media clone needs 1..5')
        if len({a['asset_id'] for a in assets}) != len(assets):
            raise ValueError('duplicate asset lineage')
        for index, asset in enumerate(assets):
            ad, cr, story, media, tags = source_data[index % len(source_data)]
            if asset.get('language') != p['language'] or not asset.get('association_verified') or not asset.get('ready'):
                raise ValueError('asset language/readiness mismatch')
            if not asset.get('thumbnail_url') or not asset.get('vertical_video_id'):
                raise ValueError('asset thumbnail/media incomplete')
            cta = copy.deepcopy(media['call_to_action']); cta.setdefault('value', {})['link'] = request['website_url'] if reference else p['destination_base'] + '?' + tags
            vd = {'video_id': asset['vertical_video_id'], 'title': media.get('title') or media.get('name'),
                  'message': request.get('_primary_text', request.get('primary_text', media['message'])), 'call_to_action': cta, 'image_url': asset['thumbnail_url']}
            if not vd['title']:
                raise ValueError('copy headline missing')
            if media.get('link_description') or media.get('description'):
                vd['link_description'] = media.get('link_description') or media['description']
            creative = {'name': f'SHEIN {p["manager_code"]} C{number} {asset["canonical_filename"]}',
                        'object_story_spec': {'page_id': p['page_id'], 'video_data': vd},
                        'degrees_of_freedom_spec': _individual_dof(cr), 'url_tags': '' if reference else tags}
            ig = p.get('instagram_user_id') if reference else cr.get('instagram_user_id') or story.get('instagram_user_id')
            if ig:
                creative['object_story_spec']['instagram_user_id'] = ig
            if cr.get('contextual_multi_ads') is not None:
                creative['contextual_multi_ads'] = copy.deepcopy(cr['contextual_multi_ads'])
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
    if not budget.is_finite() or budget <= 0 or budget != budget.to_integral_value():
        raise ValueError('exact positive cent budget required')
    shell = {'idempotency_key': request['request_id'], 'app_key': account_config['app_key'], 'account_id': aid,
             'mode': mode, 'name': name, 'adset_name': source['adset']['name'].replace(old, new),
             'start_time': start.isoformat(), 'status': request['status'], 'ads': ads}
    if request.get('start_now') is True:
        shell['start_intent'] = 'IMMEDIATE'
    if mode == 'from_zero_prestaged':
        shell['campaign_create'] = _campaign_create(campaign, int(budget))
        shell['adset_create'] = _adset_create(source['adset'])
        shell['adset_create']['promoted_object'] = copy.deepcopy(source['adset']['promoted_object'])
        for field in ['bid_amount', 'bid_constraints']:
            if source['adset'].get(field) is not None:
                shell['adset_create'][field] = copy.deepcopy(source['adset'][field])
        if bid_updates is not None:
            shell['adset_create'].update(bid_updates)
        if reference:
            from .shein_reference import receipt
            shell['reference'] = receipt(source, reference)
            # Preserve the live configuration, not the G005 fallback defaults.
            required = {'billing_event', 'optimization_goal', 'targeting', 'promoted_object',
                        'attribution_spec', 'regional_regulated_categories',
                        'regional_regulation_identities', 'is_dynamic_creative'}
            if not required.issubset(source['adset']):
                raise ValueError('complete compatible live reference adset required')
            shell['adset_create'].update({k: copy.deepcopy(source['adset'][k]) for k in required})
            if bid_updates is not None:
                shell['adset_create'].update(bid_updates)
    else:
        shell.update(source_campaign_id=campaign['id'], source_adset_id=source['adset']['id'],
                     campaign_updates={'daily_budget': str(int(budget)), 'bid_strategy': campaign['bid_strategy']})
        if bid_updates is not None:
            shell.update(bid_override=True, adset_updates=bid_updates)
        if mode == 'pure_clone':
            if account_config.get('pure_clone_setup_policy') == 'PRESERVE_SOURCE_DEFINITION' and all(ad['creative_payload'].get('object_story_spec') for ad in ads):
                shell['creative_materialization_route'] = 'source_definition_two_phase'
            else:
                shell['creative_materialization_route'] = 'full_media_two_phase' if any(ad['creative_payload'].get('asset_feed_spec') for ad in ads) else 'existing_post_two_phase'
    return {'schema_version': 3, 'request_id': request['request_id'], 'operation': 'SHEIN-US-DIRECT', 'graph_version': 'v26.0',
            'created_at': datetime.now(timezone.utc).isoformat(), 'prevalidated': False, 'execution_mode': mode, 'campaigns': [shell]}
