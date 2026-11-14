import copy
import json
from pathlib import Path
import sys
import tempfile
from typing import Any
import unittest
from unittest.mock import patch

sys.path.insert(0, '/root/mgs-agent/scripts')
import mgs_sb_reservoir_continuity as m  # pyright: ignore[reportMissingImports]


class ReservoirReceiptTests(unittest.TestCase):
    def setUp(self):
        self.job = {'id': m.JOB, 'enabled': True, 'state': 'scheduled',
                    'last_run_at': m.LAST_RUN, 'last_dispatch': {'scheduled_at': m.SLOT},
                    'last_status': 'error'}
        self.evidence = {'catalog_sha256': m.CATALOG_SHA, 'candidate_id': m.CANDIDATE,
                         'available': dict(m.COVERAGE)}
        self.message: dict[str, Any] = {'id': m.REPORT, 'channel_id': m.CHANNEL,
                        'author': {'id': '1496296175014252634'}, 'content': '', 'mentions': [],
                        'timestamp': '2026-11-14T11:34:34+00:00',
                        'embeds': [{'fields': [
                            {'name': 'Tipo', 'value': 'data'},
                            {'name': 'Path', 'value': 'data/sb-utility-generated-candidates.json'},
                            {'name': 'Evidência', 'value': m.CANDIDATE + '; cobertura 24/19/4'}]}]}
        self.calls = []
        p = patch.object(m, 'native_contract_hash', return_value=m.CONTRACT)
        p.start()
        self.addCleanup(p.stop)

    def get(self, method, url):
        self.calls.append((method, url))
        return self.message

    def observe(self, job=None):
        return m.observation(job or self.job, validator=lambda _: self.evidence, getter=self.get)

    def test_exact_slot_reads_existing_report_without_rewriting_scheduler_error(self):
        before = copy.deepcopy(self.job)
        result = self.observe()
        self.assertTrue(result['verified'])
        self.assertEqual(result['slot'], m.SLOT)
        self.assertEqual(self.job, before)
        self.assertEqual(self.calls, [('GET', f'https://discord.com/api/v10/channels/{m.CHANNEL}/messages/{m.REPORT}')])

    def test_paused_disabled_active_and_other_job_fail_before_get(self):
        for change in ({'enabled': False}, {'state': 'paused'}, {'state': 'completed'},
                       {'fire_claim': 'writer'}, {'id': 'other'}):
            with self.subTest(change=change):
                self.assertIsNone(self.observe(self.job | change))
        self.assertEqual(self.calls, [])

    def test_changed_contract_fails_closed(self):
        with patch.object(m, 'native_contract_hash', return_value='changed'):
            self.assertIsNone(self.observe())
        self.assertEqual(self.calls, [])

    def test_later_run_or_slot_cannot_use_historical_receipt(self):
        for change in ({'last_run_at': '2026-11-15T06:34:00-05:00'},
                       {'last_dispatch': {'scheduled_at': '2026-11-15T06:30:00-05:00'}},
                       {'last_dispatch': {}}):
            self.assertIsNone(self.observe(self.job | change))
        self.assertEqual(self.calls, [])

    def test_catalog_drift_or_candidate_mismatch_fails_closed(self):
        for key in ('catalog_sha256', 'candidate_id'):
            previous = self.evidence[key]
            self.evidence[key] = 'wrong'
            self.assertIsNone(self.observe())
            self.evidence[key] = previous
        self.assertEqual(self.calls, [])

    def test_all_verticals_require_deficit_plus_reserve(self):
        for vertical in m.COVERAGE:
            self.evidence['available'][vertical] -= 1
            self.assertIsNone(self.observe())
            self.evidence['available'][vertical] += 1
        self.assertEqual(self.calls, [])

    def test_wrong_report_identity_author_channel_or_payload_fails(self):
        original = copy.deepcopy(self.message)
        for change in ({'id': 'other'}, {'channel_id': 'other'}, {'author': {'id': 'other'}},
                       {'content': 'text'}, {'mentions': [{'id': '1'}]}, {'embeds': []},
                       {'timestamp': '2026-11-13T11:34:34+00:00'}):
            self.message = original | change
            self.assertIsNone(self.observe())

    def test_wrong_embed_scope_fails_closed(self):
        for field in self.message['embeds'][0]['fields']:
            previous = field['value']
            field['value'] = 'wrong'
            self.assertIsNone(self.observe())
            field['value'] = previous

    def test_get_failure_keeps_unverified_without_post(self):
        def fail(method, url):
            self.assertEqual(method, 'GET')
            raise RuntimeError('Discord HTTP 429; delivery remains pending')
        self.assertIsNone(m.observation(self.job, validator=lambda _: self.evidence, getter=fail))

    def test_local_validator_error_keeps_unverified(self):
        def fail(_):
            raise ValueError('coverage changed')
        self.assertIsNone(m.observation(self.job, validator=fail, getter=self.get))
        self.assertEqual(self.calls, [])

    def test_local_validation_rejects_catalog_drift_before_import(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / 'data').mkdir()
            (base / 'data/sb-utility-generated-candidates.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'catalog drift'):
                m.local_validation(base)


if __name__ == '__main__':
    unittest.main()
