import importlib.util,sys,json,tempfile,unittest,copy,argparse
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-mavroa-cpr-roi-20261120.py')
s=importlib.util.spec_from_file_location('subject20',P);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
AT=datetime.fromisoformat('2026-11-20T13:31:27.328000-05:00')
MAN={'request_id':m.REQUEST,'account_id':m.AID,'thread_id':m.TID,'requester_discord_id':m.USER,'mode':'finite_read_only_periodic_cpr_roi','date':'2026-11-20','timezone_name':'America/New_York','timezone':'America/New_York','currency':'USD','account_name':'Mavroa-US-SHEIN-ES-04-G004','request_time':AT.isoformat(),'edit_cutoff':AT.isoformat(),'expires_at':'2026-11-21T00:00:00-05:00','slots':[],'campaigns':[],'cohort_frozen':False,'dynamic_discovery':{'enabled':False,'future_changes':False,'future_creations':False},'meta_writes':False,'publisher':{'publisherId':'digital-trust_mavroa','name':'mavroa'},'domain':'mavroa.com'}
def camp(cid='1',at=AT,aid=m.AID):return {'id':cid,'name':cid.zfill(3)+' - test','account_id':aid,'created_time':at.isoformat(),'status':'ACTIVE'}
class Fake:
 def __init__(self,cs=None):self.cs=cs or [];self.calls=[];self.meta=self;self.token='fixture';self.sets=[];self.ins=[];self.sb=[]
 def source(self,run,name,fn):
  assert name!='activities'
  v={'id':'act_'+m.AID,'name':MAN['account_name'],'currency':'USD','timezone_name':'America/New_York'} if name=='account' else fn()
  m.save(run/(name+'.json'),v);m.save(run/(name+'-observed-at.json'),{'observed_at':AT.isoformat()});return v
 def paged(self,path,params):
  self.calls.append((path,params));return self.cs if path.endswith('/campaigns') else self.sets if path.endswith('/adsets') else self.ins
 def graph_batch_get(self,token,queries):
  self.calls.append(('batch',queries));cm={c['id']:c for c in self.cs}
  return 200,[{'code':200,'body':json.dumps(cm[q['path']])} if q['path'] in cm else {'code':404,'body':{}} for q in queries],{}
 def sbquery(self,path,payload):return self.sb if path.startswith('/report') else {}
def snap(rows):return {'rows':rows,'observed_at':AT.isoformat(),'sb_at':AT.isoformat(),'delay':{},'discovery_pending':[]}
def row(i):return {'number':str(i).zfill(3),'status':'PAUSED','group':'new','pending':None,'meta_spend':'1','results':'2','cpr':'0.5','roi':'10'}
class Tests(unittest.TestCase):
 def tmp(self):return tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch'))
 def test_cutoff_exact(self):self.assertTrue(m.candidate(camp(),MAN,AT))
 def test_after_request(self):self.assertFalse(m.candidate(camp(at=AT+timedelta(microseconds=1)),MAN,AT))
 def test_other_day(self):self.assertFalse(m.candidate(camp(at=AT-timedelta(days=1)),MAN,AT))
 def test_other_account(self):
  with self.assertRaises(AssertionError):m.candidate(camp(aid='other'),MAN,AT)
 def test_old_edited_excluded_without_activities(self):
  with self.tmp() as p:
   obj=Fake([camp('1',AT-timedelta(days=1)),camp('2')]);members,_,_=m.discover(obj,MAN,Path(p),argparse.Namespace(fetch_activities=lambda *a:(_ for _ in ()).throw(AssertionError('activities'))))
   self.assertEqual(set(members),{'2'});self.assertEqual(members['2']['reasons'],['created_today'])
 def test_fixed_ids_only_batch(self):
  with self.tmp() as p:
   c={**camp(),'number':'001','reasons':['created_today']};v={**MAN,'cohort_frozen':True,'campaigns':[c]};obj=Fake([c,camp('2')]);members,_,_=m.discover(obj,v,Path(p),None)
   self.assertEqual(set(members),{'1'});self.assertEqual(obj.calls[0][0],'batch');self.assertEqual([q['path'] for q in obj.calls[0][1]],['1'])
 def test_fixed_empty_no_api(self):
  obj=Fake();members,_,_=m.discover(obj,{**MAN,'cohort_frozen':True},None,None);self.assertFalse(members);self.assertFalse(obj.calls)
 def test_fixed_missing_preserved(self):
  with self.tmp() as p:
   c={**camp(),'number':'001','reasons':['created_today']};members,current,missing=m.discover(Fake(),{**MAN,'cohort_frozen':True,'campaigns':[c]},Path(p),None)
   self.assertEqual(set(members),{'1'});self.assertFalse(current);self.assertEqual(missing,['1'])
 def test_expiration_without_api(self):
  with self.tmp() as p:
   r=Path(p);m.save(r/'manifest.json',MAN)
   with patch.object(m,'ROOT',r),patch.object(m,'scope',side_effect=AssertionError('API')):self.assertEqual(m.execute(argparse.Namespace(initial=True,dry_run=False),datetime.fromisoformat(MAN['expires_at']))['status'],'EXPIRED')
 def test_replay_without_api(self):
  with self.tmp() as p:
   r=Path(p);m.save(r/'manifest.json',MAN);m.save(r/'runs/initial/complete.json',{'status':'ALREADY_VERIFIED'})
   with patch.object(m,'ROOT',r),patch.object(m,'scope',side_effect=AssertionError('API')):self.assertEqual(m.execute(argparse.Namespace(initial=True,dry_run=False),AT)['status'],'ALREADY_VERIFIED')
 def test_timezone_live(self):
  v={**MAN,'timezone_name':'America/Los_Angeles'};self.assertFalse(m.applicable(v,datetime.fromisoformat('2026-11-20T00:01:00+00:00')))
 def test_exact_action(self):self.assertEqual(m.w.metric({'spend':'1','actions':[{'action_type':m.w.ACTION,'value':'2'}]})['cpr'],'0.5')
 def test_alias_wrong(self):self.assertIsNone(m.w.metric({'spend':'1','actions':[{'action_type':'omni_add_to_wishlist','value':'2'}]})['cpr'])
 def test_zero_results(self):self.assertIsNone(m.w.metric({'spend':'1'})['cpr'])
 def test_roi_sb_not_meta(self):self.assertEqual(m.f.roi('20','10'),100);self.assertIsNone(m.f.roi('20','0'));self.assertEqual(m.f.roi('0','10'),-100)
 def test_missing_finance(self):self.assertIsNone(m.f.sum_metric([],'INVESTIMENT'));self.assertIsNone(m.f.roi(None,'10'));self.assertIsNone(m.f.roi('10',None))
 def test_duplicates(self):
  x={'CUSTOMER_ID':m.AID,'CAMPAIGN_ID':'1','DATE':MAN['date'],'ADGROUP_ID':'x','INVESTIMENT':'1'}
  with self.assertRaises(m.f.FinancialSourceError):m.f.scoped_evidence([x,x],m.AID,[MAN['date']])
 def test_decimal_storage(self):
  with self.tmp() as p:
   path=Path(p)/'decimal.json';v=m.Decimal('0.12345678901234567890123456789');m.save(path,{'x':v});self.assertEqual(m.load(path)['x'],str(v))
 def test_text(self):
  text='\n'.join(m.text(snap({'1':row(1)}),MAN));self.assertIn('0,50',text);self.assertIn('+10,00%',text);self.assertNotIn('alteradas hoje',text);self.assertNotIn('serão incluídas',text)
 def test_pagination(self):
  parts=m.text(snap({str(i):row(i) for i in range(1,300)}),MAN);self.assertTrue(all(len(x.encode('utf-16-le'))//2<=2000 for x in parts));text='\n'.join(parts)
  for i in range(1,300):self.assertEqual(text.count('C'+str(i).zfill(3)+' |'),1)
 def test_delivery_destination(self):
  _,delivery,_=m.helpers();self.assertEqual((delivery.TID,delivery.USER),(m.TID,m.USER))
 def test_numeric_isolation(self):
  with self.tmp() as p:
   r=Path(p);obj=Fake();cs={str(i):{**camp(str(i)),'number':str(i).zfill(3),'reasons':['created_today']} for i in [1,2]}
   obj.sets=[{'id':cid,'campaign_id':cid,'account_id':m.AID,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}} for cid in cs];obj.ins=[{'campaign_id':cid,'date_start':MAN['date'],'date_stop':MAN['date'],'spend':v,'actions':[{'action_type':m.w.ACTION,'value':'1'}]} for cid,v in [('1','NaN'),('2','0.50')]]
   with patch.object(m,'discover',return_value=(cs,cs,[])):s=m.collect(argparse.Namespace(Runner=lambda *a:obj),None,MAN,r,{})
   self.assertIn('1',s['pending']);self.assertEqual(s['rows']['2']['cpr'],'0.50')
 def test_empty_no_global_finance(self):
  with self.tmp() as p:
   obj=Fake()
   with patch.object(m,'discover',return_value=({}, {}, [])):s=m.collect(argparse.Namespace(Runner=lambda *a:obj),None,MAN,Path(p),{})
   self.assertFalse(s['rows']);self.assertFalse(obj.calls)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));m.save(m.ROOT/'tests.json',{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful()});raise SystemExit(not result.wasSuccessful())
