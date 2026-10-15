"""Offline finite-policy fixtures; never evidence of live advertising."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_direct_traffic_landing_followup as fixtures
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3 import landing_retry_policy as finite
from ares_campaign_v3 import landing_followup_reporting as reporting


class FiniteRetryTests(unittest.TestCase):
    setUpBase=fixtures.FollowupTests.setUp
    tearDown=fixtures.FollowupTests.tearDown
    arm=fixtures.FollowupTests.arm
    success=fixtures.FollowupTests.success

    def setUp(self):
        self.setUpBase()
        self.path=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.cfg={'enabled':True,'generation':'offline-finite-3-1','authority_thread_id':core.INCIDENT_THREAD,'initial_no_ad_attempts':3,'final_no_ad_attempts':1}
        self.path.write_text(json.dumps({'no_ad_retry_policy':self.cfg}))

    def closure(self,tab='unused'):
        return {'new_tab_identity':tab,'tab_closed_verified':True,'other_tabs_preserved':True,'closed_screenshot':f'closed-{self.clock.value+21}.png'}

    def attempt(self,key=None,idx=0,result='NO_AD'):
        key=key or self.key
        self.clock.value+=60
        j=self.q.claim('worker');self.assertEqual(j['key'],key)
        self.q.begin(key,'worker',idx)
        attempt=self.q.job(key)['links'][idx]['attempt']
        e=self.closure(f'tab-{idx}-{attempt}')
        if result=='PASS':
            e.update({'observed_url':self.q.job(key)['payload']['links'][idx]['landing_url'],'network_ad_confirmed':True,'ad_description':'offline fixture only','samples':[{'monotonic_seconds':t,'ad_visible':True,'tab_active':True,'screenshot':f'fixture-{self.clock.value+t}.png'} for t in [0,5,10]]})
        self.q.result(key,'worker',idx,result,e)

    def exhaust(self,key=None,idx=0):
        for _ in range(3):self.attempt(key,idx)

    def test_three_absences_then_defer_not_recovery(self):
        self.arm()
        for n in [1,2]:
            self.attempt();self.assertEqual(self.q.job(self.key)['links'][0]['state'],'WAIT_RETRY');self.assertEqual(self.q.no_ad_count(self.key,0),n)
        self.attempt();self.assertEqual(self.q.job(self.key)['state'],'DEFERRED_NO_AD')
        self.assertIsNone(self.q.claim_recovery('repair'))
        self.assertIsNone(self.q.claim('other'))
        self.assertEqual(self.q.no_ad_count(self.key,0),3)

    def test_final_one_attempt_then_single_review_report(self):
        self.arm();self.exhaust();self.assertEqual(finite.maintain(self.q)['state'],'FINAL_RETRY_SCHEDULED')
        self.assertEqual(self.q.no_ad_count(self.key,0),0)
        self.attempt();self.assertEqual(self.q.job(self.key)['links'][0]['state'],'REVIEW_REQUIRED')
        finite.maintain(self.q);finite.maintain(self.q)
        rows=self.q.db.execute("SELECT * FROM messages WHERE key LIKE 'landing-final-review:%'").fetchall()
        self.assertEqual(len(rows),1);self.assertIn('3 tentativas iniciais e em 1 tentativa final',rows[0]['content'])
        self.dc.deliver(self.q,rows[0]['key']);self.dc.deliver(self.q,rows[0]['key']);self.assertEqual(self.dc.posts,2)
        self.assertIsNone(self.q.claim('again'));self.assertIsNone(self.q.claim_recovery('again'))
        self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],4)
        self.assertIsNone(self.q.db.execute('SELECT 1 FROM messages WHERE content=?',(core.SUCCESS,)).fetchone())

    def test_final_success_keeps_exact_success_gate(self):
        self.arm();self.exhaust();finite.maintain(self.q);self.attempt(result='PASS');finite.maintain(self.q)
        self.assertEqual(self.q.job(self.key)['state'],'OBSERVED')
        self.assertIsNotNone(self.q.db.execute('SELECT 1 FROM messages WHERE content=?',(core.SUCCESS,)).fetchone())
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM messages WHERE key LIKE 'landing-final-review:%'").fetchone())

    def multi(self):
        p=copy.deepcopy(self.payload);p['operation']='FINITE-MULTI';p['links'].append(copy.deepcopy(p['links'][0]))
        for f in ['effective_campaign_url','landing_url']:p['links'][1][f]=p['links'][1][f].replace('g01','g02')
        key=self.q.stage(p,lambda u:True);core.publish_creation(self.q,key,'offline multi',self.dc)
        return key

    def test_skip_to_next_before_final_then_return(self):
        key=self.multi();self.exhaust(key,0)
        self.assertEqual(self.q.job(key)['state'],'READY')
        self.assertEqual(finite.maintain(self.q)['state'],'INITIAL_OR_FINAL_IN_PROGRESS')
        self.assertIsNone(finite.final_start(self.q,key,0))
        self.attempt(key,1,'PASS');finite.maintain(self.q)
        self.assertIsNotNone(finite.final_start(self.q,key,0))
        self.assertEqual(self.q.job(key)['links'][1]['state'],'PASSED')

    def test_report_waits_for_all_final_links(self):
        key=self.multi();self.exhaust(key,0);self.exhaust(key,1)
        finite.maintain(self.q);self.attempt(key,0)
        finite.maintain(self.q)
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM messages WHERE key LIKE 'landing-final-review:%'").fetchone())
        self.attempt(key,1);finite.maintain(self.q)
        self.assertEqual(self.q.db.execute("SELECT count(*) FROM messages WHERE key LIKE 'landing-final-review:%'").fetchone()[0],2)

    def test_preserve_legacy_two_absences_only_add_third(self):
        self.path.write_text('{}');self.arm();self.attempt();self.attempt()
        self.assertEqual(self.q.job(self.key)['state'],'ATTENTION')
        self.path.write_text(json.dumps({'no_ad_retry_policy':self.cfg}))
        finite.maintain(self.q);self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],2)
        self.attempt();self.assertEqual(self.q.job(self.key)['state'],'DEFERRED_NO_AD')
        self.assertEqual(self.q.no_ad_count(self.key,0),3)

    def test_live_worker_not_migrated(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0)
        self.assertEqual(finite.maintain(self.q)['state'],'WAITING_SAFE_BOUNDARY')
        self.assertEqual(self.q.job(self.key)['state'],'RUNNING')

    def test_uncertain_closure_blocks_final(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0)
        self.q.result(self.key,'worker',0,'ERROR',{'diagnosis':'offline uncertain tab'})
        self.assertEqual(finite.maintain(self.q)['state'],'WAITING_SAFE_BOUNDARY')
        self.assertIsNone(self.q.claim('other'))

    def test_technical_error_does_not_consume_no_ad(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0)
        self.q.result(self.key,'worker',0,'ERROR',{**self.closure('technical'),'diagnosis':'offline capture failed'})
        self.assertEqual(self.q.no_ad_count(self.key,0),0)
        self.assertEqual(self.q.job(self.key)['state'],'READY')

    def test_missing_latest_closure_cannot_migrate(self):
        self.path.write_text('{}');self.arm();self.attempt();self.attempt()
        self.path.write_text(json.dumps({'no_ad_retry_policy':self.cfg}))
        with patch.object(finite,'closed_latest',return_value=False):finite.maintain(self.q)
        self.assertEqual(self.q.job(self.key)['state'],'ATTENTION')

    def test_reporting_stops_after_verified_review_not_fake_complete(self):
        self.arm();self.exhaust();finite.maintain(self.q);self.attempt();finite.maintain(self.q)
        cfg={'enabled':True,'authority_message_id':'150000000000000001','generation':'150000000000000001','thread_id':core.INCIDENT_THREAD,'report_jobs':[self.key]}
        self.assertEqual(reporting.snapshot(self.q,cfg)['phase'],'FINITE_REPORT_PENDING')
        for r in self.q.db.execute("SELECT key FROM messages WHERE key LIKE 'landing-final-review:%'").fetchall():self.dc.deliver(self.q,r['key'])
        s=reporting.snapshot(self.q,cfg);self.assertEqual(s['phase'],'FINITE_REVIEW_DELIVERED');self.assertFalse(s['all_done'])
        reporting.prepare(self.q,cfg);self.clock.value+=900
        self.assertIsNone(reporting.prepare(self.q,cfg))

    def test_worker_prompt_uses_active_three_plus_one_not_legacy_two(self):
        self.arm();j=self.q.job(self.key);j['state']='RECONCILING'
        text=core.worker_prompt(self.key,'worker',0,j)
        self.assertIn('até 3 ausências reais',text);self.assertNotIn('Duas ausências NO_AD confirmadas não permitem',text)

    def test_later_intake_does_not_starve_frozen_final_return(self):
        key=self.multi();self.exhaust(key,0);finite.maintain(self.q)
        p=copy.deepcopy(self.payload);p['operation']='LATER-INTAKE'
        later=self.q.stage(p,lambda u:True);core.publish_creation(self.q,later,'later fixture',self.dc)
        self.clock.value+=1
        # Complete the already frozen peer without exercising unrelated intake.
        with self.q.tx():self.q.db.execute('UPDATE jobs SET created=? WHERE key=?',(self.clock.value,later))
        self.attempt(key,1,'PASS')
        self.assertEqual(finite.maintain(self.q)['state'],'FINAL_RETRY_SCHEDULED')
        self.assertIsNotNone(finite.final_start(self.q,key,0))
        self.assertEqual(self.q.job(later)['state'],'READY')

    def test_migration_is_idempotent_and_never_restarts_existing_history(self):
        self.path.write_text('{}');self.arm();self.attempt();self.attempt()
        self.path.write_text(json.dumps({'no_ad_retry_policy':self.cfg}))
        finite.maintain(self.q);finite.maintain(self.q)
        self.assertEqual(self.q.db.execute("SELECT count(*) FROM events WHERE kind='finite_retry_migrated'").fetchone()[0],1)
        self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],2)


if __name__=='__main__':unittest.main()
