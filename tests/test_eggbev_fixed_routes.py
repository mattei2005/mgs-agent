import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/ares/discord/eggbev-fixed-routes.json"
OPERATION = ROOT / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
VERSIONED_CONFIG = ROOT / "profiles/ares-config.yaml"


class EggbevFixedRoutesTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.operation = json.loads(OPERATION.read_text(encoding="utf-8"))
        self.config = yaml.safe_load(VERSIONED_CONFIG.read_text(encoding="utf-8"))

    def test_exactly_six_unique_fixed_routes(self):
        routes = self.registry["routes"]
        self.assertEqual(len(routes), 6)
        ids = [str(route["thread_id"]) for route in routes.values()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            set(ids),
            {
                "1543280854024060999",
                "1543312825890381865",
                "1543333373945053184",
                "1541578606076231750",
                "1541578596253175858",
                "1541578556037927053",
            },
        )

    def test_preservation_policy_and_required_members(self):
        policy = self.registry["preservation_policy"]
        self.assertTrue(policy["never_create_replacement_when_id_is_recoverable"])
        self.assertTrue(policy["never_delete"])
        self.assertTrue(policy["archive_preserves_history"])
        self.assertEqual(policy["auto_archive_duration_minutes"], 10080)
        self.assertEqual(
            set(policy["required_member_ids"]),
            {"1055570806945620030", "1496296175014252634", "344196393512075265"},
        )

    def test_every_route_has_prompt_and_no_operational_banner_message(self):
        prompts = self.config["discord"]["channel_prompts"]
        self.assertFalse(self.registry["preservation_policy"]["pinned_route_messages"])
        for route in self.registry["routes"].values():
            thread_id = str(route["thread_id"])
            prompt_path = ROOT / route["prompt_file"]
            self.assertTrue(prompt_path.exists())
            self.assertTrue(prompt_path.read_text(encoding="utf-8").strip())
            self.assertEqual(prompt_path.read_text(encoding="utf-8").strip(), str(prompts[thread_id]).strip())
            self.assertNotIn("pin_marker", route)
            self.assertNotIn("pin_content", route)
            self.assertNotIn("canonical_message_id", route)

    def test_operation_route_ids_match_registry(self):
        contracts = self.operation["discord"]["route_contracts"]
        mapping = {
            "rules": "rules",
            "page_lead_guardrail": "page_lead_guardrail",
            "campaign_cloning": "campaign_cloning",
            "roas_cycle": "roas_cycle",
            "daily_reporting": "daily_reporting",
            "campaign_creation": "campaign_creation",
        }
        for registry_key, operation_key in mapping.items():
            self.assertEqual(
                str(self.registry["routes"][registry_key]["thread_id"]),
                str(contracts[operation_key]["thread_id"]),
            )


if __name__ == "__main__":
    unittest.main()
