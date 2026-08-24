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
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
POLICY_DEFAULT = BASE / 'policies' / 'openzedfinanzas_cc_es_hoa_v2.json'
STATE_DIR = BASE / 'state' / 'hoa'
REPORT_DIR = BASE / 'reports' / 'hoa'
COMMON_PATH = Path('/root/mgs-agent/scripts/ares-meta-common.py')
SB_COMMON_PATH = Path('/root/mgs-agent/scripts/ares-smartbidding-common.py')


def load_common():
    spec = importlib.util.spec_from_file_location('ares_meta_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load common module from {COMMON_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_smartbidding_common():
    spec = importlib.util.spec_from_file_location('ares_smartbidding_common', SB_COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load Smart Bidding helper from {SB_COMMON_PATH}')
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


def display_campaign_name(name: str | None) -> str:
    text = str(name or '').strip()
    # Display-only normalization for Discord tables. It keeps the human
    # campaign identity visible on mobile: "Elena Santana - ES - ESP - 009".
    # Does not rename Meta objects; raw campaign_name remains in audit.
    m = re.match(r'(.+?)\s-\s([A-Z]{2})\s-\s([A-Z]{3})\s-\s\(pg[_-]?\d+\)\s-\s(.+)$', text)
    if m:
        suffix = m.group(4).strip()
        suffix = re.sub(r'^(\d{1,2})$', lambda x: f'{int(x.group(1)):03d}', suffix)
        suffix = re.sub(r'(\s-\s)(\d{1,2})$', lambda x: f'{x.group(1)}{int(x.group(2)):03d}', suffix)
        return f'{m.group(1).strip()} - {m.group(2)} - {m.group(3)} - {suffix}'
    return re.sub(r'(\s-\s)(\d{1,2})$', lambda m: f'{m.group(1)}{int(m.group(2)):03d}', text)


def parse_meta_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
    except Exception:
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception:
            return None


def fmt_start_date(campaign: dict, tz: ZoneInfo) -> str:
    started = parse_meta_time(campaign.get('start_time') or campaign.get('created_time'))
    if not started:
        return 'n/i'
    return started.astimezone(tz).strftime('%d/%m/%Y')


def compact_action(action: str) -> str:
    mapping = {
        'eu manteria em observação': 'observar',
        'eu pausaria/seguraria': 'pausar/seg',
        'eu substituiria': 'substituir',
    }
    return mapping.get(action, action)


def campaign_sequence(name: str | None) -> int:
    text = str(name or '').strip()
    m = re.search(r'(?:^|\s-\s)(\d{1,3})$', text)
    if m:
        return int(m.group(1))
    return 9999


def status_rank(status: str | None) -> int:
    order = {'ACTIVE': 0, 'IN_PROCESS': 1, 'WITH_ISSUES': 2, 'PAUSED': 3, 'HIST': 9, 'UNKNOWN': 10}
    return order.get(str(status or '').upper(), 8)


def is_live_status(status: str | None) -> bool:
    return str(status or '').upper() in {'ACTIVE', 'PAUSED', 'IN_PROCESS', 'WITH_ISSUES'}


def dedupe_hist_rows(rows: list[dict]) -> list[dict]:
    """Hide historical-only duplicates when a live campaign with the same display name exists.

    The HOA report merges live campaign objects with insight history. If a campaign
    appears in both streams under the same human name/number, keep the live row in
    Discord and leave the technical duplicate only in JSON audit/snapshots.
    """
    live_keys = {
        str(row.get('campaign_display_name') or row.get('campaign') or '').strip().lower()
        for row in rows
        if is_live_status(row.get('effective_status'))
    }
    if not live_keys:
        return rows
    deduped = []
    for row in rows:
        key = str(row.get('campaign_display_name') or row.get('campaign') or '').strip().lower()
        if str(row.get('effective_status') or '').upper() == 'HIST' and key in live_keys:
            continue
        deduped.append(row)
    return deduped


def country_vertical_from_name(name: str | None, op_cfg: dict) -> str:
    text = str(name or '')
    parts = [p.strip() for p in text.split(' - ')]
    country = parts[1] if len(parts) >= 3 and re.fullmatch(r'[A-Z]{2}', parts[1]) else op_cfg.get('country') or ''
    vertical = op_cfg.get('vertical') or 'CC'
    return f'{country} / {vertical}' if country else vertical


def recommendation_id(now_local: datetime, seq: int) -> str:
    return f'REC-{now_local.strftime("%Y%m%d-%H%M")}-{seq:03d}'


def simulated_action_for_hoa(replacement: bool, today_bad: bool, pacing: str) -> str:
    if replacement and pacing != 'melhorando':
        return 'eu substituiria'
    if today_bad:
        return 'eu pausaria/seguraria'
    return 'eu manteria em observação'


def management_scope(op_cfg: dict) -> dict:
    return op_cfg.get('management_scope') or {}


def manual_hold_pg_ids(op_cfg: dict) -> set[str]:
    return {str(x.get('pg_id')) for x in (management_scope(op_cfg).get('manual_holds') or []) if x.get('pg_id')}


def active_focus_pg_ids(op_cfg: dict) -> set[str]:
    return {str(x.get('pg_id')) for x in (management_scope(op_cfg).get('active_focus') or []) if x.get('pg_id')}


def normalize_bid_strategy(value: str | None) -> str:
    strategy = str(value or 'UNKNOWN').strip().upper()
    aliases = {
        'LOWEST_COST_NO_CAP': 'LOWEST_COST_WITHOUT_CAP',
        'LOWEST_COST_WITHOUT_BID_CAP': 'LOWEST_COST_WITHOUT_CAP',
    }
    return aliases.get(strategy, strategy)


def campaign_age_days(campaign: dict, now_local: datetime) -> float | None:
    created = parse_meta_time(campaign.get('created_time') or campaign.get('start_time'))
    if not created:
        return None
    return (now_local - created.astimezone(now_local.tzinfo)).total_seconds() / 86400


def grace_block_reason(campaign: dict, op_cfg: dict, now_local: datetime) -> str | None:
    age = campaign_age_days(campaign, now_local)
    grace_days = float((op_cfg.get('learning_grace') or {}).get('action_grace_days') or 3)
    test_name = str((op_cfg.get('test_grace') or {}).get('name_contains') or 'TEST').upper()
    if age is None or age >= grace_days:
        return None
    if test_name in str(campaign.get('name') or '').upper():
        return 'TEST < 3d'
    return 'learning < 3d'


def classify_bad_day(metrics: dict, min_spend: float, min_mo: float, cpmo_target: float) -> tuple[bool, str]:
    spend = float(metrics.get('spend') or 0)
    mo = float(metrics.get('MO') or 0)
    cpmo = metrics.get('CPMO')
    if spend < min_spend or mo < min_mo:
        return False, 'volume insuficiente'
    if cpmo is not None and float(cpmo) > cpmo_target:
        return True, 'CPMO alto'
    return False, 'ok'


def is_in_management_scope(op_cfg: dict, pg_id: str) -> tuple[bool, str | None]:
    if pg_id in manual_hold_pg_ids(op_cfg):
        return False, 'manual_hold'
    focus = active_focus_pg_ids(op_cfg)
    if focus and pg_id not in focus:
        return False, 'outside_active_focus'
    return True, None


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
    fields = 'id,name,effective_status,status,daily_budget,lifetime_budget,start_time,created_time,stop_time,bid_strategy'
    params = {
        'fields': fields,
        'limit': 500,
        'effective_status': json.dumps(['ACTIVE', 'PAUSED', 'IN_PROCESS', 'WITH_ISSUES']),
    }
    rows = graph_all(common, f'act_{account_id}/campaigns', token, params)
    return {str(r.get('id')): r for r in rows if r.get('id')}


def fetch_adset_bid_strategies(common, token: str, account_id: str) -> dict[str, str]:
    rows = graph_all(common, f'act_{account_id}/adsets', token, {'fields': 'id,campaign_id,bid_strategy', 'limit': 500})
    by_campaign: dict[str, set[str]] = {}
    for row in rows:
        cid = str(row.get('campaign_id') or '')
        if cid:
            by_campaign.setdefault(cid, set()).add(normalize_bid_strategy(row.get('bid_strategy')))
    result = {}
    for cid, values in by_campaign.items():
        if 'COST_CAP' in values:
            result[cid] = 'COST_CAP'
        elif 'LOWEST_COST_WITHOUT_CAP' in values:
            result[cid] = 'LOWEST_COST_WITHOUT_CAP'
        elif 'LOWEST_COST' in values:
            result[cid] = 'LOWEST_COST'
        else:
            result[cid] = sorted(values)[0] if values else 'UNKNOWN'
    return result


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


def fmt_percent(v) -> str:
    if v is None or (isinstance(v, float) and (math.isinf(v) or math.isnan(v))):
        return '-'
    return f'{float(v):+.1f}%'


def build_roi_summary(op_cfg: dict, report_date: str, focus_spend_by_pg: dict[str, float]) -> list[dict]:
    config = op_cfg.get('smart_bidding_roi') or {}
    if not config.get('enabled'):
        return []
    rows = []
    try:
        smartbidding = load_smartbidding_common()
    except Exception as exc:
        for pg_id, spend in sorted(focus_spend_by_pg.items()):
            rows.append({
                'pg_id': pg_id,
                'period': report_date,
                'currency': str(config.get('currency') or 'USD'),
                'meta_spend': round(float(spend or 0), 2),
                'drip_revenue': None,
                'broadcast_revenue': None,
                'total_revenue': None,
                'roi_drip_pct': None,
                'roi_broadcast_pct': None,
                'roi_total_pct': None,
                'status': 'SB helper indisponível',
                'error': str(exc)[:300],
            })
        return rows
    for pg_id, spend in sorted(focus_spend_by_pg.items()):
        base = {
            'pg_id': pg_id,
            'period': report_date,
            'currency': str(config.get('currency') or 'USD'),
            'meta_spend': round(float(spend or 0), 2),
        }
        try:
            revenue = smartbidding.fetch_page_revenue(report_date=report_date, pg_id=pg_id, config=config)
            matched = int(revenue.get('matched_rows') or 0)
            drip = float(revenue.get('drip_revenue') or 0)
            broadcast = float(revenue.get('broadcast_revenue') or 0)
            total = float(revenue.get('total_revenue') or 0)
            status = 'OK'
            if matched <= 0:
                status = 'SB sem linha'
            elif float(spend or 0) <= 0:
                status = 'Meta sem spend'
            base.update({
                'matched_rows': matched,
                'drip_revenue': round(drip, 2),
                'broadcast_revenue': round(broadcast, 2),
                'total_revenue': round(total, 2),
                'revenue_residual': round(float(revenue.get('revenue_residual') or 0), 2),
                'roi_drip_pct': round(smartbidding.compute_roi_pct(drip, spend), 2) if matched > 0 else None,
                'roi_broadcast_pct': round(smartbidding.compute_roi_pct(broadcast, spend), 2) if matched > 0 else None,
                'roi_total_pct': round(smartbidding.compute_roi_pct(total, spend), 2) if matched > 0 else None,
                'status': status,
                'revenue_source': revenue.get('source'),
                'spend_source': config.get('spend_source'),
                'credential_report': revenue.get('token_report'),
            })
        except Exception as exc:
            base.update({
                'drip_revenue': None,
                'broadcast_revenue': None,
                'total_revenue': None,
                'roi_drip_pct': None,
                'roi_broadcast_pct': None,
                'roi_total_pct': None,
                'status': 'SB erro',
                'error': str(exc)[:300],
            })
        rows.append(base)
    return rows


def trunc(s, n=34):
    s = str(s)
    return s if len(s) <= n else s[: max(0, n-3)] + '...'


def output_table(title: str, rows: list[dict], columns: list[tuple[str, str]], prefix: str | None = None, rows_per_block: int = 8) -> str:
    lines = []
    if prefix:
        lines += [prefix, '']
    if not rows:
        lines += ['```text', title, '', 'Sem campanhas no foco deste checkpoint.', '```']
        return '\n'.join(lines)

    rendered = [{k: trunc(row.get(k, ''), 34) for k, _ in columns} for row in rows]
    total_blocks = max(1, math.ceil(len(rendered) / rows_per_block))
    for block_idx in range(total_blocks):
        block = rendered[block_idx * rows_per_block:(block_idx + 1) * rows_per_block]
        widths = {k: len(label) for k, label in columns}
        for row in block:
            for k, _ in columns:
                widths[k] = max(widths[k], len(str(row.get(k, ''))))
        header = ' | '.join(label.ljust(widths[k]) for k, label in columns)
        sep = '-|-'.join('-' * widths[k] for k, _ in columns)
        block_title = title if total_blocks == 1 else f'{title} — bloco {block_idx + 1}/{total_blocks}'
        lines += ['```text', block_title, '', header, sep]
        for row in block:
            lines.append(' | '.join(str(row.get(k, '')).ljust(widths[k]) for k, _ in columns))
        lines.append('```')
        if block_idx + 1 < total_blocks:
            lines.append('')
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
    ap.add_argument('--report-date', help='YYYY-MM-DD in account timezone; defaults to today')
    ap.add_argument('--checkpoint-time', default=None, help='HH:MM in account timezone; defaults to now, or 22:00 for historical dates')
    args = ap.parse_args()

    common = load_common()
    policy = load_json(Path(args.policy))
    op_cfg = load_json(BASE / 'operations' / f'{args.operation_id}.json')
    token, _field = common.get_token_from_1password()
    tz = ZoneInfo(args.account_tz)
    real_now_local = utc_now().astimezone(tz)
    if args.report_date:
        today = date.fromisoformat(args.report_date)
        checkpoint_time = args.checkpoint_time or ('22:00' if today < real_now_local.date() else real_now_local.strftime('%H:%M'))
        hour, minute = [int(x) for x in checkpoint_time.split(':', 1)]
        now_local = datetime.combine(today, time(hour, minute), tzinfo=tz)
    else:
        now_local = real_now_local
        today = now_local.date()
    d1 = today - timedelta(days=1)
    d2 = today - timedelta(days=2)
    d3 = today - timedelta(days=3)

    checkpoint = now_local.strftime('%H:%M')
    is_final = checkpoint.startswith('22:')
    weights = policy.get('hoa_weights') or {'today': 0.5, 'yesterday': 0.3, 'day_before_yesterday': 0.2}
    cpmo_target = float((policy.get('hoa') or {}).get('target_cpmo_usd') or (policy.get('initial_cpmo_baseline') or {}).get('suggested_initial_CPMO_target_usd') or 2.0)
    bad_day_gates = policy.get('bad_day_gates') or {}
    min_spend = float(bad_day_gates.get('minimum_spend_usd') or 10.0)
    min_mo = float(bad_day_gates.get('minimum_MO') or 5.0)
    replacement_required = int(bad_day_gates.get('bad_days_required_for_replacement') or 2)
    complete_days_window = int(bad_day_gates.get('complete_days_window') or 3)
    daily_cap = float((policy.get('budget') or {}).get('daily_account_cap_usd') or 300.0)
    test_share = float((policy.get('budget') or {}).get('creative_test_share') or 0.2)

    account_name = fetch_account_name(common, token, args.account_id)
    campaigns = fetch_campaigns(common, token, args.account_id)
    adset_bids = fetch_adset_bid_strategies(common, token, args.account_id)
    for cid, bid in adset_bids.items():
        if cid in campaigns and (bid == 'COST_CAP' or not campaigns[cid].get('bid_strategy')):
            campaigns[cid]['bid_strategy'] = bid
    insights = fetch_insights(common, token, args.account_id, d3.isoformat(), today.isoformat())

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

    focus_pg_ids = active_focus_pg_ids(op_cfg)
    focus_spend_by_pg = {pg_id: 0.0 for pg_id in focus_pg_ids}
    for row in insights:
        if row.get('date_start') != today.isoformat():
            continue
        pg_id = page_id_from_name(row.get('campaign_name'))
        if focus_pg_ids and pg_id not in focus_pg_ids:
            continue
        focus_spend_by_pg.setdefault(pg_id, 0.0)
        focus_spend_by_pg[pg_id] += float(row.get('spend') or 0)
    for cid, camp in campaigns.items():
        cname = camp.get('name') or cid
        pg_id = page_id_from_name(cname)
        if focus_pg_ids and pg_id not in focus_pg_ids:
            continue
        by_campaign.setdefault(cid, {'campaign_id': cid, 'campaign_name': cname, 'days': {}})

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
        d3_m = days.get(d3.isoformat(), {'spend': 0, 'MO': 0, 'CPMO': None})

        y_bad, y_reason = classify_bad_day(y_m, min_spend, min_mo, cpmo_target)
        d2_bad, d2_reason = classify_bad_day(d2_m, min_spend, min_mo, cpmo_target)
        d3_bad, d3_reason = classify_bad_day(d3_m, min_spend, min_mo, cpmo_target)
        today_bad, today_reason = classify_bad_day(today_m, min_spend, min_mo, cpmo_target)
        bad_complete = int(y_bad) + int(d2_bad) + int(d3_bad)

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
        campaign_obj = campaigns.get(cid) or {}
        bid_strategy = normalize_bid_strategy(campaign_obj.get('bid_strategy'))
        grace_reason = grace_block_reason(campaign_obj, op_cfg, now_local)
        cost_cap_excluded = bid_strategy == 'COST_CAP'
        action_eligible = not cost_cap_excluded and grace_reason is None
        replacement = bad_complete >= replacement_required and action_eligible
        pg_id = page_id_from_name(cname)
        is_focus_page = bool(focus_pg_ids and pg_id in focus_pg_ids)
        watch = replacement or (today_bad and action_eligible) or (weighted_cpmo is not None and weighted_cpmo > cpmo_target)
        if watch or is_focus_page:
            in_scope, scope_reason = is_in_management_scope(op_cfg, pg_id)
            if not in_scope:
                snapshot_campaigns[cid] = {
                    'campaign_name': cname,
                    'today': today_m,
                    'weighted_CPMO': weighted_cpmo,
                    'bad_complete_days': bad_complete,
                    'bad_complete_days_window': complete_days_window,
                    'pacing': pacing,
                    'scope_skip': scope_reason,
                }
                continue
            if cost_cap_excluded:
                status = 'COST_CAP sem ação'
            elif grace_reason:
                status = f'{grace_reason} informativo'
            else:
                status = 'replacement candidate' if replacement and pacing != 'melhorando' else ('hold: pacing melhora' if replacement else ('watchlist' if watch else 'sem alerta'))
            reasons = []
            if y_bad: reasons.append(f'D-1 {y_reason}')
            if d2_bad: reasons.append(f'D-2 {d2_reason}')
            if d3_bad: reasons.append(f'D-3 {d3_reason}')
            if today_bad: reasons.append(f'hoje {today_reason}')
            if cost_cap_excluded: reasons.append('COST_CAP fora de pausa por custo')
            if grace_reason: reasons.append(f'{grace_reason}; sem ação')
            suggested = simulated_action_for_hoa(replacement, today_bad, pacing) if watch and action_eligible else 'sem ação'
            seq = len(watch_rows) + 1
            watch_rows.append({
                'rec_id': recommendation_id(now_local, seq),
                'pg_id': pg_id,
                'page_name': page_name_from_campaign(cname),
                'campaign': cname,
                'campaign_display_name': display_campaign_name(cname),
                'start_date': fmt_start_date(campaign_obj, tz),
                'effective_status': campaign_obj.get('effective_status') or 'HIST',
                'bid_strategy': bid_strategy,
                'spend_today': fmt_money(today_m.get('spend') or 0),
                'mo_today': int(today_m.get('MO') or 0),
                'cpmo_today': fmt_money(today_m.get('CPMO')) if today_m.get('CPMO') is not None else '-',
                'hoa_cpmo': fmt_money(weighted_cpmo),
                'target': fmt_money(cpmo_target),
                'bad_days': f'{bad_complete}/{complete_days_window} completos',
                'pacing': pacing,
                'status': status,
                'suggested_action': compact_action(suggested),
                'reason': '; '.join(reasons) or ('sem alerta' if not watch else 'HOA acima alvo'),
            })
        snapshot_campaigns[cid] = {
            'campaign_name': cname,
            'today': today_m,
            'weighted_CPMO': weighted_cpmo,
            'bad_complete_days': bad_complete,
            'bad_complete_days_window': complete_days_window,
            'bid_strategy': bid_strategy,
            'grace_block': grace_reason,
            'pacing': pacing,
        }

    watch_rows = dedupe_hist_rows(watch_rows)

    for idx, row in enumerate(sorted(
        watch_rows,
        key=lambda r: (
            campaign_sequence(r.get('campaign')),
            status_rank(r.get('effective_status')),
            str(r.get('campaign')),
            str(r.get('rec_id')),
        ),
    ), 1):
        row['rec_id'] = recommendation_id(now_local, idx)
        watch_rows[idx - 1] = row

    budget_left = max(0.0, daily_cap - total_today_spend)
    test_pool = daily_cap * test_share
    test_budget_left = max(0.0, test_pool - min(total_today_spend, test_pool))
    budget_status = 'sem espaço p/ teste' if test_budget_left <= 0 else f'teste livre USD {test_budget_left:.2f}'
    roi_summary = build_roi_summary(op_cfg, today.isoformat(), focus_spend_by_pg)

    event = {
        'operation_id': args.operation_id,
        'account_id': args.account_id,
        'account_name': account_name,
        'created_at': utc_now().isoformat(),
        'local_time': now_local.isoformat(),
        'checkpoint': checkpoint,
        'mode': 'read_only_dry_run_no_meta_write',
        'policy_schema_version': policy.get('schema_version'),
        'target_cpmo_usd': cpmo_target,
        'bad_day_gate': {
            'minimum_spend_usd': min_spend,
            'minimum_MO': min_mo,
            'bad_days_required': replacement_required,
            'complete_days_window': complete_days_window,
        },
        'daily_cap_usd': daily_cap,
        'creative_test_pool_usd': test_pool,
        'today_spend_usd': round(total_today_spend, 2),
        'budget_left_usd': round(budget_left, 2),
        'test_budget_left_usd': round(test_budget_left, 2),
        'roi_mode': (op_cfg.get('smart_bidding_roi') or {}).get('mode'),
        'roi_summary': roi_summary,
        'watch_count': len(watch_rows),
        'watch_rows': watch_rows,
        'campaigns': snapshot_campaigns,
    }
    stamp = utc_now().strftime('%Y%m%dT%H%M%SZ')
    report_path = REPORT_DIR / args.operation_id / f'hoa-{stamp}.json'
    snapshot_path = STATE_DIR / args.operation_id / f'snapshot-{stamp}.json'
    write_json(report_path, event)
    write_json(snapshot_path, event)

    focus_label = ', '.join(sorted(focus_pg_ids)) if focus_pg_ids else 'conta toda'
    title = f'{account_name} — {now_local.strftime("%Y-%m-%d")} — {now_local.strftime("%H:%M %Z")} — HOA gestor — foco {focus_label} — {budget_status}'
    # Output at every checkpoint so Rodolfo can see the manager pass; still concise.
    rows = watch_rows
    if not rows and not args.always_output and not is_final:
        return 0
    if not rows and is_final:
        rows = [{'rec_id':'-', 'campaign_display_name':'-', 'start_date':'-', 'effective_status':'-', 'spend_today':'0.00', 'mo_today':0, 'cpmo_today':'-', 'hoa_cpmo':'-', 'suggested_action':'sem ação', 'reason':'sem campanhas no foco', 'status': budget_status}]
    header_prefix = (
        f'<@344196393512075265> HOA — relatório das {now_local.strftime("%H:%M")} ({args.account_tz}) da página em foco.\n'
        'Estou só analisando as campanhas; não alterei nada na Meta.\n'
        'ROI = cashflow diário da página (receita SB × spend Meta); informativo e sem ação automática.\n'
        'Para registrar uma decisão, responda usando o nome completo da campanha.'
    )
    campaign_block = output_table(
        title,
        rows,
        [('campaign_display_name','Nome campanha'),('start_date','Início'),('effective_status','Status'),('spend_today','Spend'),('mo_today','MO'),('cpmo_today','CPMO'),('hoa_cpmo','HOA'),('suggested_action','Ação'),('reason','Motivo')],
    )
    roi_rows = []
    for item in roi_summary:
        roi_rows.append({
            'pg_id': item.get('pg_id'),
            'meta_spend': fmt_money(item.get('meta_spend')),
            'drip_revenue': fmt_money(item.get('drip_revenue')),
            'total_revenue': fmt_money(item.get('total_revenue')),
            'roi_drip': fmt_percent(item.get('roi_drip_pct')),
            'roi_total': fmt_percent(item.get('roi_total_pct')),
            'status': item.get('status'),
        })
    blocks = [header_prefix]
    if roi_rows:
        blocks.append(output_table(
            f'ROI da página — {today.isoformat()} — USD — informativo',
            roi_rows,
            [('pg_id','PG'),('meta_spend','Spend'),('drip_revenue','Receita Drip'),('total_revenue','Receita Total'),('roi_drip','ROI Drip'),('roi_total','ROI Total'),('status','Status')],
        ))
    blocks.append(campaign_block)
    print('\n\n'.join(blocks))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
