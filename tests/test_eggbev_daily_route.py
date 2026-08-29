import json
import subprocess
import unittest
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / "scripts/ares-eggbev-daily-config-report.py"
OP = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
ACCOUNT = BASE / "data/ares/meta-ads/accounts/1034081997659047.json"
VERSIONED_CONFIG = BASE / "profiles/ares-config.yaml"
PROMPT = BASE / "data/ares/discord/thread-prompts/1541578596253175858.txt"


class EggbevDailyRouteTests(unittest.TestCase):
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
        cls.operation = json.loads(OP.read_text())
        cls.account = json.loads(ACCOUNT.read_text())["accounts"][0]

    def test_schedule_and_period_semantics(self):
        for value in ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]:
            self.assertIn(value, self.report)
        self.assertIn("fechamento anterior + referência parcial atual", self.report)
        self.assertIn("Relatório sob demanda a qualquer momento: sim", self.report)

    def test_runtime_is_read_only_and_not_automated(self):
        required = [
            "Modo: `read_only`",
            "Runner construído: sim",
            "Consulta sob demanda: sim",
            "Post automático habilitado: não",
            "Cron Diário habilitado: não",
            "Writes habilitados: não",
        ]
        for value in required:
            self.assertIn(value, self.report)

    def test_report_discloses_renderer_coverage_and_remaining_limitations(self):
        required = [
            "freshness",
            "`N/D`",
            "currently effective ACTIVE campaigns",
            "Limite silencioso de linhas: não",
            "Truncamento do nome da campanha: não",
            "full name",
            "current status",
            "start_time America/New_York",
            "Cost per messaging conversation started",
            "UTM_CAMPAIGN",
            "FB_PAGE_ID",
            "RPS bruto = `REVENUE × 1.000 / SESSIONS`",
            "real ROI and estimated ROI remain N/D",
            "25 campanhas, todas preservadas",
        ]
        for value in required:
            self.assertIn(value, self.report)

    def test_daily_scope_excludes_global_and_other_route_detail(self):
        forbidden = [
            "gpt-5.6-sol",
            "openai-codex",
            "OAuth ChatGPT",
            "Spend > US$2",
            "LEADS > 5.000",
            "GET_STARTED_PAYLOAD",
            "ADS ON 1.1",
        ]
        for value in forbidden:
            self.assertNotIn(value, self.report)

    def test_route_contract_and_versioned_prompt_match_source(self):
        route = self.operation["discord"]["route_contracts"]["daily_reporting"]
        self.assertEqual(route["thread_id"], "1541578596253175858")
        self.assertEqual(route["live_report_script"], "scripts/ares-eggbev-daily-report.py")
        self.assertFalse(self.account["runtime_routes"]["daily_reporting"]["post_enabled"])

        config = yaml.safe_load(VERSIONED_CONFIG.read_text())
        prompt = config["discord"]["channel_prompts"]["1541578596253175858"].strip()
        self.assertEqual(prompt, PROMPT.read_text().strip())


if __name__ == "__main__":
    unittest.main()
