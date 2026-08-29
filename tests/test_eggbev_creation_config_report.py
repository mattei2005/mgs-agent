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
            "DIGITAL TRUST",
            "ACTIVE",
            "GET/readback",
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

    def test_unresolved_placements_are_fail_closed(self):
        self.assertIn("lista exata de posições ainda não está materializada", self.report)
        self.assertIn("bloqueia manifest/write", self.report)
        self.assertIn("não copiar placements de outra operação", self.report)

    def test_runtime_truth_is_explicit(self):
        self.assertIn("Runner Eggbev de criação construído: não", self.report)
        self.assertIn("Conta cadastrada no Engine v3: não", self.report)
        self.assertIn("Write de criação habilitado: não", self.report)

    def test_route_contract_and_versioned_thread_prompt(self):
        operation = json.loads(OP.read_text())
        route = operation["discord"]["route_contracts"]["campaign_creation"]
        self.assertEqual(route["thread_id"], "1541578556037927053")
        self.assertEqual(route["configuration_report_script"], "scripts/ares-eggbev-creation-config-report.py")

        config = yaml.safe_load(VERSIONED_CONFIG.read_text())
        prompt = config["discord"]["channel_prompts"]["1541578556037927053"]
        self.assertIn("configuracao operacional da criacao Eggbev", prompt)
        self.assertIn("ares-eggbev-creation-config-report.py", prompt)
        prompt_source = PROMPT.read_text().strip()
        self.assertTrue(prompt_source.startswith("INSTRUCAO ESPECIFICA"))
        self.assertEqual(prompt.strip(), prompt_source)


if __name__ == "__main__":
    unittest.main()
