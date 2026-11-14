import unittest
from unittest.mock import patch
from test_b013_profile_removal_alert import load_monitor_module

class SheetIdentitySyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_monitor_module()

    def test_sorting_remaps_to_current_identity_row_and_marker(self):
        scan = [{'user': 'A@EXAMPLE.COM', 'segurador': 'José', 'row': 7, 'sheet_x': '', 'verdict': 'unlinked_confirmed'}]
        fresh = [{'user': 'a@example.com', 'segurador': 'Jose', 'row': 19, 'sheet_x': 'X'}]
        got = self.ns.remap_sheet_sync_results(scan, fresh)
        self.assertEqual((got[0]['row'], got[0]['sheet_x']), (19, 'X'))
        self.assertEqual(scan[0]['row'], 7)

    def test_reassigned_identity_is_not_written(self):
        self.assertEqual(self.ns.remap_sheet_sync_results([{'user': 'a@x', 'segurador': 'A', 'row': 7}], []), [])

    def test_new_assignment_waits_for_next_scan(self):
        self.assertEqual(self.ns.remap_sheet_sync_results([], [{'user': 'a@x', 'segurador': 'A', 'row': 7}]), [])

    def test_duplicate_current_identity_fails_closed(self):
        row = {'user': 'a@x', 'segurador': 'A', 'row': 7}
        with self.assertRaisesRegex(RuntimeError, 'duplicated'):
            self.ns.remap_sheet_sync_results([], [row, row])

    def test_duplicate_scan_identity_fails_closed(self):
        row = {'user': 'a@x', 'segurador': 'A', 'row': 7}
        with self.assertRaisesRegex(RuntimeError, 'duplicated'):
            self.ns.remap_sheet_sync_results([row, row], [row])

    def test_actual_sync_uses_fresh_row_and_preserves_unknown(self):
        ns = self.ns
        scan = [{'user': 'a@x', 'segurador': 'A', 'row': 7, 'sheet_x': '', 'verdict': 'unlinked_confirmed'},
                {'user': 'b@x', 'segurador': 'B', 'row': 8, 'sheet_x': '', 'verdict': 'unknown'}]
        fresh = [{'user': 'a@x', 'segurador': 'A', 'row': 19, 'sheet_x': ''},
                 {'user': 'b@x', 'segurador': 'B', 'row': 20, 'sheet_x': 'X'}]
        calls = []
        def request(method, path, token, payload):
            calls.append(payload)
            return 200, {'totalUpdatedCells': 1}
        with patch.dict(ns.sync_sheet_x.__globals__, {'sheet_rows': lambda _: fresh, 'google_service_account_access_token': lambda: 'fixture', 'sheet_title_for_gid': lambda *_: 'Fixture', 'sheets_request': request, 'DRY_RUN': False}):
            result = ns.sync_sheet_x({'sheet_id': 'fixture'}, scan)
        self.assertEqual(calls[0]['data'], [{'range': "'Fixture'!A19:A19", 'majorDimension': 'ROWS', 'values': [['X']]}])
        self.assertEqual(result['unknown_preserved'], 1)
        self.assertEqual(result['updated_cells'], 1)

if __name__ == '__main__':
    unittest.main()
