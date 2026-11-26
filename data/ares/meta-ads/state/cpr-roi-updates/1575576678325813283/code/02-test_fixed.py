import unittest,tempfile,argparse,copy,json,importlib.util,sys,hashlib
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-mavroa07-cpr-roi-20261126.py');s=importlib.util.spec_from_file_location('test07',P);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
M=m.load(m.ROOT/'fixture-manifest.json');M['cohort_frozen']=True;AT=datetime.fromisoformat(M['request_time']);CID='111';C={'id':CID,'name':'001 - fixture','account_id':m.AID,'created_time':AT.isoformat(),'number':'001','reasons':['created_today'],'status':'PAUSED'}
class Fake:
 def __init__(self):self.calls=[];self.meta=self;self.token='fixture'
 def source(self,run,name,fn):
  v=fn();m.save(run/(name+'.json'),v);m.save(run/(name+'-observed-at.json'),{'observed_at':AT.isoformat()});return v
 def graph_batch_get(self,token,qs):self.calls.append(('batch',qs));return 200,[{'code':200,'body':C} for q in qs],{}
 def graph(self,*args):return {'id':'act_'+m.AID,'name':M['account_name'],'currency':'USD','timezone_name':M['timezone_name']}
 def paged(self,path,params):
  self.calls.append((path,params))
  if path.endswith('/adsets'):return [{'account_id':m.AID,'campaign_id':CID,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}}]
  if path.endswith('/insights'):return [{'campaign_id':CID,'spend':'1','actions':[{'action_type':m.w.ACTION,'value':'2'}],'date_start':M['date'],'date_stop':M['date']}]
  raise AssertionError('Discovery/activities forbidden')
 def sbquery(self,*a):return []
class Tests(unittest.TestCase):
 def tmp(self):return tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch'))
 def test_positive_boundary(self):self.assertTrue(m.candidate(C,M,AT))
 def test_after_cutoff(self):self.assertFalse(m.candidate({**C,'created_time':(AT+timedelta(microseconds=1)).isoformat()},M,AT+timedelta(hours=1)))
 def test_prior_day(self):self.assertFalse(m.candidate({**C,'created_time':(AT-timedelta(days=1)).isoformat()},M,AT))
 def test_next_day(self):self.assertFalse(m.candidate({**C,'created_time':(AT+timedelta(days=1)).isoformat()},M,AT+timedelta(days=1)))
 def test_other_account(self):
  with self.assertRaises(AssertionError):m.candidate({**C,'account_id':'other'},M,AT)
 def test_frozen_only_no_activities(self):
  with self.tmp() as p:
   r=Fake();members,current,missing=m.discover(r,{**M,'campaigns':[C]},Path(p),argparse.Namespace(fetch_activities=lambda *a:(_ for _ in ()).throw(AssertionError('Activities'))));self.assertEqual(set(members),{CID});self.assertEqual(members[CID]['status'],'PAUSED');self.assertEqual([q['path'] for q in r.calls[0][1]],[CID])
 def test_empty_no_calls(self):
  with self.tmp() as p:
   r=Fake();d=argparse.Namespace(Runner=lambda *a:r);res=m.collect(d,None,{**M,'campaigns':[]},Path(p),{});self.assertEqual(res['rows'],{});self.assertEqual(r.calls,[])
 def test_old_edited_not_admitted(self):
  with self.tmp() as p:
   r=Fake();members,_,_=m.discover(r,{**M,'campaigns':[]},Path(p),object());self.assertEqual(members,{});self.assertFalse(r.calls)
 def test_collect_scope_and_finance_absence(self):
  with self.tmp() as p:
   r=Fake();res=m.collect(argparse.Namespace(Runner=lambda *a:r),None,{**M,'campaigns':[C]},Path(p),{});self.assertEqual(res['rows'][CID]['cpr'],'0.5');self.assertIsNone(res['rows'][CID]['roi']);self.assertTrue(all(json.loads(params['filtering'])[0]['value']==[CID] for path,params in r.calls if path.endswith(('/insights','/adsets'))))
 def test_cpr_exact(self):self.assertEqual(m.w.metric({'spend':'1','actions':[{'action_type':m.w.ACTION,'value':'2'}]})['cpr'],'0.5')
 def test_cpr_wrong_alias(self):self.assertIsNone(m.w.metric({'spend':'1','actions':[{'action_type':'omni_add_to_wishlist','value':'2'}]})['cpr'])
 def test_zero_results(self):self.assertIsNone(m.w.metric({'spend':'1','actions':[{'action_type':m.w.ACTION,'value':'0'}]})['cpr'])
 def test_finance_zero_missing(self):self.assertEqual(m.f.roi('0','10'),-100);self.assertIsNone(m.f.roi('10','0'));self.assertIsNone(m.f.roi(None,'10'));self.assertIsNone(m.f.sum_metric([],'INVESTIMENT'))
 def test_duplicate_finance(self):
  row={'CUSTOMER_ID':m.AID,'CAMPAIGN_ID':CID,'DATE':M['date'],'ADGROUP_ID':'x','INVESTIMENT':'1'}
  with self.assertRaises(m.f.FinancialSourceError):m.f.scoped_evidence([row,row],m.AID,[M['date']])
 def test_decimal_storage(self):
  with self.tmp() as p:
   x=m.Decimal('0.1234567890123456789');m.save(Path(p)/'x.json',{'x':x});self.assertEqual(m.load(Path(p)/'x.json')['x'],str(x))
 def test_replay_cli_no_api(self):
  with self.tmp() as p:
   r=Path(p);m.save(r/'manifest.json',M);m.save(r/'runs/initial/complete.json',{'status':'COMPLETE_GET_VERIFIED'})
   with patch.object(m,'ROOT',r),patch.object(m,'scope',side_effect=AssertionError('API')),patch.object(m,'helpers',side_effect=AssertionError('Network')),patch.object(sys,'argv',['runner','--initial']),patch.object(m,'datetime') as dt:
    dt.now.return_value=AT;dt.fromisoformat=datetime.fromisoformat;m.main()
 def test_expiry_cli_no_api(self):
  with self.tmp() as p:
   r=Path(p);m.save(r/'manifest.json',M)
   with patch.object(m,'ROOT',r),patch.object(m,'scope',side_effect=AssertionError('API')),patch.object(m,'helpers',side_effect=AssertionError('Network')),patch.object(sys,'argv',['runner','--initial']),patch.object(m,'datetime') as dt:
    dt.now.return_value=datetime.fromisoformat(M['expires_at']);dt.fromisoformat=datetime.fromisoformat;m.main()
 def test_not_due(self):
  with self.tmp() as p:
   r=Path(p);m.save(r/'manifest.json',M)
   with patch.object(m,'ROOT',r),patch.object(m,'scope',side_effect=AssertionError('API')):self.assertEqual(m.execute(argparse.Namespace(initial=False,dry_run=False),AT)['status'],'NOT_DUE')
 def test_transport_binding(self):self.assertEqual(m.helpers()[1].TID,m.TID)
 def test_pagination_and_selection_text(self):
  rows={str(i):{'number':str(i).zfill(3),'status':'PAUSED','group':'new','pending':None,'meta_spend':'1','results':'1','cpr':'1','roi':'10'} for i in range(1,200)}
  parts=m.text({'rows':rows,'observed_at':AT.isoformat(),'sb_at':AT.isoformat(),'delay':{},'discovery_pending':[]},M);self.assertTrue(all(len(p.encode('utf-16-le'))//2<=2000 for p in parts));text='\n'.join(parts)
  for row in rows.values():self.assertEqual(text.count('C'+row['number']+' |'),1)
  self.assertIn('Conta 07',text);self.assertNotIn('Conta 04',text);self.assertIn('Seleção fixa',text);self.assertNotIn('serão incluídas',text);self.assertNotIn('anteriores alteradas hoje',text)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));qa={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful(),'suite':'fixed_cohort_07','fixtures':['exact_boundary','after_boundary','prior_day','next_day','other_account','frozen_ids_only','no_activities','empty_no_finance','paused_preserved','exact_cpr','alias_rejected','zero_results','finance_zero_missing','duplicate_finance','decimal','cli_replay_no_api','cli_expiry_no_api','transport','utf16_pagination']};m.save(m.ROOT/'tests.json',qa);m.save(m.ROOT/'additional-tests.json',qa);raise SystemExit(not result.wasSuccessful())
