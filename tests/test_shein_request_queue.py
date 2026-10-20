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
        self.assertEqual(q.dependencies(self.req, '123', self.base), [])

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
