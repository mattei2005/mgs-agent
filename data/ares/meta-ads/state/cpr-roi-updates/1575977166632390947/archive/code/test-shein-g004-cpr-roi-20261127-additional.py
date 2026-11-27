import importlib.util,sys,unittest,json,tempfile
from pathlib import Path
from datetime import datetime,timedelta
from types import SimpleNamespace
H=Path('/root/.hermes/profiles/ares/scripts')
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
n=module('current_runner',H/'shein-g004-cpr-roi-20261127.py');i=module('current_intake',H/'shein-g004-cpr-roi-20261127-intake.py')
class Extra(unittest.TestCase):
 def setUp(self):
  self.start=datetime.fromisoformat(n.DAY+'T00:00:00-05:00');self.end=self.start+timedelta(hours=16)
  self.event={'event_time':(self.start+timedelta(hours=10)).isoformat(),'event_type':'update_campaign_run_status','object_id':'1','actor_id':'2','extra_data':{'run_status':{'old_value':1,'new_value':15}}}
 def test_material_pause(self):self.assertTrue(i.material(self.event,self.start,self.end))
 def test_processing_excluded(self):self.event['extra_data']['run_status']['new_value']=17;self.assertFalse(i.material(self.event,self.start,self.end))
 def test_actor_zero_excluded(self):self.event['actor_id']='0';self.assertFalse(i.material(self.event,self.start,self.end))
 def test_after_cutoff_excluded(self):self.event['event_time']=(self.end+timedelta(seconds=1)).isoformat();self.assertFalse(i.material(self.event,self.start,self.end))
 def test_cap_changed_strategy_same(self):
  self.event.update(event_type='update_ad_set_bid_strategy',extra_data={'old_value':'COST_CAP','new_value':'COST_CAP','additional_value':{'old_value':90,'new_value':70}});self.assertTrue(i.material(self.event,self.start,self.end))
 def test_stable_cap_excluded(self):
  self.event.update(event_type='update_ad_set_bid_strategy',extra_data={'old_value':'COST_CAP','new_value':'COST_CAP','additional_value':{'old_value':90,'new_value':90}});self.assertFalse(i.material(self.event,self.start,self.end))
 def test_exact_creation_cutoff_included(self):
  c={'id':'1','name':'001 - fixture','account_id':n.AID,'created_time':self.end.isoformat()};self.assertEqual(set(n.candidates([c],self.end)),{'1'})
 def test_adjacent_days_excluded(self):
  for shift in [-1,1]:
   c={'id':'1','name':'001 - fixture','account_id':n.AID,'created_time':(self.end+timedelta(days=shift)).isoformat()};self.assertEqual(n.candidates([c],self.end),{})
 def test_hierarchy_and_new_overlap(self):
  old={'id':'p','account_id':n.AID,'name':'001 - fixture','created_time':(self.start-timedelta(days=1)).isoformat()}
  self.event['event_type']='update_ad_set_run_status';obj={'id':'1','account_id':n.AID,'campaign_id':'p'}
  rows=i.select([self.event],{'1':obj},{'p':old},self.start,self.end);self.assertEqual(rows[0]['id'],'p')
  old['created_time']=self.start.isoformat();self.assertEqual(i.select([self.event],{'1':obj},{'p':old},self.start,self.end),[])
 def test_explicit_false_future_flags(self):
  m=n.load(n.ROOT/'manifest.json');self.assertFalse(m['dynamic_discovery']['enabled']);self.assertFalse(m['discover_future_edits']);self.assertNotEqual(m['antecedent_request_id'],m['request_id'])
 def test_identity_both_forms(self):
  for aid in [n.AID,'act_'+n.AID]:self.assertEqual(aid.removeprefix('act_'),n.AID)
  self.assertNotEqual('act_1'.removeprefix('act_'),n.AID)
 def test_allocator_self_excludes_exact_job_only(self):
  a=module('current_allocator',H/'shein-g004-cpr-roi-20261127-audit.py');rows=[{'scheduler_path':str(n.HOME/'cron/jobs.json'),'job_id':'a'},{'scheduler_path':str(n.HOME/'cron/jobs.json'),'job_id':'b'}];left,removed=a.exclude(rows,'a');self.assertEqual(left,[rows[1]])
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]));n.save(n.ROOT/'additional-tests.json',{'pass':r.wasSuccessful(),'tests_run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'source':str(Path(__file__))});sys.exit(not r.wasSuccessful())
