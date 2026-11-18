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


class CurrentFinanceOccurrenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / m.RECOVERIES[m.CURRENT_KEY][0]
        self.root.mkdir(parents=True)
        self.ids = [str(i) for i in range(55)]
        self.book = {
            'sheets': [{'properties': {'sheetId': 271321738}, 'data': [{'rowData': [
                {'values': [{'note': 'ID da conta: ' + aid}]} for aid in self.ids]}]}]}
        self.contract = {'thread_id': m.THREAD, 'business_id': '155263197283282',
                         'spreadsheet_id': '1PrKBawAGgRxx1LPcjcf8U6QH4ZcJfJTn-niJ2SzCdyU',
                         'sheet_id': 271321738, 'account_ids': self.ids,
                         'pay_now_account_ids': self.ids[:40],
                         'h_source': 'accounts_list_outstanding_balance'}
        self.receipt = {'continuity_key': m.CURRENT_KEY, 'accounts': 55,
                        'fresh_metrics_count': 55, 'fresh_h_count': 40, 'pending_ui': [],
                        'scheduled_at': m.CURRENT_SLOT, 'native_contract_hash': m.CURRENT_HASH,
                        'source_key': m.SOURCE + ':20261118T0802', 'business_refresh_complete': True,
                        'groups': {'Cartão de crédito': 15, 'Linha de crédito': 40},
                        'h_read_times': {aid: '2026-11-18T10:00:00-05:00' for aid in self.ids[:40]},
                        'validated_metrics_at': '2026-11-18T11:09:16-05:00',
                        'average_periods': [['2026-11-15', '2026-11-17']],
                        'month_periods': [['2026-11-01', '2026-11-18']],
                        'invoices': {'period': '2026-10-01', 'pending': 30, 'due_usd': '417864.11'},
                        'D_verified_published_ids': self.ids[:8], 'historical_blank_d': []}
        for name in ('source_to_live_sheet_cgij_exact', 'invoice_source_to_live_sheet_ef_exact',
                     'h_source_to_live_sheet_and_note_exact', 'd_ledger_to_live_sheet_exact',
                     'h_original_collection_times_preserved', 'other_sheet_data_unchanged'):
            self.receipt[name] = True
        for name in ('payments_executed', 'billing_changes', 'meta_writes', 'cron_changes'):
            self.receipt[name] = 0
        cp = self.base / 'data/meta-manual-payments/digital-trust-workbook-contract.json'
        cp.parent.mkdir(parents=True)
        cp.write_text(json.dumps(self.contract))
        (self.root / 'recovery-final-workbook.json').write_text(json.dumps(self.book))
        self.save_receipt()
        self.job = {'id': m.JOB, 'enabled': True, 'state': 'scheduled',
                    'last_dispatch': {'scheduled_at': m.CURRENT_SLOT},
                    'last_run_at': '2026-11-18T08:09:08-05:00'}

    def save_receipt(self):
        (self.root / 'recovery-financial-validation.json').write_text(json.dumps(self.receipt))

    def test_actual_validator_accepts_55_and_rejects_missing_proof(self):
        m.validate(self.base, lambda _: self.book, key=m.CURRENT_KEY)
        self.receipt['h_read_times'].pop('0')
        self.save_receipt()
        with self.assertRaises(ValueError):
            m.validate(self.base, lambda _: self.book, key=m.CURRENT_KEY)

    def test_no_cross_slot_or_old_contract_authority(self):
        with patch.object(m, 'native_contract_hash', return_value=m.CURRENT_HASH):
            self.assertTrue(m.scope(self.job, key=m.CURRENT_KEY))
            for edit in ({'enabled': False}, {'fire_claim': {'by': 'other'}},
                         {'last_dispatch': {'scheduled_at': '2026-11-18T14:02:00-05:00'}}):
                self.assertFalse(m.scope(self.job | edit, key=m.CURRENT_KEY))
            self.assertFalse(m.scope(self.job, key=m.KEY))

    def test_current_delivery_idempotency_and_occurrence_target(self):
        calls = []
        def transport(payload, **kwargs):
            calls.append(kwargs['prior_id'])
            self.assertEqual(payload['nonce'], m.CURRENT_KEY)
            self.assertEqual(payload['content'].count('• '), 6)
            self.assertIn('55/55', payload['content'])
            if kwargs['prior_id'] is None:
                kwargs['on_created']('789')
            return '789'
        with patch.object(m, 'native_contract_hash', return_value=m.CURRENT_HASH):
            result = m.resume(self.job, base=self.base, reader=lambda _: self.book,
                              transport=transport, key=m.CURRENT_KEY)
            m.resume(self.job, base=self.base, reader=lambda _: self.book,
                     transport=transport, key=m.CURRENT_KEY, verify_only=True)
        self.assertEqual(calls, [None, '789'])
        self.assertEqual(result['target'], m.SOURCE + ':20261118T0802')

    def test_wrong_period_and_changed_workbook_fail_closed(self):
        changed = copy.deepcopy(self.book)
        changed['sheets'][0]['data'][0]['rowData'][0]['values'][0]['note'] += 'changed'
        with self.assertRaises(ValueError):
            m.validate(self.base, lambda _: changed, key=m.CURRENT_KEY)
        self.receipt['month_periods'] = [['2026-11-01', '2026-11-19']]
        self.save_receipt()
        with self.assertRaises(ValueError):
            m.validate(self.base, lambda _: self.book, key=m.CURRENT_KEY)

    def test_supervisor_routes_same_occurrence_to_adapter_without_agent(self):
        import mgs_automation_supervisor as supervisor
        jobs = self.base / 'profiles/zeus/cron'
        jobs.mkdir(parents=True)
        (jobs / 'jobs.json').write_text(json.dumps({'jobs': [self.job]}))
        row = {'key': m.CURRENT_KEY, 'source': json.dumps({'job_id': m.JOB})}
        with patch.object(supervisor, 'PROFILES', self.base / 'profiles'), \
                patch.object(m, 'resume', return_value={'receipt': 'verified'} ) as resume:
            result = supervisor.run_worker(row, 'verify_only', base=self.base)
        self.assertTrue(result.startswith('Resolvido:'))
        self.assertEqual(resume.call_args.kwargs['key'], m.CURRENT_KEY)
        self.assertTrue(resume.call_args.kwargs['verify_only'])


if __name__ == '__main__':
    unittest.main()
