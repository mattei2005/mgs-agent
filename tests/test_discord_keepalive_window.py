"""Daily keepalive safety margin, DST and overdue-active regressions."""
import datetime as dt
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'scripts/monitor-discord-thread-archive-warnings.py'
spec = importlib.util.spec_from_file_location('week_window_monitor', SOURCE)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NOW = dt.datetime(2026, 11, 1, 14, 16, 2, tzinfo=dt.timezone.utc)


class WindowTests(unittest.TestCase):
    def collect(self, remaining, duration=10080, archived=False):
        activity = NOW + dt.timedelta(seconds=remaining, minutes=-duration)
        value = {'id': '123', 'parent_id': '456', 'name': 'fixture',
                 'thread_metadata': {'archived': archived, 'auto_archive_duration': duration,
                                     'archive_timestamp': activity.isoformat()}}
        with patch.object(mod, 'load_env_token', return_value='fixture-only'), patch.object(mod, 'api_json', return_value=(200, {'threads': [value]})):
            rows, errors = mod.collect_threads(NOW)
        self.assertEqual(errors, [])
        return rows

    def test_daily_seconds_drift_covered(self):
        self.assertIn('123', self.collect(24 * 3600 + 12))

    def test_fall_dst_hour_covered(self):
        self.assertIn('123', self.collect(25 * 3600 + 12))

    def test_overdue_still_active_recovered(self):
        self.assertIn('123', self.collect(-60))

    def test_future_not_bumped(self):
        self.assertEqual(self.collect(27 * 3600), {})

    def test_one_day_scope_unchanged(self):
        self.assertEqual(self.collect(3600, duration=1440), {})

    def test_archived_never_implicitly_reopened(self):
        self.assertEqual(self.collect(-60, archived=True), {})


if __name__ == '__main__':
    unittest.main()
