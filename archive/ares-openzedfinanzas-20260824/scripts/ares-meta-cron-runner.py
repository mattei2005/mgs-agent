#!/usr/bin/env python3
"""Deterministic Ares Meta Ads cron runner.

Modes:
- intraday: read Meta, evaluate R1-R4 with 2-checkpoint persistence, write local audit, print sanitized Discord log only on confirmed proposed action/error.
- reactivate-all: legacy CLI name for the 00:30 safe reactivation pass; only provenance `paused_by_ares_rule` can become a candidate.

No production write is implemented here. Ruleset v2 and HOA target are approved as configuration, but Meta write stays disabled until a separate explicit release with writer + GET-after-write validation.
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


def normalize_bid_strategy(value: str | None) -> str:
    strategy = str(value or 'UNKNOWN').strip().upper()
    aliases = {
        'LOWEST_COST_NO_CAP': 'LOWEST_COST_WITHOUT_CAP',
        'LOWEST_COST_WITHOUT_BID_CAP': 'LOWEST_COST_WITHOUT_CAP',
    }
    return aliases.get(strategy, strategy)


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
    if op == 'in':
        return actual in expected
    if op == 'not_in':
        return actual not in expected
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
    bid_strategy = normalize_bid_strategy(campaign.get('bid_strategy'))
    if 'COST_CAP_no_cost_pause' in (rule.get('exclusions') or []) and bid_strategy == 'COST_CAP':
        return False, 'COST_CAP_no_cost_pause'
    for cond in (rule.get('condition') or {}).get('all') or []:
        expected = cond.get('value')
        if 'metric' in cond:
            actual = metrics.get(cond['metric'])
        else:
            field = cond.get('field')
            actual = campaign.get(field)
            if field == 'bid_strategy':
                actual = normalize_bid_strategy(actual)
                if isinstance(expected, list):
                    expected = [normalize_bid_strategy(x) for x in expected]
                else:
                    expected = normalize_bid_strategy(expected)
        if not cmp_value(actual, cond.get('op'), expected):
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
        by_campaign.setdefault(cid, set()).add(normalize_bid_strategy(row.get('bid_strategy')))
    out = {}
    for cid, vals in by_campaign.items():
        if 'COST_CAP' in vals:
            out[cid] = 'COST_CAP'
        elif 'LOWEST_COST_WITHOUT_CAP' in vals:
            out[cid] = 'LOWEST_COST_WITHOUT_CAP'
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


def atomic_json_write(path: Path, payload: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    os.chmod(tmp, mode)
    tmp.replace(path)


def persistence_state_path(operation_id: str, account_id: str) -> Path:
    override = os.environ.get('ARES_META_INTRADAY_PERSISTENCE_STATE')
    if override:
        return Path(override)
    safe_op = re.sub(r'[^A-Za-z0-9_.-]+', '-', operation_id)
    safe_account = re.sub(r'[^A-Za-z0-9_.-]+', '-', account_id)
    return BASE / 'state' / f'intraday-rule-persistence-{safe_op}-{safe_account}.json'


def provenance_state_path(operation_id: str, account_id: str) -> Path:
    override = os.environ.get('ARES_META_CAMPAIGN_PROVENANCE_STATE')
    if override:
        return Path(override)
    safe_op = re.sub(r'[^A-Za-z0-9_.-]+', '-', operation_id)
    safe_account = re.sub(r'[^A-Za-z0-9_.-]+', '-', account_id)
    return BASE / 'state' / f'campaign-action-provenance-{safe_op}-{safe_account}.json'


def load_json_state(path: Path, default: dict) -> dict:
    try:
        value = json.loads(path.read_text()) if path.exists() else default
        return value if isinstance(value, dict) else default
    except Exception:
        return default


def checkpoint_bucket(now_local: dt.datetime, interval_minutes: int) -> dt.datetime:
    minute = (now_local.minute // interval_minutes) * interval_minutes
    return now_local.replace(minute=minute, second=0, microsecond=0)


def apply_persistence(
    state: dict,
    campaign_id: str,
    selected_rule_id: str | None,
    rule_ids: list[str],
    checkpoint: dt.datetime,
    interval_minutes: int,
) -> int:
    day = checkpoint.date().isoformat()
    if state.get('date_local') != day:
        state.clear()
        state.update({'schema_version': '1.0', 'date_local': day, 'campaigns': {}})
    state.setdefault('campaigns', {})
    campaign_state = state['campaigns'].setdefault(campaign_id, {'rules': {}})
    rules_state = campaign_state.setdefault('rules', {})
    selected_count = 0
    for rule_id in rule_ids:
        entry = rules_state.setdefault(rule_id, {'count': 0, 'last_matched': False})
        checkpoint_iso = checkpoint.isoformat(timespec='minutes')
        if entry.get('last_checkpoint') == checkpoint_iso:
            if rule_id == selected_rule_id:
                if not entry.get('last_matched'):
                    entry['count'] = 1
                entry['last_matched'] = True
                selected_count = int(entry.get('count') or 0)
            else:
                entry['count'] = 0
                entry['last_matched'] = False
            continue
        if rule_id == selected_rule_id:
            previous = None
            try:
                previous = dt.datetime.fromisoformat(str(entry.get('last_checkpoint'))) if entry.get('last_checkpoint') else None
            except Exception:
                previous = None
            gap_minutes = None if previous is None else (checkpoint - previous).total_seconds() / 60
            consecutive = bool(entry.get('last_matched')) and gap_minutes is not None and 0 < gap_minutes <= interval_minutes * 1.5
            entry['count'] = int(entry.get('count') or 0) + 1 if consecutive else 1
            entry['last_matched'] = True
            selected_count = int(entry['count'])
        else:
            entry['count'] = 0
            entry['last_matched'] = False
        entry['last_checkpoint'] = checkpoint_iso
    state['updated_at'] = utc_now().isoformat()
    return selected_count


def campaign_budget_usd(campaign: dict, fallback: float = 25.0) -> float:
    raw = campaign.get('daily_budget')
    if raw not in (None, ''):
        try:
            return float(raw) / 100.0
        except Exception:
            pass
    return float(fallback)


def spend_projection_usd(spend_so_far: float, now_local: dt.datetime) -> float:
    seconds = now_local.hour * 3600 + now_local.minute * 60 + now_local.second
    elapsed_fraction = max(seconds / 86400.0, 1 / 48)
    return float(spend_so_far) / elapsed_fraction


def reactivation_gate(
    pause_origin: str,
    allowed_origin: str,
    candidate_budget: float,
    budget_max: float,
    projected_active_count: int,
    max_active: int,
    projected_spend: float,
    cap: float,
) -> tuple[bool, str]:
    if pause_origin != allowed_origin:
        return False, 'pause_origin_not_allowed'
    if candidate_budget > budget_max:
        return False, 'candidate_budget_above_max'
    if projected_active_count + 1 > max_active:
        return False, 'active_campaign_count_cap'
    if projected_spend + candidate_budget > cap:
        return False, 'projected_spend_cap'
    return True, 'eligible'


def run_intraday(args) -> int:
    common = load_common()
    op_cfg = load_operation(args.operation_id)
    ruleset = load_rules(op_cfg)
    token, token_field = common.get_token_from_1password(TOKEN_ITEM)
    tz = ZoneInfo(args.account_tz or 'Europe/Madrid')
    now_local = utc_now().astimezone(tz)
    interval_minutes = int((ruleset.get('persistence_policy') or {}).get('checkpoint_interval_minutes') or op_cfg.get('intraday_interval_minutes') or 30)
    checkpoint = checkpoint_bucket(now_local, interval_minutes)
    state_path = persistence_state_path(args.operation_id, args.account_id)
    persistence_state = load_json_state(state_path, {'schema_version': '1.0', 'date_local': checkpoint.date().isoformat(), 'campaigns': {}})
    event = {
        'ts_utc': utc_now().isoformat(),
        'job': 'intraday',
        'operation_id': args.operation_id,
        'account_id': args.account_id,
        'ruleset': ruleset.get('ruleset'),
        'mode': 'dry_run',
        'write_enabled': False,
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'timezone': str(tz),
        'checkpoint_local': checkpoint.isoformat(timespec='minutes'),
        'persistence_state': str(state_path),
        'candidates': [],
        'pending_persistence': [],
        'errors': [],
    }
    account_name = f'act_{args.account_id}'
    try:
        account_name = fetch_account_name(common, token, args.account_id)
        campaigns = fetch_campaigns(common, token, args.account_id)
        adset_bids = fetch_adset_bid_strategies(common, token, args.account_id)
        insights = fetch_today_insights(common, token, args.account_id)
        insights_by_campaign = {str(row.get('campaign_id') or ''): row for row in insights if row.get('campaign_id')}
        for cid, bid in adset_bids.items():
            if cid in campaigns and (bid == 'COST_CAP' or not campaigns[cid].get('bid_strategy')):
                campaigns[cid]['bid_strategy'] = bid
        by_prio = sorted([r for r in (ruleset.get('rules') or []) if r.get('enabled')], key=lambda r: int(r.get('priority') or 99))
        rule_ids = [str(r.get('id')) for r in by_prio]
        for cid, campaign in campaigns.items():
            row = insights_by_campaign.get(cid) or {'campaign_id': cid, 'campaign_name': campaign.get('name'), 'spend': 0, 'actions': []}
            metrics = derive_metrics(row)
            campaign_name = campaign.get('name') or row.get('campaign_name') or cid
            pg_id = page_id_from_name(campaign_name)
            in_scope, scope_reason = is_in_management_scope(op_cfg, pg_id)
            in_learning_grace, age_days, grace_days = is_learning_grace(campaign, op_cfg, tz)
            in_test_grace = is_test_grace(campaign, op_cfg, tz)
            selected_rule = None
            if in_scope and not in_learning_grace and not in_test_grace:
                for rule in by_prio:
                    match, excluded = rule_matches(rule, campaign, metrics, op_cfg, tz)
                    if excluded:
                        continue
                    if match:
                        selected_rule = rule
                        break
            elif not in_scope:
                event.setdefault('skipped_scope', []).append({'campaign_id': cid, 'campaign_name': campaign_name, 'pg_id': pg_id, 'reason': scope_reason})
            elif in_learning_grace or in_test_grace:
                event.setdefault('skipped_grace', []).append({
                    'campaign_id': cid,
                    'campaign_name': campaign_name,
                    'reason': 'TEST_grace_3_days' if in_test_grace else 'learning_grace_3_days',
                    'campaign_age_days': None if age_days is None else round(age_days, 2),
                })
            selected_rule_id = str(selected_rule.get('id')) if selected_rule else None
            consecutive = apply_persistence(persistence_state, cid, selected_rule_id, rule_ids, checkpoint, interval_minutes)
            if not selected_rule:
                continue
            required = int((selected_rule.get('persistence') or {}).get('consecutive_checkpoints') or (ruleset.get('persistence_policy') or {}).get('required') or 1)
            persistence_label = f'{consecutive}/{required} checkpoints'
            if consecutive < required:
                event['pending_persistence'].append({
                    'campaign_id': cid,
                    'campaign_name': campaign_name,
                    'pg_id': pg_id,
                    'rule': selected_rule_id,
                    'persistence': persistence_label,
                    'spend': round(metrics['spend'], 2),
                    'MO': int(metrics['MO']) if float(metrics['MO']).is_integer() else metrics['MO'],
                    'CPMO': None if metrics['CPMO'] is None else round(metrics['CPMO'], 2),
                })
                continue
            seq = len(event['candidates']) + 1
            reason = f'{rule_display(selected_rule)}; persistência {persistence_label}'
            event['candidates'].append({
                'rec_id': recommendation_id(tz, seq),
                'pg_id': pg_id,
                'page_name': page_name_from_campaign(campaign_name),
                'country_vertical': country_vertical_from_name(campaign_name, op_cfg),
                'rule': rule_display(selected_rule),
                'status': campaign.get('effective_status'),
                'action': selected_rule.get('action'),
                'simulated_action': simulated_action_label(selected_rule.get('action')),
                'reason': reason,
                'campaign_id': cid,
                'campaign_name': campaign_name,
                'campaign_display_name': display_campaign_name(campaign_name),
                'start_date': fmt_start_date(campaign, tz),
                'bid_strategy': normalize_bid_strategy(campaign.get('bid_strategy')),
                'spend': round(metrics['spend'], 2),
                'MO': int(metrics['MO']) if float(metrics['MO']).is_integer() else metrics['MO'],
                'CPMO': None if metrics['CPMO'] is None else round(metrics['CPMO'], 2),
                'campaign_age_days': None if age_days is None else round(age_days, 2),
                'learning_grace_days': grace_days,
                'persistence_count': consecutive,
                'persistence_required': required,
                'mode': 'dry_run_no_write',
            })
        atomic_json_write(state_path, persistence_state)
        event['summary'] = {
            'campaigns_seen': len(campaigns),
            'insight_rows': len(insights),
            'pending_persistence_count': len(event['pending_persistence']),
            'candidate_count': len(event['candidates']),
        }
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
        prefix = '<@344196393512075265> dry-run intraday v2: 2 checkpoints confirmados; análise real sem write.'
        print(output_table(fmt_account_title(account_name, tz, 'Intraday Meta v2 — decisões simuladas'), rows, [('rec_short','REC'),('campaign_short','Campanha'),('pg_id','PG'),('start_date','Início'),('spend','Spend'),('MO','MO'),('CPMO','CPMO'),('simulated_action','Ação'),('reason_short','Motivo'),('status','Status')], prefix=prefix))
    else:
        maybe_output_intraday_heartbeat(event, account_name, tz, audit)
    return 0


def run_reactivate_all(args) -> int:
    common = load_common()
    op_cfg = load_operation(args.operation_id)
    ruleset = load_rules(op_cfg)
    token, token_field = common.get_token_from_1password(TOKEN_ITEM)
    tz = ZoneInfo(args.account_tz or 'Europe/Madrid')
    now_local = utc_now().astimezone(tz)
    reactivate_cfg = ruleset.get('reactivate_all') or {}
    gates = reactivate_cfg.get('gates') or {}
    provenance_path = provenance_state_path(args.operation_id, args.account_id)
    provenance = load_json_state(provenance_path, {'schema_version': '1.0', 'campaigns': {}})
    allowed_origin = str(reactivate_cfg.get('allowed_pause_origin') or 'paused_by_ares_rule')
    event = {
        'ts_utc': utc_now().isoformat(),
        'job': 'reactivate_safe_00_30',
        'legacy_cli_job': 'reactivate-all',
        'operation_id': args.operation_id,
        'account_id': args.account_id,
        'ruleset': ruleset.get('ruleset'),
        'mode': 'dry_run',
        'write_enabled': False,
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'provenance_state': str(provenance_path),
        'allowed_pause_origin': allowed_origin,
        'candidates': [],
        'errors': [],
        'exclusion_list': op_cfg.get('reactivate_exclusion_list') or [],
    }
    account_name = f'act_{args.account_id}'
    try:
        account_name = fetch_account_name(common, token, args.account_id)
        campaigns = fetch_campaigns(common, token, args.account_id)
        insights = fetch_today_insights(common, token, args.account_id)
        spend_so_far = sum(float(row.get('spend') or 0) for row in insights)
        active_campaigns = [c for c in campaigns.values() if c.get('effective_status') == 'ACTIVE']
        max_active = int(gates.get('max_active_campaigns') or 12)
        cap = float(gates.get('daily_account_cap_usd') or 300.0)
        budget_max = float(gates.get('candidate_daily_budget_max_usd') or 25.0)
        configured_active_budget = sum(campaign_budget_usd(c, budget_max) for c in active_campaigns)
        run_rate_projection = spend_projection_usd(spend_so_far, now_local)
        projected_spend = max(configured_active_budget, run_rate_projection)
        projected_active_count = len(active_campaigns)
        event['gates'] = {
            'daily_account_cap_usd': cap,
            'max_active_campaigns': max_active,
            'candidate_daily_budget_max_usd': budget_max,
            'active_campaigns_before': projected_active_count,
            'configured_active_budget_usd': round(configured_active_budget, 2),
            'spend_so_far_usd': round(spend_so_far, 2),
            'run_rate_projection_usd': round(run_rate_projection, 2),
            'base_projected_spend_usd': round(projected_spend, 2),
        }
        exclusions = set(op_cfg.get('reactivate_exclusion_list') or []) | manual_hold_pg_ids(op_cfg)
        provenance_campaigns = provenance.get('campaigns') or {}
        for campaign in sorted(campaigns.values(), key=lambda c: str(c.get('id'))):
            if campaign.get('effective_status') != 'PAUSED':
                continue
            campaign_id = str(campaign.get('id') or '')
            campaign_name = campaign.get('name')
            pg_id = page_id_from_name(campaign_name)
            record = provenance_campaigns.get(campaign_id) or {}
            pause_origin = str(record.get('pause_origin') or 'unknown')
            if pause_origin != allowed_origin:
                event.setdefault('skipped_provenance', []).append({
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_name,
                    'pg_id': pg_id,
                    'pause_origin': pause_origin,
                    'reason': 'pause_origin_not_allowed',
                })
                continue
            in_learning_grace, age_days, grace_days = is_learning_grace(campaign, op_cfg, tz)
            if in_learning_grace:
                event.setdefault('skipped_learning_grace', []).append({
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_name,
                    'age_days': None if age_days is None else round(age_days, 2),
                    'learning_grace_days': grace_days,
                    'reason': 'learning_grace_no_reactivate_action',
                })
                continue
            in_scope, scope_reason = is_in_management_scope(op_cfg, pg_id)
            if campaign_id in exclusions or campaign_name in exclusions or pg_id in exclusions or not in_scope:
                event.setdefault('skipped_scope', []).append({'campaign_id': campaign_id, 'campaign_name': campaign_name, 'pg_id': pg_id, 'reason': 'manual_hold_or_exclusion' if pg_id in exclusions else scope_reason})
                continue
            candidate_budget = campaign_budget_usd(campaign, budget_max)
            eligible, gate_reason = reactivation_gate(
                pause_origin, allowed_origin, candidate_budget, budget_max,
                projected_active_count, max_active, projected_spend, cap,
            )
            if not eligible:
                detail = {
                    'campaign_id': campaign_id,
                    'reason': gate_reason,
                    'candidate_budget_usd': round(candidate_budget, 2),
                    'projected_active_count': projected_active_count + 1,
                    'max_active_campaigns': max_active,
                    'projected_spend_usd': round(projected_spend + candidate_budget, 2),
                    'cap_usd': cap,
                }
                bucket = 'skipped_budget' if gate_reason == 'candidate_budget_above_max' else 'skipped_cap'
                event.setdefault(bucket, []).append(detail)
                continue
            projected_active_count += 1
            projected_spend += candidate_budget
            seq = len(event['candidates']) + 1
            event['candidates'].append({
                'rec_id': recommendation_id(tz, seq),
                'pg_id': pg_id,
                'page_name': page_name_from_campaign(campaign_name),
                'country_vertical': country_vertical_from_name(campaign_name, op_cfg),
                'rule': 'reativar-00:30-paused_by_ares_rule',
                'reason': 'proveniência paused_by_ares_rule confirmada; gates de quantidade e cap aprovados',
                'status': campaign.get('effective_status'),
                'action': 'reactivate_campaign',
                'simulated_action': simulated_action_label('reactivate_campaign'),
                'campaign_id': campaign_id,
                'campaign_name': campaign_name,
                'campaign_display_name': display_campaign_name(campaign_name),
                'start_date': fmt_start_date(campaign, tz),
                'candidate_budget_usd': round(candidate_budget, 2),
                'projected_active_count': projected_active_count,
                'projected_spend_usd': round(projected_spend, 2),
                'mode': 'dry_run_no_write',
            })
        event['summary'] = {
            'campaigns_seen': len(campaigns),
            'paused_seen': sum(1 for c in campaigns.values() if c.get('effective_status') == 'PAUSED'),
            'skipped_unknown_or_forbidden_provenance': len(event.get('skipped_provenance') or []),
            'candidate_count': len(event['candidates']),
            'projected_active_count_after': projected_active_count,
            'projected_spend_usd_after': round(projected_spend, 2),
        }
    except Exception as e:
        event['errors'].append(str(e)[:1000])
    audit = audit_write('reactivate-all', event)
    if event['errors']:
        print(output_table(fmt_account_title(account_name, tz, 'Reativação segura 00:30 — ERRO'), [{'erro': event['errors'][0], 'audit': str(audit)}], [('erro','Erro'),('audit','Audit')], prefix='<@344196393512075265> erro no cron de reativação segura 00:30.'))
        return 0
    if event['candidates']:
        rows = event['candidates']
        for r in rows:
            r['rec_short'] = compact_rec_id(r.get('rec_id'))
            r['campaign_short'] = compact_campaign_name(r.get('campaign_display_name') or r.get('campaign_name'))
            r['reason_short'] = compact_reason(r.get('reason'))
        prefix = '<@344196393512075265> dry-run reativação 00:30: somente paused_by_ares_rule; nenhum write executado.'
        print(output_table(fmt_account_title(account_name, tz, 'Reativação segura 00:30 — decisões simuladas'), rows, [('rec_short','REC'),('campaign_short','Campanha'),('pg_id','PG'),('start_date','Início'),('simulated_action','Ação'),('reason_short','Motivo'),('status','Status')], prefix=prefix))
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
