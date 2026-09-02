#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "data/ares/meta-ads/strategy-families/chatpion-bot-messenger.json"
CONSUMERS = ROOT / "data/ares/meta-ads/strategy-families/chatpion-bot-messenger-consumers.json"
SKILL = ROOT / "profiles/ares-skills/growth/chatpion-bot-campaign-operations/SKILL.md"
OPERATION = ROOT / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
REGISTRY = ROOT / "data/ares/discord/eggbev-fixed-routes.json"


def load_module():
    path = ROOT / "scripts/ares-chatpion-bot-strategy-sync.py"
    spec = importlib.util.spec_from_file_location("chatpion_sync", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChatPionStrategyArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.family = json.loads(FAMILY.read_text())
        self.consumers = json.loads(CONSUMERS.read_text())
        self.operation = json.loads(OPERATION.read_text())
        self.registry = json.loads(REGISTRY.read_text())

    def test_family_skill_has_no_consumer_identity(self):
        content = SKILL.read_text()
        for forbidden in ("Eggbev", "FinanceAdX", "Lyzmo", "1034081997659047", "1541578622106865815"):
            self.assertNotIn(forbidden, content)
        self.assertIn("family", content.lower())
        self.assertIn("operation", content.lower())

    def test_family_contract_is_identity_free(self):
        serialized = FAMILY.read_text()
        for forbidden in ("Eggbev", "FinanceAdX", "Lyzmo", "1034081997659047", "1541578622106865815"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(self.family["family_id"], "chatpion_bot_messenger")
        self.assertFalse(self.family["thread_projection_policy"]["delete_messages"])

    def test_active_consumer_binding(self):
        consumer = self.consumers["consumers"]["Eggbev-US-CC-EN-BOT"]
        self.assertEqual(consumer["status"], "active")
        binding = self.operation["strategy_binding"]
        self.assertEqual(binding["family_id"], self.family["family_id"])
        self.assertEqual(self.operation["operation_skill"], "chatpion-bot-campaign-operations")

    def test_all_routes_resolve_to_generic_skill(self):
        expected = "chatpion-bot-campaign-operations"
        for route in self.registry["routes"].values():
            self.assertEqual(route["required_skill"], expected)
        for route in self.operation["discord"]["route_contracts"].values():
            self.assertEqual(route["required_skill"], expected)

    def test_operation_threshold_remains_operation_specific(self):
        threshold = self.operation["roas_cycle_policy"]["threshold"]
        self.assertEqual(threshold["current_value"], 0.36)
        self.assertIn("1544770844381679666", threshold["latest_change"]["source"])
        self.assertNotIn("threshold", self.family.get("defaults", {}))

    def test_route_change_always_includes_rules(self):
        module = load_module()
        self.assertEqual(module.route_set(["roas_cycle"]), ["roas_cycle", "rules"])
        self.assertEqual(module.route_set(["rules"]), ["rules"])

    def test_projection_edits_only_persisted_ares_message(self):
        from unittest import mock

        module = load_module()
        registry = {"consumers": {}}
        consumer = {"routes": {"rules": "thread-1"}, "projection_messages": {"rules": "message-1"}}
        responses = [
            (200, {"id": "message-1", "content": "old", "author": {"id": module.ARES_BOT_ID}}),
            (200, {}),
            (200, {"id": "message-1", "content": "new", "author": {"id": module.ARES_BOT_ID}}),
        ]
        with mock.patch.object(module, "request", side_effect=responses) as request:
            result = module.publish_projection("token", registry, "operation", consumer, "rules", "new")
        self.assertEqual(result["action"], "edited")
        self.assertTrue(result["readback_ok"])
        self.assertEqual(request.call_args_list[1].args[1], "PATCH")

    def test_prompt_sources_equal_versioned_config(self):
        config = yaml.safe_load((ROOT / "profiles/ares-config.yaml").read_text())
        prompts = config["discord"]["channel_prompts"]
        for route in self.registry["routes"].values():
            thread_id = str(route["thread_id"])
            source = (ROOT / route["prompt_file"]).read_text().strip()
            self.assertEqual(source, prompts[thread_id].strip())
            self.assertIn("chatpion-bot-campaign-operations", source)


if __name__ == "__main__":
    unittest.main()
