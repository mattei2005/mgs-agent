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
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

COMMON_PATH = Path('/root/mgs-agent/scripts/ares-eggbev-roas-common.py')
REPORTING_PATH = Path('/root/mgs-agent/scripts/ares-eggbev-daily-report.py')


def _load_common():
    import importlib.util
    spec = importlib.util.spec_from_file_location('ares_eggbev_roas_common_runtime', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load Eggbev ROAS common runtime')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = _load_common()


def _load_reporting():
    import importlib.util
    spec = importlib.util.spec_from_file_location('ares_eggbev_cycle_reporting', REPORTING_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load Eggbev reporting helpers')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reporting = _load_reporting()


def parse_at(value: str | None) -> dt.datetime:
    if not value:
        return common.now_et()
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=common.ET)
    return parsed.astimezone(common.ET)


def _cycle_at(value: Any) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(common.norm(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(common.ET)


def _phase_label(value: Any) -> str:
    return {
        'PHASE_1': 'Fase 1', 'PHASE_2': 'Fase 2',
        'RESET': 'Reset diário', 'NO_CYCLE': 'Fora de ciclo',
    }.get(common.norm(value), common.norm(value) or 'N/D')


def _fmt_percent(value: Any) -> str:
    return 'N/D' if common.finite_float(value) is None else common.fmt_number(value) + '%'


def _fmt_signed_percent(value: Any) -> str:
    number = common.finite_float(value)
    if number is None:
        return 'N/D'
    return ('+' if number > 0 else '') + common.fmt_number(number, 1) + '%'


def _display_width(value: Any) -> int:
    text = common.norm(value)
    return sum(
        0 if unicodedata.combining(char) or char == '\ufe0f'
        else 2 if unicodedata.east_asian_width(char) in {'W', 'F'}
        else 1
        for char in text
    )


def _fit(value: Any, width: int, align: str = 'left') -> str:
    text = common.norm(value) or 'N/D'
    if _display_width(text) > width:
        clipped = ''
        for char in text:
            suffix = '…'
            if _display_width(clipped + char + suffix) > width:
                break
            clipped += char
        text = clipped + '…'
    padding = max(0, width - _display_width(text))
    return (' ' * padding + text) if align == 'right' else (text + ' ' * padding)


def _campaign_key(row: dict[str, Any], index: int) -> str:
    name = common.norm(row.get('name'))
    utm = common.norm(row.get('utm_campaign'))
    leading = re.match(r'^\s*(\d{1,4})\s*[-–]', name)
    sequence = re.search(r'\bC\d{1,3}\b', name, flags=re.IGNORECASE)
    prefix = leading.group(1) if leading else sequence.group(0).upper() if sequence else f'{index:02d}'
    return f'{prefix}/{utm}' if utm else prefix


def _roi_signal(value: Any) -> str:
    number = common.finite_float(value)
    return '⚪' if number is None else '🟢' if number >= 0 else '🔴'


def _delivery_signal(status: Any) -> str:
    return '🟢' if common.norm(status).upper() == 'ACTIVE' else '🔴'


def _campaign_action(decisions: list[dict[str, Any]], scaled: bool) -> tuple[str, str, str]:
    pause_count = sum(1 for row in decisions if row.get('action') == 'PAUSE_AD')
    reactivate_count = sum(1 for row in decisions if row.get('action') == 'REACTIVATE_AD')
    if pause_count:
        return '🛑', 'CORTAR', f'{pause_count} anúncio(s)'
    if reactivate_count:
        return '♻️', 'REATIVAR', f'{reactivate_count} anúncio(s)'
    if scaled:
        return '🚀', 'ESCALA +10%', 'recomendação; budget write gated'
    if decisions and all(row.get('action') == 'KEEP' for row in decisions):
        return '✅', 'MANTER', f'{len(decisions)} anúncio(s)'
    return '👁️', 'OBSERVAR', 'sem decisão executável'


def _append_table_pages(
    lines: list[str], title: str, header: str, separator: str,
    rows: list[str], page_size: int = 12,
) -> None:
    pages = [rows[index:index + page_size] for index in range(0, len(rows), page_size)] or [[]]
    total = len(pages)
    for index, page in enumerate(pages, start=1):
        label = f'{title} • {index}/{total}' if total > 1 else title
        lines.extend(['', f'**{label}**', '```text', header, separator, *page, '```'])


def _roi_percent(revenue: Any, investment: Any) -> float | None:
    revenue_value = common.finite_float(revenue)
    investment_value = common.finite_float(investment)
    if revenue_value is None or investment_value is None or investment_value <= 0:
        return None
    return (revenue_value - investment_value) * 100.0 / investment_value


def aggregate_economic_reporting(sb_bundle: dict[str, Any]) -> dict[str, Any]:
    """Aggregate report-only economics by exact Meta campaign ID + UTM."""
    if not sb_bundle.get('economic_ready'):
        return {
            'ready': False,
            'reason': sb_bundle.get('economic_reason') or 'economic_source_not_ready',
            'by_campaign_utm': {},
            'freshness': dict(sb_bundle.get('economic_freshness') or {}),
        }
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    utm_campaigns: dict[str, set[str]] = {}
    for source in sb_bundle.get('economic_performance_rows') or []:
        campaign_id = common.norm(source.get('CAMPAIGN_ID'))
        utm = reporting.normalize_utm_campaign(source.get('UTM_ADGROUP'))
        if not campaign_id or not utm:
            continue
        key = (campaign_id, utm)
        item = grouped.setdefault(key, {
            'campaign_id': campaign_id, 'utm_campaign': utm,
            'investment': 0.0, 'net_revenue': 0.0, 'estimated_revenue_direct': 0.0,
            'sessions': 0.0, 'gam_impressions': 0.0, 'source_rows': 0,
        })
        item['investment'] += common.finite_float(source.get('INVESTIMENT')) or 0.0
        item['net_revenue'] += common.finite_float(source.get('NET_REVENUE')) or 0.0
        item['estimated_revenue_direct'] += common.finite_float(source.get('REVENUE_ESTIMATED')) or 0.0
        item['sessions'] += common.finite_float(source.get('SESSIONS')) or 0.0
        item['gam_impressions'] += common.finite_float(source.get('GAM_IMPRESSIONS')) or 0.0
        item['source_rows'] += 1
        utm_campaigns.setdefault(utm, set()).add(campaign_id)
    estimated_by_utm = {
        reporting.normalize_utm_campaign(row.get('utm_adgroup')): row
        for row in ((sb_bundle.get('economic_estimated') or {}).get('grouped') or [])
        if reporting.normalize_utm_campaign(row.get('utm_adgroup'))
    }
    for (_, utm), item in grouped.items():
        estimate = estimated_by_utm.get(utm) if len(utm_campaigns.get(utm) or set()) == 1 else None
        estimated_revenue = common.finite_float((estimate or {}).get('estimatedRevenue'))
        if estimated_revenue is None and item['estimated_revenue_direct'] > 0:
            estimated_revenue = item['estimated_revenue_direct']
        item.update({
            'roi_real': _roi_percent(item['net_revenue'], item['investment']),
            'roi_estimated': _roi_percent(estimated_revenue, item['investment']),
            'rps': item['net_revenue'] * 1000.0 / item['sessions'] if item['sessions'] > 0 else None,
            'block_cpm': item['net_revenue'] * 1000.0 / item['gam_impressions'] if item['gam_impressions'] > 0 else None,
            'estimated_revenue': estimated_revenue,
            'estimate_confidence': common.finite_float((estimate or {}).get('confidence')),
            'estimated_join_status': 'matched' if estimate else ('ambiguous_utm' if len(utm_campaigns.get(utm) or set()) > 1 else 'estimate_missing'),
            'source_route': 'Smart Bidding /report/performance_per_campaigns + /estimated/revenue/utm_adgroup',
            'currency': 'USD',
        })
    return {
        'ready': True,
        'reason': None,
        'by_campaign_utm': grouped,
        'freshness': dict(sb_bundle.get('economic_freshness') or {}),
    }


def build_campaign_reporting(meta_bundle: dict[str, Any], sb_bundle: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Build reconciled campaign rows for the ROAS renderer without changing decisions."""
    meta = reporting.aggregate_meta(meta_bundle)
    sb = reporting.aggregate_sb(sb_bundle)
    merged = reporting.merge_campaign_sources(meta, sb)
    economics = aggregate_economic_reporting(sb_bundle)
    by_id = {common.norm(row.get('campaign_id')): dict(row) for row in merged.get('campaigns') or []}
    decisions_by_campaign: dict[str, list[dict[str, Any]]] = {}
    ordered_ids: list[str] = []
    for decision in plan.get('decisions') or []:
        campaign_id = common.norm(decision.get('campaign_id'))
        if not campaign_id:
            continue
        if campaign_id not in decisions_by_campaign:
            decisions_by_campaign[campaign_id] = []
            ordered_ids.append(campaign_id)
        decisions_by_campaign[campaign_id].append(decision)
    for merged_row in merged.get('campaigns') or []:
        campaign_id = common.norm(merged_row.get('campaign_id'))
        if campaign_id and campaign_id not in decisions_by_campaign:
            decisions_by_campaign[campaign_id] = []
            ordered_ids.append(campaign_id)
    scale_by_id = {
        common.norm(row.get('campaign_id')): row
        for row in plan.get('budget_scale_candidates') or []
        if common.norm(row.get('campaign_id'))
    }
    live_campaigns = {
        common.norm(row.get('id')): row
        for source in ('campaigns', 'tracked_campaigns', 'campaign_readbacks')
        for row in meta_bundle.get(source) or []
        if common.norm(row.get('id'))
    }
    identities = reporting.meta_campaign_identities(meta_bundle)
    rows: list[dict[str, Any]] = []
    for campaign_id in ordered_ids:
        decisions = decisions_by_campaign.get(campaign_id) or []
        row = dict(by_id.get(campaign_id) or {})
        live = live_campaigns.get(campaign_id) or {}
        if not row:
            spend = sum(common.finite_float(item.get('spend')) or 0.0 for item in decisions)
            purchase_value = sum(common.finite_float(item.get('purchase_value')) or 0.0 for item in decisions)
            impressions = sum(common.finite_float(item.get('impressions')) or 0.0 for item in decisions)
            link_clicks = sum(common.finite_float(item.get('link_clicks')) or 0.0 for item in decisions)
            results = sum(common.finite_float(item.get('messaging_results')) or 0.0 for item in decisions)
            started = sum(common.finite_float(item.get('messaging_started')) or 0.0 for item in decisions)
            weighted_ctr = sum((common.finite_float(item.get('ctr')) or 0.0) * (common.finite_float(item.get('impressions')) or 0.0) for item in decisions)
            row.update({
                'campaign_id': campaign_id,
                'name': common.norm(live.get('name')) or common.norm(decisions[0].get('campaign_name')) or campaign_id,
                'status': reporting.campaign_status(live),
                'budget_usd': reporting.campaign_budget_usd(live),
                'spend': spend,
                'messaging_results': results,
                'cost_per_message': spend / results if results > 0 else None,
                'messaging_started': started,
                'cost_per_messaging_started': spend / started if started > 0 else None,
                'link_clicks': link_clicks,
                'cpc_link': spend / link_clicks if link_clicks > 0 else None,
                'purchase_roas': purchase_value / spend if spend > 0 else None,
                'cpm': spend * 1000.0 / impressions if impressions > 0 else None,
                'ctr': weighted_ctr / impressions if impressions > 0 else None,
                'join_status': 'campaign_reporting_row_not_reconciled',
                **(identities.get(campaign_id) or {}),
            })
        economic = (economics.get('by_campaign_utm') or {}).get((campaign_id, reporting.normalize_utm_campaign(row.get('utm_campaign'))))
        emoji, action, action_detail = _campaign_action(decisions, campaign_id in scale_by_id)
        row.update({
            'action_emoji': emoji,
            'action_label': action,
            'action_detail': action_detail,
            'pause_ads': sum(1 for item in decisions if item.get('action') == 'PAUSE_AD'),
            'reactivate_ads': sum(1 for item in decisions if item.get('action') == 'REACTIVATE_AD'),
            'keep_ads': sum(1 for item in decisions if item.get('action') == 'KEEP'),
            'decision_reasons': sorted({common.norm(item.get('reason')) for item in decisions if common.norm(item.get('reason'))}),
            'roi_real': (economic or {}).get('roi_real'),
            'roi_estimated': (economic or {}).get('roi_estimated'),
            'block_cpm': (economic or {}).get('block_cpm'),
            'rps': (economic or {}).get('rps') if economic else row.get('pricing_rps'),
            'economic_join_status': 'matched' if economic else (economics.get('reason') or 'economic_campaign_utm_not_found'),
            'economic_source': (economic or {}).get('source_route'),
            'economic_freshness': dict(economics.get('freshness') or {}),
            'estimate_confidence': (economic or {}).get('estimate_confidence'),
            'scale': scale_by_id.get(campaign_id),
        })
        rows.append(row)
    return {
        'campaigns': rows,
        'campaign_count': len(rows),
        'source_join_matched': sum(1 for row in rows if row.get('join_status') == 'matched'),
        'economic_join_matched': sum(1 for row in rows if row.get('economic_join_status') == 'matched'),
        'leads_total': (sum(common.finite_float(row.get('sb_leads')) or 0.0 for row in rows) if any(common.finite_float(row.get('sb_leads')) is not None for row in rows) else None),
        'smart_bidding_freshness': dict(sb.get('freshness') or {}),
        'smart_bidding_reason': sb.get('reason'),
        'metric_notes': {
            'rps': 'RPS* report-only = Smart Bidding NET_REVENUE×1.000/SESSIONS.',
            'roi': 'ROI real* = (NET_REVENUE−INVESTIMENT)/INVESTIMENT; ROI est.* uses estimatedRevenue with the same denominator.',
            'block_cpm': 'CPM bloco* = Smart Bidding NET_REVENUE×1.000/GAM_IMPRESSIONS.',
        },
    }


def _dashboard_row(index: int, row: dict[str, Any]) -> str:
    action = {
        'ESCALA +10%': 'ESCALA',
        'REATIVAR': 'REATIVAR',
        'CORTAR': 'CORTAR',
        'MANTER': 'MANTER',
        'OBSERVAR': 'OBSERVAR',
    }.get(common.norm(row.get('action_label')), common.norm(row.get('action_label')) or 'N/D')
    values = [
        _fit(_roi_signal(row.get('roi_real')) + _roi_signal(row.get('roi_estimated')), 4),
        _fit(_delivery_signal(row.get('status')), 2),
        _fit(index, 2, 'right'),
        _fit(_campaign_key(row, index), 14),
        _fit(row.get('status'), 8),
        _fit(action, 8),
        _fit(common.fmt_number(row.get('cost_per_messaging_started')), 6, 'right'),
        _fit(common.fmt_number(row.get('purchase_roas')), 5, 'right'),
        _fit(common.fmt_number(row.get('cost_per_message')), 6, 'right'),
        _fit(common.fmt_number(row.get('messaging_results'), 0), 4, 'right'),
        _fit(common.fmt_number(row.get('budget_usd')), 7, 'right'),
        _fit(common.fmt_number(row.get('spend')), 7, 'right'),
        _fit(common.fmt_number(row.get('cpm')), 6, 'right'),
        _fit(_fmt_percent(row.get('ctr')), 6, 'right'),
        _fit(common.fmt_number(row.get('cpc_link')), 6, 'right'),
        '│',
        _fit(row.get('sb_page_id') or row.get('meta_page_id'), 15),
        _fit(row.get('sb_page_name'), 16),
        _fit(common.fmt_number(row.get('sb_cost_subscriber')), 7, 'right'),
        _fit(common.fmt_number(row.get('sb_revenue')), 8, 'right'),
        _fit(common.fmt_number(row.get('sb_profit')), 8, 'right'),
        _fit(_fmt_signed_percent(row.get('sb_roi_percent')), 8, 'right'),
        _fit(common.fmt_number(row.get('sb_leads'), 0), 6, 'right'),
        _fit(_fmt_signed_percent(row.get('sb_drip_roi_percent')), 9, 'right'),
        _fit(common.fmt_number(row.get('sb_broadcast_revenue')), 8, 'right'),
    ]
    return ' '.join(values)


def render_report(run: dict[str, Any]) -> str:
    source = run.get('source_gate') or {}
    plan = run.get('plan') or {}
    counts = plan.get('counts') or {}
    campaign_report = run.get('reporting') or {}
    campaigns = campaign_report.get('campaigns') or []
    reasons = source.get('reasons') or []
    started = _cycle_at(run.get('started_at_et'))
    date_label = started.strftime('%d/%m/%Y') if started else 'N/D'
    time_label = started.strftime('%H:%M') if started else 'N/D'
    mode = 'SIMULAÇÃO' if run.get('mode') == 'dry_run' else 'CONTROLLED WRITE'
    title_emoji = '⚠️' if reasons else '🛑' if counts.get('pause_ads') else '♻️' if counts.get('reactivate_ads') else '🚀' if counts.get('budget_scale_candidates') else '✅'
    lines = [
        f"## {title_emoji} CORTE & ROAS",
        f"**Eggbev US-CC-EN • {date_label} • {time_label} ET • {_phase_label(run.get('phase'))}**",
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
        f"`{mode}` • Threshold `{common.fmt_number(run.get('threshold'))}` • `USD`",
        '',
        f"**🎯 CICLO**  `{campaign_report.get('campaign_count', 0)} camp` • `{counts.get('ads_considered', 0)} ads` • "
        f"🛑 `{counts.get('pause_ads', 0)}` • ♻️ `{counts.get('reactivate_ads', 0)}` • "
        f"🚀 `{counts.get('budget_scale_candidates', 0)}` • ✅ `{sum(1 for row in plan.get('decisions') or [] if row.get('action') == 'KEEP')}`",
        f"**🛡️ FONTES**  Meta `{run.get('meta_status') or 'N/D'}` • SB `{run.get('smart_bidding_status') or 'N/D'}` • "
        f"Join `{campaign_report.get('source_join_matched', 0)}/{campaign_report.get('campaign_count', 0)}` • Econ `{campaign_report.get('economic_join_matched', 0)}/{campaign_report.get('campaign_count', 0)}`",
    ]
    if run.get('phase') == 'RESET':
        lines.append('🔄 Reset local do threshold; nenhuma leitura ou alteração Meta necessária.')
    elif reasons:
        lines.append('⚠️ **Ações bloqueadas:** ' + '; '.join(reasons))
    else:
        lines.append('✅ Fontes reconciliadas e regra nativa sem conflito.')

    if campaigns:
        dashboard_header = (
            'R/E  On  #  Camp/Pg        Delivery Ação      C/msg  ROAS  C/res  Res  Budget   Spend    CPM    CTR    CPC '
            '│ Page ID         Page               C/Sub      Rev   Profit     ROI%  Leads  ROI Drip   Rev BC'
        )
        dashboard_rows = [_dashboard_row(index, row) for index, row in enumerate(campaigns, start=1)]
        _append_table_pages(
            lines,
            '📊 PAINEL ÚNICO • Meta Ads + Smart Bidding',
            dashboard_header,
            '-' * len(dashboard_header),
            dashboard_rows,
            page_size=6,
        )
    else:
        lines.extend(['', 'ℹ️ Nenhuma campanha/anúncio entrou no ciclo.'])

    actionable = [row for row in plan.get('decisions') or [] if row.get('action') != 'KEEP']
    if actionable:
        lines.extend(['', '**🛑 CORTES E ♻️ REATIVAÇÕES POR ANÚNCIO**'])
        for row in actionable:
            emoji = '🛑' if row.get('action') == 'PAUSE_AD' else '♻️'
            lines.append(
                f"{emoji} **{row.get('ad_name') or row.get('ad_id')}** • Spend {common.fmt_money(row.get('spend'))} • "
                f"ROAS {common.fmt_number(row.get('purchase_roas'))} • `{row.get('reason')}`"
            )

    scale_candidates = plan.get('budget_scale_candidates') or []
    if scale_candidates:
        lines.extend(['', '**🚀 ESCALA DE BUDGET • recomendação**'])
        for row in scale_candidates:
            lines.append(
                f"🚀 **{row.get('campaign_name') or row.get('campaign_id')}** • ROAS {common.fmt_number(row.get('purchase_roas'))} • "
                f"{common.fmt_money(row.get('current_daily_budget_usd'))} → {common.fmt_money(row.get('target_daily_budget_usd'))} "
                f"(+{common.fmt_number(row.get('increase_percent'), 0)}%)"
            )
        lines.append('⚠️ Budget write permanece bloqueado até aprovação de Rodolfo/Geizian e teto/envelope.')

    writes = run.get('writes') or []
    if writes:
        confirmed = sum(1 for row in writes if row.get('ok'))
        lines.append(f"\n**✅ Readback de writes:** {confirmed}/{len(writes)} confirmados.")
    lines.extend([
        '',
        '**ℹ️ LEGENDA**',
        '`R/E` = sinais do ROI real/estimado • `On` = campanha ACTIVE • `Camp/Pg` = prefixo da campanha + UTM.',
        '`C/msg` = spend ÷ conversa iniciada • `C/res` = spend ÷ resultado • `CPC` = spend ÷ link click.',
        '`C/Sub*` = investimento ÷ SUBSCRIBED • `Profit*` = REVENUE − INVESTIMENT • `ROI%*` e `ROI Drip*` usam o mesmo investimento.',
        'Campos SB ficam `N/D` sem UTM + Page ID + freshness válidos. São informativos; Meta Purchase ROAS continua decidindo corte/reativação.',
    ])
    if run.get('phase') == 'RESET':
        lines.append('Reset diário: threshold voltou para 0,40; nenhum corte ou reativação Meta.')
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
                    run['delivery'] = common.post_to_thread(runtime.get('thread_id') or '1541578606076231750', report, '⚔️ Corte & ROAS')
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
            meta_bundle = reporting.enrich_campaign_readbacks(meta, token, meta_bundle)
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
                meta_bundle.get('campaigns') or [], plan.get('decisions') or [],
                common.finite_float(scale_policy.get('roas_threshold')) or 0.50,
                common.finite_float(scale_policy.get('increase_percent')) or 10.0,
            )
            plan['budget_scale_candidates'] = scale_candidates
            plan.setdefault('counts', {})['budget_scale_candidates'] = len(scale_candidates)
            gate = common.source_gate(meta_bundle, sb_bundle, phase)
            campaign_reporting = build_campaign_reporting(meta_bundle, sb_bundle, plan)
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
                    'economic_ready': sb_bundle.get('economic_ready'),
                    'economic_reason': sb_bundle.get('economic_reason'),
                    'economic_freshness': sb_bundle.get('economic_freshness'),
                    'economic_target_rows': len(sb_bundle.get('economic_performance_rows') or []),
                    'economic_http_statuses': sb_bundle.get('economic_http_statuses'),
                },
                'source_gate': gate, 'plan': plan, 'reporting': campaign_reporting,
            })
            common.atomic_json(audit_path, run)
            if args.apply and not gate.get('write_ready'):
                report = render_report(run)
                run['delivery'] = common.post_to_thread(runtime.get('thread_id') or '1541578606076231750', report, '⚔️ Corte & ROAS')
                raise RuntimeError('source/native-rule gate blocked controlled writes')
            if args.apply and phase in {'PHASE_1', 'PHASE_2'}:
                execute_plan(meta, token, plan, state, run)
                state['last_cycle'] = {'run_id': run_id, 'at_et': started.isoformat(), 'phase': phase}
                common.atomic_json(common.ROAS_STATE_PATH, state)
            report = render_report(run)
            if args.post_report:
                run['delivery'] = common.post_to_thread(runtime.get('thread_id') or '1541578606076231750', report, '⚔️ Corte & ROAS')
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
