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
        policy = self.operation["daily_reporting_policy"]
        self.assertEqual(policy["approved_times"], ["08:00"])
        self.assertEqual(policy["schedule_status"], "daily_design_approved_0800_et_cron_and_post_pending_separate_enable")
        self.assertIn("Horário desenhado e aprovado para o Diário: `08:00 America/New_York`", self.report)
        self.assertIn("fechamento completo de D-1", PROMPT.read_text())
        self.assertIn("cron e post automático permanecem desabilitados", self.report)
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
            "currently effective ACTIVE campaign",
            "Limite silencioso de linhas: não",
            "Truncamento do nome da campanha: não",
            "full name",
            "current status",
            "start_time America/New_York",
            "Cost per messaging conversation started",
            "UTM_CAMPAIGN",
            "FB_PAGE_ID",
            "RPS, CPM, EPC e demais métricas de monetização preferem campos diretos",
            "vertical, Messenger Pages or domain",
            "implementation gap, not a Smart Bidding data-availability limitation",
            "25 campanhas, todas preservadas",
            "tabela única completa",
            "Baseline: até 7 snapshots; mínimo de 3",
            "atenção a partir de 30% abaixo; crítico a partir de 40% abaixo",
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
        self.assertFalse(self.account["runtime_routes"]["daily_reporting"]["cron_enabled"])
        self.assertFalse(self.account["runtime_routes"]["daily_reporting"]["schedule_enabled"])

        config = yaml.safe_load(VERSIONED_CONFIG.read_text())
        prompt = config["discord"]["channel_prompts"]["1541578596253175858"].strip()
        self.assertEqual(prompt, PROMPT.read_text().strip())

    def test_anomaly_detector_is_eggbev_read_only(self):
        detector = self.operation["daily_reporting_policy"]["revenue_anomaly_detection"]
        self.assertEqual(detector["scope"], "Eggbev Daily only; no CPV source, runner, schedule, prompt or policy is read or modified")
        self.assertEqual(detector["baseline_days"], 7)
        self.assertEqual(detector["minimum_comparable_samples"], 3)
        self.assertEqual(detector["warning_drop_percent"], 30)
        self.assertEqual(detector["critical_drop_percent"], 40)
        self.assertFalse(detector["writes"]["meta"])
        self.assertFalse(detector["writes"]["smart_bidding"])
        self.assertFalse(detector["writes"]["budget"])


if __name__ == "__main__":
    unittest.main()
