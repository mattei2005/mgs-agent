"""Offline3+1+60s+1 fixtures: not evidence of actual ads or live visits."""
import json,unittest
from unittest.mock import patch
import test_direct_traffic_landing_retry_policy as retry_fixtures
from ares_campaign_v3 import landing_retry_policy as finite
from ares_campaign_v3 import landing_followup as core

class AutomaticRecoveryTests(unittest.TestCase):
    setUpBase=retry_fixtures.FiniteRetryTests.setUpBase
    setUp=retry_fixtures.FiniteRetryTests.setUp
    tearDown=retry_fixtures.FiniteRetryTests.tearDown
    arm=retry_fixtures.FiniteRetryTests.arm
    success=retry_fixtures.FiniteRetryTests.success
    attempt=retry_fixtures.FiniteRetryTests.attempt
    exhaust=retry_fixtures.FiniteRetryTests.exhaust
    closure=retry_fixtures.FiniteRetryTests.closure
    multi=retry_fixtures.FiniteRetryTests.multi
    def enable_extra(self):
        self.cfg['automatic_recovery']={'enabled':True,'additional_no_ad_attempts':1,'wait_after_round_seconds':60}
        self.path.write_text(json.dumps({'no_ad_retry_policy':self.cfg}))
    def waiting(self):
        self.arm();self.exhaust();finite.maintain(self.q);self.attempt();self.enable_extra()
        # This helper enables the new rule BEFORE the fourth result in new tests.
    def exhaust_four(self):
        self.enable_extra();self.arm();self.exhaust();finite.maintain(self.q);self.attempt()
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'COOLDOWN_NO_AD')
    def test_cooldown_is60_seconds_and_durable(self):
        self.exhaust_four();first=finite.maintain(self.q);self.assertEqual(first['state'],'AUTOMATIC_RECOVERY_COOLDOWN');due=first['due']
        self.assertFalse(first['pc1_lease_required']);self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],4)
        self.clock.value=due-1;self.assertEqual(finite.maintain(self.q)['due'],due);self.assertIsNone(self.q.claim('early'))
        self.clock.value=due;self.assertEqual(finite.maintain(self.q)['state'],'AUTOMATIC_RECOVERY_SCHEDULED')
        self.assertEqual(self.q.no_ad_count(self.key,0),0);self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],4)
    def test_fifth_pass_without_manual_request(self):
        self.exhaust_four();due=finite.maintain(self.q)['due'];self.clock.value=due;finite.maintain(self.q);self.attempt(result='PASS')
        self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],5);self.assertEqual(self.q.job(self.key)['state'],'OBSERVED')
        self.assertIsNone(self.q.db.execute("select 1 from messages where key like 'landing-final-review:%'").fetchone())
    def test_fifth_absence_reports_once_and_no_sixth(self):
        self.exhaust_four();due=finite.maintain(self.q)['due'];self.clock.value=due;finite.maintain(self.q);self.attempt();finite.maintain(self.q);finite.maintain(self.q)
        j=self.q.job(self.key);self.assertEqual(j['links'][0]['state'],'REVIEW_REQUIRED');self.assertEqual(j['links'][0]['attempt'],5)
        self.assertIsNone(self.q.claim('sixth'));self.assertIsNone(self.q.claim_recovery('sixth'))
        notices=self.q.db.execute("select * from messages where key like 'landing-final-review:%'").fetchall();self.assertEqual(len(notices),1);self.assertIn('recuperação automática após60segundos',notices[0]['content'])
    def test_no_premature_review_during_wait(self):
        self.exhaust_four();finite.maintain(self.q)
        self.assertIsNone(self.q.db.execute("select 1 from messages where key like 'landing-final-review:%'").fetchone())
    def test_cooldown_waits_for_all_final_peers(self):
        self.enable_extra();key=self.multi();self.exhaust(key,0);self.exhaust(key,1)
        finite.maintain(self.q);self.attempt(key,0);finite.maintain(self.q)
        self.assertIsNone(self.q.db.execute("select 1 from events where kind='finite_automatic_recovery_wait'").fetchone())
        self.attempt(key,1);wait=finite.maintain(self.q);self.assertEqual(wait['state'],'AUTOMATIC_RECOVERY_COOLDOWN')
        self.clock.value=wait['due'];finite.maintain(self.q);self.attempt(key,0,'PASS');finite.maintain(self.q);self.attempt(key,1,'PASS')
        self.assertEqual(self.q.db.execute("select count(*) from events where kind='finite_automatic_recovery_wait'").fetchone()[0],1)
        self.assertEqual(self.q.job(key)['state'],'OBSERVED')
    def test_error_is_not_additional_absence(self):
        self.exhaust_four();self.clock.value=finite.maintain(self.q)['due'];finite.maintain(self.q)
        self.clock.value+=1;self.q.claim('worker');self.q.begin(self.key,'worker',0)
        self.q.result(self.key,'worker',0,'ERROR',{**self.closure('technical'),'diagnosis':'offline transport failure'})
        self.assertEqual(self.q.no_ad_count(self.key,0),0);self.assertEqual(self.q.job(self.key)['state'],'READY')
    def test_reviewed_history_not_rearmed_by_rule_change(self):
        self.arm();self.exhaust();finite.maintain(self.q);self.attempt();self.enable_extra();finite.maintain(self.q)
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'REVIEW_REQUIRED');self.assertIsNone(finite.recovery_start(self.q,self.key,0))
    def test_reject_unbounded_or_wrong_delay(self):
        self.enable_extra();self.cfg['automatic_recovery']['additional_no_ad_attempts']=2;self.path.write_text(json.dumps({'no_ad_retry_policy':self.cfg}))
        with self.assertRaises(ValueError):finite.policy()
    def test_lean_closure_uses_current_native_time_not_image(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0)
        with self.q.tx():self.q.db.execute('update links set evidence=? where job=?',(json.dumps({'observation_mode':'LEAN_NORMAL_NEW_TAB','closed_at':self.clock.value+1}),self.key))
        link=self.q.job(self.key)['links'][0]
        with patch.object(core,'validate_closure'),patch.object(core,'file_evidence',side_effect=AssertionError('No image gallery required')):self.assertTrue(finite.closed_latest(self.q,self.key,link))
