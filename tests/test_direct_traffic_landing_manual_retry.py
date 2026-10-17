"""Offline tests for explicitly authorized, single-target retry."""
import unittest
from unittest.mock import patch
from test_direct_traffic_landing_retry_policy import FiniteRetryTests
from ares_campaign_v3 import landing_retry_policy as finite
from ares_campaign_v3 import landing_followup as core

class ManualRetryTests(FiniteRetryTests):
    def review(self):
        self.arm();self.exhaust();finite.maintain(self.q);self.attempt()
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'REVIEW_REQUIRED')

    def authorize(self,mid='1561029313275633679',due=None):
        return finite.authorize_single_retry(self.q,self.key,0,authority_message_id=mid,authority_thread_id=core.INCIDENT_THREAD,not_before=self.clock.value+300 if due is None else due)

    def test_one_extra_only_with_deadline_and_history(self):
        self.review();before=self.q.job(self.key)['links'][0]['attempt'];due=self.clock.value+300
        self.authorize(due=due)
        self.assertIsNone(self.q.claim('early'))
        self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],before)
        self.assertEqual(self.authorize(due=due)['state'],'ALREADY_AUTHORIZED')
        self.clock.value=due;self.attempt()
        self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],before+1)
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'REVIEW_REQUIRED')
        self.assertEqual(self.authorize(due=due)['state'],'ALREADY_AUTHORIZED')
        self.assertIsNone(self.q.claim('no-loop'))

    def test_success_removes_current_review_but_preserves_events(self):
        self.review();self.authorize();self.clock.value+=300;self.attempt(result='PASS')
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'PASSED')
        self.assertEqual(self.q.job(self.key)['state'],'OBSERVED')
        self.assertTrue(self.q.db.execute("SELECT 1 FROM events WHERE kind='finite_no_ad_exhausted'").fetchone())

    def test_rejects_non_review_and_unclosed(self):
        self.arm()
        with self.assertRaises(ValueError):self.authorize()
        self.exhaust();finite.maintain(self.q);self.attempt()
        with patch.object(finite,'closed_latest',return_value=False):
            with self.assertRaises(ValueError):self.authorize()

    def test_rejects_bad_authority_and_mutated_deadline(self):
        self.review()
        with self.assertRaises(ValueError):self.authorize(mid='invalid')
        due=self.clock.value+300;self.authorize(due=due)
        with self.assertRaises(ValueError):self.authorize(due=due+1)

if __name__=='__main__':unittest.main()
