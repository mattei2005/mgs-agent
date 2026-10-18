"""Offline regression for Rodolfo's observer-only source exclusion."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_lean import observation_url,tracking_query_matches

class SourceRemovalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.root=Path(self.tmp.name)
  self.path=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';self.path.parent.mkdir(parents=True)
  self.route={'observation_query_flag':{'name':'nocache','value':None},'observation_query_removal':{'enabled':True,'keys':['utm_source'],'authority_message_id':'1561388270649221291','applies_to':'OBSERVER_URL_ONLY_NOT_META_CAMPAIGN_URL'}}
  self.sync();self.mock=patch.object(core,'BASE',self.root);self.mock.start()
 def tearDown(self):self.mock.stop();self.tmp.cleanup()
 def sync(self):self.path.write_text(json.dumps({'active_observation_route':self.route}))
 def test_exact_delta_and_idempotence(self):
  u='https://example.invalid/r/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b01fb01c138&utm_adgroup=b01fb01c138g01&x=%2F+%20'
  expected='https://example.invalid/r/?utm_medium=g002-s&utm_campaign=b01fb01c138&utm_adgroup=b01fb01c138g01&x=%2F+%20&nocache'
  self.assertEqual(observation_url(u),expected);self.assertEqual(observation_url(expected),expected)
 def test_all_source_values_and_duplicates_removed(self):
  self.assertEqual(observation_url('https://example.invalid/?x=1&utm_source=&utm_source=other&utm_source&x=2'),'https://example.invalid/?x=1&x=2&nocache')
 def test_encoded_source_key_and_encoded_other_values(self):
  self.assertEqual(observation_url('https://example.invalid/?utm%5Fsource=facebook&x=utm_source%3Dfacebook'),'https://example.invalid/?x=utm_source%3Dfacebook&nocache')
 def test_only_source_becomes_bare_flag(self):
  self.assertEqual(observation_url('https://example.invalid/?utm_source=facebook'),'https://example.invalid/?nocache')
 def test_fragment_preserved_flag_before_fragment(self):
  self.assertEqual(observation_url('https://example.invalid/?utm_source=facebook&x=%2f#section'),'https://example.invalid/?x=%2f&nocache#section')
 def test_source_like_other_keys_unchanged(self):
  self.assertEqual(observation_url('https://example.invalid/?not_utm_source=a&UTM_SOURCE=b'),'https://example.invalid/?not_utm_source=a&UTM_SOURCE=b&nocache')
 def test_disabled_historical_rule(self):
  self.route.pop('observation_query_removal');self.sync()
  self.assertEqual(observation_url('https://example.invalid/?utm_source=facebook'),'https://example.invalid/?utm_source=facebook&nocache')
 def test_no_flag_still_removes_source(self):
  self.route.pop('observation_query_flag');self.sync()
  self.assertEqual(observation_url('https://example.invalid/?utm_source=facebook&x=%2F'),'https://example.invalid/?x=%2F')
 def test_guard_rejects_other_removals(self):
  self.route['observation_query_removal']['keys']=['utm_campaign'];self.sync()
  with self.assertRaises(ValueError):observation_url('https://example.invalid/?utm_source=facebook')
 def test_guard_requires_observer_only(self):
  self.route['observation_query_removal']['applies_to']='META';self.sync()
  with self.assertRaises(ValueError):observation_url('https://example.invalid/?utm_source=facebook')
 def test_tracking_accepts_only_delta_and_historical(self):
  original='utm_source=facebook&utm_campaign=b01fb01c138&utm_adgroup=b01fb01c138g01'
  actual='utm_campaign=b01fb01c138&utm_adgroup=b01fb01c138g01&nocache'
  self.assertTrue(tracking_query_matches(actual,original));self.assertTrue(tracking_query_matches(original+'&nocache',original))
  for bad in [actual.replace('c138g01','c139g01'),actual+'&extra=x',actual.replace('&nocache','&nocache=1')]:self.assertFalse(tracking_query_matches(bad,original))
 def test_original_campaign_payload_unchanged(self):
  payload={'effective_campaign_url':'https://example.invalid/quiz/?utm_source=facebook&utm_campaign=b01fb01c138'}
  before=json.dumps(payload,sort_keys=True);observation_url(payload['effective_campaign_url']);self.assertEqual(json.dumps(payload,sort_keys=True),before)

if __name__=='__main__':unittest.main()
