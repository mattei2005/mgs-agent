import importlib.util
import json
import unittest
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'could not load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SB = load_module('ares_smartbidding_common_test', '/root/mgs-agent/scripts/ares-smartbidding-common.py')
HOA = load_module('ares_meta_hoa_manager_test', '/root/mgs-agent/scripts/ares-meta-hoa-manager.py')


class SmartBiddingRoiTests(unittest.TestCase):
    def test_roi_formula_matches_dashboard_semantics(self):
        self.assertEqual(SB.compute_roi_pct(150, 100), 50.0)
        self.assertEqual(SB.compute_roi_pct(0, 100), -100.0)
        self.assertIsNone(SB.compute_roi_pct(100, 0))

    def test_auth0_parser_selects_username_password_form(self):
        parser = SB.LoginFormsParser()
        parser.feed(
            '<form action="/social"><input name="connection" value="google"></form>'
            '<form action="/login"><input name="state" value="x">'
            '<input name="username"><input name="password"></form>'
        )
        form = next(x for x in parser.forms if 'username' in x['inputs'] and 'password' in x['inputs'])
        self.assertEqual(form['action'], '/login')
        self.assertIn('state', form['inputs'])

    def test_hoa_roi_block_is_compact_and_balanced(self):
        text = HOA.output_table(
            'ROI da página',
            [{'pg_id': 'pg_22091', 'meta_spend': '122.76', 'roi_drip': '+19.9%', 'roi_total': '+21.1%', 'status': 'OK'}],
            [('pg_id','PG'),('meta_spend','Spend'),('roi_drip','ROI Drip'),('roi_total','ROI Total'),('status','Status')],
        )
        self.assertIn('ROI Drip', text)
        self.assertNotIn('ROI Broad', text)
        self.assertIn('ROI Total', text)
        self.assertEqual(text.count('```'), 2)
        self.assertLess(len(text), 2000)

    def test_scope_does_not_change_rules_or_hoa_target(self):
        operation = json.loads(Path('/root/mgs-agent/data/ares/meta-ads/operations/OpenzedFinanzas-CC-ES.json').read_text())
        policy = json.loads(Path('/root/mgs-agent/data/ares/meta-ads/policies/openzedfinanzas_cc_es_hoa_v1.json').read_text())
        rules = json.loads(Path('/root/mgs-agent/data/ares/meta-ads/rules/openzedfinanzas_cc_es_intraday_v1.json').read_text())
        self.assertTrue(operation['smart_bidding_roi']['enabled'])
        self.assertEqual(policy['hoa']['target_cpmo_usd'], 2.0)
        self.assertEqual([r['id'] for r in rules['rules']], ['R1', 'R2', 'R3', 'R4', 'R5'])
        self.assertEqual(rules['rules'][0]['condition']['all'][1]['value'], 5.0)
        self.assertEqual(rules['rules'][3]['condition']['all'][2]['value'], 2.0)


if __name__ == '__main__':
    unittest.main()
