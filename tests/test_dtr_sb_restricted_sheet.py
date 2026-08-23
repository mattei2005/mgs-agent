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

    def test_sheet_rows_uses_service_account_api_and_keeps_filtered_out_rows(self):
        values = [
            ['Removidos acumulado', 'User', 'Segurador', 'Migrado', 'NO APP', 'APP PROVISORIO'],
            ['', 'active@example.com', 'Active User', 'FALSE', 'B013-1', ''],
            ['X', 'removed@example.com', 'Removed User', 'FALSE', 'B006-2', ''],
            ['', 'note@example.com', 'Operational Note', 'FALSE', 'CONTA DESATIVADA', ''],
            ['', 'provisional-only@example.com', 'Provisional Only', 'FALSE', '', 'B007'],
        ]
        with mock.patch.object(sync, 'google_access_token', return_value='fixture-token'), \
             mock.patch.object(sync, 'sheets_api', return_value={'values': values}) as sheets_api:
            rows = sync.sheet_rows()

        self.assertEqual(len(rows), 4)
        self.assertEqual(sync.active_users_from_sheet(rows), ['active@example.com'])
        args = sheets_api.call_args.args
        self.assertEqual(args[:2], ('fixture-token', 'GET'))
        self.assertIn('sheets.googleapis.com/v4/spreadsheets/', args[2])
        self.assertIn('Migracao%2022%2F06', args[2])
        self.assertIn('%21A%3AN', args[2])

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

    def test_sheets_api_retries_transport_timeout(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"values": []}'

        with mock.patch.object(sync.urllib.request, 'urlopen', side_effect=[TimeoutError('read timed out'), Response()]) as urlopen, \
             mock.patch.object(sync.time, 'sleep') as sleep:
            result = sync.sheets_api('fixture-token', 'GET', 'https://sheets.googleapis.com/fixture')

        self.assertEqual(result, {'values': []})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_sheets_api_stops_after_transport_retry_budget(self):
        with mock.patch.object(sync.urllib.request, 'urlopen', side_effect=TimeoutError('read timed out')) as urlopen, \
             mock.patch.object(sync.time, 'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'transport error after 3 attempts'):
                sync.sheets_api('fixture-token', 'GET', 'https://sheets.googleapis.com/fixture')

        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_args_list, [mock.call(1.0), mock.call(2.0)])

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

    def test_segurador_falls_back_to_structured_notes(self):
        row = {
            **self.raw(7, 'Broadcast'),
            'PROFILE_NAME': None,
            'NOTES': '09 - PERFIL SEGURADOR - Đoàn Diệu Hồng - ZUOUT - #2022',
        }
        report_rows, _ = sync.restricted_sheet_rows([row], {'bot@example.com'}, '2026-07-15')
        self.assertEqual(report_rows[0]['segurador'], 'Đoàn Diệu Hồng')

    def test_verified_dtr_enrichment_survives_sb_only_rebuild_and_fresh_dtr_wins(self):
        desired = [{
            'fb page id': '1', 'page id': '10', 'bot user': 'bot@example.com',
            'segurador': '', 'codigos': '#2022, APP_DELETED',
        }]
        previous = [{
            'fb page id': '1', 'page id': '10', 'bot user': 'bot@example.com',
            'segurador': 'Segurador anterior', 'codigos': '#2022',
        }]
        preserved = sync.merge_report_enrichment(desired, previous)
        self.assertEqual(preserved[0]['segurador'], 'Segurador anterior')
        self.assertEqual(preserved[0]['codigos'], '#2022')

        fresh = [{
            'fb_page_id': '1', 'page_id': '10', 'bot_user': 'bot@example.com',
            'segurador': 'Segurador atual', 'codes': ['#2022', '#551'],
        }]
        updated = sync.merge_report_enrichment(desired, previous, fresh)
        self.assertEqual(updated[0]['segurador'], 'Segurador atual')
        self.assertEqual(updated[0]['codigos'], '#2022, #551')

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
        self.assertIn('📊 PÁGINAS RESTRITAS — RESUMO OPERACIONAL', joined)
        self.assertIn('Broadcast restritas: 1', joined)
        self.assertIn('2026-08-01         1  openzed', joined)
        self.assertNotIn('eggbev', joined)

    def test_discord_alert_titles_use_stable_semantic_emojis(self):
        summary = {'started_at': '2026-07-16T12:00:00-04:00', 'stats': {}}
        restricted = [{
            'page_name': 'Page Test', 'fb_page_id': '123', 'page_id': '456',
            'bot_user': 'bot@example.com', 'segurador': 'Segurador',
            'sites': 'openzed', 'status_sb': 'Broadcast',
            'restricted_until': '2026-08-01', 'codes': ['#2022'],
        }]
        exited = [{
            'nome da pagina': 'Page Test', 'fb page id': '123', 'page id': '456',
            'bot user': 'bot@example.com', 'segurador': 'Segurador',
            'status sb': 'Broadcast', 'codigos': '#2022', 'data saida': '2026-08-01',
        }]

        new_blocks = sync.build_new_restrictions_alerts(restricted * 30, summary)
        self.assertGreater(len(new_blocks), 1)
        self.assertTrue(all('🆕 PÁGINAS RESTRITAS — NOVAS APLICADAS' in block for block in new_blocks))
        self.assertIn('✅ PÁGINAS RESTRITAS — VARREDURA CONCLUÍDA', sync.build_no_new_restrictions_alert(summary))
        self.assertIn('🟢 PÁGINAS QUE SAÍRAM DA RESTRIÇÃO', sync.build_exited_restrictions_alerts(exited, summary)[0])


if __name__ == '__main__':
    unittest.main()
