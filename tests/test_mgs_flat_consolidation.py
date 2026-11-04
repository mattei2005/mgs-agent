import copy
import hashlib
import json
import unittest
from unittest.mock import patch, Mock
import mgs_flat_consolidation as c


class ConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.meta = {'id': 'source', 'name': 'image.jpg', 'mimeType': 'image/jpeg',
                     'size': '3', 'md5Checksum': 'm', 'sha256Checksum': 's',
                     'createdTime': 't', 'properties': {}, 'version': '2',
                     'parents': ['ready'], 'trashed': False,
                     'owners': [{'emailAddress': c.b.ACCOUNT}], 'permissions': []}
        self.asset = {'sourceId': 'source', 'name': 'image.jpg', 'mimeType': 'image/jpeg',
                      'size': '3', 'md5': 'm', 'sha256': 's', 'sourceCreatedTime': 't',
                      'sourceParentId': 'old', 'relativeParent': ['OP', 'IMG', '01_READY']}
        before = copy.deepcopy(self.meta)
        before['parents'] = ['old']
        self.snapshot = {'objects': {'source': {'metadata': before}}}
        self.job = {'jobId': 'job', 'assets': [self.asset]}
        chain = [{'id': 'ready', 'name': '01_READY', 'parents': ['fmt']},
                 {'id': 'fmt', 'name': 'IMG', 'parents': ['op']},
                 {'id': 'op', 'name': 'OP', 'parents': [c.ROOT]}]
        self.proof = {'records': {'source': {'metadata_after': copy.deepcopy(self.meta),
                            'snapshot_sha256': c.sha(self.snapshot),
                            'jobs': {'job': {'job_sha256': c.sha(self.job),
                                            'asset_sha256': c.sha(self.asset)}},
                            'full_streams_verified': True,
                            'hashes': {'size': '3', 'md5': 'm', 'sha256': 's'},
                            'destination_parent': 'ready', 'chain': chain}}}
        self.binding = {'phase': 'active', 'authority_message_id': c.AUTHORITY,
                        'processing_root_id': c.ROOT,
                        'proofs': [{'source_ids': ['source']}]}
        self.nodes = {x['id']: {**self.meta, **x, 'mimeType': c.b.FOLDER} for x in chain}
        self.nodes[c.ROOT] = {**self.meta, 'id': c.ROOT, 'mimeType': c.b.FOLDER,
                             'parents': ['1u58O4XYH2hgd9zUlDMP_8huuTkAjH3_W']}
        self.d = Mock()
        self.d.meta.side_effect = lambda fid: copy.deepcopy(self.nodes[fid])

    def verify(self):
        with patch.object(c.b, 'read_json', return_value=self.binding), \
             patch.object(c, 'read_proof', return_value=self.proof):
            return c.verify(self.d, self.meta, self.asset, self.job, self.snapshot)

    def test_valid_exact_binding(self):
        self.assertTrue(self.verify())

    def test_unknown_source_not_accepted(self):
        self.asset['sourceId'] = 'other'
        self.assertFalse(self.verify())

    def test_disabled_not_accepted(self):
        self.binding['phase'] = 'disabled'
        self.assertFalse(self.verify())

    def test_reject_authority_drift(self):
        self.binding['authority_message_id'] = 'other'
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_duplicate_source(self):
        self.binding['proofs'] *= 2
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_byte_drift(self):
        self.meta['sha256Checksum'] = 'wrong'
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_parent_drift(self):
        self.meta['parents'] = ['other']
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_job_drift(self):
        self.job['extra'] = 'changed'
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_snapshot_drift(self):
        self.snapshot['changed'] = True
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_chain_rename(self):
        self.nodes['op']['name'] = 'OP 2'
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_chain_move(self):
        self.nodes['op']['parents'] = ['other']
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_public(self):
        self.meta['permissions'] = [{'type': 'anyone'}]
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_owner(self):
        self.meta['owners'] = [{'emailAddress': 'wrong'}]
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_false_streams(self):
        self.proof['records']['source']['full_streams_verified'] = False
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_reject_version_regression(self):
        self.meta['version'] = '0'
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_missing_job(self):
        self.job = None
        with self.assertRaises(c.b.ArchiveError): self.verify()

    def test_move_unknown_intent_rejected(self):
        self.d.meta.side_effect = None
        self.d.meta.return_value = copy.deepcopy(self.meta)
        journal = Mock(data={'intents': {'consolidate:source': {'destination_parent': 'ready'}}})
        with self.assertRaises(c.b.ArchiveError):
            c.move_once(Mock(), self.d, journal, 'source', 'ready', 'other', self.meta)
        journal.intent.assert_not_called()

    def test_move_landed_replay_no_mutation(self):
        self.d.meta.side_effect = None
        self.d.meta.return_value = copy.deepcopy(self.meta)
        journal = Mock(data={'intents': {'consolidate:source': {'destination_parent': 'ready'}}})
        with patch.object(c.f, 'rpc_once') as rpc:
            c.move_once(Mock(), self.d, journal, 'source', 'old', 'ready', self.meta)
            rpc.assert_not_called()

    def test_unjournalled_landed_move_rejected(self):
        self.d.meta.side_effect = None
        self.d.meta.return_value = copy.deepcopy(self.meta)
        with self.assertRaises(c.b.ArchiveError):
            c.move_once(Mock(), self.d, Mock(data={'intents': {}}),
                        'source', 'old', 'ready', self.meta)

    def test_publisher_proof_digest_rejected(self):
        pin = {'proof_sha256': 'wrong', 'proof_file_id': 'proof', 'source_ids': ['source']}
        self.d.meta.side_effect = None
        self.d.meta.return_value = {'properties': {'mgsArchiveType': 'lineage_map'}}
        self.d.raw.return_value = b'{}'
        self.d._consolidation_proofs = {}
        with patch.object(c.b, 'require_publisher'), patch.object(c.b, 'control_object_scope', return_value=True):
            with self.assertRaises(c.b.ArchiveError): c.read_proof(self.d, pin)


if __name__ == '__main__':
    unittest.main()
