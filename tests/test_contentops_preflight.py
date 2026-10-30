"""Offline safety tests. Synthetic credentials only; no network or 1Password calls."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('contentops_preflight', Path(__file__).resolve().parents[1] / 'scripts/mgs-contentops-preflight.py')
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

class PreflightSafetyTests(unittest.TestCase):
    domain = 'fixture.invalid'

    def item(self, base=None, password='synthetic-secret'):
        fields = [{'label': 'api_auth_user', 'value': 'synthetic-user'}, {'label': 'api_application_password', 'value': password}]
        if base is not None:
            fields.append({'label': 'api_base', 'value': base})
        return {'fields': fields}

    def resolve(self, item):
        with patch.object(M, 'op_json', side_effect=[[{'id': 'synthetic-id', 'title': 'Wordpress - ' + self.domain}], item]):
            return M.resolve(self.domain)

    def test_literal_domain_rejects_url_before_subprocess(self):
        with patch.object(M.subprocess, 'run') as invoke:
            with self.assertRaisesRegex(M.PreflightError, 'literal_domain_required'):
                M.gate('https://fixture.invalid')
            invoke.assert_not_called()

    def test_domain_gate_precedes_credentials(self):
        with patch.object(M, 'gate', side_effect=M.PreflightError('domain_not_authorized')), patch.object(M, 'resolve') as resolve:
            with self.assertRaisesRegex(M.PreflightError, 'domain_not_authorized'):
                M.run(self.domain)
            resolve.assert_not_called()

    def test_ambiguous_item_is_blocked(self):
        entries = [{'id': str(i), 'title': 'Wordpress - ' + self.domain} for i in range(2)]
        with patch.object(M, 'op_json', return_value=entries) as op:
            with self.assertRaisesRegex(M.PreflightError, 'canonical_login_missing_or_ambiguous'):
                M.resolve(self.domain)
            self.assertEqual(op.call_count, 1)

    def test_base_wp_json_adds_version_once(self):
        self.assertEqual(self.resolve(self.item('https://fixture.invalid/wp-json'))[2], 'https://fixture.invalid/wp-json/wp/v2')

    def test_versioned_base_does_not_duplicate(self):
        self.assertEqual(self.resolve(self.item('https://fixture.invalid/wp-json/wp/v2/'))[2], 'https://fixture.invalid/wp-json/wp/v2')

    def test_default_base_is_exact_origin(self):
        self.assertEqual(self.resolve(self.item())[2], 'https://fixture.invalid/wp-json/wp/v2')

    def test_other_origin_is_rejected(self):
        with self.assertRaisesRegex(M.PreflightError, 'canonical_api_origin_mismatch'):
            self.resolve(self.item('https://unrelated.invalid/wp-json/wp/v2'))

    def test_missing_rest_pair_does_not_use_browser_password(self):
        with self.assertRaisesRegex(M.PreflightError, 'canonical_rest_fields_missing'):
            self.resolve({'fields': [{'label': 'username', 'value': 'synthetic-user'}, {'label': 'password', 'value': 'browser-only-synthetic'}]})

    def test_unsafe_curl_auth_value_is_rejected(self):
        with self.assertRaisesRegex(M.PreflightError, 'unsupported_auth_transport_characters'):
            self.resolve(self.item(password='synthetic"invalid'))

    def test_failed_plugins_check_is_not_full_success(self):
        with patch.object(M, 'gate'), patch.object(M, 'resolve', return_value=('synthetic-user', 'synthetic-secret', 'https://fixture.invalid/wp-json/wp/v2')), patch.object(M, 'get_json', side_effect=[(200, {'roles': ['administrator'], 'capabilities': {'activate_plugins': True}}), (403, {'code': 'synthetic_denied'})]):
            result = M.run(self.domain)
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['remote_mutations'], 0)

if __name__ == '__main__':
    unittest.main()
