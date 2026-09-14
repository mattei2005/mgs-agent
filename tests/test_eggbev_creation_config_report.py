import json
import subprocess
import unittest
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / "scripts/ares-eggbev-creation-config-report.py"
OP = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
OP_V3 = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json"
BOT_FAMILY = BASE / "data/ares/meta-ads/strategy-families/chatpion-bot-messenger.json"
DIRECT_FAMILY = BASE / "data/ares/meta-ads/strategy-families/direct-traffic-web-cbo.json"
DIRECT_CONSUMERS = BASE / "data/ares/meta-ads/strategy-families/direct-traffic-web-cbo-consumers.json"
ENGINE_CONFIG = BASE / "data/ares/meta-ads/engine-v3/config.json"
VERSIONED_CONFIG = BASE / "profiles/ares-config.yaml"
PROMPT = BASE / "data/ares/discord/thread-prompts/1541578556037927053.txt"


class EggbevCreationConfigReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        completed = subprocess.run(
            ["python3", str(SCRIPT), "--check"],
            cwd=BASE,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.report = completed.stdout

    def test_report_is_scoped_to_campaign_creation(self):
        required = [
            "1541578556037927053",
            "act_1034081997659047",
            "Eggbev-US-CC-EN-01-G006",
            "AUCTION",
            "SALES",
            "CBO",
            "HIGHEST_VOLUME",
            "AdG1",
            "1×1×3",
            "1×1×5",
            "America/New_York",
            "Primary text",
            "GET_STARTED_PAYLOAD",
            "eggbev-us-cc-en-messenger-welcome.json",
            "JSON-AGT",
            "ecc2204e5f94203434a212737bb0110ed3d53780478a701c80809d0807f819ad",
            "DIGITAL TRUST",
            "ACTIVE",
            "GET/readback",
            "pg_5024_dup01_live_validated_v1",
            "162 - Amy Shook - ENG - US - (pg_5024) C001 DUP01",
        ]
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, self.report)

    def test_report_does_not_return_global_agent_configuration(self):
        forbidden = [
            "gpt-5.6-sol",
            "openai-codex",
            "OAuth ChatGPT",
            "security.tirith",
            "Hermes v0",
            "Máximo de turnos",
            "global tool inventory",
        ]
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, self.report)

    def test_manual_placements_are_materialized_and_audience_network_is_forbidden(self):
        self.assertIn("payload exato materializado por readback", self.report)
        self.assertIn("Audience Network proibida", self.report)
        operation = json.loads(OP.read_text())
        payload = operation["campaign_creation_policy"]["manual_placements_payload"]
        self.assertEqual(payload["publisher_platforms"], ["facebook", "instagram", "messenger"])
        self.assertEqual(payload["audience_network"], "forbidden")
        self.assertNotIn("explore", payload["instagram_positions"])
        self.assertIn("explore_home", payload["instagram_positions"])

    def test_dup01_is_the_canonical_creation_model_without_media_reuse(self):
        operation = json.loads(OP.read_text())
        creation = operation["campaign_creation_policy"]
        self.assertEqual(creation["latest_standardization"]["canonical_creation_model"], "pg_5024_dup01_live_validated_v1")
        self.assertEqual(creation["copy_source_policy"]["default"], "pg_5024_dup01_live_validated_v1")
        self.assertEqual(creation["creation_reference_policy"]["default_reference_campaign"], "162 - Amy Shook - ENG - US - (pg_5024) C001 DUP01")
        self.assertIn("never reuse", creation["latest_standardization"]["application_scope"])
        self.assertIn("configuração, não mídia nem IDs", self.report)

    def test_canonical_messenger_json_file_is_mandatory_and_checked(self):
        operation = json.loads(OP.read_text())
        template = operation["campaign_creation_policy"]["message_template"]
        template_path = BASE / template["canonical_file"]
        self.assertTrue(template_path.is_file())
        self.assertEqual(template["semantic_sha256"], "ecc2204e5f94203434a212737bb0110ed3d53780478a701c80809d0807f819ad")
        self.assertIn("creative loads this file", template["injection_policy"])
        self.assertIn("compared directly", template["readback_policy"])
        self.assertEqual(template["template_name"], "JSON-AGT")
        self.assertIn("template_name=JSON-AGT", self.report)
        self.assertIn("Toda campanha nova carrega esse arquivo", self.report)

    def test_runtime_truth_is_explicit(self):
        self.assertIn("Runner Eggbev de criação construído: sim", self.report)
        self.assertIn("Conta cadastrada no Engine v3: sim", self.report)
        self.assertIn("Modo `from_zero_prestaged` onboarded para Eggbev: sim", self.report)
        self.assertIn("Write de criação habilitado: sim", self.report)
        self.assertIn("Publicação continua bloqueada pelo OK explícito e pela autoridade financeira vigente no execute", self.report)
        self.assertNotIn("USD 45 não é default", self.report)

    def test_route_contract_and_versioned_thread_prompt(self):
        operation = json.loads(OP.read_text())
        route = operation["discord"]["route_contracts"]["campaign_creation"]
        self.assertEqual(route["thread_id"], "1541578556037927053")
        self.assertEqual(route["configuration_report_script"], "scripts/ares-eggbev-creation-config-report.py")

        config = yaml.safe_load(VERSIONED_CONFIG.read_text())
        prompt = config["discord"]["channel_prompts"]["1541578556037927053"]
        self.assertIn("configuracao operacional da criacao Eggbev", prompt)
        self.assertIn("ares-eggbev-creation-config-report.py", prompt)
        self.assertIn("pg_5024_dup01_live_validated_v1", prompt)
        self.assertIn("todas as tres headlines", prompt)
        self.assertIn("nao enviar `explore`", prompt)
        prompt_source = PROMPT.read_text().strip()
        self.assertTrue(prompt_source.startswith("INSTRUCAO ESPECIFICA"))
        self.assertEqual(prompt.strip(), prompt_source)

    def test_speed_contract_keeps_bot_pages_user_scoped_and_media_on_demand(self):
        operation = json.loads(OP.read_text())
        operation_v3 = json.loads(OP_V3.read_text())
        family = json.loads(BOT_FAMILY.read_text())
        engine = json.loads(ENGINE_CONFIG.read_text())
        speed = operation["campaign_creation_speed_policy_20260914"]
        self.assertIn("never require importing", speed["page_model"])
        self.assertIn("approximately 3000 Pages", speed["page_model"])
        self.assertIn("exact ad account", speed["media_model"])
        self.assertIn("no global", speed["media_model"])
        self.assertEqual(operation_v3["hot_path_optimization"]["media_variants"], ["vertical", "square"])
        self.assertIn("no Business Manager Page import", operation_v3["hot_path_optimization"]["page_model"])
        self.assertIn("must not require importing", family["scale_invariants"]["page_assignment"])
        self.assertEqual(engine["accounts"]["1034081997659047"]["marketing_api_access_tier"], "standard_access")

    def test_direct_traffic_parent_family_contains_shein_and_car_without_cross_inheritance(self):
        family = json.loads(DIRECT_FAMILY.read_text())
        consumers = json.loads(DIRECT_CONSUMERS.read_text())
        self.assertEqual(family["family_id"], "direct_traffic_web_cbo")
        self.assertFalse(family["shared_campaign_mechanics"]["global_meta_prestage"])
        self.assertTrue(family["page_policy"]["business_manager_assignment_supported"])
        self.assertTrue(family["isolation"]["no_cross_inheritance"])
        self.assertEqual(
            set(consumers["consumers"]),
            {"SHEIN-US-DIRECT", "Creditoparaveiculo-BR-CAR-BR"},
        )
        self.assertEqual(consumers["consumers"]["SHEIN-US-DIRECT"]["media_variants"], ["vertical"])
        self.assertEqual(consumers["consumers"]["Creditoparaveiculo-BR-CAR-BR"]["media_variants"], ["vertical", "square"])


if __name__ == "__main__":
    unittest.main()
