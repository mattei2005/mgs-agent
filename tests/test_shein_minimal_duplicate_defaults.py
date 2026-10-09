"""Bare duplicate + next local midnight defaults; offline only."""
import unittest
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import shein_single_clone as route

POLICY={'operation_id':'SHEIN-US-DIRECT','request_defaults':{'final_status':'ACTIVE','authority':'344196393512075265','scope':'new_creation_requests_only','default_start':'NEXT_LOCAL_DAY_MIDNIGHT','reference_budget_default':'INHERIT_FOR_PURE_CLONE'}}

class MinimalDuplicateTests(unittest.TestCase):
    def test_bare_source_resolves_inherit_budget_and_midnight_marker(self):
        r=route.apply_request_defaults({'source_number':72},POLICY)
        self.assertEqual(r['status'],'ACTIVE');self.assertTrue(r['budget_from_reference']);self.assertTrue(r['start_next_midnight']);self.assertNotIn('start_time',r)

    def test_midnight_uses_account_timezone_not_vps_date(self):
        r=route.apply_request_defaults({'source_number':72},POLICY)
        src={'campaign':{'daily_budget':'15000'}}
        p={'timezone':'America/Los_Angeles'}
        resolved=route.resolve_intent(r,src,now=datetime(2026,10,9,2,0,tzinfo=timezone.utc),profile=p)
        self.assertEqual(resolved['start_time'],'2026-10-09T00:00:00-07:00');self.assertEqual(resolved['budget_usd'],'150')

    def test_calendar_day_resolution_handles_dst_offset(self):
        r=route.apply_request_defaults({'source_number':72},POLICY)
        resolved=route.resolve_intent(r,{'campaign':{'daily_budget':'10000'}},now=datetime(2026,11,1,17,0,tzinfo=timezone.utc),profile={'timezone':'America/New_York'})
        self.assertEqual(resolved['start_time'],'2026-11-02T00:00:00-05:00')

    def test_explicit_now_budget_and_paused_are_never_overridden(self):
        r=route.apply_request_defaults({'source_number':72,'status':'PAUSED','start_now':True,'budget_usd':'30'},POLICY)
        self.assertEqual(r['status'],'PAUSED');self.assertNotIn('start_next_midnight',r);self.assertNotIn('budget_from_reference',r)

    def test_explicit_date_kept_literal(self):
        literal='2030-10-09T00:10:00-04:00';r=route.apply_request_defaults({'source_number':72,'start_time':literal,'budget_usd':'30'},POLICY)
        self.assertEqual(r['start_time'],literal);self.assertNotIn('start_next_midnight',r)

if __name__=='__main__':unittest.main()
