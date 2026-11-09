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
        binding = {'source_parent': 'old', 'destination_parent': 'ready',
                   'metadata_before': self.meta, 'authority': c.AUTHORITY}
        journal = Mock(data={'intents': {'consolidate:source': {'binding': binding, 'id': 'source'}}})
        with patch.object(c.f, 'rpc_once') as rpc:
            c.move_once(Mock(), self.d, journal, 'source', 'old', 'ready', self.meta)
            rpc.assert_not_called()
            journal.landed.assert_not_called()

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


class CanonicalBucketTests(unittest.TestCase):
    def setUp(self):
        self.d = Mock()
        self.tree = {'op': [{'id': 'img', 'name': 'IMG', 'mimeType': c.b.FOLDER}],
                     'img': [{'id': 'ready', 'name': '01_READY', 'mimeType': c.b.FOLDER}]}
        self.d.listing.side_effect = lambda parent: copy.deepcopy(self.tree.get(parent, []))

    def test_existing_bucket(self):
        self.assertEqual(c.destination_for_path(self.d.listing, 'op', ['IMG', '01_READY']), 'ready')

    def test_missing_format_read_only_plan(self):
        self.assertIsNone(c.destination_for_path(self.d.listing, 'op', ['VID', '99_LEGACY'], allow_missing=True))
        self.d.api.assert_not_called()

    def test_missing_format_strict_rejected(self):
        with self.assertRaises(c.b.ArchiveError):
            c.destination_for_path(self.d.listing, 'op', ['VID', '01_READY'])

    def test_missing_status_read_only_plan(self):
        self.assertIsNone(c.destination_for_path(self.d.listing, 'op', ['IMG', '99_LEGACY'], allow_missing=True))

    def test_duplicate_format_not_missing(self):
        self.tree['op'] *= 2
        with self.assertRaises(c.b.ArchiveError):
            c.destination_for_path(self.d.listing, 'op', ['IMG', '01_READY'], allow_missing=True)

    def test_wrong_mime_rejected(self):
        self.tree['op'][0]['mimeType'] = 'text/plain'
        with self.assertRaises(c.b.ArchiveError):
            c.destination_for_path(self.d.listing, 'op', ['IMG', '01_READY'], allow_missing=True)

    def test_provision_occurs_only_after_streams_and_strict_readback(self):
        import tempfile
        from pathlib import Path
        candidate = {'operation_id': 'op', 'records': {'source': {
            'destination_path': ['VID', '01_READY'], 'destination_parent': None}}}
        events = []
        def preflight(*args, **kwargs):
            if kwargs.get('allow_missing'):
                return candidate
            events.append('strict')
            raise c.b.ArchiveError('STOP_AFTER_STRICT_TEST')
        def folder(owner, sa, parent, name, journal):
            events.append(name)
            return 'folder-' + name
        with tempfile.TemporaryDirectory() as td, patch.object(c, 'HOME', Path(td)), \
             patch.object(c, 'authority'), patch.object(c, 'enabled', return_value=True), \
             patch.object(c.b, 'read_json', side_effect=lambda path, default=None: default), patch.object(c.b, 'atomic_json'), \
             patch.object(c.transport, 'Journal'), patch.object(c, 'preflight', side_effect=preflight), \
             patch.object(c, 'streams', side_effect=lambda *args: events.append('streams')), \
             patch.object(c, 'canonical_folder', side_effect=folder), patch.object(c, 'move_once') as move:
            with self.assertRaisesRegex(c.b.ArchiveError, 'STOP_AFTER_STRICT_TEST'):
                c.consolidate(Mock(), Mock(), 'generation')
            self.assertEqual(events, ['streams', 'VID', '01_READY', 'strict'])
            move.assert_not_called()

    def test_failed_streams_never_provision(self):
        import tempfile
        from pathlib import Path
        candidate = {'operation_id': 'op', 'records': {'source': {
            'destination_path': ['VID', '01_READY'], 'destination_parent': None}}}
        with tempfile.TemporaryDirectory() as td, patch.object(c, 'HOME', Path(td)), \
             patch.object(c, 'authority'), patch.object(c, 'enabled', return_value=True), \
             patch.object(c.b, 'read_json', side_effect=lambda path, default=None: default), patch.object(c.b, 'atomic_json'), \
             patch.object(c.transport, 'Journal'), patch.object(c, 'preflight', return_value=candidate), \
             patch.object(c, 'streams', side_effect=c.b.ArchiveError('BAD_BYTES')), \
             patch.object(c, 'canonical_folder') as create:
            with self.assertRaisesRegex(c.b.ArchiveError, 'BAD_BYTES'):
                c.consolidate(Mock(), Mock(), 'generation')
            create.assert_not_called()

    def test_noncanonical_path_rejected(self):
        for path in [['VID', 'CUSTOM'], ['OTHER', '01_READY'], ['VID']]:
            with self.assertRaises(c.b.ArchiveError):
                c.destination_for_path(self.d.listing, 'op', path, allow_missing=True)


class MaintenanceIntegrationTests(unittest.TestCase):
    def run_tick(self, apply):
        import contextlib
        import tempfile
        from pathlib import Path
        import mgs_flat_maintenance as m
        @contextlib.contextmanager
        def lease():
            yield {'claims': {}}
        @contextlib.contextmanager
        def queue(**kwargs):
            yield object()
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            receipt = home / 'maintenance' / 'generation' / 'receipt-state.json'
            receipt.parent.mkdir(parents=True)
            receipt.write_text('{"status":"verified"}')
            def read(path, default=None):
                if path == receipt:
                    return {'status': 'verified'}
                if str(path).endswith('result.json'):
                    return {}
                return default if default is not None else {}
            with patch.object(m, 'HOME', home), patch.object(m.f, 'authority'), \
                 patch.object(m.flat, 'policy', return_value={'active': True}), \
                 patch.object(m.intake, 'locked_state', lease), \
                 patch.object(m.b, 'queue_lock', queue), \
                 patch.object(m.b, 'read_json', side_effect=read), \
                 patch.object(m.b, 'atomic_json'), patch.object(m.b, 'Drive'), \
                 patch.object(m.cut, 'inventory', return_value={}), \
                 patch.object(m.t, 'OwnerDrive') as owner, \
                 patch.object(c, 'enabled', return_value=True), \
                 patch.object(c, 'consolidate', return_value={
                     'generation': 'generation', 'files': 2}) as consolidate:
                result = m.run(apply)
                return result, owner.call_count, consolidate.call_count

    def test_dry_run_never_enters_private_consolidation(self):
        result, owners, writes = self.run_tick(False)
        self.assertEqual((owners, writes), (0, 0))
        self.assertFalse(result['apply'])

    def test_existing_lane_retries_one_accepted_generation(self):
        result, owners, writes = self.run_tick(True)
        self.assertEqual((owners, writes), (1, 1))
        self.assertEqual(result['consolidated_generation'], 'generation')
        self.assertEqual(result['delete_writes'], 0)


if __name__ == '__main__':
    unittest.main()
