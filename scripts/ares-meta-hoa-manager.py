#!/usr/bin/env python3
"""Ares HOA manager for Meta Ads (read-only/dry-run).

Computes weighted 3-day HOA, pacing snapshots, loser candidates and budget room.
Never writes to Meta.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
POLICY_DEFAULT = BASE / 'policies' / 'openzedfinanzas_cc_es_hoa_v1.json'
STATE_DIR = BASE / 'state' / 'hoa'
REPORT_DIR = BASE / 'reports' / 'hoa'
COMMON_PATH = Path('/root/mgs-agent/scripts/ares-meta-common.py')


def load_common():
    spec = importlib.util.spec_from_file_location('ares_meta_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load common module from {COMMON_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def page_id_from_name(name: str | None) -> str:
    m = re.search(r'\(\s*pg[_-]?(\d+)\s*\)', str(name or ''), re.I)
    return f"pg_{m.group(1)}" if m else 'não identificado'


def page_name_from_campaign(name: str | None) -> str:
    text = str(name or '').strip()
    m = re.match(r'(.+?)\s-\s[A-Z]{2}\s-\s', text)
    return m.group(1).strip() if m else 'não identificado'


def country_vertical_from_name(name: str | None, op_cfg: dict) -> str:
    text = str(name or '')
    parts = [p.strip() for p in text.split(' - ')]
    country = parts[1] if len(parts) >= 3 and re.fullmatch(r'[A-Z]{2}', parts[1]) else op_cfg.get('country') or ''
    vertical = op_cfg.get('vertical') or 'CC'
    return f'{country} / {vertical}' if country else vertical


def mo_from_actions(actions) -> float:
    total = 0.0
    for a in actions or []:
        if a.get('action_type') == 'complete_registration':
            try:
                total += float(a.get('value') or 0)
            except Exception:
                pass
    return total


def graph_all(common, path: str, token: str, params: dict) -> list[dict]:
    status, payload, _ = common.graph_get(path, token, params)
    if status != 200:
        raise RuntimeError(json.dumps({'status': status, 'error': common.safe_meta_error(payload)}, ensure_ascii=False))
    rows = []
    while True:
        rows.extend(payload.get('data') or [])
        next_url = (payload.get('paging') or {}).get('next')
        if not next_url:
            break
        with urllib.request.urlopen(next_url, timeout=45) as resp:
            payload = json.loads(resp.read().decode('utf-8', 'replace'))
    return rows


def fetch_account_name(common, token: str, account_id: str) -> str:
    status, payload, _ = common.graph_get(f'act_{account_id}', token, {'fields': 'name,account_id,currency,timezone_name'})
    if status == 200:
        return payload.get('name') or f'act_{account_id}'
    return f'act_{account_id}'


def fetch_campaigns(common, token: str, account_id: str) -> dict[str, dict]:
    fields = 'id,name,effective_status,status,daily_budget,lifetime_budget,start_time,stop_time'
    rows = graph_all(common, f'act_{account_id}/campaigns', token, {'fields': fields, 'limit': 500})
    return {str(r.get('id')): r for r in rows if r.get('id')}


def fetch_insights(common, token: str, account_id: str, since: str, until: str) -> list[dict]:
    params = {
        'level': 'campaign',
        'fields': 'campaign_id,campaign_name,spend,actions,date_start,date_stop',
        'time_increment': '1',
        'time_range': json.dumps({'since': since, 'until': until}),
        'limit': '500',
    }
    return graph_all(common, f'act_{account_id}/insights', token, params)


def fmt_money(v) -> str:
    if v is None or (isinstance(v, float) and (math.isinf(v) or math.isnan(v))):
        return 'n/a'
    return f'{float(v):.2f}'


def trunc(s, n=34):
    s = str(s)
    return s if len(s) <= n else s[: max(0, n-3)] + '...'


def output_table(title: str, rows: list[dict], columns: list[tuple[str, str]], prefix: str | None = None) -> str:
    lines = []
    if prefix:
        lines += [prefix, '']
    lines += ['```text', title, '']
    if not rows:
        lines += ['Sem campanhas em watchlist no checkpoint.', '```']
        return '\n'.join(lines)
    rendered = []
    for row in rows:
        rendered.append({k: trunc(row.get(k, ''), 42) for k, _ in columns})
    widths = {k: len(label) for k, label in columns}
    for row in rendered:
        for k, _ in columns:
            widths[k] = max(widths[k], len(str(row.get(k, ''))))
    header = ' | '.join(label.ljust(widths[k]) for k, label in columns)
    sep = '-|-'.join('-' * widths[k] for k, _ in columns)
    lines += [header, sep]
    for row in rendered:
        lines.append(' | '.join(str(row.get(k, '')).ljust(widths[k]) for k, _ in columns))
    lines.append('```')
    return '\n'.join(lines)


def latest_snapshot(operation_id: str) -> dict:
    files = sorted((STATE_DIR / operation_id).glob('snapshot-*.json'))
    if not files:
        return {}
    try:
        return load_json(files[-1])
    except Exception:
        return {}


def status_for_today(curr_cpmo, prev_cpmo, mo_today, spend_today, min_spend):
    if spend_today < min_spend:
        return 'sem volume'
    if curr_cpmo is None:
        return 'ruim sem MO'
    if prev_cpmo is None:
        return 'sem histórico'
    if curr_cpmo <= prev_cpmo * 0.9:
        return 'melhorando'
    if curr_cpmo >= prev_cpmo * 1.1:
        return 'piorando'
    return 'estável'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--operation-id', default='OpenzedFinanzas-CC-ES')
    ap.add_argument('--account-id', default='1356770869843984')
    ap.add_argument('--account-tz', default='Europe/Madrid')
    ap.add_argument('--policy', default=str(POLICY_DEFAULT))
    ap.add_argument('--always-output', action='store_true')
    args = ap.parse_args()

    common = load_common()
    policy = load_json(Path(args.policy))
    op_cfg = load_json(BASE / 'operations' / f'{args.operation_id}.json')
    token, _field = common.get_token_from_1password()
    tz = ZoneInfo(args.account_tz)
    now_local = utc_now().astimezone(tz)
    today = now_local.date()
    d1 = today - timedelta(days=1)
    d2 = today - timedelta(days=2)

    checkpoint = now_local.strftime('%H:%M')
    is_final = checkpoint.startswith('22:')
    weights = policy.get('hoa_weights') or {'today': 0.5, 'yesterday': 0.3, 'day_before_yesterday': 0.2}
    cpmo_target = float((policy.get('hoa') or {}).get('target_cpmo_usd') or (policy.get('initial_cpmo_baseline') or {}).get('suggested_initial_CPMO_target_usd') or 2.0)
    min_spend = float((policy.get('bad_day_gates') or {}).get('minimum_spend_usd') or 5.0)
    min_mo = float((policy.get('bad_day_gates') or {}).get('minimum_MO') or 2.0)
    daily_cap = float((policy.get('budget') or {}).get('daily_account_cap_usd') or 300.0)
    test_share = float((policy.get('budget') or {}).get('creative_test_share') or 0.2)

    account_name = fetch_account_name(common, token, args.account_id)
    campaigns = fetch_campaigns(common, token, args.account_id)
    insights = fetch_insights(common, token, args.account_id, d2.isoformat(), today.isoformat())

    by_campaign: dict[str, dict] = {}
    total_today_spend = 0.0
    for row in insights:
        cid = str(row.get('campaign_id') or '')
        if not cid:
            continue
        cname = row.get('campaign_name') or (campaigns.get(cid) or {}).get('name') or cid
        day = row.get('date_start')
        spend = float(row.get('spend') or 0)
        mo = mo_from_actions(row.get('actions'))
        cpmo = (spend / mo) if mo > 0 else None
        rec = by_campaign.setdefault(cid, {'campaign_id': cid, 'campaign_name': cname, 'days': {}})
        rec['days'][day] = {'spend': spend, 'MO': mo, 'CPMO': cpmo}
        if day == today.isoformat():
            total_today_spend += spend

    prev = latest_snapshot(args.operation_id)
    prev_campaigns = prev.get('campaigns') or {}
    watch_rows = []
    snapshot_campaigns = {}

    for cid, rec in by_campaign.items():
        cname = rec['campaign_name']
        days = rec['days']
        today_m = days.get(today.isoformat(), {'spend': 0, 'MO': 0, 'CPMO': None})
        y_m = days.get(d1.isoformat(), {'spend': 0, 'MO': 0, 'CPMO': None})
        d2_m = days.get(d2.isoformat(), {'spend': 0, 'MO': 0, 'CPMO': None})

        def day_bad(m):
            spend = float(m.get('spend') or 0)
            mo = float(m.get('MO') or 0)
            cpmo = m.get('CPMO')
            if spend < min_spend:
                return False, 'sem volume'
            if mo < min_mo:
                return True, 'MO baixo'
            if cpmo is not None and float(cpmo) > cpmo_target:
                return True, 'CPMO alto'
            return False, 'ok'

        y_bad, y_reason = day_bad(y_m)
        d2_bad, d2_reason = day_bad(d2_m)
        today_bad, today_reason = day_bad(today_m)
        bad_complete = int(y_bad) + int(d2_bad)

        components = []
        for key, day, w in [('today', today.isoformat(), weights.get('today', .5)), ('yesterday', d1.isoformat(), weights.get('yesterday', .3)), ('day_before_yesterday', d2.isoformat(), weights.get('day_before_yesterday', .2))]:
            m = days.get(day)
            if not m:
                continue
            spend = float(m.get('spend') or 0)
            mo = float(m.get('MO') or 0)
            cpmo = m.get('CPMO')
            if spend < min_spend:
                continue
            # Penalize spend with no/low MO for score visibility.
            score_cpmo = float(cpmo) if cpmo is not None else cpmo_target * 2
            components.append((score_cpmo, w))
        if components:
            weighted_cpmo = sum(v*w for v,w in components) / sum(w for _,w in components)
        else:
            weighted_cpmo = None

        prev_cpmo = (((prev_campaigns.get(cid) or {}).get('today') or {}).get('CPMO'))
        pacing = status_for_today(today_m.get('CPMO'), prev_cpmo, today_m.get('MO') or 0, today_m.get('spend') or 0, min_spend)
        replacement = bad_complete >= 2
        watch = replacement or today_bad or (weighted_cpmo is not None and weighted_cpmo > cpmo_target)
        if watch:
            status = 'replacement candidate' if replacement and pacing != 'melhorando' else ('hold: pacing melhora' if replacement else 'watchlist')
            reasons = []
            if y_bad: reasons.append(f'D-1 {y_reason}')
            if d2_bad: reasons.append(f'D-2 {d2_reason}')
            if today_bad: reasons.append(f'hoje {today_reason}')
            watch_rows.append({
                'pg_id': page_id_from_name(cname),
                'page_name': page_name_from_campaign(cname),
                'campaign': cname,
                'hoa_cpmo': fmt_money(weighted_cpmo),
                'target': fmt_money(cpmo_target),
                'bad_days': f'{bad_complete}/2 completos',
                'pacing': pacing,
                'status': status,
                'reason': '; '.join(reasons) or 'HOA acima alvo',
            })
        snapshot_campaigns[cid] = {
            'campaign_name': cname,
            'today': today_m,
            'weighted_CPMO': weighted_cpmo,
            'bad_complete_days': bad_complete,
            'pacing': pacing,
        }

    budget_left = max(0.0, daily_cap - total_today_spend)
    test_pool = daily_cap * test_share
    test_budget_left = max(0.0, test_pool - min(total_today_spend, test_pool))
    budget_status = 'sem espaço p/ teste' if test_budget_left <= 0 else f'teste livre USD {test_budget_left:.2f}'

    event = {
        'operation_id': args.operation_id,
        'account_id': args.account_id,
        'account_name': account_name,
        'created_at': utc_now().isoformat(),
        'local_time': now_local.isoformat(),
        'checkpoint': checkpoint,
        'mode': 'read_only_dry_run_no_meta_write',
        'target_cpmo_usd': cpmo_target,
        'daily_cap_usd': daily_cap,
        'creative_test_pool_usd': test_pool,
        'today_spend_usd': round(total_today_spend, 2),
        'budget_left_usd': round(budget_left, 2),
        'test_budget_left_usd': round(test_budget_left, 2),
        'watch_count': len(watch_rows),
        'watch_rows': watch_rows,
        'campaigns': snapshot_campaigns,
    }
    stamp = utc_now().strftime('%Y%m%dT%H%M%SZ')
    report_path = REPORT_DIR / args.operation_id / f'hoa-{stamp}.json'
    snapshot_path = STATE_DIR / args.operation_id / f'snapshot-{stamp}.json'
    write_json(report_path, event)
    write_json(snapshot_path, event)

    title = f'{account_name} — {now_local.strftime("%Y-%m-%d")} — {now_local.strftime("%H:%M %Z")} — HOA gestor dry-run — {budget_status}'
    # Output at every checkpoint so Rodolfo can see the manager pass; still concise.
    rows = watch_rows[:12]
    if not rows and not args.always_output and not is_final:
        return 0
    if not rows and is_final:
        rows = [{'pg_id':'-', 'page_name':'-', 'hoa_cpmo':'-', 'target':fmt_money(cpmo_target), 'bad_days':'0/2 completos', 'pacing':'sem watchlist', 'status': budget_status}]
    print(output_table(
        title,
        rows,
        [('pg_id','PG ID'),('page_name','Nome da página'),('hoa_cpmo','HOA CPMO'),('target','Alvo'),('bad_days','Dias ruins'),('pacing','Pacing'),('status','Status')],
        prefix='<@344196393512075265> HOA checkpoint read-only. Nenhum write foi executado.'
    ))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
