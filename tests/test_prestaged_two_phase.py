import sys,unittest,copy
from pathlib import Path
from types import SimpleNamespace as S
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3.prestaged_two_phase import rejected_slots,materialize

class TwoPhaseTests(unittest.TestCase):
 def test_only_exact_rejection_selects_slot(self):
  r={'error':{'detail':{'children':[{'name':'recovery_ad_copy_1_2','error':{'code':100,'error_subcode':1443048}},{'name':'ad_copy_2_1','error':{'code':2}}]}}}
  self.assertEqual(rejected_slots(r),{'1.2'})
 def test_materialize_journals_and_reuses_existing_layers(self):
  payload={'name':'Wanted','object_story_spec':{'page_id':'3','video_data':{'video_id':'4','message':'literal'}},'url_tags':''};ad=S(source_ad_id='9',name='AD 02',creative_payload=payload)
  class Engine:
   def __init__(self):self.calls=[]
   def _batch(self,b,t,ops,stage):
    self.calls.append((stage,ops));rows=[]
    for o in ops:
     if o.name.startswith('fallback_ad_verify'):body={'id':'8','account_id':'1','adset_id':'6','source_ad_id':'9','name':'AD 02','status':'PAUSED','creative':{'id':'7'}}
     elif o.name.startswith('fallback_read'):body={'id':'7','account_id':'1',**copy.deepcopy(payload)}
     elif o.name.startswith('prestaged_fallback_creative'):body={'id':'7'}
     elif o.name.startswith('recovery_ad_copy'):body={'copied_ad_id':'8'}
     else:body={'success':True}
     rows.append(S(name=o.name,body=body,code=200))
    return rows
  e=Engine();rec={};result=materialize(e,S(account_id='1'),None,rec,[(1,2,ad,'6',None)])
  self.assertEqual(result,{(1,2):'8'});self.assertEqual(len(e.calls),4)
  copyop=[x for x in e.calls[0][1] if x.name.startswith('recovery_ad_copy')][0]
  self.assertNotIn('creative_parameters',copyop.body)
  rec={'confirmed_objects':{'prestaged_fallback_creative_1_2':{'id':'7'}}};e=Engine()
  result=materialize(e,S(account_id='1'),None,rec,[(1,2,ad,'6',{'id':'8'})])
  self.assertEqual(result,{(1,2):'8'});self.assertEqual(len(e.calls),3)
  self.assertTrue(all(o.method=='GET' or o.relative_url=='8' for _,ops in e.calls for o in ops))

if __name__=='__main__':unittest.main()
