"""Legacy pilot's empty archive path is not its frozen source ancestry."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ares_archive_bridge as b
import ares_archive_locations as loc
import mgs_archive_layout_cutover as layout


class RelocatedPilot(unittest.TestCase):
    def fixture(self):
        parent = 'frozen-parent'
        before = {'id': b.PILOT, 'name': 'pilot.mp4', 'mimeType': 'video/mp4',
                  'size': '7', 'md5Checksum': b.PILOT_MD5, 'sha256Checksum': b.PILOT_SHA,
                  'createdTime': '2026-10-20T09:15:22.981Z', 'version': '12',
                  'parents': [parent], 'driveId': b.SOURCE_DRIVE, 'trashed': False}
        asset = {'sourceId': b.PILOT, 'sourceParentId': parent, 'name': before['name'],
                 'mimeType': before['mimeType'], 'size': before['size'], 'md5': b.PILOT_MD5,
                 'sha256': b.PILOT_SHA, 'sourceCreatedTime': before['createdTime'],
                 'version': '12', 'relativeParent': [], 'role': 'clean'}
        meta = {k: v for k, v in before.items() if k != 'driveId'}
        meta.update(version='14', owners=[{'emailAddress': b.ACCOUNT}])
        snapshot = {'schema': 'mgs.archive.stock.snapshot.v1', 'objects': {
            b.PILOT: before, parent: {'id': parent, 'name': 'Nicolas',
                'parents': [b.SOURCE_ROOT], 'mimeType': b.FOLDER,
                'driveId': b.SOURCE_DRIVE, 'trashed': False}}}
        proof = {'status': 'same_ids_verified', 'snapshot_sha256': layout.ba.sha(snapshot),
                 'stock_root_id': 'stock-root', 'native_snapshot_id': 'native-snapshot'}
        job = {'jobId': '526d7a2a007c1fed4b2a9147f92d62b4', 'kind': 'canary',
               'lineageId': 'PILOT-ONLY', 'assets': [asset]}
        return asset, meta, snapshot, proof, job

    def verify(self, change=None):
        asset, meta, snapshot, proof, job = self.fixture()
        if change:
            change(asset, meta, snapshot, proof, job)
        proof['snapshot_sha256'] = layout.ba.sha(snapshot)
        d = Mock()
        d.meta.return_value = {'lastModifyingUser': {
            'permissionId': b.PUBLISHER_PERMISSION_IDS[b.CANONICAL_SA]}}
        d.raw.return_value = b.canonical(snapshot)
        def read(path, default=None):
            return snapshot if path == layout.SNAPSHOT else proof
        with patch.object(loc, 'active', return_value={'same_ids_verified': True, 'stock_root_id': 'stock-root'}), \
             patch.object(b, 'read_json', side_effect=read), \
             patch.object(loc, 'stock_metadata_allowed', return_value=True), \
             patch.object(loc, 'stock_parent', return_value=['Nicolas']), \
             patch.object(b, 'control_object_scope', return_value=True), \
             patch.object(b, 'config_load', return_value={'control_folder_id': 'control'}):
            return layout.verify_relocated(d, meta, asset, job=job)

    def test_original_pilot_empty_destination_path_uses_frozen_source_path(self):
        self.assertTrue(self.verify())

    def test_wrong_job_cannot_bypass_relative_path(self):
        with self.assertRaises(b.ArchiveError):
            self.verify(lambda a, m, s, p, j: j.update(jobId='other-job'))

    def test_noncanary_cannot_bypass_relative_path(self):
        with self.assertRaises(b.ArchiveError):
            self.verify(lambda a, m, s, p, j: j.update(kind='production'))

    def test_wrong_pilot_hash_rejected(self):
        with self.assertRaises(b.ArchiveError):
            self.verify(lambda a, m, s, p, j: a.update(sha256='0' * 64))

    def test_missing_frozen_parent_rejected(self):
        with self.assertRaises(b.ArchiveError):
            self.verify(lambda a, m, s, p, j: s['objects'].pop('frozen-parent'))

    def test_changed_frozen_parent_name_rejected(self):
        with self.assertRaises(b.ArchiveError):
            self.verify(lambda a, m, s, p, j: s['objects']['frozen-parent'].update(name='Different'))

    def test_cycle_in_frozen_parent_rejected(self):
        with self.assertRaises(b.ArchiveError):
            self.verify(lambda a, m, s, p, j: s['objects']['frozen-parent'].update(parents=['frozen-parent']))

    def test_regular_asset_path_still_required(self):
        self.assertTrue(self.verify(lambda a, m, s, p, j: (a.update(relativeParent=['Nicolas']), j.update(kind='production'))))

    def test_native_snapshot_status_still_required(self):
        with self.assertRaises(b.ArchiveError):
            self.verify(lambda a, m, s, p, j: p.update(status='pending'))


if __name__ == '__main__':
    unittest.main()
