import importlib.util,sys,json,tempfile,unittest,copy,argparse
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-mavroa-cpr-roi-20261121.py')
s=importlib.util.spec_from_file_location('subject14',P);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
MAN=m.load(m.ROOT/'manifest.json');Z=m.ZoneInfo(MAN['timezone_name']);AT=datetime.fromisoformat('2026-11-21T15:00:00-05:00');MAN['campaigns']=[];MAN['edit_cutoff']=AT.isoformat();MAN['request_time']=AT.isoformat();MAN['edits_frozen']=False;MAN['discover_future_edits']=True;MAN['dynamic_discovery']['future_changes']=True
def camp(cid='1',dt='2026-11-21T14:45:00-05:00',aid=m.AID):return {'id':cid,'account_id':aid,'name':cid.zfill(3)+' - test','created_time':dt,'status':'ACTIVE'}
def ev(kind='update_campaign_budget',oid='1',typ='CAMPAIGN_GROUP',extra=None,actor='2'):
 return {'object_id':oid,'object_type':typ,'event_time':AT.isoformat(),'event_type':kind,'actor_id':actor,'extra_data':json.dumps(extra if extra is not None else {'old_value':1,'new_value':2})}
class FakeRunner:
 def __init__(self,root,cs=None,events=None):self.root=root;self.cs=cs or [];self.events=events or [];self.calls=[];self.meta=self;self.token='fixture';self.ins=[];self.sets=[]
 def source(self,run,name,fn):
  if name=='account':v=m.load(m.ROOT/'live-account.json')
  elif name=='activities':v={'events':self.events,'pages':[{'has_next':False}]}
  else:v=fn()
  m.save(run/(name+'.json'),v);m.save(run/(name+'-observed-at.json'),{'observed_at':AT.isoformat()});return v
 def graph(self,*a):raise AssertionError('Unexpected direct API')
 def paged(self,path,params):
  self.calls.append((path,params))
  if path.endswith('/campaigns'):return self.cs
  if path.endswith('/adsets'):return self.sets
  if path.endswith('/insights'):return self.ins
  raise AssertionError(path)
 def graph_batch_get(self,token,queries):
  self.calls.append(('batch',queries));return (200,[{'code':200,'body':json.dumps({'id':q['path'],'account_id':m.AID,'campaign_id':'1'})} for q in queries],{})
 def sbquery(self,*args):return []
class Tests(unittest.TestCase):
 def test_live_timezone(self):
  x=copy.deepcopy(MAN);x['timezone_name']='America/Los_Angeles';self.assertFalse(m.applicable(x,datetime.fromisoformat('2026-11-21T00:01:00+00:00')))
 def test_expiration_without_api(self):
  a=argparse.Namespace(initial=True,dry_run=False)
  with patch.object(m,'scope',side_effect=AssertionError('API')):self.assertEqual(m.execute(a,datetime.fromisoformat(MAN['expires_at']))['status'],'EXPIRED')
 def test_replay_without_api(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as p:
   r=Path(p);m.save(r/'manifest.json',MAN);m.save(r/'runs/initial/complete.json',{'status':'ALREADY_VERIFIED'})
   with patch.object(m,'ROOT',r),patch.object(m,'scope',side_effect=AssertionError('API')):self.assertEqual(m.execute(argparse.Namespace(initial=True,dry_run=False),AT)['status'],'ALREADY_VERIFIED')
 def test_date_creation(self):
  self.assertTrue(m.candidate(camp(),MAN,AT));self.assertFalse(m.candidate(camp(dt='2026-11-20T23:59:59-05:00'),MAN,AT));self.assertFalse(m.candidate(camp(dt='2026-11-21T15:00:01-05:00'),MAN,AT))
  with self.assertRaises(AssertionError):m.candidate(camp(aid='other'),MAN,AT)
 def test_material_lifecycle(self):
  begin=AT-timedelta(hours=15);end=AT+timedelta(seconds=1)
  self.assertFalse(m.event_material(ev(actor='0'),begin,end))
  for old,new in [(1,17),(17,1),(17,9),(9,1)]:self.assertFalse(m.event_material(ev(kind='update_campaign_run_status',extra={'run_status':{'old_value':old,'new_value':new}}),begin,end))
  self.assertTrue(m.event_material(ev(kind='update_campaign_run_status',extra={'run_status':{'old_value':1,'new_value':15}}),begin,end))
 def test_material_bid(self):
  e=ev(kind='update_ad_set_bid_strategy',extra={'old_value':'COST_CAP','new_value':'COST_CAP','additional_value':{'old_value':85,'new_value':95}})
  self.assertTrue(m.event_material(e,AT-timedelta(seconds=1),AT))
  self.assertFalse(m.event_material(ev(extra={'old_value':None,'new_value':'COST_CAP'}),AT-timedelta(seconds=1),AT))
 def test_exact_action(self):
  self.assertEqual(m.w.metric({'spend':'1','actions':[{'action_type':m.w.ACTION,'value':'2'}]})['cpr'],'0.5');self.assertIsNone(m.w.metric({'spend':'1','actions':[{'action_type':'omni_add_to_wishlist','value':'2'}]})['cpr'])
  self.assertIsNone(m.w.metric({'spend':'1'})['cpr'])
 def test_finance(self):
  self.assertEqual(m.f.roi('20','10'),100);self.assertIsNone(m.f.roi('20','0'));self.assertIsNone(m.f.sum_metric([],'INVESTIMENT'));self.assertEqual(m.f.sum_metric([{'INVESTIMENT':'0'}],'INVESTIMENT'),0)
 def test_duplicates(self):
  row={'CUSTOMER_ID':m.AID,'CAMPAIGN_ID':'1','DATE':MAN['date'],'ADGROUP_ID':'x','INVESTIMENT':'1'}
  with self.assertRaises(m.f.FinancialSourceError):m.f.scoped_evidence([row,row],m.AID,[MAN['date']])
 def test_hierarchy_and_dynamic(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as p:
   r=Path(p);obj=FakeRunner(r,[camp('1',dt='2026-11-20T10:00:00-05:00'),camp('2')],[ev('update_ad_set_bid_strategy','child','CAMPAIGN')]);ac=argparse.Namespace(fetch_activities=lambda *a:None)
   with patch.object(m,'datetime') as dt:
    dt.now.return_value=AT;dt.combine=datetime.combine;dt.min=datetime.min;dt.fromisoformat=datetime.fromisoformat
    members,current,missing=m.discover(obj,MAN,r,ac)
   self.assertEqual(set(members),{'1','2'});self.assertIn('changed_today',members['1']['reasons']);self.assertIn('created_today',members['2']['reasons']);self.assertEqual(missing,[])
 def test_collect_numeric_isolation(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as p:
   r=Path(p);obj=FakeRunner(r);cs={'1':{**camp('1'),'number':'001','reasons':['created_today']},'2':{**camp('2'),'number':'002','reasons':['created_today']}}
   obj.sets=[{'id':cid,'campaign_id':cid,'account_id':m.AID,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}} for cid in cs]
   obj.ins=[{'campaign_id':cid,'date_start':MAN['date'],'date_stop':MAN['date'],'spend':val,'actions':[{'action_type':m.w.ACTION,'value':'1'}]} for cid,val in [('1','NaN'),('2','0.50')]]
   d=argparse.Namespace(Runner=lambda *a:obj)
   with patch.object(m,'discover',return_value=(cs,cs,[])):res=m.collect(d,None,MAN,r,{})
   self.assertIn('1',res['pending']);self.assertIsNone(res['rows']['2']['pending']);self.assertEqual(res['rows']['2']['cpr'],'0.50')
   calls=[(path,params) for path,params in obj.calls if path.endswith('/insights')];self.assertEqual(json.loads(calls[0][1]['filtering'])[0]['value'],['1','2'])
 def test_empty_no_finance(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as p:
   obj=FakeRunner(Path(p));d=argparse.Namespace(Runner=lambda *a:obj)
   with patch.object(m,'discover',return_value=({}, {}, [])):res=m.collect(d,None,MAN,Path(p),{})
   self.assertEqual(res['rows'],{});self.assertEqual(obj.calls,[])
 def test_text_and_transport(self):
  d,delivery,ac=m.helpers();self.assertEqual(delivery.TID,m.TID)
  snap={'observed_at':AT.isoformat(),'sb_at':AT.isoformat(),'delay':{'totalMinutes':0,'currentFillTime':None,'confident':False},'discovery_pending':[],'rows':{'1':{'number':'001','status':'ACTIVE','group':'new','pending':None,'meta_spend':'1','results':'2','cpr':'0.5','roi':'10'}}}
  parts=m.text(snap,MAN);text='\n'.join(parts);self.assertIn('0,50',text);self.assertIn('10,00%',text);self.assertIn('Atraso GAM/SB: n/d',text);self.assertIn('Mavroa',text);self.assertNotIn('Yolokfx',text);self.assertTrue(all(len(s.encode('utf-16-le'))//2<=2000 for s in parts))
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);result=unittest.TextTestRunner(verbosity=1).run(suite);m.save(m.ROOT/'tests.json',{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful()});raise SystemExit(not result.wasSuccessful())
