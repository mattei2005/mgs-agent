import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mgs_private_control_store as store
import ares_archive_bridge as bridge

spec = importlib.util.spec_from_file_location('backup_finalize_test', Path(__file__).resolve().parents[1] / 'scripts/mgs-offsite-backup.py')
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class AckMetadataTests(unittest.TestCase):
    def test_ambiguous_patch_already_landed_only_reads(self):
        d = Mock()
        props = {'mgsArchiveType': 'backup_direct_ack', 'sha256': 'a' * 64}
        d.api.side_effect = bridge.ArchiveError('DRIVE_HTTP_500')
        d.meta.return_value = {'properties': props}
        with patch.object(bridge, 'require_publisher'):
            store.publish_properties(d, 'same-id', props, 'backup_direct_ack')
        self.assertEqual(d.api.call_count, 1)
        d.meta.assert_called_once_with('same-id')

    def test_not_landed_retries_same_id_after_get(self):
        d = Mock()
        d.api.side_effect = [bridge.ArchiveError('DRIVE_HTTP_500'), {}]
        d.meta.return_value = {'properties': {}}
        with patch.object(bridge, 'require_publisher'), patch('time.sleep'):
            store.publish_properties(d, 'same-id', {'sha256': 'a'}, 'backup_direct_ack')
        self.assertEqual(d.api.call_args_list[0], d.api.call_args_list[1])
        self.assertEqual(d.meta.call_count, 1)

    def test_other_kind_and_rate_limit_not_retried(self):
        for kind, error in [('request', 'DRIVE_HTTP_500'), ('backup_direct_ack', 'DRIVE_HTTP_429')]:
            d = Mock()
            d.api.side_effect = bridge.ArchiveError(error)
            with self.assertRaises(bridge.ArchiveError):
                store.publish_properties(d, 'same-id', {}, kind)
            self.assertEqual(d.api.call_count, 1)
            d.meta.assert_not_called()

    def test_five_failure_limit_not_approached(self):
        d = Mock()
        d.api.side_effect = bridge.ArchiveError('DRIVE_HTTP_500')
        d.meta.return_value = {'properties': {}}
        with patch.object(bridge, 'require_publisher'), patch('time.sleep'), self.assertRaises(bridge.ArchiveError):
            store.publish_properties(d, 'same-id', {'sha256': 'a'}, 'backup_direct_ack')
        self.assertEqual(d.api.call_count, 3)

    def test_existing_media_resumes_only_properties(self):
        data = b'approved ACK bytes'
        import hashlib
        digest = hashlib.sha256(data).hexdigest()
        meta = {'id': 'same-id', 'name': 'ack.json', 'parents': ['parent'], 'trashed': False,
                'sha256Checksum': digest, 'properties': {'mgsArchiveType': 'private_control_slot',
                'expectedKind': 'backup_direct_ack', 'expectedSha256': digest}}
        after = copy.deepcopy(meta)
        after['properties'].update(store.publication_properties('backup_direct_ack', digest))
        d = Mock()
        d.one.return_value = {'id': 'same-id'}
        d.meta.side_effect = [meta, after]
        d.raw.return_value = data
        with patch.object(bridge, 'read_json', return_value={}), patch.object(store, 'validate_request'), patch.object(bridge, 'require_publisher'), patch.object(store.subprocess, 'run') as child:
            result = store.publish_sa(d, 'parent', 'ack.json', data, 'application/json', 'key', 'backup_direct_ack')
        self.assertEqual(result, 'same-id')
        child.assert_not_called()
        d.api.assert_called_once_with('PATCH', 'files/same-id', {'supportsAllDrives': 'true', 'fields': 'id'}, {'properties': store.publication_properties('backup_direct_ack', digest)})


class FinalizeTests(unittest.TestCase):
    def test_same_snapshot_finalization_and_hash_mismatch_gate(self):
        import mgs_private_backup_upload as private
        row = {'id': 'same-id', 'binding': {'name': 'exact-name', 'mode': 'quick', 'canary': False,
               'parent_id': 'parent', 'size': 10, 'md5': 'md5', 'sha256': 'sha'}}
        meta = {'id': 'same-id', 'name': 'exact-name', 'parents': ['parent'], 'trashed': False,
                'size': '10', 'md5Checksum': 'md5', 'sha256Checksum': 'sha', 'createdTime': '2026-11-20T19:00:00Z'}
        for hashes_ok in [False, True]:
            d = Mock()
            d.meta.return_value = meta
            d.hashes.return_value = {'size': '10', 'md5': 'md5', 'sha256': 'sha' if hashes_ok else 'bad'}
            d.raw.return_value = json.dumps({'file_id': 'same-id', 'sha256': 'sha', 'status': 'verified'}).encode()
            state = {'last_success': {'quick': {'created_at_utc': '2026-11-20T20:00:00Z', 'remote_file_id': 'newer'}}}
            with patch.object(backup, 'load_config', return_value={'state_path': 'fixture.json'}), patch.object(backup, 'acquire_lock', return_value=Mock()), patch.object(private, 'contract', return_value={'enabled': True}), patch.object(private, 'validate_slot'), patch.object(bridge, 'read_json', side_effect=[{'archiveRootId': 'root'}, {'intents': {'a': row}}]), patch.object(bridge, 'require_publisher'), patch.object(bridge, 'Drive', return_value=d), patch.object(private, 'publish_ack', return_value={'file_id': 'ack'}) as ack, patch.object(backup, 'state_load', return_value=state), patch.object(backup, 'atomic_json') as save, patch.object(backup, 'append_event'):
                if not hashes_ok:
                    with self.assertRaises(RuntimeError):
                        backup.finalize_direct_backup('same-id', 'exact-name')
                    ack.assert_not_called()
                    save.assert_not_called()
                else:
                    result = backup.finalize_direct_backup('same-id', 'exact-name')
                    self.assertEqual(result['remote_file_id'], 'same-id')
                    self.assertFalse(result['retention_applied'])
                    self.assertEqual(state['last_success']['quick']['remote_file_id'], 'newer')
                    self.assertIn('same-id', state['recovered_occurrences'])
                    save.assert_called_once()
            d.api.assert_not_called()

    def test_absent_or_duplicate_journal_fails_without_business_write(self):
        import mgs_private_backup_upload as private
        for intents in [{}, {'a': {'id': 'same-id'}, 'b': {'id': 'same-id'}}]:
            lock = Mock()
            with patch.object(backup, 'load_config', return_value={}), patch.object(backup, 'acquire_lock', return_value=lock), patch.object(private, 'contract', return_value={'enabled': True}), patch.object(bridge, 'read_json', side_effect=[{}, {'intents': intents}]), patch.object(private, 'publish_ack') as ack, patch.object(bridge, 'Drive') as drive:
                with self.assertRaises(RuntimeError):
                    backup.finalize_direct_backup('same-id', 'exact-name')
                drive.assert_not_called()
                ack.assert_not_called()
                lock.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()