"""Case-only manager interoperability; all partition/native guards stay active."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ares_manager_storage_standard as s


class ManagerCodeInteropTests(unittest.TestCase):
    def setUp(self):
        self.slot = {'operation': 'SHEIN_US_ES', 'format': 'IMG',
                     'manager_code': 'g006', 'manager_name': 'Nicolas',
                     'exclusive_id': 'exclusiveOffline006', 'used_id': 'usedOffline006',
                     'parent_id': 'imgOffline006', 'operation_id': 'opOffline006'}
        self.policy = {'schema': s.SCHEMA, 'authority_message_id': s.AUTHORITY,
                       'phase': 'active', 'stock_root_id': 'stockOffline006',
                       'slots': [self.slot]}
        self.metadata = {
            'exclusiveOffline006': {'id': 'exclusiveOffline006', 'name': 'NICOLAS - Exclusivos',
                'mimeType': s.b.FOLDER, 'parents': ['imgOffline006'], 'capabilities': {'canEdit': True}},
            'imgOffline006': {'name': 'IMG', 'parents': ['opOffline006']},
            'opOffline006': {'name': 'SHEIN_US_ES', 'parents': ['stockOffline006']},
        }

    def test_registered_six_codes_upper_lower_and_existing_names(self):
        self.assertEqual(set(s.layout.MANAGERS), {f'g{i:03d}' for i in range(1, 7)})
        for code, name in s.layout.MANAGERS.items():
            for value in (code, code.upper(), name, name.upper(), name.lower()):
                with self.subTest(value=value):
                    self.assertEqual(s.manager_code(value), code)

    def test_unknown_or_nonliteral_codes_remain_rejected(self):
        for value in ('G000', 'G007', 'g999', 'G006-extra', 'g6', ' G006', 'G006 ',
                      'Ｇ００６', 'Ğ006', '', 'unknown'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(s.StandardError, '^STANDARD_UNREGISTERED_MANAGER$'):
                    s.manager_code(value)

    def test_destinations_preserve_operation_format_state_and_manager(self):
        with patch.object(s, 'policy', return_value=self.policy):
            for value in ('g006', 'G006', 'Nicolas'):
                self.assertEqual(s.destination('SHEIN_US_ES', 'IMG', value), 'exclusiveOffline006')
                self.assertEqual(s.destination('SHEIN_US_ES', 'IMG', value, 'used'), 'usedOffline006')
            for op, fmt, manager, state in (
                ('SHEIN_US_EN', 'IMG', 'G006', 'exclusive'),
                ('SHEIN_US_ES', 'VID', 'G006', 'exclusive'),
                ('SHEIN_US_ES', 'IMG', 'G005', 'exclusive'),
                ('SHEIN_US_ES', 'IMG', 'G006', 'other')):
                with self.subTest(op=op, fmt=fmt, manager=manager, state=state):
                    with self.assertRaisesRegex(s.StandardError, '^STANDARD_DESTINATION_SCOPE$'):
                        s.destination(op, fmt, manager, state)

    def folder(self, **scope):
        with patch.object(s, 'policy', return_value=self.policy), \
             patch.object(s.storage, 'meta', side_effect=lambda d, fid: self.metadata[fid]), \
             patch.object(s.loc, 'stock_root', return_value='stockOffline006'), \
             patch.object(s.loc, 'stock_metadata_allowed', return_value=True):
            return s.validate_folder(object(), 'exclusiveOffline006', **scope)

    def test_uppercase_folder_passes_all_native_checks(self):
        before = copy.deepcopy(self.policy)
        self.assertEqual(self.folder(operation='SHEIN_US_ES', fmt='IMG', manager='G006',
                                     state='exclusive')['id'], 'exclusiveOffline006')
        self.assertEqual(self.policy, before)

    def test_each_wrong_manager_and_unknown_still_blocked(self):
        for code in ('G001', 'G002', 'G003', 'G004', 'G005', 'g005', 'Kelly'):
            with self.subTest(code=code):
                with self.assertRaisesRegex(s.StandardError, '^STANDARD_FOLDER_PARTITION$'):
                    self.folder(manager=code)
        with self.assertRaisesRegex(s.StandardError, '^STANDARD_UNREGISTERED_MANAGER$'):
            self.folder(manager='G007')

    def test_native_folder_ancestry_and_capability_remain_required(self):
        mutations = [('exclusiveOffline006', 'parents', ['wrong']),
                     ('exclusiveOffline006', 'capabilities', {'canEdit': False}),
                     ('exclusiveOffline006', 'name', 'KELLY - Exclusivos'),
                     ('imgOffline006', 'name', 'VID'),
                     ('opOffline006', 'name', 'SHEIN_US_EN')]
        baseline = copy.deepcopy(self.metadata)
        for fid, field, value in mutations:
            with self.subTest(fid=fid, field=field):
                self.metadata = copy.deepcopy(baseline)
                self.metadata[fid][field] = value
                with self.assertRaises(s.StandardError):
                    self.folder(manager='G006')


if __name__ == '__main__':
    unittest.main()
