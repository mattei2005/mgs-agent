"""Offline tests: exact two approved reviews, no Meta or Discord network."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from ares_campaign_v3 import reviewed_copy_omissions as r
from ares_campaign_v3.creative_copy_policy import effective,verify_creative
from ares_campaign_v3.shein_continuation import content_digest
ROOT=Path('/root/mgs-agent/data/ares/meta-ads/audit/shein')
class ReviewedCopyOmissionsTests(unittest.TestCase):
 def fixture(self,approval='1568735094816903181'):
  d=ROOT/('reviewed-omissions-'+approval)
  return [json.loads((d/(n+'.json')).read_text()) for n in ['receipt','state.before','checkpoint.before','messages']]
 def get(self,messages):
  def fake(path):
   if '/messages?' in path:return [m for m in messages.values() if (m.get('author') or {}).get('bot')]
   return messages[path.rsplit('/',1)[-1]]
  return fake
 def test_both_independent_bindings_validate_and_scope_counts(self):
  for mid,n in [('1568735094816903181',6),('1568734975329697994',5)]:
   receipt,s,cp,msgs=self.fixture(mid);proof=r.validate(receipt,s,cp,get_message=self.get(msgs))
   self.assertTrue(proof['verified']);self.assertEqual(len(receipt['binding']['slots']),10);self.assertEqual(len(receipt['accepted_omissions']),n)
 def context(self):
  receipt,s,cp,msgs=self.fixture();proof=r.validate(receipt,s,cp,get_message=self.get(msgs));return receipt,s,proof
 def payload(self,receipt,s):
  slot=receipt['binding']['slots'][0];c=next(c for c in s['manifest']['campaigns'] if c['idempotency_key']==slot['key']);e=effective(next(a['creative_payload'] for a in c['ads'] if a['source_ad_id']==slot['source_ad_id']))
  actual=copy.deepcopy(e);actual['id']=slot['creative_id']
  for k in receipt['accepted_omissions']:actual['degrees_of_freedom_spec']['creative_features_spec'].pop(k)
  return e,actual
 def test_only_accepted_absence_passes_original_payload_unchanged(self):
  receipt,s,proof=self.context();e,a=self.payload(receipt,s);before=copy.deepcopy(e);marker=r.CURRENT.set(proof)
  try:verify_creative(a,e);self.assertEqual(e,before)
  finally:r.CURRENT.reset(marker)
 def test_default_remains_strict(self):
  receipt,s,proof=self.context();e,a=self.payload(receipt,s)
  with self.assertRaises(ValueError):verify_creative(a,e)
 def test_explicit_out_other_omission_and_new_enabled_rejected(self):
  receipt,s,proof=self.context();e,a=self.payload(receipt,s);marker=r.CURRENT.set(proof)
  try:
   for kind in ['explicit_out','extra_missing','new_in','subset']:
    bad=copy.deepcopy(a);f=bad['degrees_of_freedom_spec']['creative_features_spec']
    if kind=='explicit_out':f[receipt['accepted_omissions'][0]]={'enroll_status':'OPT_OUT'}
    elif kind=='extra_missing':f.pop('enhance_cta')
    elif kind=='new_in':f['unapproved_feature']={'enroll_status':'OPT_IN'}
    else:f[receipt['accepted_omissions'][0]]={'enroll_status':'OPT_IN'}
    with self.subTest(kind=kind),self.assertRaises(ValueError):verify_creative(bad,e)
  finally:r.CURRENT.reset(marker)
 def test_all_original_features_returning_is_accepted(self):
  receipt,s,proof=self.context();e,a=self.payload(receipt,s)
  a['degrees_of_freedom_spec']=copy.deepcopy(e['degrees_of_freedom_spec']);marker=r.CURRENT.set(proof)
  try:verify_creative(a,e)
  finally:r.CURRENT.reset(marker)
 def test_wrong_creative_payload_and_receipt_changes_rejected(self):
  receipt,s,proof=self.context();e,a=self.payload(receipt,s);marker=r.CURRENT.set(proof)
  try:
   wrong=copy.deepcopy(a);wrong['id']='foreign'
   with self.assertRaises(ValueError):verify_creative(wrong,e)
   changed=copy.deepcopy(e);changed['url_tags']='wrong'
   with self.assertRaises(ValueError):verify_creative(a,changed)
   proof['receipt']['accepted_omissions'].append('extra')
   with self.assertRaises(ValueError):verify_creative(a,e)
  finally:r.CURRENT.reset(marker)
 def test_request_source_clock_seals_and_ids_are_bound(self):
  receipt,s,cp,msgs=self.fixture()
  for field in ['request','source','execution_started_at','manifest','target_manifest']:
   changed=copy.deepcopy(s);changed[field]='changed'
   with self.subTest(field=field),self.assertRaises((ValueError,TypeError)):r.validate(receipt,changed,cp,get_message=self.get(msgs))
  changed=copy.deepcopy(cp);changed['bundles'][0]['readback_results'][-1]['body']={}
  with self.assertRaises((ValueError,KeyError)):r.validate(receipt,s,changed,get_message=self.get(msgs))
 def test_dialogue_identity_content_and_history_are_bound(self):
  receipt,s,cp,msgs=self.fixture()
  for field,val in [('content','não'),('edited_timestamp','now'),('channel_id','wrong')]:
   changed=copy.deepcopy(msgs);changed[receipt['approval_id']][field]=val
   with self.subTest(field=field),self.assertRaises(ValueError):r.validate(receipt,s,cp,get_message=self.get(changed))
  base=self.get(msgs)
  def intervening(path):
   if '/messages?' in path:return [msgs[receipt['prompt_id']],{'id':str(int(receipt['prompt_id'])+1),'author':{'id':'human','bot':False}}]
   return base(path)
  with self.assertRaises(ValueError):r.validate(receipt,s,cp,get_message=intervening)
 def test_grant_not_transferable_to_other_account_or_request(self):
  receipt,s,cp,msgs=self.fixture();changed=copy.deepcopy(receipt);changed['binding']['account_id']='foreign'
  with self.assertRaises(ValueError):r.validate(changed,s,cp,get_message=self.get(msgs))
  changed=copy.deepcopy(s);changed['request']['request_id']='another-request'
  with self.assertRaises(ValueError):r.validate(receipt,changed,cp,get_message=self.get(msgs))
if __name__=='__main__':unittest.main()
