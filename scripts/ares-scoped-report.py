#!/usr/bin/env python3
"""Deterministic read-only reports from the Ares positive catalog only."""
from __future__ import annotations
import argparse
import datetime as dt
import importlib.util
import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / 'scripts' / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError('Read-only report dependency unavailable')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

scope = module('ares_report_scope', 'mgs-ares-asset-scope.py')


def select_accounts(requested=None):
    data = scope.load_scope()
    known = {row['account_id']: row for row in data['ad_accounts']}
    if requested is None:
        return data, list(known.values())
    result = []
    seen = set()
    for raw in requested:
        if not isinstance(raw, str) or not scope.allowed_account(raw, data):
            raise scope.ScopeError(scope.DENY)
        aid = raw.removeprefix('act_')
        if aid not in seen:
            result.append(known[aid])
            seen.add(aid)
    if not result:
        raise ValueError('Seleção vazia; relatório não executado.')
    return data, result


def safe_error(body):
    error = body.get('error', {}) if isinstance(body, dict) else {}
    return {key: error[key] for key in ('code', 'error_subcode') if key in error}


def read_pages(meta, token, path, params, first=None, max_pages=100):
    rows = []
    cursors = set()
    for index in range(max_pages):
        if index == 0 and first is not None:
            status, body = first
        else:
            status, body, _ = meta.graph_get(path, token, params)
        if status != 200 or not isinstance(body, dict) or not isinstance(body.get('data'), list):
            return rows, False, status, safe_error(body)
        rows.extend(body['data'])
        paging = body.get('paging') or {}
        if not paging.get('next'):
            return rows, True, status, {}
        after = (paging.get('cursors') or {}).get('after')
        if not after or after in cursors:
            return rows, False, status, {'pagination': 'unresolved_cursor'}
        cursors.add(after)
        params = dict(params, after=after)
    return rows, False, 200, {'pagination': 'page_limit'}


def charge_projection(event):
    extra = event.get('extra_data')
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except ValueError:
            extra = {}
    extra = extra if isinstance(extra, dict) else {}
    amount = None
    amount_field = None
    for key in ('amount', 'charge_amount', 'amount_charged'):
        value = extra.get(key)
        if value is not None and not isinstance(value, bool):
            try:
                number = Decimal(str(value))
                if number.is_finite():
                    amount, amount_field = str(number), key
                    break
            except InvalidOperation:
                pass
    currency = extra.get('currency')
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        currency = None
    return {'event_type': event.get('event_type'), 'event_time': event.get('event_time'),
            'amount_as_returned': amount, 'amount_source_field': amount_field,
            'currency_as_returned': currency, 'charged_instrument': 'not_proven_by_current_payment_method'}


def collect(mode, item, since, until, requested=None, progress=None):
    # Selection is validated before importing transport or fetching credentials.
    data, accounts = select_accounts(requested)
    start, end = dt.date.fromisoformat(since), dt.date.fromisoformat(until)
    if end < start:
        raise ValueError('Período inválido.')
    if not item:
        raise ValueError('Vínculo corporativo de credencial explícito é obrigatório.')
    os.environ['ARES_META_GRAPH_VERSION'] = 'v26.0'
    meta = module('ares_scoped_report_transport', 'ares-meta-common.py')
    token, _ = meta.get_token_from_1password(item)
    result = {'mode': mode, 'business_id': data['operational_business_id'], 'source': 'Meta Graph v26.0',
              'since': since, 'until': until, 'selection_source': 'Ares positive catalog',
              'expected_accounts': len(accounts), 'credential_item': item, 'rows': [], 'mutations': 0}
    if mode == 'invoices':
        if requested is not None:
            raise ValueError('Faturas consolidadas exigem o recorte corporativo completo; sem rateio por conta.')
        params = {'fields': 'id,invoice_id,ad_account_ids,currency,amount,payment_status,invoice_date,billing_period',
                  'issue_start_date': since, 'issue_end_date': str(end + dt.timedelta(days=1)), 'limit': 100}
        invoices, complete, status, error = read_pages(meta, token, data['operational_business_id'] + '/business_invoices', params)
        if any(not isinstance(row.get('ad_account_ids'), list) or not row['ad_account_ids'] or any(not scope.allowed_account(str(aid), data) for aid in row['ad_account_ids']) for row in invoices):
            raise scope.ScopeError(scope.DENY)
        fields = ('id', 'invoice_id', 'ad_account_ids', 'currency', 'amount', 'payment_status', 'invoice_date', 'billing_period')
        result.update(rows=[{k: row[k] for k in fields if k in row} for row in invoices], complete=complete,
                      http_status=status, error=error,
                      limitation='Somente faturas expostas pela Meta no período; vazio não comprova inexistência de faturas. Gasto publicitário não é fatura paga.')
        return result
    timezone = ZoneInfo('America/New_York')
    start_time = dt.datetime.combine(start, dt.time.min, timezone).isoformat()
    end_time = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, timezone).isoformat()
    if mode == 'inventory':
        params = {'fields': 'id,account_id,name,business{id},currency,timezone_name,amount_spent,balance,funding_source_details'}
        suffix = ''
    elif mode == 'spend':
        params = {'fields': 'account_id,account_currency,date_start,date_stop,spend',
                  'time_range': json.dumps({'since': since, 'until': until}), 'level': 'account', 'limit': 100}
        suffix = '/insights'
    elif mode == 'charges':
        params = {'fields': 'event_type,event_time,extra_data', 'since': start_time, 'until': end_time, 'category': 'BUDGET', 'limit': 100}
        suffix = '/activities'
    else:
        raise ValueError('Modo de leitura desconhecido.')
    for offset in range(0, len(accounts), 25):
        batch_accounts = accounts[offset:offset + 25]
        requests = [{'name': a['account_id'], 'path': 'act_' + a['account_id'] + suffix, 'params': params} for a in batch_accounts]
        status, responses, _ = meta.graph_batch_get(token, requests)
        if status != 200 or not isinstance(responses, list) or len(responses) != len(requests):
            raise RuntimeError('Leitura batch incompleta; progresso já concluído preservado.')
        for account, response in zip(batch_accounts, responses):
            aid = account['account_id']
            code, body = response['code'], response.get('body')
            row = {'account_id': aid, 'name': account['name'], 'http_status': code, 'complete': False}
            if code != 200:
                row.update(availability='unavailable', error=safe_error(body))
            elif mode == 'inventory':
                if not isinstance(body, dict) or str(body.get('account_id')) != aid or str((body.get('business') or {}).get('id')) != data['operational_business_id']:
                    raise scope.ScopeError(scope.DENY)
                payment = body.get('funding_source_details') or {}
                row.update(complete=True, availability='available', currency=body.get('currency'), timezone=body.get('timezone_name'),
                           amount_spent_source=body.get('amount_spent'), balance_source=body.get('balance'),
                           payment_type=payment.get('type') if isinstance(payment, dict) else None,
                           payment_instrument='not_included')
            else:
                values, complete, page_status, error = read_pages(meta, token, 'act_' + aid + suffix, params, first=(code, body))
                row.update(complete=complete, availability='available' if complete else 'partial', http_status=page_status, error=error)
                if mode == 'spend':
                    if any(str(v.get('account_id')) != aid for v in values):
                        raise scope.ScopeError(scope.DENY)
                    row['spend_rows'] = [{k: value[k] for k in ('account_id', 'account_currency', 'date_start', 'date_stop', 'spend') if k in value} for value in values]
                else:
                    events = [v for v in values if str(v.get('event_type', '')).startswith('ad_account_billing_')]
                    row['billing_events'] = [charge_projection(event) for event in events]
                    row['limitation'] = 'Eventos retornados pela Meta; valor/unidade não inferidos do saldo, gasto ou cartão padrão atual.'
            result['rows'].append(row)
            if progress:
                progress.parent.mkdir(parents=True, exist_ok=True)
                with progress.open('a') as stream:
                    stream.write(json.dumps({'mode': mode, **row}, ensure_ascii=False) + '\n')
    result['complete_accounts'] = sum(row['complete'] for row in result['rows'])
    result['complete'] = result['complete_accounts'] == len(accounts)
    if len({r['account_id'] for r in result['rows']}) != len(accounts):
        raise RuntimeError('Cobertura de contas não reconciliada.')
    result['scope_verified'] = all(scope.allowed_account(r['account_id'], data) for r in result['rows'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'inventory', 'spend', 'charges', 'invoices'])
    parser.add_argument('--item')
    parser.add_argument('--since')
    parser.add_argument('--until')
    parser.add_argument('--account-ids', nargs='+')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.mode == 'plan':
        data, accounts = select_accounts(args.account_ids)
        result = {'business_id': data['operational_business_id'], 'selected_accounts': len(accounts), 'source': 'positive_catalog_only', 'http_calls': 0}
    else:
        if not args.item or not args.since or not args.until:
            parser.error('Leitura exige vínculo de credencial e período explícitos.')
        result = collect(args.mode, args.item, args.since, args.until, args.account_ids,
                         progress=args.out.with_suffix('.progress.jsonl') if args.out else None)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    # Default stdout is validation metadata, never financial/card payloads.
    print(json.dumps({k: v for k, v in result.items() if k not in {'rows'}}, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
