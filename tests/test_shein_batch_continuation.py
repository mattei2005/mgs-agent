import copy,unittest
from test_shein_authorized_continuation import ContinuationTests

class BatchContinuationTests(ContinuationTests):
 def batch(self):
  m,d,s,c,g=self.fixture();d['quantity']=s['request']['quantity']=3
  d.pop('existing_campaign_id');d.pop('existing_adset_id')
  d['existing_campaign_ids']=['111','112','113'];d['existing_adset_ids']=['211','212','213']
  c['bundles']=[{'campaign_ids':['111','112'],'adset_ids':['211','212']},{'campaign_ids':['113'],'adset_ids':['213']}]
  targets=[{'idempotency_key':'same-'+str(i),'account_id':'999','status':'ACTIVE'} for i in range(3)]
  s['target_manifest']['campaigns']=copy.deepcopy(targets);s['manifest']['campaigns']=copy.deepcopy(targets)
  return m,d,s,c,g
 def test_exact_multi_bundle_ids_with_original_clock_and_scope(self):
  m,d,s,c,g=self.batch();before=copy.deepcopy(s);p=m.validate_descriptor(d,s,c,get_message=g)
  self.assertEqual(p['campaign_ids'],['111','112','113']);self.assertEqual(s,before)
  marker=m.APPROVED_RESUME.set({'descriptor':d,'state':s,'checkpoint':c,'verified':p})
  try:
   for target in s['target_manifest']['campaigns']:self.assertTrue(m.allows_elapsed_campaign(target))
   self.assertFalse(m.allows_elapsed_campaign({'idempotency_key':'extra','account_id':'999','status':'ACTIVE'}))
  finally:m.APPROVED_RESUME.reset(marker)
 def test_changed_batch_id_order_rejected(self):
  m,d,s,c,g=self.batch();d['existing_campaign_ids'].reverse()
  with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)
 def test_duplicate_or_incomplete_ids_rejected(self):
  for values in [['111','111','113'],['111','112']]:
   m,d,s,c,g=self.batch();d['existing_campaign_ids']=values
   with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)
 def test_quantity_change_rejected(self):
  m,d,s,c,g=self.batch();d['quantity']=2
  with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)

if __name__=='__main__':unittest.main()
