#!/usr/bin/env python3
"""Rodolfo one-shot: US-EN -> (US_APP), scoped campaign names only."""
from __future__ import annotations
import argparse
import copy
import fcntl
import importlib.util
import json
import os
import sys
from typing import Any
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
sys.path.insert(0, str(BASE / 'scripts'))
from ares_campaign_v3.coordination import AccountWriterLeaseStore

REQUEST = 'shein-us-en-to-us-app-20261015-2355-rodolfo'
AT = datetime.fromisoformat('2026-10-15T23:55:00-04:00')
AUDIT = BASE / 'data/ares/meta-ads/audit/shein' / REQUEST
STATE = BASE / 'data/ares/meta-ads/state/manual-campaign-actions' / (REQUEST + '.json')
BRANDS = {'Escalatepower', 'Mavroa', 'Vizioid'}
TERMINAL = {'ARCHIVED', 'DELETED'}
CHILD_FIELDS = ('adsets.limit(100){id,name,status,daily_budget,lifetime_budget,'
                'bid_amount,bid_strategy,start_time,end_time,promoted_object,'
                'ads.limit(100){id,name,status,creative{id}}}')
FIELDS = ('id,account_id,name,status,objective,buying_type,daily_budget,lifetime_budget,'
          'bid_strategy,start_time,stop_time,spend_cap,special_ad_categories,' + CHILD_FIELDS)


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.pending')
    with temporary.open('w') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def save(state):
    state['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
    atomic(STATE, state)


def load_common():
    spec = importlib.util.spec_from_file_location('rename_common', BASE / 'scripts/ares-meta-common.py')
    assert spec is not None and spec.loader is not None
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    setattr(common, 'GRAPH_VERSION', 'v26.0')
    return common


def scope():
    catalog = json.loads((BASE / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json').read_text())
    selected = [a for a in catalog['accounts'] if a['name'].split('-')[0] in BRANDS]
    assert len(selected) == 18 and len({a['account_id'] for a in selected}) == 18
    assert all('-US-SHEIN-' in a['name'] for a in selected)
    return selected


def desired_name(name):
    # Literal replacement only: never rebuild naming or normalize other text.
    return name.replace('US-EN', '(US_APP)')


def timing_guard(now):
    if now < AT:
        raise ValueError('too_early')
    if now > AT + timedelta(minutes=30):
        raise ValueError('late_start_requires_review')


def safe_reason(exc):
    allowed = {'too_early', 'late_start_requires_review', 'account_identity_drift',
               'pagination_incomplete', 'child_pagination_requires_review',
               'campaign_account_drift', 'campaign_name_external_drift',
               'non_name_invariant_drift', 'name_readback_pending',
               'authorized_account_scope_drift'}
    reason = str(exc)
    return reason if reason in allowed else type(exc).__name__


def get(common, token, path, params):
    status, body, _ = common.graph_get(path, token, params)
    if status != 200:
        raise RuntimeError('meta_read_http_' + str(status))
    return body


def discovery(common, token, accounts):
    targets = []
    for account in accounts:
        aid = account['account_id']
        live = get(common, token, 'act_' + aid, {'fields': 'account_id,name,account_status'})
        if live.get('account_id') != aid or live.get('name') != account['name']:
            raise ValueError('account_identity_drift')
        params = {'fields': 'id,account_id,name,status', 'limit': 500}
        seen = set()
        while True:
            body = get(common, token, 'act_' + aid + '/campaigns', params)
            for campaign in body.get('data', []):
                assert campaign.get('account_id') == aid
                if campaign.get('status') in {'ACTIVE', 'PAUSED'} and 'US-EN' in campaign['name']:
                    targets.append({'id': campaign['id'], 'account_id': aid,
                                    'account_name': live['name'], 'discovery_name': campaign['name']})
            paging = body.get('paging', {})
            if not paging.get('next'):
                break
            cursor = paging.get('cursors', {}).get('after')
            if not cursor or cursor in seen:
                raise ValueError('pagination_incomplete')
            seen.add(cursor)
            params['after'] = cursor
    assert len(targets) == len({c['id'] for c in targets})
    return targets


def snapshot(common, token, campaign_id):
    body = get(common, token, campaign_id, {'fields': FIELDS})
    def normalize(value: Any) -> Any:
        if isinstance(value, dict):
            if 'data' in value:
                if value.get('paging', {}).get('next'):
                    raise ValueError('child_pagination_requires_review')
                return sorted((normalize(x) for x in value['data']), key=lambda x: x['id'])
            return {k: normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        return value
    return normalize(body)


def invariant(body):
    return {k: v for k, v in body.items() if k != 'name'}


def reconcile_one(common, token, target, state):
    current = snapshot(common, token, target['id'])
    if current['account_id'] != target['account_id']:
        raise ValueError('campaign_account_drift')
    before = target.get('before')
    if before is None:
        if current['status'] not in {'ACTIVE', 'PAUSED'}:
            target['state'] = 'SKIPPED_TERMINAL'
            save(state)
            return
        if current['name'] != target['discovery_name']:
            raise ValueError('campaign_name_external_drift')
        target.update(before=copy.deepcopy(current), desired_name=desired_name(current['name']))
        save(state)
        before = target['before']
    if invariant(current) != invariant(before):
        raise ValueError('non_name_invariant_drift')
    if current['name'] == target['desired_name']:
        target.update(state='VERIFIED', after=current)
        save(state)
        return
    if current['name'] != before['name']:
        raise ValueError('campaign_name_external_drift')
    target['state'] = 'NAME_WRITE_IN_FLIGHT'
    target['attempts'] = target.get('attempts', 0) + 1
    save(state)
    # The only mutable field is name; readback is required even after HTTP error.
    try:
        status, _, _ = common.graph_post_once(target['id'], token, {'name': target['desired_name']})
        target['last_write_http'] = status
    except Exception as exc:
        target['last_write_exception_type'] = type(exc).__name__
    save(state)
    final = snapshot(common, token, target['id'])
    if invariant(final) != invariant(before):
        raise ValueError('non_name_invariant_drift')
    if final['name'] != target['desired_name']:
        raise ValueError('name_readback_pending')
    target.update(state='VERIFIED', after=final)
    save(state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with STATE.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(STATE.read_text()) if STATE.exists() else {
            'request_id': REQUEST, 'authorized_by': '344196393512075265',
            'source_thread_id': '1560359535175143545', 'scheduled_for': AT.isoformat(),
            'brands': sorted(BRANDS), 'scope': 'ACTIVE/PAUSED campaign name literal replacement only',
            'status': 'PREPARING', 'targets': []}
        try:
            if not args.dry_run:
                if state.get('status') == 'COMPLETE':
                    return 0
                timing_guard(datetime.now(timezone.utc))
            accounts = scope()
            allowed = {a['account_id'] for a in accounts}
            if state.get('account_ids') and set(state['account_ids']) != allowed:
                raise ValueError('authorized_account_scope_drift')
            common = load_common()
            operation = json.loads((BASE / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
            token, _ = common.get_token_from_1password(operation['credential_architecture']['shared_car_shein_bisu']['token_item'])
            if args.dry_run:
                targets = discovery(common, token, accounts)
                for target in targets:
                    value = snapshot(common, token, target['id'])
                    assert value['name'] == target['discovery_name']
                    target.update(before=value, desired_name=desired_name(value['name']))
                atomic(AUDIT / 'dry-run.json', {'accounts': accounts, 'targets': targets,
                       'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'meta_writes': 0})
                if not state.get('targets_frozen'):
                    state.update(status='SCHEDULE_PENDING', preview_count=len(targets), account_ids=sorted(allowed))
                    save(state)
                print(json.dumps({'dry_run': True, 'accounts': len(accounts), 'campaigns': len(targets),
                                  'scheduled_for': AT.isoformat(), 'meta_writes': 0}))
                return 0
            if not state.get('targets_frozen'):
                state.update(targets=discovery(common, token, accounts), targets_frozen=True,
                             status='RUNNING', started_at_utc=datetime.now(timezone.utc).isoformat())
                save(state)
            config = json.loads((BASE / 'data/ares/meta-ads/engine-v3/config.json').read_text())
            leases = AccountWriterLeaseStore(config['state_root'])
            failures = []
            for target in state['targets']:
                if target.get('state') in {'VERIFIED', 'SKIPPED_TERMINAL'}:
                    continue
                assert target['account_id'] in allowed
                claimed = False
                try:
                    leases.claim(target['account_id'], REQUEST)
                    claimed = True
                    # Each retry begins with an exact GET; no blind write replay.
                    for attempt in range(3):
                        try:
                            reconcile_one(common, token, target, state)
                            break
                        except Exception:
                            if attempt == 2:
                                raise
                except Exception as exc:
                    target.update(error_type=type(exc).__name__, error_reason=safe_reason(exc), state='RECOVERY_REQUIRED')
                    failures.append(target['id'])
                    save(state)
                finally:
                    if claimed:
                        leases.release(target['account_id'], REQUEST)
            verified = [t for t in state['targets'] if t.get('state') == 'VERIFIED']
            state.update(status='RECOVERY_REQUIRED' if failures else 'COMPLETE',
                         verified_count=len(verified), failed_ids=failures)
            if failures:
                state['next_step'] = 'Resolve per-target recorded error, GET exact saved IDs, compare before/desired names and invariants, resume only missing name writes under the same request. No other mutations.'
            save(state)
            atomic(AUDIT / 'execution.json', state)
            if failures:
                print('⚠️ Troca US-EN → (US_APP): ' + str(len(verified)) + ' campanhas confirmadas; '
                      + str(len(failures)) + ' pendentes. Ares mantém o pedido para recuperação, sem ampliar o escopo.')
                return 0  # Deliver only the short PT-BR pending result; state is not COMPLETE.
            print('✅ Troca US-EN → (US_APP) concluída em ' + str(len(verified))
                  + ' campanhas de Escalatepower, Mavroa e Vizioid. Nomes confirmados na Meta; '
                    'status, orçamento, lance, início e conjuntos/anúncios preservados. Arquivadas/excluídas não foram alteradas.')
            return 0
        except Exception as exc:
            state.update(status='RECOVERY_REQUIRED', error_type=type(exc).__name__,
                         error_reason=safe_reason(exc), next_step='Reconcile exact saved IDs and before/desired names; resume only missing name updates after resolving recorded cause. No campaign creation or non-name writes.')
            save(state)
            print('⚠️ Troca US-EN → (US_APP) ainda não concluída. Pedido preservado para recuperação pelo Ares; nenhuma ampliação de escopo.')
            return 0  # Cron transport succeeded; operational failure remains in durable state.


if __name__ == '__main__':
    raise SystemExit(main())
