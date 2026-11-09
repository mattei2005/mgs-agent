#!/usr/bin/env python3
import importlib.util
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path


DAILY_SCRIPT = Path('/root/mgs-agent/scripts/dtr-sb-daily-match-audit.py')
SYNC_SCRIPT = Path('/root/mgs-agent/scripts/dtr-sb-page-health-sync.py')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


daily = load_module('dtr_sb_daily_match_audit_test', DAILY_SCRIPT)
sync = load_module('dtr_sb_page_health_sync_for_daily_test', SYNC_SCRIPT)
collector = daily.load_audit_mod()


class DailyAuditCollectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_retries_once_with_fresh_collection(self):
        failed = {'errors': ['TimeoutError: navigation'], 'accounts': []}
        recovered = {'errors': [], 'accounts': [], 'login_ok': True}
        with patch.object(collector, '_dtr_collect_user_once', AsyncMock(side_effect=[failed, recovered])) as run, \
                patch.object(collector.asyncio, 'sleep', AsyncMock()) as sleep:
            result = await collector.dtr_collect_user('user', 'item', 0)
        self.assertEqual(result, recovered)
        self.assertEqual(run.await_count, 2)
        sleep.assert_awaited_once_with(5)

    async def test_repeated_timeout_stops_after_two_attempts(self):
        failed = {'errors': ['TimeoutError: navigation'], 'accounts': []}
        with patch.object(collector, '_dtr_collect_user_once', AsyncMock(return_value=failed)) as run, \
                patch.object(collector.asyncio, 'sleep', AsyncMock()):
            self.assertEqual(await collector.dtr_collect_user('user', 'item'), failed)
        self.assertEqual(run.await_count, 2)

    async def test_authentication_failure_is_not_retried(self):
        failed = {'errors': ['RuntimeError: login rejected'], 'accounts': []}
        with patch.object(collector, '_dtr_collect_user_once', AsyncMock(return_value=failed)) as run:
            self.assertEqual(await collector.dtr_collect_user('user', 'item'), failed)
        run.assert_awaited_once()

    async def test_account_timeout_retries_but_remains_fail_closed(self):
        failed = {'errors': [], 'accounts': [{'errors': ['TimeoutError: account']}], 'login_ok': True}
        with patch.object(collector, '_dtr_collect_user_once', AsyncMock(return_value=failed)) as run, \
                patch.object(collector.asyncio, 'sleep', AsyncMock()):
            result = await collector.dtr_collect_user('user', 'item')
        self.assertEqual(run.await_count, 2)
        self.assertEqual(daily.collection_errors(result), ['TimeoutError: account'])

    async def test_success_is_not_retried(self):
        success = {'errors': [], 'accounts': [{'errors': []}], 'login_ok': True}
        with patch.object(collector, '_dtr_collect_user_once', AsyncMock(return_value=success)) as run:
            self.assertEqual(await collector.dtr_collect_user('user', 'item'), success)
        run.assert_awaited_once()


class DailyAuditRestrictionMetricTest(unittest.TestCase):
    def test_uses_canonical_inclusive_active_date_and_status_breakdown(self):
        rows = [
            {'status': 'Broadcast', 'restricted_until': '2026-08-01'},
            {'status': 'Broadcast', 'restricted_until': '2026-08-02'},
            {'status': 'broadcast', 'restricted_until': '2026-08-03'},
            {'status': 'campaign', 'restricted_until': '2026-08-03'},
            {'status': 'On-hold', 'restricted_until': '2026-08-03'},
            {'status': 'Blocked', 'restricted_until': '2026-08-03'},
            {'status': 'Ready', 'restricted_until': '2026-08-03'},
            {'status': 'Broadcast', 'restricted_until': ''},
        ]

        counts = daily.canonical_restriction_counts(
            rows,
            '2026-08-02',
            sync.active_restricted,
        )

        self.assertEqual(counts, {
            'Broadcast': 2,
            'Campaign': 1,
            'On-hold': 1,
            'Blocked': 1,
            'Other': 1,
            'Total': 6,
        })

    def test_report_exposes_broadcast_metric_without_legacy_mislabel(self):
        summary = {
            'dtr_pages_after_ignore': 10,
            'sb_rows_after_ignore': 10,
            'both_by_fb': 10,
            'ok_match': 10,
            'actionable_issues': 0,
            'ignored_total': 0,
            'dtr_only': 0,
            'sb_only': 0,
            'restriction_as_of_date': '2026-08-02',
        }
        report = daily.build_report(
            summary,
            {'Broadcast': 7, 'Campaign': 1, 'On-hold': 1, 'Blocked': 1, 'Ready': 0},
            {'Broadcast': 2, 'Campaign': 1, 'On-hold': 0, 'Blocked': 0, 'Other': 0, 'Total': 3},
            [],
            set(),
            0,
        )

        self.assertIn('Broadcast restritas  2', report)
        self.assertIn('Data inclusiva: RESTRICTED_UNTIL >= 2026-08-02', report)
        self.assertNotIn('Restricted ativo', report)

    def test_full_operational_report_remains_discord_chunk_safe(self):
        summary = {
            'dtr_pages_after_ignore': 2856,
            'sb_rows_after_ignore': 2856,
            'both_by_fb': 2831,
            'ok_match': 2831,
            'actionable_issues': 25,
            'ignored_total': 46,
            'dtr_only': 23,
            'sb_only': 2,
            'restriction_as_of_date': '2026-08-02',
        }
        issue_rows = [{
            'fb': f'90000000000{i:03d}',
            'pg_dtr': str(1000 + i),
            'pg_sb': '',
            'status': 'Broadcast',
            'login_dtr': 'bot-user-with-long-name@example.com',
            'login_sb': '',
            'problem': 'missing_in_sb',
        } for i in range(25)]
        report = daily.build_report(
            summary,
            {'Broadcast': 912, 'Campaign': 30, 'On-hold': 1677, 'Blocked': 127, 'Ready': 110},
            {'Broadcast': 463, 'Campaign': 1, 'On-hold': 0, 'Blocked': 0, 'Other': 0, 'Total': 464},
            issue_rows,
            set(),
            0,
        )
        chunks = daily.chunk_discord(report)

        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 1900 for chunk in chunks))
        self.assertEqual(sum(chunk.count('Broadcast restritas') for chunk in chunks), 1)
        self.assertEqual(sum(chunk.count('missing_in_sb') for chunk in chunks), 25)


if __name__ == '__main__':
    unittest.main()