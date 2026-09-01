#!/usr/bin/env python3
"""One-time Eggbev reactivation for every eligible campaign with 2026-08-31 spend."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path('/root/mgs-agent')
if str(BASE / 'scripts') not in sys.path:
    sys.path.insert(0, str(BASE / 'scripts'))
from ares_campaign_v3.eggbev_page_eligibility import PageEligibilityError, load_denylist, page_eligibility

COMMON_PATH = BASE / 'scripts/ares-eggbev-roas-common.py'
AUDIT_DIR = BASE / 'data/ares/meta-ads/audit/eggbev/one-time-reactivation'
STATE_PATH = BASE / 'data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/reactivate-created-for-20260831.json'
LOCK_PATH = BASE / 'data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/reactivate-created-for-20260831.lock'
SOURCE_DATE = '2026-08-31'
EXPECTED_EXECUTION_DATE = '2026-09-01'
EXPECTED_START = dt.time(0, 12)
EXPECTED_END = dt.time(0, 28)
ACCOUNT_ID = '1034081997659047'



def load_common():
    import importlib.util
    spec = importlib.util.spec_from_file_location('eggbev_one_time_common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('runtime comum indisponível')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, 'r+')


def acquire_with_timeout(handle, seconds: int = 45) -> None:
    deadline = time.monotonic() + seconds
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise RuntimeError('lock da operação ocupado')
            time.sleep(1)


def exact_status(row: dict[str, Any]) -> str:
    return str(row.get('configured_status') or row.get('status') or '').strip().upper()


def graph_get_required(meta, token: str, object_id: str, fields: str) -> dict[str, Any]:
    status, body, _ = meta.graph_get(object_id, token, {'fields': fields})
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError('readback Meta incompleto')
    return body


def campaign_insights(common, meta, token: str) -> dict[str, dict[str, Any]]:
    rows = common.fetch_all_meta(meta, token, f'act_{ACCOUNT_ID}/insights', {
        'level': 'campaign',
        'fields': 'campaign_id,campaign_name,spend,impressions',
        'time_range': json.dumps({'since': SOURCE_DATE, 'until': SOURCE_DATE}),
        'limit': 500,
    })
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        campaign_id = str(row.get('campaign_id') or '')
        spend = common.finite_float(row.get('spend')) or 0.0
        if not campaign_id or spend <= 0:
            continue
        if campaign_id in result:
            raise RuntimeError('insights de campanha duplicados no dia-base')
        result[campaign_id] = {
            'campaign_id': campaign_id,
            'campaign_name': row.get('campaign_name'),
            'spend_usd': round(spend, 2),
            'impressions': int(common.finite_float(row.get('impressions')) or 0),
        }
    if not result:
        raise RuntimeError('nenhuma campanha com gasto no dia-base')
    return result


def non_deleted(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if exact_status(row) not in {'DELETED', 'ARCHIVED'}]


def collect_scope(common, meta, token: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    account = graph_get_required(meta, token, f'act_{ACCOUNT_ID}', 'id,name,account_status,currency,timezone_name')
    if int(account.get('account_status') or 0) != 1 or account.get('currency') != 'USD' or account.get('timezone_name') != 'America/New_York':
        raise RuntimeError('identidade da conta não confere')
    insights = campaign_insights(common, meta, token)
    account_campaigns = common.fetch_all_meta(meta, token, f'act_{ACCOUNT_ID}/campaigns', {
        'fields': 'id,name,status,effective_status,configured_status,start_time,daily_budget,updated_time',
        'filtering': json.dumps([{'field': 'id', 'operator': 'IN', 'value': sorted(insights)}]),
        'limit': 100,
    })
    campaigns_by_id = {str(row.get('id') or ''): row for row in account_campaigns if row.get('id')}
    missing_campaign_ids = sorted(set(insights) - set(campaigns_by_id))
    for campaign_id in missing_campaign_ids:
        campaigns_by_id[campaign_id] = graph_get_required(
            meta, token, campaign_id,
            'id,name,status,effective_status,configured_status,start_time,daily_budget,updated_time',
        )
    live_campaigns: dict[str, dict[str, Any]] = {}
    excluded: list[dict[str, Any]] = []
    for campaign_id in sorted(insights):
        campaign = campaigns_by_id[campaign_id]
        status = exact_status(campaign)
        if status in {'DELETED', 'ARCHIVED'}:
            excluded.append({
                'campaign_id': campaign_id,
                'campaign_name': campaign.get('name') or insights[campaign_id].get('campaign_name'),
                'spend_usd': insights[campaign_id]['spend_usd'],
                'reason': f'campaign_{status.lower()}',
            })
            continue
        live_campaigns[campaign_id] = campaign
    account_adsets = common.fetch_all_meta(meta, token, f'act_{ACCOUNT_ID}/adsets', {
        'fields': 'id,name,status,effective_status,configured_status,campaign_id,updated_time',
        'filtering': json.dumps([{'field': 'campaign.id', 'operator': 'IN', 'value': sorted(live_campaigns)}]),
        'limit': 100,
    })
    account_ads = common.fetch_all_meta(meta, token, f'act_{ACCOUNT_ID}/ads', {
        'fields': 'id,name,status,effective_status,configured_status,adset_id,campaign_id,updated_time,creative{id,object_story_spec,url_tags}',
        'filtering': json.dumps([{'field': 'campaign.id', 'operator': 'IN', 'value': sorted(live_campaigns)}]),
        'limit': 100,
    })
    adsets_by_campaign: dict[str, list[dict[str, Any]]] = {}
    ads_by_campaign: dict[str, list[dict[str, Any]]] = {}
    for row in account_adsets:
        campaign_id = str(row.get('campaign_id') or '')
        if campaign_id in live_campaigns:
            adsets_by_campaign.setdefault(campaign_id, []).append(row)
    for row in account_ads:
        campaign_id = str(row.get('campaign_id') or '')
        if campaign_id in live_campaigns:
            ads_by_campaign.setdefault(campaign_id, []).append(row)
    denylist = load_denylist()
    scope: list[dict[str, Any]] = []
    for campaign_id, campaign in sorted(live_campaigns.items()):
        adsets = non_deleted([row for row in adsets_by_campaign.get(campaign_id, []) if isinstance(row, dict)])
        ads = non_deleted([row for row in ads_by_campaign.get(campaign_id, []) if isinstance(row, dict)])
        if not adsets or not ads:
            raise RuntimeError('campanha com gasto sem hierarquia elegível')
        adset_ids = {str(row.get('id') or '') for row in adsets}
        if '' in adset_ids or any(str(ad.get('adset_id') or '') not in adset_ids for ad in ads):
            raise RuntimeError('vínculo anúncio-conjunto divergente')
        page_ids = {
            str(((ad.get('creative') or {}).get('object_story_spec') or {}).get('page_id') or '')
            for ad in ads
        }
        page_ids.discard('')
        if len(page_ids) != 1:
            raise RuntimeError('identidade da Page nos anúncios é ausente ou ambígua')
        try:
            eligibility = page_eligibility(
                campaign.get('name'),
                meta_page_id=next(iter(page_ids)),
                denylist=denylist,
            )
        except PageEligibilityError as exc:
            eligibility = {'eligible': False, 'reason': 'page_eligibility_unverifiable', 'detail': str(exc)}
        if not eligibility.get('eligible'):
            excluded.append({
                'campaign_id': campaign_id,
                'campaign_name': campaign.get('name'),
                'spend_usd': insights[campaign_id]['spend_usd'],
                'page_token': eligibility.get('page_token'),
                'page_name': eligibility.get('page_name'),
                'current_restricted_until': eligibility.get('current_restricted_until'),
                'reason': eligibility.get('reason'),
            })
            continue
        scope.append({
            'campaign': campaign,
            'adsets': adsets,
            'ads': ads,
            'insight': insights[campaign_id],
            'meta_page_id': next(iter(page_ids)),
            'page_eligibility': eligibility,
        })
    if not scope or len(scope) + len(excluded) != len(insights):
        raise RuntimeError('contagem do escopo de gasto não reconciliou')
    return scope, excluded


def reconcile_status(common, meta, token: str, object_id: str, preflight: dict[str, Any] | None = None) -> dict[str, Any]:
    if preflight is not None and exact_status(preflight) == 'ACTIVE':
        return {
            'object_id': object_id,
            'ok': True,
            'stage': 'preflight_already_active',
            'before': {'status': 'ACTIVE'},
            'after': {'status': 'ACTIVE'},
            'meta_write': False,
        }
    result = common.reconcile_status_write(meta, token, object_id, 'ACTIVE')
    if result.get('ok'):
        return result
    current = graph_get_required(meta, token, object_id, 'id,name,status,effective_status,configured_status,updated_time')
    if exact_status(current) == 'ACTIVE':
        result.update({'ok': True, 'stage': 'recovered_by_readback'})
        return result
    retry = common.reconcile_status_write(meta, token, object_id, 'ACTIVE')
    retry['retry_after_readback'] = True
    return retry


def final_readback(common, meta, token: str, scope: list[dict[str, Any]]) -> dict[str, Any]:
    target_ids = {
        'campaigns': {str(item['campaign']['id']) for item in scope},
        'adsets': {str(row['id']) for item in scope for row in item['adsets']},
        'ads': {str(row['id']) for item in scope for row in item['ads']},
    }
    target_campaign_ids = sorted(target_ids['campaigns'])
    rows_by_kind = {
        'campaigns': common.fetch_all_meta(meta, token, f'act_{ACCOUNT_ID}/campaigns', {
            'fields': 'id,status,effective_status,configured_status,updated_time',
            'filtering': json.dumps([{'field': 'id', 'operator': 'IN', 'value': target_campaign_ids}]),
            'limit': 100,
        }),
        'adsets': common.fetch_all_meta(meta, token, f'act_{ACCOUNT_ID}/adsets', {
            'fields': 'id,status,effective_status,configured_status,updated_time',
            'filtering': json.dumps([{'field': 'campaign.id', 'operator': 'IN', 'value': target_campaign_ids}]),
            'limit': 100,
        }),
        'ads': common.fetch_all_meta(meta, token, f'act_{ACCOUNT_ID}/ads', {
            'fields': 'id,status,effective_status,configured_status,updated_time',
            'filtering': json.dumps([{'field': 'campaign.id', 'operator': 'IN', 'value': target_campaign_ids}]),
            'limit': 100,
        }),
    }
    counts = {'campaigns': 0, 'adsets': 0, 'ads': 0}
    failures: list[dict[str, str]] = []
    for kind in ('campaigns', 'adsets', 'ads'):
        live_map = {str(row.get('id') or ''): row for row in rows_by_kind[kind] if row.get('id')}
        for object_id in sorted(target_ids[kind]):
            live = live_map.get(object_id)
            if live is None:
                live = graph_get_required(meta, token, object_id, 'id,status,effective_status,configured_status,updated_time')
            if exact_status(live) == 'ACTIVE':
                counts[kind] += 1
            else:
                failures.append({'kind': kind, 'object_id': object_id, 'status': exact_status(live)})
    return {'ok': not failures, 'counts': counts, 'failures': failures}


def clear_roas_provenance(common, target_ad_ids: set[str], audit: dict[str, Any]) -> None:
    try:
        state = common.load_json(common.ROAS_STATE_PATH)
    except Exception:
        state = common.default_state(common.now_et().date())
    paused = state.get('paused_ads') if isinstance(state.get('paused_ads'), dict) else {}
    removed = sorted(ad_id for ad_id in target_ad_ids if ad_id in paused)
    for ad_id in removed:
        paused.pop(ad_id, None)
    state['paused_ads'] = paused
    state['last_manual_reconciliation'] = {
        'request_id': 'eggbev-reactivate-created-for-20260831-nicolas-01',
        'at_et': common.now_et().isoformat(),
        'scope': 'all_non_archived_campaigns_with_spend_on_2026-08-31_excluding_restricted_pages',
        'removed_paused_ad_provenance_count': len(removed),
    }
    common.atomic_json(common.ROAS_STATE_PATH, state)
    audit['roas_provenance_reconciliation'] = {'removed_count': len(removed)}


def summarize_dry_run(scope: list[dict[str, Any]], exclusions: list[dict[str, Any]]) -> str:
    eligible_spend = sum(float(item['insight']['spend_usd']) for item in scope)
    restricted = [row for row in exclusions if row.get('reason') in {'restricted_page_history', 'page_eligibility_unverifiable'}]
    archived = [row for row in exclusions if row.get('reason') in {'campaign_archived', 'campaign_deleted'}]
    statuses = {
        'campaigns_active': sum(exact_status(item['campaign']) == 'ACTIVE' for item in scope),
        'adsets_active': sum(exact_status(row) == 'ACTIVE' for item in scope for row in item['adsets']),
        'ads_active': sum(exact_status(row) == 'ACTIVE' for item in scope for row in item['ads']),
    }
    return json.dumps({
        'status': 'DRY_RUN_OK',
        'source_date_et': SOURCE_DATE,
        'campaigns_with_spend_total': len(scope) + len(exclusions),
        'eligible_campaigns': len(scope),
        'eligible_adsets': sum(len(item['adsets']) for item in scope),
        'eligible_ads': sum(len(item['ads']) for item in scope),
        'eligible_spend_usd': round(eligible_spend, 2),
        'all_spend_usd': round(eligible_spend + sum(float(row.get('spend_usd') or 0) for row in exclusions), 2),
        **statuses,
        'budget_writes': 0,
        'excluded_restricted_campaigns': len(restricted),
        'excluded_restricted_pages': sorted({str(row['page_token']) for row in restricted if row.get('page_token')}),
        'excluded_archived_or_deleted_campaigns': len(archived),
    }, ensure_ascii=False, indent=2)


def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    common = load_common()
    started = common.now_et()
    run_id = started.strftime('eggbev-reactivate-created-for-20260831-%Y%m%dT%H%M%S%z')
    audit_path = AUDIT_DIR / f'{run_id}.json'
    audit: dict[str, Any] = {
        'request_id': 'eggbev-reactivate-created-for-20260831-nicolas-01',
        'authorized_by': 'Nicolas Holanda',
        'authorization_scope': 'reactivate every non-archived Eggbev campaign with spend on 2026-08-31 and all non-deleted ad sets/ads; exclude every restricted Page; no budget write',
        'scope_selector': 'Meta campaign-level Insights spend > 0 on 2026-08-31',
        'source_date_et': SOURCE_DATE,
        'started_at_et': started.isoformat(),
        'mode': 'dry_run' if args.dry_run else 'controlled_write',
        'writes': [],
        'ok': False,
    }
    common.atomic_json(audit_path, audit)
    try:
        if not args.dry_run:
            if started.date().isoformat() != EXPECTED_EXECUTION_DATE or not (EXPECTED_START <= started.time().replace(tzinfo=None) <= EXPECTED_END):
                raise RuntimeError('execução fora da janela única autorizada')
            if STATE_PATH.exists():
                previous = common.load_json(STATE_PATH)
                if previous.get('ok'):
                    raise RuntimeError('pedido único já concluído')
        account_doc = common.load_json(common.ACCOUNT_PATH)
        account = (account_doc.get('accounts') or [{}])[0]
        meta, _sb, token, credential_readback = common.load_runtime_modules(account)
        audit['credential_readback'] = credential_readback
        with open_lock(LOCK_PATH) as own_lock, common.open_lock() as roas_lock:
            acquire_with_timeout(own_lock)
            acquire_with_timeout(roas_lock)
            scope, exclusions = collect_scope(common, meta, token)
            audit['preflight'] = {
                'campaigns': len(scope),
                'adsets': sum(len(item['adsets']) for item in scope),
                'ads': sum(len(item['ads']) for item in scope),
                'campaigns_with_spend': sum(item['insight']['spend_usd'] > 0 for item in scope),
                'total_spend_usd': round(sum(item['insight']['spend_usd'] for item in scope), 2),
                'campaigns': [item['insight'] for item in scope],
                'campaigns_with_spend_total': len(scope) + len(exclusions),
                'exclusions': exclusions,
            }
            common.atomic_json(audit_path, audit)
            if args.dry_run:
                audit['ok'] = True
                audit['finished_at_et'] = common.now_et().isoformat()
                common.atomic_json(audit_path, audit)
                print(summarize_dry_run(scope, exclusions))
                return 0
            latest_denylist = load_denylist()
            for item in scope:
                eligibility = page_eligibility(
                    item['campaign'].get('name'),
                    meta_page_id=item['meta_page_id'],
                    denylist=latest_denylist,
                )
                if not eligibility.get('eligible'):
                    raise RuntimeError('Page tornou-se inelegível na reconciliação imediatamente anterior ao write')
            for item in scope:
                campaign_id = str(item['campaign']['id'])
                campaign_result = reconcile_status(common, meta, token, campaign_id, item['campaign'])
                campaign_result.update({'kind': 'campaign', 'campaign_id': campaign_id})
                audit['writes'].append(campaign_result)
                common.atomic_json(audit_path, audit)
                if not campaign_result.get('ok'):
                    continue
                for adset in item['adsets']:
                    result = reconcile_status(common, meta, token, str(adset['id']), adset)
                    result.update({'kind': 'adset', 'campaign_id': campaign_id})
                    audit['writes'].append(result)
                    common.atomic_json(audit_path, audit)
                if not all(row.get('ok') for row in audit['writes'] if row.get('campaign_id') == campaign_id and row.get('kind') == 'adset'):
                    continue
                for ad in item['ads']:
                    result = reconcile_status(common, meta, token, str(ad['id']), ad)
                    result.update({'kind': 'ad', 'campaign_id': campaign_id})
                    audit['writes'].append(result)
                    common.atomic_json(audit_path, audit)
            readback = final_readback(common, meta, token, scope)
            audit['final_readback'] = readback
            if not readback['ok']:
                raise RuntimeError('readback final não confirmou toda a hierarquia')
            target_ads = {str(ad['id']) for item in scope for ad in item['ads']}
            clear_roas_provenance(common, target_ads, audit)
            audit['budget_writes'] = 0
            audit['ok'] = True
            audit['finished_at_et'] = common.now_et().isoformat()
            common.atomic_json(audit_path, audit)
            common.atomic_json(STATE_PATH, {
                'request_id': audit['request_id'],
                'ok': True,
                'finished_at_et': audit['finished_at_et'],
                'audit_path': str(audit_path),
                'counts': readback['counts'],
            })
            counts = readback['counts']
            restricted_pages = ', '.join(sorted({str(row['page_token']) for row in exclusions if row.get('reason') == 'restricted_page_history' and row.get('page_token')})) or 'nenhuma'
            archived_count = sum(row.get('reason') in {'campaign_archived', 'campaign_deleted'} for row in exclusions)
            print(
                '✅ Eggbev — lote elegível de 31/08 reativado e confirmado por readback Meta.\n'
                f"- {counts['campaigns']} campanhas, {counts['adsets']} conjuntos e {counts['ads']} anúncios ficaram ACTIVE.\n"
                f'- Pages restritas excluídas: {restricted_pages}.\n'
                f'- Campanhas arquivadas/excluídas ignoradas: {archived_count}. Nenhum budget foi alterado.'
            )
            return 0
    except Exception as exc:
        audit['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        audit['finished_at_et'] = common.now_et().isoformat()
        common.atomic_json(audit_path, audit)
        if args.dry_run:
            print(json.dumps({'status': 'BLOCKED', 'reason': str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(
                '⚠️ Eggbev — reativação automática bloqueada.\n'
                f'- Motivo: {str(exc)}.\n'
                '- O pedido ficou preservado para recovery por readback; nenhum budget foi alterado.'
            )
        return 1


if __name__ == '__main__':
    sys.exit(main())
