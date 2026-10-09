"""Offline policy tests: same-day elapsed schedule becomes NOW, no state replay."""
import copy
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import shein_single_clone as route

POLICY={'enabled':True,'approved_by':'344196393512075265','scope':'explicit_start_same_account_day_only','when_elapsed':'IMMEDIATE_AFTER_QA'}
PROFILE={'timezone':'America/New_York','expired_schedule_policy':POLICY}
NOW=datetime(2030,10,9,15,32,tzinfo=timezone.utc)
SOURCE={'campaign':{'daily_budget':'7500'}}

class ElapsedScheduleTests(unittest.TestCase):
    def resolve(self,start,profile=None,**extra):
        r={'start_time':start,'status':'ACTIVE','budget_usd':'75',**extra};before=copy.deepcopy(r)
        out=route.resolve_intent(r,SOURCE,now=NOW,profile=profile or PROFILE)
        self.assertEqual(r,before)
        return out

    def test_expired_today_uses_current_time_with_technical_buffer(self):
        out=self.resolve('2030-10-09T11:30:00-04:00')
        self.assertIs(out.get('start_now'),True)
        self.assertEqual(out['start_time'],'2030-10-09T15:32:30+00:00')
        self.assertEqual(out['schedule_adjustment']['requested_start_time'],'2030-10-09T11:30:00-04:00')
        self.assertEqual(out['status'],'ACTIVE');self.assertEqual(out['budget_usd'],'75')

    def test_exact_current_time_also_becomes_now(self):
        self.assertTrue(self.resolve('2030-10-09T11:32:00-04:00').get('start_now'))

    def test_future_time_same_day_or_future_day_stays_literal(self):
        for start in ['2030-10-09T11:33:00-04:00','2030-10-10T11:30:00-04:00']:
            out=self.resolve(start);self.assertEqual(out['start_time'],start);self.assertNotIn('start_now',out)

    def test_expired_prior_date_not_silently_moved(self):
        start='2030-10-08T11:30:00-04:00';out=self.resolve(start)
        self.assertEqual(out['start_time'],start);self.assertNotIn('start_now',out)

    def test_disabled_or_unapproved_policy_preserves_old_behavior(self):
        for p in [{'timezone':'America/New_York'}, {'timezone':'America/New_York','expired_schedule_policy':{**POLICY,'approved_by':'other'}}]:
            out=self.resolve('2030-10-09T11:30:00-04:00',profile=p)
            self.assertNotIn('start_now',out)

    def test_paused_stays_paused(self):
        out=self.resolve('2030-10-09T11:30:00-04:00',status='PAUSED')
        self.assertTrue(out.get('start_now'));self.assertEqual(out['status'],'PAUSED')

    def test_midnight_default_not_changed_to_now(self):
        out=self.resolve('2030-10-09T00:00:00-04:00',start_next_midnight=True)
        self.assertNotIn('start_now',out)

    def test_account_timezone_defines_calendar_day(self):
        p={'timezone':'America/Los_Angeles','expired_schedule_policy':POLICY}
        # Still yesterday in Los Angeles although UTC date is today.
        original=copy.deepcopy(NOW)
        r={'start_time':'2030-10-09T00:00:00+00:00'}
        out=route.resolve_intent(r,SOURCE,now=datetime(2030,10,9,1,0,tzinfo=timezone.utc),profile=p)
        self.assertTrue(out.get('start_now'))
        self.assertEqual(NOW,original)

if __name__=='__main__':unittest.main()
