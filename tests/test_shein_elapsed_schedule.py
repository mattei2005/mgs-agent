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

    def test_elapsed_intake_builds_immediate_target_without_mutating_source(self):
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from test_shein_general_runtime import case
        from ares_campaign_v3 import shein_general as general
        from ares_campaign_v3.schema import Manifest
        r,s,a,_=case(4,status='ACTIVE');r['start_time']='2030-10-09T11:30:00-04:00'
        before=copy.deepcopy(s)
        resolved=route.resolve_intent(r,s,now=NOW,profile=PROFILE)
        payload=general.build(resolved,s,114,a)
        self.assertEqual(payload['campaigns'][0]['start_intent'],'IMMEDIATE')
        self.assertEqual(Manifest.from_dict(payload).campaigns[0].start_intent,'IMMEDIATE')
        self.assertEqual(r['start_time'],'2030-10-09T11:30:00-04:00');self.assertEqual(s,before)

    def test_elapsed_intent_crosses_real_manifest_validation_boundary(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_shein_general_runtime import case
        from ares_campaign_v3.schema import Manifest
        for status in ('ACTIVE', 'PAUSED'):
            with self.subTest(status=status):
                request, source, account, _ = case(4, status=status)
                request.update(start_time='2030-10-09T11:30:00-04:00',
                               budget_usd='100', bid_strategy='COCAP', bid_usd='0.85')
                original = copy.deepcopy((request, source))
                resolved = route.resolve_intent(request, source, now=NOW, profile=PROFILE)
                audit = copy.deepcopy(resolved['schedule_adjustment'])
                payload = route.build_manifest(resolved, source, 114, account)
                campaign = Manifest.from_dict(payload).campaigns[0]
                self.assertEqual(campaign.start_intent, 'IMMEDIATE')
                self.assertEqual(payload['campaigns'][0]['status'], status)
                self.assertEqual(payload['campaigns'][0]['campaign_updates']['daily_budget'], '10000')
                self.assertEqual(payload['campaigns'][0]['campaign_updates']['bid_strategy'], 'COST_CAP')
                self.assertEqual(payload['campaigns'][0]['adset_updates']['bid_amount'], '85')
                self.assertEqual(resolved['schedule_adjustment'], audit)
                self.assertEqual((request, source), original)
                self.assertNotIn('schedule_adjustment', payload['campaigns'][0])

    def test_schedule_audit_is_not_accepted_as_human_request_field(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_shein_general_runtime import case
        request, _, _, _ = case(4)
        request['schedule_adjustment'] = {'intent': 'IMMEDIATE_AFTER_QA'}
        with self.assertRaisesRegex(route.RouteBlocked, 'unknown request field'):
            route.validate_request(request)
        with self.assertRaisesRegex(route.RouteBlocked, 'unknown request field'):
            route.run_request(request, confirm_execute=False)

    def test_unrelated_internal_field_still_fails_manifest_boundary(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_shein_general_runtime import case
        request, source, account, _ = case(4)
        request['skip_qa'] = True
        with self.assertRaisesRegex(route.RouteBlocked, 'unknown request field'):
            route.build_manifest(request, source, 114, account)

    def test_account_timezone_defines_calendar_day(self):
        p={'timezone':'America/Los_Angeles','expired_schedule_policy':POLICY}
        # Still yesterday in Los Angeles although UTC date is today.
        original=copy.deepcopy(NOW)
        r={'start_time':'2030-10-09T00:00:00+00:00'}
        out=route.resolve_intent(r,SOURCE,now=datetime(2030,10,9,1,0,tzinfo=timezone.utc),profile=p)
        self.assertTrue(out.get('start_now'))
        self.assertEqual(NOW,original)

if __name__=='__main__':unittest.main()
