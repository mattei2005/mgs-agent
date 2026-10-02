#!/usr/bin/env python3
"""Offline nominal comparison; no APR/CET estimation or product recommendation."""
import json
import re
import sys
from decimal import Decimal

CENT = Decimal('0.01')
ROOT_FIELDS = {'currency', 'amount_received', 'offers'}
OFFER_FIELDS = {'label', 'installments', 'installment_amount', 'upfront_fees'}
MONEY_PATTERN = re.compile(r'\d{1,12}(?:\.\d{1,2})?\Z', re.ASCII)


def money(value):
    if not isinstance(value, str) or not MONEY_PATTERN.fullmatch(value):
        raise ValueError('Money must be a nonnegative decimal string with at most two decimal places.')
    return Decimal(value)


def compare(payload):
    if not isinstance(payload, dict) or set(payload) != ROOT_FIELDS:
        raise ValueError('Provide exactly currency, amount_received and offers; no personal data.')
    currency = payload['currency']
    if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency, flags=re.ASCII):
        raise ValueError('Currency must be a three-letter code. No currency conversion is supported.')
    received = money(payload['amount_received'])
    if received <= 0:
        raise ValueError('amount_received must be positive and equal for all offers.')
    offers = payload['offers']
    if not isinstance(offers, list) or not 2 <= len(offers) <= 5:
        raise ValueError('Provide two to five comparable offers.')
    rows, labels = [], set()
    for offer in offers:
        if not isinstance(offer, dict) or set(offer) != OFFER_FIELDS:
            raise ValueError('Offer fields must be label, installments, installment_amount and upfront_fees.')
        label = offer['label']
        if not isinstance(label, str) or not label.strip() or len(label) > 80 or any(ord(c) < 32 for c in label):
            raise ValueError('Use a short non-personal offer label.')
        if label in labels:
            raise ValueError('Offer labels must be unique.')
        labels.add(label)
        count = offer['installments']
        if type(count) is not int or not 1 <= count <= 600:
            raise ValueError('installments must be an integer between 1 and 600.')
        payment = money(offer['installment_amount'])
        fees = money(offer['upfront_fees'])
        total = count * payment + fees
        rows.append({
            'label': label, 'installments': count,
            'installment_amount': format(payment.quantize(CENT), 'f'),
            'upfront_fees': format(fees.quantize(CENT), 'f'),
            'total_paid': format(total.quantize(CENT), 'f'),
            'cost_above_received': format((total - received).quantize(CENT), 'f'),
        })
    rows.sort(key=lambda row: Decimal(row['total_paid']))
    return {
        'currency': currency, 'amount_received': format(received.quantize(CENT), 'f'),
        'comparison_basis': 'nominal_total_paid_only', 'offers': rows,
        'limitations': [
            'All offers must provide the same amount received in the same currency.',
            'Installments must be fixed and upfront_fees must not already be included in installments.',
            'This is not APR/CET, present-value analysis, credit eligibility or personalized financial advice.',
        ],
    }


def main():
    try:
        raw = sys.stdin.read(65537)
        if len(raw) > 65536:
            raise ValueError('Input is too large.')
        result = compare(json.loads(raw))
    except (ValueError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
