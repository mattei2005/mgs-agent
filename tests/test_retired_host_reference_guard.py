"""Immutable inventory evidence must not disable operational host protection."""
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-retired-host-references.py"
SPEC = importlib.util.spec_from_file_location("retired_host_guard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class HistoricalEvidenceTests(unittest.TestCase):
    def scan(self, relative, content, allowed_relative=None, allowed_content=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            allowlist = {}
            if allowed_relative is not None:
                assert allowed_content is not None
                allowlist[allowed_relative] = hashlib.sha256(allowed_content).hexdigest()
            result = subprocess.CompletedProcess([], 0, relative.encode() + b"\0")
            failures = []
            with patch.object(guard, "REPO", root), patch.object(
                guard, "HISTORICAL_EVIDENCE_SHA256", allowlist
            ), patch.object(guard.subprocess, "run", return_value=result):
                guard.tracked_repo_failures(failures)
            return failures

    def test_verified_immutable_snapshot_is_preserved(self):
        relative = "data/zeus/example/inventory-before-runtime-entry.json"
        content = guard.RETIRED_HOST.encode()
        self.assertEqual(self.scan(relative, content, relative, content), [])

    def test_modified_snapshot_still_blocks(self):
        relative = "data/zeus/example/inventory-before-runtime-entry.json"
        content = guard.RETIRED_HOST.encode()
        self.assertEqual(
            self.scan(relative, content + b" changed", relative, content),
            [f"repo:{relative}"],
        )

    def test_sibling_operational_file_still_blocks(self):
        relative = "data/zeus/example/connection.json"
        content = guard.RETIRED_HOST.encode()
        self.assertEqual(
            self.scan(relative, content, "data/zeus/example/inventory-before-runtime-entry.json", content),
            [f"repo:{relative}"],
        )

    def test_unregistered_inventory_snapshot_still_blocks(self):
        relative = "data/zeus/other/inventory-before-runtime-entry.json"
        self.assertEqual(self.scan(relative, guard.RETIRED_HOST.encode()), [f"repo:{relative}"])

    def test_profile_operational_surface_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.yaml"
            target.write_text(guard.RETIRED_HOST)
            failures = []
            guard.scan_tree(target, "profile-zeus", failures)
            self.assertEqual(failures, [f"profile-zeus:{target}"])

    def test_adspower_amendment_snapshot_registration_is_exact(self):
        relative = "data/adspower-warming-20261008/delivery-amendment-1559206352956432395/inventory-before.json"
        self.assertIn(relative, guard.HISTORICAL_EVIDENCE_SHA256)
        self.assertFalse(any(relative.startswith(prefix) for prefix in guard.REPO_ALLOWLIST_PREFIXES))

    def test_registered_production_snapshot_hash_matches(self):
        for relative, expected in guard.HISTORICAL_EVIDENCE_SHA256.items():
            with self.subTest(relative=relative):
                self.assertEqual(hashlib.sha256((guard.REPO / relative).read_bytes()).hexdigest(), expected)

    def test_php_recheck_registration_is_exact_negative_evidence(self):
        relative = "reports/php-security-20261021/hetzner-recheck-1562886130582552618.json"
        content = (guard.REPO / relative).read_bytes()
        hits = [line for line in content.decode().splitlines() if guard.RETIRED_HOST in line]
        self.assertEqual(len(hits), 1)
        self.assertIn(f"retired agent {guard.RETIRED_HOST} not probed.", hits[0])
        self.assertIn(relative, guard.HISTORICAL_EVIDENCE_SHA256)
        self.assertFalse(any(relative.startswith(prefix) for prefix in guard.REPO_ALLOWLIST_PREFIXES))
        self.assertEqual(self.scan(relative, content, relative, content), [])
        self.assertEqual(
            self.scan(relative, content + b" changed", relative, content),
            [f"repo:{relative}"],
        )

    def test_payment_schedule_snapshot_registration_is_exact_removed_history(self):
        relative = "reports/meta-manual-payments-scheduling-1563960345826037821/inventory-pre-update.json"
        content = (guard.REPO / relative).read_bytes()
        self.assertEqual(content.decode().count(guard.RETIRED_HOST), 1)
        records = json.loads(content)["runtime_artifacts"]
        hits = [row for row in records if guard.RETIRED_HOST in json.dumps(row)]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["id"], "runcloud-retired-ssh-allow-removal-20260712")
        self.assertEqual(hits[0]["status"], "removed_validated")
        self.assertIn(guard.RETIRED_HOST, hits[0]["removed_rule"])
        self.assertIn(relative, guard.HISTORICAL_EVIDENCE_SHA256)
        self.assertFalse(any(relative.startswith(prefix) for prefix in guard.REPO_ALLOWLIST_PREFIXES))
        self.assertEqual(self.scan(relative, content, relative, content), [])
        self.assertEqual(
            self.scan(relative, content + b" changed", relative, content),
            [f"repo:{relative}"],
        )

    def test_payment_schedule_sibling_connection_target_still_blocks(self):
        evidence = "reports/meta-manual-payments-scheduling-1563960345826037821/inventory-pre-update.json"
        relative = "reports/meta-manual-payments-scheduling-1563960345826037821/connection.json"
        content = guard.RETIRED_HOST.encode()
        self.assertEqual(
            self.scan(relative, content, evidence, content),
            [f"repo:{relative}"],
        )

    def test_payment_followup_snapshots_are_exact_removed_history(self):
        relatives = (
            "reports/meta-pay-now-1563981039230255186/inventory-pre-update.json",
            "reports/meta-september-invoices-1564022485366734969/inventory-before.json",
            "reports/meta-sheet-subtitle-1563999324587819020/inventory-before.json",
        )
        canonical = json.loads((guard.REPO / "data/infra-inventory.json").read_text())
        removed = [row for row in canonical["runtime_artifacts"]
                   if row.get("id") == "runcloud-retired-ssh-allow-removal-20260712"]
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["status"], "removed_validated")
        for relative in relatives:
            with self.subTest(relative=relative):
                content = (guard.REPO / relative).read_bytes()
                self.assertEqual(content.decode().count(guard.RETIRED_HOST), 1)
                hits = [row for row in json.loads(content)["runtime_artifacts"]
                        if guard.RETIRED_HOST in json.dumps(row)]
                self.assertEqual(hits, removed)
                self.assertIn(relative, guard.HISTORICAL_EVIDENCE_SHA256)
                self.assertFalse(any(relative.startswith(prefix)
                                     for prefix in guard.REPO_ALLOWLIST_PREFIXES))
                self.assertEqual(self.scan(relative, content, relative, content), [])
                self.assertEqual(
                    self.scan(relative, content + b" changed", relative, content),
                    [f"repo:{relative}"],
                )
                sibling = str(Path(relative).with_name("connection.json"))
                self.assertEqual(
                    self.scan(sibling, guard.RETIRED_HOST.encode(), relative, content),
                    [f"repo:{sibling}"],
                )

    def test_php_report_sibling_connection_target_still_blocks(self):
        relative = "reports/php-security-20261021/connection.json"
        evidence = "reports/php-security-20261021/hetzner-recheck-1562886130582552618.json"
        content = guard.RETIRED_HOST.encode()
        self.assertEqual(
            self.scan(relative, content, evidence, content),
            [f"repo:{relative}"],
        )


if __name__ == "__main__":
    unittest.main()
