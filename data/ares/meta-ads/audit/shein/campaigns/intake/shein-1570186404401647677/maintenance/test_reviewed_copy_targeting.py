import copy, importlib.util, json, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, '/root/mgs-agent/scripts')
from ares_campaign_v3 import shein_reviewed_targeting as legacy
from ares_campaign_v3.shein_continuation import content_digest
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('ares_campaign_v3.reviewed_copy_targeting', HERE/'reviewed_copy_targeting.py')
m = importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
BASE=Path('/root/mgs-agent/data/ares/meta-ads')
RID='shein-1569025252971774224-c1'
STATE=json.loads((BASE/'state/shein-campaigns/single-clone'/RID/'state.json').read_text())
CHECK=json.loads((BASE/'engine-v3/state/checkpoints'/(RID+'-869857549542755.json')).read_text())

class ReviewTests(unittest.TestCase):
 def setUp(self):
  self.s=copy.deepcopy(STATE);self.c=copy.deepcopy(CHECK)
  self.target=copy.deepcopy(self.s['source']['adset']['targeting']);self.target['user_age_unknown']=True
  del self.target['targeting_automation']['individual_setting']
 def test_known_delta(self):self.assertEqual(len(m.delta(self.s['source']['adset']['targeting'],self.target)),4)
 def test_extra_geo_rejected(self):
  self.target['geo_locations']['countries']=['BR']
  with self.assertRaises(ValueError):m.delta(self.s['source']['adset']['targeting'],self.target)
 def test_unknown_age_false_rejected(self):
  self.target['user_age_unknown']=None
  with self.assertRaises(ValueError):m.delta(self.s['source']['adset']['targeting'],self.target)
 def test_changed_device_not_omission(self):
  self.target['targeting_automation']['individual_setting']={'device':0}
  with self.assertRaises(ValueError):m.delta(self.s['source']['adset']['targeting'],self.target)
 def test_unchanged_target_not_review(self):
  with self.assertRaises(ValueError):m.delta(self.target,self.target)
 def test_real_binding_verified(self):m.require_binding(self.s,self.c,m.binding(self.s,self.c))
 def test_budget_change_rejected(self):
  b=m.binding(self.s,self.c);self.s['manifest']['campaigns'][0]['campaign_updates']['daily_budget']='4600'
  with self.assertRaises(ValueError):m.require_binding(self.s,self.c,b)
 def test_clock_change_rejected(self):
  b=m.binding(self.s,self.c);self.s['execution_started_at']='2030-01-01T00:00:00Z'
  with self.assertRaises(ValueError):m.require_binding(self.s,self.c,b)
 def test_child_change_rejected(self):
  b=m.binding(self.s,self.c);self.c['bundles'][0]['ad_ids'][0]='999'
  with self.assertRaises(ValueError):m.require_binding(self.s,self.c,b)
 def test_source_change_rejected(self):
  b=m.binding(self.s,self.c);self.s['source']['adset']['targeting']['age_min']=21
  with self.assertRaises(ValueError):m.require_binding(self.s,self.c,b)
 def test_partial_creation_rejected(self):
  self.c['bundles'][0]['status']='IN_PROGRESS'
  with self.assertRaises(ValueError):m.binding(self.s,self.c)
 def test_missing_registry_rejected(self):
  with patch.object(m,'POLICY_INDEX',HERE/'nonexistent.json'):
   with self.assertRaises(FileNotFoundError):m.validate_review({},self.s,self.c,get_message=lambda p: {})
 def review_fixture(self):
  bound=m.binding(self.s,self.c)
  aid=self.s['request']['authorized_by']; origin=self.s['request']['source_thread_id']
  prompt='1570187430781255801'; approval='1570236401524547606'; original=self.s['request']['source_message_id']
  messages={mid:{'id':mid,'channel_id':origin,'content':text,'author':{'id':who,'bot':bot}} for mid,text,who,bot in [(original,'original',aid,False),(prompt,'exact targeting question','1508864261504630925',True),(approval,'activate all',aid,False)]}
  receipt={'schema_version':1,'binding':bound,'approved_by':aid,'approval_id':approval,'prompt_id':prompt,'dialogue':[{'id':mid,'digest':m.message_digest(msg)} for mid,msg in messages.items()], 'targeting_by_adset':{s['adset_id']:self.target for s in bound['slots']},'accepted_paths':m.delta(self.s['source']['adset']['targeting'],self.target)}
  descriptor={'reviewed_targeting_kind':m.KIND,'reviewed_targeting':bound,'targeting_review_receipt':receipt,'recovery_review_message_id':approval,'recovery_review_thread_id':origin,'recovery_review_content':'activate all','late_activation_authorized':True}
  history=[messages[prompt],messages[original]]
  def get(path):return copy.deepcopy(history if '?before=' in path else messages[path.rsplit('/',1)[1]])
  index=HERE/'test-policy-index.json'
  def register():index.write_text(json.dumps({'requests':{self.s['request']['request_id']:{'receipt_digest':content_digest(receipt),'approved_by':aid,'approval_id':approval,'account_id':self.c['account_id'],'review_authority':'SHEIN_CHANNEL_POLICY'}}}))
  register();self.addCleanup(index.unlink,missing_ok=True)
  self.enterContext(patch.object(m,'POLICY_INDEX',index))
  self.auth=self.enterContext(patch('ares_campaign_v3.shein_channel_authority.verify',return_value={'verified':True}))
  return receipt,descriptor,messages,history,get,register
 def test_registered_review_live_authority(self):
  r,d,msg,h,get,reg=self.review_fixture();self.assertEqual(m.validate_review(d,self.s,self.c,get_message=get)['kind'],m.KIND);self.assertTrue(self.auth.call_args.kwargs['force'])
 def test_wrong_actor_rejected(self):
  r,d,msg,h,get,reg=self.review_fixture();msg[r['approval_id']]['author']['id']='999'
  with self.assertRaises(ValueError):m.validate_review(d,self.s,self.c,get_message=get)
 def test_edited_message_rejected(self):
  r,d,msg,h,get,reg=self.review_fixture();msg[r['approval_id']]['edited_timestamp']='now'
  with self.assertRaises(ValueError):m.validate_review(d,self.s,self.c,get_message=get)
 def test_intervening_human_rejected(self):
  r,d,msg,h,get,reg=self.review_fixture();h.append({'id':'1570187430781255802','author':{'bot':False}})
  with self.assertRaises(ValueError):m.validate_review(d,self.s,self.c,get_message=get)
 def test_unregistered_receipt_change_rejected(self):
  r,d,msg,h,get,reg=self.review_fixture();r['accepted_paths']=[]
  with self.assertRaises(ValueError):m.validate_review(d,self.s,self.c,get_message=get)
 def test_registered_extra_delta_rejected(self):
  r,d,msg,h,get,reg=self.review_fixture();next(iter(r['targeting_by_adset'].values()))['age_min']=21;reg()
  with self.assertRaises(ValueError):m.validate_review(d,self.s,self.c,get_message=get)
 def test_missing_slot_rejected(self):
  r,d,msg,h,get,reg=self.review_fixture();r['targeting_by_adset'].pop(next(iter(r['targeting_by_adset'])));reg()
  with self.assertRaises(ValueError):m.validate_review(d,self.s,self.c,get_message=get)
 def test_revoked_authority_rejected(self):
  r,d,msg,h,get,reg=self.review_fixture();self.auth.return_value={'verified':False}
  with self.assertRaises(ValueError):m.validate_review(d,self.s,self.c,get_message=get)
 def test_integration_dispatch(self):
  bound=m.binding(self.s,self.c)
  self.assertEqual(legacy.require_binding(self.s,self.c,bound,kind=m.KIND),bound)
 def test_legacy_unknown_kind_stays_closed(self):
  with self.assertRaises(ValueError):legacy.require_binding(self.s,self.c,{},kind='other-kind')

if __name__=='__main__':unittest.main(verbosity=2)
