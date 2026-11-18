import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, '/root/mgs-agent/scripts')
import mgs_finance_continuity as m


class FinanceDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / m.RUN
        self.root.mkdir(parents=True)
        self.snapshot = {'sheets': []}
        (self.root / 'recovery-final-workbook-0114.json').write_text(json.dumps(self.snapshot))
        self.receipt = {'h_read_times': {'1': '2026-11-08T23:50:00-05:00', '2': '2026-11-09T00:28:00-05:00'}}
        self.contract = {'spreadsheet_id': 'fixture', 'sheet_id': 1}
        self.sent = []
        self.job = {'id': m.JOB, 'enabled': True, 'state': 'scheduled'}
        self.patches = [patch.object(m, 'validate', return_value=(self.receipt, self.contract)),
                        patch.object(m, 'native_contract_hash', return_value=m.HASH)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def transport(self, payload, **kwargs):
        self.sent.append(kwargs['prior_id'])
        self.assertEqual(kwargs['channel'], m.THREAD)
        self.assertEqual(payload['allowed_mentions']['parse'], [])
        if kwargs['prior_id'] is None:
            kwargs['on_created']('123')
        return '123'

    def test_delivery_then_retry_only_gets_exact_registered_id(self):
        a = m.resume(self.job, base=self.base, transport=self.transport)
        b = m.resume(self.job, base=self.base, transport=self.transport, verify_only=True)
        self.assertEqual(self.sent, [None, '123'])
        self.assertEqual(a['message_id'], b['message_id'])

    def test_failed_get_keeps_accepted_id_and_frozen_payload(self):
        def failed(payload, **kwargs):
            kwargs['on_created']('456')
            raise RuntimeError('fixture GET failure')
        with self.assertRaises(RuntimeError):
            m.resume(self.job, base=self.base, transport=failed)
        state = m.load(self.root / 'financial-delivery.json')
        self.assertEqual(state['message_id'], '456')
        m.resume(self.job, base=self.base, transport=self.transport)
        self.assertEqual(self.sent, ['456'])

    def test_verify_only_never_starts_post(self):
        with self.assertRaises(ValueError):
            m.resume(self.job, base=self.base, transport=self.transport, verify_only=True)
        self.assertEqual(self.sent, [])
        self.assertFalse((self.root / 'financial-delivery.json').exists())

    def test_current_occurrence_has_distinct_snapshot_and_nonce(self):
        key = '6a8f887c7ddb0077beeeb05b'
        run, snapshot = m.RECOVERIES[key]
        root = self.base / run
        root.mkdir(parents=True)
        (root / snapshot).write_text(json.dumps(self.snapshot))
        self.receipt.update(scheduled_at='2026-11-09T08:02:00-05:00',
                            validated_metrics_at='2026-11-09T10:42:48-05:00')
        m.resume(self.job, base=self.base, transport=self.transport, key=key)
        state = m.load(root / 'financial-delivery.json')
        self.assertEqual(state['continuity_key'], key)
        self.assertEqual(state['payload']['nonce'], key)
        self.assertIn('09/11 às 08h02', state['payload']['content'])
        self.assertIn('09/11 às 10h42', state['payload']['content'])
        self.assertFalse((self.root / 'financial-delivery.json').exists())
        m.resume(self.job, base=self.base, transport=self.transport,
                 key=key, verify_only=True)
        self.assertEqual(self.sent, [None, '123'])

    def test_paused_active_and_changed_contract_do_not_deliver(self):
        for edits in ({'enabled': False}, {'state': 'paused'}, {'fire_claim': 'active'}):
            with self.assertRaises(ValueError):
                m.resume(self.job | edits, base=self.base, transport=self.transport)
        with patch.object(m, 'native_contract_hash', return_value='changed'):
            with self.assertRaises(ValueError):
                m.resume(self.job, base=self.base, transport=self.transport)
        self.assertEqual(self.sent, [])

    def test_snapshot_drift_denies_replay(self):
        m.resume(self.job, base=self.base, transport=self.transport)
        (self.root / 'recovery-final-workbook-0114.json').write_text('{}')
        with self.assertRaises(ValueError):
            m.resume(self.job, base=self.base, transport=self.transport)
        self.assertEqual(self.sent, [None])

    def test_authored_comparison_preserves_notes_and_formulas(self):
        sheet = {'properties': {'sheetId': 1}, 'data': [{'rowData': [{'values': [
            {'userEnteredValue': {'formulaValue': '=ROUND(SUM(A1),2)'}, 'note': 'source'}]}]}]}
        changed = copy.deepcopy(sheet)
        changed['data'][0]['rowData'][0]['values'][0]['note'] = 'other'
        self.assertNotEqual(m.authored(sheet), m.authored(changed))

    def test_newer_scheduled_slot_not_certified_by_old_delivery(self):
        (self.root / 'financial-delivery.json').write_text('{}')
        (self.root / 'recovery-financial-validation.json').write_text(json.dumps(
            {'validated_metrics_at': '2026-11-09T01:14:29-05:00'}))
        job = self.job | {'last_run_at': '2026-11-09T08:02:00-05:00'}
        self.assertIsNone(m.observation(job, base=self.base))

    def test_concurrent_sort_preserves_complete_rows_and_rejects_data_change(self):
        a = {'basicFilter': {'range': {'startRowIndex': 0, 'endRowIndex': 2,
                                      'endColumnIndex': 10},
                             'sortSpecs': [{'dimensionIndex': 7, 'sortOrder': 'ASCENDING'}]},
             'data': [{'rowData': [{'values': [{'note': 'ID da conta: 2',
                                               'userEnteredValue': {'numberValue': 20}}]},
                                  {'values': [{'note': 'ID da conta: 1',
                                               'userEnteredValue': {'numberValue': 10}}]}]}]}
        b = copy.deepcopy(a)
        b['data'][0]['rowData'].reverse()
        b['basicFilter']['sortSpecs'][0]['dimensionIndex'] = 8
        self.assertEqual(m.sorted_view(a), m.sorted_view(b))
        b['data'][0]['rowData'][0]['values'][0]['note'] += ' modified'
        self.assertNotEqual(m.sorted_view(a), m.sorted_view(b))


if __name__ == '__main__':
    unittest.main()
