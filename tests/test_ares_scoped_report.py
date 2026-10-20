import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

BASE = Path('/root/mgs-agent')
spec = importlib.util.spec_from_file_location('scoped_report_tests', BASE / 'scripts/ares-scoped-report.py')
assert spec and spec.loader
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

@pytest.fixture
def positive_scope():
    return {'operational_business_id': '555555', 'ad_accounts': [{'account_id': '111111', 'name': 'Synthetic A'}, {'account_id': '222222', 'name': 'Synthetic B'}]}


def test_all_selection_is_exact_positive_catalog(positive_scope):
    with patch.object(report.scope, 'load_scope', return_value=positive_scope):
        _, accounts = report.select_accounts()
    assert {a['account_id'] for a in accounts} == {'111111', '222222'}


def test_unknown_selection_stops_before_credentials_or_transport(positive_scope):
    with patch.object(report.scope, 'load_scope', return_value=positive_scope), patch.object(report, 'module') as transport:
        with pytest.raises(ValueError):
            report.collect('spend', 'synthetic-item', '2026-10-19', '2026-10-19', ['333333'])
        transport.assert_not_called()


def test_malformed_source_id_is_not_repaired(positive_scope):
    with patch.object(report.scope, 'load_scope', return_value=positive_scope):
        for bad in [' 111111', '111111x', 'act_%31%31%31%31%31%31']:
            with pytest.raises(ValueError):
                report.select_accounts([bad])


def test_spend_generic_end_to_end_offline(positive_scope):
    meta = Mock()
    meta.get_token_from_1password.return_value = ('synthetic-no-secret', 'fixture')
    meta.graph_batch_get.return_value = (200, [
        {'code': 200, 'body': {'data': [{'account_id': aid, 'account_currency': 'USD', 'spend': '1.00'}]}}
        for aid in ['111111', '222222']], {})
    with patch.object(report.scope, 'load_scope', return_value=positive_scope), patch.object(report, 'module', return_value=meta):
        result = report.collect('spend', 'synthetic-item', '2026-10-19', '2026-10-19')
    assert result['complete'] and result['scope_verified']
    assert result['expected_accounts'] == result['complete_accounts'] == 2
    requests = meta.graph_batch_get.call_args.args[1]
    assert {r['path'] for r in requests} == {'act_111111/insights', 'act_222222/insights'}
    meta.graph_post.assert_not_called()
    assert result['mutations'] == 0


def test_permission_error_is_reported_without_fallback(positive_scope):
    meta = Mock()
    meta.get_token_from_1password.return_value = ('synthetic-no-secret', 'fixture')
    meta.graph_batch_get.return_value = (200, [
        {'code': 403, 'body': {'error': {'code': 200, 'message': 'Do not copy this provider message'}}},
        {'code': 200, 'body': {'data': []}}], {})
    with patch.object(report.scope, 'load_scope', return_value=positive_scope), patch.object(report, 'module', return_value=meta):
        result = report.collect('charges', 'synthetic-item', '2026-10-19', '2026-10-19')
    assert not result['complete']
    assert result['rows'][0]['availability'] == 'unavailable'
    assert 'provider message' not in json.dumps(result)
    assert meta.get_token_from_1password.call_count == 1
    meta.graph_get.assert_not_called()


def test_billing_projection_does_not_disclose_instrument_or_invent_amount():
    row = report.charge_projection({'event_type': 'ad_account_billing_charge', 'event_time': '2026-10-19T12:00:00Z', 'extra_data': json.dumps({'display_string': 'synthetic-instrument', 'balance': '999', 'currency': 'USD'})})
    assert row['amount_as_returned'] is None
    assert 'synthetic-instrument' not in json.dumps(row)
    assert row['charged_instrument'] == 'not_proven_by_current_payment_method'


def test_charge_projection_retains_source_unit_not_assumed_currency_units():
    row = report.charge_projection({'event_type': 'ad_account_billing_charge', 'extra_data': {'amount': '1000', 'currency': 'USD'}})
    assert row['amount_as_returned'] == '1000'
    assert row['amount_source_field'] == 'amount'


def test_cursor_pagination_never_follows_authenticated_next_url():
    meta = Mock()
    meta.graph_get.side_effect = [
        (200, {'data': [{'x': 1}], 'paging': {'next': 'https://example.invalid/do-not-fetch?access_token=synthetic', 'cursors': {'after': 'cursor-one'}}}, {}),
        (200, {'data': [{'x': 2}]}, {})]
    rows, complete, _, _ = report.read_pages(meta, 'synthetic', 'act_111111/activities', {'fields': 'event_type'})
    assert complete and len(rows) == 2
    assert all(call.args[0] == 'act_111111/activities' for call in meta.graph_get.call_args_list)
    assert meta.graph_get.call_args_list[1].args[2]['after'] == 'cursor-one'


def test_unresolvable_pagination_is_not_marked_complete():
    meta = Mock()
    meta.graph_get.return_value = (200, {'data': [], 'paging': {'next': 'https://example.invalid/unknown'}}, {})
    _, complete, _, error = report.read_pages(meta, 'synthetic', 'act_111111/activities', {})
    assert not complete and error['pagination'] == 'unresolved_cursor'


def test_invoices_fixed_business_end_to_end_offline(positive_scope):
    meta = Mock()
    meta.get_token_from_1password.return_value = ('synthetic-no-secret', 'fixture')
    meta.graph_get.return_value = (200, {'data': [{'id': '777777', 'invoice_id': 'INV-FIXTURE', 'ad_account_ids': ['111111'], 'currency': 'USD', 'amount': '1.00', 'payment_status': 'Paid'}]}, {})
    with patch.object(report.scope, 'load_scope', return_value=positive_scope), patch.object(report, 'module', return_value=meta):
        result = report.collect('invoices', 'synthetic-item', '2026-10-01', '2026-10-19')
    assert result['complete'] and result['http_status'] == 200
    assert meta.graph_get.call_args.args[0] == '555555/business_invoices'
    assert result['rows'][0]['ad_account_ids'] == ['111111']


def test_invoice_with_unapproved_account_is_retained_not_returned(positive_scope):
    meta = Mock()
    meta.get_token_from_1password.return_value = ('synthetic-no-secret', 'fixture')
    meta.graph_get.return_value = (200, {'data': [{'ad_account_ids': ['333333']}]}, {})
    with patch.object(report.scope, 'load_scope', return_value=positive_scope), patch.object(report, 'module', return_value=meta):
        with pytest.raises(ValueError):
            report.collect('invoices', 'synthetic-item', '2026-10-01', '2026-10-19')
