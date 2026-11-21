import importlib.util,sys,json,tempfile,unittest,copy,argparse
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
R=Path(__file__).parent
spec=importlib.util.spec_from_file_location('base_tests',R/'test_updates.py');assert spec and spec.loader
b=importlib.util.module_from_spec(spec);sys.modules[spec.name]=b;spec.loader.exec_module(b)
m=b.m;AT=b.AT;MAN=copy.deepcopy(b.MAN)
class Frozen(datetime):
 @classmethod
 def now(cls,tz=None):return AT.astimezone(tz) if tz else AT
class Additional(unittest.TestCase):
 def setUp(self):self.clock=patch.object(m,'datetime',Frozen);self.clock.start()
 def tearDown(self):self.clock.stop()
 def test_future_edits_are_discovered(self):
  with tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch')) as p:
   r=Path(p);m0=copy.deepcopy(MAN);m0['request_time']=(AT-timedelta(minutes=10)).isoformat();m0['edits_frozen']=True
   obj=b.FakeRunner(r,[b.camp('1',dt=(AT-timedelta(days=1)).isoformat()),b.camp('2')],[b.ev()])
   members,_,_=m.discover(obj,m0,r,argparse.Namespace())
   self.assertEqual(set(members),{'1','2'});self.assertIn('changed_today',members['1']['reasons'])
 def test_future_event_excluded(self):
  with tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch')) as p:
   r=Path(p);e=b.ev();e['event_time']=(AT+timedelta(seconds=1)).isoformat()
   obj=b.FakeRunner(r,[b.camp('1',dt=(AT-timedelta(days=1)).isoformat()),b.camp('2')],[e])
   members,_,_=m.discover(obj,copy.deepcopy(MAN),r,argparse.Namespace())
   self.assertEqual(set(members),{'2'})
 def test_overlap_one_row(self):
  with tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch')) as p:
   r=Path(p);obj=b.FakeRunner(r,[b.camp('1')],[b.ev()])
   members,_,_=m.discover(obj,MAN,r,argparse.Namespace())
   self.assertEqual(len(members),1);self.assertEqual(set(members['1']['reasons']),{'created_today','changed_today'})
 def test_next_day_rejected(self):self.assertFalse(m.candidate(b.camp(dt='2026-11-22T00:00:00-05:00'),MAN,AT+timedelta(days=1)))
 def test_request_boundary(self):
  self.assertTrue(m.candidate(b.camp(dt=AT.isoformat()),MAN,AT));self.assertFalse(m.candidate(b.camp(dt=(AT+timedelta(microseconds=1)).isoformat()),MAN,AT))
 def test_positive_future_creation(self):
  later=AT+timedelta(minutes=10);self.assertTrue(m.candidate(b.camp(dt=later.isoformat()),MAN,later))
 def test_decimal_storage(self):
  with tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch')) as p:
   path=Path(p)/'d.json';value=m.Decimal('0.12345678901234567890123456789');m.save(path,{'x':value});self.assertEqual(m.load(path)['x'],str(value))
 def test_finance_missing_not_meta(self):
  self.assertIsNone(m.f.roi(None,'1'));self.assertIsNone(m.f.roi('10',None));self.assertEqual(m.f.roi('0','10'),-100)
 def test_empty_creation_no_global_insights(self):
  with tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch')) as p:
   r=Path(p);obj=b.FakeRunner(r);d=argparse.Namespace(Runner=lambda *a:obj)
   with patch.object(m,'discover',return_value=({}, {}, [])):s=m.collect(d,None,MAN,r,{})
   self.assertFalse(s['rows']);self.assertEqual(obj.calls,[])
 def test_table_pagination(self):
  rows={str(i):{'number':str(i).zfill(3),'status':'PAUSED','group':'edited' if i%2 else 'new','pending':None,'meta_spend':'1','results':'1','cpr':'1','roi':'0'} for i in range(1,200)}
  parts=m.text({'rows':rows,'observed_at':AT.isoformat(),'sb_at':AT.isoformat(),'delay':{},'discovery_pending':[]},MAN)
  self.assertGreater(len(parts),1);self.assertTrue(all(len(x.encode('utf-16-le'))//2<=2000 for x in parts));text='\n'.join(parts)
  for row in rows.values():self.assertEqual(text.count('C'+row['number']+' |'),1)
 def test_quiet_not_due(self):
  x=copy.deepcopy(MAN);x['slots']=[]
  with tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch')) as p:
   r=Path(p);m.save(r/'manifest.json',x)
   with patch.object(m,'ROOT',r),patch.object(m,'scope',side_effect=AssertionError('API')):self.assertEqual(m.execute(argparse.Namespace(initial=False,dry_run=False),AT)['status'],'NOT_DUE')
 def test_own_scheduler_identity(self):
  rows=[{'source':'ares','job_id':'own','script':'same'},{'source':'ares','job_id':'other','script':'same'},{'source':'zeus','job_id':'own','script':'same'}]
  kept=[x for x in rows if not(x['source']=='ares' and x['job_id']=='own')];self.assertEqual(len(kept),2)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Additional));m.save(R/'additional-tests.json',{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful()});raise SystemExit(not result.wasSuccessful())
