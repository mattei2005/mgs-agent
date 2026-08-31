#!/usr/bin/env python3
"""Eggbev Daily and on-demand report runner.

Default is read-only stdout. Discord posting is separately gated in the live
operation contract and is disabled while no cron has been approved.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import statistics
import sys
import urllib.parse
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
ANOMALY_STATE_PATH = common.BASE / 'data/ares/meta-ads/state/eggbev/daily-revenue-baseline.json'


def parse_at(value: str | None) -> dt.datetime:
    if not value:
        return common.now_et()
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=common.ET)
    return parsed.astimezone(common.ET)


def report_dates(period: str, at: dt.datetime) -> list[tuple[str, str]]:
    if period == 'auto':
        if at.strftime('%H:%M') == '08:00':
            return [
                ((at.date() - dt.timedelta(days=1)).isoformat(), 'Fechamento D-1'),
                (at.date().isoformat(), 'Sinal atual 08:00'),
            ]
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


def roi_percent(revenue: Any, investment: Any) -> float | None:
    revenue_value = common.finite_float(revenue)
    investment_value = common.finite_float(investment)
    if revenue_value is None or investment_value is None or investment_value <= 0:
        return None
    return (revenue_value - investment_value) * 100.0 / investment_value


def campaign_status(row: dict[str, Any]) -> str:
    return common.norm(row.get('effective_status') or row.get('status') or row.get('configured_status')) or 'N/D'


def campaign_budget_usd(row: dict[str, Any]) -> float | None:
    minor = common.finite_float(row.get('daily_budget'))
    if minor is None:
        minor = common.finite_float(row.get('lifetime_budget'))
    return minor / 100.0 if minor is not None else None


def format_start_time(value: Any) -> str:
    raw = common.norm(value)
    if not raw:
        return 'N/D'
    try:
        parsed = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return 'N/D'
    if parsed.tzinfo is None:
        return 'N/D'
    return parsed.astimezone(common.ET).strftime('%d/%m %H:%M')


def format_percent(value: Any) -> str:
    number = common.finite_float(value)
    return 'N/D' if number is None else common.fmt_number(number) + '%'


def format_money_br(value: Any) -> str:
    number = common.finite_float(value)
    if number is None:
        return 'N/D'
    return '$' + f'{number:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def enrich_campaign_readbacks(meta, token: str, bundle: dict[str, Any]) -> dict[str, Any]:
    """Read back campaigns and ads needed for exact UTM/Page reconciliation."""
    enriched = dict(bundle)
    by_id: dict[str, dict[str, Any]] = {}
    for source in ('campaigns', 'tracked_campaigns'):
        for row in bundle.get(source) or []:
            campaign_id = common.norm(row.get('id'))
            if campaign_id:
                by_id[campaign_id] = row
    insight_ids = sorted({common.norm(row.get('campaign_id')) for row in bundle.get('insights') or [] if common.norm(row.get('campaign_id'))})
    errors: list[dict[str, Any]] = []
    fields = 'id,name,status,effective_status,configured_status,daily_budget,lifetime_budget,start_time,updated_time'
    for campaign_id in insight_ids:
        if campaign_id in by_id:
            continue
        status, row, _ = meta.graph_get(campaign_id, token, {'fields': fields})
        if status == 200 and isinstance(row, dict):
            by_id[campaign_id] = row
        else:
            errors.append({'campaign_id': campaign_id, 'http_status': status})
    enriched['campaign_readbacks'] = list(by_id.values())
    enriched['campaign_readback_errors'] = errors
    ad_by_id: dict[str, dict[str, Any]] = {}
    for source in ('ads', 'tracked_ads'):
        for row in bundle.get(source) or []:
            ad_id = common.norm(row.get('id'))
            if ad_id:
                ad_by_id[ad_id] = row
    insight_ad_ids = sorted({common.norm(row.get('ad_id')) for row in bundle.get('insights') or [] if common.norm(row.get('ad_id'))})
    ad_errors: list[dict[str, Any]] = []
    ad_fields = 'id,name,campaign{id,name},creative{id,url_tags,object_story_spec}'
    for ad_id in insight_ad_ids:
        if ad_id in ad_by_id:
            continue
        status, row, _ = meta.graph_get(ad_id, token, {'fields': ad_fields})
        if status == 200 and isinstance(row, dict):
            ad_by_id[ad_id] = row
        else:
            ad_errors.append({'ad_id': ad_id, 'http_status': status})
    enriched['ad_readbacks'] = list(ad_by_id.values())
    enriched['ad_readback_errors'] = ad_errors
    return enriched


PG_TOKEN = re.compile(r'(?i)(?:^|[^a-z0-9])(pg_\d+)(?:$|[^a-z0-9])')


def normalize_utm_campaign(value: Any) -> str:
    token = common.norm(value).lower()
    return token if re.fullmatch(r'pg_\d+', token) else ''


def utms_from_text(value: Any) -> set[str]:
    raw = common.norm(value)
    if not raw:
        return set()
    candidates: list[str] = []
    try:
        parsed = urllib.parse.urlparse(raw)
        query = parsed.query if parsed.query else raw.lstrip('?')
        candidates.extend(urllib.parse.parse_qs(query, keep_blank_values=True).get('utm_campaign') or [])
    except ValueError:
        pass
    candidates.extend(match.group(1) for match in PG_TOKEN.finditer(raw))
    return {token for value in candidates if (token := normalize_utm_campaign(value))}


def recursive_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from recursive_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_strings(item)


def meta_campaign_identities(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, set[str]]] = defaultdict(lambda: {'utms': set(), 'page_ids': set()})
    for ad in bundle.get('ad_readbacks') or bundle.get('ads') or []:
        campaign_id = common.norm((ad.get('campaign') or {}).get('id'))
        if not campaign_id:
            continue
        creative = ad.get('creative') or {}
        grouped[campaign_id]['utms'].update(utms_from_text(creative.get('url_tags')))
        story = creative.get('object_story_spec') or {}
        page_id = common.norm(story.get('page_id'))
        if page_id:
            grouped[campaign_id]['page_ids'].add(page_id)
        for raw in recursive_strings(story):
            grouped[campaign_id]['utms'].update(utms_from_text(raw))
    result: dict[str, dict[str, Any]] = {}
    for campaign_id, values in grouped.items():
        utms = sorted(values['utms'])
        page_ids = sorted(values['page_ids'])
        result[campaign_id] = {
            'utm_campaign': utms[0] if len(utms) == 1 else None,
            'meta_page_id': page_ids[0] if len(page_ids) == 1 else None,
            'utm_candidates': utms,
            'page_id_candidates': page_ids,
            'identity_issue': ('multiple_meta_utms' if len(utms) > 1 else 'multiple_meta_page_ids' if len(page_ids) > 1 else None),
            'utm_source': 'creative',
        }
    return result


def aggregate_meta(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get('insights') or []
    spends = sum(common.finite_float(row.get('spend')) or 0.0 for row in rows)
    impressions = sum(common.finite_float(row.get('impressions')) or 0.0 for row in rows)
    link_clicks = sum(common.finite_float(row.get('inline_link_clicks')) or 0.0 for row in rows)
    purchases_value = sum(common.action_value(row.get('action_values'), common.PURCHASE_ACTIONS) or 0.0 for row in rows)
    messaging_results = sum(common.action_value(row.get('actions'), common.MESSAGING_ACTIONS) or 0.0 for row in rows)
    messaging_started = sum(common.action_value(row.get('actions'), common.MESSAGING_STARTED_ACTIONS) or 0.0 for row in rows)
    roas = purchases_value / spends if spends > 0 else None
    cpm = spends * 1000.0 / impressions if impressions > 0 else None
    cpc_link = spends / link_clicks if link_clicks > 0 else None
    cost_per_message = spends / messaging_results if messaging_results > 0 else None
    cost_per_messaging_started = spends / messaging_started if messaging_started > 0 else None
    weighted_ctr_numerator = sum((common.finite_float(row.get('ctr')) or 0.0) * (common.finite_float(row.get('impressions')) or 0.0) for row in rows)
    ctr = weighted_ctr_numerator / impressions if impressions > 0 else None
    by_campaign: dict[str, dict[str, Any]] = defaultdict(lambda: {
        'name': '', 'spend': 0.0, 'purchase_value': 0.0, 'messaging_results': 0.0,
        'messaging_started': 0.0,
        'impressions': 0.0, 'link_clicks': 0.0, 'ctr_weighted': 0.0, 'has_insight': False,
    })
    for row in rows:
        campaign_id = common.norm(row.get('campaign_id')) or 'unknown'
        target = by_campaign[campaign_id]
        target['name'] = common.norm(row.get('campaign_name')) or target['name']
        target['spend'] += common.finite_float(row.get('spend')) or 0.0
        target['purchase_value'] += common.action_value(row.get('action_values'), common.PURCHASE_ACTIONS) or 0.0
        target['messaging_results'] += common.action_value(row.get('actions'), common.MESSAGING_ACTIONS) or 0.0
        target['messaging_started'] += common.action_value(row.get('actions'), common.MESSAGING_STARTED_ACTIONS) or 0.0
        row_impressions = common.finite_float(row.get('impressions')) or 0.0
        target['impressions'] += row_impressions
        target['link_clicks'] += common.finite_float(row.get('inline_link_clicks')) or 0.0
        target['ctr_weighted'] += (common.finite_float(row.get('ctr')) or 0.0) * row_impressions
        target['has_insight'] = True

    readbacks = bundle.get('campaign_readbacks')
    if readbacks is None:
        readbacks = list(bundle.get('campaigns') or []) + list(bundle.get('tracked_campaigns') or [])
    readback_by_id = {common.norm(row.get('id')): row for row in readbacks if common.norm(row.get('id'))}
    for campaign_id, row in readback_by_id.items():
        if campaign_status(row) == 'ACTIVE' and campaign_id not in by_campaign:
            by_campaign[campaign_id]['name'] = common.norm(row.get('name'))

    identities = meta_campaign_identities(bundle)
    campaigns = []
    for campaign_id, row in by_campaign.items():
        live = readback_by_id.get(campaign_id) or {}
        has_insight = bool(row['has_insight'])
        spend = row['spend'] if has_insight else None
        results = row['messaging_results'] if has_insight else None
        started = row['messaging_started'] if has_insight else None
        impressions_campaign = row['impressions'] if has_insight else None
        link_clicks_campaign = row['link_clicks'] if has_insight else None
        status = campaign_status(live)
        if has_insight and status == 'N/D':
            note = 'Entrega no período; status/budget não reconciliados'
        elif has_insight and status == 'ACTIVE':
            note = 'Entrega no período'
        elif has_insight:
            note = f'Entrega no período; estado atual {status}'
        else:
            note = 'ACTIVE sem linha de insight no período'
        identity = dict(identities.get(campaign_id) or {})
        if not identity.get('utm_campaign'):
            name_tokens = sorted({match.group(1).lower() for match in PG_TOKEN.finditer(common.norm(live.get('name')) or row['name'])})
            if len(name_tokens) == 1:
                identity['utm_campaign'] = name_tokens[0]
                identity['utm_source'] = 'campaign_name_fallback'
        campaigns.append({
            'campaign_id': campaign_id,
            'name': common.norm(live.get('name')) or row['name'] or campaign_id,
            'status': status,
            'start_time': live.get('start_time'),
            'budget_usd': campaign_budget_usd(live),
            'spend': spend,
            'purchase_roas': row['purchase_value'] / spend if spend is not None and spend > 0 else None,
            'messaging_results': results,
            'cost_per_message': spend / results if spend is not None and results is not None and results > 0 else None,
            'messaging_started': started,
            'cost_per_messaging_started': spend / started if spend is not None and started is not None and started > 0 else None,
            'impressions': impressions_campaign,
            'link_clicks': link_clicks_campaign,
            'cpm': spend * 1000.0 / impressions_campaign if spend is not None and impressions_campaign is not None and impressions_campaign > 0 else None,
            'ctr': row['ctr_weighted'] / impressions_campaign if impressions_campaign is not None and impressions_campaign > 0 else None,
            'cpc_link': spend / link_clicks_campaign if spend is not None and link_clicks_campaign is not None and link_clicks_campaign > 0 else None,
            'has_insight': has_insight,
            'note': note,
            **identity,
        })
    campaigns.sort(key=lambda row: (row['status'] != 'ACTIVE', -(row['spend'] or 0.0), row['name']))
    active_budget = sum(campaign_budget_usd(row) or 0.0 for row in readback_by_id.values() if campaign_status(row) == 'ACTIVE')
    return {
        'spend': spends, 'purchase_value': purchases_value, 'purchase_roas': roas,
        'messaging_results': messaging_results, 'cost_per_message': cost_per_message,
        'messaging_started': messaging_started, 'cost_per_messaging_started': cost_per_messaging_started,
        'impressions': impressions, 'link_clicks': link_clicks, 'cpm': cpm, 'ctr': ctr, 'cpc_link': cpc_link,
        'active_budget': active_budget,
        'campaigns': campaigns,
        'campaigns_in_scope': len(campaigns),
        'active_without_insight': sum(1 for row in campaigns if row['status'] == 'ACTIVE' and not row['has_insight']),
        'campaign_readback_errors': list(bundle.get('campaign_readback_errors') or []),
        'ad_readback_errors': list(bundle.get('ad_readback_errors') or []),
    }


def aggregate_sb(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get('target_report_rows') or []
    ready = bool(bundle.get('daily_reporting_ready', bundle.get('ready')))
    ready_reason = bundle.get('daily_reporting_reason', bundle.get('reason'))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        utm = normalize_utm_campaign(row.get('UTM_CAMPAIGN'))
        if utm:
            grouped[utm].append(row)
    page_index = bundle.get('page_index') or {}
    by_utm: dict[str, dict[str, Any]] = {}
    for utm, source_rows in sorted(grouped.items()):
        def total(key: str) -> float | None:
            values = [common.finite_float(row.get(key)) for row in source_rows]
            valid = [value for value in values if value is not None]
            return sum(valid) if valid else None
        investment = total('INVESTIMENT')
        revenue = total('REVENUE')
        drip_revenue = total('DRIP_REVENUE')
        broadcast_revenue = total('BD_REVENUE')
        subscribed = total('SUBSCRIBED')
        sessions = total('SESSIONS')
        acquisition_clicks = total('ACQUISITION_CLICKS')
        avg_values = [(common.finite_float(row.get('AVG_PRICE')), common.finite_float(row.get('SESSIONS'))) for row in source_rows]
        avg_pairs = [(value, weight or 0.0) for value, weight in avg_values if value is not None]
        avg_weight = sum(weight for _, weight in avg_pairs)
        avg_price = (sum(value * weight for value, weight in avg_pairs) / avg_weight if avg_weight > 0 else (sum(value for value, _ in avg_pairs) / len(avg_pairs) if avg_pairs else None))
        pages = list(page_index.get(utm) or page_index.get(utm.lower()) or [])
        page_ids = sorted({common.norm(row.get('FB_PAGE_ID')) for row in pages if common.norm(row.get('FB_PAGE_ID'))})
        raw_metrics = {
            'investment': investment,
            'revenue': revenue,
            'profit': revenue - investment if revenue is not None and investment is not None else None,
            'roi_percent': roi_percent(revenue, investment),
            'drip_revenue': drip_revenue,
            'drip_roi_percent': roi_percent(drip_revenue, investment),
            'broadcast_revenue': broadcast_revenue,
            'subscribed': subscribed,
            'cost_per_subscriber': investment / subscribed if investment is not None and subscribed and subscribed > 0 else None,
            'leads': total('LEADS'),
            'sessions': sessions,
            'acquisition_clicks': acquisition_clicks,
            'avg_price': avg_price,
            'rps_gross': revenue * 1000.0 / sessions if revenue is not None and sessions and sessions > 0 else None,
            'epc_gross': revenue / acquisition_clicks if revenue is not None and acquisition_clicks and acquisition_clicks > 0 else None,
        }
        by_utm[utm] = {
            'utm_campaign': utm,
            'report_row_count': len(source_rows),
            'page_row_count': len(pages),
            'sb_page_id': page_ids[0] if len(page_ids) == 1 else None,
            'page_name': common.norm(pages[0].get('PAGE_NAME')) if len(pages) == 1 else None,
            'page_mapping_issue': ('sb_page_missing' if not pages else 'sb_page_duplicate_or_ambiguous' if len(pages) != 1 or len(page_ids) != 1 else None),
            **({key: value for key, value in raw_metrics.items()} if ready else {key: None for key in raw_metrics}),
        }
    revenue_total = sum_field(rows, 'REVENUE') if ready else None
    sessions_total = sum_field(rows, 'SESSIONS') if ready else None
    clicks_total = sum_field(rows, 'ACQUISITION_CLICKS') if ready else None
    avg_pairs_global = [
        (common.finite_float(row.get('AVG_PRICE')), common.finite_float(row.get('SESSIONS')) or 0.0)
        for row in rows
        if common.finite_float(row.get('AVG_PRICE')) is not None
    ]
    avg_weight_global = sum(weight for _, weight in avg_pairs_global)
    avg_price_global = (
        sum(value * weight for value, weight in avg_pairs_global) / avg_weight_global
        if ready and avg_weight_global > 0
        else None
    )
    return {
        'ready': ready, 'reason': ready_reason, 'rows': len(rows),
        'investment': sum_field(rows, 'INVESTIMENT') if ready else None,
        'revenue': revenue_total,
        'profit': (revenue_total - sum_field(rows, 'INVESTIMENT')) if ready and revenue_total is not None else None,
        'roi_percent': roi_percent(revenue_total, sum_field(rows, 'INVESTIMENT')) if ready else None,
        'drip_revenue': sum_field(rows, 'DRIP_REVENUE') if ready else None,
        'drip_roi_percent': roi_percent(sum_field(rows, 'DRIP_REVENUE'), sum_field(rows, 'INVESTIMENT')) if ready else None,
        'broadcast_revenue': sum_field(rows, 'BD_REVENUE') if ready else None,
        'subscribed': sum_field(rows, 'SUBSCRIBED') if ready else None,
        'cost_per_subscriber': (sum_field(rows, 'INVESTIMENT') / sum_field(rows, 'SUBSCRIBED')) if ready and sum_field(rows, 'SUBSCRIBED') > 0 else None,
        'leads': sum_field(rows, 'LEADS') if ready else None,
        'leads_total': sum_field(rows, 'LEADS_TOTAL') if ready else None,
        'avg_price': avg_price_global,
        'rps_gross': revenue_total * 1000.0 / sessions_total if revenue_total is not None and sessions_total and sessions_total > 0 else None,
        'epc_gross': revenue_total / clicks_total if revenue_total is not None and clicks_total and clicks_total > 0 else None,
        'available_account_names': bundle.get('available_account_names'),
        'freshness': dict(bundle.get('freshness') or {}),
        'by_utm': by_utm,
        'roi_real': None, 'roi_estimated': None,
        'formula_note': 'ROI real/estimado N/D. Pricing: RPS bruto = REVENUE×1.000/SESSIONS; EPC bruto = REVENUE/ACQUISITION_CLICKS.',
    }


def aggregate_campaign_economics(bundle: dict[str, Any], report_date: str, current_date: str) -> dict[str, Any]:
    """Build fresh Smart Bidding economics by exact campaign ID + UTM."""
    freshness = dict(bundle.get('economic_freshness') or {})
    if not bundle.get('economic_ready'):
        return {
            'ready': False,
            'reason': bundle.get('economic_reason') or 'economic_source_not_ready',
            'by_campaign_utm': {},
            'freshness': freshness,
        }
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    utm_campaigns: dict[str, set[str]] = defaultdict(set)
    for source in bundle.get('economic_performance_rows') or []:
        campaign_id = common.norm(source.get('CAMPAIGN_ID'))
        utm = normalize_utm_campaign(source.get('UTM_ADGROUP'))
        if not campaign_id or not utm:
            continue
        key = (campaign_id, utm)
        item = grouped.setdefault(key, {
            'campaign_id': campaign_id,
            'utm_campaign': utm,
            'investment': 0.0,
            'net_revenue': 0.0,
            'estimated_revenue_direct': 0.0,
            'has_investment': False,
            'has_net_revenue': False,
            'has_estimated_revenue_direct': False,
            'source_rows': 0,
        })
        investment = common.finite_float(source.get('INVESTIMENT'))
        net_revenue = common.finite_float(source.get('NET_REVENUE'))
        estimated_direct = common.finite_float(source.get('REVENUE_ESTIMATED'))
        if investment is not None:
            item['investment'] += investment
            item['has_investment'] = True
        if net_revenue is not None:
            item['net_revenue'] += net_revenue
            item['has_net_revenue'] = True
        if estimated_direct is not None:
            item['estimated_revenue_direct'] += estimated_direct
            item['has_estimated_revenue_direct'] = True
        item['source_rows'] += 1
        utm_campaigns[utm].add(campaign_id)

    estimated_by_utm = {
        normalize_utm_campaign(row.get('utm_adgroup')): row
        for row in ((bundle.get('economic_estimated') or {}).get('grouped') or [])
        if normalize_utm_campaign(row.get('utm_adgroup'))
    }
    for (_, utm), item in grouped.items():
        # The live estimate endpoint is current-state only. Historical reports use
        # the date-scoped REVENUE_ESTIMATED field from performance_per_campaigns.
        estimate = (
            estimated_by_utm.get(utm)
            if report_date == current_date and len(utm_campaigns.get(utm) or set()) == 1
            else None
        )
        estimated_revenue = common.finite_float((estimate or {}).get('estimatedRevenue'))
        estimate_source = 'estimated/revenue/utm_adgroup'
        if estimated_revenue is None and item['has_estimated_revenue_direct']:
            estimated_revenue = item['estimated_revenue_direct']
            estimate_source = 'performance_per_campaigns.REVENUE_ESTIMATED'
        investment = item['investment'] if item['has_investment'] else None
        net_revenue = item['net_revenue'] if item['has_net_revenue'] else None
        item.update({
            'roi_real': roi_percent(net_revenue, investment),
            'roi_estimated': roi_percent(estimated_revenue, investment),
            'estimated_revenue': estimated_revenue,
            'estimate_confidence': common.finite_float((estimate or {}).get('confidence')),
            'estimate_source': estimate_source if estimated_revenue is not None else None,
            'source_route': 'Smart Bidding /report/performance_per_campaigns + /estimated/revenue/utm_adgroup',
            'currency': 'USD',
        })
    return {
        'ready': True,
        'reason': None,
        'by_campaign_utm': grouped,
        'freshness': freshness,
    }


def merge_campaign_economics(meta: dict[str, Any], economics: dict[str, Any]) -> dict[str, Any]:
    merged = dict(meta)
    campaigns: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    by_key = economics.get('by_campaign_utm') or {}
    for source in meta.get('campaigns') or []:
        row = dict(source)
        campaign_id = common.norm(row.get('campaign_id'))
        utm = normalize_utm_campaign(row.get('utm_campaign'))
        economic = by_key.get((campaign_id, utm)) if campaign_id and utm else None
        if not economics.get('ready'):
            status = common.norm(economics.get('reason')) or 'economic_source_not_ready'
        elif not campaign_id:
            status = 'campaign_id_missing'
        elif not utm:
            status = 'economic_utm_missing'
        elif not economic:
            status = 'economic_campaign_utm_not_found'
        else:
            status = 'matched'
        row.update({
            'roi_real': (economic or {}).get('roi_real'),
            'roi_estimated': (economic or {}).get('roi_estimated'),
            'economic_join_status': status,
            'economic_source': (economic or {}).get('source_route'),
            'estimated_revenue_source': (economic or {}).get('estimate_source'),
            'estimate_confidence': (economic or {}).get('estimate_confidence'),
        })
        counts[status] += 1
        campaigns.append(row)
    merged['campaigns'] = campaigns
    merged['economic_join_counts'] = dict(sorted(counts.items()))
    merged['economic_join_matched'] = counts.get('matched', 0)
    merged['economic_freshness'] = dict(economics.get('freshness') or {})
    return merged


def merge_campaign_sources(meta: dict[str, Any], sb: dict[str, Any]) -> dict[str, Any]:
    merged = dict(meta)
    campaigns: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    for source in meta.get('campaigns') or []:
        row = dict(source)
        utm = normalize_utm_campaign(row.get('utm_campaign'))
        sb_row = (sb.get('by_utm') or {}).get(utm) if utm else None
        status = 'matched'
        if row.get('identity_issue'):
            status = common.norm(row.get('identity_issue'))
        elif not utm:
            status = 'meta_utm_missing'
        elif not sb_row:
            status = 'sb_utm_not_found'
        elif sb_row.get('page_mapping_issue'):
            status = common.norm(sb_row.get('page_mapping_issue'))
        elif not row.get('meta_page_id'):
            status = 'meta_page_id_missing'
        elif common.norm(row.get('meta_page_id')) != common.norm(sb_row.get('sb_page_id')):
            status = 'meta_sb_page_id_mismatch'
        elif not sb.get('ready'):
            status = common.norm(sb.get('reason')) or 'smart_bidding_not_ready'
        external: dict[str, Any] = sb_row if status == 'matched' and isinstance(sb_row, dict) else {}
        row.update({
            'join_status': status,
            'sb_page_id': (sb_row or {}).get('sb_page_id') if isinstance(sb_row, dict) else None,
            'sb_page_name': (sb_row or {}).get('page_name') if isinstance(sb_row, dict) else None,
            'sb_investment': external.get('investment'),
            'sb_revenue': external.get('revenue'),
            'sb_profit': external.get('profit'),
            'sb_roi_percent': external.get('roi_percent'),
            'sb_drip_revenue': external.get('drip_revenue'),
            'sb_drip_roi_percent': external.get('drip_roi_percent'),
            'sb_broadcast_revenue': external.get('broadcast_revenue'),
            'sb_subscribed': external.get('subscribed'),
            'sb_cost_subscriber': external.get('cost_per_subscriber'),
            'sb_leads': external.get('leads'),
            'pricing_avg': external.get('avg_price'),
            'pricing_rps': external.get('rps_gross'),
            'pricing_epc': external.get('epc_gross'),
        })
        counts[status] += 1
        campaigns.append(row)
    merged['campaigns'] = campaigns
    merged['source_join_counts'] = dict(sorted(counts.items()))
    merged['source_join_matched'] = counts.get('matched', 0)
    return merged


def apply_period_campaign_scope(meta: dict[str, Any], label: str) -> dict[str, Any]:
    """D-1 shows campaigns that actually produced an insight row in D-1."""
    scoped = dict(meta)
    campaigns = list(meta.get('campaigns') or [])
    if label not in {'Fechamento D-1', 'Fechamento anterior'}:
        return scoped
    excluded = [row for row in campaigns if not row.get('has_insight')]
    campaigns = [row for row in campaigns if row.get('has_insight')]
    counts: dict[str, int] = defaultdict(int)
    for row in campaigns:
        counts[common.norm(row.get('join_status')) or 'N/D'] += 1
    scoped['campaigns'] = campaigns
    scoped['campaigns_in_scope'] = len(campaigns)
    scoped['active_without_insight'] = 0
    scoped['active_without_d1_insight_excluded'] = len(excluded)
    scoped['source_join_counts'] = dict(sorted(counts.items()))
    scoped['source_join_matched'] = counts.get('matched', 0)
    return scoped


def prepare_daily_sb_bundle(bundle: dict[str, Any], report_date: str) -> dict[str, Any]:
    """Apply Daily-only date and freshness gates without changing ROAS writes."""
    prepared = dict(bundle)
    rows = [
        row for row in bundle.get('target_report_rows') or []
        if common.norm(row.get('DATE'))[:10] == report_date
    ]
    prepared['target_report_rows'] = rows
    legacy_ready = bool(bundle.get('ready'))
    delay = dict(bundle.get('economic_freshness') or {})
    delay_ready = delay.get('ready') is True
    prepared['daily_reporting_ready'] = bool(rows) and (legacy_ready or delay_ready)
    if not rows:
        prepared['daily_reporting_reason'] = 'target_account_absent_for_exact_report_date'
    elif prepared['daily_reporting_ready']:
        prepared['daily_reporting_reason'] = None
    else:
        prepared['daily_reporting_reason'] = (
            common.norm(bundle.get('reason'))
            or common.norm(bundle.get('economic_reason'))
            or 'smart_bidding_freshness_unverifiable'
        )
    if delay_ready and not legacy_ready:
        prepared['freshness'] = {
            'ready': True,
            'reason': None,
            'latest_at_et': delay.get('current_fill_time'),
            'age_minutes': delay.get('age_minutes'),
            'max_age_hours': 2.0,
            'timestamp_field': 'estimated.delay.currentFillTime',
            'evidence': delay.get('evidence'),
        }
    return prepared


def default_anomaly_state() -> dict[str, Any]:
    return {
        'schema_version': 1,
        'operation_id': 'Eggbev-US-CC-EN-BOT',
        'snapshots': [],
    }


def load_anomaly_state(path: Path = ANOMALY_STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return default_anomaly_state()
    try:
        payload = common.load_json(path)
    except Exception:
        return default_anomaly_state()
    if not isinstance(payload, dict) or not isinstance(payload.get('snapshots'), list):
        return default_anomaly_state()
    return payload


def snapshot_kind(label: str) -> tuple[str | None, str | None]:
    if label == 'Fechamento D-1' or label == 'Fechamento anterior':
        return 'closed_day', '23:59'
    if label == 'Sinal atual 08:00':
        return 'same_clock', '08:00'
    return None, None


def build_revenue_snapshot(
    sb: dict[str, Any], report_date: str, label: str, observed_at_et: str,
) -> dict[str, Any]:
    kind, cutoff = snapshot_kind(label)
    if kind is None:
        return {'eligible': False, 'reason': 'period_not_anomaly_comparable'}
    if not sb.get('ready'):
        return {
            'eligible': False,
            'date': report_date,
            'kind': kind,
            'cutoff': cutoff,
            'reason': common.norm(sb.get('reason')) or 'smart_bidding_not_ready',
        }
    pages: list[dict[str, Any]] = []
    coverage_issues: list[dict[str, str]] = []
    for utm, row in sorted((sb.get('by_utm') or {}).items()):
        issue = common.norm(row.get('page_mapping_issue'))
        revenue = common.finite_float(row.get('revenue'))
        if issue or revenue is None:
            coverage_issues.append({
                'utm_campaign': utm,
                'reason': issue or 'revenue_missing',
            })
            continue
        pages.append({
            'utm_campaign': utm,
            'page_id': common.norm(row.get('sb_page_id')) or None,
            'page_name': common.norm(row.get('page_name')) or None,
            'revenue': revenue,
            'broadcast_revenue': common.finite_float(row.get('broadcast_revenue')),
            'drip_revenue': common.finite_float(row.get('drip_revenue')),
            'leads': common.finite_float(row.get('leads')),
        })
    if not pages:
        return {
            'eligible': False,
            'date': report_date,
            'kind': kind,
            'cutoff': cutoff,
            'reason': 'no_reconciled_page_revenue_rows',
            'coverage_issues': coverage_issues,
        }
    return {
        'eligible': True,
        'date': report_date,
        'kind': kind,
        'cutoff': cutoff,
        'observed_at_et': observed_at_et,
        'pages': pages,
        'coverage_issues': coverage_issues,
    }


def anomaly_page_key(row: dict[str, Any]) -> str:
    return common.norm(row.get('page_id')) or common.norm(row.get('utm_campaign')).lower()


def analyze_revenue_snapshot(
    snapshot: dict[str, Any], state: dict[str, Any], policy: dict[str, Any],
) -> dict[str, Any]:
    if not snapshot.get('eligible'):
        reason = snapshot.get('reason')
        if reason == 'period_not_anomaly_comparable':
            return {
                'status': 'not_comparable_window',
                'reason': reason,
                'alerts': [],
                'coverage_issues': snapshot.get('coverage_issues') or [],
            }
        return {
            'status': 'source_unavailable',
            'reason': reason,
            'alerts': [],
            'coverage_issues': snapshot.get('coverage_issues') or [],
        }
    window = int(policy.get('baseline_days') or 7)
    minimum = int(policy.get('minimum_comparable_samples') or 3)
    warning = common.finite_float(policy.get('warning_drop_percent')) or 30.0
    critical = common.finite_float(policy.get('critical_drop_percent')) or 40.0
    history = [
        row for row in state.get('snapshots') or []
        if row.get('eligible')
        and row.get('kind') == snapshot.get('kind')
        and row.get('cutoff') == snapshot.get('cutoff')
        and common.norm(row.get('date')) < common.norm(snapshot.get('date'))
    ]
    history.sort(key=lambda row: common.norm(row.get('date')), reverse=True)
    history = history[:window]
    samples_by_page: dict[str, list[float]] = defaultdict(list)
    for historical in history:
        for page in historical.get('pages') or []:
            value = common.finite_float(page.get('revenue'))
            key = anomaly_page_key(page)
            if key and value is not None:
                samples_by_page[key].append(value)
    alerts: list[dict[str, Any]] = []
    insufficient = 0
    for page in snapshot.get('pages') or []:
        key = anomaly_page_key(page)
        samples = samples_by_page.get(key, [])[:window]
        current = common.finite_float(page.get('revenue'))
        if current is None or len(samples) < minimum:
            insufficient += 1
            continue
        baseline = statistics.median(samples)
        if baseline <= 0:
            insufficient += 1
            continue
        drop = (baseline - current) * 100.0 / baseline
        severity = 'critical' if drop >= critical else 'warning' if drop >= warning else 'ok'
        if severity != 'ok':
            alerts.append({
                'severity': severity,
                'utm_campaign': page.get('utm_campaign'),
                'page_name': page.get('page_name'),
                'current_revenue': current,
                'baseline_median_revenue': baseline,
                'drop_percent': drop,
                'sample_count': len(samples),
                'comparison': f"{snapshot.get('kind')}@{snapshot.get('cutoff')}",
            })
    alerts.sort(key=lambda row: (row.get('severity') != 'critical', -(row.get('drop_percent') or 0.0)))
    return {
        'status': 'alert' if alerts else 'baseline_forming' if insufficient else 'ok',
        'alerts': alerts,
        'pages_evaluated': len(snapshot.get('pages') or []),
        'pages_without_baseline': insufficient,
        'history_snapshots': len(history),
        'minimum_comparable_samples': minimum,
        'coverage_issues': snapshot.get('coverage_issues') or [],
    }


def upsert_anomaly_snapshot(
    state: dict[str, Any], snapshot: dict[str, Any], observed_at_et: str,
    retention_days: int = 45,
) -> dict[str, Any]:
    updated = dict(state)
    snapshots = [dict(row) for row in state.get('snapshots') or []]
    if snapshot.get('eligible'):
        key = (snapshot.get('date'), snapshot.get('kind'), snapshot.get('cutoff'))
        snapshots = [
            row for row in snapshots
            if (row.get('date'), row.get('kind'), row.get('cutoff')) != key
        ]
        snapshots.append(dict(snapshot))
    snapshots.sort(key=lambda row: (common.norm(row.get('date')), common.norm(row.get('kind')), common.norm(row.get('cutoff'))))
    if snapshots:
        latest = dt.date.fromisoformat(max(common.norm(row.get('date')) for row in snapshots))
        floor = latest - dt.timedelta(days=retention_days)
        snapshots = [row for row in snapshots if dt.date.fromisoformat(common.norm(row.get('date'))) >= floor]
    updated['snapshots'] = snapshots
    updated['updated_at_et'] = observed_at_et
    return updated


def anomaly_bullets(analysis: dict[str, Any], maximum: int = 5) -> list[str]:
    if analysis.get('status') == 'not_comparable_window':
        return [
            '⚪ Monitor de anomalia não aplicado nesta parcial. Comparações válidas usam D-1 fechado ou o snapshot exato das 08:00 contra snapshots anteriores de 08:00.'
        ]
    if analysis.get('status') == 'source_unavailable':
        return [
            '⚪ Monitor de receita sem leitura confiável: '
            + (common.norm(analysis.get('reason')) or 'fonte indisponível')
            + '. A ausência do sinal é tratada como alerta de cobertura, não como receita zero.'
        ]
    bullets: list[str] = []
    for alert in analysis.get('alerts') or []:
        icon = '🔴' if alert.get('severity') == 'critical' else '🟠'
        page = common.norm(alert.get('page_name')) or common.norm(alert.get('utm_campaign')) or 'página N/D'
        bullets.append(
            f"{icon} {page} ({alert.get('utm_campaign') or 'UTM N/D'}): receita {common.fmt_money(alert.get('current_revenue'))} "
            f"vs mediana {common.fmt_money(alert.get('baseline_median_revenue'))} "
            f"({alert.get('drop_percent'):.1f}% abaixo; n={alert.get('sample_count')}). "
            'Verificar disparo, bloco/funil e entrega da página com o responsável.'
        )
    if not bullets and analysis.get('status') == 'baseline_forming':
        bullets.append(
            f"⚪ Baseline de receita em formação: {analysis.get('history_snapshots', 0)}/"
            f"{analysis.get('minimum_comparable_samples', 3)} snapshots comparáveis; nenhuma queda é inferida antes do mínimo."
        )
    if analysis.get('coverage_issues'):
        bullets.append(f"⚪ {len(analysis.get('coverage_issues') or [])} página(s) sem join/fonte suficiente; revisar cobertura antes de concluir performance.")
    return bullets[:maximum]


def operational_alert_bullets(period: dict[str, Any]) -> list[str]:
    campaigns = (period.get('meta') or {}).get('campaigns') or []
    bullets: list[str] = []
    names: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for campaign in campaigns:
        names[common.norm(campaign.get('name'))].append(campaign)
    for name, rows in sorted(names.items()):
        if name and len(rows) > 1:
            bullets.append(
                f"🟠 Nome duplicado: {len(rows)} campanhas distintas aparecem como `{name}`. "
                'Confirmar a origem antes de clonar.'
            )
    for campaign in campaigns:
        name = common.norm(campaign.get('name'))
        name_utm_match = re.search(r'\((pg_\d+)\)', name, flags=re.I)
        actual_utm = common.norm(campaign.get('utm_campaign'))
        if name_utm_match and actual_utm and name_utm_match.group(1).lower() != actual_utm.lower():
            bullets.append(
                f"🟠 Naming/UTM divergente: `{name}` indica `{name_utm_match.group(1)}`, "
                f"mas o criativo ativo reconcilia com `{actual_utm}`/{common.norm(campaign.get('sb_page_name')) or 'página N/D'}. "
                'Não usar como fonte de clone sem conferência.'
            )
    return bullets


def aligned_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    widths = [max(len(headers[index]), *(len(row[index]) for row in rows)) for index in range(len(headers))]

    def line(values: list[str]) -> str:
        return '  '.join(value.ljust(widths[index]) for index, value in enumerate(values)).rstrip()

    return [line(headers), line(['─' * width for width in widths]), *[line(row) for row in rows]]


def compact_campaign_key(name: Any, fallback: Any = None) -> str:
    text = common.norm(name)
    sequence = re.match(r'^\s*(\d+)', text)
    campaign = re.search(r'\bC(\d+)\b', text, flags=re.I)
    duplicate = re.search(r'\bDUP(\d+)\b', text, flags=re.I)
    parts: list[str] = []
    if sequence:
        parts.append(sequence.group(1))
    if campaign:
        parts.append(f"C{int(campaign.group(1)):03d}")
    if duplicate:
        parts.append(f"D{int(duplicate.group(1)):02d}")
    return '·'.join(parts) or text or common.norm(fallback) or 'N/D'


def source_alias(name: Any, campaign_id: Any) -> str:
    """Stable human alias for carrying a Daily row to Clone preflight."""
    compact = compact_campaign_key(name, campaign_id).replace('·', '-')
    identity = common.norm(campaign_id) or common.norm(name) or compact
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:4].upper()
    return f'SRC-{compact}-{digest}'


def campaign_name_page(value: Any) -> str:
    match = re.match(r'^\s*\d+\s*-\s*(.*?)\s*-\s*(?:ENG|EN)\b', common.norm(value), flags=re.I)
    return common.norm(match.group(1)) if match else ''


def annotate_campaign_display_identities(meta: dict[str, Any]) -> dict[str, Any]:
    """Persist report-only source aliases and visible tracking integrity signals."""
    annotated = dict(meta)
    campaigns = [dict(row) for row in meta.get('campaigns') or []]
    name_counts: dict[str, int] = defaultdict(int)
    for row in campaigns:
        name_counts[common.norm(row.get('name')).casefold()] += 1
    counts: dict[str, int] = defaultdict(int)
    for row in campaigns:
        name = common.norm(row.get('name'))
        actual_utm = common.norm(row.get('utm_campaign')).lower()
        name_match = re.search(r'\((pg_\d+)\)', name, flags=re.I)
        name_utm = name_match.group(1).lower() if name_match else ''
        expected_page = campaign_name_page(name)
        actual_page = common.norm(row.get('sb_page_name'))
        reasons: list[str] = []
        if name and name_counts[name.casefold()] > 1:
            reasons.append('duplicate_name')
        if name_utm and actual_utm and name_utm != actual_utm:
            reasons.append('name_utm_mismatch')
        if expected_page and actual_page and expected_page.casefold() != actual_page.casefold():
            reasons.append('name_page_mismatch')
        join_status = common.norm(row.get('join_status'))
        if join_status and join_status != 'matched':
            reasons.append(join_status)
        if any(reason in {'duplicate_name', 'name_utm_mismatch', 'name_page_mismatch'} for reason in reasons):
            signal = '⚠️'
            category = 'warning'
        elif reasons or not actual_utm or not actual_page:
            signal = '🟡'
            category = 'review'
        else:
            signal = '🧬'
            category = 'reconciled'
        row['source_alias'] = source_alias(name, row.get('campaign_id'))
        row['identity_signal'] = signal
        row['identity_reasons'] = sorted(set(reasons))
        counts[category] += 1
    annotated['campaigns'] = campaigns
    annotated['identity_signal_counts'] = dict(sorted(counts.items()))
    return annotated


def roi_marker(value: Any) -> str:
    number = common.finite_float(value)
    if number is None:
        return '⚪'
    if number >= 0:
        return '🟢'
    if number > -15:
        return '🟡'
    return '🔴'


def format_roi_cell(value: Any) -> str:
    number = common.finite_float(value)
    if number is None:
        return '⚪N/D'
    return f'{roi_marker(number)}{common.fmt_number(number, 1)}%'


def reconciliation_signal(meta_spend: Any, sb_investment: Any) -> tuple[str, float | None]:
    meta_value = common.finite_float(meta_spend)
    sb_value = common.finite_float(sb_investment)
    if meta_value is None or sb_value is None or meta_value <= 0:
        return '⚪', None
    score = max(0.0, 100.0 - abs(sb_value - meta_value) * 100.0 / meta_value)
    return ('✅' if score >= 98 else '🟡' if score >= 95 else '🔴'), score


def compact_page_label(row: dict[str, Any]) -> str:
    page = common.norm(row.get('sb_page_name'))
    first_name = page.split()[0] if page else ''
    utm = common.norm(row.get('utm_campaign'))
    utm_short = utm.removeprefix('pg_') if utm else ''
    if first_name and utm_short:
        return f'{first_name}/{utm_short}'
    return page or utm or 'N/D'


def build_page_summary(
    campaigns: list[dict[str, Any]], current_dashboard: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    sb_fields = (
        'sb_investment', 'sb_revenue', 'sb_broadcast_revenue', 'sb_drip_revenue',
        'sb_roi_percent', 'sb_leads', 'pricing_avg', 'pricing_rps', 'pricing_epc',
    )
    for campaign in campaigns:
        utm = common.norm(campaign.get('utm_campaign')).lower()
        key = utm or common.norm(campaign.get('sb_page_name')).lower() or common.norm(campaign.get('campaign_id'))
        group = groups.setdefault(key, {
            'utm_campaign': common.norm(campaign.get('utm_campaign')),
            'page_name': common.norm(campaign.get('sb_page_name')),
            'campaigns': 0,
            'delivered': 0,
            'spend': 0.0,
            'messaging_started': 0.0,
            'roas_value': 0.0,
            'roas_spend': 0.0,
            **{field: None for field in sb_fields},
        })
        group['campaigns'] += 1
        spend = common.finite_float(campaign.get('spend'))
        messaging = common.finite_float(campaign.get('messaging_started'))
        roas = common.finite_float(campaign.get('purchase_roas'))
        if campaign.get('has_insight') or spend is not None:
            group['delivered'] += 1
        if spend is not None:
            group['spend'] += spend
            if roas is not None:
                group['roas_value'] += spend * roas
                group['roas_spend'] += spend
        if messaging is not None:
            group['messaging_started'] += messaging
        for field in sb_fields:
            value = common.finite_float(campaign.get(field))
            if group.get(field) is None and value is not None:
                group[field] = value
    summaries: list[dict[str, Any]] = []
    for group in groups.values():
        spend = group['spend']
        messaging = group['messaging_started']
        group['purchase_roas'] = group['roas_value'] / group['roas_spend'] if group['roas_spend'] > 0 else None
        group['cost_per_messaging_started'] = spend / messaging if messaging > 0 else None
        group['page_label'] = (
            f"{group.get('page_name')} · {group.get('utm_campaign')}"
            if group.get('page_name') and group.get('utm_campaign')
            else group.get('page_name') or group.get('utm_campaign') or 'N/D'
        )
        current_row = ((current_dashboard or {}).get('by_utm') or {}).get(
            common.norm(group.get('utm_campaign')).lower()
        )
        group['sb_broadcast_current'] = (
            common.finite_float((current_row or {}).get('broadcast_revenue'))
            if (current_dashboard or {}).get('ready') and isinstance(current_row, dict)
            else None
        )
        summaries.append(group)
    named = [row for row in summaries if common.norm(row.get('page_name'))]
    unnamed = [row for row in summaries if not common.norm(row.get('page_name'))]
    named.sort(
        key=lambda row: (
            common.norm(row.get('page_name')).casefold(),
            common.norm(row.get('utm_campaign')).casefold(),
        ),
        reverse=True,
    )
    unnamed.sort(key=lambda row: common.norm(row.get('utm_campaign')).casefold())
    return [*named, *unnamed]


def render_page_meta_table(pages: list[dict[str, Any]]) -> list[str]:
    rows = [[
        common.norm(page.get('page_label')), str(page.get('campaigns') or 0), str(page.get('delivered') or 0),
        common.fmt_money(page.get('spend')), common.fmt_number(page.get('purchase_roas')),
        common.fmt_money(page.get('cost_per_messaging_started')),
    ] for page in pages]
    return aligned_table(['Página / UTM', 'Camp', 'Entr.', 'Spend', 'ROAS', 'C/msg'], rows)


def render_page_economics_table(pages: list[dict[str, Any]]) -> list[str]:
    rows = [[
        common.norm(page.get('page_label')), common.fmt_money(page.get('sb_investment')),
        common.fmt_money(page.get('sb_revenue')), common.fmt_money(page.get('sb_broadcast_revenue')),
        common.fmt_money(page.get('sb_drip_revenue')), format_percent(page.get('sb_roi_percent')),
        common.fmt_number(page.get('sb_leads'), 0), common.fmt_money(page.get('pricing_rps')),
        common.fmt_money(page.get('pricing_epc')),
    ] for page in pages]
    return aligned_table(['Página / UTM', 'SB Inv', 'Receita', 'BC', 'Drip', 'ROI', 'Leads', 'RPS', 'EPC'], rows)


def render_campaign_table(campaigns: list[dict[str, Any]]) -> list[str]:
    rows: list[list[str]] = []
    for index, row in enumerate(campaigns, start=1):
        if not (row.get('has_insight') or common.finite_float(row.get('spend')) is not None):
            continue
        rows.append([
            str(index), compact_campaign_key(row.get('name'), row.get('campaign_id')), compact_page_label(row),
            common.norm(row.get('status')) or 'N/D', common.fmt_money(row.get('budget_usd')),
            common.fmt_money(row.get('spend')), common.fmt_number(row.get('purchase_roas')),
            common.fmt_money(row.get('cost_per_messaging_started')),
            common.fmt_number(row.get('messaging_started'), 0), common.fmt_money(row.get('cpm')),
            format_percent(row.get('ctr')),
        ])
    return aligned_table(['#', 'Camp', 'Página', 'St', 'Budget', 'Spend', 'ROAS', 'C/msg', 'Msg', 'CPM', 'CTR'], rows)


def render_no_delivery_table(campaigns: list[dict[str, Any]]) -> list[str]:
    rows: list[list[str]] = []
    for index, row in enumerate(campaigns, start=1):
        if row.get('has_insight') or common.finite_float(row.get('spend')) is not None:
            continue
        rows.append([
            str(index), compact_campaign_key(row.get('name'), row.get('campaign_id')), compact_page_label(row),
            format_start_time(row.get('start_time')), common.fmt_money(row.get('budget_usd')),
            common.norm(row.get('status')) or 'N/D',
        ])
    return aligned_table(['#', 'Camp', 'Página', 'Início', 'Budget', 'St'], rows)


def status_label(value: Any) -> str:
    return {
        'ACTIVE': 'ATIVA',
        'PAUSED': 'PAUSADA',
        'ARCHIVED': 'ARQUIV.',
        'DELETED': 'EXCLUÍDA',
    }.get(common.norm(value).upper(), common.norm(value) or 'N/D')


def render_grouped_page_tables(
    pages: list[dict[str, Any]], campaigns: list[dict[str, Any]],
) -> list[str]:
    """Render one short decision block per Page with clone-source aliases."""
    indexed: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for original_index, campaign in enumerate(campaigns, start=1):
        utm = common.norm(campaign.get('utm_campaign')).lower()
        key = utm or common.norm(campaign.get('sb_page_name')).lower() or common.norm(campaign.get('campaign_id'))
        indexed[key].append((original_index, campaign))

    lines: list[str] = []
    headers = ['ID', 'Fonte', 'Ent.', 'St', 'Budget', 'Spend', 'Msg', '$/Msg', 'ROAS', 'ROI real', 'ROI est.', 'CPM', 'CTR']
    for page in pages:
        key = common.norm(page.get('utm_campaign')).lower() or common.norm(page.get('page_name')).lower()
        page_campaigns = sorted(
            indexed.get(key) or [],
            key=lambda item: (
                compact_campaign_key(item[1].get('name'), item[1].get('campaign_id')).casefold(),
                common.norm(item[1].get('campaign_id')),
            ),
        )
        label = common.norm(page.get('page_label')) or 'Página N/D'
        count = len(page_campaigns)
        noun = 'campanha' if count == 1 else 'campanhas'
        identity_ok = sum(1 for _, row in page_campaigns if common.norm(row.get('identity_signal')) == '🧬')
        lines.extend([
            '', f"{roi_marker(page.get('sb_roi_percent'))} **{label}** · {count} {noun} · {page.get('delivered') or 0}● · 🧬 {identity_ok}/{count}",
            f"`💵 {format_money_br(page.get('spend'))} · 💬 {common.fmt_number(page.get('messaging_started'), 0)}/{format_money_br(page.get('cost_per_messaging_started'))} · ROAS {common.fmt_number(page.get('purchase_roas'))} │ 🧾 {format_money_br(page.get('sb_investment'))}→{format_money_br(page.get('sb_revenue'))} · ROI* {format_roi_cell(page.get('sb_roi_percent'))} · 💧 {format_money_br(page.get('sb_drip_revenue'))} · 📣 {format_money_br(page.get('sb_broadcast_current'))}`",
        ])
        rows: list[list[str]] = []
        for _, row in page_campaigns:
            delivered = bool(row.get('has_insight') or common.finite_float(row.get('spend')) is not None)
            rows.append([
                common.norm(row.get('identity_signal')) or '🟡',
                common.norm(row.get('source_alias')) or source_alias(row.get('name'), row.get('campaign_id')),
                '●' if delivered else '○', status_label(row.get('status')),
                format_money_br(row.get('budget_usd')), format_money_br(row.get('spend')),
                common.fmt_number(row.get('messaging_started'), 0), format_money_br(row.get('cost_per_messaging_started')),
                common.fmt_number(row.get('purchase_roas')), format_roi_cell(row.get('roi_real')),
                format_roi_cell(row.get('roi_estimated')), format_money_br(row.get('cpm')), format_percent(row.get('ctr')),
            ])
        chunks = [rows[offset:offset + 10] for offset in range(0, len(rows), 10)] or [[]]
        for chunk_index, chunk in enumerate(chunks, start=1):
            if len(chunks) > 1:
                lines.append(f"**Tabela da página • {chunk_index}/{len(chunks)}**")
            lines.extend(['```text', *aligned_table(headers, chunk), '```'])
    return lines


def render_period(period: dict[str, Any]) -> list[str]:
    meta = period['meta']
    sb = period['smart_bidding']
    current_dashboard = period.get('current_dashboard') or {}
    current_freshness = current_dashboard.get('freshness') or {}
    reconciliation_icon, reconciliation = reconciliation_signal(meta.get('spend'), sb.get('investment'))
    reconciliation_text = 'N/D' if reconciliation is None else common.fmt_number(reconciliation) + '%'
    lines = [
        f"**{period['label']} · {period['date']}**",
        f"{reconciliation_icon} Meta×SB {reconciliation_text} · 💵 Meta {format_money_br(meta.get('spend'))} · 🧾 SB {format_money_br(sb.get('investment'))} · 💰 Receita {format_money_br(sb.get('revenue'))}",
        f"💬 {common.fmt_number(meta.get('messaging_started'), 0)} Msg · {format_money_br(meta.get('cost_per_messaging_started'))}/msg · 💧 Drip {format_money_br(sb.get('drip_revenue'))} · 📣 BC agora {format_money_br(current_dashboard.get('broadcast_revenue'))}",
        f"⏱ SB {((str((sb.get('freshness') or {}).get('age_minutes')) + ' min') if (sb.get('freshness') or {}).get('age_minutes') is not None else 'N/D')} · Dash {((str(current_freshness.get('age_minutes')) + ' min') if current_freshness.get('age_minutes') is not None else 'N/D')} · campo {common.norm((sb.get('freshness') or {}).get('timestamp_field')) or 'N/D'} · máx. 2h",
    ]
    if not sb.get('ready'):
        lines.append('⚠️ Smart Bidding não reconciliada: ' + common.norm(sb.get('reason')) + '.')
    campaigns = meta.get('campaigns') or []
    if campaigns:
        pages = build_page_summary(campaigns, current_dashboard)
        lines.extend([
            '', '**📊 Visão unificada · Página → fonte de clone**',
            *render_grouped_page_tables(pages, campaigns),
        ])
        lines.append('🧬 identidade conciliada · 🟡 revisar cobertura · ⚠️ conflito de nome/UTM/Página. `Fonte` é o alias para levar à thread Clonar Campanhas; todo clone ainda exige preflight.')
        lines.append('`Msg` = messaging_conversation_started_7d. `ROI real/est.` = Smart Bidding por campanha+UTM exatas; `ROI pág.*` permanece no nível Página/UTM.')
        lines.append(f"Conciliação Meta×SB×Pricing: {meta.get('source_join_matched', 0)}/{len(campaigns)} campanhas com UTM + Page ID + freshness válidos.")
        lines.append(f"Conciliação ROI campanha×UTM: {meta.get('economic_join_matched', 0)}/{len(campaigns)} com fonte econômica fresca e match exato.")
        if meta.get('active_without_d1_insight_excluded'):
            lines.append(f"ℹ️ ACTIVE atuais sem insight em D-1: {meta.get('active_without_d1_insight_excluded')}; fora da tabela D-1 porque não rodaram no período fechado.")
        if meta.get('active_without_insight'):
            lines.append(f"ℹ️ ACTIVE sem insight no período: {meta.get('active_without_insight')}; campanhas mantidas visíveis com métricas `N/D`.")
        if meta.get('campaign_readback_errors'):
            lines.append(f"⚠️ Status/budget não reconciliados para {len(meta.get('campaign_readback_errors') or [])} campanha(s) com insight.")
        if meta.get('ad_readback_errors'):
            lines.append(f"⚠️ Criativo/UTM/Page ID não relidos para {len(meta.get('ad_readback_errors') or [])} anúncio(s).")
    else:
        lines.append('Nenhuma campanha ACTIVE e nenhuma campanha com insight Meta no período.')
    return lines


def render_report(run: dict[str, Any]) -> str:
    lines = [
        '📊 **Eggbev-US-CC-EN — Diário**',
        f"Gerado: {run.get('started_at_et')} | Conta: Eggbev-US-CC-EN-01-G006 | Moeda: USD",
        'Fontes: Meta Ads API + Smart Bidding Messenger + Pricing/monetização reconciliados por UTM e Page ID',
        '',
    ]
    rendered_periods = [
        period for period in run.get('periods') or []
        if period.get('label') != 'Sinal atual 08:00'
    ]
    for index, period in enumerate(rendered_periods):
        if index:
            lines.append('\n──────────')
        lines.extend(render_period(period))
    alerts: list[str] = []
    for period in run.get('periods') or []:
        label = period.get('label')
        if label == 'Sinal atual 08:00':
            prefix = 'Hoje 08:00 — '
        elif label in {'Fechamento D-1', 'Fechamento anterior'}:
            prefix = 'D-1 — '
        else:
            prefix = f"{common.norm(label) or 'Período'} — "
        for bullet in anomaly_bullets(period.get('revenue_anomaly') or {}):
            alerts.append(prefix + bullet)
        alerts.extend(operational_alert_bullets(period))
    if alerts:
        lines.extend(['', '**Fique de olho**', *[f'- {bullet}' for bullet in alerts[:5]]])
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--period', default='auto', help='auto, today, yesterday or YYYY-MM-DD')
    parser.add_argument('--post', action='store_true', help='post to fixed Daily thread when runtime is enabled')
    parser.add_argument('--at', help='read-only ISO timestamp for deterministic auto-period selection')
    parser.add_argument('--no-baseline-write', action='store_true', help='do not persist local revenue baseline snapshots')
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
    daily_policy = operation.get('daily_reporting_policy') or {}
    runtime = daily_policy.get('runtime') or {}
    anomaly_policy = daily_policy.get('revenue_anomaly_detection') or {}
    threshold_policy = (operation.get('roas_cycle_policy') or {}).get('threshold') or {}
    state, _ = common.load_state(at.date(), common.finite_float(threshold_policy.get('daily_reset_value')) or 0.40)
    anomaly_state = load_anomaly_state()
    anomaly_snapshots_written = 0
    run: dict[str, Any] = {
        'ok': False, 'mode': 'read_only', 'run_id': run_id, 'started_at_et': at.isoformat(),
        'period_request': args.period, 'periods': [], 'writes_attempted': 0,
        'anomaly_state_path': str(ANOMALY_STATE_PATH),
        'anomaly_snapshots_written': 0,
        'audit_path': str(audit_path),
    }
    common.atomic_json(audit_path, run)
    try:
        if args.post and not runtime.get('post_enabled'):
            raise RuntimeError(runtime.get('blocked_reason') or 'Daily posting disabled')
        meta, sb, token, credential = common.load_runtime_modules(account)
        run['credential_readback'] = credential
        account_id = common.norm((operation.get('account') or {}).get('account_id'))
        current_date = at.date().isoformat()
        sb_cache: dict[str, dict[str, Any]] = {}
        try:
            current_bundle = common.fetch_sb_bundle(sb, operation, current_date)
        except Exception as exc:
            current_bundle = {
                'ready': False, 'reason': f'{type(exc).__name__}: {exc}',
                'target_report_rows': [], 'available_account_names': [],
            }
        current_bundle = prepare_daily_sb_bundle(current_bundle, current_date)
        sb_cache[current_date] = current_bundle
        current_dashboard = aggregate_sb(current_bundle)
        current_dashboard['date'] = current_date
        current_dashboard['source_route'] = '/report/messenger BD_REVENUE'
        run['current_dashboard_readback'] = {
            'date': current_date,
            'source_route': current_dashboard['source_route'],
            'ready': current_dashboard.get('ready'),
            'broadcast_revenue': current_dashboard.get('broadcast_revenue'),
            'page_rows': len(current_dashboard.get('by_utm') or {}),
            'freshness': current_dashboard.get('freshness'),
        }
        for report_date, label in report_dates(args.period, at):
            meta_bundle = common.fetch_meta_bundle(meta, token, account_id, state, report_date)
            meta_bundle = enrich_campaign_readbacks(meta, token, meta_bundle)
            if report_date in sb_cache:
                sb_bundle = sb_cache[report_date]
            else:
                try:
                    sb_bundle = common.fetch_sb_bundle(sb, operation, report_date)
                except Exception as exc:
                    sb_bundle = {'ready': False, 'reason': f'{type(exc).__name__}: {exc}', 'target_report_rows': [], 'available_account_names': []}
                sb_bundle = prepare_daily_sb_bundle(sb_bundle, report_date)
                sb_cache[report_date] = sb_bundle
            meta_aggregate = aggregate_meta(meta_bundle)
            sb_aggregate = aggregate_sb(sb_bundle)
            meta_aggregate = merge_campaign_sources(meta_aggregate, sb_aggregate)
            meta_aggregate = apply_period_campaign_scope(meta_aggregate, label)
            economics = aggregate_campaign_economics(sb_bundle, report_date, current_date)
            meta_aggregate = merge_campaign_economics(meta_aggregate, economics)
            meta_aggregate = annotate_campaign_display_identities(meta_aggregate)
            snapshot = build_revenue_snapshot(sb_aggregate, report_date, label, at.isoformat())
            anomaly = analyze_revenue_snapshot(snapshot, anomaly_state, anomaly_policy)
            if snapshot.get('eligible'):
                anomaly_state = upsert_anomaly_snapshot(
                    anomaly_state,
                    snapshot,
                    at.isoformat(),
                    int(anomaly_policy.get('retention_days') or 45),
                )
                anomaly_snapshots_written += 1
            run['periods'].append({
                'date': report_date, 'label': label,
                'meta': meta_aggregate,
                'smart_bidding': sb_aggregate,
                'current_dashboard': current_dashboard,
                'revenue_anomaly': anomaly,
                'readback': {
                    'meta_insight_rows': len(meta_bundle.get('insights') or []),
                    'meta_campaign_readbacks': len(meta_bundle.get('campaign_readbacks') or []),
                    'meta_campaign_readback_errors': len(meta_bundle.get('campaign_readback_errors') or []),
                    'meta_ad_readbacks': len(meta_bundle.get('ad_readbacks') or []),
                    'meta_ad_readback_errors': len(meta_bundle.get('ad_readback_errors') or []),
                    'smart_bidding_target_rows': len(sb_bundle.get('target_report_rows') or []),
                    'smart_bidding_available_accounts': sb_bundle.get('available_account_names'),
                    'source_join_counts': meta_aggregate.get('source_join_counts'),
                    'economic_join_counts': meta_aggregate.get('economic_join_counts'),
                    'economic_freshness': meta_aggregate.get('economic_freshness'),
                },
            })
            common.atomic_json(audit_path, run)
        if anomaly_snapshots_written and not args.no_baseline_write:
            common.atomic_json(ANOMALY_STATE_PATH, anomaly_state)
        run['anomaly_snapshots_written'] = 0 if args.no_baseline_write else anomaly_snapshots_written
        run['anomaly_snapshots_observed'] = anomaly_snapshots_written
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
