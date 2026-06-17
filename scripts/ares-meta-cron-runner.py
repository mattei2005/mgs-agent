#!/usr/bin/env python3
"""Deterministic Ares Meta Ads cron runner.

Modes:
- intraday: read Meta, evaluate R1-R5, write local audit, print sanitized Discord log only on proposed action/error.
- reactivate-all: read Meta paused campaigns, write local audit, print sanitized Discord log only when candidates/error.

No production write is implemented here. This runner is dry-run/read-only until Rodolfo explicitly approves controlled write and the writer is added with GET-after-write validation.
Never prints access tokens or raw credentials.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
COMMON_PATH = '/root/mgs-agent/scripts/ares-meta-common.py'
ACCOUNT_ID_DEFAULT = '1356770869843984'
OPERATION_ID_DEFAULT = 'OpenzedFinanzas-CC-ES'
TOKEN_ITEM = 'Token Meta API'
MAX_ROWS_OUTPUT = 12


def load_common():
    spec = importlib.util.spec_from_file_location('ares_meta_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load common helper: {COMMON_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def ts_slug() -> str:
    return utc_now().strftime('%Y%m%dT%H%M%SZ')


def parse_meta_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        # Meta commonly returns 2026-06-17T10:00:00-0700
        return dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
    except Exception:
        try:
            return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return None


def load_operation(operation_id: str) -> dict:
    return json.loads((BASE / 'operations' / f'{operation_id}.json').read_text())


def load_rules(op: dict) -> dict:
    return json.loads((BASE / 'rules' / f"{op['ruleset']}.json").read_text())


def action_value(row: dict, action_type: str) -> float:
    for action in row.get('actions') or []:
        if action.get('action_type') == action_type:
            try:
                return float(action.get('value') or 0)
            except Exception:
                return 0.0
    return 0.0


def derive_metrics(row: dict) -> dict:
    spend = float(row.get('spend') or 0)
    mo = action_value(row, 'complete_registration')
    cpmo = None if mo <= 0 else spend / mo
    return {'spend': spend, 'MO': mo, 'CPMO': cpmo}


def page_id_from_name(name: str | None) -> str:
    m = re.search(r'\(\s*pg[_-]?(\d+)\s*\)', str(name or ''), re.I)
    return f"pg_{m.group(1)}" if m else 'não identificado'


def country_vertical_from_name(name: str | None, op_cfg: dict) -> str:
    text = str(name or '')
    # Ex.: "Carla Rojas - US - ESP - (pg_22068) - 3" => country US; vertical from operation CC.
    m = re.search(r'\s-\s([A-Z]{2})\s-\s', text)
    country = m.group(1) if m else str(op_cfg.get('country') or 'NA')
    vertical = str(op_cfg.get('vertical') or 'NA')
    return f'{country} / {vertical}'


def fmt_account_title(account_name: str, tz: ZoneInfo, label: str) -> str:
    now = utc_now().astimezone(tz)
    return f'{account_name} — {now.strftime("%Y-%m-%d")} — {now.strftime("%H:%M %Z")} — {label}'


def rule_display(rule: dict) -> str:
    rid = str(rule.get('id') or '').upper()
    desc = str(rule.get('description') or '').strip()
    if rid and desc:
        # Keep Discord table readable but preserve the R-number explicitly.
        short = desc.split('=>', 1)[0].strip()
        return f'{rid} — {short}'
    return rid or 'não identificada'


def cmp_value(actual, op: str, expected) -> bool:
    if actual is None:
        return False
    if op == 'eq':
        return actual == expected
    if op == 'gt':
        return actual > expected
    if op == 'gte':
        return actual >= expected
    if op == 'lt':
        return actual < expected
    if op == 'lte':
        return actual <= expected
    raise ValueError(f'unsupported op: {op}')


def campaign_age_days(campaign: dict, tz: ZoneInfo) -> float | None:
    created = parse_meta_time(campaign.get('created_time'))
    if not created:
        return None
    return (utc_now().astimezone(tz) - created.astimezone(tz)).total_seconds() / 86400


def is_test_grace(campaign: dict, op_cfg: dict, tz: ZoneInfo) -> bool:
    tg = op_cfg.get('test_grace') or {}
    needle = str(tg.get('name_contains') or 'TEST').upper()
    name = str(campaign.get('name') or '').upper()
    if needle not in name:
        return False
    age = campaign_age_days(campaign, tz)
    return age is not None and age < float(tg.get('grace_days') or 3)


def rule_matches(rule: dict, campaign: dict, metrics: dict, op_cfg: dict, tz: ZoneInfo) -> tuple[bool, str | None]:
    if not rule.get('enabled'):
        return False, 'disabled'
    if 'TEST_grace_3_days' in (rule.get('exclusions') or []) and is_test_grace(campaign, op_cfg, tz):
        return False, 'TEST_grace_3_days'
    bid_strategy = str(campaign.get('bid_strategy') or 'UNKNOWN')
    if 'COST_CAP_no_cost_pause' in (rule.get('exclusions') or []) and bid_strategy == 'COST_CAP':
        return False, 'COST_CAP_no_cost_pause'
    for cond in (rule.get('condition') or {}).get('all') or []:
        if 'metric' in cond:
            actual = metrics.get(cond['metric'])
        else:
            actual = campaign.get(cond.get('field'))
        if not cmp_value(actual, cond.get('op'), cond.get('value')):
            return False, None
    return True, None


def graph_get_all(common, token: str, path: str, params: dict) -> list[dict]:
    rows = []
    next_url = None
    current_path = path
    current_params = dict(params)
    while True:
        if next_url:
            # Avoid reconstructing next URL with token in logs; parse only the Graph path and query params.
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(next_url)
            current_path = parsed.path.split('/v20.0/', 1)[-1]
            current_params = {k: v[-1] for k, v in parse_qs(parsed.query).items() if k != 'access_token'}
        status, payload, _headers = common.graph_get(current_path, token, current_params)
        if not (200 <= status < 300):
            raise RuntimeError(json.dumps({'http_status': status, 'error': common.safe_meta_error(payload)}, ensure_ascii=False))
        rows.extend(payload.get('data') or [])
        next_url = ((payload.get('paging') or {}).get('next'))
        if not next_url:
            return rows


def fetch_campaigns(common, token: str, account_id: str) -> dict[str, dict]:
    fields = 'id,name,status,effective_status,created_time,updated_time,bid_strategy,daily_budget,lifetime_budget,objective'
    rows = graph_get_all(common, token, f'act_{account_id}/campaigns', {'fields': fields, 'limit': 200})
    return {r['id']: r for r in rows if r.get('id')}


def fetch_account_name(common, token: str, account_id: str) -> str:
    status, payload, _headers = common.graph_get(f'act_{account_id}', token, {'fields': 'name,account_id'})
    if 200 <= status < 300 and isinstance(payload, dict):
        return str(payload.get('name') or f'act_{account_id}')
    return f'act_{account_id}'


def fetch_adset_bid_strategies(common, token: str, account_id: str) -> dict[str, str]:
    rows = graph_get_all(common, token, f'act_{account_id}/adsets', {'fields': 'id,campaign_id,bid_strategy', 'limit': 200})
    by_campaign: dict[str, set[str]] = {}
    for row in rows:
        cid = row.get('campaign_id')
        if not cid:
            continue
        by_campaign.setdefault(cid, set()).add(row.get('bid_strategy') or 'UNKNOWN')
    out = {}
    for cid, vals in by_campaign.items():
        if 'COST_CAP' in vals:
            out[cid] = 'COST_CAP'
        elif 'LOWEST_COST' in vals:
            out[cid] = 'LOWEST_COST'
        else:
            out[cid] = sorted(vals)[0] if vals else 'UNKNOWN'
    return out


def fetch_today_insights(common, token: str, account_id: str) -> list[dict]:
    fields = 'campaign_id,campaign_name,spend,actions,date_start,date_stop'
    return graph_get_all(
        common,
        token,
        f'act_{account_id}/insights',
        {'level': 'campaign', 'date_preset': 'today', 'fields': fields, 'action_breakdowns': 'action_type', 'limit': 200},
    )


def output_table(title: str, rows: list[dict], columns: list[tuple[str, str]], prefix: str = '') -> str:
    if not rows:
        return ''
    limited = rows[:MAX_ROWS_OUTPUT]
    prepared = []
    for row in limited:
        prepared.append([str(row.get(key, ''))[:44] for key, _label in columns])
    widths = []
    for idx, (_key, label) in enumerate(columns):
        widths.append(max(len(label), *(len(r[idx]) for r in prepared)))
    lines = []
    if prefix:
        lines.append(prefix)
        lines.append('')
    lines.append('```text')
    lines.append(title)
    lines.append('')
    lines.append(' | '.join(label.ljust(widths[idx]) for idx, (_key, label) in enumerate(columns)))
    lines.append('-|-'.join('-' * w for w in widths))
    for vals in prepared:
        lines.append(' | '.join(vals[idx].ljust(widths[idx]) for idx in range(len(widths))))
    if len(rows) > len(limited):
        lines.append(f'... +{len(rows)-len(limited)} linhas no audit local')
    lines.append('```')
    return '\n'.join(lines)


def audit_write(kind: str, event: dict) -> Path:
    out_dir = BASE / 'audit' / kind
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f'{kind}-{ts_slug()}.json'
    path.write_text(json.dumps(event, indent=2, ensure_ascii=False) + '\n')
    return path


def run_intraday(args) -> int:
    common = load_common()
    op_cfg = load_operation(args.operation_id)
    ruleset = load_rules(op_cfg)
    token, token_field = common.get_token_from_1password(TOKEN_ITEM)
    tz = ZoneInfo(args.account_tz or 'Europe/Madrid')
    event = {
        'ts_utc': utc_now().isoformat(),
        'job': 'intraday',
        'operation_id': args.operation_id,
        'account_id': args.account_id,
        'mode': 'dry_run',
        'write_enabled': False,
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'timezone': str(tz),
        'candidates': [],
        'errors': [],
    }
    account_name = f'act_{args.account_id}'
    try:
        account_name = fetch_account_name(common, token, args.account_id)
        campaigns = fetch_campaigns(common, token, args.account_id)
        adset_bids = fetch_adset_bid_strategies(common, token, args.account_id)
        insights = fetch_today_insights(common, token, args.account_id)
        for cid, bid in adset_bids.items():
            if cid in campaigns and not campaigns[cid].get('bid_strategy'):
                campaigns[cid]['bid_strategy'] = bid
        by_prio = sorted(ruleset.get('rules') or [], key=lambda r: int(r.get('priority') or 99))
        for row in insights:
            cid = str(row.get('campaign_id') or '')
            campaign = campaigns.get(cid, {'id': cid, 'name': row.get('campaign_name'), 'effective_status': 'UNKNOWN'})
            metrics = derive_metrics(row)
            for rule in by_prio:
                match, excluded = rule_matches(rule, campaign, metrics, op_cfg, tz)
                if excluded:
                    continue
                if match:
                    campaign_name = campaign.get('name') or row.get('campaign_name')
                    event['candidates'].append({
                        'pg_id': page_id_from_name(campaign_name),
                        'country_vertical': country_vertical_from_name(campaign_name, op_cfg),
                        'rule': rule_display(rule),
                        'status': campaign.get('effective_status'),
                        'action': rule.get('action'),
                        'campaign_id': cid,
                        'campaign_name': campaign_name,
                        'bid_strategy': campaign.get('bid_strategy') or 'UNKNOWN',
                        'spend': round(metrics['spend'], 2),
                        'MO': int(metrics['MO']) if float(metrics['MO']).is_integer() else metrics['MO'],
                        'CPMO': None if metrics['CPMO'] is None else round(metrics['CPMO'], 2),
                        'mode': 'dry_run_no_write',
                    })
                    break
        event['summary'] = {'campaigns_seen': len(campaigns), 'insight_rows': len(insights), 'candidate_count': len(event['candidates'])}
    except Exception as e:
        event['errors'].append(str(e)[:1000])
    audit = audit_write('intraday', event)
    if event['errors']:
        print(output_table(fmt_account_title(account_name, tz, 'Intraday Meta — ERRO'), [{'erro': event['errors'][0], 'audit': str(audit)}], [('erro', 'Erro'), ('audit', 'Audit')], prefix='<@344196393512075265> erro no cron intraday Meta.'))
        return 0
    if event['candidates']:
        rows = event['candidates']
        for r in rows:
            r['CPMO'] = '' if r['CPMO'] is None else r['CPMO']
        print(output_table(fmt_account_title(account_name, tz, 'Intraday Meta — dry-run'), rows, [('pg_id','PG ID'),('country_vertical','País/Vertical'),('rule','Regra usada'),('status','Status')], prefix='<@344196393512075265> dry-run intraday encontrou ações candidatas. Nenhum write foi executado.'))
    return 0


def run_reactivate_all(args) -> int:
    common = load_common()
    op_cfg = load_operation(args.operation_id)
    token, token_field = common.get_token_from_1password(TOKEN_ITEM)
    event = {
        'ts_utc': utc_now().isoformat(),
        'job': 'reactivate_all',
        'operation_id': args.operation_id,
        'account_id': args.account_id,
        'mode': 'dry_run',
        'write_enabled': False,
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'candidates': [],
        'errors': [],
        'exclusion_list': op_cfg.get('reactivate_exclusion_list') or [],
    }
    account_name = f'act_{args.account_id}'
    try:
        account_name = fetch_account_name(common, token, args.account_id)
        campaigns = fetch_campaigns(common, token, args.account_id)
        exclusions = set(op_cfg.get('reactivate_exclusion_list') or [])
        for campaign in campaigns.values():
            if campaign.get('effective_status') != 'PAUSED':
                continue
            if campaign.get('id') in exclusions or campaign.get('name') in exclusions:
                continue
            campaign_name = campaign.get('name')
            event['candidates'].append({
                'pg_id': page_id_from_name(campaign_name),
                'country_vertical': country_vertical_from_name(campaign_name, op_cfg),
                'rule': 'reativar-todas',
                'status': campaign.get('effective_status'),
                'action': 'reactivate_campaign',
                'campaign_id': campaign.get('id'),
                'campaign_name': campaign_name,
                'mode': 'dry_run_no_write',
            })
        event['summary'] = {'campaigns_seen': len(campaigns), 'candidate_count': len(event['candidates'])}
    except Exception as e:
        event['errors'].append(str(e)[:1000])
    audit = audit_write('reactivate-all', event)
    if event['errors']:
        print(output_table(fmt_account_title(account_name, ZoneInfo(args.account_tz or 'Europe/Madrid'), 'Reativar-todas Meta — ERRO'), [{'erro': event['errors'][0], 'audit': str(audit)}], [('erro','Erro'),('audit','Audit')], prefix='<@344196393512075265> erro no cron reativar-todas Meta.'))
        return 0
    if event['candidates']:
        print(output_table(fmt_account_title(account_name, ZoneInfo(args.account_tz or 'Europe/Madrid'), 'Reativar-todas Meta — dry-run'), event['candidates'], [('pg_id','PG ID'),('country_vertical','País/Vertical'),('rule','Regra usada'),('status','Status')], prefix='<@344196393512075265> dry-run reativar-todas encontrou campanhas pausadas. Nenhum write foi executado.'))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--job', choices=['intraday', 'reactivate-all'], required=True)
    ap.add_argument('--operation-id', default=OPERATION_ID_DEFAULT)
    ap.add_argument('--account-id', default=ACCOUNT_ID_DEFAULT)
    ap.add_argument('--account-tz', default='Europe/Madrid')
    args = ap.parse_args()
    if args.job == 'intraday':
        return run_intraday(args)
    return run_reactivate_all(args)


if __name__ == '__main__':
    raise SystemExit(main())
