#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import monitor_honcho_billing_watch as monitor  # noqa: E402


class HonchoBillingWatchTests(unittest.TestCase):
    def setUp(self):
        self.now = 2_000_000_000.0

    def event(self, unit="zeus-gateway.service", cursor="c1", timestamp=None, message=None):
        return {
            "_SYSTEMD_UNIT": unit,
            "__CURSOR": cursor,
            "__REALTIME_TIMESTAMP": str(int((timestamp or self.now) * 1_000_000)),
            "MESSAGE": message
            or "Honcho dialectic query failed: Payment required: Insufficient credits.",
        }

    def test_extracts_only_insufficient_credit_events_and_profiles(self):
        rows = [
            self.event(cursor="z1"),
            self.event(unit="ares-gateway.service", cursor="a1"),
            self.event(cursor="noise", message="ordinary gateway warning"),
        ]
        summary = monitor.summarize(rows)
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["profiles"], ["ares", "zeus"])
        self.assertEqual(summary["last_cursors"], {
            "ares-gateway.service": "a1",
            "zeus-gateway.service": "noise",
        })
        self.assertNotIn("ordinary", json.dumps(summary))

    def test_first_credit_error_alerts_immediately(self):
        summary = monitor.summarize([self.event()])
        decision = monitor.decide(summary, {}, {}, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision, {"action": "alert", "reason": "first_402"})

    def test_active_incident_suppresses_repeat_before_reminder(self):
        summary = monitor.summarize([self.event(cursor="c2")])
        state = {"active": True, "active_since": self.now - 3600, "last_alert_at": self.now - 3600}
        decision = monitor.decide(summary, state, {}, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "none")

    def test_active_incident_sends_daily_reminder(self):
        summary = monitor.summarize([])
        state = {"active": True, "active_since": self.now - 90_000, "last_alert_at": self.now - 90_000}
        decision = monitor.decide(summary, state, {}, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision, {"action": "alert", "reason": "daily_reminder"})

    def test_health_probe_after_alert_closes_incident(self):
        summary = monitor.summarize([])
        state = {"active": True, "active_since": self.now - 3600, "last_alert_at": self.now - 3600}
        health = {"last_status": "ok", "last_check": "2033-05-18T03:33:20Z"}
        decision = monitor.decide(summary, state, health, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision, {"action": "recovery", "reason": "validated_health_probe"})

    def test_old_health_probe_does_not_close_new_incident(self):
        summary = monitor.summarize([])
        state = {"active": True, "active_since": self.now, "last_alert_at": self.now}
        health = {"last_status": "ok", "last_check": "2020-01-01T00:00:00Z"}
        decision = monitor.decide(summary, state, health, now_epoch=self.now, reminder_hours=24)
        self.assertEqual(decision["action"], "none")

    def test_next_state_preserves_cursors_and_never_stores_messages(self):
        summary = monitor.summarize([self.event(cursor="c9")])
        decision = {"action": "alert", "reason": "first_402"}
        state = monitor.next_state(summary, {}, decision, now_epoch=self.now)
        encoded = json.dumps(state)
        self.assertTrue(state["active"])
        self.assertEqual(state["last_cursors"]["zeus-gateway.service"], "c9")
        self.assertNotIn("Payment required", encoded)
        self.assertNotIn("MESSAGE", encoded)

    def test_recovery_state_clears_active_but_keeps_cursors(self):
        summary = monitor.summarize([])
        old = {"active": True, "active_since": self.now - 50, "last_cursors": {"zeus-gateway.service": "c1"}}
        state = monitor.next_state(summary, old, {"action": "recovery", "reason": "validated_health_probe"}, now_epoch=self.now)
        self.assertFalse(state["active"])
        self.assertIsNone(state["active_since"])
        self.assertEqual(state["last_cursors"]["zeus-gateway.service"], "c1")

    def test_payload_contract_targets_alerts_infra_and_mentions_only_alerts(self):
        alert = monitor.payload({"action": "alert", "reason": "first_402"}, ["zeus"], self.now)
        recovery = monitor.payload({"action": "recovery", "reason": "validated_health_probe"}, [], self.now)
        self.assertEqual(monitor.DEFAULT_CHANNEL_ID, "1498132022634483894")
        self.assertIn("<@344196393512075265>", alert["content"])
        self.assertEqual(alert["allowed_mentions"]["users"], ["344196393512075265"])
        self.assertEqual(recovery["content"], "")
        self.assertEqual(recovery["allowed_mentions"], {"parse": []})

    def test_active_billing_watcher_makes_six_hour_probe_due(self):
        health_script = ROOT / "scripts" / "monitor-honcho-health.sh"
        with tempfile.TemporaryDirectory(prefix="honcho-health-schedule-") as raw:
            watch_state = Path(raw) / "watch.json"
            watch_state.write_text(json.dumps({"active": True}))
            env = dict(os.environ)
            env.update({
                "HONCHO_BILLING_WATCH_STATE": str(watch_state),
                "HONCHO_CURRENT_HOUR": "2",
                "HONCHO_SCHEDULE_ONLY": "1",
            })
            result = subprocess.run(
                [str(health_script)], env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PROBE_DUE reason=billing_watch_active", result.stdout)


if __name__ == "__main__":
    unittest.main()
