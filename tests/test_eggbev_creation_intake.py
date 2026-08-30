import argparse
import datetime as dt
import importlib.util
import unittest
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ares-eggbev-creation-intake-simulate.py"
SPEC = importlib.util.spec_from_file_location("eggbev_creation_intake", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EggbevCreationIntakeTests(unittest.TestCase):
    def make_args(self, **overrides):
        values = {
            "page_token": "pg_5024",
            "campaign_count": 3,
            "creatives_per_campaign": 3,
            "source_folder": "cc en us",
            "daily_budget_usd": None,
            "creation_reference": None,
            "primary_text": None,
            "headline": None,
            "description": None,
            "cta": None,
            "campaign_name_template": None,
            "ad_name_template": None,
            "tracking_reference": None,
            "placements_reference": None,
            "live_page_check": True,
            "output": None,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def page_fixture(self):
        return {
            "page_token": "pg_5024",
            "smart_bidding_page_rows": 1,
            "unique_page_identity": True,
            "page_id_present": True,
            "meta_page_read_http": 200,
            "meta_page_accessible": True,
            "page_name": "Amy Shook",
            "leads_snapshot": 65,
            "messenger_source_ready": False,
            "messenger_source_reason": "smart_bidding_freshness_unverifiable",
            "existing_campaign_name_matches": 0,
        }

    def test_next_midnight_uses_new_york_and_next_calendar_day(self):
        now = dt.datetime(2026, 8, 29, 20, 0, tzinfo=ZoneInfo("America/New_York"))
        self.assertEqual(MODULE.next_midnight(now), "2026-08-30T00:00:00-04:00")

    @mock.patch.object(MODULE, "live_page_check")
    def test_minimal_request_applies_defaults_and_requires_nine_unique_assets(self, page_check):
        page_check.return_value = self.page_fixture()
        result = MODULE.simulate(self.make_args())
        self.assertEqual(result["request"]["required_unique_assets"], 9)
        self.assertEqual(result["defaults_applied"]["structure"], "3 campaigns x 1 ad set x 3 ads")
        self.assertFalse(result["defaults_applied"]["creative_reuse_across_campaigns"])
        self.assertTrue(result["defaults_applied"]["start_time"].endswith("T00:00:00-04:00"))
        self.assertEqual(result["status"], "NEEDS_INPUT")
        self.assertEqual(
            result["missing_user_inputs"],
            ["daily_budget_usd_per_campaign", "ad_names_or_approved_ad_name_template"],
        )
        self.assertEqual(result["meta_writes"], 0)
        self.assertEqual(result["reservations_written"], 0)

    @mock.patch.object(MODULE, "live_page_check")
    def test_complete_user_inputs_are_ready_for_scoped_prestage(self, page_check):
        page_check.return_value = self.page_fixture()
        result = MODULE.simulate(
            self.make_args(
                daily_budget_usd=50.0,
                creation_reference="approved-fixture-reference",
                ad_name_template="AD {index}",
            )
        )
        self.assertEqual(result["missing_user_inputs"], [])
        self.assertEqual(result["status"], "READY_FOR_SCOPED_RECONCILIATION_AND_PRESTAGE")
        self.assertEqual(result["readiness_blockers"], [])
        self.assertIn("prestage to act_1034081997659047/advideos", result["automatic_request_steps_pending"])
        self.assertEqual(result["meta_writes"], 0)
        self.assertEqual(result["reservations_written"], 0)

    def test_inventory_is_ready_but_not_globally_released(self):
        result = MODULE.inventory_summary(9)
        self.assertGreaterEqual(result["technically_ready_clean"], 9)
        self.assertEqual(result["ares_eligible_now"], 0)
        self.assertFalse(result["sufficient_eligible_now"])
        self.assertTrue(result["request_can_trigger_scoped_release_review"])


if __name__ == "__main__":
    unittest.main()
