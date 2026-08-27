#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path('/root/mgs-agent/scripts/refresh-sb-restricted-history-sheet.py')
spec = importlib.util.spec_from_file_location('refresh_sb_restricted_history_sheet_test', SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f'cannot load {SCRIPT}')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshRestrictedHistorySheetTest(unittest.TestCase):
    @staticmethod
    def state_payload(currently_restricted=True):
        page = {
            'entries_detected': 2,
            'exits_confirmed': 1,
            'renewals_detected': 3,
            'status_changes_detected': 4,
            'currently_restricted': currently_restricted,
        }
        return {
            'history': {
                'page_count': 1,
                'pages': {'bot@example.com|456': page},
                'totals': {
                    'entries_detected': 2,
                    'exits_confirmed': 1,
                    'renewals_detected': 3,
                    'status_changes_detected': 4,
                    'currently_restricted': 1 if currently_restricted else 0,
                },
            },
        }

    def test_load_validated_history_accepts_exact_totals(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / 'state.json'
            state_path.write_text(json.dumps(self.state_payload()), encoding='utf-8')
            original = getattr(refresh, 'STATE_PATH')
            setattr(refresh, 'STATE_PATH', state_path)
            try:
                history, totals = refresh.load_validated_history()
            finally:
                setattr(refresh, 'STATE_PATH', original)

        self.assertEqual(history['page_count'], 1)
        self.assertEqual(totals['currently_restricted'], 1)
        self.assertEqual(totals['renewals_detected'], 3)

    def test_load_validated_history_rejects_totals_drift(self):
        payload = self.state_payload()
        payload['history']['totals']['entries_detected'] = 99
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / 'state.json'
            state_path.write_text(json.dumps(payload), encoding='utf-8')
            original = getattr(refresh, 'STATE_PATH')
            setattr(refresh, 'STATE_PATH', state_path)
            try:
                with self.assertRaisesRegex(RuntimeError, 'totals mismatch'):
                    refresh.load_validated_history()
            finally:
                setattr(refresh, 'STATE_PATH', original)


if __name__ == '__main__':
    unittest.main()
