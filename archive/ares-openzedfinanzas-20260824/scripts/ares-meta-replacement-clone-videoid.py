#!/usr/bin/env python3
"""Controlled replacement clone using video_id/image_hash assets, not raw creative specs.

Creates one PAUSED campaign with USD 25/day, one cloned adset, and exactly 3 PAUSED ads.
If the full 3-ad build fails, deletes the partial campaign and writes audit JSON.
Never prints tokens.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
COMMON_PATH = Path('/root/mgs-agent/scripts/ares-meta-common.py')
AUDIT_DIR = BASE / 'audit' / 'clone'


def load_common():
    spec = importlib.util.spec_from_file_location('ares_meta_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load common module from {COMMON_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def utc_now():
    return datetime.now(timezone.utc)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def graph_post(common, path: str, token: str, params: dict):
    clean_params = {k: v for k, v in params.items() if v is not None}
    clean_params['access_token'] = token
    data = urllib.parse.urlencode(clean_params).encode('utf-8')
    url = f'https://graph.facebook.com/{common.GRAPH_VERSION}/{path.lstrip("/")}'
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'mgs-ares-meta-ads/0.2'})
    try:
        common._throttle_before_request()
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode('utf-8', 'replace')
            return resp.status, json.loads(body), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            payload = json.loads(body)
        except Exception:
            payload = {'raw': body[:1000]}
        return e.code, payload, dict(e.headers)


def graph_all(common, path: str, token: str, params: dict):
    status, payload, _ = common.graph_get(path, token, params)
    if status != 200:
        raise RuntimeError(json.dumps({'status': status, 'error': common.safe_meta_error(payload)}, ensure_ascii=False))
    rows = []
    while True:
        rows.extend(payload.get('data') or [])
        next_url = (payload.get('paging') or {}).get('next')
        if not next_url:
            break
        common._throttle_before_request()
        with urllib.request.urlopen(next_url, timeout=60) as resp:
            payload = json.loads(resp.read().decode('utf-8', 'replace'))
    return rows


def mo(actions) -> float:
    total = 0.0
    for a in actions or []:
        if a.get('action_type') == 'complete_registration':
            try:
                total += float(a.get('value') or 0)
            except Exception:
                pass
    return total


def replacement_campaign_name(source_name: str, start_local: datetime, seq: int = 1) -> str:
    parts = [p.strip() for p in source_name.split(' - ')]
    prefix = ' - '.join(parts[:4]) if len(parts) >= 4 else source_name
    return f'{prefix} - RPL - {start_local.strftime("%Y%m%d")} - {seq:02d}'


def scrub_error(common, payload):
    return common.safe_meta_error(payload)


def source_text(asset_feed_spec: dict, key: str, fallback: str = '') -> str:
    arr = asset_feed_spec.get(key) or []
    if not arr:
        return fallback
    first = arr[0] if isinstance(arr[0], dict) else {}
    return first.get('text') or first.get('name') or fallback


def first_asset(creative: dict):
    afs = creative.get('asset_feed_spec') or {}
    videos = afs.get('videos') or []
    images = afs.get('images') or []
    if videos and videos[0].get('video_id'):
        return {'kind': 'video', 'id': videos[0].get('video_id'), 'thumbnail_url': videos[0].get('thumbnail_url')}
    if images and images[0].get('hash'):
        return {'kind': 'image', 'id': images[0].get('hash')}
    if creative.get('video_id'):
        return {'kind': 'video', 'id': creative.get('video_id')}
    if creative.get('image_hash'):
        return {'kind': 'image', 'id': creative.get('image_hash')}
    return None


def build_creative_params(src_creative: dict, idx: int, page_id: str, instagram_user_id: str | None, start_local: datetime, mode: str):
    afs = src_creative.get('asset_feed_spec') or {}
    asset = first_asset(src_creative)
    if not asset:
        raise ValueError('creative_without_video_id_or_image_hash')
    body = source_text(afs, 'bodies', 'Hola, toca el botón para continuar.')
    title = source_text(afs, 'titles', '')
    cta = (afs.get('call_to_action_types') or ['APPLY_NOW'])[0]
    oss = {'page_id': page_id}
    if instagram_user_id:
        oss['instagram_user_id'] = instagram_user_id

    if mode in {'video_data', 'video_data_minimal'}:
        if asset['kind'] != 'video':
            raise ValueError('video_data_mode_requires_video')
        video_data = {
            'video_id': asset['id'],
            'message': body,
        }
        if title:
            video_data['title'] = title
        if asset.get('thumbnail_url'):
            video_data['image_url'] = asset.get('thumbnail_url')
        if mode == 'video_data':
            # Messenger CTA. Do not use messenger_doc as website_url.
            video_data['call_to_action'] = {'type': cta, 'value': {'app_destination': 'MESSENGER'}}
        oss['video_data'] = video_data
        params = {
            'name': f'RPL video_id {start_local.strftime("%Y%m%d")} {idx:02d} - {asset["id"]}',
            'object_story_spec': json.dumps(oss),
        }
        if mode == 'video_data':
            # Do not send standard_enhancements. Keep only safe welcome-message hint.
            params['page_welcome_message'] = json.dumps({'is_user_editing': True})
        return params, asset

    if mode == 'asset_feed_videoid':
        # Keep DCO-like structure but only with create-safe asset references; no messenger_doc/link_urls/raw URLs.
        safe_afs = {
            'videos': [{'video_id': asset['id']}],
            'bodies': [{'text': body}],
            'titles': [{'text': title or body[:40]}],
            'call_to_action_types': [cta],
        }
        if afs.get('ad_formats'):
            safe_afs['ad_formats'] = afs.get('ad_formats')
        params = {
            'name': f'RPL asset_video_id {start_local.strftime("%Y%m%d")} {idx:02d} - {asset["id"]}',
            'object_story_spec': json.dumps(oss),
            'asset_feed_spec': json.dumps(safe_afs),
            'degrees_of_freedom_spec': json.dumps({'creative_features_spec': {'standard_enhancements': {'enroll_status': 'OPT_OUT'}}}),
            'page_welcome_message': json.dumps({'is_user_editing': True}),
        }
        return params, asset

    raise ValueError(f'unknown_creative_mode:{mode}')


def delete_campaign(common, token, campaign_id: str, audit: dict, reason: str):
    st, payload, _ = graph_post(common, campaign_id, token, {'status': 'DELETED'})
    rec = {'campaign_id': campaign_id, 'reason': reason, 'delete_status': st, 'delete_payload': payload}
    st2, verify, _ = common.graph_get(campaign_id, token, {'fields': 'id,name,status,effective_status,daily_budget'})
    rec['verify_status'] = st2
    rec['verify'] = verify if st2 == 200 else common.safe_meta_error(verify)
    audit.setdefault('cleanups', []).append(rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account-id', default='1356770869843984')
    ap.add_argument('--operation-id', default='OpenzedFinanzas-CC-ES')
    ap.add_argument('--loser-campaign-id', default='120248290564280604')
    ap.add_argument('--timezone', default='Europe/Madrid')
    ap.add_argument('--daily-budget-usd', type=float, default=25.0)
    ap.add_argument('--creative-count', type=int, default=3)
    ap.add_argument('--creative-mode', choices=['video_data', 'video_data_minimal', 'asset_feed_videoid'], default='video_data')
    ap.add_argument('--omit-instagram-user-id', action='store_true', help='Do not copy instagram_user_id from source creative; useful when token/ad account lacks IG asset access.')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if args.daily_budget_usd > 25.0:
        raise SystemExit('Refusing to create campaign above USD 25/day')
    if args.creative_count != 3:
        raise SystemExit('Replacement must create exactly 3 ads')

    # Use Graph v25 for this creation flow; read-only crons remain unaffected unless env is inherited.
    os.environ['ARES_META_GRAPH_VERSION'] = os.environ.get('ARES_META_GRAPH_VERSION', 'v25.0')
    common = load_common()
    common.GRAPH_VERSION = os.environ['ARES_META_GRAPH_VERSION']
    token, field = common.get_token_from_1password()

    tz = ZoneInfo(args.timezone)
    now_local = utc_now().astimezone(tz)
    start_local = (now_local + timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
    stamp = utc_now().strftime('%Y%m%dT%H%M%SZ')
    audit = {
        'created_at': utc_now().isoformat(),
        'mode': 'dry_run' if args.dry_run else 'controlled_write_videoid_clone',
        'graph_version': common.GRAPH_VERSION,
        'token_field': field,
        'token_len': len(token),
        'account_id': args.account_id,
        'operation_id': args.operation_id,
        'loser_campaign_id': args.loser_campaign_id,
        'daily_budget_usd': args.daily_budget_usd,
        'start_time_local': start_local.isoformat(),
        'creative_mode': args.creative_mode,
        'steps': [],
        'created': {},
        'errors': [],
    }

    try:
        campaign_fields = 'id,name,objective,buying_type,bid_strategy,status,effective_status,daily_budget,special_ad_categories,source_campaign_id,smart_promotion_type'
        st, source_campaign, _ = common.graph_get(args.loser_campaign_id, token, {'fields': campaign_fields})
        if st != 200:
            audit['errors'].append({'step': 'get_source_campaign', 'error': scrub_error(common, source_campaign)})
            raise RuntimeError('source_campaign_unreadable')
        audit['source_campaign'] = source_campaign

        adset_fields = 'id,name,campaign_id,status,effective_status,billing_event,optimization_goal,destination_type,targeting,promoted_object,attribution_spec,start_time,end_time,bid_strategy,bid_amount'
        source_adsets = graph_all(common, f'{args.loser_campaign_id}/adsets', token, {'fields': adset_fields, 'limit': 100})
        audit['source_adsets_count'] = len(source_adsets)
        if not source_adsets:
            raise RuntimeError('source_campaign_has_no_adsets')
        canonical_adset = source_adsets[0]
        promoted = canonical_adset.get('promoted_object') or {}
        page_id = promoted.get('page_id')
        if not page_id:
            raise RuntimeError('source_adset_missing_page_id')

        since = (now_local.date() - timedelta(days=2)).isoformat()
        until = now_local.date().isoformat()
        insight_rows = graph_all(common, f'act_{args.account_id}/insights', token, {
            'level': 'ad',
            'fields': 'campaign_id,campaign_name,ad_id,ad_name,spend,actions,date_start,date_stop',
            'time_increment': '1',
            'time_range': json.dumps({'since': since, 'until': until}),
            'limit': 500,
        })
        by_ad = {}
        for r in insight_rows:
            aid = r.get('ad_id')
            if not aid:
                continue
            a = by_ad.setdefault(aid, {'ad_id': aid, 'ad_name': r.get('ad_name'), 'campaign_id': r.get('campaign_id'), 'campaign_name': r.get('campaign_name'), 'spend': 0.0, 'MO': 0.0})
            a['spend'] += float(r.get('spend') or 0)
            a['MO'] += mo(r.get('actions'))
        ranked = []
        for a in by_ad.values():
            if a['spend'] < 5 or a['MO'] < 2:
                continue
            a['CPMO'] = a['spend'] / a['MO'] if a['MO'] else None
            ranked.append(a)
        ranked.sort(key=lambda x: x['CPMO'] if x['CPMO'] is not None else 9999)

        account_ads = graph_all(common, f'act_{args.account_id}/ads', token, {
            'fields': 'id,name,campaign_id,adset_id,status,effective_status,creative{id,name,object_story_spec,asset_feed_spec,effective_object_story_id,object_type,url_tags,degrees_of_freedom_spec}',
            'limit': 500,
        })
        ad_map = {a.get('id'): a for a in account_ads}
        winners = []
        seen_assets = set()
        for r in ranked:
            ad = ad_map.get(r['ad_id'])
            creative = (ad or {}).get('creative') or {}
            asset = first_asset(creative)
            if not asset:
                continue
            asset_key = (asset['kind'], asset['id'])
            if asset_key in seen_assets:
                continue
            seen_assets.add(asset_key)
            winners.append({**r, 'source_ad': ad, 'creative_id': creative.get('id'), 'asset': asset})
            if len(winners) >= args.creative_count:
                break
        audit['winner_selection'] = [
            {k: (round(v, 4) if isinstance(v, float) else v) for k, v in w.items() if k not in {'source_ad'}}
            for w in winners
        ]
        if len(winners) != 3:
            raise RuntimeError(f'not_enough_winners_with_assets:{len(winners)}')

        source_name = source_campaign.get('name') or f'campaign_{args.loser_campaign_id}'
        existing_campaigns = graph_all(common, f'act_{args.account_id}/campaigns', token, {'fields': 'id,name,status,effective_status', 'limit': 500})
        existing_names = {c.get('name') for c in existing_campaigns}
        seq = 1
        new_campaign_name = replacement_campaign_name(source_name, start_local, seq)
        while new_campaign_name in existing_names:
            seq += 1
            new_campaign_name = replacement_campaign_name(source_name, start_local, seq)
        audit['new_campaign_name'] = new_campaign_name

        if args.dry_run:
            out = AUDIT_DIR / f'clone-videoid-dry-run-{stamp}.json'
            write_json(out, audit)
            print(json.dumps({'status': 'dry_run_ok', 'audit': str(out), 'new_campaign_name': new_campaign_name, 'winners': audit['winner_selection']}, ensure_ascii=False, indent=2))
            return 0

        campaign_params = {
            'name': new_campaign_name,
            'objective': source_campaign.get('objective'),
            'buying_type': source_campaign.get('buying_type') or 'AUCTION',
            'status': 'PAUSED',
            'daily_budget': str(int(round(args.daily_budget_usd * 100))),
            'bid_strategy': source_campaign.get('bid_strategy'),
            'special_ad_categories': json.dumps(source_campaign.get('special_ad_categories') or []),
            'special_ad_category_country': json.dumps(['ES']),
            'start_time': start_local.strftime('%Y-%m-%dT%H:%M:%S%z'),
        }
        st, payload, _ = graph_post(common, f'act_{args.account_id}/campaigns', token, campaign_params)
        audit['steps'].append({'step': 'create_campaign', 'status': st, 'payload': payload})
        if st not in (200, 201) or not payload.get('id'):
            audit['errors'].append({'step': 'create_campaign', 'error': scrub_error(common, payload)})
            raise RuntimeError('create_campaign_failed')
        new_campaign_id = payload['id']
        audit['created']['campaign_id'] = new_campaign_id

        src = canonical_adset
        adset_params = {
            'name': f"{src.get('name','Adset')} - RPL {start_local.strftime('%Y%m%d')}",
            'campaign_id': new_campaign_id,
            'status': 'PAUSED',
            'billing_event': src.get('billing_event'),
            'optimization_goal': src.get('optimization_goal'),
            'destination_type': src.get('destination_type'),
            'targeting': json.dumps(src.get('targeting') or {}),
            'promoted_object': json.dumps(src.get('promoted_object') or {}),
            'attribution_spec': json.dumps([{'event_type': 'CLICK_THROUGH', 'window_days': 1}]),
            'start_time': start_local.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'bid_strategy': src.get('bid_strategy'),
            'bid_amount': src.get('bid_amount'),
        }
        st, payload, _ = graph_post(common, f'act_{args.account_id}/adsets', token, adset_params)
        audit['steps'].append({'step': 'create_adset', 'source_adset_id': src.get('id'), 'status': st, 'payload': payload})
        if st not in (200, 201) or not payload.get('id'):
            audit['errors'].append({'step': 'create_adset', 'error': scrub_error(common, payload)})
            raise RuntimeError('create_adset_failed')
        new_adset_id = payload['id']
        audit['created']['adsets'] = [new_adset_id]

        created_ads = []
        for idx, w in enumerate(winners, 1):
            src_creative = (w['source_ad'] or {}).get('creative') or {}
            oss = src_creative.get('object_story_spec') or {}
            instagram_user_id = None if args.omit_instagram_user_id else oss.get('instagram_user_id')
            creative_params, asset = build_creative_params(src_creative, idx, page_id, instagram_user_id, start_local, args.creative_mode)
            st, payload, _ = graph_post(common, f'act_{args.account_id}/adcreatives', token, creative_params)
            audit['steps'].append({'step': 'create_adcreative', 'mode': args.creative_mode, 'source_creative_id': src_creative.get('id'), 'asset': asset, 'status': st, 'payload': payload})
            if st not in (200, 201) or not payload.get('id'):
                audit['errors'].append({'step': 'create_adcreative', 'source_creative_id': src_creative.get('id'), 'error': scrub_error(common, payload)})
                raise RuntimeError('create_adcreative_failed')
            new_creative_id = payload['id']
            ad_params = {
                'name': f"Ad RPL {idx:02d} - {asset['kind']} {asset['id']}",
                'adset_id': new_adset_id,
                'status': 'PAUSED',
                'creative': json.dumps({'creative_id': new_creative_id}),
            }
            st2, payload2, _ = graph_post(common, f'act_{args.account_id}/ads', token, ad_params)
            audit['steps'].append({'step': 'create_ad', 'source_ad_id': w['ad_id'], 'new_creative_id': new_creative_id, 'status': st2, 'payload': payload2})
            if st2 not in (200, 201) or not payload2.get('id'):
                audit['errors'].append({'step': 'create_ad', 'source_ad_id': w['ad_id'], 'error': scrub_error(common, payload2)})
                raise RuntimeError('create_ad_failed')
            created_ads.append({'ad_id': payload2['id'], 'creative_id': new_creative_id, 'source_ad_id': w['ad_id'], 'asset': asset})
        audit['created']['ads'] = created_ads

        st, verify_campaign, _ = common.graph_get(new_campaign_id, token, {'fields': 'id,name,status,effective_status,daily_budget,start_time,objective'})
        st_ads, verify_ads_payload, _ = common.graph_get(f'{new_campaign_id}/ads', token, {'fields': 'id,name,status,effective_status,creative{id,name}', 'limit': 20})
        st_adsets, verify_adsets_payload, _ = common.graph_get(f'{new_campaign_id}/adsets', token, {'fields': 'id,name,status,effective_status', 'limit': 20})
        ads = verify_ads_payload.get('data', []) if st_ads == 200 else []
        audit['verification'] = {
            'campaign_status': st,
            'campaign': verify_campaign if st == 200 else scrub_error(common, verify_campaign),
            'ads_status': st_ads,
            'ads': ads if st_ads == 200 else scrub_error(common, verify_ads_payload),
            'adsets_status': st_adsets,
            'adsets': verify_adsets_payload.get('data', []) if st_adsets == 200 else scrub_error(common, verify_adsets_payload),
        }
        if st != 200 or st_ads != 200 or len(ads) != 3:
            audit['errors'].append({'step': 'verification', 'error': f'expected_3_ads_got_{len(ads)}'})
            delete_campaign(common, token, new_campaign_id, audit, 'verification_failed')
            raise RuntimeError('verification_failed')

        out = AUDIT_DIR / f'clone-videoid-success-{stamp}.json'
        write_json(out, audit)
        print(json.dumps({
            'status': 'created_paused',
            'audit': str(out),
            'new_campaign_id': new_campaign_id,
            'new_campaign_name': verify_campaign.get('name'),
            'campaign_status': verify_campaign.get('status'),
            'effective_status': verify_campaign.get('effective_status'),
            'daily_budget': verify_campaign.get('daily_budget'),
            'start_time': verify_campaign.get('start_time'),
            'ads_created': len(ads),
            'adsets_created': len(audit['verification']['adsets']),
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        cid = audit.get('created', {}).get('campaign_id')
        if cid and not audit.get('cleanups'):
            try:
                delete_campaign(common, token, cid, audit, f'exception:{type(e).__name__}')
            except Exception as cleanup_error:
                audit.setdefault('cleanup_errors', []).append(str(cleanup_error))
        audit['final_error'] = str(e)
        out = AUDIT_DIR / f'clone-videoid-failed-{stamp}.json'
        write_json(out, audit)
        print(json.dumps({'status': 'failed', 'audit': str(out), 'error': str(e), 'created_campaign_id': cid}, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
