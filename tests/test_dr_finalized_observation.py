import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mgs_dr_recovery_continuity as m
from mgs_automation_continuity import Queue
from mgs_automation_supervisor import drive


class FinalizedObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / ('reports/automation-recovery-' + m.FINAL_KEY)
        self.root.mkdir(parents=True)
        self.job = {'id': m.JOB, 'enabled': True, 'state': 'scheduled',
                    'last_run_at': m.FINAL_LAST_RUN, 'last_dispatch': {'scheduled_at': m.FINAL_SLOT}}
        self.execution = {'operation': m.FINAL_KEY, 'returncode': 0,
                          'command': ['/usr/bin/python3', '/root/mgs-agent/scripts/mgs-offsite-backup.py', 'finalize-direct', '--remote-id', m.FINAL_FILE, '--expected-name', m.FINAL_NAME]}
        self.result = {'status': 'PASS', 'mode': 'quick', 'tier': 'hourly', 'remote_file_id': m.FINAL_FILE,
                       'remote_name': m.FINAL_NAME, 'remote_size_bytes': int(m.FINAL_SIZE),
                       'encrypted_sha256': m.FINAL_SHA, 'encrypted_md5': m.FINAL_MD5,
                       'archive_sha256_stream_verified': True, 'retention_applied': False,
                       'retention_trashed_count': 0, 'recovery': 'same_snapshot_existing_upload_finalized',
                       'archive_native_ack': {'file_id': m.FINAL_ACK, 'sha256': 'a' * 64}}
        self.remote = {'id': m.FINAL_FILE, 'name': m.FINAL_NAME, 'parents': [m.PARENT],
                       'trashed': False, 'size': m.FINAL_SIZE, 'md5Checksum': m.FINAL_MD5, 'sha256Checksum': m.FINAL_SHA}
        self.ack_meta = {'id': m.FINAL_ACK, 'parents': [m.ACK_PARENT], 'trashed': False,
                         'properties': {'mgsArchiveType': 'backup_direct_ack'}, 'sha256Checksum': 'a' * 64}
        self.ack = {'schema': 'mgs.backup.direct.archive.ack.v1', 'status': 'verified',
                    'file_id': m.FINAL_FILE, 'parent_id': m.PARENT, 'size': m.FINAL_SIZE,
                    'md5': m.FINAL_MD5, 'sha256': m.FINAL_SHA, 'tier': 'hourly',
                    'canonical_sa_upload': True, 'independent_sa_stream_verified': True, 'archive_trash_enabled': False}
        self.msg = {'id': '123', 'channel_id': m.CHANNEL, 'author': {'id': '1496296175014252634'},
                    'content': '', 'mentions': [], 'embeds': [{'description': m.FINAL_FILE}]}
        self.save()
        p = patch.object(m, 'native_contract_hash', return_value=m.CONTRACT)
        p.start()
        self.addCleanup(p.stop)

    def save(self):
        for name, obj in [('canonical-execution.json', self.execution), ('canonical-finalize.stdout', self.result),
                          ('independent-readback.json', {'operation': m.FINAL_KEY, 'GET_verified': True, 'report_infra_message_id': '123'})]:
            (self.root / name).write_text(json.dumps(obj))

    def read(self, fid, media=False):
        return self.ack if media else self.remote if fid == m.FINAL_FILE else self.ack_meta

    def observe(self, job=None):
        return m.observation(job or self.job, base=self.base, reader=self.read, getter=lambda *args: self.msg)

    def test_live_same_snapshot_evidence(self):
        obs = self.observe()
        self.assertTrue(obs['verified'])
        self.assertTrue(obs['evidence']['same_original_snapshot'])
        self.assertFalse(obs['evidence']['upload_replayed'])

    def test_paused_claimed_changed_or_later_slot_rejected(self):
        for change in [{'enabled': False}, {'state': 'paused'}, {'fire_claim': 'owned'},
                       {'last_run_at': 'later'}, {'last_dispatch': {'scheduled_at': 'later'}}]:
            self.assertIsNone(self.observe(self.job | change))
        with patch.object(m, 'native_contract_hash', return_value='drift'):
            self.assertIsNone(self.observe())

    def test_remote_ack_and_report_drift_rejected(self):
        for target in [self.remote, self.ack_meta, self.ack, self.msg]:
            prior = copy.deepcopy(target)
            for key in list(target):
                target[key] = None
                self.assertIsNone(self.observe(), key)
                target.clear()
                target.update(copy.deepcopy(prior))

    def test_execution_receipt_fields_required(self):
        for target in [self.execution, self.result]:
            prior = copy.deepcopy(target)
            for key in list(target):
                target[key] = None
                self.save()
                self.assertIsNone(self.observe(), key)
                target.clear()
                target.update(copy.deepcopy(prior))
            self.save()

    def test_isolated_queue_closes_without_business_writer(self):
        obs = self.observe()
        q = Queue(self.base / 'queue.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(obs['target'], obs['source'], 'fixture', now=obs['at'] - 100)
        def forbidden(*args):
            self.fail('must not replay backup')
        drive(q, {obs['target']: obs}, forbidden, lambda: False, lambda _: False, lambda *_: None,
              now=obs['at'], max_jobs=0)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')


class November23FinalizedObservationTests(FinalizedObservationTests):
    def setUp(self):
        slot, values = next(iter(m.FINALIZED_OCCURRENCES.items()))
        names = ('FINAL_KEY', 'FINAL_LAST_RUN', 'FINAL_FILE', 'FINAL_ACK',
                 'FINAL_NAME', 'FINAL_SHA', 'FINAL_MD5', 'FINAL_SIZE')
        values_patch = patch.multiple(m, FINAL_SLOT=slot, **dict(zip(names, values)))
        values_patch.start()
        self.addCleanup(values_patch.stop)
        super().setUp()

    def test_does_not_accept_previous_or_next_slot(self):
        for slot in ('2026-11-20T14:23:00-05:00', '2026-11-23T17:23:00-05:00'):
            self.assertIsNone(self.observe(self.job | {'last_dispatch': {'scheduled_at': slot}}))


if __name__ == '__main__':
    unittest.main()
