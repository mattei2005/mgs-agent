#!/usr/bin/env python3
"""Apply an approved Meta naming plan for Ares.

Controlled write approved by Rodolfo. Reads a read-only naming plan JSON and
updates names for adsets, ads and adcreatives. Never prints tokens.
Writes full before/write/after audit.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from collections import OrderedDict

COMMON_PATH = Path('/root/mgs-agent/scripts/ares-meta-common.py')
DEFAULT_PLAN = Path('/root/mgs-agent/data/ares/meta-ads/audit/naming/elena-20260619/elena-naming-plan-readonly.json')
AUDIT_DIR = Path('/root/mgs-agent/data/ares/meta-ads/audit/naming/elena-20260619')
GRAPH_VERSION = 'v25.0'


def load_common():
    spec = importlib.util.spec_from_file_location('ares_meta_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {COMMON_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    setattr(mod, 'GRAPH_VERSION', GRAPH_VERSION)
    return mod


def utc_now():
    return datetime.now(timezone.utc)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def graph_post(common, token: str, path: str, params: dict, dry_run: bool = False):
    clean = {k: v for k, v in params.items() if v is not None}
    if dry_run:
        return 0, {'dry_run': True, 'path': path, 'params': clean}
    body = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)) for k, v in clean.items()}
    body['access_token'] = token
    req = urllib.request.Request(
        f'https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip("/")}',
        data=urllib.parse.urlencode(body).encode('utf-8'),
        headers={'User-Agent': 'mgs-ares-meta-naming/1.0'},
    )
    try:
        common._throttle_before_request()
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode('utf-8', 'replace')
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:1200]}


def graph_get_name(common, token: str, object_id: str, type_name: str, dry_run: bool = False):
    if dry_run:
        return 0, {'id': object_id, 'name': '<dry_run>'}
    # adcreatives do not support effective_status/status fields.
    fields = 'id,name' if type_name == 'adcreative' else 'id,name,effective_status,status'
    status, payload, _ = common.graph_get(object_id, token, {'fields': fields})
    return status, payload


def unique_objects(plan_rows: list[dict], id_field: str, old_field: str, new_field: str, type_name: str) -> list[dict]:
    out: OrderedDict[str, dict] = OrderedDict()
    for row in plan_rows:
        oid = row.get(id_field)
        new = row.get(new_field)
        if not oid or not new:
            continue
        old = row.get(old_field)
        if oid in out:
            if out[oid]['new_name'] != new:
                raise RuntimeError(f'conflicting new_name for {type_name} {oid}: {out[oid]["new_name"]} vs {new}')
            continue
        out[oid] = {'type': type_name, 'id': oid, 'old_name_plan': old, 'new_name': new}
    return list(out.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default=str(DEFAULT_PLAN))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip-adcreatives', action='store_true')
    args = ap.parse_args()

    plan_path = Path(args.plan)
    plan_doc = json.loads(plan_path.read_text())
    rows = plan_doc.get('plan') or []
    if not rows:
        raise SystemExit('empty plan')

    adsets = unique_objects(rows, 'adset_id', 'old_adset_name', 'new_adset_name', 'adset')
    ads = unique_objects(rows, 'ad_id', 'old_ad_name', 'new_ad_name', 'ad')
    creatives = [] if args.skip_adcreatives else unique_objects(rows, 'creative_id', 'old_creative_name', 'new_creative_name', 'adcreative')
    objects = adsets + ads + creatives

    common = load_common()
    token, field = common.get_token_from_1password()
    stamp = utc_now().strftime('%Y%m%dT%H%M%SZ')
    audit = {
        'created_at': utc_now().isoformat(),
        'mode': 'dry_run' if args.dry_run else 'controlled_write_rename',
        'plan': str(plan_path),
        'token_report': {'item': 'Token Meta API', 'field': field, 'len': len(token)},
        'counts': {'adsets': len(adsets), 'ads': len(ads), 'adcreatives': len(creatives), 'total_objects': len(objects)},
        'results': [],
    }

    for obj in objects:
        rec = dict(obj)
        st_before, before = graph_get_name(common, token, obj['id'], obj['type'], dry_run=args.dry_run)
        rec['before_status'] = st_before
        rec['before'] = before if st_before in (0, 200) else common.safe_meta_error(before)
        # Skip if already equal.
        if st_before == 200 and isinstance(before, dict) and before.get('name') == obj['new_name']:
            rec['write_status'] = 'skipped_already_named'
            st_after, after = st_before, before
        else:
            st_write, payload = graph_post(common, token, obj['id'], {'name': obj['new_name']}, dry_run=args.dry_run)
            rec['write_status'] = st_write
            rec['write_payload'] = payload if st_write in (0, 200, 201) else common.safe_meta_error(payload)
            st_after, after = graph_get_name(common, token, obj['id'], obj['type'], dry_run=args.dry_run)
        rec['after_status'] = st_after
        rec['after'] = after if st_after in (0, 200) else common.safe_meta_error(after)
        rec['ok'] = args.dry_run or (st_after == 200 and isinstance(after, dict) and after.get('name') == obj['new_name'])
        audit['results'].append(rec)

    audit['summary'] = {
        'ok': all(r.get('ok') for r in audit['results']),
        'ok_count': sum(1 for r in audit['results'] if r.get('ok')),
        'error_count': sum(1 for r in audit['results'] if not r.get('ok')),
        'by_type': {},
    }
    for typ in ['adset', 'ad', 'adcreative']:
        subset = [r for r in audit['results'] if r['type'] == typ]
        audit['summary']['by_type'][typ] = {
            'total': len(subset),
            'ok': sum(1 for r in subset if r.get('ok')),
            'errors': sum(1 for r in subset if not r.get('ok')),
        }
    out = AUDIT_DIR / f'elena-naming-apply-{stamp}.json'
    write_json(out, audit)
    print(json.dumps({'ok': audit['summary']['ok'], 'dry_run': args.dry_run, 'audit': str(out), **audit['summary']}, ensure_ascii=False, indent=2))
    return 0 if audit['summary']['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
