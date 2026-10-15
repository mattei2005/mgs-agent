"""Offline PC1 reliability tests; fixtures are not live ad observations."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_direct_traffic_landing_followup as old
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3 import landing_reliability as rel
from ares_campaign_v3 import landing_screenshot_cleanup as cleanup
from ares_campaign_v3 import landing_intake as intake
from ares_campaign_v3 import landing_followup_reporting as reporting


class ReliabilityTests(unittest.TestCase):
    setUpBase=old.FollowupTests.setUp
    tearDown=old.FollowupTests.tearDown
    arm=old.FollowupTests.arm
    closure=old.FollowupTests.closure
    success=old.FollowupTests.success

    def setUp(self):
        self.setUpBase();self.path=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';self.path.parent.mkdir(exist_ok=True)
        self.cfg={'pc1_execution_policy':{'enabled':True,'technical_error_limit':3,'technical_retry_delay_seconds':0,'resource_priority':'PHYSICAL_PC1_ONLY','delete_screenshots_after_complete':True},'no_ad_retry_policy':{'enabled':True,'generation':'offline-zero','authority_thread_id':core.INCIDENT_THREAD,'initial_no_ad_attempts':3,'final_no_ad_attempts':1,'retry_after_seconds':0}}
        self.path.write_text(json.dumps(self.cfg))

    def error(self,key=None,idx=0):
        key=key or self.key;j=self.q.claim('worker');self.assertEqual(j['key'],key);self.q.begin(key,'worker',idx)
        n=self.q.job(key)['links'][idx]['attempt'];self.q.result(key,'worker',idx,'ERROR',{**self.closure('error-'+str(n)),'diagnosis':'offline opening/capture failure'})

    def test_zero_delay_and_same_process_retry_but_no_fourth_absence(self):
        self.arm();self.q.claim('worker')
        for n in range(1,4):
            self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'NO_AD',self.closure('noad-'+str(n)))
            link=self.q.job(self.key)['links'][0]
            if n<3:
                self.assertEqual(link['due'],self.clock.value)
                rel.reclaim_retry(self.q,self.key,'worker',0)
        self.assertEqual(self.q.job(self.key)['state'],'DEFERRED_NO_AD')
        with self.assertRaises(ValueError):rel.reclaim_retry(self.q,self.key,'worker',0)

    def test_retry_directories_differ_between_attempts_same_owner(self):
        self.assertNotEqual(rel.run_directory(self.q,'worker',self.key,0,1),rel.run_directory(self.q,'worker',self.key,0,2))

    def test_third_technical_error_is_hard_block_and_not_no_ad(self):
        self.arm()
        for _ in range(3):self.error()
        self.assertEqual(self.q.job(self.key)['state'],'TECHNICAL_REPAIR');self.assertEqual(self.q.no_ad_count(self.key,0),0)
        self.assertIsNone(self.q.claim('ordinary'))
        j=self.q.claim_recovery('repair');self.assertEqual(j['state'],'REPAIRING')
        with self.assertRaises(ValueError):self.q.begin(self.key,'repair',0)
        with self.assertRaisesRegex(ValueError,'probe receipt'):rel.approve_repair(self.q,self.key,'repair',0,'invented.json')

    def test_begin_guard_still_blocks_if_only_state_flag_is_changed(self):
        self.arm()
        for _ in range(3):self.error()
        with self.q.tx():
            self.q.db.execute("UPDATE jobs SET state='RUNNING',owner='worker',lease_until=? WHERE key=?",(self.clock.value+600,self.key))
            self.q.db.execute("UPDATE links SET state='WAIT_RETRY' WHERE job=?",(self.key,))
        with self.assertRaisesRegex(ValueError,'technical-repair gate'):self.q.begin(self.key,'worker',0)

    def test_verified_probe_releases_gate_without_resetting_absence_history(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'NO_AD',self.closure('noad'))
        for _ in range(3):self.error()
        self.q.claim_recovery('repair')
        with self.q.tx():self.q.event(self.key,'technical_probe_verified',{'owner':'repair','idx':0,'probe_file':'offline-real-probe-receipt.json'})
        rel.approve_repair(self.q,self.key,'repair',0,'offline-real-probe-receipt.json')
        self.assertEqual(rel.technical_errors(self.q,self.key,0),0);self.assertEqual(self.q.no_ad_count(self.key,0),1)
        self.assertEqual(self.q.job(self.key)['state'],'READY')

    def multi(self):
        p=copy.deepcopy(self.payload);p['operation']='PC1-MULTI';p['links'].append(copy.deepcopy(p['links'][0]))
        for f in ['effective_campaign_url','landing_url']:p['links'][1][f]=p['links'][1][f].replace('g01','g02')
        key=self.q.stage(p,lambda _:True);core.publish_creation(self.q,key,'offline multi',self.dc);return key

    def test_safe_technical_failure_does_not_hold_next_link(self):
        key=self.multi()
        for _ in range(3):self.error(key,0)
        self.assertEqual(self.q.job(key)['state'],'READY');self.assertIsNone(self.q.claim_recovery('repair'))
        self.assertEqual(self.q.claim('next')['key'],key);self.q.begin(key,'next',1)

    def test_fair_due_selection_skips_future_due_head(self):
        key=self.multi()
        with self.q.tx():self.q.db.execute('UPDATE links SET due=? WHERE job=? AND idx=0',(self.clock.value+60,key))
        self.assertEqual(self.q.claim('next')['key'],key);self.q.begin(key,'next',1)

    def test_unrelated_native_turn_does_not_block_pc1_observer(self):
        with patch.object(intake,'POLICY',self.path),patch.object(intake,'readonly',side_effect=AssertionError('must not query unrelated turns')):
            self.assertFalse(intake.native_busy())

    def test_expired_repair_requires_cleanup_and_no_normal_open(self):
        self.arm()
        for _ in range(3):self.error()
        self.q.claim_recovery('repair');self.clock.value+=601;self.q.recover_expired()
        self.assertEqual(self.q.job(self.key)['state'],'NEEDS_RECONCILIATION');self.assertIsNone(self.q.claim('next'))

    def test_claim_is_preparation_not_proven_opening(self):
        self.arm();self.q.claim('worker');cfg={'report_jobs':[self.key]};s=reporting.snapshot(self.q,cfg)
        self.assertEqual(s['opened_jobs'],0);self.assertNotIn('observação em execução',reporting.render(s,self.q,cfg))

    def test_repair_cannot_defer_an_uncertain_probe_window(self):
        self.arm()
        for _ in range(3):self.error()
        self.q.claim_recovery('repair');probe=self.root/'uncertain-probe.json';probe.write_text(json.dumps({'tests_returncode':0,'opening':{'new_window_created':True}}))
        with self.q.tx():self.q.event(self.key,'technical_probe_intent',{'owner':'repair','idx':0,'probe_file':str(probe)})
        with self.assertRaisesRegex(ValueError,'probe window uncertain'):self.q.deferred(self.key,'repair')
        self.assertEqual(self.q.job(self.key)['state'],'REPAIRING')

    def test_repair_can_defer_without_any_probe_input(self):
        self.arm()
        for _ in range(3):self.error()
        self.q.claim_recovery('repair');self.q.deferred(self.key,'repair')
        self.assertEqual(self.q.job(self.key)['state'],'TECHNICAL_REPAIR')

    def completed(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'PASS',self.success())
        self.dc.deliver(self.q,self.key+':success')
        with self.q.tx():self.q.db.execute("UPDATE jobs SET state='COMPLETE' WHERE key=?",(self.key,))

    def files(self):
        artifact=self.root/'artifacts';cache=self.root/'images';photo=artifact/self.key/'0'/'1'/'sample.png';photo.parent.mkdir(parents=True);photo.write_bytes(b'offline-image-not-a-live-screenshot'*10)
        unrelated=cache/'other-task.png';unrelated.parent.mkdir();unrelated.write_bytes(b'unrelated')
        audit=photo.parent/'audit.json';audit.write_text('{"keep":true}')
        return artifact,cache,photo,unrelated,audit

    def test_cleanup_only_after_complete_keeps_json_and_unrelated_images(self):
        self.completed();artifact,cache,photo,unrelated,audit=self.files()
        with patch.object(cleanup,'IMAGE_ROOTS',(artifact,cache)):
            plan=cleanup.prune_completed(self.q);self.assertEqual(plan['files'],1);self.assertTrue(photo.exists())
            result=cleanup.prune_completed(self.q,apply=True);self.assertEqual(result['files'],1);self.assertFalse(photo.exists())
            self.assertEqual(cleanup.prune_completed(self.q,apply=True)['files'],0)
        self.assertTrue(unrelated.exists());self.assertTrue(audit.exists())
        self.assertTrue(json.loads(self.q.job(self.key)['links'][0]['evidence'])['screenshots_purged'])
        self.assertIsNotNone(self.q.db.execute("SELECT 1 FROM events WHERE kind='validated_screenshot_retention_receipt'").fetchone())

    def test_observed_without_verified_completion_never_purges(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'PASS',self.success())
        artifact,cache,photo,_,_=self.files()
        with patch.object(cleanup,'IMAGE_ROOTS',(artifact,cache)):self.assertEqual(cleanup.prune_completed(self.q,apply=True)['files'],0)
        self.assertTrue(photo.exists())

    def test_image_shared_with_incomplete_job_is_protected(self):
        self.completed();artifact,cache,photo,_,_=self.files();p=copy.deepcopy(self.payload);p['operation']='OTHER-PENDING';other=self.q.stage(p,lambda _:True)
        with self.q.tx():self.q.db.execute('UPDATE links SET evidence=? WHERE job=?',(json.dumps({'observation_screenshot':str(photo)}),other))
        with patch.object(cleanup,'IMAGE_ROOTS',(artifact,cache)):self.assertEqual(cleanup.prune_completed(self.q,apply=True)['files'],0)
        self.assertTrue(photo.exists())

    def test_cleanup_refuses_symlink_outside_scope(self):
        self.completed();artifact,cache,photo,_,_=self.files();outside=self.root/'outside.png';outside.write_bytes(b'keep');photo.unlink();photo.symlink_to(outside)
        with patch.object(cleanup,'IMAGE_ROOTS',(artifact,cache)):self.assertEqual(cleanup.prune_completed(self.q,apply=True)['files'],0)
        self.assertTrue(outside.exists())


if __name__=='__main__':unittest.main()
