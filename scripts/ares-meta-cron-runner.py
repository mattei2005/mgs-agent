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
import os
import re
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
COMMON_PATH = '/root/mgs-agent/scripts/ares-meta-common.py'
ACCOUNT_ID_DEFAULT = '1356770869843984'
OPERATION_ID_DEFAULT = 'OpenzedFinanzas-CC-ES'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN'
MAX_ROWS_OUTPUT = 0  # 0 = show every row; Discord poster splits long messages safely.


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


def page_name_from_campaign(name: str | None) -> str:
    text = str(name or '').strip()
    # Ex.: "Carla Rojas - US - ESP - (pg_22068) - 3" => "Carla Rojas".
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


def compact_campaign_name(name: str | None) -> str:
    """Mobile-first label for Discord cron tables; raw name stays in audit."""
    display = display_campaign_name(name)
    parts = [p.strip() for p in display.split(' - ')]
    if len(parts) >= 4:
        first = parts[0].split()[0] if parts[0] else parts[0]
        return f'{first} {parts[1]} {parts[2]} {parts[-1]}'
    return display[:22]


def compact_rec_id(rec_id: str | None) -> str:
    m = re.search(r'(\d{3})$', str(rec_id or ''))
    return f'REC{m.group(1)}' if m else str(rec_id or '')[:6]


def compact_reason(reason: str | None) -> str:
    text = str(reason or '')
    rule = re.search(r'\b(R\d)\b', text)
    rule_text = rule.group(1) if rule else ''
    if text.lower().startswith('learning'):
        return f'Learning<3d; {rule_text}'.strip('; ')
    return text[:24]


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


def recommendation_id(tz: ZoneInfo, seq: int) -> str:
    now = utc_now().astimezone(tz)
    return f'REC-{now.strftime("%Y%m%d-%H%M")}-{seq:03d}'


def fmt_start_date(campaign: dict, tz: ZoneInfo) -> str:
    started = parse_meta_time(campaign.get('start_time') or campaign.get('created_time'))
    if not started:
        return 'não informado'
    return started.astimezone(tz).strftime('%d/%m/%Y')


def management_scope(op_cfg: dict) -> dict:
    return op_cfg.get('management_scope') or {}


def manual_hold_pg_ids(op_cfg: dict) -> set[str]:
    scope = management_scope(op_cfg)
    return {str(x.get('pg_id')) for x in (scope.get('manual_holds') or []) if x.get('pg_id')}


def active_focus_pg_ids(op_cfg: dict) -> set[str]:
    scope = management_scope(op_cfg)
    return {str(x.get('pg_id')) for x in (scope.get('active_focus') or []) if x.get('pg_id')}


def simulated_action_label(action: str | None) -> str:
    mapping = {
        'pause_campaign': 'eu pausaria',
        'reactivate_campaign': 'eu reativaria',
        'replace_campaign': 'eu substituiria',
        'observe_learning': 'OBSERVAR',
    }
    return mapping.get(str(action or ''), f'eu faria {action}' if action else 'avaliar')


def learning_grace_days(op_cfg: dict) -> float:
    learning = op_cfg.get('learning_grace') or {}
    if learning.get('enabled') is False:
        return 0.0
    return float(learning.get('action_grace_days') or 3)


def is_learning_grace(campaign: dict, op_cfg: dict, tz: ZoneInfo) -> tuple[bool, float | None, float]:
    age = campaign_age_days(campaign, tz)
    grace_days = learning_grace_days(op_cfg)
    if grace_days <= 0 or age is None:
        return False, age, grace_days
    return age < grace_days, age, grace_days


def is_in_management_scope(op_cfg: dict, pg_id: str) -> tuple[bool, str | None]:
    if pg_id in manual_hold_pg_ids(op_cfg):
        return False, 'manual_hold'
    focus = active_focus_pg_ids(op_cfg)
    if focus and pg_id not in focus:
        return False, 'outside_active_focus'
    return True, None


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
    fields = 'id,name,status,effective_status,created_time,start_time,updated_time,bid_strategy,daily_budget,lifetime_budget,objective'
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
    limited = rows if MAX_ROWS_OUTPUT <= 0 else rows[:MAX_ROWS_OUTPUT]
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
    if MAX_ROWS_OUTPUT > 0 and len(rows) > len(limited):
        lines.append(f'... +{len(rows)-len(limited)} linhas no audit local')
    lines.append('```')
    return '\n'.join(lines)


def heartbeat_state_path(operation_id: str, account_id: str) -> Path:
    override = os.environ.get('ARES_META_INTRADAY_HEARTBEAT_STATE')
    if override:
        return Path(override)
    safe_op = re.sub(r'[^A-Za-z0-9_.-]+', '-', operation_id)
    safe_account = re.sub(r'[^A-Za-z0-9_.-]+', '-', account_id)
    return BASE / 'state' / f'intraday-heartbeat-{safe_op}-{safe_account}.json'


def heartbeat_due(operation_id: str, account_id: str, now: dt.datetime) -> tuple[bool, float]:
    """Return whether a no-action heartbeat should be emitted.

    Disabled by default. The cron wrapper enables it with
    ARES_META_INTRADAY_HEARTBEAT_HOURS=3 so ad-hoc/manual runner calls keep the
    historical silent-on-clean behavior unless explicitly testing heartbeat.
    """
    raw = os.environ.get('ARES_META_INTRADAY_HEARTBEAT_HOURS', '').strip()
    if not raw:
        return False, 0.0
    try:
        hours = float(raw)
    except ValueError:
        return False, 0.0
    if hours <= 0:
        return False, hours
    path = heartbeat_state_path(operation_id, account_id)
    try:
        state = json.loads(path.read_text()) if path.exists() else {}
        last_raw = state.get('last_heartbeat_utc')
        if last_raw:
            last = dt.datetime.fromisoformat(str(last_raw))
            if last.tzinfo is None:
                last = last.replace(tzinfo=dt.UTC)
            elapsed_hours = (now - last.astimezone(dt.UTC)).total_seconds() / 3600
            return elapsed_hours >= hours, hours
    except Exception:
        # Fail open: if state is corrupt/unreadable, emit a heartbeat and repair
        # the file instead of silently removing the signal of life.
        return True, hours
    return True, hours


def record_heartbeat(operation_id: str, account_id: str, now: dt.datetime, audit: Path) -> None:
    path = heartbeat_state_path(operation_id, account_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        'last_heartbeat_utc': now.astimezone(dt.UTC).isoformat(),
        'operation_id': operation_id,
        'account_id': account_id,
        'last_audit': str(audit),
    }
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def maybe_output_intraday_heartbeat(event: dict, account_name: str, tz: ZoneInfo, audit: Path) -> None:
    now = utc_now()
    due, hours = heartbeat_due(str(event.get('operation_id')), str(event.get('account_id')), now)
    if not due:
        return
    summary = event.get('summary') or {}
    row = {
        'status': 'OK',
        'campaigns': summary.get('campaigns_seen', 0),
        'insights': summary.get('insight_rows', 0),
        'candidates': summary.get('candidate_count', 0),
        'errors': len(event.get('errors') or []),
        'mode': 'dry-run/read-only',
    }
    prefix = f'<@344196393512075265> heartbeat intraday: cron vivo; sem candidato R1-R5 nos últimos {hours:g}h.'
    print(output_table(fmt_account_title(account_name, tz, 'Intraday Meta — heartbeat'), [row], [('status','Status'),('campaigns','Campanhas'),('insights','Insights'),('candidates','Candidatos'),('errors','Erros'),('mode','Modo')], prefix=prefix))
    record_heartbeat(str(event.get('operation_id')), str(event.get('account_id')), now, audit)


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
            in_learning_grace, age_days, grace_days = is_learning_grace(campaign, op_cfg, tz)
            for rule in by_prio:
                match, excluded = rule_matches(rule, campaign, metrics, op_cfg, tz)
                if excluded:
                    continue
                if match:
                    campaign_name = campaign.get('name') or row.get('campaign_name')
                    pg_id = page_id_from_name(campaign_name)
                    in_scope, scope_reason = is_in_management_scope(op_cfg, pg_id)
                    if not in_scope:
                        event.setdefault('skipped_scope', []).append({'campaign_id': cid, 'campaign_name': campaign_name, 'pg_id': pg_id, 'reason': scope_reason})
                        break
                    action = rule.get('action')
                    simulated_action = simulated_action_label(action)
                    reason = rule_display(rule)
                    mode = 'dry_run_no_write'
                    if in_learning_grace and action in {'pause_campaign', 'reactivate_campaign'}:
                        action = 'observe_learning'
                        simulated_action = simulated_action_label(action)
                        age_label = 'desconhecida' if age_days is None else f'{age_days:.2f}d'
                        reason = f'Learning < {grace_days:g}d; regra acionou ({rule_display(rule)}), mas é só informativo. Idade {age_label}'
                        mode = 'learning_grace_info_no_action'
                    seq = len(event['candidates']) + 1
                    event['candidates'].append({
                        'rec_id': recommendation_id(tz, seq),
                        'pg_id': pg_id,
                        'page_name': page_name_from_campaign(campaign_name),
                        'country_vertical': country_vertical_from_name(campaign_name, op_cfg),
                        'rule': rule_display(rule),
                        'status': campaign.get('effective_status'),
                        'action': action,
                        'simulated_action': simulated_action,
                        'reason': reason,
                        'campaign_id': cid,
                        'campaign_name': campaign_name,
                        'campaign_display_name': display_campaign_name(campaign_name),
                        'start_date': fmt_start_date(campaign, tz),
                        'bid_strategy': campaign.get('bid_strategy') or 'UNKNOWN',
                        'spend': round(metrics['spend'], 2),
                        'MO': int(metrics['MO']) if float(metrics['MO']).is_integer() else metrics['MO'],
                        'CPMO': None if metrics['CPMO'] is None else round(metrics['CPMO'], 2),
                        'campaign_age_days': None if age_days is None else round(age_days, 2),
                        'learning_grace_days': grace_days,
                        'mode': mode,
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
            r['rec_short'] = compact_rec_id(r.get('rec_id'))
            r['campaign_short'] = compact_campaign_name(r.get('campaign_display_name') or r.get('campaign_name'))
            r['reason_short'] = compact_reason(r.get('reason'))
            r['CPMO'] = '' if r['CPMO'] is None else r['CPMO']
        prefix = '<@344196393512075265> dry-run intraday: análise real sem write. Learning <3d = informativo; sem pausar/reativar.'
        print(output_table(fmt_account_title(account_name, tz, 'Intraday Meta — decisões simuladas'), rows, [('rec_short','REC'),('campaign_short','Campanha'),('pg_id','PG'),('start_date','Início'),('spend','Spend'),('MO','MO'),('CPMO','CPMO'),('simulated_action','Ação'),('reason_short','Motivo'),('status','Status')], prefix=prefix))
    else:
        maybe_output_intraday_heartbeat(event, account_name, tz, audit)
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
        exclusions = set(op_cfg.get('reactivate_exclusion_list') or []) | manual_hold_pg_ids(op_cfg)
        for campaign in campaigns.values():
            if campaign.get('effective_status') != 'PAUSED':
                continue
            campaign_name = campaign.get('name')
            in_learning_grace, age_days, grace_days = is_learning_grace(campaign, op_cfg, ZoneInfo(args.account_tz or 'Europe/Madrid'))
            if in_learning_grace:
                event.setdefault('skipped_learning_grace', []).append({
                    'campaign_id': campaign.get('id'),
                    'campaign_name': campaign_name,
                    'age_days': None if age_days is None else round(age_days, 2),
                    'learning_grace_days': grace_days,
                    'reason': 'learning_grace_no_reactivate_action',
                })
                continue
            pg_id = page_id_from_name(campaign_name)
            in_scope, scope_reason = is_in_management_scope(op_cfg, pg_id)
            if campaign.get('id') in exclusions or campaign.get('name') in exclusions or pg_id in exclusions or not in_scope:
                event.setdefault('skipped_scope', []).append({'campaign_id': campaign.get('id'), 'campaign_name': campaign_name, 'pg_id': pg_id, 'reason': 'manual_hold_or_exclusion' if pg_id in exclusions else scope_reason})
                continue
            seq = len(event['candidates']) + 1
            event['candidates'].append({
                'rec_id': recommendation_id(ZoneInfo(args.account_tz or 'Europe/Madrid'), seq),
                'pg_id': pg_id,
                'page_name': page_name_from_campaign(campaign_name),
                'country_vertical': country_vertical_from_name(campaign_name, op_cfg),
                'rule': 'reativar-todas',
                'reason': 'campanha pausada dentro do escopo; simularia reativação',
                'status': campaign.get('effective_status'),
                'action': 'reactivate_campaign',
                'simulated_action': simulated_action_label('reactivate_campaign'),
                'campaign_id': campaign.get('id'),
                'campaign_name': campaign_name,
                'campaign_display_name': display_campaign_name(campaign_name),
                'start_date': fmt_start_date(campaign, ZoneInfo(args.account_tz or 'Europe/Madrid')),
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
        rows = event['candidates']
        for r in rows:
            r['rec_short'] = compact_rec_id(r.get('rec_id'))
            r['campaign_short'] = compact_campaign_name(r.get('campaign_display_name') or r.get('campaign_name'))
            r['reason_short'] = compact_reason(r.get('reason'))
        prefix = '<@344196393512075265> dry-run reativar-todas: ações simuladas; nenhum write executado.'
        print(output_table(fmt_account_title(account_name, ZoneInfo(args.account_tz or 'Europe/Madrid'), 'Reativar-todas Meta — decisões simuladas'), rows, [('rec_short','REC'),('campaign_short','Campanha'),('pg_id','PG'),('start_date','Início'),('simulated_action','Ação'),('reason_short','Motivo'),('status','Status')], prefix=prefix))
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
