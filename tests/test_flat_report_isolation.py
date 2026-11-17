import ast
import contextlib
import pathlib
import unittest
from unittest.mock import Mock, patch
import mgs_flat_maintenance as m


class ReportIsolationTests(unittest.TestCase):
    def execute(self, *, creative_only, apply=True, media=False, report_failure=False):
        nodes = {'report': {'id': 'report', 'mimeType': 'application/vnd.google-apps.spreadsheet', 'parents': [m.b.SOURCE_DRIVE]}}
        claims = {}
        if media:
            nodes.update({'root': {'id': 'root', 'name': 'SHEIN_US_ES', 'mimeType': m.b.FOLDER, 'parents': [m.b.SOURCE_ROOT]},
                          'raw': {'id': 'raw', 'mimeType': 'video/mp4', 'parents': ['root'], 'sha256Checksum': 'a'*64}})
            claims['batch'] = {'status': 'complete', 'proofs': [{'source_id': 'raw', 'raw_sha256': 'a'*64, 'clean_source_id': 'clean', 'clean_sha256': 'b'*64}], 'batch': {}}
        @contextlib.contextmanager
        def locked():
            yield {'claims': claims}
        @contextlib.contextmanager
        def queue(**kwargs):
            yield object()
        def read(path, default=None):
            return {'requests': {}} if pathlib.Path(path) == m.flat.REQUESTS else {'mappings': {}}
        report = Mock(side_effect=RuntimeError('unknown_or_public_principal') if report_failure else None)
        tree = Mock(return_value={'receipt_file_id': 'receipt'})
        with contextlib.ExitStack() as s:
            s.enter_context(patch.object(m.f, 'authority'))
            s.enter_context(patch.object(m.flat, 'policy', return_value={'active': True}))
            s.enter_context(patch.object(m.flat, 'registered_operations', return_value=['SHEIN_US_ES']))
            s.enter_context(patch.object(m.intake, 'locked_state', locked))
            s.enter_context(patch.object(m.b, 'queue_lock', queue))
            s.enter_context(patch.object(m.b, 'read_json', side_effect=read))
            s.enter_context(patch.object(m.b, 'atomic_json'))
            drive = s.enter_context(patch.object(m.b, 'Drive'))
            owner = s.enter_context(patch.object(m.t, 'OwnerDrive'))
            s.enter_context(patch.object(m.t, 'Journal'))
            s.enter_context(patch.object(m.cut, 'inventory', return_value=nodes))
            s.enter_context(patch('mgs_flat_consolidation.enabled', return_value=False))
            s.enter_context(patch.object(m, 'transfer_report', report))
            s.enter_context(patch.object(m, 'transfer_tree', tree))
            result = m.run(apply=apply, creative_only=creative_only)
        return result, report, tree, drive, owner

    def test_public_report_cannot_block_creative_intake(self):
        r, report, tree, drive, owner = self.execute(creative_only=True, report_failure=True)
        self.assertEqual(r['status'], 'ok')
        self.assertEqual(r['reports_deferred'], ['report'])
        self.assertEqual(r['maintenance_scope'], 'creative')
        report.assert_not_called()
        owner.assert_not_called()
        tree.assert_not_called()
        self.assertEqual(r['delete_writes'], 0)

    def test_media_maintenance_continues_with_unrelated_report(self):
        r, report, tree, drive, owner = self.execute(creative_only=True, media=True, report_failure=True)
        report.assert_not_called()
        tree.assert_called_once()
        self.assertEqual(r['completed_generations'][0]['root_id'], 'root')
        self.assertEqual(r['reports_deferred'], ['report'])

    def test_general_report_lane_preserved(self):
        r, report, tree, drive, owner = self.execute(creative_only=False)
        report.assert_called_once()
        self.assertEqual(r['reports_archived'], ['report'])
        self.assertEqual(r['reports_deferred'], [])

    def test_general_report_guard_not_relaxed(self):
        with self.assertRaisesRegex(RuntimeError, 'unknown_or_public_principal'):
            self.execute(creative_only=False, report_failure=True)

    def test_dry_run_has_no_owner_or_transfer(self):
        r, report, tree, drive, owner = self.execute(creative_only=True, media=True, apply=False)
        owner.assert_not_called()
        report.assert_not_called()
        tree.assert_not_called()

    def test_real_monitor_selects_creative_scope(self):
        import ares_autonomous_intake
        source = pathlib.Path(ares_autonomous_intake.__file__).read_text()
        calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'run' and n.args and isinstance(n.args[0], ast.List) and any(isinstance(e, ast.Constant) and e.value == '--apply' for e in n.args[0].elts)]
        self.assertEqual(len(calls), 1)
        self.assertIn('--creative-only', [e.value for e in calls[0].args[0].elts if isinstance(e, ast.Constant)])


if __name__ == '__main__':
    unittest.main()
