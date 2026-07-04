#!/usr/bin/env python3
"""Create 15 scheduled Elena pg_22091 duplicates to reach 20 campaigns total.

Rodolfo-approved 2026-06-19:
- keep 5 current Elena campaigns;
- create 15 additional functional duplicates from those 5;
- each new campaign: USD 25/day, 1 adset, 3 ads;
- schedule starts between 00:00 and 01:00 Europe/Madrid;
- no bid cap on new adsets (LOWEST_COST_WITHOUT_CAP, no bid_amount);
- use existing source creatives by creative_id to avoid raw creative deep-copy/standard_enhancements.

Never prints tokens. Cleans up partial campaign on failure before continuing.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
AUDIT_DIR = BASE / 'audit' / 'controlled-write'
COMMON_PATH = Path('/root/mgs-agent/scripts/ares-meta-common.py')
GRAPH_VERSION = 'v25.0'
ACCOUNT_ID = '1356770869843984'
SOURCE_CAMPAIGNS = [
    '120248940291730604',  # Elena 1
    '120248940367280604',  # Elena 2
    '120248940367270604',  # Elena 3
    '120248940367540604',  # Elena 4
    '120248940367260604',  # Elena 5
]


def load_common():
    spec = importlib.util.spec_from_file_location('ares_meta_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load common module from {COMMON_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GRAPH_VERSION = GRAPH_VERSION
    return mod


def utc_now():
    return datetime.now(timezone.utc)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def safe_error(common, payload):
    return common.safe_meta_error(payload) if isinstance(payload, dict) else {'raw': str(payload)[:1000]}


def graph_post(common, token, path, params, dry_run=False):
    clean = {k: v for k, v in params.items() if v is not None}
    if dry_run:
        return 0, {'dry_run': True, 'path': path, 'params': clean}
    body = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)) for k, v in clean.items()}
    body['access_token'] = token
    req = urllib.request.Request(
        f'https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip("/")}',
        data=urllib.parse.urlencode(body).encode('utf-8'),
        headers={'User-Agent': 'mgs-ares-meta-ads/bulk-elena-duplicates'},
    )
    try:
        common._throttle_before_request()
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:1200]}


def graph_get(common, token, path, params):
    return common.graph_get(path, token, params)[:2]


def graph_all(common, token, path, params):
    status, payload = graph_get(common, token, path, params)
    if status != 200:
        raise RuntimeError(json.dumps({'status': status, 'error': safe_error(common, payload)}, ensure_ascii=False))
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


def delete_campaign(common, token, cid, audit, reason, dry_run=False):
    st, p = graph_post(common, token, cid, {'status': 'DELETED'}, dry_run=dry_run)
    stv, pv = graph_get(common, token, cid, {'fields': 'id,name,status,effective_status'}) if not dry_run else (0, {'dry_run': True})
    audit.setdefault('cleanups', []).append({'campaign_id': cid, 'reason': reason, 'delete_status': st, 'delete_payload': p if st in (0, 200) else safe_error(common, p), 'verify_status': stv, 'verify': pv if stv in (0, 200) else safe_error(common, pv)})


def existing_elena_names(common, token):
    rows = graph_all(common, token, f'act_{ACCOUNT_ID}/campaigns', {'fields': 'id,name,status,effective_status', 'limit': 500})
    return {r.get('name') for r in rows}, rows


def all_account_adsets(common, token):
    return graph_all(common, token, f'act_{ACCOUNT_ID}/adsets', {'fields': 'id,name,campaign_id,status,effective_status,billing_event,optimization_goal,destination_type,targeting,promoted_object,attribution_spec,bid_strategy,bid_amount', 'limit': 500})


def all_account_ads(common, token):
    return graph_all(common, token, f'act_{ACCOUNT_ID}/ads', {'fields': 'id,name,campaign_id,adset_id,status,effective_status,creative{id,name}', 'limit': 500})


def choose_source_adset(campaign_id, adsets_by_campaign):
    adsets = adsets_by_campaign.get(campaign_id) or []
    if not adsets:
        raise RuntimeError('no_adsets')
    # Prefer Conjunto 01 for consistency if available, then non-deleted stable order.
    adsets_sorted = sorted(adsets, key=lambda a: (0 if '01' in (a.get('name') or '') else 1, 0 if a.get('effective_status') != 'DELETED' else 1, a.get('id') or ''))
    return adsets_sorted[0], adsets


def source_ads(adset_id, ads_by_adset):
    ads = list(ads_by_adset.get(adset_id) or [])
    # Use exactly 3 ads; prefer active, then stable order by name/id.
    ads.sort(key=lambda a: (0 if a.get('effective_status') == 'ACTIVE' or a.get('status') == 'ACTIVE' else 1, a.get('name') or '', a.get('id') or ''))
    selected = [a for a in ads if ((a.get('creative') or {}).get('id'))][:3]
    if len(selected) != 3:
        raise RuntimeError(f'expected_3_ads_with_creatives_got_{len(selected)}')
    return selected


def start_times(tz, count):
    now_local = utc_now().astimezone(tz)
    # If before today's midnight, schedule next local midnight; otherwise next day midnight.
    start_day = now_local.date()
    midnight = datetime.combine(start_day, datetime.min.time(), tzinfo=tz)
    if now_local >= midnight:
        midnight = midnight + timedelta(days=1)
    slots = []
    for i in range(count):
        minute = int(round(i * 60 / max(1, count)))
        if minute >= 60:
            minute = 59
        slots.append(midnight + timedelta(minutes=minute))
    return slots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--timezone', default='Europe/Madrid')
    ap.add_argument('--total-new', type=int, default=15)
    args = ap.parse_args()
    dry_run = not args.execute
    common = load_common()
    token, field = common.get_token_from_1password()
    tz = ZoneInfo(args.timezone)
    stamp = utc_now().strftime('%Y%m%dT%H%M%SZ')
    total_new = args.total_new
    slots = start_times(tz, total_new)
    audit = {
        'created_at': utc_now().isoformat(),
        'mode': 'execute' if args.execute else 'dry_run',
        'account_id': ACCOUNT_ID,
        'source_campaigns': SOURCE_CAMPAIGNS,
        'total_new': args.total_new,
        'target_new_campaigns': total_new,
        'budget_minor_units': '2500',
        'token_report': {'item': 'Token Meta API', 'field': field, 'len': len(token)},
        'created': [],
        'errors': [],
    }
    existing_names, all_campaigns = existing_elena_names(common, token)
    audit['existing_campaign_count'] = len(all_campaigns)
    account_adsets = all_account_adsets(common, token)
    account_ads = all_account_ads(common, token)
    adsets_by_campaign = {}
    for adset in account_adsets:
        adsets_by_campaign.setdefault(adset.get('campaign_id'), []).append(adset)
    ads_by_adset = {}
    for ad in account_ads:
        ads_by_adset.setdefault(ad.get('adset_id'), []).append(ad)
    idx = 0
    try:
        templates = []
        for source_cid in SOURCE_CAMPAIGNS:
            stc, source_campaign = graph_get(common, token, source_cid, {'fields': 'id,name,objective,buying_type,special_ad_categories,status,effective_status'})
            if stc != 200:
                audit.setdefault('skipped_sources', []).append({'source_campaign_id': source_cid, 'stage': 'get_source_campaign', 'error': safe_error(common, source_campaign)})
                continue
            try:
                source_adset, all_source_adsets = choose_source_adset(source_cid, adsets_by_campaign)
                ads = source_ads(source_adset['id'], ads_by_adset)
            except Exception as e:
                audit.setdefault('skipped_sources', []).append({'source_campaign_id': source_cid, 'source_campaign_name': source_campaign.get('name'), 'stage': 'template_build', 'error': str(e)})
                continue
            templates.append({'source_cid': source_cid, 'source_campaign': source_campaign, 'source_adset': source_adset, 'ads': ads})
        if not templates:
            raise RuntimeError('no_usable_source_templates')
        audit['usable_template_count'] = len(templates)
        for i in range(total_new):
                tpl = templates[i % len(templates)]
                source_cid = tpl['source_cid']
                source_campaign = tpl['source_campaign']
                source_adset = tpl['source_adset']
                ads = tpl['ads']
                idx += 1
                n = idx
                start_local = slots[idx - 1]
                base_name = source_campaign.get('name') or f'Elena {source_cid}'
                new_name = f'{base_name} - DUP - {start_local.strftime("%Y%m%d-%H%M")} - {n:02d}'
                seq = 1
                while new_name in existing_names:
                    seq += 1
                    new_name = f'{base_name} - DUP - {start_local.strftime("%Y%m%d-%H%M")} - {n:02d}-{seq:02d}'
                existing_names.add(new_name)
                rec = {'source_campaign_id': source_cid, 'source_campaign_name': base_name, 'new_campaign_name': new_name, 'start_time_local': start_local.isoformat(), 'source_adset_id': source_adset['id'], 'source_ads': [{'id': a['id'], 'creative_id': (a.get('creative') or {}).get('id')} for a in ads], 'steps': []}
                new_cid = None
                try:
                    campaign_params = {
                        'name': new_name,
                        'objective': source_campaign.get('objective'),
                        'buying_type': source_campaign.get('buying_type') or 'AUCTION',
                        'status': 'ACTIVE',
                        'daily_budget': '2500',
                        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
                        'special_ad_categories': source_campaign.get('special_ad_categories') or [],
                        'special_ad_category_country': ['ES'],
                        'start_time': start_local.strftime('%Y-%m-%dT%H:%M:%S%z'),
                    }
                    st, p = graph_post(common, token, f'act_{ACCOUNT_ID}/campaigns', campaign_params, dry_run=dry_run)
                    rec['steps'].append({'step': 'create_campaign', 'status': st, 'payload': p if st in (0, 200, 201) else safe_error(common, p)})
                    if st not in (0, 200, 201) or (not dry_run and not p.get('id')):
                        raise RuntimeError('create_campaign_failed')
                    new_cid = p.get('id') if not dry_run else f'dry_run_campaign_{idx}'
                    rec['new_campaign_id'] = new_cid
                    adset_params = {
                        'name': f'{source_adset.get("name") or "Conjunto 01"} - DUP {idx:02d}',
                        'campaign_id': new_cid,
                        'status': 'ACTIVE',
                        'billing_event': source_adset.get('billing_event'),
                        'optimization_goal': source_adset.get('optimization_goal'),
                        'destination_type': source_adset.get('destination_type'),
                        'targeting': source_adset.get('targeting') or {},
                        'promoted_object': source_adset.get('promoted_object') or {},
                        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
                        'start_time': start_local.strftime('%Y-%m-%dT%H:%M:%S%z'),
                    }
                    st, p = graph_post(common, token, f'act_{ACCOUNT_ID}/adsets', adset_params, dry_run=dry_run)
                    rec['steps'].append({'step': 'create_adset', 'status': st, 'payload': p if st in (0, 200, 201) else safe_error(common, p)})
                    if st not in (0, 200, 201) or (not dry_run and not p.get('id')):
                        raise RuntimeError('create_adset_failed')
                    new_adset_id = p.get('id') if not dry_run else f'dry_run_adset_{idx}'
                    rec['new_adset_id'] = new_adset_id
                    new_ads = []
                    for ad_i, ad in enumerate(ads, 1):
                        creative_id = (ad.get('creative') or {}).get('id')
                        ad_params = {
                            'name': f'{ad.get("name") or "Ad"} - DUP {idx:02d}.{ad_i:02d}',
                            'adset_id': new_adset_id,
                            'status': 'ACTIVE',
                            'creative': {'creative_id': creative_id},
                        }
                        st, p = graph_post(common, token, f'act_{ACCOUNT_ID}/ads', ad_params, dry_run=dry_run)
                        rec['steps'].append({'step': 'create_ad', 'source_ad_id': ad.get('id'), 'creative_id': creative_id, 'status': st, 'payload': p if st in (0, 200, 201) else safe_error(common, p)})
                        if st not in (0, 200, 201) or (not dry_run and not p.get('id')):
                            raise RuntimeError('create_ad_failed')
                        new_ads.append(p.get('id') if not dry_run else f'dry_run_ad_{idx}_{ad_i}')
                    rec['new_ads'] = new_ads
                    if not dry_run:
                        stv, vcamp = graph_get(common, token, new_cid, {'fields': 'id,name,status,effective_status,daily_budget,start_time'})
                        vadsets = graph_all(common, token, f'{new_cid}/adsets', {'fields': 'id,name,status,effective_status,bid_amount,bid_strategy,start_time', 'limit': 10})
                        vads = graph_all(common, token, f'{new_cid}/ads', {'fields': 'id,name,status,effective_status,adset_id', 'limit': 20})
                        rec['verification'] = {'campaign_status': stv, 'campaign': vcamp, 'adsets': vadsets, 'ads': vads}
                        if stv != 200 or len(vadsets) != 1 or len(vads) != 3:
                            raise RuntimeError('verification_failed')
                    audit['created'].append(rec)
                except Exception as e:
                    rec['error'] = str(e)
                    audit['errors'].append(rec)
                    if new_cid and not dry_run:
                        delete_campaign(common, token, new_cid, audit, f'partial_failure:{type(e).__name__}', dry_run=False)
    except Exception as e:
        audit['errors'].append({'stage': 'top_level', 'error': str(e)[:1500]})
    ok = len(audit['created']) == total_new and not audit['errors']
    audit['final'] = {'ok': ok, 'dry_run': dry_run, 'created_count': len(audit['created']), 'error_count': len(audit['errors'])}
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIT_DIR / f'elena-bulk-duplicates-{stamp}.json'
    write_json(out, audit)
    print(json.dumps({'ok': ok, 'dry_run': dry_run, 'audit': str(out), 'created_count': len(audit['created']), 'error_count': len(audit['errors']), 'created_campaign_ids': [r.get('new_campaign_id') for r in audit['created']]}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
