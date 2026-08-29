import json
import unittest
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
OP = BASE / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json'
PROMPT = BASE / 'data/ares/discord/thread-prompts/1543312825890381865.txt'
VERSIONED_CONFIG = BASE / 'profiles/ares-config.yaml'


class EggbevPageLeadThreadRouteTests(unittest.TestCase):
    def test_exact_thread_prompt_is_persisted_and_active(self):
        prompt_source = PROMPT.read_text().strip()
        config = yaml.safe_load(VERSIONED_CONFIG.read_text())
        active = config['discord']['channel_prompts']['1543312825890381865'].strip()
        self.assertEqual(active, prompt_source)
        self.assertIn('Limite de Leads', active)
        self.assertIn('configuracao operacional desta rota', active)
        self.assertIn('freshness', active.lower())

    def test_operation_contains_a_dedicated_route_contract(self):
        operation = json.loads(OP.read_text())
        route = operation['discord']['route_contracts']['page_lead_guardrail']
        self.assertEqual(route['thread_id'], '1543312825890381865')
        self.assertTrue(route['exact_thread_prompt_active'])
        self.assertEqual(route['canonical_prompt_source'], 'data/ares/discord/thread-prompts/1543312825890381865.txt')

    def test_parent_channel_prompt_points_to_current_rules_thread(self):
        config = yaml.safe_load(VERSIONED_CONFIG.read_text())
        parent = config['discord']['channel_prompts']['1539422731727147079']
        self.assertIn('regras 1543280854024060999', parent)
        self.assertNotIn('regras 1541578622106865815', parent)


if __name__ == '__main__':
    unittest.main(verbosity=2)
