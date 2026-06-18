#!/usr/bin/env python3
"""Controlled Meta campaign replacement clone for Ares.

Creates a PAUSED replacement campaign from a loser campaign using the best
account-level creatives. Never prints tokens. Writes audit JSON for every step.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
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


def page_id_token(name: str) -> str:
    m = re.search(r'\(\s*(pg[_-]?\d+)\s*\)', name or '', re.I)
    return m.group(1).replace('-', '_').lower() if m else 'pg_unknown'


def base_page_name(name: str) -> str:
    m = re.match(r'(.+?)\s-\s[A-Z]{2}\s-\s', name or '')
    return m.group(1).strip() if m else 'Unknown Page'


def replacement_campaign_name(source_name: str, start_local: datetime, seq: int = 1) -> str:
    parts = [p.strip() for p in source_name.split(' - ')]
    if len(parts) >= 4:
        prefix = ' - '.join(parts[:4])
    else:
        prefix = source_name
    return f'{prefix} - RPL - {start_local.strftime("%Y%m%d")} - {seq:02d}'


def graph_post(common, path: str, token: str, params: dict):
    clean_params = {k: v for k, v in params.items() if v is not None}
    clean_params['access_token'] = token
    data = urllib.parse.urlencode(clean_params).encode('utf-8')
    url = f'https://graph.facebook.com/{common.GRAPH_VERSION}/{path.lstrip("/")}'
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'mgs-ares-meta-ads/0.1'})
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


def clean_creative_spec(spec):
    spec = copy.deepcopy(spec or {})
    # Meta rejects read-only fields inside asset_feed_spec on create. Keep asset ids/hashes/texts.
    def scrub(obj):
        if isinstance(obj, dict):
            for k in list(obj.keys()):
                if k in {'id', 'thumbnail_url', 'url', 'permalink_url'}:
                    # Do not remove adlabel ids; they are nested under adlabels and may be required.
                    if k == 'id' and 'name' in obj and len(obj) <= 2:
                        continue
                    obj.pop(k, None)
                else:
                    scrub(obj[k])
        elif isinstance(obj, list):
            for item in obj:
                scrub(item)
    # Only strip thumbnail_url on videos; preserve adlabel ids to keep customization rules intact.
    for v in (spec.get('asset_feed_spec') or {}).get('videos', []) or []:
        v.pop('thumbnail_url', None)
    return spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account-id', default='1356770869843984')
    ap.add_argument('--operation-id', default='OpenzedFinanzas-CC-ES')
    ap.add_argument('--loser-campaign-id', default='120248290564280604')
    ap.add_argument('--timezone', default='Europe/Madrid')
    ap.add_argument('--daily-budget-usd', type=float, default=25.0)
    ap.add_argument('--creative-count', type=int, default=3)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if args.daily_budget_usd > 25.0:
        raise SystemExit('Refusing to create campaign above USD 25/day')

    common = load_common()
    token, _field = common.get_token_from_1password()
    tz = ZoneInfo(args.timezone)
    now_local = utc_now().astimezone(tz)
    start_local = (now_local + timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
    stamp = utc_now().strftime('%Y%m%dT%H%M%SZ')
    audit = {
        'created_at': utc_now().isoformat(),
        'mode': 'dry_run' if args.dry_run else 'controlled_write_create_paused_campaign',
        'account_id': args.account_id,
        'operation_id': args.operation_id,
        'loser_campaign_id': args.loser_campaign_id,
        'daily_budget_usd': args.daily_budget_usd,
        'max_budget_guardrail_usd': 25.0,
        'start_time_local': start_local.isoformat(),
        'steps': [],
        'created': {},
        'errors': [],
    }

    # Source campaign/adsets/ads.
    campaign_fields = 'id,name,objective,buying_type,bid_strategy,status,effective_status,daily_budget,special_ad_categories,source_campaign_id,smart_promotion_type'
    st, source_campaign, _ = common.graph_get(args.loser_campaign_id, token, {'fields': campaign_fields})
    if st != 200:
        audit['errors'].append({'step': 'get_source_campaign', 'error': common.safe_meta_error(source_campaign)})
        out = AUDIT_DIR / f'clone-attempt-{stamp}.json'; write_json(out, audit); print(json.dumps({'status':'blocked','audit':str(out),'error':'source_campaign_unreadable'}, ensure_ascii=False)); return 1
    audit['source_campaign'] = source_campaign

    adset_fields = 'id,name,campaign_id,status,effective_status,billing_event,optimization_goal,destination_type,targeting,promoted_object,attribution_spec,start_time,end_time,bid_strategy,bid_amount'
    source_adsets = graph_all(common, f'{args.loser_campaign_id}/adsets', token, {'fields': adset_fields, 'limit': 100})
    audit['source_adsets'] = source_adsets

    # Account ad insights and ad/creative map.
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
        'fields': 'id,name,campaign_id,adset_id,status,effective_status,creative{id,name,object_story_spec,asset_feed_spec,effective_object_story_id,object_type,url_tags}',
        'limit': 500,
    })
    ad_map = {a.get('id'): a for a in account_ads}

    winners = []
    seen_creatives = set()
    for r in ranked:
        ad = ad_map.get(r['ad_id'])
        if not ad or not ad.get('creative'):
            continue
        creative_id = ad['creative'].get('id')
        if creative_id in seen_creatives:
            continue
        seen_creatives.add(creative_id)
        winners.append({**r, 'source_ad': ad, 'creative_id': creative_id, 'adset_id': ad.get('adset_id')})
        if len(winners) >= args.creative_count:
            break
    audit['winner_selection'] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in w.items() if k not in {'source_ad'}} for w in winners]
    if len(winners) < args.creative_count:
        audit['errors'].append({'step': 'winner_selection', 'error': f'Only {len(winners)} eligible creatives found'})
        out = AUDIT_DIR / f'clone-attempt-{stamp}.json'; write_json(out, audit); print(json.dumps({'status':'blocked','audit':str(out),'error':'not_enough_creatives'}, ensure_ascii=False)); return 1

    source_name = source_campaign.get('name') or f'campaign_{args.loser_campaign_id}'
    base_new_campaign_name = replacement_campaign_name(source_name, start_local)
    existing_campaigns = graph_all(common, f'act_{args.account_id}/campaigns', token, {'fields': 'id,name,status,effective_status', 'limit': 500})
    existing_names = {c.get('name') for c in existing_campaigns}
    seq = 1
    new_campaign_name = base_new_campaign_name
    while new_campaign_name in existing_names:
        seq += 1
        new_campaign_name = replacement_campaign_name(source_name, start_local, seq)
    audit['new_campaign_name'] = new_campaign_name

    if args.dry_run:
        out = AUDIT_DIR / f'clone-dry-run-{stamp}.json'; write_json(out, audit)
        print(json.dumps({'status': 'dry_run_ok', 'audit': str(out), 'new_campaign_name': new_campaign_name, 'winners': audit['winner_selection']}, ensure_ascii=False, indent=2))
        return 0

    # 1) Create campaign PAUSED with USD 25/day max.
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
        audit['errors'].append({'step': 'create_campaign', 'error': common.safe_meta_error(payload)})
        out = AUDIT_DIR / f'clone-attempt-{stamp}.json'; write_json(out, audit); print(json.dumps({'status':'failed','audit':str(out),'step':'create_campaign'}, ensure_ascii=False)); return 1
    new_campaign_id = payload['id']
    audit['created']['campaign_id'] = new_campaign_id

    # 2) Create only the adsets needed by selected winners, cloning matching source adset specs; map source adset->new adset.
    source_adset_map = {s['id']: s for s in source_adsets}
    needed_source_adset_ids = []
    for w in winners:
        if w['adset_id'] not in needed_source_adset_ids:
            needed_source_adset_ids.append(w['adset_id'])
    new_adsets = {}
    for src_adset_id in needed_source_adset_ids:
        src = source_adset_map.get(src_adset_id) or source_adsets[0]
        params = {
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
        st, payload, _ = graph_post(common, f'act_{args.account_id}/adsets', token, params)
        audit['steps'].append({'step': 'create_adset', 'source_adset_id': src_adset_id, 'status': st, 'payload': payload})
        if st not in (200, 201) or not payload.get('id'):
            audit['errors'].append({'step': 'create_adset', 'source_adset_id': src_adset_id, 'error': common.safe_meta_error(payload)})
            out = AUDIT_DIR / f'clone-attempt-{stamp}.json'; write_json(out, audit); print(json.dumps({'status':'partial_failed','audit':str(out),'created_campaign_id':new_campaign_id,'step':'create_adset'}, ensure_ascii=False)); return 1
        new_adsets[src_adset_id] = payload['id']
    audit['created']['adsets'] = new_adsets

    # 3) Create exactly 3 new creatives and ads, all PAUSED.
    created_ads = []
    for idx, w in enumerate(winners, 1):
        src_ad = w['source_ad']
        src_creative = src_ad.get('creative') or {}
        spec = clean_creative_spec(src_creative)
        creative_params = {
            'name': f"RPL {start_local.strftime('%Y%m%d')} {idx:02d} - {src_creative.get('id')}",
            'object_story_spec': json.dumps(spec.get('object_story_spec') or {}),
            'asset_feed_spec': json.dumps(spec.get('asset_feed_spec') or {}),
            'url_tags': src_creative.get('url_tags'),
        }
        st, payload, _ = graph_post(common, f'act_{args.account_id}/adcreatives', token, creative_params)
        audit['steps'].append({'step': 'create_adcreative', 'source_creative_id': src_creative.get('id'), 'status': st, 'payload': payload})
        creative_for_ad = None
        created_creative_id = None
        if st in (200, 201) and payload.get('id'):
            created_creative_id = payload['id']
            creative_for_ad = {'creative_id': created_creative_id}
        else:
            # Fallback: use existing winning creative so the replacement campaign can still be built paused.
            audit['steps'].append({'step': 'create_adcreative_fallback_existing', 'source_creative_id': src_creative.get('id'), 'reason': common.safe_meta_error(payload)})
            creative_for_ad = {'creative_id': src_creative.get('id')}
        adset_id = new_adsets.get(w['adset_id']) or next(iter(new_adsets.values()))
        ad_params = {
            'name': f"Ad RPL {idx:02d} - from {w['ad_id']}",
            'adset_id': adset_id,
            'status': 'PAUSED',
            'creative': json.dumps(creative_for_ad),
        }
        st2, payload2, _ = graph_post(common, f'act_{args.account_id}/ads', token, ad_params)
        audit['steps'].append({'step': 'create_ad', 'source_ad_id': w['ad_id'], 'status': st2, 'payload': payload2, 'new_creative_id': created_creative_id, 'used_existing_creative_fallback': created_creative_id is None})
        if st2 not in (200, 201) or not payload2.get('id'):
            audit['errors'].append({'step': 'create_ad', 'source_ad_id': w['ad_id'], 'error': common.safe_meta_error(payload2)})
            out = AUDIT_DIR / f'clone-attempt-{stamp}.json'; write_json(out, audit); print(json.dumps({'status':'partial_failed','audit':str(out),'created_campaign_id':new_campaign_id,'step':'create_ad'}, ensure_ascii=False)); return 1
        created_ads.append({'ad_id': payload2['id'], 'source_ad_id': w['ad_id'], 'source_creative_id': src_creative.get('id'), 'new_creative_id': created_creative_id, 'adset_id': adset_id})
    audit['created']['ads'] = created_ads

    # 4) Verify created objects.
    st, verify_campaign, _ = common.graph_get(new_campaign_id, token, {'fields': 'id,name,status,effective_status,daily_budget,start_time,objective'})
    st_ads, verify_ads_payload, _ = common.graph_get(f'{new_campaign_id}/ads', token, {'fields': 'id,name,status,effective_status,creative{id,name}', 'limit': 20})
    audit['verification'] = {'campaign_status': st, 'campaign': verify_campaign, 'ads_status': st_ads, 'ads': verify_ads_payload.get('data', []) if st_ads == 200 else common.safe_meta_error(verify_ads_payload)}
    out = AUDIT_DIR / f'clone-success-{stamp}.json'
    write_json(out, audit)
    print(json.dumps({
        'status': 'created_paused',
        'audit': str(out),
        'new_campaign_id': new_campaign_id,
        'new_campaign_name': verify_campaign.get('name'),
        'campaign_status': verify_campaign.get('status'),
        'daily_budget': verify_campaign.get('daily_budget'),
        'ads_created': len(created_ads),
        'new_creatives_created': sum(1 for a in created_ads if a.get('new_creative_id')),
        'existing_creative_fallbacks': sum(1 for a in created_ads if not a.get('new_creative_id')),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
