import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_request_queue as q


class RequestQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'data/ares/meta-ads'
        self.inv = self.base / 'data/ares/creative-ops/inventory/assets.jsonl'
        self.inv.parent.mkdir(parents=True)
        self.req = {'request_id': 'shein-1234', 'account': '123', 'authorized_by': 'N',
                    'source_channel_id': 'CHAN', 'source_thread_id': 'THREAD',
                    'manager_media_folder_id': 'F', 'campaign_groups': [
                        {'files': ['A.mp4'], 'product_label': 'A', 'primary_text': 'literal'}]}
        self.rows = [{'asset_id': 'A', 'canonical_filename': 'A.mp4',
                      'reservation_request_id': 'shein-1111', 'reservation_authority': 'N',
                      'status': '02_TESTING', 'test_history': [{'campaign_id': 'old'}]}]
        self.inv.write_text(json.dumps(self.rows[0]) + '\n')
        self.state('shein-1111', 'RECOVERY_PENDING')

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, rid, phase):
        p = self.root / 'state/shein-campaigns/single-clone' / rid / 'state.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        s = {'phase': phase, 'request': {'request_id': rid, 'account': '456',
             'authorized_by': 'N', 'source_channel_id': 'CHAN'},
             'summary': {'campaigns': [{'campaign_id': 'old'}]}}
        p.write_text(json.dumps(s))
        return p

    def test_active_dependency_is_queued_without_reservation_theft(self):
        before = self.inv.read_bytes()
        result = q.dependencies(self.req, '123', self.base)
        self.assertEqual(result, ['shein-1111'])
        self.assertEqual(before, self.inv.read_bytes())

    def test_terminal_dependency_releases_wait(self):
        self.state('shein-1111', 'COMPLETE_FUTURE_ACTIVE')
        self.assertEqual(q.dependencies(self.req, '123', self.base), [])

    def test_missing_state_is_not_terminal(self):
        self.state('shein-1111', 'RECOVERY_PENDING').unlink()
        self.assertEqual(q.dependencies(self.req, '123', self.base), ['shein-1111'])

    def test_terminal_without_summary_is_not_complete(self):
        p = self.state('shein-1111', 'COMPLETE_FUTURE_ACTIVE')
        s = json.loads(p.read_text()); s.pop('summary'); p.write_text(json.dumps(s))
        self.assertEqual(q.dependencies(self.req, '123', self.base), ['shein-1111'])

    def test_cross_partition_cannot_be_claimed(self):
        self.state('shein-1111', 'COMPLETE_FUTURE_ACTIVE')
        p = self.root / 'state/shein-campaigns/single-clone/shein-1111/state.json'
        s = json.loads(p.read_text()); s['request']['source_channel_id'] = 'OTHER'; p.write_text(json.dumps(s))
        with self.assertRaisesRegex(ValueError, 'partition'):
            q.dependencies(self.req, '123', self.base)

    def test_enqueue_is_idempotent_and_request_immutable(self):
        one = q.enqueue(self.req, 'campaign', ['shein-1111'], self.base)
        two = q.enqueue(self.req, 'campaign', ['shein-1111'], self.base)
        self.assertEqual(one['request_id'], two['request_id'])
        p = q.job_path(self.base, self.req['request_id'])
        saved = json.loads(p.read_text())
        self.assertEqual(saved['request'], self.req)
        changed = copy.deepcopy(self.req); changed['budget_usd'] = '999'
        with self.assertRaisesRegex(ValueError, 'immutable'):
            q.enqueue(changed, 'campaign', [], self.base)

    def test_same_account_recovery_is_a_dependency(self):
        p = self.state('shein-2222', 'POSTPROCESS_PENDING')
        s = json.loads(p.read_text()); s['request']['account'] = '123'; p.write_text(json.dumps(s))
        self.assertIn('shein-2222', q.dependencies(self.req, '123', self.base))

    def test_no_global_serialization_of_unrelated_accounts(self):
        self.inv.write_text('')
        self.state('shein-2222', 'POSTPROCESS_PENDING')
        request = {k: v for k, v in self.req.items() if k not in {'campaign_groups', 'manager_media_folder_id'}}
        self.assertEqual(q.dependencies(request, '123', self.base), [])

    def test_terminal_claim_preserves_history_and_unrelated_rows(self):
        from unittest.mock import patch, Mock
        self.state('shein-1111', 'COMPLETE_FUTURE_ACTIVE')
        extra = {'asset_id': 'Z', 'canonical_filename': 'Z.mp4', 'reservation_request_id': 'elsewhere'}
        self.inv.write_text('\n'.join(json.dumps(x) for x in self.rows + [extra]) + '\n')
        config = self.root / 'engine-v3/config.json'; config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'accounts': {'123': {'token_item': 'test-only'}}}))
        common = Mock(); common.get_token_from_1password.return_value = ('fake', 'field')
        ops = Mock()
        ops.atomic_inventory.side_effect = lambda rows: self.inv.write_text('\n'.join(json.dumps(x) for x in rows) + '\n')
        with patch('ares_campaign_v3.shein_single_clone._load_common', return_value=common), patch('ares_campaign_v3.shein_media_handoff._ops', return_value=ops):
            q.claim_terminal(self.req, '123', self.base)
        rows = [json.loads(x) for x in self.inv.read_text().splitlines()]
        self.assertEqual(rows[0]['reservation_request_id'], self.req['request_id'])
        self.assertEqual(rows[0]['test_history'], self.rows[0]['test_history'])
        self.assertEqual(rows[1], extra)
        self.assertEqual(rows[0]['reservation_history'][-1]['previous_request_id'], 'shein-1111')

    def test_failed_dependency_never_releases_reservation(self):
        self.state('shein-1111', 'FAILED')
        self.assertEqual(q.dependencies(self.req, '123', self.base), ['shein-1111'])

    def test_different_author_same_partition_can_wait(self):
        req = {**self.req, 'authorized_by': 'OTHER_HUMAN'}
        self.assertEqual(q.dependencies(req, '123', self.base), ['shein-1111'])

    def test_active_claim_is_rejected_without_side_effect(self):
        before = self.inv.read_bytes()
        with self.assertRaises(BlockingIOError):
            q.claim_terminal(self.req, '123', self.base)
        self.assertEqual(before, self.inv.read_bytes())

    def test_waiting_tick_never_calls_campaign_runner(self):
        from unittest.mock import patch
        q.enqueue(self.req, 'campaign', ['shein-1111'], self.base)
        job = json.loads(q.job_path(self.base, self.req['request_id']).read_text())
        with patch('ares_campaign_v3.shein_single_clone.lookup_account', return_value={'account_id': '123'}), patch.object(q.subprocess, 'run') as runner:
            q.tick(job, self.base)
        runner.assert_not_called()
        self.assertEqual(job['status'], 'WAITING')

    def test_ready_tick_resumes_original_request_via_central_runner(self):
        from unittest.mock import patch, Mock
        self.state('shein-1111', 'COMPLETE_FUTURE_ACTIVE')
        q.enqueue(self.req, 'campaign', [], self.base)
        job = json.loads(q.job_path(self.base, self.req['request_id']).read_text())
        completed = Mock(stdout=json.dumps({'status': 'RECOVERY_PENDING', 'retry_after_seconds': 305}), returncode=0)
        with patch('ares_campaign_v3.shein_single_clone.lookup_account', return_value={'account_id': '123'}), patch.object(q, 'claim_terminal') as claim, patch.object(q.subprocess, 'run', return_value=completed) as runner:
            q.tick(job, self.base)
        claim.assert_called_once()
        command = runner.call_args.args[0]
        self.assertIn('ares-shein-campaigns.py', command[1])
        self.assertEqual(command[2], 'campaign')
        self.assertEqual(json.loads(Path(command[4]).read_text()), self.req)
        self.assertEqual(job['request']['request_id'], self.req['request_id'])
        self.assertEqual(job['status'], 'RECOVERY_PENDING')

    def test_incomplete_final_proof_never_notifies(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            q.verify_final({'phase': 'COMPLETE_FUTURE_ACTIVE', 'summary': {
                'campaigns': [{'campaign_id': 'C'}]}, 'final_readback': []})

    def test_exact_final_media_proof_required(self):
        value = {'phase': 'COMPLETE_FUTURE_ACTIVE', 'request': {'status': 'ACTIVE'},
                 'summary': {'campaigns': [{'campaign_id': 'C'}], 'account_id': '123', 'ads': 1},
                 'final_readback': [{'campaign': {'id': 'C', 'account_id': '123', 'status': 'ACTIVE'},
                     'ads': {'data': [{'id': 'A', 'status': 'ACTIVE', 'creative': {'id': 'CR'}}]},
                     'adsets': {'data': [{'id': 'SET', 'status': 'ACTIVE'}]}}],
                 'media_qa': {'C': {'verified': True, 'ad_ids': ['OTHER'], 'creative_ids': ['CR']}}}
        with self.assertRaisesRegex(ValueError, 'QA'):
            q.verify_final(value)
        value['media_qa']['C']['ad_ids'] = ['A']
        q.verify_final(value)

    def test_native_exact_content_reconciles_without_nonce_or_resend(self):
        from unittest.mock import patch
        q.enqueue(self.req, 'campaign', [], self.base)
        job = json.loads(q.job_path(self.base, self.req['request_id']).read_text())
        job.update(delivery_intent_at='2026-10-20T13:06:00+00:00', native_completion_content='verified fixture receipt')
        message = {'id': 'M', 'channel_id': 'THREAD', 'content': 'verified fixture receipt', 'author': {'id': 'ARES'}}
        with patch.object(q, 'BASE', self.base), patch.object(q, 'verify_final'), patch('ares_campaign_v3.shein_channel_authority._get', side_effect=[{'id': 'ARES'}, [message], message]), patch('urllib.request.urlopen') as post:
            q.notify(job, {'completed_at': 'time'})
        post.assert_not_called()
        self.assertEqual(job['status'], 'DELIVERED')
        self.assertEqual(job['notification'], 'M')

    def test_other_author_cannot_satisfy_native_delivery(self):
        from unittest.mock import patch
        q.enqueue(self.req, 'campaign', [], self.base)
        job = json.loads(q.job_path(self.base, self.req['request_id']).read_text())
        job.update(delivery_intent_at='2026-10-20T13:06:00+00:00', native_completion_content='verified fixture receipt')
        message = {'id': 'M', 'channel_id': 'THREAD', 'content': 'verified fixture receipt', 'author': {'id': 'OTHER'}}
        with patch.object(q, 'BASE', self.base), patch.object(q, 'verify_final'), patch('ares_campaign_v3.shein_channel_authority._get', side_effect=[{'id': 'ARES'}, [message]]), patch('urllib.request.urlopen') as post:
            with self.assertRaisesRegex(ValueError, 'uncertain'):
                q.notify(job, {'completed_at': 'time'})
        post.assert_not_called()
        self.assertNotEqual(job['status'], 'DELIVERED')

    def test_final_notice_contains_only_verified_completion(self):
        with self.assertRaises(ValueError):
            q.completion_text({'phase': 'POSTPROCESS_PENDING'})
        s = {'phase': 'COMPLETE_FUTURE_ACTIVE', 'request': {'source_number': 1},
             'summary': {'campaigns': [{'campaign_id': 'x'}], 'ads': 2,
                         'budget_usd': 20, 'account_id': '123', 'posts_preserved': False},
             'final_readback': [{'campaign': {'name': '004 - Product', 'status': 'ACTIVE'}}]}
        text = q.completion_text(s)
        self.assertIn('004', text)
        self.assertNotIn('queue', text)
        self.assertNotIn('PID', text)
        self.assertIn('US$20', text)


if __name__ == '__main__':
    unittest.main()
