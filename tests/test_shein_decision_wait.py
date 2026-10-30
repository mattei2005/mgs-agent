import copy
import fcntl
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_decision_wait as dw, shein_request_queue as q


class DecisionWaitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.owner = 'shein-historical'; self.rid = 'shein-new'; self.account = '123'
        self.request = {'request_id': self.rid, 'account': self.account,
                        'source_channel_id': 'CHAN', 'source_thread_id': 'THREAD',
                        'campaign_groups': [{'files': ['new.png']}], 'authorized_by': 'HUMAN'}
        self.rows = [{'asset_id': 'NEW', 'canonical_filename': 'new.png',
                      'clean_checksum': 'new-bytes', 'image_hash': 'new-hash'}]
        self.inv = self.base / 'data/ares/creative-ops/inventory/assets.jsonl'
        self.inv.parent.mkdir(parents=True)
        self.write_rows()
        self.spath = q.root(self.base) / 'single-clone' / self.owner / 'state.json'
        self.spath.parent.mkdir(parents=True)
        self.state = {'request': {'request_id': self.owner, 'account': self.account,
                                 'source_channel_id': 'CHAN', 'source_thread_id': 'THREAD'},
                      'phase': 'POSTPROCESS_PENDING', 'engine_result': {
                          'status': 'COMPLETE_PAUSED', 'request_id': self.owner, 'campaign_ids': ['C1', 'C2']},
                      'manifest': {'campaigns': [{'account_id': '123', 'status': 'PAUSED',
                          'ads': [{'media': {'asset_id': 'OLD', 'checksum': 'old-bytes',
                                             'video_id': 'old-video'}}]} for _ in range(2)]}}
        self.eroot = self.base / 'engine-state'
        config = self.base / 'data/ares/meta-ads/engine-v3/config.json'
        config.parent.mkdir(parents=True); q.atomic(config, {'state_root': str(self.eroot)})
        self.cp = self.eroot / 'checkpoints' / (self.owner + '-123.json')
        q.atomic(self.cp, {'account_id': '123', 'status': 'COMPLETE',
                          'manual_reconciliation_required': False, 'campaign_ids': ['C1', 'C2']})
        self.lease = self.eroot / 'writer-leases/123.json'
        q.atomic(self.lease, {'account_id': '123', 'request_id': self.owner, 'status': 'COMPLETE',
                              'blocks_readers': False, 'released_at_utc': '2026-10-29T00:00:00Z'})
        self.lease.with_suffix('.lock').touch()
        self.alock = q.root(self.base) / 'single-clone/account-123.lock'; self.alock.touch()
        self.record = {'schema_version': 1, 'classification': 'WAITING_HUMAN_DECISION',
                       'request_id': self.owner, 'account_id': '123',
                       'review': {'thread_id': 'THREAD', 'channel_id': 'CHAN',
                                  'message_id': '1565343225894666345', 'author_id': '1508864261504630925',
                                  'decision': 'UNANSWERED', 'material_difference': True},
                       'campaign_readback': [{'id': x, 'account_id': '123', 'status': 'PAUSED'} for x in ['C1','C2']],
                       'verified_at': '2026-10-30T00:00:00Z', 'maintenance_task_id': 'test-fixture',
                       'evidence_source': 'SYNTHETIC FIXTURE ONLY'}
        self.seal()

    def tearDown(self): self.tmp.cleanup()

    def write_rows(self):
        self.inv.write_text(''.join(json.dumps(r) + '\n' for r in self.rows))

    def seal(self):
        q.atomic(self.spath, self.state)
        self.record.update(state_sha256=dw.digest(self.spath), checkpoint_sha256=dw.digest(self.cp))
        q.atomic(dw.record_path(self.base, self.owner), self.record)

    def deps(self): return q.dependencies(self.request, '123', self.base)

    def test_inert_review_disjoint_media_is_not_account_dependency(self):
        before = [p.read_bytes() for p in [self.spath, self.inv, self.lease, self.cp]]
        self.assertEqual(self.deps(), [])
        self.assertEqual(before, [p.read_bytes() for p in [self.spath, self.inv, self.lease, self.cp]])
        self.assertFalse(q.terminal(self.state))

    def test_shared_asset_identity_blocks_even_without_reservation(self):
        self.rows[0]['asset_id'] = 'OLD'; self.write_rows()
        self.assertEqual(self.deps(), [self.owner])

    def test_shared_checksum_different_lineage_blocks(self):
        self.rows[0]['clean_checksum'] = 'old-bytes'; self.write_rows()
        self.assertEqual(self.deps(), [self.owner])

    def test_shared_media_id_blocks(self):
        self.rows[0]['video_id'] = 'old-video'; self.write_rows()
        self.assertEqual(self.deps(), [self.owner])

    def test_active_reservation_preserved(self):
        self.rows[0]['reservation_request_id'] = self.owner; self.write_rows(); before = self.inv.read_bytes()
        self.assertEqual(self.deps(), [self.owner])
        self.assertEqual(before, self.inv.read_bytes())
        with self.assertRaises(BlockingIOError): q.claim_terminal(self.request, '123', self.base)
        self.assertEqual(before, self.inv.read_bytes())

    def test_any_active_writer_lease_blocks(self):
        for status in ['IN_PROGRESS','RECOVERY_PENDING','ACTIVATION_PENDING','UNKNOWN','COMPLETE']:
            with self.subTest(status=status):
                q.atomic(self.lease, {'account_id': '123', 'request_id': 'another-writer',
                                     'status': status, 'blocks_readers': True})
                self.assertEqual(self.deps(), [self.owner])

    def test_ambiguous_lease_blocks(self):
        for lease in [{}, {'account_id':'123','status':'COMPLETE','blocks_readers':False},
                      {'account_id':'other','status':'COMPLETE','blocks_readers':False,'released_at_utc':'yes'}]:
            with self.subTest(lease=lease):
                q.atomic(self.lease, lease); self.assertEqual(self.deps(), [self.owner])

    def test_account_process_lock_blocks(self):
        with self.alock.open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.deps(), [self.owner])

    def test_writer_lease_update_lock_blocks(self):
        with self.lease.with_suffix('.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.deps(), [self.owner])

    def test_missing_record_blocks(self):
        dw.record_path(self.base, self.owner).unlink(); self.assertEqual(self.deps(), [self.owner])

    def test_state_drift_blocks(self):
        self.state['unreconciled'] = True; q.atomic(self.spath, self.state)
        self.assertEqual(self.deps(), [self.owner])

    def test_engine_checkpoint_drift_blocks(self):
        self.cp.write_text('{}'); self.assertEqual(self.deps(), [self.owner])

    def test_unknown_phase_with_record_blocks(self):
        self.state['phase'] = 'UNKNOWN'; self.seal(); self.assertEqual(self.deps(), [self.owner])

    def test_engine_incomplete_or_activation_in_progress_blocks(self):
        for status in ['IN_PROGRESS','DEFERRED_QUOTA','COMPLETE_FUTURE_ACTIVE', None]:
            with self.subTest(status=status):
                self.state['engine_result']['status'] = status; self.seal()
                self.assertEqual(self.deps(), [self.owner])

    def test_partial_or_ambiguous_qa_blocks(self):
        for key in ['qa_proof','summary','media_qa','activation_result']:
            with self.subTest(key=key):
                self.state[key] = {'partial':True}; self.seal(); self.assertEqual(self.deps(), [self.owner])
                self.state.pop(key)

    def test_bad_review_or_nonpaused_object_blocks(self):
        for mutate in [lambda: self.record['review'].update(decision='APPROVED'),
                       lambda: self.record['review'].update(author_id='HUMAN'),
                       lambda: self.record['review'].update(material_difference=False),
                       lambda: self.record['campaign_readback'][0].update(status='ACTIVE')]:
            old = copy.deepcopy(self.record); mutate(); self.seal()
            self.assertEqual(self.deps(), [self.owner]); self.record = old

    def test_no_selected_media_fails_closed(self):
        self.request.pop('campaign_groups'); self.assertEqual(self.deps(), [self.owner])

    def test_other_partition_fails_closed(self):
        self.request['source_channel_id'] = 'OTHER'; self.assertEqual(self.deps(), [self.owner])

    def test_other_account_not_serialized(self):
        self.assertEqual(q.dependencies(self.request, '456', self.base), [])

    def test_bad_evidence_does_not_bypass_by_queue_cycle(self):
        self.record['review']['decision'] = 'UNKNOWN'; self.seal()
        q.enqueue(self.state['request'], 'campaign', [self.rid], self.base)
        self.assertEqual(self.deps(), [self.owner])

    def queue(self):
        q.enqueue(self.request, 'prepare-media', [self.owner], self.base)
        return json.loads(q.job_path(self.base,self.rid).read_text())

    def test_other_active_writer_still_serializes_account(self):
        other = {'request': {'request_id': 'other-writer', 'account': '123'}, 'phase': 'ENGINE_PENDING'}
        q.atomic(q.root(self.base) / 'single-clone/other-writer/state.json', other)
        self.assertEqual(self.deps(), ['other-writer'])

    def test_inventory_media_alias_blocks(self):
        self.rows[0]['meta_video_id'] = 'old-video'; self.write_rows()
        self.assertEqual(self.deps(), [self.owner])

    def test_filename_in_historical_ad_name_blocks(self):
        name = 'SHEIN_US_ES_IMG_BOLSAS_GRATIS_NV_001'
        self.state['manifest']['campaigns'][0]['ads'][0]['name'] = 'AD 01 - ' + name
        self.seal(); self.rows[0]['canonical_filename'] = name + '.png'; self.write_rows()
        self.request['campaign_groups'][0]['files'] = [name + '.png']
        self.assertEqual(self.deps(), [self.owner])

    def test_incomplete_historical_media_fails_closed(self):
        self.state['manifest']['campaigns'][0]['ads'] = [{'name': 'unknown'}]
        self.seal(); self.assertEqual(self.deps(), [self.owner])

    def test_cross_account_or_active_manifest_fails_closed(self):
        for key, val in [('account_id', '456'), ('status', 'ACTIVE')]:
            with self.subTest(key=key):
                old = copy.deepcopy(self.state); self.state['manifest']['campaigns'][0][key] = val
                self.seal(); self.assertEqual(self.deps(), [self.owner]); self.state = old

    def test_durable_maintenance_hold_beats_stale_worker_snapshot(self):
        job = self.queue(); live = copy.deepcopy(job); live['maintenance_hold'] = {'task':'maintenance'}
        q.atomic(q.job_path(self.base,self.rid),live)
        with patch.object(q.subprocess,'run') as run:
            q.tick(job,self.base)
        run.assert_not_called()
        self.assertEqual(json.loads(q.job_path(self.base,self.rid).read_text()),live)

    def test_foreground_owner_is_never_autoexecuted(self):
        job = self.queue(); job['dispatch_owner'] = 'foreground'
        q.atomic(q.job_path(self.base,self.rid),job)
        with patch.object(q.subprocess,'run') as run: q.tick(job,self.base)
        run.assert_not_called()

    def test_historical_review_never_autoexecuted(self):
        q.enqueue(self.state['request'],'campaign',[],self.base)
        job = json.loads(q.job_path(self.base,self.owner).read_text())
        with patch.object(q.subprocess,'run') as run: q.tick(job,self.base)
        run.assert_not_called()

    def test_non_ares_cannot_take_handoff(self):
        self.queue()
        with patch.dict(os.environ, {'HERMES_PROFILE':'zeus'}):
            with self.assertRaisesRegex(ValueError,'Ares profile'): q.take_foreground(self.request,self.base)

    def test_ares_handoff_is_dry_and_preserves_immutable_request(self):
        self.queue(); before = self.inv.read_bytes()
        with patch.dict(os.environ,{'HERMES_PROFILE':'ares'}), patch.object(q,'authorize_queue_request',return_value={'account_id':'123'}), patch.object(q.subprocess,'run') as run:
            out = q.take_foreground(self.request,self.base)
        run.assert_not_called(); self.assertEqual(out['campaign_writes'],0)
        job = json.loads(q.job_path(self.base,self.rid).read_text())
        self.assertEqual(job['request'],self.request); self.assertEqual(job['dispatch_owner'],'foreground')
        self.assertEqual(before,self.inv.read_bytes())

    def test_dispatch_lock_prevents_handoff_worker_race(self):
        job=self.queue(); path=q.job_path(self.base,self.rid)
        with path.with_suffix('.dispatch.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(q.subprocess,'run') as run: q.tick(job,self.base)
            run.assert_not_called()
            with patch.dict(os.environ,{'HERMES_PROFILE':'ares'}), patch.object(q,'authorize_queue_request',return_value={'account_id':'123'}):
                with self.assertRaises(BlockingIOError): q.take_foreground(self.request,self.base)

    def test_handoff_rejects_changed_request_or_running_job(self):
        self.queue()
        with patch.dict(os.environ,{'HERMES_PROFILE':'ares'}), patch.object(q,'authorize_queue_request',return_value={'account_id':'123'}):
            with self.assertRaises(ValueError):q.take_foreground({**self.request,'budget_usd':'99'},self.base)
            job=json.loads(q.job_path(self.base,self.rid).read_text());job['status']='RUNNING';q.atomic(q.job_path(self.base,self.rid),job)
            with self.assertRaises(ValueError):q.take_foreground(self.request,self.base)


if __name__ == '__main__': unittest.main()
