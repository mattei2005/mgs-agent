#!/usr/bin/env python3
import importlib.util
import io
import json
import unittest
import urllib.error
from datetime import datetime
from email.message import Message
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

SCRIPT = Path('/root/mgs-agent/scripts/dtr-sb-page-health-sync.py')
spec = importlib.util.spec_from_file_location('dtr_sb_page_health_sync_sheet', SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f'cannot load {SCRIPT}')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class RestrictedSheetDatasetTest(unittest.TestCase):
    def setUp(self):
        self.original_ignore = sync.load_global_ignore_keys
        setattr(sync, 'load_global_ignore_keys', lambda: (set(), set()))

    def tearDown(self):
        setattr(sync, 'load_global_ignore_keys', self.original_ignore)

    def test_discord_delivery_retries_rate_limit_using_retry_after(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({'id': 'message-1'}).encode()

        headers = Message()
        headers['Retry-After'] = '0.01'
        rate_limited = urllib.error.HTTPError(
            'https://discord.invalid',
            429,
            'Too Many Requests',
            headers,
            io.BytesIO(json.dumps({'retry_after': 0.01}).encode()),
        )
        with mock.patch.object(sync, 'discord_token', return_value='test-token'), \
             mock.patch.object(sync.urllib.request, 'urlopen', side_effect=[rate_limited, Response()]) as urlopen, \
             mock.patch.object(sync.time, 'sleep') as sleep:
            result = sync.post_discord('fixture', max_attempts=2)

        self.assertEqual(result, {'status': 200, 'message_id': 'message-1', 'attempts': 2})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0.25)

    def test_sheets_api_retries_transient_503(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"sheets": []}'

        unavailable = urllib.error.HTTPError(
            'https://sheets.googleapis.com/fixture',
            503,
            'Service Unavailable',
            Message(),
            io.BytesIO(b'{"error":{"status":"UNAVAILABLE"}}'),
        )
        with mock.patch.object(sync.urllib.request, 'urlopen', side_effect=[unavailable, Response()]) as urlopen, \
             mock.patch.object(sync.time, 'sleep') as sleep:
            result = sync.sheets_api('fixture-token', 'GET', 'https://sheets.googleapis.com/fixture')

        self.assertEqual(result, {'sheets': []})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_sheets_api_does_not_retry_nontransient_400(self):
        bad_request = urllib.error.HTTPError(
            'https://sheets.googleapis.com/fixture',
            400,
            'Bad Request',
            Message(),
            io.BytesIO(b'{"error":{"status":"INVALID_ARGUMENT"}}'),
        )
        with mock.patch.object(sync.urllib.request, 'urlopen', side_effect=bad_request) as urlopen, \
             mock.patch.object(sync.time, 'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'Google Sheets HTTP 400'):
                sync.sheets_api('fixture-token', 'GET', 'https://sheets.googleapis.com/fixture')

        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @staticmethod
    def raw(page_id, status, date='2026-07-16', site='openzed'):
        return {
            'USER_LOGIN': 'bot@example.com',
            'PAGE_ID': str(page_id),
            'FB_PAGE_ID': f'900000000000{page_id}',
            'PAGE_NAME': f'Page {page_id}',
            'PROFILE_NAME': 'Segurador Teste',
            'STATUS': status,
            'RESTRICTED_UNTIL': date,
            'PUBLISHER_ID': f'digital-trust_{site}',
            'NOTES': '#2022',
        }

    def test_includes_campaign_and_excludes_onhold_blocked_and_expired(self):
        rows = [
            self.raw(1, 'Broadcast'),
            self.raw(2, 'Campaign'),
            self.raw(3, 'On-hold'),
            self.raw(4, 'Blocked'),
            self.raw(5, 'Broadcast', '2026-07-14'),
            {**self.raw(6, 'Broadcast'), 'USER_LOGIN': 'inactive@example.com'},
        ]

        report_rows, stats = sync.restricted_sheet_rows(
            rows,
            {'bot@example.com'},
            '2026-07-15',
        )

        self.assertEqual([row['page id'] for row in report_rows], ['1', '2'])
        self.assertEqual([row['status sb'] for row in report_rows], ['Broadcast', 'Campaign'])
        self.assertEqual(stats['sheet_rows_included'], 2)
        self.assertEqual(stats['sheet_broadcast_restricted'], 1)
        self.assertEqual(stats['sheet_other_status_included'], 1)
        self.assertEqual(stats['sheet_on_hold_excluded'], 1)
        self.assertEqual(stats['sheet_blocked_excluded'], 1)

    def test_summary_and_total_tabs_are_canonical_and_complete(self):
        report_rows = [
            {
                'link da pagina': 'https://facebook.com/1',
                'nome da pagina': 'A',
                'fb page id': '1',
                'page id': '10',
                'bot user': 'bot@example.com',
                'segurador': 'S',
                'sites': 'openzed',
                'status sb': 'Broadcast',
                'codigos': '#2022',
                'data saida': '2026-08-01',
            },
            {
                'link da pagina': 'https://facebook.com/2',
                'nome da pagina': 'B',
                'fb page id': '2',
                'page id': '11',
                'bot user': 'bot@example.com',
                'segurador': 'S',
                'sites': 'eggbev,openzed',
                'status sb': 'Campaign',
                'codigos': '',
                'data saida': '2026-08-01',
            },
        ]
        headers = list(report_rows[0])
        datasets = sync.build_report_datasets(report_rows, headers)
        summary = sync.build_summary_dataset(
            report_rows,
            {
                'sheet_broadcast_restricted': 1,
                'sheet_other_status_included': 1,
                'sheet_on_hold_excluded': 4,
            },
            datetime(2026, 7, 16, 12, 0, tzinfo=ZoneInfo('America/New_York')),
        )

        self.assertIn(sync.REPORT_TOTAL_TAB, datasets)
        self.assertNotIn(sync.REPORT_LEGACY_TOTAL_TAB, datasets)
        self.assertEqual(len(datasets[sync.REPORT_TOTAL_TAB]) - 1, 2)
        self.assertEqual(len(datasets['openzed']) - 1, 2)
        self.assertEqual(summary[2], ['Broadcast restritas', '1'])
        self.assertEqual(summary[3], ['Outras restritas ativas', '1'])
        self.assertEqual(summary[4], ['On-hold ignoradas', '4'])
        self.assertEqual(summary[5], ['Data de Saída', 'Páginas', 'Sites'])
        self.assertEqual(summary[6], ['2026-08-01', '2', 'eggbev, openzed'])

    def test_discord_operational_summary_stays_broadcast_only(self):
        rows = [
            {'status sb': 'Broadcast', 'data saida': '2026-08-01', 'sites': 'openzed'},
            {'status sb': 'Campaign', 'data saida': '2026-08-01', 'sites': 'eggbev'},
        ]
        messages = sync.build_operational_summary_alerts(
            rows,
            {
                'started_at': '2026-07-16T12:00:00-04:00',
                'sheet_broadcast_restricted': 1,
                'sheet_on_hold_excluded': 4,
            },
        )
        joined = '\n'.join(messages)
        self.assertIn('Broadcast restritas: 1', joined)
        self.assertIn('2026-08-01         1  openzed', joined)
        self.assertNotIn('eggbev', joined)


if __name__ == '__main__':
    unittest.main()
