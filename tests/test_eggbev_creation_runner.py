from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SCRIPTS = BASE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("eggbev_creation_runner", SCRIPTS / "ares-eggbev-creation.py")
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class EggbevCreationRunnerTests(unittest.TestCase):
    def test_offline_smoke_builds_three_by_three_without_network_or_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "smoke.json"
            result = RUNNER.offline_smoke(output)
            self.assertEqual(result["status"], "OFFLINE_SMOKE_OK")
            self.assertEqual(result["campaigns"], 3)
            self.assertEqual(result["ads"], 9)
            self.assertEqual(result["network_calls"], 0)
            self.assertEqual(result["writes"], 0)
            self.assertTrue(output.is_file())

    def test_scoped_selection_is_deterministic_and_not_filename_order(self):
        rows = []
        for index in range(20):
            rows.append({
                "asset_id": f"asset-{index:02d}",
                "canonical_filename": f"ZZZ-{19-index:02d}.mp4",
                "clean_checksum": f"checksum-{index:02d}",
                "perceptual_fingerprint": f"fingerprint-{index:02d}",
                "approved_for_scoped_request": True,
            })
        data = {"assets": rows}
        first = RUNNER.select_assets(data, "request-A", 9)
        again = RUNNER.select_assets(data, "request-A", 9)
        other = RUNNER.select_assets(data, "request-B", 9)
        self.assertEqual([row["asset_id"] for row in first], [row["asset_id"] for row in again])
        self.assertNotEqual([row["asset_id"] for row in first], [row["asset_id"] for row in other])
        self.assertNotEqual([row["canonical_filename"] for row in first], sorted(row["canonical_filename"] for row in first))
        self.assertEqual(len({row["perceptual_fingerprint"] for row in first}), 9)

    def test_budget_parser_accepts_one_or_per_campaign_and_rejects_missing(self):
        self.assertEqual(RUNNER.usd_minor_list("50", 3), [5000, 5000, 5000])
        self.assertEqual(RUNNER.usd_minor_list("40,50,60", 3), [4000, 5000, 6000])
        with self.assertRaises(RUNNER.CreationBlocked):
            RUNNER.usd_minor_list("40,50", 3)
        with self.assertRaises(RUNNER.CreationBlocked):
            RUNNER.usd_minor_list("0", 3)

    def test_automatic_ad_names_reset_slots_per_campaign_and_use_asset_stem(self):
        selected = [
            {"canonical_filename": f"CC_US_EN_VID_TEST_{index:03d}.mp4"}
            for index in range(1, 7)
        ]
        names = RUNNER.automatic_ad_names(selected, 3)
        self.assertEqual(names[0], "AD 01 - CC_US_EN_VID_TEST_001")
        self.assertEqual(names[2], "AD 03 - CC_US_EN_VID_TEST_003")
        self.assertEqual(names[3], "AD 01 - CC_US_EN_VID_TEST_004")
        self.assertEqual(len(names), len(set(names)))

    def test_automatic_ad_names_fail_closed_without_canonical_filename(self):
        with self.assertRaises(RUNNER.CreationBlocked):
            RUNNER.automatic_ad_names([{"asset_id": "asset-1"}], 3)

    def test_immediate_start_is_future_and_does_not_change_default_midnight(self):
        immediate = RUNNER.datetime.fromisoformat(RUNNER.immediate_execute_start())
        default = RUNNER.datetime.fromisoformat(RUNNER.next_midnight())
        now = RUNNER.datetime.now(RUNNER.ET)
        self.assertGreater(immediate, now)
        self.assertLessEqual((immediate - now).total_seconds(), 301)
        self.assertEqual((default.hour, default.minute, default.second), (0, 0, 0))

    def test_messenger_json_readback_parser_ignores_key_order_and_rejects_invalid(self):
        self.assertEqual(
            RUNNER.parsed_json_object('{"b":2,"a":1}'),
            RUNNER.parsed_json_object({"a": 1, "b": 2}),
        )
        with self.assertRaises(RUNNER.CreationBlocked):
            RUNNER.parsed_json_object("not-json")

    def test_execute_requires_both_human_and_financial_gates_before_state_read(self):
        args = argparse.Namespace(
            request_id="not-created",
            summary_digest="digest",
            financial_approved_by="Kelly",
            confirm_nicolas_ok=False,
            confirm_execute=False,
        )
        with self.assertRaises(RUNNER.CreationBlocked) as caught:
            RUNNER.execute_request(args)
        self.assertEqual(caught.exception.stage, "approval")
        args.confirm_nicolas_ok = True
        args.confirm_execute = True
        with self.assertRaises(RUNNER.CreationBlocked) as caught:
            RUNNER.execute_request(args)
        self.assertEqual(caught.exception.stage, "financial_gate")

    def test_nicolas_has_standing_eggbev_budget_authority(self):
        self.assertIn("Nicolas", RUNNER.FINANCIAL_APPROVERS)
        self.assertIn("Nicolas Holanda", RUNNER.FINANCIAL_APPROVERS)

    def test_engine_assignment_mapping_uses_bundle_order_and_exact_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.json"
            audit.write_text(json.dumps({
                "lanes": {
                    RUNNER.ACCOUNT_ID: {
                        "bundles": [
                            {"index": 1, "status": "COMPLETE", "campaign_ids": ["c1", "c2"], "adset_ids": ["s1", "s2"], "creative_ids": [f"cr{i}" for i in range(1, 7)], "ad_ids": [f"a{i}" for i in range(1, 7)]},
                            {"index": 2, "status": "COMPLETE", "campaign_ids": ["c3"], "adset_ids": ["s3"], "creative_ids": [f"cr{i}" for i in range(7, 10)], "ad_ids": [f"a{i}" for i in range(7, 10)]},
                        ]
                    }
                }
            }))
            state = {"campaign_sequences": [1, 2, 3], "selected_assets": [{"asset_id": f"asset-{i}"} for i in range(9)]}
            rows = RUNNER.engine_assignments({"audit_path": str(audit)}, state)
            self.assertEqual(len(rows), 9)
            self.assertEqual(rows[0], {"campaign_id": "c1", "adset_id": "s1", "creative_id": "cr1", "ad_id": "a1"})
            self.assertEqual(rows[3]["campaign_id"], "c2")
            self.assertEqual(rows[8], {"campaign_id": "c3", "adset_id": "s3", "creative_id": "cr9", "ad_id": "a9"})

    def test_prestage_is_registry_first_and_titles_include_checksum(self):
        class Uploader:
            def __init__(self):
                self.titles = []
            def upload(self, path, title):
                self.titles.append(title)
                return f"video-{len(self.titles)}"
            def wait_ready(self, ids):
                return {value: {"ready": True} for value in ids}
            def verify_association(self, ids):
                return {value: {"associated": True} for value in ids}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vertical = root / "vertical.mp4"
            square = root / "square.mp4"
            vertical.write_bytes(b"vertical")
            square.write_bytes(b"square")
            checksum = hashlib.sha256(vertical.read_bytes()).hexdigest()
            registry = RUNNER.MediaRegistry(root / "registry.json")
            uploader = Uploader()
            service = RUNNER.PrestageService(registry, uploader)
            first = service.prestage(account_id="100", asset_id="asset-1", checksum=checksum, vertical_path=vertical, square_path=square)
            second = service.prestage(account_id="100", asset_id="asset-1", checksum=checksum, vertical_path=vertical, square_path=square)
            self.assertEqual(first, second)
            self.assertEqual(len(uploader.titles), 2)
            self.assertTrue(all("asset-1" in title and checksum[:12] in title for title in uploader.titles))


if __name__ == "__main__":
    unittest.main()
