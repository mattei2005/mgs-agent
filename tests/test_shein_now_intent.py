"""Regression for explicit NOW/inherited budget; no Meta network calls."""
import copy
import unittest
from datetime import datetime,timezone,timedelta
from test_shein_general_runtime import case
from test_shein_single_clone_route import fixture,live_fixture
from ares_campaign_v3 import shein_single_clone as route
from ares_campaign_v3 import shein_general as compiler
from ares_campaign_v3.schema import Manifest,ManifestError

class NowIntentTests(unittest.TestCase):
    def test_request_accepts_now_and_budget_reference_without_manual_lookup(self):
        r,_,_,_=case(1,status='ACTIVE');r.pop('start_time');r.pop('budget_usd');r.update(start_now=True,budget_from_reference=True)
        route.validate_request(r)

    def test_explicit_now_survives_elapsed_technical_buffer_in_schema(self):
        r,s,a,_=case(1,status='ACTIVE');r.update(start_now=True,start_time=(datetime.now(timezone.utc)-timedelta(seconds=60)).replace(microsecond=0).isoformat())
        p=compiler.build(r,s,114,a);self.assertEqual(p['campaigns'][0]['start_intent'],'IMMEDIATE')
        manifest=Manifest.from_dict(p);self.assertEqual(manifest.campaigns[0].start_intent,'IMMEDIATE')

    def test_scheduled_start_expired_still_rejected(self):
        r,s,a,_=case(1,status='ACTIVE');r['start_time']='2000-01-01T00:00:00-04:00'
        with self.assertRaises(ManifestError):Manifest.from_dict(compiler.build(r,s,114,a))

    def test_paused_in_process_does_not_replay_or_reject_valid_media_tree(self):
        r,s,a=fixture();p=route.build_manifest(r,s,114,a);live=live_fixture(p,s);live['campaign']['effective_status']='IN_PROCESS'
        self.assertEqual(route.verify_readback(p,s,live),[])

    def test_resolution_uses_live_budget_and_integer_time_once(self):
        r,s,a,_=case(1,status='ACTIVE');r.pop('start_time');r.pop('budget_usd');r.update(start_now=True,budget_from_reference=True)
        instant=datetime(2026,10,8,16,0,0,987654,tzinfo=timezone.utc)
        resolved=route.resolve_intent(r,s,now=instant)
        self.assertEqual(resolved['budget_usd'],'40')
        self.assertEqual(datetime.fromisoformat(resolved['start_time']).microsecond,0)
        self.assertEqual(r.get('budget_usd'),None)

if __name__=='__main__':unittest.main()
