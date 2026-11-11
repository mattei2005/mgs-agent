"""Focused regression coverage for human renewal vs stale-thread enforcer."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'scripts/discord-archive-stale-agent-threads.py'
spec = importlib.util.spec_from_file_location('archive_activity_enforcer', SOURCE)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 5, 16, 0, tzinfo=UTC)
OLD = NOW - dt.timedelta(days=8)
FRESH = NOW - dt.timedelta(minutes=8)


def snowflake(stamp):
    return str((int(stamp.timestamp() * 1000) - mod.DISCORD_EPOCH_MS) << 22)


def thread(last=OLD, archive: str | None = FRESH.isoformat(), duration=10080):
    return {'id': snowflake(OLD - dt.timedelta(days=5)), 'parent_id': '123',
            'last_message_id': snowflake(last), 'name': 'renewed',
            'thread_metadata': {'archived': False, 'archive_timestamp': archive,
                                'auto_archive_duration': duration}}


class ActivityTests(unittest.TestCase):
    def test_human_renewal_wins(self):
        self.assertEqual(mod.thread_activity_time(thread()), FRESH)

    def test_deleted_keepalive_last_id_wins(self):
        self.assertEqual(mod.thread_activity_time(thread(last=FRESH, archive=OLD.isoformat())), FRESH)

    def test_invalid_archive_uses_last(self):
        self.assertEqual(mod.thread_activity_time(thread(archive='invalid')), OLD)

    def test_missing_archive_uses_last(self):
        self.assertEqual(mod.thread_activity_time(thread(archive=None)), OLD)

    def test_naive_archive_not_trusted(self):
        self.assertEqual(mod.thread_activity_time(thread(archive='2026-11-05T15:52:00')), OLD)

    def test_creation_fallback(self):
        value = thread(archive=None)
        value.pop('last_message_id')
        self.assertEqual(mod.thread_activity_time(value), mod.snowflake_time(value['id']))

    def exercise_main(self, value):
        calls = []
        class Frozen(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW
        def api(token, method, path, body=None):
            calls.append((method, path, body))
            if '/threads/active' in path:
                return {'threads': [value]}
            if method == 'GET':
                return {'guild_id': '456'}
            return {}
        out = io.StringIO()
        with patch.object(mod, 'load_profile', return_value=mod.Profile('zeus', 'fixture-only', ['123'])), patch.object(mod, 'request_json', side_effect=api), patch.object(mod.dt, 'datetime', Frozen), patch.object(mod.time, 'sleep'), patch.object(sys, 'argv', ['test', '--profiles', 'zeus', '--apply', '--summary-only']), contextlib.redirect_stdout(out):
            self.assertEqual(mod.main(), 0)
        return calls, json.loads(out.getvalue())['summary']

    def test_apply_preserves_reopened_week_thread(self):
        calls, result = self.exercise_main(thread())
        self.assertFalse(any(c[0] == 'PATCH' for c in calls))
        self.assertEqual(result['archived'], 0)

    def test_apply_still_archives_truly_stale_day_thread(self):
        calls, result = self.exercise_main(thread(archive=OLD.isoformat(), duration=1440))
        self.assertEqual([c for c in calls if c[0] == 'PATCH'], [('PATCH', '/channels/' + thread()['id'], {'archived': True})])
        self.assertEqual(result['archived'], 1)


if __name__ == '__main__':
    unittest.main()
