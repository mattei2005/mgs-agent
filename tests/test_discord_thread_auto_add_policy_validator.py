#!/usr/bin/env python3
import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-discord-thread-auto-add-policy.py"
spec = importlib.util.spec_from_file_location("thread_policy_validator", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class DiscordThreadPolicyValidatorTests(unittest.TestCase):
    def test_systemctl_properties_are_order_independent(self):
        text = "MainPID=658805\nActiveState=active\nSubState=running\nActiveEnterTimestamp=Thu 2026-08-20 19:37:26 EDT\n"
        self.assertEqual(
            validator.parse_systemctl_properties(text),
            {"MainPID": "658805", "ActiveState": "active", "SubState": "running", "ActiveEnterTimestamp": "Thu 2026-08-20 19:37:26 EDT"},
        )

    def test_systemd_snapshot_accepts_main_pid_first(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="MainPID=658805\nActiveState=active\nSubState=running\nActiveEnterTimestamp=Thu 2026-08-20 19:37:26 EDT\n",
            stderr="",
        )
        with mock.patch.object(validator.subprocess, "run", return_value=completed):
            result = validator.systemd_snapshot("ares")
        self.assertEqual(result["pid"], "658805")
        self.assertEqual(result["ActiveState"], "active")
        self.assertEqual(result["SubState"], "running")

    def test_systemd_snapshot_rejects_inactive_state_as_transient(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="MainPID=0\nActiveState=activating\nSubState=start\n",
            stderr="",
        )
        with mock.patch.object(validator.subprocess, "run", return_value=completed):
            with self.assertRaises(validator.ValidationError) as caught:
                validator.systemd_snapshot("ares")
        self.assertEqual(caught.exception.code, "gateway_not_ready")
        self.assertTrue(caught.exception.transient)

    def test_per_channel_mapping_preserves_explicit_empty_and_order(self):
        raw = '{"private":[],"cpv":["105","321"]}'
        result = validator.read_mapping(raw, code="bad")
        self.assertEqual(result["private"], [])
        self.assertEqual(result["cpv"], ["105", "321"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
