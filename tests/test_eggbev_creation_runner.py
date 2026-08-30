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

    def test_execute_requires_both_human_and_financial_gates_before_state_read(self):
        args = argparse.Namespace(
            request_id="not-created",
            summary_digest="digest",
            financial_approved_by="Nicolas",
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
