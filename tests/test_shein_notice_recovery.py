"""Offline delivery-recovery regressions; never send a real Discord message."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_request_queue as q


class NoticeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.job = {'request_id': 'shein-12345', 'request': {'source_thread_id': 'THREAD'},
                    'status': 'RECOVERY_PENDING', 'notification': None,
                    'delivery_intent_at': '2026-10-20T13:00:00+00:00',
                    'last_error_type': 'OldError', 'retry_after_epoch': 100}
        self.message = {'id': 'M', 'channel_id': 'THREAD', 'author': {'id': 'ARES'},
                        'content': 'receipt', 'timestamp': '2026-10-20T13:01:00+00:00'}
        self.state = {'completed_at': '2026-10-20T13:00:00+00:00'}

    def tearDown(self):
        self.tmp.cleanup()

    def test_paginated_lookup_finds_receipt_beyond_first_100(self):
        first = [{'id': str(1000-i), 'channel_id': 'THREAD', 'author': {'id': 'OTHER'},
                  'content': 'other', 'timestamp': '2026-10-20T13:02:00+00:00'} for i in range(100)]
        get = Mock(side_effect=[first, [self.message]])
        result = q.find_notice(self.job, 'THREAD', 'nonce', 'receipt', 'ARES', get)
        self.assertEqual(result['message']['id'], 'M')
        self.assertTrue(result['complete'])
        self.assertEqual(result['pages'], 2)
        self.assertIn('before=901', get.call_args_list[-1].args[0])

    def test_lookup_does_not_treat_bad_history_as_absence(self):
        with self.assertRaises(ValueError):
            q.find_notice(self.job, 'THREAD', 'nonce', 'receipt', 'ARES', Mock(return_value={}))

    def test_retry_after_complete_absence_keeps_same_nonce_and_canonical_ua(self):
        response = io.BytesIO(json.dumps(self.message).encode()); response.status = 200
        with patch.object(q, 'BASE', self.base), patch.object(q, 'verify_final'), patch.object(q, 'completion_text', return_value='receipt'), patch('ares_campaign_v3.shein_channel_authority._get', side_effect=[{'id': 'ARES'}, [], self.message]), patch('pathlib.Path.read_text', return_value='DISCORD_BOT_TOKEN=offline-only'), patch('urllib.request.urlopen', return_value=response) as post:
            q.notify(self.job, self.state)
        request = post.call_args.args[0]
        self.assertEqual(request.get_header('User-agent'), 'MGS-Ares/1.0')
        payload = json.loads(request.data)
        self.assertEqual(payload['nonce'], 'sq12345')
        self.assertTrue(payload['enforce_nonce'])
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        self.assertEqual(self.job['status'], 'DELIVERED')
        self.assertNotIn('last_error_type', self.job)
        self.assertNotIn('retry_after_epoch', self.job)

    def test_lost_post_response_is_reconciled_without_second_post(self):
        with patch.object(q, 'BASE', self.base), patch.object(q, 'verify_final'), patch.object(q, 'completion_text', return_value='receipt'), patch('ares_campaign_v3.shein_channel_authority._get', side_effect=[{'id': 'ARES'}, [self.message], self.message]), patch('urllib.request.urlopen') as post:
            q.notify(self.job, self.state)
        post.assert_not_called()
        self.assertEqual(self.job['notification'], 'M')

    def test_repeated_history_cursor_never_proves_absence(self):
        rows = [{'id': str(1000-i), 'channel_id': 'THREAD', 'author': {'id': 'OTHER'},
                 'content': 'other', 'timestamp': '2026-10-20T13:02:00+00:00'} for i in range(100)]
        with self.assertRaisesRegex(ValueError, 'pagination'):
            q.find_notice(self.job, 'THREAD', 'nonce', 'receipt', 'ARES', Mock(return_value=rows))

    def test_attention_is_single_verified_infra_embed(self):
        self.job['delivery_attention_required'] = True
        result = Mock(returncode=0, stdout='ok message_id=42')
        read = {'id': '42', 'content': '', 'embeds': [{'title': 'REPORT-INFRA'}], 'mentions': []}
        with patch.object(q, 'BASE', self.base), patch.object(q.subprocess, 'run', return_value=result) as send, patch('ares_campaign_v3.shein_channel_authority._get', return_value=read) as get:
            q.delivery_attention(self.job)
            q.delivery_attention(self.job)
        self.assertEqual(send.call_count, 1)
        get.assert_called_once_with('/channels/1498132022634483894/messages/42')
        self.assertEqual(self.job['delivery_alert_message_id'], '42')

    def test_exhausted_retries_do_not_send_again(self):
        self.job['delivery_attempts'] = 3
        with patch.object(q, 'BASE', self.base), patch.object(q, 'verify_final'), patch.object(q, 'completion_text', return_value='receipt'), patch('ares_campaign_v3.shein_channel_authority._get', side_effect=[{'id': 'ARES'}, []]), patch('urllib.request.urlopen') as post:
            with self.assertRaises(ValueError):
                q.notify(self.job, self.state)
        post.assert_not_called()
        self.assertTrue(self.job.get('delivery_attention_required'))


if __name__ == '__main__':
    unittest.main()
