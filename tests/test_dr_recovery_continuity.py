import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, '/root/mgs-agent/scripts')
import mgs_dr_recovery_continuity as m  # pyright: ignore[reportMissingImports]
from mgs_automation_continuity import Queue  # pyright: ignore[reportMissingImports]
from mgs_automation_supervisor import drive  # pyright: ignore[reportMissingImports]


class DRReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / ('reports/automation-recovery-' + m.KEY)
        self.root.mkdir(parents=True)
        self.job = {'id': m.JOB, 'enabled': True, 'state': 'scheduled',
                    'last_run_at': m.LAST_RUN, 'last_dispatch': {'scheduled_at': m.SLOT},
                    'last_status': 'error'}
        self.execution = {'operation': m.KEY, 'returncode': 0,
                          'command': 'canonical backup --mode quick --no-retention'}
        self.result = {'status': 'PASS', 'mode': 'quick', 'tier': 'hourly',
                       'remote_file_id': m.FILE, 'remote_size_bytes': int(m.SIZE),
                       'retention_applied': False, 'retention_trashed_count': 0}
        self.prior = {'operation': m.KEY, 'canonical_result': {'archive_sha256_stream_verified': True}}
        self.remote = {'id': m.FILE, 'trashed': False, 'parents': [m.PARENT], 'size': m.SIZE,
                       'md5Checksum': m.MD5, 'sha256Checksum': m.SHA,
                       'appProperties': {'sha256': m.SHA}}
        self.ack_meta = {'id': m.ACK, 'trashed': False, 'parents': [m.ACK_PARENT]}
        self.ack = {'file_id': m.FILE, 'parent_id': m.PARENT, 'sha256': m.SHA, 'md5': m.MD5,
                    'size': m.SIZE, 'status': 'verified', 'tier': 'hourly',
                    'schema': 'mgs.backup.direct.archive.ack.v1', 'canonical_sa_upload': True,
                    'independent_sa_stream_verified': True, 'archive_trash_enabled': False}
        self.message = {'id': m.REPORT, 'channel_id': m.CHANNEL,
                        'author': {'id': '1496296175014252634'}, 'content': '', 'mentions': [],
                        'embeds': [{'description': m.FILE}]}
        self.calls = []
        self.save()
        p = patch.object(m, 'native_contract_hash', return_value=m.CONTRACT)
        p.start()
        self.addCleanup(p.stop)

    def save(self):
        for name, value in [('canonical-execution.json', self.execution),
                            ('canonical-retry.stdout', self.result),
                            ('independent-readback.json', self.prior)]:
            (self.root / name).write_text(json.dumps(value))

    def read(self, fid, media=False):
        self.calls.append((fid, media))
        return self.ack if media else self.remote if fid == m.FILE else self.ack_meta

    def get(self, method, url):
        self.assertEqual(method, 'GET')
        self.assertEqual(url, f'https://discord.com/api/v10/channels/{m.CHANNEL}/messages/{m.REPORT}')
        return self.message

    def observe(self, job=None):
        return m.observation(job or self.job, base=self.base, reader=self.read, getter=self.get)

    def test_live_receipt_without_upload_or_scheduler_rewrite(self):
        before = copy.deepcopy(self.job)
        r = self.observe()
        self.assertTrue(r['verified'])
        self.assertFalse(r['evidence']['historical_snapshot_recreated'])
        self.assertEqual(r['slot'], m.SLOT)
        self.assertEqual(self.job, before)
        self.assertEqual(self.calls, [(m.FILE, False), (m.ACK, False), (m.ACK, True)])

    def test_scope_drift_and_later_slot_reject_before_network(self):
        for change in ({'id': 'other'}, {'enabled': False}, {'state': 'paused'},
                       {'state': 'completed'}, {'fire_claim': 'active'},
                       {'last_run_at': 'later'}, {'last_dispatch': {'scheduled_at': 'later'}}):
            self.assertIsNone(self.observe(self.job | change))
        with patch.object(m, 'native_contract_hash', return_value='changed'):
            self.assertIsNone(self.observe())
        self.assertEqual(self.calls, [])

    def test_local_receipts_must_prove_canonical_no_retention_success(self):
        for target in (self.execution, self.result, self.prior):
            original = copy.deepcopy(target)
            for key in list(target):
                target[key] = None
                self.save()
                self.assertIsNone(self.observe(), key)
                target.clear()
                target.update(copy.deepcopy(original))
        self.assertEqual(self.calls, [])

    def test_remote_drift_rejects(self):
        original = copy.deepcopy(self.remote)
        for key in original:
            self.remote[key] = None
            self.assertIsNone(self.observe(), key)
            self.remote = copy.deepcopy(original)

    def test_ack_identity_location_and_content_reject(self):
        for target in (self.ack_meta, self.ack):
            original = copy.deepcopy(target)
            for key in original:
                target[key] = None
                self.assertIsNone(self.observe(), key)
                target.clear()
                target.update(copy.deepcopy(original))

    def test_report_identity_and_delivery_reject(self):
        original = copy.deepcopy(self.message)
        for key, value in [('id', 'other'), ('channel_id', 'other'), ('author', {}),
                           ('content', 'unexpected'), ('mentions', [{}]), ('embeds', [])]:
            self.message = original | {key: value}
            self.assertIsNone(self.observe(), key)
        self.message = original | {'embeds': [{'description': 'other backup'}]}
        self.assertIsNone(self.observe())

    def test_failed_read_stays_pending(self):
        def failed(*args):
            raise OSError('read unavailable')
        self.assertIsNone(m.observation(self.job, base=self.base, reader=failed, getter=self.get))

    def test_isolated_independent_supervisor_closure(self):
        obs = self.observe()
        q = Queue(self.base / 'queue.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(obs['target'], obs['source'], 'fixture', now=obs['at'] - 100)
        def forbidden(*args):
            self.fail('No business runner needed for verified receipt')
        drive(q, {obs['target']: obs}, forbidden, lambda: False, lambda _: False,
              lambda *_: None, now=obs['at'], max_jobs=0)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')


if __name__ == '__main__':
    unittest.main()
