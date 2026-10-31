"""Bounded retries for validated SB reads; no live credentials or HTTP."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

SPEC = importlib.util.spec_from_file_location(
    'sb_transport_recovery',
    Path(__file__).resolve().parents[1] / 'scripts/ares-smartbidding-common.py',
)
assert SPEC is not None and SPEC.loader is not None
sb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sb)


class SmartBiddingTransportRecoveryTests(unittest.TestCase):
    def setUp(self):
        for name, value in [
            ('_scoped_catalog', []),
            ('_validate_sb_request', None),
            ('_validate_sb_response', None),
            ('get_access_token', ('synthetic-token', 'fixture')),
            ('invalidate_token_cache', None),
        ]:
            mock = patch.object(sb, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        self.http = patch.object(sb.requests, 'request').start()
        self.sleep = patch.object(sb.time, 'sleep').start()
        self.jitter = patch.object(sb.secrets, 'randbelow', return_value=0).start()
        self.addCleanup(patch.stopall)

    def response(self, status=200, body=None):
        return Mock(status_code=status, json=Mock(return_value=body or {}), headers={'Retry-After': '60'})

    def test_timeout_and_connection_error_recover_same_read(self):
        self.http.side_effect = [sb.requests.exceptions.ReadTimeout(), sb.requests.exceptions.ConnectionError(), self.response()]
        status, _, _ = sb.api_request('POST', '/metrics', payload={'publishers': ['fixture']})
        self.assertEqual(status, 200)
        self.assertEqual(self.http.call_count, 3)
        self.assertEqual(self.sleep.call_args_list, [call(1.0), call(2.0)])
        self.assertTrue(all(call == self.http.call_args for call in self.http.call_args_list))
        sb.get_access_token.assert_called_once()
        sb.invalidate_token_cache.assert_not_called()

    def test_three_failures_stop_without_refresh(self):
        self.http.side_effect = sb.requests.exceptions.ReadTimeout()
        with self.assertRaises(sb.requests.exceptions.ReadTimeout):
            sb.api_request('GET', '/metrics')
        self.assertEqual(self.http.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)
        sb.invalidate_token_cache.assert_not_called()

    def test_http_responses_including_cooldown_are_not_retried(self):
        for status in [429, 500, 503]:
            with self.subTest(status=status):
                self.http.reset_mock()
                self.http.side_effect = None
                self.http.return_value = self.response(status)
                self.assertEqual(sb.api_request('GET', '/metrics')[0], status)
                self.http.assert_called_once()
        self.sleep.assert_not_called()

    def test_scope_denied_before_credentials_or_http(self):
        sb._validate_sb_request.side_effect = ValueError('denied')
        with self.assertRaises(ValueError):
            sb.api_request('DELETE', '/unsafe')
        self.http.assert_not_called()
        sb.get_access_token.assert_not_called()

    def test_response_scope_still_fail_closed(self):
        self.http.return_value = self.response()
        sb._validate_sb_response.side_effect = ValueError('response denied')
        with self.assertRaises(ValueError):
            sb.api_request('GET', '/metrics')
        self.http.assert_called_once()

    def test_transport_budget_is_shared_across_auth_refresh(self):
        self.http.side_effect = [sb.requests.exceptions.ReadTimeout(), self.response(401), sb.requests.exceptions.ReadTimeout(), sb.requests.exceptions.ReadTimeout()]
        with self.assertRaises(sb.requests.exceptions.ReadTimeout):
            sb.api_request('GET', '/metrics')
        self.assertEqual(self.http.call_count, 4)
        self.assertEqual(self.sleep.call_count, 2)
        sb.invalidate_token_cache.assert_called_once()

    def test_login_transport_is_not_retried(self):
        sb.get_access_token.side_effect = sb.requests.exceptions.ReadTimeout()
        with self.assertRaises(sb.requests.exceptions.ReadTimeout):
            sb.api_request('GET', '/metrics')
        self.http.assert_not_called()
        self.sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
