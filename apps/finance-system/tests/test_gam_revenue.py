import json
import datetime as dt
import pathlib
import tempfile
import unittest
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from openpyxl import Workbook

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from gam_revenue import REPORTS, build_plan, load_rules
from finance_gam_revenue_sync import run_spend_step, scheduled_slot, spend_ready


class GamRevenuePlanTests(unittest.TestCase):
    def test_intake_and_finalize_slots_and_spend_gate(self):
        contract = {"poll_minutes": [3, 13, 22, 28], "finalize_minutes": [22, 31, 41]}
        self.assertTrue(scheduled_slot(dt.datetime(2026, 9, 12, 8, 3), contract, intake=True, finalize=False))
        self.assertFalse(scheduled_slot(dt.datetime(2026, 9, 12, 9, 3), contract, intake=True, finalize=False))
        self.assertTrue(scheduled_slot(dt.datetime(2026, 9, 12, 9, 22), contract, intake=False, finalize=True))
        self.assertFalse(scheduled_slot(dt.datetime(2026, 9, 12, 8, 22), contract, intake=False, finalize=True))
        with self.assertRaises(ValueError):
            scheduled_slot(dt.datetime(2026, 9, 12, 8, 3), contract, intake=True, finalize=True)
        self.assertTrue(spend_ready({"last_status": "ok", "last_until": "2026-09-11"}, "2026-09-11"))
        self.assertFalse(spend_ready({"last_status": "ok", "last_until": "2026-09-10"}, "2026-09-11"))
        self.assertFalse(spend_ready({"last_status": "failed", "last_until": "2026-09-11"}, "2026-09-11"))

    def make_book(self, root, key, rows):
        cfg = REPORTS[key]
        path = pathlib.Path(root) / cfg["attachment"]
        book = Workbook()
        props = book.active
        assert props is not None
        props.title = "Properties" if key == "usd" else "Propriedades"
        labels = (
            [("Report name", cfg["report_name"]), ("Report currency", cfg["currency"]), ("Publisher network", cfg["network"]), ("Time zone", "America/Sao_Paulo"), ("Date range", "Sep 10, 2026")]
            if key == "usd"
            else [("Nome do relatório", cfg["report_name"]), ("Moeda do relatório", cfg["currency"]), ("Rede do publisher", cfg["network"]), ("Fuso horário", "America/Sao_Paulo"), ("Período", "set. 10, 2026")]
        )
        for row in labels:
            props.append(row)
        data = book.create_sheet(cfg["report_name"])
        data.append(["Date" if key == "usd" else "Data", "Placement" if key == "usd" else "Posição", "utm_medium (utm_medium)", "utm_campaign (utm_campaign)", "utm_content (utm_content)", "Ad Exchange revenue" if key == "usd" else "Receita do Ad Exchange"])
        for row in rows:
            data.append(row)
        book.save(path)
        return path

    def pair(self, root, usd_rows, cad_rows, rules=None):
        paths = {"usd": self.make_book(root, "usd", usd_rows), "cad": self.make_book(root, "cad", cad_rows)}
        rules_path = pathlib.Path(root) / "rules.json"
        rules_path.write_text(json.dumps(rules or load_rules()))
        return build_plan(paths, rules_path=rules_path)

    def test_known_rows_reconcile_and_preserve_strategy(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_creditoparaveiculo_br", "g003-s", "c1", "x", 10]],
                [["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 20]],
            )
            self.assertEqual(plan["blockers"], [])
            self.assertEqual(plan["source_totals"], {"CAD": "20", "USD": "10"})
            self.assertEqual({entry["source_manager_tag"] for entry in plan["entries"]}, {"g003-s", "g006-d"})
            self.assertTrue(plan["summary"]["currency_totals_reconciled"])

    def test_missing_medium_uses_site_owner_and_observed_operation(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_creditoparaveiculo_br", "g002-s", "c1", "x", 1]],
                [
                    ["2026-09-10", "pl_digital-trust_eggbev_us", "g001-s", "c2", "x", 2],
                    ["2026-09-10", "pl_digital-trust_eggbev_us", "-", "c3", "x", 3],
                ],
            )
            self.assertEqual(plan["blockers"], [])
            eggbev = sorted(entry["source_manager_tag"] for entry in plan["entries"] if entry["site"] == "Eggbev")
            self.assertEqual(eggbev, ["g001-s", "g006-s"])

    def test_valid_medium_preserves_guest_manager_on_another_managers_site(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_gamezonead_br", "g001-s", "c1", "x", 1]],
                [["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 2]],
            )
            self.assertEqual(plan["blockers"], [])
            game = next(entry for entry in plan["entries"] if entry["site"] == "GameZoneAd")
            self.assertEqual(game["source_manager_tag"], "g001-s")

    def test_openzed_missing_medium_returns_to_isliago_not_guest_manager(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_creditoparaveiculo_br", "g002-s", "c1", "x", 1]],
                [
                    ["2026-09-10", "pl_digital-trust_openzed_us", "g001-d", "c2", "x", 2],
                    ["2026-09-10", "pl_digital-trust_openzed_us", "-", "c3", "x", 3],
                ],
            )
            self.assertEqual(plan["blockers"], [])
            tags = sorted(entry["source_manager_tag"] for entry in plan["entries"] if entry["site"] == "Openzed")
            self.assertEqual(tags, ["g001-d", "g003-d"])

    def test_new_country_blocks_without_invention(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_cliquet_gb", "g002-d", "c1", "x", 1]],
                [["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 2]],
            )
            self.assertEqual(plan["blockers"][0]["type"], "new_domain_country")
            self.assertEqual(plan["blockers"][0]["country"], "gb")
            self.assertFalse(plan["summary"]["currency_totals_reconciled"])

    def test_shared_site_missing_medium_uses_mgs_with_observed_operation(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_creditoparaveiculo_br", "g002-s", "c1", "x", 1]],
                [
                    ["2026-09-10", "pl_digital-trust_yolokfx_us", "g003-d", "c2", "x", 2],
                    ["2026-09-10", "pl_digital-trust_yolokfx_us", "-", "-", "x", Decimal("1.25")],
                ],
            )
            self.assertEqual(plan["blockers"], [])
            yolo = next(x for x in plan["entries"] if x["site"] == "Yolokfx" and x["source_manager_tag"] == "g002-d")
            self.assertEqual(yolo["source_manager_tag"], "g002-d")
            self.assertEqual(yolo["gross"], "1.25")

    def test_noncanonical_medium_without_manager_uses_owner_and_operation(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_creditoparaveiculo_br", "gestor-x-s", "c1", "x", 1]],
                [["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 2]],
            )
            self.assertEqual(plan["blockers"], [])
            row = next(x for x in plan["lineage"] if x["site"] == "CreditoParaVeiculo")
            self.assertEqual(row["manager_tag"], "g002-s")
            self.assertEqual(row["source_medium"], "gestor-x-s")

    def test_missing_medium_with_mixed_operations_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_creditoparaveiculo_br", "g002-s", "c1", "x", 1]],
                [
                    ["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 2],
                    ["2026-09-10", "pl_digital-trust_eggbev_us", "g006-s", "c3", "x", 3],
                    ["2026-09-10", "pl_digital-trust_eggbev_us", "-", "c4", "x", 4],
                ],
            )
            self.assertEqual(plan["blockers"][0]["type"], "ambiguous_missing_manager_operation")

    def test_run_spend_step_uses_exact_revenue_date_and_validates_state(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = pathlib.Path(td) / "spend-state.json"
            state_path.write_text(json.dumps({"last_status": "waiting", "last_until": "2026-09-09"}))
            def complete(*_args, **_kwargs):
                state_path.write_text(json.dumps({"last_status": "ok", "last_until": "2026-09-10"}))
                return type("Run", (), {"returncode": 0, "stdout": json.dumps({"pass": True, "until": "2026-09-10"}) + "\n", "stderr": ""})()
            with patch("finance_gam_revenue_sync.subprocess.run", side_effect=complete) as run:
                result = run_spend_step("2026-09-10", state_path=state_path)
            self.assertTrue(result["pass"])
            self.assertEqual(result["state"]["last_until"], "2026-09-10")
            self.assertIn("--pipeline-date", run.call_args.args[0])
            self.assertIn("2026-09-10", run.call_args.args[0])

    def test_approved_country_override_changes_country_and_vertical_together(self):
        with tempfile.TemporaryDirectory() as td:
            rules = deepcopy(load_rules())
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_gamezonead_mx", "g002-s", "c1", "x", 1]],
                [["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 2]],
                rules,
            )
            self.assertEqual(plan["blockers"], [])
            entry = next(x for x in plan["entries"] if x["site"] == "GameZoneAd")
            self.assertEqual(entry["source_vertical"], "br-game-br")
            self.assertEqual(entry["country"], "BR")
            self.assertEqual(entry["source_manager_tag"], "g002-s")


if __name__ == "__main__":
    unittest.main()
