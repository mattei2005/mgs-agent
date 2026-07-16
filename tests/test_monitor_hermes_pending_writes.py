#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import monitor_hermes_pending_writes as monitor  # noqa: E402


class PendingMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mgs-pending-monitor-")
        self.root = Path(self.tmp.name) / "profiles"
        self.now = 2_000_000_000.0

    def tearDown(self):
        self.tmp.cleanup()

    def record(
        self,
        profile,
        subsystem,
        pid,
        age_hours,
        summary="SECRET CONTENT",
        failure_type=None,
    ):
        target = self.root / profile / "pending" / subsystem
        target.mkdir(parents=True, exist_ok=True)
        record = {
            "id": pid,
            "created_at": self.now - age_hours * 3600,
            "summary": summary,
            "payload": {"content": "DO NOT LEAK"},
        }
        if failure_type:
            record["failure_type"] = failure_type
            record["persisted"] = True
        (target / f"{pid}.json").write_text(json.dumps(record))

    def memory_store(self, profile, filename, chars, memory_limit=2200, user_limit=1375):
        target = self.root / profile
        (target / "memories").mkdir(parents=True, exist_ok=True)
        (target / "config.yaml").write_text(
            "memory:\n"
            f"  memory_char_limit: {memory_limit}\n"
            f"  user_char_limit: {user_limit}\n"
        )
        (target / "memories" / filename).write_text("x" * chars)

    def test_summary_counts_and_never_contains_content(self):
        self.record("zeus", "memory", "aaa111", 25)
        self.record("zeus", "skills", "bbb222", 2)
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        encoded = json.dumps(summary)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["aged"], 1)
        self.assertNotIn("SECRET", encoded)
        self.assertNotIn("DO NOT LEAK", encoded)

    def test_exactly_24_hours_is_aged(self):
        self.record("atena", "memory", "a1", 24)
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        self.assertEqual(summary["aged"], 1)

    def test_first_aged_item_alerts(self):
        self.record("zeus", "skills", "a1", 25)
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        decision = monitor.decide(summary, {}, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "alert")

    def test_same_set_is_suppressed_before_reminder(self):
        self.record("zeus", "skills", "a1", 25)
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        state = {"aged_ids": ["zeus/skills/a1"], "last_alert_at": self.now - 2 * 3600}
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "none")

    def test_new_aged_id_alerts_even_inside_reminder_window(self):
        self.record("zeus", "skills", "a1", 25)
        self.record("ares", "memory", "a2", 30)
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        state = {"aged_ids": ["zeus/skills/a1"], "last_alert_at": self.now - 2 * 3600}
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "alert")

    def test_daily_reminder_after_24_hours(self):
        self.record("zeus", "skills", "a1", 49)
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        state = {"aged_ids": ["zeus/skills/a1"], "last_alert_at": self.now - 25 * 3600}
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "alert")
        self.assertEqual(decision["reason"], "daily_reminder")

    def test_recovery_when_aged_queue_clears(self):
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        state = {"aged_ids": ["zeus/skills/a1"], "last_alert_at": self.now - 3600}
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "recovery")

    def test_scanner_error_preserves_last_confirmed_aged_set(self):
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        summary["errors"] = ["zeus/skills/bad.json: JSONDecodeError"]
        state = {"aged_ids": ["zeus/skills/a1"], "last_alert_at": self.now - 3600}
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        updated = monitor.next_state(summary, state, decision, now_epoch=self.now)
        self.assertEqual(decision["action"], "error")
        self.assertEqual(updated["aged_ids"], ["zeus/skills/a1"])

    def test_capacity_exactly_70_percent_warns_by_default_without_content(self):
        self.memory_store("zeus", "MEMORY.md", 700, memory_limit=1000)
        summary = monitor.scan_pending(self.root, now_epoch=self.now)
        encoded = json.dumps(summary)
        self.assertEqual(summary["capacity"]["threshold_percent"], 70.0)
        self.assertEqual(summary["capacity"]["warning_ids"], ["zeus.memory"])
        self.assertEqual(summary["capacity"]["rows"]["zeus.memory"]["percent"], 70.0)
        self.assertNotIn("x" * 20, encoded)

    def test_first_capacity_warning_alerts_and_repeats_are_suppressed(self):
        self.memory_store("zeus", "USER.md", 900, user_limit=1000)
        summary = monitor.scan_pending(self.root, now_epoch=self.now)
        first = monitor.decide(summary, {}, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(first["reason"], "first_capacity_warning")
        state = {
            "aged_ids": [],
            "capacity_warning_ids": ["zeus.user"],
            "last_alert_at": self.now - 3600,
        }
        repeated = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(repeated["action"], "none")

    def test_capacity_recovery_after_compaction(self):
        summary = monitor.scan_pending(self.root, now_epoch=self.now)
        state = {
            "aged_ids": [],
            "capacity_warning_ids": ["zeus.memory", "zeus.user"],
            "last_alert_at": self.now - 3600,
        }
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "recovery")
        self.assertEqual(decision["reason"], "warnings_cleared")

    def test_scanner_error_preserves_capacity_warning_set(self):
        summary = monitor.scan_pending(self.root, now_epoch=self.now)
        summary["errors"] = ["zeus/config.yaml: ParserError"]
        state = {
            "aged_ids": [],
            "capacity_warning_ids": ["zeus.user"],
            "last_alert_at": self.now - 3600,
        }
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        updated = monitor.next_state(summary, state, decision, now_epoch=self.now)
        self.assertEqual(updated["capacity_warning_ids"], ["zeus.user"])

    def test_capacity_overflow_dead_letter_alerts_immediately_without_content(self):
        self.record(
            "ares", "memory", "overflow1", 0.1,
            failure_type="capacity_overflow",
        )
        summary = monitor.scan_pending(self.root, now_epoch=self.now, threshold_hours=24)
        decision = monitor.decide(summary, {}, now_epoch=self.now, reminder_hours=24)
        payload = monitor.build_payload(summary, decision)
        encoded = json.dumps(payload)

        self.assertEqual(summary["aged"], 0)
        self.assertEqual(summary["dead_letter_ids"], ["ares/memory/overflow1"])
        self.assertEqual(decision, {"action": "alert", "reason": "first_dead_letter"})
        self.assertIn("overflow1", encoded)
        self.assertNotIn("SECRET CONTENT", encoded)
        self.assertNotIn("DO NOT LEAK", encoded)

    def test_capacity_overflow_dead_letter_anti_spam_and_new_id(self):
        self.record("ares", "memory", "overflow1", 0.1, failure_type="capacity_overflow")
        summary = monitor.scan_pending(self.root, now_epoch=self.now)
        state = {
            "aged_ids": [],
            "capacity_warning_ids": [],
            "dead_letter_ids": ["ares/memory/overflow1"],
            "last_alert_at": self.now - 3600,
        }
        suppressed = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(suppressed["action"], "none")

        self.record("zeus", "memory", "overflow2", 0.0, failure_type="capacity_overflow")
        expanded = monitor.scan_pending(self.root, now_epoch=self.now)
        alerted = monitor.decide(expanded, state, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(alerted, {"action": "alert", "reason": "new_dead_letter"})

    def test_capacity_overflow_dead_letter_recovery(self):
        summary = monitor.scan_pending(self.root, now_epoch=self.now)
        state = {
            "aged_ids": [],
            "capacity_warning_ids": [],
            "dead_letter_ids": ["ares/memory/overflow1"],
            "last_alert_at": self.now - 3600,
        }
        decision = monitor.decide(summary, state, now_epoch=self.now, reminder_hours=24)
        updated = monitor.next_state(summary, state, decision, now_epoch=self.now)
        self.assertEqual(decision, {"action": "recovery", "reason": "warnings_cleared"})
        self.assertEqual(updated["dead_letter_ids"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
