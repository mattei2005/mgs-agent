#!/usr/bin/env python3
"""One-shot controlled write for Elena pg_22091 at account midnight.

Rodolfo-approved 2026-06-19:
- keep current Elena campaigns only;
- set each campaign daily budget to USD 25;
- keep 1 adset per campaign and 3 ads in that adset;
- pause the other adset/ad group;
- remove USD 2 bid cap by switching kept adset to LOWEST_COST_WITHOUT_CAP when Meta accepts it;
- disable Meta automated PAUSE rules.

Never prints tokens. Writes audit JSON with safe payloads.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
AUDIT_DIR = BASE / 'audit' / 'controlled-write'
COMMON_PATH = Path('/root/mgs-agent/scripts/ares-meta-common.py')
GRAPH_VERSION = 'v25.0'
ACCOUNT_ID = '1356770869843984'
TARGET_CAMPAIGN_IDS = [
    '120248940367540604',  # Elena 4
    '120248940367280604',  # Elena 2
    '120248940367270604',  # Elena 3
    '120248940367260604',  # Elena 5
    '120248940291730604',  # Elena 1
]
PAUSE_RULE_IDS = [
    '1706384407070888',  # DESATIVAR ANÚNCIOS SEM RESULTADOS
    '1142483632283037',  # DESATIVAR ANÚNCIOS RUINS
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
    if isinstance(payload, dict):
        return common.safe_meta_error(payload)
    return {'raw': str(payload)[:1000]}


def graph_get(common, token, path, params):
    return common.graph_get(path, token, params)[:2]


def graph_post(common, token, path, params, dry_run=False):
    clean = {k: v for k, v in params.items() if v is not None}
    if dry_run:
        return 0, {'dry_run': True, 'path': path, 'params': clean}
    body = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)) for k, v in clean.items()}
    body['access_token'] = token
    req = urllib.request.Request(
        f'https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip("/")}',
        data=urllib.parse.urlencode(body).encode('utf-8'),
        headers={'User-Agent': 'mgs-ares-meta-ads/controlled-write'},
    )
    try:
        common._throttle_before_request()
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:1000]}


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
        with urllib.request.urlopen(next_url, timeout=45) as resp:
            payload = json.loads(resp.read().decode('utf-8', 'replace'))
    return rows


def mo_from_actions(actions):
    total = 0.0
    for a in actions or []:
        if a.get('action_type') == 'complete_registration':
            try:
                total += float(a.get('value') or 0)
            except Exception:
                pass
    return total


def adset_metrics(common, token, adset_ids):
    if not adset_ids:
        return {}
    since = (utc_now().date() - timedelta(days=2)).isoformat()
    until = utc_now().date().isoformat()
    rows = graph_all(common, token, f'act_{ACCOUNT_ID}/insights', {
        'level': 'adset',
        'fields': 'adset_id,adset_name,spend,actions,date_start,date_stop',
        'time_range': json.dumps({'since': since, 'until': until}),
        'time_increment': 'all_days',
        'filtering': json.dumps([{'field': 'adset.id', 'operator': 'IN', 'value': adset_ids}]),
        'limit': '200',
    })
    out = {aid: {'spend': 0.0, 'MO': 0.0, 'CPMO': None} for aid in adset_ids}
    for r in rows:
        aid = str(r.get('adset_id') or '')
        spend = float(r.get('spend') or 0)
        mo = mo_from_actions(r.get('actions'))
        rec = out.setdefault(aid, {'spend': 0.0, 'MO': 0.0, 'CPMO': None})
        rec['spend'] += spend
        rec['MO'] += mo
    for rec in out.values():
        rec['CPMO'] = (rec['spend'] / rec['MO']) if rec['MO'] > 0 else None
    return out


def choose_keep_adset(adsets, ads_by_adset, metrics):
    def score(a):
        aid = a.get('id')
        m = metrics.get(aid) or {}
        active_ads = sum(1 for ad in ads_by_adset.get(aid, []) if ad.get('effective_status') == 'ACTIVE' or ad.get('status') == 'ACTIVE')
        mo = float(m.get('MO') or 0)
        cpmo = m.get('CPMO')
        cpmo_score = -(float(cpmo)) if cpmo is not None else -999999
        conjunto01 = 1 if re.search(r'\b01\b', a.get('name') or '') else 0
        return (mo, cpmo_score, active_ads, conjunto01)
    return sorted(adsets, key=score, reverse=True)[0]


def verify_campaign(common, token, campaign_id):
    stc, c = graph_get(common, token, campaign_id, {'fields': 'id,name,status,effective_status,daily_budget'})
    adsets = graph_all(common, token, f'{campaign_id}/adsets', {'fields': 'id,name,status,effective_status,bid_amount,bid_strategy', 'limit': 20})
    ads = graph_all(common, token, f'{campaign_id}/ads', {'fields': 'id,name,status,effective_status,adset_id', 'limit': 50})
    return {'campaign_status': stc, 'campaign': c, 'adsets': adsets, 'ads': ads}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true', help='Perform writes. Omit for dry-run.')
    ap.add_argument('--account-id', default=ACCOUNT_ID)
    args = ap.parse_args()
    dry_run = not args.execute
    common = load_common()
    token, field = common.get_token_from_1password()
    audit = {
        'created_at': utc_now().isoformat(),
        'mode': 'execute' if args.execute else 'dry_run',
        'account_id': args.account_id,
        'target_campaign_ids': TARGET_CAMPAIGN_IDS,
        'token_report': {'item': 'Token Meta API', 'field': field, 'len': len(token)},
        'writes': [],
        'campaigns': [],
        'rule_updates': [],
        'errors': [],
    }
    try:
        # Idempotently disable Meta automated PAUSE rules.
        for rid in PAUSE_RULE_IDS:
            st, p = graph_post(common, token, rid, {'status': 'DISABLED'}, dry_run=dry_run)
            stv, pv = graph_get(common, token, rid, {'fields': 'id,name,status,execution_spec'}) if not dry_run else (0, {'dry_run': True})
            audit['rule_updates'].append({'rule_id': rid, 'post_status': st, 'post_payload': p if st in (0, 200) else safe_error(common, p), 'verify_status': stv, 'verify': pv if stv in (0, 200) else safe_error(common, pv)})

        for cid in TARGET_CAMPAIGN_IDS:
            stc, camp = graph_get(common, token, cid, {'fields': 'id,name,status,effective_status,daily_budget'})
            if stc != 200:
                audit['errors'].append({'campaign_id': cid, 'stage': 'campaign_get', 'error': safe_error(common, camp)})
                continue
            adsets = graph_all(common, token, f'{cid}/adsets', {'fields': 'id,name,status,effective_status,bid_amount,bid_strategy', 'limit': 20})
            ads = graph_all(common, token, f'{cid}/ads', {'fields': 'id,name,status,effective_status,adset_id', 'limit': 50})
            ads_by_adset = {}
            for ad in ads:
                ads_by_adset.setdefault(ad.get('adset_id'), []).append(ad)
            metrics = adset_metrics(common, token, [a['id'] for a in adsets])
            keep = choose_keep_adset(adsets, ads_by_adset, metrics)
            keep_id = keep['id']
            rec = {'campaign_before': camp, 'keep_adset_id': keep_id, 'keep_adset_name': keep.get('name'), 'adsets_before': adsets, 'adset_metrics_3d': metrics, 'actions': []}
            # Campaign budget to USD25 = 2500 minor units.
            st, p = graph_post(common, token, cid, {'daily_budget': '2500'}, dry_run=dry_run)
            rec['actions'].append({'target': cid, 'type': 'campaign_budget_2500', 'status': st, 'payload': p if st in (0, 200) else safe_error(common, p)})
            for adset in adsets:
                aid = adset['id']
                if aid == keep_id:
                    # Activate kept adset and attempt to remove bid cap. Meta may reject bid_strategy changes; capture evidence.
                    st, p = graph_post(common, token, aid, {'status': 'ACTIVE', 'bid_strategy': 'LOWEST_COST_WITHOUT_CAP'}, dry_run=dry_run)
                    rec['actions'].append({'target': aid, 'type': 'keep_adset_active_lowest_cost_without_cap', 'status': st, 'payload': p if st in (0, 200) else safe_error(common, p)})
                    if st not in (0, 200):
                        # Fallback: keep active, try bid_amount=0 only if bid_strategy failed.
                        st2, p2 = graph_post(common, token, aid, {'status': 'ACTIVE', 'bid_amount': '0'}, dry_run=dry_run)
                        rec['actions'].append({'target': aid, 'type': 'fallback_keep_adset_active_bid_amount_0', 'status': st2, 'payload': p2 if st2 in (0, 200) else safe_error(common, p2)})
                    for ad in ads_by_adset.get(aid, []):
                        st3, p3 = graph_post(common, token, ad['id'], {'status': 'ACTIVE'}, dry_run=dry_run)
                        rec['actions'].append({'target': ad['id'], 'type': 'keep_ad_active', 'status': st3, 'payload': p3 if st3 in (0, 200) else safe_error(common, p3)})
                else:
                    st, p = graph_post(common, token, aid, {'status': 'PAUSED'}, dry_run=dry_run)
                    rec['actions'].append({'target': aid, 'type': 'pause_removed_adset', 'status': st, 'payload': p if st in (0, 200) else safe_error(common, p)})
                    for ad in ads_by_adset.get(aid, []):
                        st3, p3 = graph_post(common, token, ad['id'], {'status': 'PAUSED'}, dry_run=dry_run)
                        rec['actions'].append({'target': ad['id'], 'type': 'pause_removed_ad', 'status': st3, 'payload': p3 if st3 in (0, 200) else safe_error(common, p3)})
            rec['verify_after'] = {'dry_run': True} if dry_run else verify_campaign(common, token, cid)
            audit['campaigns'].append(rec)
    except Exception as e:
        audit['errors'].append({'stage': 'top_level', 'error': str(e)[:1500]})
    ok = not audit['errors'] and all((a.get('status') in (0, 200)) for c in audit['campaigns'] for a in c.get('actions', []))
    audit['final'] = {'ok': ok, 'dry_run': dry_run, 'campaign_count': len(audit['campaigns']), 'error_count': len(audit['errors'])}
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIT_DIR / f'elena-midnight-structure-adjust-{utc_now().strftime("%Y%m%dT%H%M%SZ")}.json'
    write_json(out, audit)
    # Compact Discord-safe output.
    rows = []
    for c in audit['campaigns']:
        camp = c.get('campaign_before') or {}
        rows.append({
            'campaign_id': camp.get('id'),
            'name': camp.get('name'),
            'keep_adset': c.get('keep_adset_name'),
            'actions': len(c.get('actions') or []),
        })
    print(json.dumps({'ok': ok, 'dry_run': dry_run, 'audit': str(out), 'campaign_count': len(rows), 'rows': rows, 'errors': audit['errors']}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
