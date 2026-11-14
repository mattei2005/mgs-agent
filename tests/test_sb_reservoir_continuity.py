import copy
import json
from pathlib import Path
import sys
import tempfile
from typing import Any
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, '/root/mgs-agent/scripts')
import mgs_sb_reservoir_continuity as m  # pyright: ignore[reportMissingImports]
from mgs_automation_continuity import Queue  # pyright: ignore[reportMissingImports]


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

    def certificate_fixture(self, root):
        q = Queue(Path(root) / 'queue.sqlite3')
        source = {'kind': 'native', 'profile': 'zeus', 'job_id': m.JOB,
                  'thread_id': m.THREAD, 'contract_hash': m.CONTRACT}
        evidence = {'status': 'OK', 'verified': True, 'target': 'native:zeus:' + m.JOB,
                    'source': source, 'slot': m.SLOT, 'evidence': copy.deepcopy(self.evidence),
                    'receipt': f'reservoir:{m.KEY};catalog:{m.CATALOG_SHA};discord:{m.CHANNEL}/{m.REPORT}',
                    'at': 1794658624.0897899}
        row = q.enqueue('native:zeus:' + m.JOB, source, 'fixture', now=1794656223)
        q.db.execute('UPDATE requests SET key=? WHERE key=?', (m.KEY, row['key']))
        q.complete(m.KEY, evidence, now=1794658629.9883673)
        self.addCleanup(q.close)
        return q

    def test_same_slot_certification_survives_later_inventory_consumption(self):
        with tempfile.TemporaryDirectory() as root:
            q = self.certificate_fixture(root)
            self.assertEqual(m.certified_occurrence(q.path),
                             {'request_key': m.KEY, 'verified_at': 1794658624.0897899})

    def test_unfinished_foreign_or_owned_certificate_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            q = self.certificate_fixture(root)
            for field, value in (('state', 'running'), ('source_key', 'native:zeus:other'),
                                 ('owner', 'another-writer')):
                original = q.get(m.KEY)[field]
                q.db.execute(f'UPDATE requests SET {field}=? WHERE key=?', (value, m.KEY))
                self.assertIsNone(m.certified_occurrence(q.path))
                q.db.execute(f'UPDATE requests SET {field}=? WHERE key=?', (original, m.KEY))

    def test_missing_or_changed_independent_completion_event_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            q = self.certificate_fixture(root)
            q.db.execute("UPDATE events SET detail='{}' WHERE kind='completed_validated'")
            self.assertIsNone(m.certified_occurrence(q.path))

    def test_other_slot_or_contract_or_unverified_receipt_cannot_certify(self):
        with tempfile.TemporaryDirectory() as root:
            q = self.certificate_fixture(root)
            original = json.loads(q.get(m.KEY)['evidence'])
            for change in ({'slot': '2026-11-15T06:30:00-05:00'}, {'verified': False},
                           {'receipt': 'worker said resolved'},
                           {'source': original['source'] | {'contract_hash': 'changed'}}):
                altered = original | change
                q.db.execute('UPDATE requests SET evidence=? WHERE key=?',
                             (json.dumps(altered), m.KEY))
                q.db.execute("UPDATE events SET detail=? WHERE kind='completed_validated'",
                             (json.dumps(altered),))
                self.assertIsNone(m.certified_occurrence(q.path))

    def local_fixture(self, root):
        base = Path(root)
        (base / 'data').mkdir()
        (base / 'logs').mkdir()
        candidates = [{'candidate_id': m.CANDIDATE if i == 0 else f'fixture-{i}',
                       'text': f'fixture text {i}', 'text_cta_hash': f'fixture-hash-{i}'}
                      for i in range(107)]
        raw = json.dumps({'candidates': {'fixture': candidates}}).encode()
        (base / 'data/sb-utility-generated-candidates.json').write_bytes(raw)
        (base / 'data/utility-message-bank.json').write_text('{"records":{}}')
        (base / 'data/sb-utility-candidate-approval-state.json').write_text('{}')
        event = {'event': 'sb_utility_candidate_catalog_replenished',
                 'ts': '2026-11-14T11:34:11.458931+00:00', 'source_thread_id': m.THREAD,
                 'candidate_ids_added': [m.CANDIDATE], 'verticals_changed': {'US-JOB-ES': 1},
                 'smart_bidding_templates_changed': False,
                 'coverage': {v: {'available': n} for v, n in m.COVERAGE.items()}}
        (base / 'logs/events-audit.jsonl').write_text(json.dumps(event) + '\n')
        runner = SimpleNamespace(
            formatted_candidate=lambda c, v: c,
            repair=SimpleNamespace(normalized=lambda t: t.lower()),
            select_catalog_candidates=lambda c, v, n, b, s, t:
                [None] * (m.COVERAGE[v] - (1 if v == 'US-JOB-ES' else 0)))
        return base, raw, runner

    def test_live_shortfall_does_not_close_without_independent_certification(self):
        with tempfile.TemporaryDirectory() as root:
            base, raw, runner = self.local_fixture(root)
            with patch.object(m, 'certified_occurrence', return_value=None):
                with self.assertRaisesRegex(ValueError, 'without certified occurrence'):
                    m._validate_locked(base, raw, runner)

    def test_historical_inventory_is_labeled_separately_from_current_inventory(self):
        with tempfile.TemporaryDirectory() as root:
            base, raw, runner = self.local_fixture(root)
            with patch.object(m, 'certified_occurrence', return_value={
                    'request_key': m.KEY, 'verified_at': 1794658624.0897899}):
                result = m._validate_locked(base, raw, runner)
                self.assertEqual(result['available'], m.COVERAGE)
                self.assertEqual(result['current_available']['US-JOB-ES'], 3)
                self.assertEqual(result['certified_occurrence']['request_key'], m.KEY)


if __name__ == '__main__':
    unittest.main()
