import importlib.util
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CRON = load_module('ares_meta_cron_runner_v2_test', '/root/mgs-agent/scripts/ares-meta-cron-runner.py')
HOA = load_module('ares_meta_hoa_manager_v2_test', '/root/mgs-agent/scripts/ares-meta-hoa-manager.py')
BASE = Path('/root/mgs-agent/data/ares/meta-ads')
OP = json.loads((BASE / 'operations' / 'OpenzedFinanzas-CC-ES.json').read_text())
RULES = json.loads((BASE / 'rules' / f"{OP['ruleset']}.json").read_text())
POLICY = json.loads(Path(OP['hoa_policy']['policy_path']).read_text())
RULE_BY_ID = {r['id']: r for r in RULES['rules']}


class RulesetV2Tests(unittest.TestCase):
    def setUp(self):
        self.tz = ZoneInfo('Europe/Madrid')
        self.campaign = {
            'id': 'c1',
            'name': 'Elena Santana - ES - ESP - (pg_22091) - 1',
            'status': 'ACTIVE',
            'effective_status': 'ACTIVE',
            'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
            'created_time': '2026-06-20T00:00:00+0000',
        }

    def test_config_values_and_write_gate(self):
        self.assertEqual(RULES['baseline']['provisional_usd'], 1.15)
        self.assertEqual(POLICY['hoa']['target_cpmo_usd'], 1.30)
        self.assertEqual(POLICY['bad_day_gates']['minimum_spend_usd'], 10.0)
        self.assertEqual(POLICY['bad_day_gates']['minimum_MO'], 5)
        self.assertEqual(POLICY['bad_day_gates']['complete_days_window'], 3)
        self.assertFalse(RULE_BY_ID['R5']['enabled'])
        self.assertEqual(RULES['reactivate_all']['scope'], 'paused_by_ares_rule_only')
        self.assertFalse(RULES['write_enabled'])
        self.assertFalse(OP['management_scope']['write_enabled'])

    def test_r4_accepts_meta_lowest_cost_without_cap(self):
        matched, excluded = CRON.rule_matches(
            RULE_BY_ID['R4'], self.campaign,
            {'spend': 10.0, 'MO': 5.0, 'CPMO': 1.76}, OP, self.tz,
        )
        self.assertTrue(matched)
        self.assertIsNone(excluded)

    def test_cost_cap_is_excluded_from_cost_pause(self):
        campaign = dict(self.campaign, bid_strategy='COST_CAP')
        for rule_id, metrics in [
            ('R1', {'spend': 4.0, 'MO': 0.0, 'CPMO': None}),
            ('R2', {'spend': 4.5, 'MO': 1.0, 'CPMO': 4.5}),
            ('R3', {'spend': 10.0, 'MO': 4.0, 'CPMO': 2.5}),
            ('R4', {'spend': 10.0, 'MO': 5.0, 'CPMO': 2.0}),
        ]:
            matched, excluded = CRON.rule_matches(RULE_BY_ID[rule_id], campaign, metrics, OP, self.tz)
            self.assertFalse(matched)
            self.assertEqual(excluded, 'COST_CAP_no_cost_pause')

    def test_two_distinct_consecutive_checkpoints_required(self):
        state = {}
        start = datetime(2026, 7, 13, 10, 0, tzinfo=self.tz)
        ids = ['R1', 'R2', 'R3', 'R4']
        self.assertEqual(CRON.apply_persistence(state, 'c1', 'R1', ids, start, 30), 1)
        self.assertEqual(CRON.apply_persistence(state, 'c1', 'R1', ids, start, 30), 1)
        self.assertEqual(CRON.apply_persistence(state, 'c1', 'R1', ids, start + timedelta(minutes=30), 30), 2)
        self.assertEqual(CRON.apply_persistence(state, 'c1', None, ids, start + timedelta(minutes=60), 30), 0)
        self.assertEqual(CRON.apply_persistence(state, 'c1', 'R1', ids, start + timedelta(minutes=90), 30), 1)
        same_checkpoint_state = {}
        self.assertEqual(CRON.apply_persistence(same_checkpoint_state, 'c2', 'R1', ids, start, 30), 1)
        self.assertEqual(CRON.apply_persistence(same_checkpoint_state, 'c2', None, ids, start, 30), 0)
        self.assertEqual(CRON.apply_persistence(same_checkpoint_state, 'c2', 'R1', ids, start, 30), 1)

    def test_hoa_bad_day_requires_all_three_gates(self):
        self.assertEqual(HOA.classify_bad_day({'spend': 10, 'MO': 5, 'CPMO': 1.31}, 10, 5, 1.30), (True, 'CPMO alto'))
        self.assertFalse(HOA.classify_bad_day({'spend': 9.99, 'MO': 5, 'CPMO': 2.0}, 10, 5, 1.30)[0])
        self.assertFalse(HOA.classify_bad_day({'spend': 10, 'MO': 4, 'CPMO': 2.0}, 10, 5, 1.30)[0])
        self.assertFalse(HOA.classify_bad_day({'spend': 10, 'MO': 5, 'CPMO': 1.30}, 10, 5, 1.30)[0])

    def test_projection_and_budget_gate_helpers(self):
        midnight_half = datetime(2026, 7, 13, 0, 30, tzinfo=self.tz)
        self.assertEqual(CRON.campaign_budget_usd({'daily_budget': '2500'}), 25.0)
        self.assertEqual(CRON.spend_projection_usd(5.0, midnight_half), 240.0)
        self.assertEqual(CRON.reactivation_gate('paused_by_ares_rule', 'paused_by_ares_rule', 25, 25, 5, 12, 125, 300), (True, 'eligible'))
        self.assertEqual(CRON.reactivation_gate('unknown', 'paused_by_ares_rule', 25, 25, 5, 12, 125, 300), (False, 'pause_origin_not_allowed'))
        self.assertEqual(CRON.reactivation_gate('paused_by_ares_rule', 'paused_by_ares_rule', 25, 25, 12, 12, 125, 300), (False, 'active_campaign_count_cap'))
        self.assertEqual(CRON.reactivation_gate('paused_by_ares_rule', 'paused_by_ares_rule', 25, 25, 5, 12, 290, 300), (False, 'projected_spend_cap'))


if __name__ == '__main__':
    unittest.main()
