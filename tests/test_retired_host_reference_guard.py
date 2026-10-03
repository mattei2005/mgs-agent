"""Immutable inventory evidence must not disable operational host protection."""
import hashlib
import importlib.util
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

    def test_registered_production_snapshot_hash_matches(self):
        for relative, expected in guard.HISTORICAL_EVIDENCE_SHA256.items():
            with self.subTest(relative=relative):
                self.assertEqual(hashlib.sha256((guard.REPO / relative).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
