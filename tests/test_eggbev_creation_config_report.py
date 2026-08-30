import json
import subprocess
import unittest
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / "scripts/ares-eggbev-creation-config-report.py"
OP = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
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


if __name__ == "__main__":
    unittest.main()
