"""Offline confidentiality regressions. No live IDs, credentials or network."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path('/root/mgs-agent')

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / 'scripts' / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

scope = load('confidentiality_scope_test', 'mgs-ares-asset-scope.py')
sb = load('confidentiality_sb_test', 'ares-smartbidding-common.py')
common = load('confidentiality_meta_test', 'ares-meta-common.py')

class MetaConfidentialityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = {'operational_business_id': '555555', 'ad_accounts': [{'account_id': '111111'}]}
        for target, value in [('is_ares_context', True), ('load_scope', self.data)]:
            obj = patch.object(scope, target, return_value=value)
            obj.start()
            self.addCleanup(obj.stop)
        obj = patch.object(scope, 'PROVENANCE', Path(self.tmp.name) / 'provenance.json')
        obj.start()
        self.addCleanup(obj.stop)

    def test_unknown_numeric_and_discovery_routes_are_denied(self):
        for path in ['222222', 'me/adaccounts', 'me/businesses', '222222/owned_ad_accounts', '222222/insights']:
            with self.subTest(path=path), self.assertRaises(scope.ScopeError):
                scope.enforce_meta_path(path)

    def test_transport_blocks_unknown_routes_before_http(self):
        for path in ['999999999999999999999999', 'me/adaccounts', 'me/businesses', '999999999999999999999999/owned_ad_accounts']:
            with self.subTest(path=path), patch.object(common.urllib.request, 'urlopen') as http:
                with self.assertRaises(ValueError):
                    common._graph_get_once(path, 'synthetic-not-a-secret')
                http.assert_not_called()

    def test_ids_parameter_cannot_override_approved_path(self):
        with self.assertRaises(scope.ScopeError):
            scope.enforce_meta_path('111111', {'ids': '222222'})

    def test_claimed_parent_is_not_proof(self):
        with self.assertRaises(scope.ScopeError):
            scope.enforce_meta_path('222222', {'account_id': '111111'})

    def test_query_and_batch_body_are_validated(self):
        requests = [
            {'method': 'GET', 'relative_url': '111111?account_id=222222'},
            {'method': 'POST', 'relative_url': 'act_111111/campaigns', 'body': 'account_id=222222'},
            {'method': 'GET', 'relative_url': '222222?account_id=111111'},
        ]
        for child in requests:
            with self.subTest(child=child), self.assertRaises(scope.ScopeError):
                scope.enforce_meta_path('', {'batch': [child]})

    def test_absolute_traversal_and_duplicate_params_denied(self):
        for path in ['https://example.invalid/111111', '111111/../222222', '111111?account_id=111111&account_id=222222']:
            with self.subTest(path=path), self.assertRaises(scope.ScopeError):
                scope.enforce_meta_path(path)

    def test_field_expansion_cannot_discover_businesses(self):
        with self.assertRaises(scope.ScopeError):
            scope.enforce_meta_path('111111', {'fields': 'id,businesses{id,name}'})

    def test_batch_approved_account_is_supported(self):
        scope.enforce_meta_path('', {'batch': [{'method': 'GET', 'relative_url': 'act_111111/campaigns?fields=id,account_id'}]}, 'POST')

    def test_app_exception_is_read_metadata_only(self):
        scope.enforce_meta_path(scope.APP_ID, {'fields': 'id,name'})
        for method, params in [('POST', {'fields': 'id,name'}), ('GET', {'fields': 'businesses'})]:
            with self.assertRaises(scope.ScopeError):
                scope.enforce_meta_path(scope.APP_ID, params, method)

    def test_response_establishes_object_provenance(self):
        scope.observe_meta_response('act_111111/campaigns', {}, {'data': [{'id': '333333', 'account_id': '111111'}]})
        scope.enforce_meta_path('333333', {'fields': 'id,name'})
        scope.enforce_meta_path('333333/insights')
        ledger = json.loads(scope.PROVENANCE.read_text())
        self.assertEqual(ledger['objects']['333333']['account_id'], '111111')
        self.assertEqual(scope.PROVENANCE.stat().st_mode & 0o777, 0o600)

    def test_response_cannot_introduce_foreign_account(self):
        with self.assertRaises(scope.ScopeError):
            scope.observe_meta_response('act_111111/campaigns', {}, {'data': [{'id': '333333', 'account_id': '222222'}]})
        self.assertFalse(scope.PROVENANCE.exists())

    def test_observer_cannot_seed_unvalidated_path(self):
        with self.assertRaises(scope.ScopeError):
            scope.observe_meta_response('222222', {}, {'id': '333333', 'account_id': '111111'})

    def test_response_from_batch_establishes_child_provenance(self):
        scope.observe_meta_response('', {'batch': [{'method': 'GET', 'relative_url': 'act_111111/campaigns'}]}, [{'code': 200, 'body': json.dumps({'data': [{'id': '333333', 'account_id': '111111'}]})}], 'POST')
        scope.enforce_meta_path('333333')

    def test_fixed_business_invoice_read_is_allowed(self):
        scope.enforce_meta_path('555555/business_invoices', {'fields': 'id,ad_account_ids,currency,amount'})

    def test_other_business_invoice_read_denied(self):
        with self.assertRaises(scope.ScopeError):
            scope.enforce_meta_path('666666/business_invoices', {'fields': 'id,ad_account_ids'})

    def test_invoice_lookup_cannot_override_business_or_omit_accounts(self):
        for params in [{'fields': 'id,amount'}, {'fields': 'id,ad_account_ids', 'invoice_id': 'synthetic-unproven'}, {'fields': 'id,ad_account_ids,download_uri'}]:
            with self.assertRaises(scope.ScopeError):
                scope.enforce_meta_path('555555/business_invoices', params)

    def test_invoice_endpoint_cannot_mutate(self):
        with self.assertRaises(scope.ScopeError):
            scope.enforce_meta_path('555555/business_invoices', {'fields': 'id,ad_account_ids'}, 'POST')

    def test_invoice_response_rejects_unknown_account(self):
        with self.assertRaises(scope.ScopeError):
            scope.observe_meta_response('555555/business_invoices', {'fields': 'id,ad_account_ids'}, {'data': [{'id': '777777', 'ad_account_ids': ['222222']}]})

    def test_invoice_response_is_accepted_only_with_positive_accounts(self):
        scope.observe_meta_response('555555/business_invoices', {'fields': 'id,ad_account_ids'}, {'data': [{'id': '777777', 'ad_account_ids': ['111111']}]})
        self.assertFalse(scope.PROVENANCE.exists())

    def test_moved_business_is_retained_before_report_callers(self):
        with self.assertRaises(scope.ScopeError):
            scope.observe_meta_response('act_111111', {'fields': 'id,account_id,business{id}'}, {'id': 'act_111111', 'account_id': '111111', 'business': {'id': '666666'}})

    def test_scope_change_invalidates_provenance(self):
        scope.observe_meta_response('act_111111/campaigns', {}, {'data': [{'id': '333333'}]})
        with patch.object(scope, 'load_scope', return_value={'ad_accounts': [{'account_id': '444444'}]}):
            with self.assertRaises(scope.ScopeError):
                scope.enforce_meta_path('333333')

class SBConfidentialityTests(unittest.TestCase):
    def test_catalog_is_local_and_does_not_fetch_credentials_or_http(self):
        with patch.object(sb, 'get_access_token') as credentials, patch.object(sb.requests, 'request') as http:
            status, companies, metadata = sb.api_request('GET', '/company')
            self.assertEqual(status, 200)
            self.assertEqual({c['companyId'] for c in companies}, {'digital-trust', 'digital-trust-2'})
            self.assertEqual(metadata['network_requests'], 0)
            credentials.assert_not_called()
            http.assert_not_called()

    def test_foreign_company_denied_before_credentials_and_http(self):
        with patch.object(sb, 'get_access_token') as credentials, patch.object(sb.requests, 'request') as http:
            with self.assertRaises(ValueError):
                sb.api_request('GET', '/company/synthetic-outside')
            credentials.assert_not_called()
            http.assert_not_called()

    def test_empty_or_unknown_publishers_denied(self):
        for body in [{}, {'publishers': []}, {'publishers': ['synthetic-outside']}]:
            with self.subTest(body=body), patch.object(sb, 'get_access_token') as credentials, patch.object(sb.requests, 'request') as http:
                with self.assertRaises(ValueError):
                    sb.api_request('POST', '/report/performance_per_campaigns', payload=body)
                credentials.assert_not_called()
                http.assert_not_called()

    def test_validated_publisher_reaches_transport(self):
        publisher = sorted(sb._publisher_scope(sb._scoped_catalog()))[0]
        with patch.object(sb, '_api_request_transport', return_value=(200, [], {})) as transport:
            status, rows, _ = sb.api_request('POST', '/report/performance_per_campaigns', payload={'publishers': [publisher]})
            self.assertEqual((status, rows), (200, []))
            transport.assert_called_once()

    def test_get_query_and_all_selector_aliases_are_checked(self):
        with patch.object(sb, 'get_access_token') as credentials:
            for path, body in [('/campaigns/Messenger?companies[]=synthetic-outside', None), ('/estimated/delay', {'publisherIds': ['synthetic-outside']})]:
                with self.assertRaises(ValueError):
                    sb.api_request('GET' if body is None else 'POST', path, payload=body)
            credentials.assert_not_called()

    def test_direct_transport_cannot_bypass_scope(self):
        with patch.object(sb, 'get_access_token') as credentials, patch.object(sb.requests, 'request') as http:
            with self.assertRaises(ValueError):
                sb._api_request_transport('GET', '/company')
            credentials.assert_not_called()
            http.assert_not_called()

    def test_contradictory_response_is_not_returned(self):
        companies = sb._scoped_catalog()
        for body in [[{'DOMAIN': 'synthetic-outside.invalid'}], [{'SOURCE': 'facebook', 'CUSTOMER_ID': '999999999999999999999999'}]]:
            with self.assertRaises(ValueError):
                sb._validate_sb_response(body, companies)

    def test_approved_response_is_accepted(self):
        companies = sb._scoped_catalog()
        host = companies[0]['publishers'][0]['host']
        account = json.loads((BASE / 'data/ares/asset-scope.json').read_text())['ad_accounts'][0]['account_id']
        sb._validate_sb_response([{'DOMAIN': host, 'SOURCE': 'facebook', 'CUSTOMER_ID': account}], companies)

    def test_mutation_route_denied(self):
        publisher = sorted(sb._publisher_scope(sb._scoped_catalog()))[0]
        with patch.object(sb, 'get_access_token') as credentials:
            for method, path in [('DELETE', '/company/digital-trust'), ('POST', '/company')]:
                with self.assertRaises(ValueError):
                    sb.api_request(method, path, payload={'publishers': [publisher]})
            credentials.assert_not_called()

    def test_scoped_pricing_read_reaches_transport(self):
        publisher = sorted(sb._publisher_scope(sb._scoped_catalog()))[0]
        for suffix in ['', '?should_update_metrics=0', '?should_update_metrics=1']:
            with self.subTest(suffix=suffix), patch.object(sb, '_api_request_transport', return_value=(200, {}, {})) as transport:
                self.assertEqual(sb.api_request('GET', '/pricing/' + publisher + suffix)[0], 200)
                transport.assert_called_once()

    def test_pricing_rejects_writes_foreign_publishers_and_ambiguous_queries(self):
        publisher = sorted(sb._publisher_scope(sb._scoped_catalog()))[0]
        route = '/pricing/' + publisher
        cases = [
            ('POST', route, None), ('PUT', route, {}), ('DELETE', route, None),
            ('GET', route, {}), ('GET', '/pricing/synthetic-outside', None),
            ('GET', route + '/rules', None), ('GET', route + '?publishers[]=synthetic-outside', None),
            ('GET', route + '?should_update_metrics=1&should_update_metrics=0', None),
            ('GET', route + '?should_update_metrics=', None),
            ('GET', route + '?should_update_metrics=2', None),
            ('GET', 'https://example.invalid' + route, None),
            ('GET', route + '#fragment', None),
        ]
        for method, path, body in cases:
            with self.subTest(method=method, path=path), patch.object(sb, 'get_access_token') as credentials, patch.object(sb.requests, 'request') as http:
                with self.assertRaises(ValueError):
                    sb.api_request(method, path, payload=body)
                credentials.assert_not_called()
                http.assert_not_called()

    def test_pricing_direct_transport_cannot_bypass_scope(self):
        with patch.object(sb, 'get_access_token') as credentials, patch.object(sb.requests, 'request') as http:
            with self.assertRaises(ValueError):
                sb._api_request_transport('GET', '/pricing/synthetic-outside')
            credentials.assert_not_called()
            http.assert_not_called()

    def test_pricing_response_must_match_requested_publisher(self):
        publisher = sorted(sb._publisher_scope(sb._scoped_catalog()))[0]
        for body in [{}, [], {'publisherId': 'synthetic-outside'}, {'publisherId': publisher}]:
            with self.subTest(body=body), patch.object(sb, 'get_access_token', return_value=('synthetic', 'fixture')), patch.object(sb.requests, 'request') as http:
                http.return_value.status_code = 200
                http.return_value.json.return_value = body
                if body == {'publisherId': publisher}:
                    self.assertEqual(sb._api_request_transport('GET', '/pricing/' + publisher)[0], 200)
                else:
                    with self.assertRaises(ValueError):
                        sb._api_request_transport('GET', '/pricing/' + publisher)

if __name__ == '__main__':
    unittest.main()
