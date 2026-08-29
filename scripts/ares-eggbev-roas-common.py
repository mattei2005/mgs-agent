#!/usr/bin/env python3
"""Shared deterministic runtime for Eggbev BOT ROAS and reports.

Read paths are live Meta + Smart Bidding. Writes are performed only by the
ROAS runner after operation-config gates, source reconciliation, native-rule
preflight, pre-read and post-write readback. Secrets are never returned.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
OP_PATH = BASE / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json'
ACCOUNT_PATH = BASE / 'data/ares/meta-ads/accounts/1034081997659047.json'
STATE_DIR = BASE / 'data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT'
ROAS_STATE_PATH = STATE_DIR / 'roas-cycle.json'
AUDIT_DIR = BASE / 'data/ares/meta-ads/audit/eggbev/roas-cycle'
LOCK_PATH = STATE_DIR / 'roas-cycle.lock'
META_COMMON_PATH = BASE / 'scripts/ares-meta-common.py'
SB_COMMON_PATH = BASE / 'scripts/ares-smartbidding-common.py'
ET = ZoneInfo('America/New_York')
DISCORD_API = 'https://discord.com/api/v10'
PURCHASE_ACTIONS = ('omni_purchase', 'purchase')
MESSAGING_ACTIONS = ('onsite_conversion.messaging_first_reply', 'onsite_conversion.messaging_conversation_started_7d')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load module {path.name}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def norm(value: Any) -> str:
    return str(value or '').strip()


def finite_float(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def now_et() -> dt.datetime:
    return dt.datetime.now(ET)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def open_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, 'r+')


def default_state(local_date: dt.date, threshold: float = 0.40) -> dict[str, Any]:
    return {
        'operation_id': 'Eggbev-US-CC-EN-BOT',
        'date_et': local_date.isoformat(),
        'threshold': round(float(threshold), 4),
        'paused_ads': {},
        'paused_campaigns': {},
        'last_cycle': None,
    }


def rollover_state(state: dict[str, Any] | None, local_date: dt.date, reset_value: float = 0.40) -> dict[str, Any]:
    """Reset daily decision fields without losing Ares pause provenance."""
    previous = state if isinstance(state, dict) else {}
    rolled = default_state(local_date, reset_value)
    for key in ('paused_ads', 'paused_campaigns'):
        value = previous.get(key)
        if isinstance(value, dict):
            rolled[key] = dict(value)
    previous_date = norm(previous.get('date_et'))
    if previous_date and previous_date != local_date.isoformat():
        rolled['provenance_rolled_from_date_et'] = previous_date
    return rolled


def load_state(local_date: dt.date, reset_value: float = 0.40) -> tuple[dict[str, Any], bool]:
    try:
        state = load_json(ROAS_STATE_PATH)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return default_state(local_date, reset_value), True
    if state.get('date_et') != local_date.isoformat():
        return rollover_state(state, local_date, reset_value), True
    state.setdefault('paused_ads', {})
    state.setdefault('paused_campaigns', {})
    state.setdefault('threshold', reset_value)
    return state, False


def phase_for_time(local_time: dt.datetime) -> str:
    hhmm = local_time.strftime('%H:%M')
    if hhmm == '00:00':
        return 'RESET'
    if hhmm in {'06:00', '08:00', '10:00', '12:00'}:
        return 'PHASE_1'
    if hhmm in {'13:00', '14:00', '16:00', '18:00', '20:00', '22:00', '23:00'}:
        return 'PHASE_2'
    return 'NO_CYCLE'


def action_value(rows: Any, wanted: tuple[str, ...]) -> float | None:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict) or norm(row.get('action_type')) not in wanted:
            continue
        value = finite_float(row.get('value'))
        if value is not None:
            return value
    return None


def fetch_all_meta(common, token: str, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    after: str | None = None
    for _ in range(100):
        request_params = dict(params)
        if after:
            request_params['after'] = after
        status, body, _ = common.graph_get(path, token, request_params)
        if status != 200 or not isinstance(body, dict):
            raise RuntimeError(f'Meta read failed for {path}: HTTP {status}')
        rows.extend(row for row in body.get('data') or [] if isinstance(row, dict))
        paging = body.get('paging') or {}
        cursor = (paging.get('cursors') or {}).get('after')
        if not paging.get('next') or not cursor or cursor == after:
            break
        after = str(cursor)
    else:
        raise RuntimeError(f'Meta pagination safety limit exceeded for {path}')
    return rows


def load_runtime_modules(account: dict[str, Any]):
    os.environ.setdefault('ARES_META_TOKEN_CACHE_PATH', '/root/.cache/mgs/ares-meta-token-eggbev-us-cc-en-01-g006.json')
    meta = load_module('ares_meta_common_eggbev_roas', META_COMMON_PATH)
    sb = load_module('ares_sb_common_eggbev_roas', SB_COMMON_PATH)
    token, token_field = meta.get_token_from_1password(account.get('token_1password_item'))
    return meta, sb, token, {'credential_item': account.get('token_1password_item'), 'field': token_field, 'token_len': len(token)}


def read_native_rules(meta, token: str, act: str) -> dict[str, Any]:
    status, body, _ = meta.graph_get(act + '/adrules_library', token, {
        'fields': 'id,name,status,evaluation_spec,execution_spec,schedule_spec,updated_time',
        'limit': 200,
    })
    rows = (body.get('data') or []) if status == 200 and isinstance(body, dict) else []
    by_name = {norm(row.get('name')): row for row in rows if norm(row.get('name'))}
    conflict = by_name.get('ADS ZERO RESULTS')
    return {
        'http_status': status,
        'count': len(rows),
        'conflict': {
            'present': bool(conflict),
            'name': 'ADS ZERO RESULTS',
            'status': conflict.get('status') if conflict else None,
            'enabled': bool(conflict and conflict.get('status') == 'ENABLED'),
        },
        'has_issues': [norm(row.get('name')) for row in rows if row.get('status') == 'HAS_ISSUES'],
    }


def detect_manual_interventions(state: dict[str, Any], tracked_ads: list[dict[str, Any]], tracked_campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag tracked objects changed after Ares' recorded write; never discard provenance automatically."""
    review: list[dict[str, Any]] = []
    groups = (
        ('ad', state.get('paused_ads') or {}, tracked_ads),
        ('campaign', state.get('paused_campaigns') or {}, tracked_campaigns),
    )
    for kind, entries, rows in groups:
        by_id = {norm(row.get('id')): row for row in rows if norm(row.get('id'))}
        for object_id, entry in entries.items():
            expected = norm((entry or {}).get('meta_updated_time')) if isinstance(entry, dict) else ''
            current = norm((by_id.get(str(object_id)) or {}).get('updated_time'))
            if expected and current and current != expected:
                review.append({
                    'kind': kind,
                    'object_id': str(object_id),
                    'expected_updated_time': expected,
                    'current_updated_time': current,
                    'action': 'ASK_NICOLAS_FOR_ORIENTATION',
                })
    return review


def fetch_meta_bundle(meta, token: str, account_id: str, state: dict[str, Any], since: str = 'today') -> dict[str, Any]:
    act = 'act_' + account_id
    status, live_account, _ = meta.graph_get(act, token, {'fields': 'id,name,account_status,currency,timezone_name,disable_reason'})
    if status != 200 or not isinstance(live_account, dict):
        raise RuntimeError(f'Meta account preflight failed: HTTP {status}')
    if live_account.get('currency') != 'USD' or live_account.get('timezone_name') != 'America/New_York' or int(live_account.get('account_status') or 0) != 1:
        raise RuntimeError('Meta identity/currency/timezone/status preflight failed')
    campaigns = fetch_all_meta(meta, token, act + '/campaigns', {
        'fields': 'id,name,status,effective_status,configured_status,daily_budget,updated_time',
        'effective_status': ['ACTIVE'],
        'limit': 200,
    })
    ads = fetch_all_meta(meta, token, act + '/ads', {
        'fields': 'id,name,status,effective_status,configured_status,campaign{id,name,status,effective_status},adset{id,name,status,effective_status},creative{id,name,object_story_spec,url_tags,effective_object_story_id}',
        'effective_status': ['ACTIVE'],
        'limit': 200,
    })
    tracked_ads: list[dict[str, Any]] = []
    for ad_id in sorted((state.get('paused_ads') or {}).keys()):
        ad_status, row, _ = meta.graph_get(ad_id, token, {'fields': 'id,name,status,effective_status,configured_status,updated_time,campaign{id,name,status,effective_status},adset{id,name,status,effective_status},creative{id,name,object_story_spec,url_tags,effective_object_story_id}'})
        if ad_status == 200 and isinstance(row, dict):
            tracked_ads.append(row)
    tracked_campaigns: list[dict[str, Any]] = []
    for campaign_id in sorted((state.get('paused_campaigns') or {}).keys()):
        cstatus, row, _ = meta.graph_get(campaign_id, token, {'fields': 'id,name,status,effective_status,configured_status,daily_budget,updated_time'})
        if cstatus == 200 and isinstance(row, dict):
            tracked_campaigns.append(row)
    fields = 'ad_id,ad_name,campaign_id,campaign_name,spend,impressions,cpm,ctr,actions,action_values,cost_per_action_type,purchase_roas'
    insight_params = {'level': 'ad', 'fields': fields, 'limit': 200}
    if since == 'today':
        insight_params['date_preset'] = 'today'
    else:
        insight_params['time_range'] = json.dumps({'since': since, 'until': since})
    insights = fetch_all_meta(meta, token, act + '/insights', insight_params)
    insights_by_ad: dict[str, dict[str, Any]] = {}
    for row in insights:
        ad_id = norm(row.get('ad_id'))
        if not ad_id:
            continue
        insights_by_ad[ad_id] = {
            'status': 'ok',
            'spend': finite_float(row.get('spend')) or 0.0,
            'impressions': finite_float(row.get('impressions')),
            'cpm': finite_float(row.get('cpm')),
            'ctr': finite_float(row.get('ctr')),
            'messaging_results': action_value(row.get('actions'), MESSAGING_ACTIONS),
            'cost_per_messaging_result': action_value(row.get('cost_per_action_type'), MESSAGING_ACTIONS),
            'purchase_roas': action_value(row.get('purchase_roas'), PURCHASE_ACTIONS),
            'purchase_value': action_value(row.get('action_values'), PURCHASE_ACTIONS),
        }
    return {
        'account': {
            'name': live_account.get('name'), 'account_status': live_account.get('account_status'),
            'currency': live_account.get('currency'), 'timezone_name': live_account.get('timezone_name'),
        },
        'campaigns': campaigns,
        'ads': ads,
        'tracked_ads': tracked_ads,
        'tracked_campaigns': tracked_campaigns,
        'manual_review': detect_manual_interventions(state, tracked_ads, tracked_campaigns),
        'insights': insights,
        'insights_by_ad': insights_by_ad,
        'native_rules': read_native_rules(meta, token, act),
    }


def _eggbev_publishers(sb, credential_item: str) -> tuple[list[str], dict[str, Any]]:
    status, companies, token_report = sb.api_request('GET', '/company', item_name=credential_item)
    if status != 200 or not isinstance(companies, list):
        raise RuntimeError(f'Smart Bidding /company failed: HTTP {status}')
    publishers: list[str] = []
    for company in companies:
        for publisher in company.get('publishers') or []:
            if norm(publisher.get('name')).lower() != 'eggbev' or not publisher.get('active', True):
                continue
            publisher_id = norm(publisher.get('publisherId'))
            if publisher_id and '_' not in publisher_id:
                publisher_id = f"{company.get('companyId')}_{publisher_id}"
            if publisher_id:
                publishers.append(publisher_id)
    publishers = sorted(set(publishers))
    if not publishers:
        raise RuntimeError('Smart Bidding Eggbev publisher was not found')
    return publishers, token_report


def fetch_sb_bundle(sb, policy: dict[str, Any], report_date: str) -> dict[str, Any]:
    source = (policy.get('page_lead_guardrail') or {}).get('source') or {}
    credential_item = norm(source.get('credential_item') or 'Ares - Smartbidding Dashboard')
    publishers, token_report = _eggbev_publishers(sb, credential_item)
    query = '&'.join('companies[]=' + urllib.parse.quote(value) for value in publishers) + '&source=Messenger'
    pages_status, pages, _ = sb.api_request('GET', '/campaigns/Messenger?' + query, item_name=credential_item)
    if pages_status != 200 or not isinstance(pages, list):
        raise RuntimeError(f'Smart Bidding pages failed: HTTP {pages_status}')
    payload = {
        'initialDate': f'{report_date}T00:00:00.000Z',
        'finalDate': f'{report_date}T23:59:59.999Z',
        'publishers': publishers,
        'currency': 'USD',
    }
    report_status, report_rows, _ = sb.api_request('POST', '/report/messenger', payload=payload, item_name=credential_item)
    if report_status not in {200, 201} or not isinstance(report_rows, list):
        raise RuntimeError(f'Smart Bidding report failed: HTTP {report_status}')
    expected_names = [norm(value).lower() for value in ((policy.get('smart_bidding_reconciliation') or {}).get('expected_account_names') or ['Eggbev-US-CC-EN-01', 'Eggbev-US-CC-EN-01-G006'])]
    target_rows = [row for row in report_rows if any(name and name in norm(row.get('ACCOUNT_NAME')).lower() for name in expected_names)]
    freshness = evaluate_sb_freshness(target_rows, now_et(), 2.0)
    page_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pages:
        utm = norm(row.get('UTM_CAMPAIGN')).lower()
        if utm:
            page_index[utm].append(row)
    return {
        'ready': bool(target_rows) and freshness.get('ready') is True,
        'reason': ('target_account_absent_from_smart_bidding_report' if not target_rows else freshness.get('reason')),
        'freshness': freshness,
        'publisher_count': len(publishers),
        'page_rows': pages,
        'page_index': dict(page_index),
        'report_rows': report_rows,
        'target_report_rows': target_rows,
        'available_account_names': sorted({norm(row.get('ACCOUNT_NAME')) for row in report_rows if norm(row.get('ACCOUNT_NAME'))}),
        'schema_keys': sorted({key for row in report_rows for key in row.keys()}),
        'credential_readback': {'item': token_report.get('credential_item'), 'token_len': token_report.get('token_len')},
    }


def evaluate_sb_freshness(rows: list[dict[str, Any]], observed_at: dt.datetime, max_age_hours: float) -> dict[str, Any]:
    """Require a timezone-aware source timestamp before economic automation."""
    fields = ('UPDATED_AT', 'UPDATED_TIME', 'LAST_UPDATED', 'LAST_UPDATE', 'DATA_UPDATED_AT')
    parsed: list[tuple[str, dt.datetime]] = []
    for row in rows:
        for field in fields:
            raw = norm(row.get(field))
            if not raw:
                continue
            try:
                value = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
            except ValueError:
                continue
            if value.tzinfo is None:
                continue
            parsed.append((field, value.astimezone(ET)))
    if not parsed:
        return {
            'ready': False,
            'reason': 'smart_bidding_freshness_unverifiable',
            'max_age_hours': float(max_age_hours),
            'timestamp_field': None,
        }
    field, latest = max(parsed, key=lambda item: item[1])
    age_seconds = max(0.0, (observed_at.astimezone(ET) - latest).total_seconds())
    ready = age_seconds <= float(max_age_hours) * 3600.0
    return {
        'ready': ready,
        'reason': None if ready else 'smart_bidding_data_stale_over_2h',
        'max_age_hours': float(max_age_hours),
        'timestamp_field': field,
        'latest_at_et': latest.isoformat(),
        'age_minutes': round(age_seconds / 60.0, 2),
    }


def normalize_ad(ad: dict[str, Any], tracked: bool = False) -> dict[str, Any]:
    campaign = ad.get('campaign') or {}
    adset = ad.get('adset') or {}
    return {
        'ad_id': norm(ad.get('id')),
        'ad_name': norm(ad.get('name')),
        'status': norm(ad.get('status')),
        'effective_status': norm(ad.get('effective_status')),
        'configured_status': norm(ad.get('configured_status') or ad.get('status')),
        'campaign_id': norm(campaign.get('id')),
        'campaign_name': norm(campaign.get('name')),
        'campaign_status': norm(campaign.get('status')),
        'campaign_effective_status': norm(campaign.get('effective_status')),
        'adset_id': norm(adset.get('id')),
        'adset_status': norm(adset.get('status')),
        'adset_effective_status': norm(adset.get('effective_status')),
        'tracked_by_ares': tracked,
    }


def decide_cycle(active_ads: list[dict[str, Any]], tracked_ads: list[dict[str, Any]], insights_by_ad: dict[str, dict[str, Any]], state: dict[str, Any], phase: str, threshold: float) -> dict[str, Any]:
    all_ads: dict[str, dict[str, Any]] = {}
    for ad in active_ads:
        row = normalize_ad(ad, False)
        if row['ad_id']:
            all_ads[row['ad_id']] = row
    for ad in tracked_ads:
        row = normalize_ad(ad, True)
        if row['ad_id']:
            all_ads[row['ad_id']] = row
    decisions: list[dict[str, Any]] = []
    for ad_id, ad in sorted(all_ads.items()):
        metric = insights_by_ad.get(ad_id) or {'status': 'no_data_today', 'spend': 0.0, 'purchase_roas': None}
        spend = finite_float(metric.get('spend')) or 0.0
        roas = finite_float(metric.get('purchase_roas'))
        is_active = ad.get('effective_status') == 'ACTIVE' and ad.get('configured_status') == 'ACTIVE'
        is_tracked_paused = ad_id in (state.get('paused_ads') or {}) and ad.get('configured_status') == 'PAUSED'
        action = 'KEEP'
        reason = 'outside_action_gate'
        if phase == 'PHASE_1' and is_active:
            if spend > 2.0 and (roas is None or roas < threshold):
                action, reason = 'PAUSE_AD', 'spent_gt_2_and_roas_below_or_nd'
            else:
                reason = 'phase1_gate_not_met'
        elif phase == 'PHASE_2' and is_active:
            if roas is None or roas < threshold:
                action, reason = 'PAUSE_AD', 'roas_below_or_nd'
            else:
                reason = 'roas_at_or_above_threshold'
        elif phase in {'PHASE_1', 'PHASE_2'} and is_tracked_paused:
            if ad.get('adset_status') != 'ACTIVE':
                reason = 'tracked_adset_not_configured_active'
            elif roas is not None and roas > threshold:
                action, reason = 'REACTIVATE_AD', 'ares_paused_and_roas_above_threshold'
            else:
                reason = 'paused_ad_not_above_threshold'
        decisions.append({**ad, **metric, 'spend': spend, 'purchase_roas': roas, 'threshold': threshold, 'phase': phase, 'action': action, 'reason': reason})
    by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row.get('campaign_id'):
            by_campaign[row['campaign_id']].append(row)
    campaign_actions: list[dict[str, Any]] = []
    tracked_campaigns = state.get('paused_campaigns') or {}
    for campaign_id, rows in sorted(by_campaign.items()):
        active_before = sum(1 for row in rows if row.get('effective_status') == 'ACTIVE' and row.get('configured_status') == 'ACTIVE')
        pauses = sum(1 for row in rows if row.get('action') == 'PAUSE_AD')
        reactivations = sum(1 for row in rows if row.get('action') == 'REACTIVATE_AD')
        active_after = active_before - pauses + reactivations
        if active_before > 0 and pauses > 0 and active_after == 0:
            campaign_actions.append({'campaign_id': campaign_id, 'campaign_name': rows[0].get('campaign_name'), 'action': 'PAUSE_CAMPAIGN', 'reason': 'zero_active_ads_after_cycle'})
        if campaign_id in tracked_campaigns and reactivations > 0:
            campaign_actions.append({'campaign_id': campaign_id, 'campaign_name': rows[0].get('campaign_name'), 'action': 'REACTIVATE_CAMPAIGN', 'reason': 'tracked_ad_recovered_above_threshold'})
    return {
        'phase': phase,
        'threshold': threshold,
        'decisions': decisions,
        'campaign_actions': campaign_actions,
        'counts': {
            'ads_considered': len(decisions),
            'pause_ads': sum(1 for row in decisions if row['action'] == 'PAUSE_AD'),
            'reactivate_ads': sum(1 for row in decisions if row['action'] == 'REACTIVATE_AD'),
            'pause_campaigns': sum(1 for row in campaign_actions if row['action'] == 'PAUSE_CAMPAIGN'),
            'reactivate_campaigns': sum(1 for row in campaign_actions if row['action'] == 'REACTIVATE_CAMPAIGN'),
        },
    }


def plan_campaign_budget_scales(campaigns: list[dict[str, Any]], decisions: list[dict[str, Any]], threshold: float, increase_percent: float = 30.0) -> list[dict[str, Any]]:
    """Plan, but never execute, campaign-level CBO increases from Meta ROAS."""
    by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row.get('campaign_id'):
            by_campaign[row['campaign_id']].append(row)
    candidates: list[dict[str, Any]] = []
    for campaign in campaigns:
        campaign_id = norm(campaign.get('id'))
        configured = norm(campaign.get('configured_status') or campaign.get('status'))
        if not campaign_id or configured != 'ACTIVE' or norm(campaign.get('effective_status')) != 'ACTIVE':
            continue
        spend = 0.0
        purchase_value = 0.0
        valid_value = False
        for row in by_campaign.get(campaign_id, []):
            if row.get('effective_status') != 'ACTIVE' or row.get('configured_status') != 'ACTIVE':
                continue
            row_spend = finite_float(row.get('spend')) or 0.0
            row_value = finite_float(row.get('purchase_value'))
            row_roas = finite_float(row.get('purchase_roas'))
            if row_value is None and row_roas is not None and row_spend > 0:
                row_value = row_roas * row_spend
            spend += row_spend
            if row_value is not None:
                purchase_value += row_value
                valid_value = True
        current_minor = finite_float(campaign.get('daily_budget'))
        if spend <= 0 or not valid_value or current_minor is None or current_minor <= 0:
            continue
        campaign_roas = purchase_value / spend
        if campaign_roas <= threshold:
            continue
        target_minor = int(current_minor * (1.0 + float(increase_percent) / 100.0) + 0.5)
        candidates.append({
            'campaign_id': campaign_id,
            'campaign_name': norm(campaign.get('name')),
            'purchase_roas': campaign_roas,
            'threshold': threshold,
            'increase_percent': float(increase_percent),
            'current_daily_budget_minor': int(current_minor),
            'target_daily_budget_minor': target_minor,
            'current_daily_budget_usd': current_minor / 100.0,
            'target_daily_budget_usd': target_minor / 100.0,
            'action': 'RECOMMEND_INCREASE_BUDGET_30_PERCENT',
            'write_enabled': False,
            'blocked_reason': 'scale_frequency_and_cooldown_pending_nicolas',
        })
    return candidates


def source_gate(meta_bundle: dict[str, Any], sb_bundle: dict[str, Any], phase: str) -> dict[str, Any]:
    reasons: list[str] = []
    if phase not in {'PHASE_1', 'PHASE_2'}:
        reasons.append('not_an_action_cycle')
    if (meta_bundle.get('native_rules') or {}).get('conflict', {}).get('enabled'):
        reasons.append('native_rule_ADS_ZERO_RESULTS_enabled')
    if meta_bundle.get('manual_review'):
        reasons.append('manual_intervention_review_required')
    if not sb_bundle.get('ready'):
        reasons.append(sb_bundle.get('reason') or 'smart_bidding_not_ready')
    return {'write_ready': not reasons, 'reasons': reasons}


def reconcile_status_write(meta, token: str, object_id: str, desired: str, fields: str = 'id,name,status,effective_status,configured_status,updated_time') -> dict[str, Any]:
    pre_status, before, _ = meta.graph_get(object_id, token, {'fields': fields})
    if pre_status != 200 or not isinstance(before, dict):
        return {'object_id': object_id, 'ok': False, 'stage': 'pre_readback', 'http_status': pre_status}
    configured = norm(before.get('configured_status') or before.get('status'))
    if configured == desired:
        return {'object_id': object_id, 'ok': True, 'stage': 'already_desired', 'before': {'status': before.get('status'), 'effective_status': before.get('effective_status'), 'updated_time': before.get('updated_time')}}
    post_status, post_body, _ = meta.graph_post_once(object_id, token, {'status': desired})
    read_status, after, _ = meta.graph_get(object_id, token, {'fields': fields})
    after_configured = norm((after or {}).get('configured_status') or (after or {}).get('status')) if isinstance(after, dict) else ''
    confirmed = read_status == 200 and after_configured == desired
    return {
        'object_id': object_id, 'ok': confirmed,
        'stage': 'confirmed' if confirmed else 'not_confirmed',
        'post_http_status': post_status,
        'post_response_success': bool(isinstance(post_body, dict) and post_body.get('success') is True),
        'readback_http_status': read_status,
        'before': {'status': before.get('status'), 'effective_status': before.get('effective_status'), 'updated_time': before.get('updated_time')},
        'after': {'status': after.get('status') if isinstance(after, dict) else None, 'effective_status': after.get('effective_status') if isinstance(after, dict) else None, 'updated_time': after.get('updated_time') if isinstance(after, dict) else None},
    }


def fmt_number(value: Any, decimals: int = 2) -> str:
    number = finite_float(value)
    if number is None:
        return 'N/D'
    return f'{number:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_money(value: Any) -> str:
    number = finite_float(value)
    return 'N/D' if number is None else f'${number:,.2f}'


def split_messages(text: str, limit: int = 1900) -> list[str]:
    lines = text.splitlines()
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in lines:
        cost = len(line) + 1
        if current and size + cost > limit:
            chunks.append('\n'.join(current))
            current, size = [], 0
        current.append(line)
        size += cost
    if current:
        chunks.append('\n'.join(current))
    return chunks


def _load_ares_discord_token() -> str:
    for raw in Path('/root/.hermes/profiles/ares/.env').read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))
    token = os.environ.get('DISCORD_BOT_TOKEN', '')
    if not token:
        raise RuntimeError('Ares Discord token missing')
    return token


def discord_request(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    token = _load_ares_discord_token()
    data = None
    headers = {'Authorization': f'Bot {token}', 'User-Agent': 'mgs-ares-eggbev-reporting/1.0'}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode()
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(DISCORD_API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode('utf-8', 'replace')
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        exc.read()
        return exc.code, None


def post_to_thread(thread_id: str, message: str) -> dict[str, Any]:
    posted: list[str] = []
    for chunk in split_messages(message):
        status, body = discord_request('POST', f'/channels/{thread_id}/messages', {'content': chunk, 'allowed_mentions': {'parse': []}})
        message_id = norm((body or {}).get('id')) if isinstance(body, dict) else ''
        if status not in {200, 201} or not message_id:
            return {'ok': False, 'http_status': status, 'posted_count': len(posted)}
        read_status, read_body = discord_request('GET', f'/channels/{thread_id}/messages/{message_id}')
        if read_status != 200 or not isinstance(read_body, dict) or norm(read_body.get('content')) != chunk:
            return {'ok': False, 'http_status': read_status, 'posted_count': len(posted), 'stage': 'readback'}
        posted.append(message_id)
    return {'ok': True, 'posted_count': len(posted), 'message_ids': posted, 'content_sha256': hashlib.sha256(message.encode()).hexdigest()}
