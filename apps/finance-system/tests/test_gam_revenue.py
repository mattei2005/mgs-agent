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
from finance_gam_revenue_sync import blocker_body, healthy_state_fields, missing_pair_is_overdue, run_spend_step, scheduled_slot, sender_allowed, should_skip_scheduled_run, spend_ready


class GamRevenuePlanTests(unittest.TestCase):
    def test_healthy_mailbox_result_clears_stale_failure_flags(self):
        self.assertEqual(
            healthy_state_fields(),
            {
                "failure_streak": 0,
                "blocked_after_five": False,
                "intervention_required": False,
                "last_failure": None,
            },
        )

    def test_mailbox_sender_allowlist_accepts_direct_google_and_forwarder(self):
        contract = {
            "mailbox": {
                "expected_senders": [
                    "admanager-noreply@google.com",
                    "contato@marketingdigitalad.com",
                ]
            }
        }
        self.assertTrue(sender_allowed("admanager-noreply@google.com", contract))
        self.assertTrue(sender_allowed("CONTATO@MARKETINGDIGITALAD.COM", contract))
        self.assertFalse(sender_allowed("unknown@example.com", contract))
        self.assertTrue(
            sender_allowed(
                "contato@marketingdigitalad.com",
                {"mailbox": {"expected_sender": "contato@marketingdigitalad.com"}},
            )
        )

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

    def test_completed_daily_cycle_suppresses_later_scheduled_slots_and_same_day_alert(self):
        complete = {"last_applied_date": "2026-09-15"}
        self.assertTrue(should_skip_scheduled_run(complete, "2026-09-15", scheduled_intake=True, finalize=False))
        self.assertTrue(should_skip_scheduled_run(complete, "2026-09-15", scheduled_intake=False, finalize=True))
        self.assertFalse(should_skip_scheduled_run(complete, "2026-09-15", scheduled_intake=False, finalize=False))
        self.assertFalse(should_skip_scheduled_run({"last_applied_date": "2026-09-14"}, "2026-09-15", scheduled_intake=True, finalize=False))
        self.assertFalse(missing_pair_is_overdue("2026-09-16", "2026-09-15"))
        self.assertTrue(missing_pair_is_overdue("2026-09-15", "2026-09-15"))
        self.assertTrue(missing_pair_is_overdue("2026-09-14", "2026-09-15"))

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

    def test_gamezone_historical_wrong_medium_is_forced_to_mgs(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_gamezonead_br", "g001-s", "c1", "x", 1]],
                [["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 2]],
            )
            self.assertEqual(plan["blockers"], [])
            game = next(entry for entry in plan["entries"] if entry["site"] == "GameZoneAd")
            self.assertEqual(game["source_manager_tag"], "g002-s")
            lineage = next(row for row in plan["lineage"] if row["site"] == "GameZoneAd")
            self.assertEqual(lineage["manager_route"], "forced_domain_exception")

    def test_boostingecon_is_always_mgs_bot_strategy(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_gamezonead_br", "g002-s", "c1", "x", 1]],
                [["2026-09-10", "pl_digital-trust_boostingecon_us", "g001-s", "c2", "x", 2]],
            )
            self.assertEqual(plan["blockers"], [])
            row = next(entry for entry in plan["entries"] if entry["site"] == "Boostingecon")
            self.assertEqual(row["source_vertical"], "us-cc-en")
            self.assertEqual(row["source_manager_tag"], "g002-d")
            lineage = next(item for item in plan["lineage"] if item["site"] == "Boostingecon")
            self.assertEqual(lineage["manager_route"], "forced_domain_exception")

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
                [["2026-09-10", "pl_digital-trust_cliquet_ca", "g002-d", "c1", "x", 1]],
                [["2026-09-10", "pl_digital-trust_eggbev_us", "g006-d", "c2", "x", 2]],
            )
            self.assertEqual(plan["blockers"][0]["type"], "new_domain_country")
            self.assertEqual(plan["blockers"][0]["country"], "ca")
            self.assertFalse(plan["summary"]["currency_totals_reconciled"])
            self.assertTrue(plan["summary"]["source_partition_reconciled"])
            self.assertTrue(plan["partial"])
            self.assertEqual(Decimal(plan["mapped_totals"]["USD"]) + Decimal(plan["blocked_totals"]["USD"]), Decimal(plan["source_totals"]["USD"]))

    def test_blocker_notice_is_compact_numbered_and_asks_only_for_missing_mapping(self):
        body = blocker_body(
            {
                "date": "2026-09-12",
                "entries": [{"id": "known"}],
                "summary": {"mapped_rows": 10, "blocked_rows": 2},
                "blockers": [
                    {
                        "type": "new_domain_country",
                        "domain": "cliquet.com",
                        "country": "br",
                        "currency": "CAD",
                        "rows": 1,
                        "revenue": "0.01683426772234963",
                        "placements": ["pl_digital-trust_cliquet_br"],
                    },
                    {
                        "type": "unknown_domain",
                        "domain": "portalrelevante",
                        "country": "us",
                        "currency": "CAD",
                        "rows": 1,
                        "revenue": "0.003935758639434707",
                        "placements": ["pl_digital-trust_portalrelevante_us"],
                        "candidate_domains": ["portalrelevante.com"],
                    },
                ],
            },
            confirmed_applied=True,
        )
        for required in (
            "1. cliquet.com / BR",
            "pl_digital-trust_cliquet_br",
            "falta somente a vertical",
            "2. portalrelevante / US",
            "pl_digital-trust_portalrelevante_us",
            "portalrelevante.com",
            "10 linhas com classificação comprovada foram aplicadas",
            "somente o complemento pendente",
            "próximos relatórios",
        ):
            self.assertIn(required, body)
        for forbidden in ("Fato:", "Diagnóstico:", "Lacuna:", "Recomendação:", "Pergunta:"):
            self.assertNotIn(forbidden, body)

    def test_20260915_permanent_domain_and_vertical_mappings(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-14", "pl_digital-trust_gamezonead_br", "g002-s", "c1", "x", 1]],
                [
                    ["2026-09-14", "pl_digital-trust_openzed_br", "-", "-", "-", 2],
                    ["2026-09-14", "pl_digital-trust_ducapes_us", "-", "-", "-", 3],
                    ["2026-09-14", "pl_digital-trust_escalatepower_us", "-", "-", "-", 4],
                    ["2026-09-14", "pl_digital-trust_wavesbee_us", "-", "-", "-", 5],
                ],
            )
            self.assertEqual(plan["blockers"], [])
            mapped = {entry["site"]: entry for entry in plan["entries"]}
            self.assertEqual((mapped["Openzed"]["source_vertical"], mapped["Openzed"]["source_manager_tag"]), ("br-car-br", "g003-d"))
            self.assertEqual((mapped["Ducapes"]["source_vertical"], mapped["Ducapes"]["source_manager_tag"]), ("us-cc-es", "g001-d"))
            self.assertEqual((mapped["Escalatepower"]["source_vertical"], mapped["Escalatepower"]["source_manager_tag"]), ("us-cc-en", "g002-d"))
            self.assertEqual((mapped["WavesBee"]["source_vertical"], mapped["WavesBee"]["source_manager_tag"]), ("us-cc-en", "g003-d"))
            self.assertEqual(plan["mapping_authority_message_id"], "1549411618570633227")
        rules = load_rules()
        self.assertEqual(rules["vertical_by_domain_country"]["finance.ducapes.com|us"], "us-cc-en")
        self.assertEqual(rules["dashboard_sites"]["finance.ducapes.com"], "Ducapes Finance")

    def test_daily_known_aliases_reuse_validated_september_mappings(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-10", "pl_digital-trust_gamezonead_br", "g002-s", "c1", "x", 1]],
                [
                    ["2026-09-10", "pl_digital-trust_cliquet_gb", "-", "-", "-", 2],
                    ["2026-09-10", "pl_digital-trust_cephyric_fr", "-", "-", "-", 3],
                    ["2026-09-10", "pl_digital-trust_topfeedfun_us", "-", "-", "-", 4],
                ],
            )
            self.assertEqual(plan["blockers"], [])
            mapped = {(entry["site"], entry["country"]): entry for entry in plan["entries"]}
            self.assertEqual(mapped[("Cliquet", "GB")]["source_vertical"], "gb-cc-en")
            self.assertEqual(mapped[("Cliquet", "GB")]["source_manager_tag"], "g002-d")
            self.assertEqual(mapped[("Cephyric", "FR")]["source_vertical"], "fr-cc-fr")
            self.assertEqual(mapped[("Cephyric", "FR")]["source_manager_tag"], "g002-d")
            self.assertEqual(mapped[("TopFeed", "US")]["source_vertical"], "us-cc-en")
            self.assertEqual(mapped[("TopFeed", "US")]["source_manager_tag"], "g004-d")

    def test_cliquet_br_is_permanent_car_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-12", "pl_digital-trust_gamezonead_br", "g002-s", "c1", "x", 1]],
                [["2026-09-12", "pl_digital-trust_cliquet_br", "-", "-", "-", Decimal("0.01683426772234963")]],
            )
            self.assertEqual(plan["blockers"], [])
            row = next(entry for entry in plan["entries"] if entry["site"] == "Cliquet")
            self.assertEqual(row["source_vertical"], "br-car-br")
            self.assertEqual(row["source_manager_tag"], "g002-d")

    def test_mavroa_us_is_permanent_shein_es_and_missing_manager_falls_back_to_mgs_direct(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-13", "pl_digital-trust_gamezonead_br", "g002-s", "c1", "x", 1]],
                [
                    ["2026-09-13", "pl_digital-trust_mavroa_us", "-", "-", "-", Decimal("0.001441427765333875")],
                    ["2026-09-13", "pl_digital-trust_mavroa_us", "g005-d", "c2", "x", Decimal("2")],
                ],
            )
            self.assertEqual(plan["blockers"], [])
            rows = sorted((entry["source_manager_tag"], entry["source_vertical"]) for entry in plan["entries"] if entry["site"] == "Mavroa")
            self.assertEqual(rows, [("g002-s", "us-shein-es"), ("g005-d", "us-shein-es")])

    def test_portal_main_and_finanzas_keep_language_split(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self.pair(
                td,
                [["2026-09-12", "pl_digital-trust_portalrelevantefinanzas_us", "-", "-", "-", 1]],
                [["2026-09-12", "pl_digital-trust_portalrelevante_us", "-", "-", "-", 2]],
            )
            self.assertEqual(plan["blockers"], [])
            mapped = {entry["site"]: entry for entry in plan["entries"]}
            self.assertEqual(mapped["Portal Relevante"]["source_vertical"], "us-cc-en")
            self.assertEqual(mapped["Portal Relevante"]["source_manager_tag"], "g001-d")
            self.assertEqual(mapped["Portal Relevante Finanzas"]["source_vertical"], "us-cc-es")
            self.assertEqual(mapped["Portal Relevante Finanzas"]["source_manager_tag"], "g001-d")

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
