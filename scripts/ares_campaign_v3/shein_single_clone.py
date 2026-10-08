"""Account-scoped SHEIN intake/readback adapter; all writes use CampaignEngine v3.

No new-media staging, credential mutation, recurring automation, or direct POST.
The rollout is deliberately limited to one PAUSED pure clone on YOLO G002.
"""
from __future__ import annotations

import copy
import fcntl
import importlib.util
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse
from zoneinfo import ZoneInfo
from contextvars import ContextVar

from .engine import CampaignEngine
from .media_registry import MediaRegistry
from .prevalidation import prevalidate_payload, validate_account_policy
from .schema import Manifest
from .shein import _individual_dof, next_campaign_numbers
from .transport import FakeBatchTransport, GraphBatchTransport

BASE = Path('/root/mgs-agent')
ACCOUNT_ID = '7840111366055613'
ACCOUNT_ALIAS = 'Yolokfx-US-SHEIN-EN-01-G002'
SYSTEM_USER_ID = '122095869861482193'
BUSINESS_ID = '155263197283282'
RODOLFO_ID = '344196393512075265'
ET = ZoneInfo('America/New_York')
REQUEST_FIELDS = {'request_id', 'account', 'source_number', 'budget_usd', 'start_time', 'status',
                  'authorized_by', 'source_thread_id', 'request_received_at', 'source_message_id',
                  'source_channel_id', 'mode', 'asset_refs', 'product_label'}
CURRENT_PROFILE = ContextVar('shein_account_profile', default=None)


def account_id():
    return (CURRENT_PROFILE.get() or {}).get('account_id', ACCOUNT_ID)


def account_alias():
    return (CURRENT_PROFILE.get() or {}).get('account_name', ACCOUNT_ALIAS)


def account_timezone():
    return ZoneInfo((CURRENT_PROFILE.get() or {}).get('timezone', 'America/New_York'))


class RouteBlocked(ValueError):
    """Only fixed, non-secret messages may be used in this exception."""


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(raw, path)
    finally:
        if os.path.exists(raw):
            os.unlink(raw)


def budget_minor(value: Any) -> int:
    try:
        dollars = Decimal(str(value))
        cents = dollars * 100
        if not dollars.is_finite() or dollars <= 0 or cents != cents.to_integral_value():
            raise RouteBlocked('budget must be a positive exact USD cent amount')
        return int(cents)
    except (InvalidOperation, ValueError, TypeError, OverflowError) as exc:
        raise RouteBlocked('invalid USD budget') from exc


def aware_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError()
        return parsed
    except (ValueError, TypeError) as exc:
        raise RouteBlocked('start and receipt timestamps require explicit timezone') from exc


def validate_request(request: dict[str, Any]) -> None:
    if set(request) - REQUEST_FIELDS:
        raise RouteBlocked('unknown request field')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}', str(request.get('request_id') or '')):
        raise RouteBlocked('invalid request_id')
    if not isinstance(request.get('account'), str) or not request['account']:
        raise RouteBlocked('exact account name or ID is required')
    if request.get('status') not in {'PAUSED', 'ACTIVE'}:
        raise RouteBlocked('explicit PAUSED or ACTIVE delivery status required')
    if not re.fullmatch(r'[0-9]{17,20}', str(request.get('authorized_by') or '')):
        raise RouteBlocked('canonical requester ID is required')
    if request.get('mode', 'pure_clone') not in {'pure_clone', 'from_zero_prestaged', 'clone_prestaged'}:
        raise RouteBlocked('unsupported SHEIN mode')
    if not re.fullmatch(r'[1-9][0-9]*', str(request.get('source_number') or '')):
        raise RouteBlocked('source_number must be a positive integer')
    if not re.fullmatch(r'[0-9]{17,20}', str(request.get('source_thread_id') or '')):
        raise RouteBlocked('source thread ID is required')
    budget_minor(request.get('budget_usd'))
    aware_time(request.get('start_time'))
    if request.get('request_received_at'):
        aware_time(request['request_received_at'])
    if request.get('source_message_id'):
        mid = str(request['source_message_id'])
        if not re.fullmatch(r'[0-9]{17,20}', mid) or int(mid) >= 2**64:
            raise RouteBlocked('invalid source message snowflake')


def request_clock(request: dict[str, Any]):
    if request.get('request_received_at'):
        return aware_time(request['request_received_at']), 'gateway request receipt to readback'
    if request.get('source_message_id'):
        validate_request(request)
        milliseconds = (int(request['source_message_id']) >> 22) + 1420070400000
        return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc), 'Discord message creation to readback'
    return None, 'runner start to readback; message timestamp unavailable'


def lookup_account(account: str, *, manager_code=None, channel_id=None) -> dict[str, Any]:
    catalog = json.loads((BASE / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json').read_text())
    if catalog.get('operation_id') != 'SHEIN-US-DIRECT':
        raise RouteBlocked('account catalog operation mismatch')
    rows = catalog.get('accounts') or []
    if len(rows) != catalog.get('account_count') or len({str(x.get('account_id')) for x in rows}) != len(rows):
        raise RouteBlocked('account catalog count or identity conflict')
    matches = [x for x in rows if account in {x.get('account_id'), x.get('name')}]
    if len(matches) != 1:
        raise RouteBlocked('account name or ID missing or ambiguous in canonical catalog')
    row = matches[0]
    if manager_code is not None and row.get('manager_code') != manager_code:
        raise RouteBlocked('account belongs to another manager')
    if channel_id is not None and row.get('channel_id') != channel_id:
        raise RouteBlocked('account belongs to another manager channel')
    return {'status': 'ACCOUNT_RESOLVED', 'snapshot_at_utc': catalog['snapshot_at_utc'], **row}


def _story(ad: dict[str, Any]) -> dict[str, Any]:
    return (ad.get('creative') or {}).get('object_story_spec') or ad.get('_reference_story') or {}


def build_manifest(request: dict[str, Any], source: dict[str, Any], number: int,
                   account_config: dict[str, Any]) -> dict[str, Any]:
    validate_request({k: v for k, v in request.items() if k != '_resolved_assets'})
    if account_config.get('shein_profile'):
        from .shein_general import build
        return build(request, source, number, account_config)
    # Legacy fixture/config compatibility; deployed general accounts use the compiler above.
    if request.get('status') != 'PAUSED' or request.get('authorized_by') != RODOLFO_ID:
        raise RouteBlocked('legacy fixture requires PAUSED Rodolfo request')
    if request.get('account') not in {ACCOUNT_ID, ACCOUNT_ALIAS}:
        raise RouteBlocked('legacy fixture account mismatch')
    if account_config.get('alias') != ACCOUNT_ALIAS or account_config.get('operation') != 'SHEIN-US-DIRECT':
        raise RouteBlocked('account registration mismatch')
    if 'pure_clone' not in (account_config.get('supported_modes') or []):
        raise RouteBlocked('account does not support pure_clone')
    campaign, adset, ads = source['campaign'], source['adset'], source['ads']
    source_number = int(request['source_number'])
    old = f'b01fb01c{source_number:03d}'
    new = f'b01fb01c{number:03d}'
    if (str(campaign.get('account_id')) != ACCOUNT_ID or campaign.get('objective') != 'OUTCOME_SALES'
            or int(campaign.get('daily_budget') or 0) <= 0):
        raise RouteBlocked('source account, sales objective or CBO budget invalid')
    if (adset.get('optimization_goal') != 'OFFSITE_CONVERSIONS'
            or (adset.get('promoted_object') or {}).get('custom_event_type') != 'ADD_TO_WISHLIST'):
        raise RouteBlocked('source event must be OFFSITE_CONVERSIONS / ADD_TO_WISHLIST')
    if not 1 <= len(ads) <= 5 or len({a.get('id') for a in ads}) != len(ads):
        raise RouteBlocked('one through five unique source ads required')
    source_name = str(campaign.get('name') or '')
    if not re.match(r'^' + str(source_number) + r'\s*-', source_name) or '(' + old + ')' not in source_name:
        raise RouteBlocked('source campaign number or account tracking prefix mismatch')
    if old + 'g01' not in str(adset.get('name') or ''):
        raise RouteBlocked('source adset tracking mismatch')
    local_start = aware_time(request['start_time']).astimezone(account_timezone())
    name = re.sub(r'\s+COPY\s+C\d+\s*$', '', source_name)
    name = re.sub(r'^' + str(source_number) + r'\b', str(number), name).replace(old, new)
    name = re.sub(r'\s+\d{2}/\d{2}(?=\s|$)', '', name)
    name = name.replace('(' + new + ')', '(' + new + ') ' + local_start.strftime('%d/%m')) + f' COPY C{source_number}'
    out_ads = []
    for ad in sorted(ads, key=lambda x: str(x.get('name') or '')):
        creative, story = ad.get('creative') or {}, _story(ad)
        post = str(creative.get('effective_object_story_id') or '')
        page = str(story.get('page_id') or '')
        if not ad.get('id') or str(ad['id']) == '0' or not page or not post.startswith(page + '_'):
            raise RouteBlocked('source ad or Page/post lineage invalid')
        if str(ad.get('adset_id')) != str(adset['id']):
            raise RouteBlocked('source ad does not belong to source adset')
        video = story.get('video_data') or {}
        link = (video.get('call_to_action') or {}).get('value', {}).get('link')
        parsed = urlparse(str(link or ''))
        if parsed.scheme != 'https' or parsed.hostname != 'yolokfx.com' or parsed.path != '/quiz/us/sh2-g002/':
            raise RouteBlocked('source destination outside this account route')
        effective = dict(parse_qsl(parsed.query, keep_blank_values=True))
        tags = dict(parse_qsl(str(creative.get('url_tags') or ''), keep_blank_values=True))
        effective.update(tags)
        expected = {'utm_source': 'facebook', 'utm_medium': 'g002-s', 'utm_campaign': old, 'utm_adgroup': old + 'g01'}
        if any(effective.get(k) != v for k, v in expected.items()):
            raise RouteBlocked('source effective tracking mismatch')
        target_tags = {**tags, 'utm_source': 'facebook', 'utm_medium': 'g002-s', 'utm_campaign': new, 'utm_adgroup': new + 'g01'}
        out_ads.append({'name': str(ad['name']), 'source_ad_id': str(ad['id']), 'creative_payload': {
            'name': f'SHEIN G002 C{number} {ad["name"]} COPY C{source_number}', 'object_story_id': post,
            'url_tags': urlencode(target_tags), 'degrees_of_freedom_spec': _individual_dof(creative)}})
    rid = request['request_id']
    return {'schema_version': 3, 'request_id': rid, 'operation': 'SHEIN-US-DIRECT', 'graph_version': 'v26.0',
            'created_at': datetime.now(timezone.utc).isoformat(), 'prevalidated': False, 'execution_mode': 'pure_clone',
            'campaigns': [{'idempotency_key': rid, 'app_key': account_config['app_key'], 'account_id': ACCOUNT_ID,
                'mode': 'pure_clone', 'creative_materialization_route': 'existing_post_two_phase',
                'source_campaign_id': str(campaign['id']), 'source_adset_id': str(adset['id']),
                'name': name, 'adset_name': adset['name'].replace(old, new), 'start_time': local_start.isoformat(),
                'status': 'PAUSED', 'campaign_updates': {'daily_budget': str(budget_minor(request['budget_usd'])),
                    'bid_strategy': campaign['bid_strategy']}, 'ads': out_ads}]}


def _same_time(a: Any, b: Any) -> bool:
    return aware_time(a).astimezone(timezone.utc) == aware_time(b).astimezone(timezone.utc)


def verify_media_ads(desired, source, live, warnings):
    actual = {a.get('name'): a for a in live['ads']['data']}
    if len(actual) != len(desired['ads']):
        raise RouteBlocked('new-media ad names/count mismatch')
    source_posts = {a.get('creative', {}).get('effective_object_story_id') for a in source['ads']}
    for expected in desired['ads']:
        ad = actual.get(expected['name']) or {}
        cr = ad.get('creative') or {}
        cp = expected['creative_payload']; story = cr.get('object_story_spec') or {}
        vd = story.get('video_data') or {}; wanted = cp['object_story_spec']['video_data']
        if ad.get('status') != desired['status'] or ad.get('issues_info') or str(ad.get('source_ad_id')) != str(expected['source_ad_id']):
            raise RouteBlocked('new-media status/lineage/issues mismatch')
        if str(ad.get('adset_id')) != str(live['adsets']['data'][0]['id']) or story.get('page_id') != cp['object_story_spec']['page_id']:
            raise RouteBlocked('new-media Page/adset mismatch')
        if not cr.get('effective_object_story_id') or cr['effective_object_story_id'] in source_posts:
            raise RouteBlocked('new-media creative reused a source post')
        for field in ['title', 'message', 'link_description']:
            if vd.get(field) != wanted.get(field):
                raise RouteBlocked('new-media copy mismatch')
        if (vd.get('call_to_action') or {}).get('type') != wanted['call_to_action']['type'] or (vd.get('call_to_action') or {}).get('value', {}).get('link') != wanted['call_to_action']['value']['link']:
            raise RouteBlocked('new-media CTA/destination mismatch')
        if dict(parse_qsl(cr.get('url_tags') or '')) != dict(parse_qsl(cp['url_tags'])):
            raise RouteBlocked('new-media tracking mismatch')
        if desired['mode'] == 'from_zero_prestaged' and vd.get('video_id') != expected['media']['vertical_video_id']:
            raise RouteBlocked('direct creation media ID mismatch')
    return warnings


def verify_readback(payload: dict[str, Any], source: dict[str, Any], live: dict[str, Any]) -> list[str]:
    desired, campaign = payload['campaigns'][0], live['campaign']
    expected_updates = desired.get('campaign_updates') or {k: desired['campaign_create'][k] for k in ['daily_budget', 'bid_strategy']}
    if any(str(campaign.get(k)) != str(v) for k, v in {'account_id': desired['account_id'], 'name': desired['name'],
            'status': desired['status'], **expected_updates}.items()):
        raise RouteBlocked('campaign readback mismatch')
    if desired['status'] == 'PAUSED' and campaign.get('effective_status') != 'PAUSED':
        raise RouteBlocked('paused campaign effective status mismatch')
    if not _same_time(campaign.get('start_time'), desired['start_time']):
        raise RouteBlocked('campaign schedule mismatch')
    sets, ads = live['adsets'].get('data') or [], live['ads'].get('data') or []
    if len(sets) != 1 or len(ads) != len(desired['ads']):
        raise RouteBlocked('target hierarchy count mismatch')
    target_set = sets[0]
    if target_set.get('status') != desired['status'] or target_set.get('name') != desired['adset_name']:
        raise RouteBlocked('adset name/status mismatch')
    if not _same_time(target_set.get('start_time'), desired['start_time']):
        raise RouteBlocked('adset schedule mismatch')
    source_set = desired.get('adset_create') or source['adset']
    for field in ['attribution_spec', 'promoted_object', 'billing_event', 'optimization_goal', 'is_dynamic_creative']:
        if target_set.get(field) != source_set.get(field):
            raise RouteBlocked('source versus target adset field mismatch: ' + field)
    source_target = copy.deepcopy(source_set.get('targeting') or {})
    target_target = copy.deepcopy(target_set.get('targeting') or {})
    warnings = []
    if source_target != target_target:
        source_flags = source_target.get('targeting_automation', {}).pop('individual_setting', None)
        target_flags = target_target.get('targeting_automation', {}).pop('individual_setting', None)
        if source_flags != {'age': 1, 'gender': 1} or target_flags is not None or source_target != target_target:
            raise RouteBlocked('unrecognized targeting divergence')
        warnings.append('Meta omitted source optional age/gender suggestion flags; copy is not literally identical')
    if desired['mode'] != 'pure_clone':
        return verify_media_ads(desired, source, live, warnings)
    desired_ads = {x['source_ad_id']: x for x in desired['ads']}
    seen = set()
    for ad in ads:
        sid = str(ad.get('source_ad_id') or '')
        if sid not in desired_ads or sid in seen:
            raise RouteBlocked('ad lineage readback mismatch')
        seen.add(sid)
        expected = desired_ads[sid]
        creative = ad.get('creative') or {}
        if ad.get('status') != desired['status'] or ad.get('name') != expected['name'] or ad.get('issues_info'):
            raise RouteBlocked('ad name/status/issues mismatch')
        if str(ad.get('adset_id')) != str(target_set['id']):
            raise RouteBlocked('target adset association mismatch')
        cp = expected['creative_payload']
        if (creative.get('object_story_id') != cp['object_story_id']
                or creative.get('effective_object_story_id') != cp['object_story_id']
                or dict(parse_qsl(str(creative.get('url_tags') or ''))) != dict(parse_qsl(cp['url_tags']))):
            raise RouteBlocked('post or tracking readback mismatch')
    return warnings


class ReadOnlyClient:
    def __init__(self, common):
        self.common = common
        self.http_requests = 0
        self.logical_gets = 0

    def graph_get(self, path, token, params):
        self.http_requests += 1
        self.logical_gets += 1
        return self.common.graph_get(path, token, params)

    def graph_batch_get(self, token, requests):
        self.http_requests += 1
        self.logical_gets += len(requests)
        return self.common.graph_batch_get(token, requests)


def _batch(common, token, requests):
    http, rows, _ = common.graph_batch_get(token, requests)
    if http != 200 or not isinstance(rows, list) or len(rows) != len(requests):
        raise RouteBlocked('read-only Graph batch failed')
    if {row.get('name') for row in rows} != {item['name'] for item in requests}:
        raise RouteBlocked('read-only Graph batch identity mismatch')
    for row in rows:
        if row.get('code') != 200 or not isinstance(row.get('body'), dict):
            err = (row.get('body') or {}).get('error') or {}
            raise RouteBlocked('read-only endpoint rejected: ' + str(row.get('name')) + '; code=' + str(err.get('code')))
    return {row.get('name'): row['body'] for row in rows}


def _complete_edge(value: dict[str, Any]) -> list[dict[str, Any]]:
    if (value.get('paging') or {}).get('next'):
        raise RouteBlocked('pagination incomplete; no campaign write permitted')
    return list(value.get('data') or [])


def read_social(common, corporate_token, page_id: str, post_ids: list[str], *, page_token=None):
    unique = sorted(set(post_ids))
    if not unique or any(not post.startswith(page_id + '_') for post in unique):
        raise RouteBlocked('social read mixes or omits Page identity')
    if not page_token:
        http, page, _ = common.graph_get(page_id, corporate_token, {'fields': 'id,name,access_token'})
        if http != 200 or str(page.get('id')) != page_id or not page.get('access_token'):
            raise RouteBlocked('Page read identity unavailable')
        page_token = page['access_token']
    results = []
    for offset in range(0, len(unique), 50):
        chunk = unique[offset:offset + 50]
        rows = _batch(common, page_token, [{'name': 'post-' + str(i), 'path': post, 'params': {
            'fields': 'id,reactions.limit(0).summary(true),comments.limit(0).summary(true),shares'}} for i, post in enumerate(chunk, 1)])
        for i, post in enumerate(chunk, 1):
            body = rows['post-' + str(i)]
            if body.get('id') != post:
                raise RouteBlocked('social post identity mismatch')
            results.append({'post_id': post, 'reactions': (body.get('reactions') or {}).get('summary', {}).get('total_count'),
                'comments': (body.get('comments') or {}).get('summary', {}).get('total_count'),
                'shares': (body.get('shares') or {}).get('count')})
    return results


def _load_common():
    spec = importlib.util.spec_from_file_location('ares_shein_single_meta', BASE / 'scripts/ares-meta-common.py')
    if spec is None or spec.loader is None:
        raise RouteBlocked('canonical credential helper unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare(request, config, common, token):
    pre = _batch(common, token, [
        {'name': 'account', 'path': 'act_' + account_id(), 'params': {'fields': 'id,name,currency,timezone_name,account_status,disable_reason,user_tasks'}},
        {'name': 'identity', 'path': 'me', 'params': {'fields': 'id,name,client_business_id'}},
        {'name': 'campaigns', 'path': 'act_' + account_id() + '/campaigns', 'params': {'fields': 'id,name,status,daily_budget', 'limit': 500}}])
    a = pre['account']
    if (a.get('id') != 'act_' + account_id() or a.get('name') != account_alias() or a.get('currency') != 'USD'
            or a.get('timezone_name') != str(account_timezone()) or a.get('account_status') != 1
            or a.get('disable_reason') != 0 or 'ADVERTISE' not in (a.get('user_tasks') or [])):
        raise RouteBlocked('live account identity, health or access mismatch')
    if str(pre['identity'].get('id')) != SYSTEM_USER_ID or str(pre['identity'].get('client_business_id')) != BUSINESS_ID:
        raise RouteBlocked('corporate credential identity mismatch')
    inventory = _complete_edge(pre['campaigns'])
    sources = [x for x in inventory if re.match(r'^[0-9]+\s*-', str(x.get('name') or ''))
               and int(re.match(r'^[0-9]+', x['name']).group()) == int(request['source_number'])]
    if len(sources) != 1:
        raise RouteBlocked('source campaign missing or ambiguous')
    cid = sources[0]['id']
    raw = _batch(common, token, [
        {'name': 'campaign', 'path': cid, 'params': {'fields': 'id,account_id,name,status,objective,daily_budget,bid_strategy,buying_type,special_ad_categories,special_ad_category_country'}},
        {'name': 'adsets', 'path': cid + '/adsets', 'params': {'fields': 'id,name,status,start_time,billing_event,optimization_goal,targeting,attribution_spec,promoted_object,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities', 'limit': 50}},
        {'name': 'ads', 'path': cid + '/ads', 'params': {'fields': 'id,name,status,source_ad_id,adset_id,creative{id,name,object_story_id,effective_object_story_id,object_story_spec,url_tags,degrees_of_freedom_spec}', 'limit': 50}}])
    sets = [x for x in _complete_edge(raw['adsets']) if x.get('status') not in {'DELETED', 'ARCHIVED'}]
    ads = [x for x in _complete_edge(raw['ads']) if x.get('status') not in {'DELETED', 'ARCHIVED'}]
    if len(sets) != 1 or not 1 <= len(ads) <= 5:
        raise RouteBlocked('single-clone route requires one adset and one through five ads')
    # An existing-post source can omit object_story_spec; resolve one verified lineage hop.
    missing = [x for x in ads if not (x.get('creative') or {}).get('object_story_spec')]
    if missing:
        if any(not x.get('source_ad_id') or str(x['source_ad_id']) == '0' for x in missing):
            raise RouteBlocked('source post lacks a resolvable ad lineage')
        lineage = _batch(common, token, [{'name': str(x['id']), 'path': str(x['source_ad_id']), 'params': {
            'fields': 'id,creative{effective_object_story_id,object_story_spec}'}} for x in missing])
        for ad in missing:
            parent = lineage[str(ad['id'])].get('creative') or {}
            if parent.get('effective_object_story_id') != ad['creative'].get('effective_object_story_id') or not parent.get('object_story_spec'):
                raise RouteBlocked('upstream Page/post lineage does not match')
            ad['_reference_story'] = parent['object_story_spec']
    source = {'campaign': raw['campaign'], 'adset': sets[0], 'ads': ads}
    number = next_campaign_numbers(inventory, 1)[0]
    compiled_request = copy.deepcopy(request)
    if request.get('mode', 'pure_clone') != 'pure_clone':
        from .shein_media_handoff import load_ready_assets
        compiled_request['_resolved_assets'] = load_ready_assets(request, CURRENT_PROFILE.get(), BASE, common, token)
    compiler_config = copy.deepcopy(config['accounts'][account_id()])
    if CURRENT_PROFILE.get():
        compiler_config['shein_profile'] = CURRENT_PROFILE.get()
    draft = build_manifest(compiled_request, source, number, compiler_config)
    pages = {str(_story(x)['page_id']) for x in ads}
    if len(pages) != 1:
        raise RouteBlocked('source uses multiple Pages')
    page_id = next(iter(pages))
    gate = _batch(common, token, [
        {'name': 'page', 'path': page_id, 'params': {'fields': 'id,name,access_token'}},
        {'name': 'assignment', 'path': page_id + '/assigned_users', 'params': {'business': BUSINESS_ID, 'fields': 'id,name,tasks', 'limit': 100}},
        {'name': 'pixels', 'path': 'act_' + account_id() + '/adspixels', 'params': {'fields': 'id,name', 'limit': 100}}])
    page_token = gate['page'].pop('access_token', None)
    if gate['page'].get('id') != page_id or not page_token:
        raise RouteBlocked('Page read identity unavailable')
    if not any(str(x.get('id')) == SYSTEM_USER_ID and 'ADVERTISE' in x.get('tasks', []) for x in _complete_edge(gate['assignment'])):
        raise RouteBlocked('Page ADVERTISE assignment missing')
    pixel = sets[0]['promoted_object']['pixel_id']
    if not any(str(x.get('id')) == str(pixel) for x in _complete_edge(gate['pixels'])):
        raise RouteBlocked('source pixel not associated with account')
    validate_account_policy(Manifest.from_dict(draft), config)
    manifest = prevalidate_payload(draft, MediaRegistry(BASE / 'data/ares/meta-ads/engine-v3/media-registry.json'))
    return {'source': source, 'account': a, 'prerequisites': gate, 'number': number,
            'page_id': page_id, 'manifest': manifest,
            'new_media_assets': compiled_request.get('_resolved_assets', [])}, page_token


def _readback(common, token, campaign_id):
    live = _batch(common, token, [
        {'name': 'campaign', 'path': campaign_id, 'params': {'fields': 'id,account_id,name,status,effective_status,daily_budget,bid_strategy,start_time'}},
        {'name': 'adsets', 'path': campaign_id + '/adsets', 'params': {'fields': 'id,name,status,start_time,targeting,attribution_spec,promoted_object,billing_event,optimization_goal,is_dynamic_creative', 'limit': 50}},
        {'name': 'ads', 'path': campaign_id + '/ads', 'params': {'fields': 'id,name,status,adset_id,source_ad_id,issues_info,creative{id,object_story_id,effective_object_story_id,object_story_spec,url_tags}', 'limit': 50}},
        {'name': 'budgets', 'path': 'act_' + account_id() + '/campaigns', 'params': {'fields': 'id,status,daily_budget', 'limit': 500}}])
    for key in ['adsets', 'ads', 'budgets']:
        _complete_edge(live[key])
    return live


def run_request(request: dict[str, Any], *, confirm_execute: bool = False) -> dict[str, Any]:
    request = copy.deepcopy(request)
    if set(request) - REQUEST_FIELDS:
        raise RouteBlocked('unknown request field')
    row = lookup_account(request.get('account', ''))
    path = BASE / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json'
    if path.exists():
        profile = json.loads(path.read_text())['profiles'][row['account_id']]
        from .shein_general import authorize
        authorize(request, profile)
        if request.get('mode') == 'from_zero_prestaged' and not request.get('source_number'):
            if not profile.get('reference_campaign_number'):
                raise RouteBlocked('empty account requires an approved same-account creation specification')
            request['source_number'] = profile['reference_campaign_number']
    else:
        raise RouteBlocked('canonical account profile source unavailable for every requester')
    marker = CURRENT_PROFILE.set(profile)
    try:
        return _run_bound_request(request, confirm_execute=confirm_execute)
    finally:
        CURRENT_PROFILE.reset(marker)


def _run_bound_request(request: dict[str, Any], *, confirm_execute: bool = False) -> dict[str, Any]:
    import subprocess
    validate_request(request)
    catalog_account = lookup_account(request['account'])
    if catalog_account.get('account_id') != account_id():
        raise RouteBlocked('single-clone account catalog binding mismatch')
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc)
    received, timing_basis = request_clock(request)
    if received and received > started_at:
        raise RouteBlocked('request receipt timestamp is in the future')
    destination = (CURRENT_PROFILE.get() or {}).get('destination_base')
    if CURRENT_PROFILE.get() and not destination:
        raise RouteBlocked('account has no approved destination/reference; onboarding prerequisite, not requester restriction')
    scope = subprocess.run(['python3', str(BASE / 'scripts/mgs-domain-scope.py'), 'check', '--agent', 'ares', destination or 'yolokfx.com'],
                           capture_output=True, text=True, timeout=20)
    if scope.returncode != 0:
        raise RouteBlocked('operational domain scope rejected')
    auth = json.loads((BASE / 'data/authorized-users.json').read_text())
    if request['authorized_by'] not in auth['agents']['ares']['authorized_user_discord_ids']:
        raise RouteBlocked('canonical requester authorization absent')
    config = json.loads((BASE / 'data/ares/meta-ads/engine-v3/config.json').read_text())
    registered = config.get('accounts', {}).get(account_id()) or {}
    runtime = registered.get('single_clone_runtime') or {}
    if runtime.get('enabled') is not True or registered.get('alias') != account_alias():
        raise RouteBlocked('single-clone runtime registration disabled or mismatched')
    operation = json.loads((BASE / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    if operation.get('operation_id') != 'SHEIN-US-DIRECT':
        raise RouteBlocked('operation contract mismatch')
    rid = request['request_id']
    state_dir = BASE / 'data/ares/meta-ads/state/shein-campaigns/single-clone' / rid
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / 'state.json'
    lock_path = state_dir.parent / ('account-' + account_id() + '.lock')
    with lock_path.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RouteBlocked('single-clone account already has an in-flight request') from exc
        old = json.loads(state_path.read_text()) if state_path.exists() else None
        if old and old.get('request') != request:
            raise RouteBlocked('request_id reused with different immutable parameters')
        common_module = _load_common()
        token, _ = common_module.get_token_from_1password(registered['token_item'])
        common = ReadOnlyClient(common_module)
        state = old
        page_token = None
        resume_phases = {'ENGINE_PENDING', 'RECOVERY_PENDING', 'POSTPROCESS_PENDING', 'COMPLETE_PAUSED', 'COMPLETE_FUTURE_ACTIVE'}
        if not state or state.get('phase') not in resume_phases:
            if aware_time(request['start_time']) <= started_at:
                raise RouteBlocked('requested schedule is no longer future; no implicit date adjustment')
            prepared, page_token = _prepare(request, config, common, token)
            state = {'schema_version': 1, 'request': request, 'phase': 'PREPARED', **prepared}
            atomic_json(state_path, state)
            atomic_json(state_dir / 'manifest-sealed.json', state['manifest'])
        manifest = Manifest.from_dict(state['manifest'])
        validate_account_policy(manifest, config)
        dry_engine = CampaignEngine(config, transport_factory=lambda account: FakeBatchTransport(account))
        plan = dry_engine.dry_run(manifest)
        timings: dict[str, Any] = {'preparation_ms': round((time.perf_counter() - started) * 1000, 3)}
        if not confirm_execute:
            # A dry-run never enters execute, including when inspecting a resumable request.
            return {'status': 'DRY_RUN_OK', 'request_id': rid, 'account_id': account_id(),
                    'source_campaign_id': state['source']['campaign']['id'], 'number': state['number'],
                    'name': manifest.campaigns[0].name, 'budget_usd': budget_minor(request['budget_usd']) / 100,
                    'start_time': manifest.campaigns[0].start_time, 'delivery_status': request['status'],
                    'plan': plan['plan'], 'timings': timings, 'campaign_writes': 0,
                    'read_http_requests': common.http_requests, 'logical_gets': common.logical_gets}
        # Seal request-scoped authority before the first engine call; crashes resume this exact manifest.
        try:
            if not state.get('engine_result'):
                if state['phase'] == 'PREPARED':
                    http, inventory, _ = common.graph_get('act_' + account_id() + '/campaigns', token,
                                                          {'fields': 'id,name,status', 'limit': 500})
                    if http != 200:
                        raise RouteBlocked('final slot reconciliation failed')
                    rows = _complete_edge(inventory)
                    if next_campaign_numbers(rows, 1)[0] != state['number'] or any(x.get('name') == manifest.campaigns[0].name for x in rows):
                        raise RouteBlocked('target sequential slot changed before write; prepare same request again')
                state['phase'] = 'ENGINE_PENDING'
                atomic_json(state_path, state)
                secret = os.environ.get('ARES_META_APP_SECRET')
                if config.get('require_appsecret_proof') is True and not secret:
                    raise RouteBlocked('required corporate app proof unavailable')
                engine = CampaignEngine(config, transport_factory=lambda account: GraphBatchTransport(
                    account, manifest.graph_version, token, app_secret=secret))
                tick = time.perf_counter()
                result = engine.execute(manifest)
                timings['engine_ms'] = round((time.perf_counter() - tick) * 1000, 3)
                state['engine_result'] = result
                if result.get('status') == 'PARTIAL_DEFERRED_QUOTA':
                    state.pop('engine_result', None)
                    state['phase'] = 'RECOVERY_PENDING'
                    atomic_json(state_path, state)
                    return {'status': 'RECOVERY_PENDING', 'request_id': rid, 'retry_after_seconds': result.get('retry_after_seconds'),
                            'campaign_ids': result.get('campaign_ids'), 'timings': timings}
                if result.get('status') not in {'COMPLETE_PAUSED', 'COMPLETE_FUTURE_ACTIVE'} or len(result.get('campaign_ids') or []) != 1:
                    state.pop('engine_result', None)
                    raise RouteBlocked('engine did not reach one complete campaign in requested delivery state')
                state['phase'] = 'POSTPROCESS_PENDING'
                atomic_json(state_path, state)
            tick = time.perf_counter()
            cid = state['engine_result']['campaign_ids'][0]
            live = _readback(common, token, cid)
            warnings = verify_readback(state['manifest'], state['source'], live)
            posts = [x['creative']['effective_object_story_id'] for x in live['ads']['data']]
            if state['manifest']['execution_mode'] == 'pure_clone':
                social = read_social(common, token, state['page_id'], posts, page_token=page_token)
            else:
                from .shein_media_handoff import finalize_ready_assets
                finalize_ready_assets(state, live, BASE, common, token)
                social = []
            timings['postprocess_ms'] = round((time.perf_counter() - tick) * 1000, 3)
            finished_at = datetime.now(timezone.utc)
            timings['runner_total_ms'] = round((time.perf_counter() - started) * 1000, 3)
            timings['request_to_readback_ms'] = round((finished_at - received).total_seconds() * 1000, 3) if received else None
            summary = {'status': state['engine_result']['status'], 'request_id': rid, 'account_id': account_id(), 'number': state['number'],
                'campaign_id': cid, 'name': live['campaign']['name'], 'source_campaign_id': state['source']['campaign']['id'],
                'budget_usd': budget_minor(request['budget_usd']) / 100, 'start_time': live['campaign']['start_time'],
                'ads': len(live['ads']['data']), 'posts_preserved': state['manifest']['execution_mode'] == 'pure_clone', 'social': social, 'warnings': warnings,
                'account_active_daily_budget_usd': sum(int(x.get('daily_budget') or 0) for x in live['budgets']['data'] if x.get('status') == 'ACTIVE') / 100,
                'request_active_budget_delta_usd': budget_minor(request['budget_usd']) / 100 if request['status'] == 'ACTIVE' else 0, 'timings': timings, 'read_http_requests': common.http_requests,
                'logical_gets': common.logical_gets, 'engine_replayed': bool(state['engine_result'].get('idempotent_replay')),
                'timing_basis': timing_basis}
            state.update(phase=state['engine_result']['status'], final_readback=live, summary=summary, completed_at=finished_at.isoformat())
            state.pop('last_error_type', None)
            atomic_json(state_path, state)
            audit = BASE / 'data/ares/meta-ads/audit/shein/campaigns/single-clone' / (rid + '-final.json')
            atomic_json(audit, state)
            return summary
        except Exception as exc:
            if state.get('phase') in {'ENGINE_PENDING', 'RECOVERY_PENDING', 'POSTPROCESS_PENDING'}:
                state['phase'] = 'POSTPROCESS_PENDING' if state.get('engine_result') else 'RECOVERY_PENDING'
                state['last_error_type'] = type(exc).__name__
                atomic_json(state_path, state)
            raise


def add_parser(subparsers):
    command = subparsers.add_parser('single-clone', help='One account-scoped PAUSED SHEIN pure clone through Engine v3')
    command.add_argument('--input', type=Path, required=True)
    command.add_argument('--confirm-execute', action='store_true')
    command.add_argument('--dry-run', action='store_true')
    campaign = subparsers.add_parser('campaign', help='Same SHEIN creation/clone pipeline for all canonical managers/accounts')
    campaign.add_argument('--input', type=Path, required=True)
    campaign.add_argument('--confirm-execute', action='store_true')
    campaign.add_argument('--dry-run', action='store_true')
    lookup = subparsers.add_parser('account-lookup', help='Read canonical exact-name account/manager/channel mapping')
    lookup.add_argument('--account', required=True)
    lookup.add_argument('--manager-code', choices=['G001', 'G002', 'G003', 'G004', 'G005', 'G006'])
    lookup.add_argument('--channel-id')


def cli_run(args):
    if args.dry_run and args.confirm_execute:
        raise RouteBlocked('dry-run and execute confirmation are mutually exclusive')
    request = json.loads(args.input.read_text())
    if not isinstance(request, dict):
        raise RouteBlocked('request must be a JSON object')
    try:
        return run_request(request, confirm_execute=args.confirm_execute)
    except RouteBlocked:
        raise
    except ValueError as exc:
        raise RouteBlocked(str(exc)) from exc
    except Exception as exc:
        # Never expose a raw provider exception, URL or credential in the operational CLI.
        raise RouteBlocked('runtime failure; resumable state retained; type=' + type(exc).__name__) from exc
