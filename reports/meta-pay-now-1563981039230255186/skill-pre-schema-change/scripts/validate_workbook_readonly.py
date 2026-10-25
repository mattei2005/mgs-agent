#!/usr/bin/env python3
"""Read-only structural/financial readback for the manual-payment workbook.
No Google write methods, Meta calls, card entry or payment actions exist here.
"""
import argparse
from collections import Counter
from decimal import Decimal
import importlib
import json
import os
import re
import sys
from urllib.parse import quote

HELPER_ROOT = '/root/mgs-agent/scripts'
CANONICAL_EMAIL = 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
SELECTORS = ('ARES_DRIVE_AUTH_MODE', 'MGS_DRIVE_AUTH_PRIMARY',
             'MGS_GOOGLE_SHEETS_AUTH_MODE', 'MGS_META_APP_ROLES_GOOGLE_AUTH_MODE')


def money(value):
    return Decimal(str(value)).quantize(Decimal('.01'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spreadsheet-id', required=True)
    parser.add_argument('--sheet-id', required=True, type=int)
    parser.add_argument('--business-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.spreadsheet_id) or args.sheet_id < 0 or not args.business_id.isdigit():
        raise ValueError('invalid_target_identifier')
    sys.path.insert(0, HELPER_ROOT)
    auth = importlib.import_module('mgs_google_workspace_auth')
    auth.load_env()
    if any(os.getenv(key) != 'service_account' for key in SELECTORS):
        raise ValueError('noncanonical_auth_selector')
    sa = auth.load_service_account()
    if sa.get('project_id') != 'mgs-core-prod' or sa.get('client_email') != CANONICAL_EMAIL:
        raise ValueError('noncanonical_service_account')
    token = auth.service_account_access_token()

    def get(url):
        status, data = auth.api_json('GET', url, token, quota_project='mgs-core-prod')
        if status != 200:
            raise ValueError('read_http_' + str(status) + ':' + str(data.get('error', {}).get('status')))
        return data

    caps = get('https://www.googleapis.com/drive/v3/files/' + args.spreadsheet_id
               + '?supportsAllDrives=true&fields=trashed,capabilities(canEdit)')
    if caps.get('trashed') or not caps.get('capabilities', {}).get('canEdit'):
        raise ValueError('target_unavailable_or_not_editable')
    root = 'https://sheets.googleapis.com/v4/spreadsheets/' + args.spreadsheet_id
    metadata = get(root + '?fields=sheets.properties')
    matches = [s['properties'] for s in metadata['sheets'] if s['properties']['sheetId'] == args.sheet_id]
    if len(matches) != 1:
        raise ValueError('sheet_id_not_unique')
    title = matches[0]['title']
    rng = "'" + title.replace("'", "''") + "'!A:G"
    formulas = get(root + '/values/' + quote(rng, safe='!:') + '?valueRenderOption=FORMULA')['values']
    effective = get(root + '/values/' + quote(rng, safe='!:') + '?valueRenderOption=UNFORMATTED_VALUE')['values']
    grid = get(root + '?includeGridData=true&ranges=' + quote(rng, safe='')
               + '&fields=sheets(data(rowData(values(note,userEnteredFormat(textFormat.link,numberFormat)))))')
    notes = grid['sheets'][0]['data'][0]['rowData']
    expected = ('Nome da conta', 'Forma de pagamento', 'Cartão usado como default',
                'Última cobrança no cartão', 'Média diária', 'Saldo a pagar', 'Total')
    if len(formulas[0]) != 7 or any(not str(actual).startswith(prefix)
            for actual, prefix in zip(formulas[0], expected)):
        raise ValueError('header_schema_mismatch')
    if len(formulas) != len(effective):
        raise ValueError('render_dimension_mismatch')
    accounts, ids, groups, totals = [], set(), Counter(), []
    currencies = set()
    for index, row in enumerate(effective):
        row = row + [''] * (7 - len(row))
        if any(isinstance(v, str) and v.startswith(('#REF!', '#VALUE!', '#DIV/0!', '#ERROR!', '#N/A')) for v in row):
            raise ValueError('formula_error_row_' + str(index + 1))
        cell = notes[index].get('values', [{}])[0] if index < len(notes) else {}
        match = re.search(r'^ID da conta: (\d+)\b', cell.get('note', ''))
        if match:
            aid = match.group(1)
            if aid in ids:
                raise ValueError('duplicate_account_id')
            ids.add(aid)
            link = cell.get('userEnteredFormat', {}).get('textFormat', {}).get('link', {}).get('uri', '')
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(link)
            query = parse_qs(parsed.query)
            if 'billing_hub/accounts/details' not in parsed.path or query.get('asset_id') != [aid]:
                raise ValueError('billing_account_link_mismatch')
            if query.get('business_id') != [args.business_id]:
                raise ValueError('billing_business_mismatch')
            row_formats = notes[index]['values']
            row_currencies = []
            for col in (4, 5, 6):
                pattern = row_formats[col].get('userEnteredFormat', {}).get('numberFormat', {}).get('pattern', '')
                cm = re.search(r'"([A-Z]{3})"', pattern)
                if not cm:
                    raise ValueError('financial_currency_format_missing')
                row_currencies.append(cm.group(1))
            if len(set(row_currencies)) != 1:
                raise ValueError('row_currency_mismatch')
            currencies.add(row_currencies[0])
            if any(not isinstance(row[c], (int, float)) or isinstance(row[c], bool) for c in (4, 5, 6)):
                raise ValueError('financial_value_missing')
            groups[row[1]] += 1
            accounts.append({'row': index + 1, 'method': row[1], 'values': row})
        elif str(row[0]).startswith('TOTAL'):
            for col in (4, 5, 6):
                if len(formulas[index]) <= col or not str(formulas[index][col]).startswith('=ROUND(SUM('):
                    raise ValueError('total_formula_missing_round_sum')
            totals.append((index + 1, row))
    if len(currencies) != 1:
        raise ValueError('mixed_currency_grand_total_not_supported')
    if not accounts or not totals:
        raise ValueError('empty_scope_or_totals')
    grand = [row for _, row in totals if str(row[0]).startswith('TOTAL GERAL')]
    if len(grand) != 1:
        raise ValueError('grand_total_not_unique')
    for col in (4, 5, 6):
        if money(grand[0][col]) != sum((money(a['values'][col]) for a in accounts), Decimal(0)):
            raise ValueError('grand_total_mismatch_column_' + str(col + 1))
    for label, heading in [('Cartão de crédito', 'TOTAL CARTÃO DE CRÉDITO'),
                           ('Linha de crédito', 'TOTAL LINHA DE CRÉDITO')]:
        if groups[label]:
            sub = [r for _, r in totals if r[0] == heading]
            if len(sub) != 1:
                raise ValueError('subtotal_not_unique')
            for col in (4, 5, 6):
                if money(sub[0][col]) != sum((money(a['values'][col]) for a in accounts if a['method'] == label), Decimal(0)):
                    raise ValueError('subtotal_mismatch')
    cards = [a for a in accounts if a['method'] == 'Cartão de crédito']
    print(json.dumps({'status': 'snapshot_readback_pass', 'spreadsheet_id': args.spreadsheet_id,
        'sheet_id': args.sheet_id, 'business_id': args.business_id, 'currency': next(iter(currencies)),
        'accounts': len(accounts), 'groups': dict(groups),
        'card_charge_values_present': sum(isinstance(a['values'][3], (int, float)) for a in cards),
        'card_charge_blank_rows': [a['row'] for a in cards if a['values'][3] == ''],
        'totals_validated_columns': ['E', 'F', 'G'], 'all_account_billing_links_checked': True,
        'historical_instrument_not_revalidated_by_this_script': True,
        'google_write_calls': 0, 'meta_calls': 0, 'payments_executed': 0}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)[:200]}, ensure_ascii=False))
        sys.exit(2)
