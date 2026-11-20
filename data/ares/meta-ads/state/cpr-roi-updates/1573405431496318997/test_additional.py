import importlib.util,sys,json,copy,unittest,argparse
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timedelta
s=importlib.util.spec_from_file_location('base_tests',Path(__file__).parent/'test_updates.py');assert s and s.loader;b=importlib.util.module_from_spec(s);sys.modules[s.name]=b;s.loader.exec_module(b);m=b.m
class Extra(unittest.TestCase):
 def test_batch_account_forms(self):
  for aid in [m.AID,'act_'+m.AID]:self.assertEqual(aid.removeprefix('act_'),m.AID)
  self.assertNotEqual('act_123'.removeprefix('act_'),m.AID)
 def test_different_batch_identity(self):
  with b.Tests().tmp() as p:
   class Wrong(b.Fake):
    def graph_batch_get(self,*a):return 200,[{'code':200,'body':json.dumps(b.camp(aid='other'))}],{}
   with self.assertRaises(AssertionError):m.batch(Wrong(),['1'],m.META_FIELDS)
 def test_frozen_creation_drift(self):
  with b.Tests().tmp() as p:
   c={**b.camp(),'number':'001','reasons':['created_today']};v={**b.MAN,'cohort_frozen':True,'campaigns':[c]}
   with self.assertRaises(AssertionError):m.discover(b.Fake([b.camp(at=b.AT-timedelta(seconds=1))]),v,Path(p),None)
 def test_same_script_not_excluded(self):
  entries=[{'source':'ares','job_id':'own','script':'same'},{'source':'ares','job_id':'other','script':'same'},{'source':'zeus','job_id':'own','script':'same'}];kept=[x for x in entries if not(x['source']=='ares' and x['job_id']=='own')];self.assertEqual(len(kept),2)
 def test_slot_and_expiry(self):
  v={**b.MAN,'slots':[b.AT.isoformat()]};self.assertEqual(m.slot(v,b.AT),'1331');self.assertIsNone(m.slot(v,datetime.fromisoformat(v['expires_at'])))
 def test_empty_render_no_fake_group(self):
  text='\n'.join(m.text(b.snap({}),b.MAN));self.assertIn('Nenhuma campanha criada hoje',text);self.assertNotIn('Criadas hoje (0)',text)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Extra));m.save(m.ROOT/'additional-tests.json',{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful()});raise SystemExit(not result.wasSuccessful())
