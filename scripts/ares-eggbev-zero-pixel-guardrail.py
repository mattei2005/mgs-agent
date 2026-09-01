#!/usr/bin/env python3
"""Pause active Eggbev campaigns after 03:00 ET when pixel results stay zero.

This is the notification-independent Page safety lane requested by Nicolas. It
uses live Meta campaign spend and the custom pixel-result action optimized by
the exact Eggbev promoted_object. Eligible writes are campaign PAUSED only,
with pre-read, one status POST and GET readback. It never reactivates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
OP_PATH = BASE / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json'
ACCOUNT_PATH = BASE / 'data/ares/meta-ads/accounts/1034081997659047.json'
STATE_PATH = BASE / 'data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/zero-pixel-result-guardrail.json'
LOCK_PATH = BASE / 'data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/zero-pixel-result-guardrail.lock'
AUDIT_DIR = BASE / 'data/ares/meta-ads/audit/guardrails/Eggbev-US-CC-EN-BOT/zero-pixel-results'
LEAD_GUARDRAIL_PATH = BASE / 'scripts/ares-eggbev-page-lead-guardrail.py'
META_COMMON_PATH = BASE / 'scripts/ares-meta-common.py'
NY = ZoneInfo('America/New_York')
PIXEL_ACTION_TYPE = 'offsite_conversion.fb_pixel_custom'


class ZeroPixelGuardrailError(RuntimeError):
    pass


def now_et() -> dt.datetime:
    return dt.datetime.now(NY)


def norm(value: Any) -> str:
    return str(value or '').strip()


def finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float('inf'), float('-inf')):
        return None
    return number


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists() and default is not None:
        return dict(default)
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ZeroPixelGuardrailError(f'invalid JSON object: {path.name}')
    return payload


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def open_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, 'r+')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ZeroPixelGuardrailError(f'cannot load module {name}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def after_daily_gate(run_at: dt.datetime, gate_hour: int = 3) -> bool:
    return run_at.astimezone(NY).hour >= int(gate_hour)


def action_value(actions: Any, action_type: str = PIXEL_ACTION_TYPE) -> float:
    total = 0.0
    for row in actions or []:
        if not isinstance(row, dict) or norm(row.get('action_type')) != action_type:
            continue
        total += finite_float(row.get('value')) or 0.0
    return total


def aggregate_campaign_insights(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        campaign_id = norm(row.get('campaign_id'))
        if not campaign_id:
            continue
        item = result.setdefault(campaign_id, {
            'campaign_id': campaign_id,
            'campaign_name': norm(row.get('campaign_name')),
            'spend': 0.0,
            'pixel_results': 0.0,
            'insight_rows': 0,
        })
        item['spend'] += finite_float(row.get('spend')) or 0.0
        item['pixel_results'] += action_value(row.get('actions'))
        item['insight_rows'] += 1
    return result


def promoted_object_matches(adset: dict[str, Any], policy: dict[str, Any]) -> bool:
    promoted = adset.get('promoted_object') or {}
    expected = policy.get('pixel_event') or {}
    return all((
        norm(adset.get('optimization_goal')).upper() == 'OFFSITE_CONVERSIONS',
        norm(promoted.get('pixel_id')) == norm(expected.get('pixel_id')),
        norm(promoted.get('custom_event_type')).upper() == norm(expected.get('custom_event_type')).upper(),
        norm(promoted.get('custom_event_str')) == norm(expected.get('custom_event_str')),
    ))


def fetch_live_snapshot(meta, token: str, act: str) -> dict[str, Any]:
    """Read account/campaign insights, then active-campaign ad sets in two batches."""

    def parse_batch(responses: Any, expected: list[str]) -> dict[str, dict[str, Any]]:
        if not isinstance(responses, list):
            raise ZeroPixelGuardrailError('Meta batch returned invalid outer payload')
        by_name = {norm(row.get('name')): row for row in responses if isinstance(row, dict)}
        result: dict[str, dict[str, Any]] = {}
        for name in expected:
            response = by_name.get(name) or {}
            code = int(response.get('code') or 0)
            body = response.get('body')
            if code != 200 or not isinstance(body, dict):
                detail = meta.safe_meta_error(body) if isinstance(body, dict) else {'invalid_body': True}
                raise ZeroPixelGuardrailError(
                    f'Meta batch child {name} failed: HTTP {code}; {json.dumps(detail, ensure_ascii=False, sort_keys=True)}'
                )
            result[name] = body
        return result

    status, responses, _ = meta.graph_batch_get(token, [
        {
            'name': 'account',
            'path': act,
            'params': {'fields': 'id,name,account_status,currency,timezone_name,disable_reason'},
        },
        {
            'name': 'campaigns',
            'path': act + '/campaigns',
            'params': {
                'fields': 'id,name,status,effective_status,configured_status,daily_budget,updated_time',
                'effective_status': ['ACTIVE'],
                'limit': 200,
            },
        },
        {
            'name': 'insights',
            'path': act + '/insights',
            'params': {
                'level': 'campaign',
                'date_preset': 'today',
                'fields': 'campaign_id,campaign_name,spend,actions',
                'action_breakdowns': 'action_target_id',
                'limit': 200,
            },
        },
    ])
    if status != 200:
        raise ZeroPixelGuardrailError(f'Meta batch preflight failed: HTTP {status}')
    primary = parse_batch(responses, ['account', 'campaigns', 'insights'])
    for name in ('campaigns', 'insights'):
        if (primary[name].get('paging') or {}).get('next'):
            raise ZeroPixelGuardrailError(f'Meta batch child {name} requires pagination; bounded snapshot incomplete')
    campaigns = primary['campaigns'].get('data')
    insights = primary['insights'].get('data')
    if not isinstance(campaigns, list) or not isinstance(insights, list):
        raise ZeroPixelGuardrailError('Meta campaign/insight batch returned invalid data')

    active_campaign_ids = [norm(row.get('id')) for row in campaigns if norm(row.get('id'))]
    adsets: list[dict[str, Any]] = []
    if active_campaign_ids:
        requests = [{
            'name': f'adsets:{campaign_id}',
            'path': campaign_id + '/adsets',
            'params': {
                'fields': 'id,name,status,effective_status,configured_status,campaign_id,optimization_goal,promoted_object,updated_time',
                'limit': 50,
            },
        } for campaign_id in active_campaign_ids]
        status, responses, _ = meta.graph_batch_get(token, requests)
        if status != 200:
            raise ZeroPixelGuardrailError(f'Meta ad-set batch failed: HTTP {status}')
        adset_bodies = parse_batch(responses, [request['name'] for request in requests])
        for name, body in adset_bodies.items():
            if (body.get('paging') or {}).get('next'):
                raise ZeroPixelGuardrailError(f'Meta batch child {name} requires pagination; bounded snapshot incomplete')
            rows = body.get('data')
            if not isinstance(rows, list):
                raise ZeroPixelGuardrailError(f'Meta batch child {name} returned invalid data')
            adsets.extend(
                row for row in rows
                if isinstance(row, dict)
                and norm(row.get('configured_status') or row.get('status')).upper() == 'ACTIVE'
                and norm(row.get('effective_status')).upper() == 'ACTIVE'
            )
    return {
        'account': primary['account'],
        'campaigns': campaigns,
        'adsets': adsets,
        'insights': insights,
    }


def plan_guardrail(
    campaigns: list[dict[str, Any]],
    adsets: list[dict[str, Any]],
    insight_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    threshold = finite_float(policy.get('spend_threshold_usd')) or 2.0
    insights = aggregate_campaign_insights(insight_rows)
    adsets_by_campaign: dict[str, list[dict[str, Any]]] = {}
    for adset in adsets:
        campaign_id = norm(adset.get('campaign_id'))
        if campaign_id:
            adsets_by_campaign.setdefault(campaign_id, []).append(adset)
    candidates: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    for campaign in campaigns:
        campaign_id = norm(campaign.get('id'))
        configured = norm(campaign.get('configured_status') or campaign.get('status')).upper()
        effective = norm(campaign.get('effective_status')).upper()
        if not campaign_id or configured != 'ACTIVE' or effective != 'ACTIVE':
            continue
        metric = insights.get(campaign_id) or {
            'campaign_id': campaign_id,
            'campaign_name': norm(campaign.get('name')),
            'spend': 0.0,
            'pixel_results': 0.0,
            'insight_rows': 0,
        }
        row = {
            'campaign_id': campaign_id,
            'campaign_name': norm(campaign.get('name')) or metric.get('campaign_name'),
            'campaign_status': configured,
            'campaign_effective_status': effective,
            'spend': finite_float(metric.get('spend')) or 0.0,
            'pixel_results': finite_float(metric.get('pixel_results')) or 0.0,
            'insight_rows': int(metric.get('insight_rows') or 0),
        }
        observed.append(row)
        if row['spend'] <= threshold or row['pixel_results'] > 0:
            continue
        linked_adsets = adsets_by_campaign.get(campaign_id, [])
        if not linked_adsets:
            issues.append({**row, 'issue': 'active_campaign_without_active_adset_readback'})
            continue
        mismatched = [adset for adset in linked_adsets if not promoted_object_matches(adset, policy)]
        if mismatched:
            issues.append({**row, 'issue': 'pixel_promoted_object_mismatch', 'active_adsets': len(linked_adsets)})
            continue
        candidates.append({
            **row,
            'reason': 'spend_strictly_over_threshold_after_03_and_zero_pixel_results',
            'spend_threshold_usd': threshold,
            'pixel_action_type': norm((policy.get('pixel_event') or {}).get('insights_action_type')) or PIXEL_ACTION_TYPE,
            'active_adsets': len(linked_adsets),
        })
    return {
        'candidates': candidates,
        'issues': issues,
        'observed': observed,
        'counts': {
            'active_campaigns': len(observed),
            'candidates': len(candidates),
            'issues': len(issues),
        },
    }


def build_action_alert(candidates: list[dict[str, Any]], actions: list[dict[str, Any]], run_at: dt.datetime) -> str:
    confirmed = sum(1 for row in actions if row.get('ok'))
    failed = len(actions) - confirmed
    names = ', '.join(norm(row.get('campaign_name')) for row in candidates[:3]) or 'N/D'
    if len(candidates) > 3:
        names += f' +{len(candidates) - 3}'
    icon = '⚠️' if failed else '⛔'
    title = 'PIXEL ZERO — PENDÊNCIA' if failed else 'PIXEL ZERO — CAMPANHAS PAUSADAS'
    return '\n'.join([
        f'{icon} **{title}**',
        f'Campanhas: **{len(candidates)}** · {names}',
        f'Regra: `após 03:00 ET` + `spend > US$2` + `Eggbev PV U = 0`',
        f'Pausadas/readback: **{confirmed}/{len(actions)}**' + (f' · pendentes: **{failed}**' if failed else ' ✅') + f' · `{run_at.strftime("%H:%M ET")}` · reativação: **não**',
    ])


def build_issue_alert(issues: list[dict[str, Any]], run_at: dt.datetime) -> str:
    codes: dict[str, int] = {}
    for row in issues:
        code = norm(row.get('issue')) or 'unknown'
        codes[code] = codes.get(code, 0) + 1
    return '\n'.join([
        '⚠️ **PIXEL ZERO — AÇÃO BLOQUEADA**',
        f'Campanhas em risco: **{len(issues)}** · ação Meta: **nenhuma**',
        'Motivos: ' + ', '.join(f'`{code}` ×{count}' for code, count in sorted(codes.items())),
        f'Fonte: `Meta Ads + promoted_object` · `{run_at.strftime("%H:%M ET")}`',
    ])


def post_with_fallback(lead_module, primary_thread_id: str, fallback_thread_id: str, message: str) -> dict[str, Any]:
    return lead_module.post_with_fallback(primary_thread_id, fallback_thread_id, message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--post-alerts', action='store_true')
    parser.add_argument('--at', help='dry-run-only ISO timestamp')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    if args.apply and args.at:
        parser.error('--at is dry-run only')
    run_at = dt.datetime.fromisoformat(args.at).astimezone(NY) if args.at else now_et()

    with open_lock() as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        operation = load_json(OP_PATH)
        policy = operation.get('zero_pixel_result_guardrail') or {}
        state = load_json(STATE_PATH, {'version': 1, 'pending_alerts': []})
        run_id = run_at.strftime('%Y%m%dT%H%M%S%z')
        audit_path = AUDIT_DIR / f'run-{run_id}.json'
        run: dict[str, Any] = {
            'run_id': run_id,
            'started_at_et': run_at.isoformat(),
            'mode': 'controlled_write' if args.apply else 'dry_run',
            'gate_hour_et': int(policy.get('after_hour_et') or 3),
            'writes': [],
            'deliveries': [],
            'ok': False,
            'audit_path': str(audit_path),
        }
        atomic_json(audit_path, run)
        try:
            if not after_daily_gate(run_at, int(policy.get('after_hour_et') or 3)):
                run.update({'ok': True, 'status': 'before_03_noop', 'finished_at_et': now_et().isoformat()})
                atomic_json(audit_path, run)
                if not args.quiet:
                    print(json.dumps({'ok': True, 'status': 'before_03_noop', 'audit_path': str(audit_path)}))
                return 0
            if args.apply and (not policy.get('policy_approved') or not (policy.get('runtime') or {}).get('write_enabled')):
                raise ZeroPixelGuardrailError('zero-pixel controlled-write is not enabled')
            if args.apply and not args.post_alerts:
                raise ZeroPixelGuardrailError('controlled-write requires --post-alerts')

            discord = policy.get('discord') or {}
            primary_thread_id = norm(discord.get('thread_id'))
            fallback_thread_id = norm(discord.get('fallback_error_thread_id'))
            if args.post_alerts and not primary_thread_id:
                raise ZeroPixelGuardrailError('missing fixed Page and Limits thread')
            lead_module = load_module('ares_eggbev_lead_zero_pixel', LEAD_GUARDRAIL_PATH)

            pending = list(state.get('pending_alerts') or [])
            remaining_pending: list[dict[str, Any]] = []
            if args.post_alerts:
                for item in pending:
                    delivery = post_with_fallback(lead_module, primary_thread_id, fallback_thread_id, norm(item.get('message')))
                    run['deliveries'].append({'type': 'pending_recovery', **delivery})
                    if not delivery.get('ok'):
                        remaining_pending.append(item)
                state['pending_alerts'] = remaining_pending
                atomic_json(STATE_PATH, state)
                if remaining_pending:
                    raise ZeroPixelGuardrailError('pending_alert_delivery_recovery_failed')

            account_file = load_json(ACCOUNT_PATH)
            account = (account_file.get('accounts') or [{}])[0]
            os.environ.setdefault('ARES_META_TOKEN_CACHE_PATH', '/root/.cache/mgs/ares-meta-token-eggbev-us-cc-en-01-g006.json')
            meta = load_module('ares_meta_common_zero_pixel', META_COMMON_PATH)
            token, token_field = meta.get_token_from_1password(account.get('token_1password_item'))
            run['credential_readback'] = {
                'item': account.get('token_1password_item'),
                'field': token_field,
                'token_len': len(token),
            }
            account_id = norm((operation.get('account') or {}).get('account_id'))
            act = 'act_' + account_id
            snapshot = fetch_live_snapshot(meta, token, act)
            live_account = snapshot['account']
            if live_account.get('currency') != 'USD' or live_account.get('timezone_name') != 'America/New_York' or int(live_account.get('account_status') or 0) != 1:
                raise ZeroPixelGuardrailError('Meta account identity/currency/timezone/status preflight failed')
            campaigns = snapshot['campaigns']
            adsets = snapshot['adsets']
            insights = snapshot['insights']
            plan = plan_guardrail(campaigns, adsets, insights, policy)
            run['meta_readback'] = {
                'account_http_status': 200,
                'active_campaigns': len(campaigns),
                'active_adsets': len(adsets),
                'campaign_insight_rows': len(insights),
                'currency': live_account.get('currency'),
                'timezone_name': live_account.get('timezone_name'),
            }
            run['plan'] = plan
            atomic_json(audit_path, run)

            if args.apply and plan['issues']:
                message = build_issue_alert(plan['issues'], run_at)
                delivery = post_with_fallback(lead_module, primary_thread_id, fallback_thread_id, message)
                run['deliveries'].append({'type': 'mapping_issue', **delivery})
                if not delivery.get('ok'):
                    state.setdefault('pending_alerts', []).append({'message': message, 'created_at_et': run_at.isoformat()})
                    atomic_json(STATE_PATH, state)
                    raise ZeroPixelGuardrailError('mapping_issue_alert_delivery_failed')

            actions: list[dict[str, Any]] = []
            if args.apply:
                for candidate in plan['candidates']:
                    action = lead_module.reconcile_pause(meta, token, candidate)
                    action.update({
                        'reason': candidate.get('reason'),
                        'spend': candidate.get('spend'),
                        'pixel_results': candidate.get('pixel_results'),
                    })
                    actions.append(action)
                    run['writes'].append(action)
                    atomic_json(audit_path, run)
                if actions:
                    message = build_action_alert(plan['candidates'], actions, run_at)
                    delivery = post_with_fallback(lead_module, primary_thread_id, fallback_thread_id, message)
                    run['deliveries'].append({'type': 'zero_pixel_action', **delivery})
                    if not delivery.get('ok'):
                        state.setdefault('pending_alerts', []).append({'message': message, 'created_at_et': run_at.isoformat()})
                        atomic_json(STATE_PATH, state)
                        raise ZeroPixelGuardrailError('action_alert_delivery_failed')

            writes_ok = all(row.get('ok') for row in actions)
            run.update({
                'ok': writes_ok,
                'status': 'completed',
                'campaigns_paused_confirmed': sum(1 for row in actions if row.get('ok')),
                'alerts_delivered': sum(1 for row in run['deliveries'] if row.get('ok')),
                'finished_at_et': now_et().isoformat(),
            })
            state.update({
                'last_run_at_et': run_at.isoformat(),
                'last_ok': writes_ok,
                'last_candidates': len(plan['candidates']),
                'last_campaigns_paused_confirmed': run['campaigns_paused_confirmed'],
                'last_audit_path': str(audit_path),
            })
            atomic_json(STATE_PATH, state)
            atomic_json(audit_path, run)
            if not args.quiet or plan['candidates'] or plan['issues']:
                print(json.dumps({
                    'ok': run['ok'],
                    'status': run['status'],
                    'active_campaigns': plan['counts']['active_campaigns'],
                    'candidates': plan['counts']['candidates'],
                    'issues': plan['counts']['issues'],
                    'campaigns_paused_confirmed': run['campaigns_paused_confirmed'],
                    'alerts_delivered': run['alerts_delivered'],
                    'audit_path': str(audit_path),
                }, ensure_ascii=False))
            return 0 if writes_ok else 2
        except Exception as exc:
            run.update({'ok': False, 'error': f'{type(exc).__name__}: {exc}', 'finished_at_et': now_et().isoformat()})
            atomic_json(audit_path, run)
            state.update({'last_run_at_et': run_at.isoformat(), 'last_ok': False, 'last_error': str(exc), 'last_audit_path': str(audit_path)})
            atomic_json(STATE_PATH, state)
            if not args.quiet:
                print(json.dumps({'ok': False, 'error': str(exc), 'audit_path': str(audit_path)}, ensure_ascii=False))
            return 2


if __name__ == '__main__':
    raise SystemExit(main())
