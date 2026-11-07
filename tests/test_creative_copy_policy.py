"""Permanent copy-only background resolution: offline preservation regressions."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
ROOT=Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/feature-review-1568723180040880239')
class CopyPolicyTests(unittest.TestCase):
 def module(self):
  from ares_campaign_v3 import creative_copy_policy
  return creative_copy_policy
 def setUp(self):self.state=json.loads((ROOT/'state.before.json').read_text())
 def test_only_named_feature_changes_without_source_mutation(self):
  m=self.module();before=copy.deepcopy(self.state)
  for campaign in self.state['manifest']['campaigns']:
   for ad in campaign['ads']:
    original=ad['creative_payload'];out=m.effective(original)
    self.assertEqual(out['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen']['enroll_status'],'OPT_OUT')
    out['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen']['enroll_status']='OPT_IN'
    self.assertEqual(out,original)
  self.assertEqual(self.state,before)
 def test_absent_out_and_other_fields_preserved(self):
  m=self.module()
  for value in [{},{'degrees_of_freedom_spec':{}},{'degrees_of_freedom_spec':{'creative_features_spec':{'image_background_gen':{'enroll_status':'OPT_OUT'},'text_optimizations':{'enroll_status':'OPT_IN'}}}}]:
   self.assertEqual(m.effective(value),value)
 def test_invalid_enrollment_fails_closed(self):
  with self.assertRaises(ValueError):self.module().effective({'degrees_of_freedom_spec':{'creative_features_spec':{'image_background_gen':{'enroll_status':'UNKNOWN'}}}})
 def test_plan_resolves_copies_and_preserves_manifest_seal(self):
  from ares_campaign_v3.schema import Manifest
  from ares_campaign_v3.planning import Planner
  raw=copy.deepcopy(self.state['manifest']);before=copy.deepcopy(raw);plan=Planner().build(Manifest.from_dict(raw))
  n=0
  for bundles in plan.lanes.values():
   for b in bundles:
    for c in b.campaigns:
     for ad in c.ads:
      n+=1;self.assertEqual(ad.creative_payload['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen']['enroll_status'],'OPT_OUT')
    for stage in b.stages:
     for op in stage.operations:
      p=op.body or {};d=p.get('degrees_of_freedom_spec') or p.get('creative_parameters',{}).get('degrees_of_freedom_spec')
      if d:self.assertEqual(d['creative_features_spec']['image_background_gen']['enroll_status'],'OPT_OUT')
  self.assertEqual(n,10);self.assertEqual(raw,before)
 def test_degree_qa_requires_out_and_every_other_feature(self):
  m=self.module();p=self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload'];resolved=m.effective(p)
  m.verify_creative(resolved,p)
  for mutation in ['background','other','omit']:
   bad=copy.deepcopy(resolved);f=bad['degrees_of_freedom_spec']['creative_features_spec']
   if mutation=='background':f['image_background_gen']['enroll_status']='OPT_IN'
   elif mutation=='other':f['text_optimizations']['enroll_status']='OPT_OUT'
   else:f.pop('text_optimizations')
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):m.verify_creative(bad,p)
 def test_receipt_binds_original_and_effective_without_changing_ids(self):
  from ares_campaign_v3.schema import Manifest
  from ares_campaign_v3.planning import Planner
  m=self.module();bundle=next(iter(Planner().build(Manifest.from_dict(self.state['manifest'])).lanes.values()))[0]
  record={'sealed_manifest_digest':'original-seal','campaign_ids':['1','2'],'adset_ids':['3','4']}
  m.record_resolution(bundle,record);saved=copy.deepcopy(record)
  m.record_resolution(bundle,record);self.assertEqual(record,saved)
  self.assertEqual(record['campaign_ids'],['1','2']);self.assertEqual(record['sealed_manifest_digest'],'original-seal')
  self.assertEqual(record['creative_copy_policy_resolution']['authority_message_id'],'1568722979569930414')
 def test_native_deep_copy_without_explicit_slots_fails_closed(self):
  from dataclasses import replace
  from ares_campaign_v3.schema import Manifest
  m=self.module();c=Manifest.from_dict(self.state['manifest']).campaigns[0]
  with self.assertRaises(ValueError):m.resolve_campaign(replace(c,ads=()))
 def test_new_creation_not_transformed(self):
  from dataclasses import replace
  from ares_campaign_v3.schema import Manifest
  m=self.module();c=Manifest.from_dict(self.state['manifest']).campaigns[0];zero=replace(c,mode='from_zero_prestaged')
  self.assertIs(m.resolve_campaign(zero),zero)
 def test_readback_cardinality_and_features_are_required(self):
  from ares_campaign_v3.schema import Manifest
  from ares_campaign_v3.planning import Planner
  m=self.module();b=next(iter(Planner().build(Manifest.from_dict(self.state['manifest'])).lanes.values()))[0]
  rows=[]
  for i,c in enumerate(b.campaigns,1):
   ads=[{'name':a.name,'source_ad_id':a.source_ad_id,'creative':copy.deepcopy(a.creative_payload)} for a in c.ads]
   rows.append({'name':'readback_ads_'+str(i),'code':200,'body':{'data':ads}})
  m.verify_record(b,{'readback_results':rows})
  rows[0]['body']['data'].pop()
  with self.assertRaises(ValueError):m.verify_record(b,{'readback_results':rows})
if __name__=='__main__':unittest.main()
