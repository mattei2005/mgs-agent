#!/usr/bin/env python3
"""Eggbev deterministic ROAS cycle runner.

Default mode is dry-run. Controlled writes require operation runtime enablement,
--apply, --post-report, reconciled sources, no conflicting native rule, and
pre/post Meta readbacks. This script never changes budget, ad set, or creative.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import sys
from pathlib import Path
from typing import Any

COMMON_PATH = Path('/root/mgs-agent/scripts/ares-eggbev-roas-common.py')


def _load_common():
    import importlib.util
    spec = importlib.util.spec_from_file_location('ares_eggbev_roas_common_runtime', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load Eggbev ROAS common runtime')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = _load_common()


def parse_at(value: str | None) -> dt.datetime:
    if not value:
        return common.now_et()
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=common.ET)
    return parsed.astimezone(common.ET)


def render_report(run: dict[str, Any]) -> str:
    source = run.get('source_gate') or {}
    plan = run.get('plan') or {}
    counts = plan.get('counts') or {}
    lines = [
        '⚔️ **Eggbev-US-CC-EN — Corte e ROAS**',
        f"Horário: {run.get('started_at_et')} | Fase: {run.get('phase')} | Threshold: {common.fmt_number(run.get('threshold'))}",
        f"Modo: {'SIMULAÇÃO' if run.get('mode') == 'dry_run' else 'CONTROLLED-WRITE'} | Meta: {run.get('meta_status')} | Smart Bidding: {run.get('smart_bidding_status')}",
    ]
    reasons = source.get('reasons') or []
    if run.get('phase') == 'RESET':
        lines.append('🔄 Reset local do threshold; nenhuma leitura ou alteração Meta necessária.')
    elif reasons:
        lines.append('🚫 Write bloqueado: ' + '; '.join(reasons))
    else:
        lines.append('✅ Fontes reconciliadas e regra nativa sem conflito.')
    lines.extend([
        '',
        '```text',
        'Ação                         Qtd',
        '---------------------------  ---',
        f"Anúncios avaliados           {counts.get('ads_considered', 0):>3}",
        f"Pausar anúncios              {counts.get('pause_ads', 0):>3}",
        f"Reativar anúncios            {counts.get('reactivate_ads', 0):>3}",
        f"Pausar campanhas             {counts.get('pause_campaigns', 0):>3}",
        f"Reativar campanhas           {counts.get('reactivate_campaigns', 0):>3}",
        f"Escalas +30% recomendadas    {counts.get('budget_scale_candidates', 0):>3}",
        '```',
    ])
    actionable = [row for row in plan.get('decisions') or [] if row.get('action') != 'KEEP']
    if actionable:
        lines.extend(['', '**Decisões por anúncio**'])
        for row in actionable[:25]:
            emoji = '⏸️' if row.get('action') == 'PAUSE_AD' else '▶️'
            lines.append(
                f"{emoji} {row.get('ad_name') or row.get('ad_id')} — Spend {common.fmt_money(row.get('spend'))} | "
                f"ROAS {common.fmt_number(row.get('purchase_roas'))} | {row.get('reason')}"
            )
        if len(actionable) > 25:
            lines.append(f"…mais {len(actionable) - 25} decisões no audit.")
    else:
        lines.extend(['', 'Nenhuma mudança de anúncio planejada neste ciclo.'])
    scale_candidates = plan.get('budget_scale_candidates') or []
    if scale_candidates:
        lines.extend(['', '**Escala de budget — recomendação dry-run**'])
        for row in scale_candidates[:25]:
            lines.append(
                f"📈 {row.get('campaign_name') or row.get('campaign_id')} — ROAS {common.fmt_number(row.get('purchase_roas'))} | "
                f"{common.fmt_money(row.get('current_daily_budget_usd'))} → {common.fmt_money(row.get('target_daily_budget_usd'))} (+30%)"
            )
        lines.append('Budget write bloqueado até Nicolas definir frequência/cooldown da escala.')
    writes = run.get('writes') or []
    if writes:
        confirmed = sum(1 for row in writes if row.get('ok'))
        lines.append(f"\nReadback de writes: {confirmed}/{len(writes)} confirmados.")
    if run.get('phase') == 'RESET':
        lines.append('\nReset diário: threshold voltou para 0,40; nenhum corte ou reativação Meta.')
    return '\n'.join(lines)


def _active_ads_for_campaign(meta, token: str, campaign_id: str) -> list[dict[str, Any]]:
    return common.fetch_all_meta(meta, token, campaign_id + '/ads', {
        'fields': 'id,name,status,effective_status,configured_status',
        'effective_status': ['ACTIVE'],
        'limit': 200,
    })


def execute_plan(meta, token: str, plan: dict[str, Any], state: dict[str, Any], run: dict[str, Any]) -> None:
    writes = run['writes']
    campaign_reactivations = [row for row in plan.get('campaign_actions') or [] if row.get('action') == 'REACTIVATE_CAMPAIGN']
    blocked_campaigns: set[str] = set()
    for row in campaign_reactivations:
        result = common.reconcile_status_write(meta, token, row['campaign_id'], 'ACTIVE')
        result.update({'kind': 'campaign', 'action': 'REACTIVATE_CAMPAIGN', 'name': row.get('campaign_name')})
        writes.append(result)
        if result.get('ok'):
            state.get('paused_campaigns', {}).pop(row['campaign_id'], None)
        else:
            blocked_campaigns.add(row['campaign_id'])
        common.atomic_json(Path(run['audit_path']), run)

    for row in [item for item in plan.get('decisions') or [] if item.get('action') == 'REACTIVATE_AD']:
        if row.get('campaign_id') in blocked_campaigns:
            writes.append({'object_id': row.get('ad_id'), 'kind': 'ad', 'action': 'REACTIVATE_AD', 'ok': False, 'stage': 'blocked_by_campaign_reactivation_failure'})
            continue
        if row.get('adset_status') != 'ACTIVE':
            writes.append({'object_id': row.get('ad_id'), 'kind': 'ad', 'action': 'REACTIVATE_AD', 'ok': False, 'stage': 'adset_not_configured_active'})
            continue
        result = common.reconcile_status_write(meta, token, row['ad_id'], 'ACTIVE')
        result.update({'kind': 'ad', 'action': 'REACTIVATE_AD', 'name': row.get('ad_name')})
        writes.append(result)
        if result.get('ok'):
            state.get('paused_ads', {}).pop(row['ad_id'], None)
        common.atomic_json(Path(run['audit_path']), run)

    for row in [item for item in plan.get('decisions') or [] if item.get('action') == 'PAUSE_AD']:
        result = common.reconcile_status_write(meta, token, row['ad_id'], 'PAUSED')
        result.update({'kind': 'ad', 'action': 'PAUSE_AD', 'name': row.get('ad_name')})
        writes.append(result)
        if result.get('ok') and result.get('stage') == 'confirmed':
            state.setdefault('paused_ads', {})[row['ad_id']] = {
                'reason': 'roas_cycle', 'campaign_id': row.get('campaign_id'),
                'paused_at_et': run.get('started_at_et'), 'phase': run.get('phase'),
                'threshold': run.get('threshold'), 'purchase_roas': row.get('purchase_roas'),
                'spend': row.get('spend'),
                'meta_updated_time': (result.get('after') or {}).get('updated_time'),
                'adset_id': row.get('adset_id'),
                'adset_updated_time': row.get('adset_updated_time'),
                'campaign_updated_time': row.get('campaign_updated_time'),
            }
        common.atomic_json(Path(run['audit_path']), run)

    for row in [item for item in plan.get('campaign_actions') or [] if item.get('action') == 'PAUSE_CAMPAIGN']:
        active = _active_ads_for_campaign(meta, token, row['campaign_id'])
        if active:
            writes.append({
                'object_id': row['campaign_id'], 'kind': 'campaign', 'action': 'PAUSE_CAMPAIGN',
                'ok': False, 'stage': 'blocked_active_ads_remain', 'active_ads_readback': len(active),
            })
            continue
        result = common.reconcile_status_write(meta, token, row['campaign_id'], 'PAUSED')
        result.update({'kind': 'campaign', 'action': 'PAUSE_CAMPAIGN', 'name': row.get('campaign_name'), 'active_ads_readback': 0})
        writes.append(result)
        if result.get('ok') and result.get('stage') == 'confirmed':
            state.setdefault('paused_campaigns', {})[row['campaign_id']] = {
                'reason': 'roas_zero_active_ads', 'paused_at_et': run.get('started_at_et'),
                'meta_updated_time': (result.get('after') or {}).get('updated_time'),
            }
            for paused_ad in (state.get('paused_ads') or {}).values():
                if isinstance(paused_ad, dict) and paused_ad.get('campaign_id') == row['campaign_id']:
                    paused_ad['campaign_updated_time'] = (result.get('after') or {}).get('updated_time')
        common.atomic_json(Path(run['audit_path']), run)


def sanitized_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        'ok': run.get('ok'), 'mode': run.get('mode'), 'run_id': run.get('run_id'),
        'started_at_et': run.get('started_at_et'), 'phase': run.get('phase'),
        'threshold': run.get('threshold'), 'meta_status': run.get('meta_status'),
        'smart_bidding_status': run.get('smart_bidding_status'),
        'source_gate': run.get('source_gate'), 'counts': (run.get('plan') or {}).get('counts'),
        'writes_attempted': len(run.get('writes') or []),
        'writes_confirmed': sum(1 for row in run.get('writes') or [] if row.get('ok')),
        'delivery': run.get('delivery'), 'audit_path': run.get('audit_path'),
        'error': run.get('error'),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='execute approved controlled writes')
    parser.add_argument('--post-report', action='store_true', help='post the cycle report to the fixed thread')
    parser.add_argument('--at', help='dry-run-only ISO timestamp in America/New_York')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    if args.apply and args.at:
        parser.error('--at is forbidden with --apply')

    with common.open_lock() as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        started = parse_at(args.at)
        run_id = started.strftime('%Y%m%dT%H%M%S%z')
        audit_path = common.AUDIT_DIR / f'run-{run_id}.json'
        operation = common.load_json(common.OP_PATH)
        account_file = common.load_json(common.ACCOUNT_PATH)
        account = (account_file.get('accounts') or [{}])[0]
        policy = operation.get('roas_cycle_policy') or {}
        runtime = policy.get('runtime') or {}
        threshold_policy = policy.get('threshold') or {}
        reset_value = common.finite_float(threshold_policy.get('daily_reset_value')) or 0.40
        state, state_reset = common.load_state(started.date(), reset_value)
        phase = common.phase_for_time(started)
        if phase == 'RESET':
            state = common.rollover_state(state, started.date(), reset_value)
            state_reset = True
        run: dict[str, Any] = {
            'ok': False, 'run_id': run_id, 'started_at_et': started.isoformat(),
            'mode': 'controlled_write' if args.apply else 'dry_run', 'phase': phase,
            'threshold': common.finite_float(state.get('threshold')) or reset_value,
            'state_reset': state_reset, 'operation_id': operation.get('operation_id'),
            'account_id': norm_id(operation), 'writes': [], 'audit_path': str(audit_path),
        }
        common.atomic_json(audit_path, run)
        try:
            if args.apply:
                if not policy.get('policy_approved'):
                    raise RuntimeError('ROAS cycle policy is not approved')
                if not runtime.get('write_enabled'):
                    raise RuntimeError(runtime.get('blocked_reason') or 'ROAS cycle write disabled')
                if not args.post_report:
                    raise RuntimeError('controlled write requires --post-report')
                if phase == 'NO_CYCLE':
                    raise RuntimeError('controlled write requested outside an approved cycle time')
            if phase == 'RESET':
                run.update({
                    'meta_status': 'not_required_for_local_reset',
                    'smart_bidding_status': 'not_required_for_local_reset',
                    'source_gate': {'write_ready': False, 'reset_ready': True, 'reasons': ['reset_only_no_meta_write']},
                    'plan': {
                        'phase': 'RESET', 'threshold': reset_value, 'decisions': [], 'campaign_actions': [],
                        'counts': {'ads_considered': 0, 'pause_ads': 0, 'reactivate_ads': 0, 'pause_campaigns': 0, 'reactivate_campaigns': 0},
                    },
                })
                if args.apply:
                    common.atomic_json(common.ROAS_STATE_PATH, state)
                report = render_report(run)
                if args.post_report:
                    run['delivery'] = common.post_to_thread(runtime.get('thread_id') or '1541578606076231750', report)
                    if not run['delivery'].get('ok'):
                        raise RuntimeError('Discord reset report delivery/readback failed')
                run['ok'] = True
                run['finished_at_et'] = common.now_et().isoformat()
                common.atomic_json(audit_path, run)
                if not args.quiet:
                    print(report if not args.post_report else json.dumps(sanitized_summary(run), ensure_ascii=False, indent=2))
                return 0
            meta, sb, token, credential_readback = common.load_runtime_modules(account)
            run['credential_readback'] = credential_readback
            meta_bundle = common.fetch_meta_bundle(meta, token, norm_id(operation), state, 'today')
            run['meta_status'] = 'ok'
            try:
                sb_bundle = common.fetch_sb_bundle(sb, operation, started.date().isoformat())
                run['smart_bidding_status'] = 'ok' if sb_bundle.get('ready') else sb_bundle.get('reason')
            except Exception as exc:
                sb_bundle = {'ready': False, 'reason': f'{type(exc).__name__}: {exc}', 'target_report_rows': [], 'available_account_names': []}
                run['smart_bidding_status'] = 'unavailable'
            plan = common.decide_cycle(
                meta_bundle.get('ads') or [], meta_bundle.get('tracked_ads') or [],
                meta_bundle.get('insights_by_ad') or {}, state, phase, run['threshold'],
            )
            scale_policy = operation.get('campaign_scaling_policy') or {}
            scale_candidates = common.plan_campaign_budget_scales(
                meta_bundle.get('campaigns') or [], plan.get('decisions') or [], run['threshold'],
                common.finite_float(scale_policy.get('increase_percent')) or 30.0,
            )
            plan['budget_scale_candidates'] = scale_candidates
            plan.setdefault('counts', {})['budget_scale_candidates'] = len(scale_candidates)
            gate = common.source_gate(meta_bundle, sb_bundle, phase)
            run.update({
                'meta_readback': {
                    'account': meta_bundle.get('account'), 'active_campaigns': len(meta_bundle.get('campaigns') or []),
                    'active_ads': len(meta_bundle.get('ads') or []), 'tracked_ads': len(meta_bundle.get('tracked_ads') or []),
                    'insight_rows': len(meta_bundle.get('insights') or []), 'native_rules': meta_bundle.get('native_rules'),
                    'manual_review': meta_bundle.get('manual_review') or [],
                },
                'smart_bidding_readback': {
                    'ready': sb_bundle.get('ready'), 'reason': sb_bundle.get('reason'),
                    'freshness': sb_bundle.get('freshness'),
                    'target_rows': len(sb_bundle.get('target_report_rows') or []),
                    'available_account_names': sb_bundle.get('available_account_names'),
                },
                'source_gate': gate, 'plan': plan,
            })
            common.atomic_json(audit_path, run)
            if args.apply and not gate.get('write_ready'):
                report = render_report(run)
                run['delivery'] = common.post_to_thread(runtime.get('thread_id') or '1541578606076231750', report)
                raise RuntimeError('source/native-rule gate blocked controlled writes')
            if args.apply and phase in {'PHASE_1', 'PHASE_2'}:
                execute_plan(meta, token, plan, state, run)
                state['last_cycle'] = {'run_id': run_id, 'at_et': started.isoformat(), 'phase': phase}
                common.atomic_json(common.ROAS_STATE_PATH, state)
            report = render_report(run)
            if args.post_report:
                run['delivery'] = common.post_to_thread(runtime.get('thread_id') or '1541578606076231750', report)
                if not run['delivery'].get('ok'):
                    raise RuntimeError('Discord cycle report delivery/readback failed')
            run['ok'] = True
            run['finished_at_et'] = common.now_et().isoformat()
            common.atomic_json(audit_path, run)
            if not args.quiet:
                print(report if not args.post_report else json.dumps(sanitized_summary(run), ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            run['ok'] = False
            run['error'] = {'type': type(exc).__name__, 'message': str(exc)}
            run['finished_at_et'] = common.now_et().isoformat()
            common.atomic_json(audit_path, run)
            print(json.dumps(sanitized_summary(run), ensure_ascii=False, indent=2), file=sys.stderr)
            return 2


def norm_id(operation: dict[str, Any]) -> str:
    return common.norm((operation.get('account') or {}).get('account_id'))


if __name__ == '__main__':
    raise SystemExit(main())
