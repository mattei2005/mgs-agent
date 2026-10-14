"""Read-only cross-account reference controls; no campaign/media writer.

Target shells use existing from_zero_prestaged mechanics. source_ad_id is
provenance on target direct ad creation, not a native cross-account copy.
API acceptance and serving remain unverified until a separately authorized run.
"""
from __future__ import annotations
import copy
import re
from urllib.parse import parse_qsl, urlparse

RODOLFO = '344196393512075265'


def validate_intent(request):
    if 'source_account' not in request:
        if 'source_campaign_id' in request or 'website_url' in request:
            raise ValueError('explicit source account required for reference destination')
        return
    if (not isinstance(request['source_account'], str) or not request['source_account']
            or not re.fullmatch(r'[1-9][0-9]+', str(request.get('source_campaign_id') or ''))):
        raise ValueError('exact reference account and campaign ID required')
    if request.get('mode') != 'from_zero_prestaged' or int(request.get('quantity', 1)) != 1:
        raise ValueError('literal reference destination requires one new from-zero campaign')
    if request.get('preserve_posts') or request.get('target_number'):
        raise ValueError('new cross-account reference cannot preserve posts or recycle numbers')
    if not isinstance(request.get('website_url'), str) or not request['website_url']:
        raise ValueError('literal requested Website URL required')


def target_profile(request, target, source, policy):
    validate_intent(request)
    if policy.get('enabled') is not True or policy.get('approved_by') != RODOLFO:
        raise ValueError('approved cross-account reference policy unavailable')
    if target['account_id'] == source['account_id']:
        raise ValueError('cross-account reference requires distinct exact accounts')
    for key in ['manager_code', 'channel_id', 'language', 'currency']:
        if not target.get(key) or source.get(key) != target[key]:
            raise ValueError('reference partition, language or currency mismatch')
    if target['currency'] != 'USD' or not target.get('page_id') or not target.get('pixel_id'):
        raise ValueError('approved target Page/pixel/currency unavailable')
    url = urlparse(request['website_url'])
    if (url.scheme != 'https' or url.username or url.password or url.fragment
            or url.port not in {None, 443} or url.hostname != target.get('operational_domain', urlparse(target.get('destination_base', '')).hostname)):
        raise ValueError('literal target Website URL identity mismatch')
    if not re.fullmatch(r'/quiz/us/sh[123]-' + target['manager_code'].lower() + r'/', url.path):
        raise ValueError('literal target quiz/manager route mismatch')
    pairs = parse_qsl(url.query, keep_blank_values=True)
    params = dict(pairs)
    if len(params) != len(pairs):
        raise ValueError('literal Website URL has duplicate tracking keys')
    token = params.get('utm_campaign', '')
    match = re.fullmatch(r'(b[0-9]+fb[0-9]+)c([0-9]+)', token)
    if (not match or not 1 <= int(match[2]) <= 999 or params.get('utm_adgroup') != token + 'g01'
            or params.get('utm_source') != 'facebook' or params.get('utm_medium') != target['manager_code'].lower() + '-s'):
        raise ValueError('literal target tracking invalid')
    result = copy.deepcopy(target)
    result.update(destination_base=request['website_url'].split('?', 1)[0], tracking_prefix=match[1],
                  utm_medium=params['utm_medium'], reference_target_token=token)
    return result


def configure(request, target, profiles, operation, lookup):
    source_row = lookup(request['source_account'], manager_code=target['manager_code'], channel_id=target['channel_id'])
    source = copy.deepcopy(profiles[source_row['account_id']])
    source['channel_authorization_policy'] = operation.get('channel_authorization_policy') or {}
    # The real origin remains the target thread. No invented source-channel flag.
    from .shein_general import authorize
    authorize(request, source)
    resolved = target_profile(request, target, source, operation.get('cross_account_reference_policy') or {})
    return resolved, source


def require_binding(request, source, target, reference):
    validate_intent(request)
    target_profile(request, target, reference, {'enabled': True, 'approved_by': RODOLFO})
    from .shein_general import authorize
    authorize(request, reference)
    if (source['campaign'].get('account_id') != reference['account_id']
            or source['campaign'].get('id') != request['source_campaign_id']
            or request['source_account'] not in {reference['account_id'], reference['account_name']}):
        raise ValueError('exact live reference identity mismatch')
    if source['adset'].get('promoted_object', {}).get('pixel_id') != reference.get('pixel_id'):
        raise ValueError('reference pixel mismatch')
    if target.get('pixel_id') != reference.get('pixel_id'):
        raise ValueError('reference pixel is not the approved target pixel')
    campaign = source['campaign']; adset = source['adset']
    if (campaign.get('objective') != 'OUTCOME_SALES' or adset.get('optimization_goal') != 'OFFSITE_CONVERSIONS'
            or adset.get('promoted_object', {}).get('custom_event_type') != 'ADD_TO_WISHLIST'):
        raise ValueError('reference fixed SHEIN event mismatch')
    required_campaign = {'buying_type', 'bid_strategy', 'special_ad_categories'}
    if campaign.get('special_ad_categories'):
        required_campaign.add('special_ad_category_country')
    required_adset = {'billing_event', 'optimization_goal', 'targeting', 'promoted_object', 'attribution_spec',
                     'regional_regulated_categories', 'regional_regulation_identities', 'is_dynamic_creative'}
    if not required_campaign.issubset(campaign) or not required_adset.issubset(adset):
        raise ValueError('complete compatible live reference settings required')
    match = re.search(r'\((' + re.escape(reference['tracking_prefix']) + r'c([0-9]+))\)', campaign['name'])
    display = re.match(r'^([0-9]+)\s*-', campaign['name'])
    if (not match or not display or int(match[2]) != int(request['source_number'])
            or int(display[1]) != int(request['source_number']) or match[1] + 'g01' not in adset['name']):
        raise ValueError('reference exact campaign number/tracking mismatch')
    from .creative_media import source_links
    for ad in source['ads']:
        cr = ad.get('creative') or {}; story = cr.get('object_story_spec') or ad.get('_reference_story') or {}
        if (story.get('page_id') != reference['page_id'] or ad.get('adset_id') != adset['id']
                or not str(cr.get('effective_object_story_id') or '').startswith(reference['page_id'] + '_')):
            raise ValueError('reference Page/adset/post identity mismatch')
        for link in source_links(cr, story):
            params = dict(parse_qsl(urlparse(link).query)); params.update(dict(parse_qsl(cr.get('url_tags') or '')))
            if (link.split('?')[0] != reference['destination_base'] or params.get('utm_medium') != reference['utm_medium']
                    or params.get('utm_campaign') != match[1] or params.get('utm_adgroup') != match[1] + 'g01'):
                raise ValueError('reference effective tracking mismatch')


def receipt(source, reference):
    return {'account_id': source['campaign']['account_id'], 'campaign_id': source['campaign']['id'],
            'adset_id': source['adset']['id'], 'ad_ids': [str(a['id']) for a in source['ads']],
            'language': reference['language'], 'page_id': reference['page_id'], 'access': 'READ_ONLY',
            'lineage_route': 'direct_ad_create_with_source_ad_id'}


def creative_degrees(creative):
    degrees = copy.deepcopy(creative.get('degrees_of_freedom_spec') or {})
    degrees.get('creative_features_spec', {}).pop('standard_enhancements', None)
    return degrees


def verify_degrees(actual, expected):
    """Preserve original individual features; new API defaults may only OPT_OUT."""
    actual = copy.deepcopy(actual or {}); expected = copy.deepcopy(expected or {})
    observed = actual.pop('creative_features_spec', {})
    wanted = expected.pop('creative_features_spec', {})
    if any(actual.get(k) != v for k, v in expected.items()):
        raise ValueError('reference creative degrees state drift')
    if (any(observed.get(k) != v for k, v in wanted.items())
            or any(v != {'enroll_status': 'OPT_OUT'} for k, v in observed.items() if k not in wanted)):
        raise ValueError('reference individual creative feature drift')
