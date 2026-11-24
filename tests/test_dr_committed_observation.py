"""Terminated scheduler must not replay an already committed native DR backup."""
import copy
import json
from unittest.mock import patch
import unittest

from test_dr_finalized_observation import FinalizedObservationTests
import mgs_dr_recovery_continuity as m


class NativeCommittedObservationTests(FinalizedObservationTests):
    def setUp(self):
        slot, values = next(iter(m.COMMITTED_OCCURRENCES.items()))
        names = ('FINAL_KEY', 'FINAL_LAST_RUN', 'FINAL_FILE', 'FINAL_ACK',
                 'FINAL_NAME', 'FINAL_SHA', 'FINAL_MD5', 'FINAL_SIZE')
        values_patch = patch.multiple(m, FINAL_SLOT=slot, **dict(zip(names, values)))
        values_patch.start()
        self.addCleanup(values_patch.stop)
        super().setUp()
        self.job.update(last_status='error', last_error='Restart-safe cron worker exited with status -15')
        self.result.pop('recovery')
        self.save()

    def save(self):
        (self.root / 'canonical-native-result.json').write_text(json.dumps(self.result))
        (self.root / 'independent-readback.json').write_text(json.dumps({
            'operation': m.FINAL_KEY, 'GET_verified': True, 'report_infra_message_id': '123'}))
        (self.base / 'data').mkdir(exist_ok=True)
        (self.base / 'data/mgs-offsite-backup-state.json').write_text(json.dumps({
            'last_success': {'quick': self.result}}))
        (self.base / 'logs').mkdir(exist_ok=True)
        self.event = {'event': 'backup_success', 'remote_file_id': m.FINAL_FILE,
                      'mode': 'quick', 'tier': 'hourly', 'size_bytes': int(m.FINAL_SIZE),
                      'sha256': m.FINAL_SHA, 'retention_trashed_count': 0}
        (self.base / 'logs/mgs-offsite-backup.jsonl').write_text(json.dumps(self.event) + '\n')

    def test_execution_receipt_fields_required(self):
        prior = copy.deepcopy(self.result)
        for key in list(self.result):
            self.result[key] = None
            self.save()
            self.assertIsNone(self.observe(), key)
            self.result.clear()
            self.result.update(copy.deepcopy(prior))
        self.save()

    def test_canonical_state_missing_or_later_backup_rejected(self):
        state_path = self.base / 'data/mgs-offsite-backup-state.json'
        for state in ({}, {'last_success': {'quick': self.result | {'remote_file_id': 'later'}}}):
            state_path.write_text(json.dumps(state))
            self.assertIsNone(self.observe())

    def test_event_missing_duplicated_or_drift_rejected(self):
        path = self.base / 'logs/mgs-offsite-backup.jsonl'
        for events in ([], [self.event, self.event], [self.event | {'event': 'backup_failure'}],
                       [self.event | {'sha256': 'drift'}], [self.event | {'size_bytes': 1}],
                       [self.event | {'tier': 'daily'}], [self.event | {'retention_trashed_count': 1}]):
            path.write_text(''.join(json.dumps(e) + '\n' for e in events))
            self.assertIsNone(self.observe())

    def test_scheduler_failure_must_match_reconciled_termination(self):
        for delta in ({'last_status': 'ok'}, {'last_error': 'different failure'},
                      {'last_dispatch': {'scheduled_at': '2026-11-23T23:23:00-05:00'}}):
            self.assertIsNone(self.observe(self.job | delta))

    def test_missing_report_get_remains_pending(self):
        self.msg['embeds'] = []
        self.assertIsNone(self.observe())

    def test_unrelated_historical_log_damage_is_not_this_occurrence(self):
        path = self.base / 'logs/mgs-offsite-backup.jsonl'
        path.write_text('\x00old-unrelated-log-damage\n' + json.dumps(self.event) + '\n')
        self.assertTrue(self.observe()['verified'])
        path.write_text('\x00' + json.dumps(self.event) + '\n')
        self.assertIsNone(self.observe())

    def test_positive_receipt_is_read_only_committed_snapshot(self):
        obs = self.observe()
        self.assertTrue(obs['evidence']['native_already_committed'])
        self.assertFalse(obs['evidence']['upload_replayed'])
        self.assertEqual(obs['slot'], m.FINAL_SLOT)


if __name__ == '__main__':
    unittest.main()
