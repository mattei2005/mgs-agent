from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from ares_campaign_v3.adapters import build_cpv_manifest
from ares_campaign_v3.daily_cpv import enforce_budget_cap, requested_campaign_count
from ares_campaign_v3.media_registry import MediaRegistry


OPERATION_PATH = ROOT / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json"
ACCOUNT_PATH = ROOT / "data/ares/meta-ads/accounts/1046241194533786.json"


class CpvInitialBudgetPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.operation = json.loads(OPERATION_PATH.read_text(encoding="utf-8"))
        self.account = json.loads(ACCOUNT_PATH.read_text(encoding="utf-8"))["accounts"][0]

    def test_canonical_policy_uses_usd25_only_for_new_campaigns(self) -> None:
        policy = self.operation["daily_budget_policy"]
        routine = self.operation["daily_new_campaign_routine"]
        self.assertEqual(policy["new_campaign_initial_budget_usd"], 25.0)
        self.assertEqual(routine["default_campaign_initial_budget_usd"], 25)
        self.assertEqual(routine["default_campaign_count_when_not_otherwise_specified"], 4)
        self.assertEqual(self.account["daily_creation_authorized"]["budget_usd_each"], 25)
        self.assertEqual(self.account["daily_budget_policy"]["new_campaign_initial_budget_usd"], 25.0)
        self.assertIn("new campaigns only", policy["new_campaign_initial_budget_rule"]["scope"])

    def test_normal_usd100_pool_plans_four_new_campaigns_at_usd25(self) -> None:
        minimal = {
            "daily_new_campaign_routine": {
                "new_campaign_budget_pool_usd": self.operation["daily_new_campaign_routine"]["new_campaign_budget_pool_usd"],
                "default_campaign_initial_budget_usd": self.operation["daily_new_campaign_routine"]["default_campaign_initial_budget_usd"],
            },
            "daily_budget_policy": self.operation["daily_budget_policy"],
        }
        count = requested_campaign_count(minimal, date(2026, 8, 28))
        self.assertEqual(count, 4)
        budget = enforce_budget_cap([], count, minimal)
        self.assertEqual(budget["initial_minor"], 2500)
        self.assertEqual(budget["new_minor"], 10000)
        self.assertEqual(budget["selected_count"], 4)

    def test_manifest_materializes_configured_usd25_budget(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cpv-budget-25-") as raw:
            registry = MediaRegistry(Path(raw) / "media-registry.json")
            assets = []
            for index in range(3):
                asset_id = f"asset-{index}"
                checksum = f"checksum-{index}"
                registry.register(
                    account_id="1046241194533786",
                    asset_id=asset_id,
                    checksum=checksum,
                    vertical_video_id=f"vertical-{index}",
                    square_video_id=f"square-{index}",
                    ready=True,
                    upload_edge="ad_account_advideos",
                    association_verified=True,
                )
                assets.append(
                    {
                        "asset_id": asset_id,
                        "checksum": checksum,
                        "canonical_filename": f"CAR_BR_BR_VID_TEST_PV_{index + 1:03d}.mp4",
                    }
                )
            templates = [
                {
                    "source_ad_id": f"source-ad-{index}",
                    "creative_payload": {
                        "object_story_spec": {"page_id": "621037101089579"},
                        "asset_feed_spec": {"videos": []},
                    },
                }
                for index in range(3)
            ]
            payload = build_cpv_manifest(
                registry=registry,
                asset_refs=assets,
                campaign_numbers=[32],
                operational_date="2026-08-28",
                request_id="cpv-budget-usd25-test",
                source_selections=[
                    {
                        "vehicle_type": "CARRO",
                        "source_campaign_id": "source-campaign",
                        "source_adset_id": "source-adset",
                        "templates": templates,
                    }
                ],
                status="ACTIVE",
                daily_budget_minor=2500,
            )
            self.assertEqual(payload["campaigns"][0]["campaign_updates"]["daily_budget"], "2500")


if __name__ == "__main__":
    unittest.main()
