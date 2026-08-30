from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.ares_campaign_v3.eggbev_create import (
    ACCOUNT_ID,
    FACEBOOK_POSITIONS,
    INSTAGRAM_POSITIONS,
    MESSENGER_POSITIONS,
    build_eggbev_from_zero_manifest,
)
from scripts.ares_campaign_v3.engine import CampaignEngine
from scripts.ares_campaign_v3.media_registry import MediaRegistry
from scripts.ares_campaign_v3.planning import Planner
from scripts.ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from scripts.ares_campaign_v3.schema import Manifest, ManifestError
from scripts.ares_campaign_v3.transport import FakeBatchTransport

BASE = Path("/root/mgs-agent")
CONFIG = json.loads((BASE / "data/ares/meta-ads/engine-v3/config.json").read_text())


class EggbevFromZeroV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = MediaRegistry(Path(self.tmp.name) / "media.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _assets(self, count: int) -> list[dict[str, str]]:
        refs = []
        for index in range(count):
            asset_id = f"eggbev_asset_{index + 1:02d}"
            checksum = f"checksum-{index + 1:02d}"
            self.registry.register(
                account_id=ACCOUNT_ID,
                asset_id=asset_id,
                checksum=checksum,
                vertical_video_id=f"vertical-{index + 1:02d}",
                square_video_id=f"square-{index + 1:02d}",
                ready=True,
                source="eggbev-offline-test",
                upload_edge="ad_account_advideos",
                association_verified=True,
            )
            refs.append({"asset_id": asset_id, "checksum": checksum})
        return refs

    def _build(self, campaigns: int = 3, ads_per_campaign: int = 3) -> dict:
        total = campaigns * ads_per_campaign
        start = (datetime.now(ZoneInfo("America/New_York")) + timedelta(days=2)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return build_eggbev_from_zero_manifest(
            registry=self.registry,
            request_id="eggbev-test-request",
            page_id="123456789012345",
            page_name="Amy Shook",
            page_token="pg_5024",
            page_sequence=162,
            campaign_sequences=list(range(1, campaigns + 1)),
            daily_budgets_minor=[5000] * campaigns,
            start_time=start.isoformat(),
            asset_refs=self._assets(total),
            ad_names=[f"AMY AD {index + 1:02d}" for index in range(total)],
        )

    def test_three_by_three_builds_valid_manifest_and_policy(self) -> None:
        payload = self._build()
        manifest = Manifest.from_dict(payload)
        validate_account_policy(manifest, CONFIG)
        self.assertEqual(len(manifest.campaigns), 3)
        self.assertEqual(sum(len(row.ads) for row in manifest.campaigns), 9)
        self.assertEqual(manifest.campaigns[0].name, "162 - Amy Shook - ENG - US - (pg_5024) C001 para Amy - Copy")

    def test_one_by_five_is_supported(self) -> None:
        payload = self._build(campaigns=1, ads_per_campaign=5)
        validate_account_policy(Manifest.from_dict(payload), CONFIG)
        self.assertEqual(len(payload["campaigns"][0]["ads"]), 5)

    def test_manual_placements_exclude_audience_network(self) -> None:
        payload = self._build(campaigns=1)
        targeting = payload["campaigns"][0]["adset_create"]["targeting"]
        self.assertEqual(targeting["publisher_platforms"], ["facebook", "instagram", "messenger"])
        self.assertEqual(targeting["facebook_positions"], FACEBOOK_POSITIONS)
        self.assertEqual(targeting["instagram_positions"], INSTAGRAM_POSITIONS)
        self.assertEqual(targeting["messenger_positions"], MESSENGER_POSITIONS)
        self.assertNotIn("audience_network", json.dumps(targeting))

    def test_copy_and_messenger_flags_match_approved_template(self) -> None:
        payload = self._build(campaigns=1)
        creative = payload["campaigns"][0]["ads"][0]["creative_payload"]
        feed = creative["asset_feed_spec"]
        welcome = json.loads(feed["additional_data"]["page_welcome_message"])
        self.assertEqual(feed["bodies"], [{"text": ""}])
        self.assertEqual([row["text"] for row in feed["titles"]], ["APPLY NOW ✅", "CARD APPROVED", "✔️ APPLY CARD"])
        self.assertEqual(feed["call_to_action_types"], ["APPLY_NOW"])
        self.assertIs(welcome["performance_booster_enabled"], False)
        self.assertIs(welcome["message_data"]["performance_booster_enabled"], False)
        self.assertNotIn("template_id", welcome)
        self.assertNotIn("standard_enhancements", json.dumps(creative))

    def test_page_and_tracking_are_materialized(self) -> None:
        payload = self._build(campaigns=1)
        campaign = payload["campaigns"][0]
        creative = campaign["ads"][0]["creative_payload"]
        self.assertEqual(campaign["adset_create"]["promoted_object"]["page_id"], "123456789012345")
        self.assertEqual(creative["object_story_spec"], {"page_id": "123456789012345"})
        self.assertEqual(creative["url_tags"], "utm_campaign=pg_5024")

    def test_from_zero_forbids_source_ids(self) -> None:
        payload = self._build(campaigns=1)
        payload["campaigns"][0]["source_campaign_id"] = "999"
        with self.assertRaisesRegex(ManifestError, "forbids source_campaign_id"):
            Manifest.from_dict(payload)

    def test_policy_rejects_dup_naming(self) -> None:
        payload = self._build(campaigns=1)
        payload["campaigns"][0]["name"] = "Amy Shook DUP01"
        with self.assertRaisesRegex(ManifestError, "naming policy"):
            validate_account_policy(Manifest.from_dict(payload), CONFIG)

    def test_policy_rejects_advantage_placements(self) -> None:
        payload = self._build(campaigns=1)
        payload["campaigns"][0]["adset_create"]["targeting"]["publisher_platforms"].append("audience_network")
        with self.assertRaisesRegex(ManifestError, "publisher_platforms"):
            validate_account_policy(Manifest.from_dict(payload), CONFIG)

    def test_policy_reads_budget_from_campaign_create(self) -> None:
        payload = self._build(campaigns=1)
        payload["campaigns"][0]["campaign_create"]["daily_budget"] = "0"
        with self.assertRaisesRegex(ManifestError, "positive"):
            validate_account_policy(Manifest.from_dict(payload), CONFIG)

    def test_duplicate_media_lineage_is_blocked_in_prevalidation(self) -> None:
        payload = self._build(campaigns=1)
        payload["campaigns"][0]["ads"][1]["media"] = copy.deepcopy(payload["campaigns"][0]["ads"][0]["media"])
        with self.assertRaisesRegex(ManifestError, "duplicate media lineage"):
            prevalidate_payload(payload, self.registry)

    def test_prevalidate_and_plan_use_direct_create_stages(self) -> None:
        payload = self._build(campaigns=3)
        validate_account_policy(Manifest.from_dict(payload), CONFIG)
        sealed = prevalidate_payload(payload, self.registry)
        manifest = Manifest.from_dict(sealed)
        engine = CampaignEngine(CONFIG, transport_factory=lambda account: FakeBatchTransport(account))
        dry_run = engine.dry_run(manifest)
        self.assertEqual(dry_run["writes"], 0)
        plan = Planner(bundle_size=2, max_ads_per_batch=10).build(manifest)
        stage_names = [
            stage.name
            for bundles in plan.lanes.values()
            for bundle in bundles
            for stage in bundle.stages
        ]
        self.assertIn("campaign_create", stage_names)
        self.assertIn("adset_create", stage_names)
        self.assertIn("creative_create", stage_names)
        self.assertIn("ad_create", stage_names)
        self.assertNotIn("campaign_copy", stage_names)
        self.assertNotIn("ad_copy_with_creative", stage_names)

    def test_missing_ad_names_blocks_before_manifest(self) -> None:
        with self.assertRaisesRegex(ValueError, "one ad name"):
            start = (datetime.now(ZoneInfo("America/New_York")) + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
            build_eggbev_from_zero_manifest(
                registry=self.registry,
                request_id="missing-names",
                page_id="123",
                page_name="Amy Shook",
                page_token="pg_5024",
                page_sequence=162,
                campaign_sequences=[1],
                daily_budgets_minor=[5000],
                start_time=start.isoformat(),
                asset_refs=self._assets(3),
                ad_names=[],
            )


if __name__ == "__main__":
    unittest.main()
