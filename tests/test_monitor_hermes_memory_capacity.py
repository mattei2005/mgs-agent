#!/usr/bin/env python3
import importlib.util
import json
import stat
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "monitor-hermes-memory-capacity.py"
spec = importlib.util.spec_from_file_location("monitor_hermes_memory_capacity", SCRIPT)
assert spec and spec.loader
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class MonitorHermesMemoryCapacityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mgs-memory-capacity-")
        self.root = Path(self.tmp.name)
        self.profiles = self.root / "profiles"
        self.state = self.root / "state.json"
        self.now = datetime(2026, 7, 17, 15, 30, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def make_profile(self, name="zeus", *, user_text="u" * 50, memory_text="m" * 50,
                     user_limit=100, memory_limit=100):
        profile = self.profiles / name
        memories = profile / "memories"
        memories.mkdir(parents=True)
        (profile / "config.yaml").write_text(
            "memory:\n"
            f"  user_char_limit: {user_limit}\n"
            f"  memory_char_limit: {memory_limit}\n",
            encoding="utf-8",
        )
        (memories / "USER.md").write_text(user_text, encoding="utf-8")
        (memories / "MEMORY.md").write_text(memory_text, encoding="utf-8")
        return profile

    def settings(self, **overrides):
        values = {
            "profiles_root": self.profiles,
            "state_file": self.state,
            "threshold_percent": 90.0,
            "target_percent": 89.0,
            "channel_id": "1527401973698007060",
            "profile_filter": (),
            "dry_run": False,
        }
        values.update(overrides)
        return monitor.Settings(**values)

    def test_discovers_only_immediate_active_profiles(self):
        self.make_profile("zeus")
        nested = self.profiles / "zeus" / "state-snapshots" / "old"
        nested.mkdir(parents=True)
        (nested / "config.yaml").write_text("memory: {}\n", encoding="utf-8")
        (self.profiles / "not-a-profile").mkdir()

        found = monitor.discover_profiles(self.profiles)

        self.assertEqual([path.name for path in found], ["zeus"])

    def test_below_threshold_is_read_only_and_writes_healthy_state(self):
        profile = self.make_profile(user_text="x" * 89)
        before = (profile / "memories" / "USER.md").read_bytes()
        calls = []
        posts = []

        result = monitor.run_monitor(
            self.settings(),
            compactor_runner=lambda *args: calls.append(args),
            poster=lambda payload: posts.append(payload) or "1",
            now=self.now,
        )

        self.assertEqual(calls, [])
        self.assertEqual(posts, [])
        self.assertEqual((profile / "memories" / "USER.md").read_bytes(), before)
        self.assertEqual(result["threshold_count"], 0)
        state = json.loads(self.state.read_text())
        self.assertEqual(state["stores"]["zeus:user"]["status"], "healthy")
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)

    def test_threshold_compacts_once_and_posts_metadata_only_success(self):
        profile = self.make_profile(user_text="x" * 90)
        calls = []
        posts = []

        def compact(profile_root, store, target_percent):
            calls.append((profile_root.name, store, target_percent))
            source = profile_root / "memories" / ("USER.md" if store == "user" else "MEMORY.md")
            before = source.read_text()
            source.write_text(before[:85], encoding="utf-8")
            backup = self.root / "secure" / "fixture"
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text(before, encoding="utf-8")
            backup.chmod(0o600)
            return {
                "success": True,
                "applied": True,
                "mode": "fixture",
                "before_chars": len(before),
                "after_chars": 85,
                "before_sha256": "a" * 64,
                "after_sha256": "b" * 64,
                "backup_path": str(backup),
                "readback_matches": True,
            }

        result = monitor.run_monitor(
            self.settings(), compactor_runner=compact,
            poster=lambda payload: posts.append(payload) or "123", now=self.now,
        )

        self.assertEqual(calls, [("zeus", "user", 89.0)])
        self.assertEqual(len(posts), 1)
        self.assertNotIn("content", posts[0])
        embed = posts[0]["embeds"][0]
        self.assertIn("compactada automaticamente", embed["title"].lower())
        rendered = json.dumps(embed, ensure_ascii=False)
        self.assertNotIn("x" * 20, rendered)
        self.assertEqual(result["compacted_count"], 1)
        self.assertEqual(result["delivery_failures"], 0)
        state = json.loads(self.state.read_text())
        self.assertEqual(state["outbox"], [])
        self.assertEqual(state["stores"]["zeus:user"]["status"], "compacted")

    def test_compactor_failure_preserves_source_and_alerts_once_with_cooldown(self):
        profile = self.make_profile(user_text="z" * 95)
        source = profile / "memories" / "USER.md"
        before = source.read_bytes()
        posts = []

        def fail(*_args):
            raise monitor.CompactionRunError("semantic_verification_failed")

        first = monitor.run_monitor(
            self.settings(), compactor_runner=fail,
            poster=lambda payload: posts.append(payload) or "1", now=self.now,
        )
        second = monitor.run_monitor(
            self.settings(), compactor_runner=fail,
            poster=lambda payload: posts.append(payload) or "2", now=self.now + timedelta(minutes=10),
        )

        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(len(posts), 1)
        self.assertIn("falha", posts[0]["embeds"][0]["title"].lower())
        self.assertEqual(first["failure_count"], 1)
        self.assertEqual(second["failure_count"], 1)
        self.assertEqual(json.loads(self.state.read_text())["outbox"], [])

    def test_failed_delivery_stays_in_outbox_and_retries(self):
        self.make_profile(user_text="q" * 95)
        post_attempts = []

        def fail_compaction(*_args):
            raise monitor.CompactionRunError("model_call_failed")

        def failed_post(payload):
            post_attempts.append(payload)
            raise monitor.DeliveryError("fixture_http_500")

        first = monitor.run_monitor(
            self.settings(), compactor_runner=fail_compaction,
            poster=failed_post, now=self.now,
        )
        state = json.loads(self.state.read_text())
        self.assertEqual(first["delivery_failures"], 1)
        self.assertEqual(len(state["outbox"]), 1)

        second = monitor.run_monitor(
            self.settings(), compactor_runner=fail_compaction,
            poster=lambda payload: post_attempts.append(payload) or "99",
            now=self.now + timedelta(minutes=10),
        )
        self.assertEqual(second["delivery_failures"], 0)
        self.assertEqual(json.loads(self.state.read_text())["outbox"], [])
        self.assertEqual(len(post_attempts), 2)

    def test_default_compactor_timeout_covers_verified_per_entry_runs(self):
        args = monitor._parser().parse_args([])
        self.assertEqual(args.compactor_timeout, 1200)

    def test_dry_run_never_compacts_posts_or_writes_state(self):
        profile = self.make_profile(user_text="d" * 95)
        before = (profile / "memories" / "USER.md").read_bytes()
        calls = []
        posts = []

        result = monitor.run_monitor(
            self.settings(dry_run=True),
            compactor_runner=lambda *args: calls.append(args),
            poster=lambda payload: posts.append(payload), now=self.now,
        )

        self.assertEqual(calls, [])
        self.assertEqual(posts, [])
        self.assertFalse(self.state.exists())
        self.assertEqual((profile / "memories" / "USER.md").read_bytes(), before)
        self.assertEqual(result["threshold_count"], 1)

    def test_invalid_profile_config_alerts_without_running_compactor(self):
        profile = self.make_profile()
        (profile / "config.yaml").write_text("memory: [\n", encoding="utf-8")
        calls = []
        posts = []

        result = monitor.run_monitor(
            self.settings(),
            compactor_runner=lambda *args: calls.append(args),
            poster=lambda payload: posts.append(payload) or "77",
            now=self.now,
        )

        self.assertEqual(calls, [])
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(len(posts), 1)
        self.assertIn("falha", posts[0]["embeds"][0]["title"].lower())
        self.assertNotIn("content", posts[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
