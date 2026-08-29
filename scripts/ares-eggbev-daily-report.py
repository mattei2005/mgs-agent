#!/usr/bin/env python3
"""Eggbev Daily and on-demand report runner.

Default is read-only stdout. Discord posting is separately gated in the live
operation contract and is disabled while no cron has been approved.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

COMMON_PATH = Path('/root/mgs-agent/scripts/ares-eggbev-roas-common.py')


def _load_common():
    import importlib.util
    spec = importlib.util.spec_from_file_location('ares_eggbev_daily_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load Eggbev report common runtime')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = _load_common()
AUDIT_DIR = common.BASE / 'data/ares/meta-ads/audit/eggbev/daily-report'


def parse_at(value: str | None) -> dt.datetime:
    if not value:
        return common.now_et()
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=common.ET)
    return parsed.astimezone(common.ET)


def report_dates(period: str, at: dt.datetime) -> list[tuple[str, str]]:
    if period == 'auto':
        if at.strftime('%H:%M') == '06:00':
            return [((at.date() - dt.timedelta(days=1)).isoformat(), 'Fechamento anterior'), (at.date().isoformat(), 'Parcial atual 06:00')]
        return [(at.date().isoformat(), 'Parcial atual')]
    if period == 'today':
        return [(at.date().isoformat(), 'Parcial atual')]
    if period == 'yesterday':
        return [((at.date() - dt.timedelta(days=1)).isoformat(), 'Fechamento anterior')]
    try:
        return [(dt.date.fromisoformat(period).isoformat(), 'Período solicitado')]
    except ValueError as exc:
        raise ValueError('--period must be auto, today, yesterday or YYYY-MM-DD') from exc


def sum_field(rows: list[dict[str, Any]], key: str) -> float:
    return sum(common.finite_float(row.get(key)) or 0.0 for row in rows)


def aggregate_meta(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get('insights') or []
    spends = sum(common.finite_float(row.get('spend')) or 0.0 for row in rows)
    impressions = sum(common.finite_float(row.get('impressions')) or 0.0 for row in rows)
    purchases_value = sum(common.action_value(row.get('action_values'), common.PURCHASE_ACTIONS) or 0.0 for row in rows)
    messaging_results = sum(common.action_value(row.get('actions'), common.MESSAGING_ACTIONS) or 0.0 for row in rows)
    roas = purchases_value / spends if spends > 0 else None
    cpm = spends * 1000.0 / impressions if impressions > 0 else None
    cost_per_message = spends / messaging_results if messaging_results > 0 else None
    weighted_ctr_numerator = sum((common.finite_float(row.get('ctr')) or 0.0) * (common.finite_float(row.get('impressions')) or 0.0) for row in rows)
    ctr = weighted_ctr_numerator / impressions if impressions > 0 else None
    by_campaign: dict[str, dict[str, Any]] = defaultdict(lambda: {'name': '', 'spend': 0.0, 'purchase_value': 0.0, 'messaging_results': 0.0})
    for row in rows:
        campaign_id = common.norm(row.get('campaign_id')) or 'unknown'
        target = by_campaign[campaign_id]
        target['name'] = common.norm(row.get('campaign_name')) or target['name']
        target['spend'] += common.finite_float(row.get('spend')) or 0.0
        target['purchase_value'] += common.action_value(row.get('action_values'), common.PURCHASE_ACTIONS) or 0.0
        target['messaging_results'] += common.action_value(row.get('actions'), common.MESSAGING_ACTIONS) or 0.0
    campaigns = []
    for campaign_id, row in by_campaign.items():
        spend = row['spend']
        campaigns.append({
            'campaign_id': campaign_id, 'name': row['name'], 'spend': spend,
            'purchase_roas': row['purchase_value'] / spend if spend > 0 else None,
            'messaging_results': row['messaging_results'],
            'cost_per_message': spend / row['messaging_results'] if row['messaging_results'] > 0 else None,
        })
    campaigns.sort(key=lambda row: (-row['spend'], row['name']))
    return {
        'spend': spends, 'purchase_value': purchases_value, 'purchase_roas': roas,
        'messaging_results': messaging_results, 'cost_per_message': cost_per_message,
        'impressions': impressions, 'cpm': cpm, 'ctr': ctr, 'campaigns': campaigns,
    }


def aggregate_sb(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get('target_report_rows') or []
    return {
        'ready': bundle.get('ready'), 'reason': bundle.get('reason'), 'rows': len(rows),
        'investment': sum_field(rows, 'INVESTIMENT'), 'revenue': sum_field(rows, 'REVENUE'),
        'drip_revenue': sum_field(rows, 'DRIP_REVENUE'), 'broadcast_revenue': sum_field(rows, 'BD_REVENUE'),
        'leads': sum_field(rows, 'LEADS'), 'leads_total': sum_field(rows, 'LEADS_TOTAL'),
        'available_account_names': bundle.get('available_account_names'),
        'roi_real': None, 'roi_estimated': None, 'rps': None,
        'formula_note': 'ROI/RPS N/D: nenhuma fórmula Eggbev aprovada; valores brutos preservados.',
    }


def render_period(period: dict[str, Any]) -> list[str]:
    meta = period['meta']
    sb = period['smart_bidding']
    lines = [
        f"**{period['label']} — {period['date']}**",
        '```text',
        'Meta (USD)                    Valor',
        '----------------------------  ------------',
        f"Amount spent                 {common.fmt_money(meta.get('spend')):>12}",
        f"Purchase ROAS                {common.fmt_number(meta.get('purchase_roas')):>12}",
        f"Results/conversas            {common.fmt_number(meta.get('messaging_results'), 0):>12}",
        f"Custo por conversa           {common.fmt_money(meta.get('cost_per_message')):>12}",
        f"CPM                           {common.fmt_money(meta.get('cpm')):>12}",
        f"CTR                           {(common.fmt_number(meta.get('ctr')) + '%'):>12}",
        '```',
        '```text',
        'Smart Bidding (USD)           Valor',
        '----------------------------  ------------',
        f"Linhas conta alvo             {sb.get('rows', 0):>12}",
        f"Investimento                  {common.fmt_money(sb.get('investment')):>12}",
        f"Receita                       {common.fmt_money(sb.get('revenue')):>12}",
        f"Receita drip                  {common.fmt_money(sb.get('drip_revenue')):>12}",
        f"Receita broadcast             {common.fmt_money(sb.get('broadcast_revenue')):>12}",
        f"Leads                         {common.fmt_number(sb.get('leads'), 0):>12}",
        f"RPS                           {'N/D':>12}",
        f"ROI real                      {'N/D':>12}",
        f"ROI estimado                  {'N/D':>12}",
        '```',
    ]
    if not sb.get('ready'):
        lines.append('⚠️ Smart Bidding não reconciliada: ' + common.norm(sb.get('reason')) + '.')
    lines.append(sb.get('formula_note'))
    campaigns = meta.get('campaigns') or []
    if campaigns:
        lines.extend(['', '**Campanhas com entrega**', '```text', 'Campanha                     Spend      ROAS  Resultados'])
        lines.append('---------------------------  --------  ------  ----------')
        for row in campaigns[:20]:
            name = (row.get('name') or row.get('campaign_id') or 'N/D')[:27]
            lines.append(f"{name:<27}  {common.fmt_money(row.get('spend')):>8}  {common.fmt_number(row.get('purchase_roas')):>6}  {common.fmt_number(row.get('messaging_results'), 0):>10}")
        lines.append('```')
    else:
        lines.append('Sem entrega Meta no período.')
    return lines


def render_report(run: dict[str, Any]) -> str:
    lines = [
        '📊 **Eggbev-US-CC-EN — Diário**',
        f"Gerado: {run.get('started_at_et')} | Conta: Eggbev-US-CC-EN-01-G006 | Moeda: USD",
        'Fonte Meta: API live | Fonte externa: Smart Bidding Messenger',
        '',
    ]
    for index, period in enumerate(run.get('periods') or []):
        if index:
            lines.append('\n──────────')
        lines.extend(render_period(period))
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--period', default='auto', help='auto, today, yesterday or YYYY-MM-DD')
    parser.add_argument('--post', action='store_true', help='post to fixed Daily thread when runtime is enabled')
    parser.add_argument('--at', help='read-only ISO timestamp for deterministic auto-period selection')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    if args.post and args.at:
        parser.error('--at is forbidden with --post')
    at = parse_at(args.at)
    run_id = at.strftime('%Y%m%dT%H%M%S%z')
    audit_path = AUDIT_DIR / f'run-{run_id}.json'
    operation = common.load_json(common.OP_PATH)
    account_file = common.load_json(common.ACCOUNT_PATH)
    account = (account_file.get('accounts') or [{}])[0]
    runtime = (operation.get('daily_reporting_policy') or {}).get('runtime') or {}
    state, _ = common.load_state(at.date(), common.finite_float((operation.get('roas_cycle_policy') or {}).get('daily_reset_value')) or 0.40)
    run: dict[str, Any] = {
        'ok': False, 'mode': 'read_only', 'run_id': run_id, 'started_at_et': at.isoformat(),
        'period_request': args.period, 'periods': [], 'writes_attempted': 0,
        'audit_path': str(audit_path),
    }
    common.atomic_json(audit_path, run)
    try:
        if args.post and not runtime.get('post_enabled'):
            raise RuntimeError(runtime.get('blocked_reason') or 'Daily posting disabled')
        meta, sb, token, credential = common.load_runtime_modules(account)
        run['credential_readback'] = credential
        account_id = common.norm((operation.get('account') or {}).get('account_id'))
        for report_date, label in report_dates(args.period, at):
            meta_bundle = common.fetch_meta_bundle(meta, token, account_id, state, report_date)
            try:
                sb_bundle = common.fetch_sb_bundle(sb, operation, report_date)
            except Exception as exc:
                sb_bundle = {'ready': False, 'reason': f'{type(exc).__name__}: {exc}', 'target_report_rows': [], 'available_account_names': []}
            run['periods'].append({
                'date': report_date, 'label': label,
                'meta': aggregate_meta(meta_bundle),
                'smart_bidding': aggregate_sb(sb_bundle),
                'readback': {
                    'meta_insight_rows': len(meta_bundle.get('insights') or []),
                    'smart_bidding_target_rows': len(sb_bundle.get('target_report_rows') or []),
                    'smart_bidding_available_accounts': sb_bundle.get('available_account_names'),
                },
            })
            common.atomic_json(audit_path, run)
        report = render_report(run)
        if args.post:
            run['delivery'] = common.post_to_thread(runtime.get('thread_id') or '1541578596253175858', report)
            if not run['delivery'].get('ok'):
                raise RuntimeError('Daily report delivery/readback failed')
        run['ok'] = True
        run['finished_at_et'] = common.now_et().isoformat()
        common.atomic_json(audit_path, run)
        if not args.quiet:
            print(report if not args.post else json.dumps({'ok': True, 'delivery': run.get('delivery'), 'audit_path': str(audit_path)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        run['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        run['finished_at_et'] = common.now_et().isoformat()
        common.atomic_json(audit_path, run)
        print(json.dumps({'ok': False, 'error': run['error'], 'writes_attempted': 0, 'audit_path': str(audit_path)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
