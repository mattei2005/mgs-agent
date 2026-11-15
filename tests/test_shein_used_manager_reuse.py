"""Offline: explicit grouped reuse is independent of cross-account reference."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_grouped_media as grouped
import ares_manager_storage_standard as standard


class UsedManagerReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        op = self.base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json'
        op.parent.mkdir(parents=True)
        op.write_text(json.dumps({'grouped_manager_media_policy': {
            'enabled': True, 'approved_by': '344196393512075265'}}))
        self.profile = {'language': 'EN', 'manager_code': 'G006'}
        self.slot = {'operation': 'SHEIN_US_EN', 'manager_code': 'g006',
                     'manager_name': 'Nicolas', 'format': 'VID'}
        self.folder = {'id': 'registered-used', 'name': 'NICOLAS - Usados'}
        self.ops = SimpleNamespace(drive_file_readback=lambda token, fid: self.folder)
        self.request = {'mode': 'clone_prestaged', 'quantity': 1,
                        'manager_media_folder_id': 'registered-used',
                        'campaign_groups': [{'files': ['SHEIN_US_EN_VID_PRODUCT_PV_001.mp4'],
                                             'product_label': 'PRODUCT', 'primary_text': 'EXACT'}]}
        self.find = self.enterContext(patch.object(standard, 'find_slot', return_value=(self.slot, 'used')))
        self.drive = self.enterContext(patch.object(standard.storage, 'drive', return_value=object()))
        self.validate = self.enterContext(patch.object(standard, 'validate_folder', return_value=self.folder))
        self.dest = self.enterContext(patch.object(standard, 'destination', return_value='registered-used'))

    def resolve(self):
        return grouped.manager_folder(self.request, self.profile, self.base, self.ops, 'fake-offline-token')

    def test_explicit_same_account_used_reuse_without_fictitious_source(self):
        before = copy.deepcopy(self.request)
        self.assertEqual(self.resolve(), self.folder)
        self.assertEqual(self.request, before)
        self.assertNotIn('source_account', self.request)
        self.assertEqual(self.validate.call_count, 2)
        self.assertEqual(self.validate.call_args_list[0].kwargs,
                         {'operation': 'SHEIN_US_EN', 'manager': 'G006'})
        self.assertEqual(self.validate.call_args_list[1].kwargs,
                         {'operation': 'SHEIN_US_EN', 'fmt': 'VID', 'manager': 'G006', 'state': 'used'})

    def test_missing_groups_still_rejected(self):
        self.request.pop('campaign_groups')
        with self.assertRaises(ValueError): self.resolve()
        self.validate.assert_not_called()

    def test_duplicate_files_still_rejected(self):
        self.request['campaign_groups'][0]['files'] *= 2
        with self.assertRaises(ValueError): self.resolve()
        self.validate.assert_not_called()

    def test_wrong_mode_still_rejected(self):
        self.request['mode'] = 'pure_clone'
        with self.assertRaises(ValueError): self.resolve()
        self.validate.assert_not_called()

    def test_native_partition_guard_not_bypassed(self):
        self.validate.side_effect = standard.StandardError('STANDARD_FOLDER_PARTITION')
        with self.assertRaisesRegex(standard.StandardError, 'STANDARD_FOLDER_PARTITION'): self.resolve()
        self.validate.assert_called_once()

    def test_exclusive_behavior_unchanged(self):
        self.find.return_value = (self.slot, 'exclusive')
        self.assertEqual(self.resolve(), self.folder)
        self.assertEqual(self.validate.call_args.kwargs['state'], 'exclusive')

    def test_cross_account_grouped_reference_still_supported(self):
        self.request.update(mode='from_zero_prestaged', source_account='real-reference')
        self.assertEqual(self.resolve(), self.folder)
        self.assertEqual(self.validate.call_args.kwargs['state'], 'used')

    def test_policy_authority_required(self):
        p = self.base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json'
        p.write_text(json.dumps({'grouped_manager_media_policy': {'enabled': False}}))
        with self.assertRaisesRegex(ValueError, 'policy unavailable'): self.resolve()
        self.validate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
