"""Exact eight-image-target gate regression; no credentials or network."""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
BASE = Path('/root/mgs-agent')
def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, BASE / rel)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
sb = load('atual_fnc_sb', 'scripts/ares-smartbidding-common.py')
gate = load('atual_fnc_domain', 'scripts/mgs-domain-scope.py')
SLUGS = {'fcp-team', 'fincben', 'fincfrog', 'finchettin', 'fincpro', 'jupalu', 'naboojobs', 'sapogamer'}
class AtualFncTests(unittest.TestCase):
    def test_exact_eight_live_identity_evidence(self):
        evidence = json.loads((BASE / 'reports/ares/sb-catalog-1564744929660637264.json').read_text())
        company = next(c for c in sb._scoped_catalog() if c['companyId'] == 'atual-fnc')
        self.assertEqual(company['publishers'], evidence['publishers'])
        self.assertEqual({p['publisherId'] for p in company['publishers']}, {'atual-fnc_' + s for s in SLUGS})
        self.assertEqual(len(company['publishers']), 8)
    def test_domains_only_ares_exact_and_www(self):
        registry = gate.load_registry(gate.DEFAULT_REGISTRY)
        for slug in SLUGS:
            host = slug + '.com'
            self.assertEqual(gate.allowed_domain(host, registry, 'ares'), host)
            self.assertEqual(gate.allowed_domain('www.' + host, registry, 'ares'), host)
            self.assertIsNone(gate.allowed_domain('child.' + host, registry, 'ares'))
            self.assertIsNone(gate.allowed_domain(host, registry, 'atena'))
    def test_local_company_projection_never_calls_http(self):
        with patch.object(sb, '_api_request_transport') as http:
            code, company, meta = sb.api_request('GET', '/company/atual-fnc')
            self.assertEqual(code, 200)
            self.assertEqual(len(company['publishers']), 8)
            self.assertEqual(meta['network_requests'], 0)
            http.assert_not_called()
    def test_exact_read_selector_accepted_mutation_blocked(self):
        companies = sb._scoped_catalog()
        for slug in SLUGS:
            sb._validate_sb_request('GET', '/report/performance_per_domain?publishers[]=atual-fnc_' + slug, None, companies)
        with self.assertRaises(ValueError):
            sb._validate_sb_request('PUT', '/company/atual-fnc', {}, companies)
        with self.assertRaises(ValueError):
            sb._validate_sb_request('GET', '/report/performance_per_domain?publishers[]=atual-fnc_unapproved', None, companies)
    def reject_modified_catalog(self, mutate):
        stored = json.loads(sb.SB_SCOPE_PATH.read_text())
        mutate(stored)
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as work:
            target = Path(work) / 'scope.json'
            target.write_text(json.dumps(stored))
            with patch.object(sb, 'SB_SCOPE_PATH', target), self.assertRaises(ValueError):
                sb._scoped_catalog()
    def test_extra_publisher_rejected(self):
        def add(d):
            c = next(c for c in d['companies'] if c['companyId'] == 'atual-fnc')
            p = copy.deepcopy(c['publishers'][0]); p['publisherId'] = 'atual-fnc_unapproved'; c['publishers'].append(p)
        self.reject_modified_catalog(add)
    def test_missing_image_publisher_rejected(self):
        self.reject_modified_catalog(lambda d: next(c for c in d['companies'] if c['companyId'] == 'atual-fnc')['publishers'].pop())
    def test_other_company_rejected(self):
        self.reject_modified_catalog(lambda d: d['companies'].append({'companyId': 'unapproved', 'publishers': []}))
if __name__ == '__main__':
    unittest.main()
