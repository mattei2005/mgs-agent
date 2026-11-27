import importlib.util,sys,unittest,tempfile,json
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
p=Path('/root/.hermes/profiles/ares/scripts/shein-g004-cpr-roi-20261127.py');sp=importlib.util.spec_from_file_location('testtarget',p);n=importlib.util.module_from_spec(sp);sys.modules[sp.name]=n;sp.loader.exec_module(n)
class Tests(unittest.TestCase):
 def setUp(self):self.at=datetime.fromisoformat('2026-11-27T15:00:00-05:00');self.c={'id':'1','account_id':n.AID,'name':'298 - test','created_time':'2026-11-27T14:50:00-0500'}
 def test_future_after_request_admitted(self):self.assertEqual(set(n.candidates([self.c],self.at)),{'1'})
 def test_after_observation_excluded(self):self.c['created_time']='2026-11-27T15:01:00-0500';self.assertFalse(n.candidates([self.c],self.at))
 def test_other_day_excluded(self):self.c['created_time']='2026-11-15T14:00:00-0500';self.assertFalse(n.candidates([self.c],self.at))
 def test_other_account_blocked(self):
  self.c['account_id']='other'
  with self.assertRaises(AssertionError):n.candidates([self.c],self.at)
 def test_duplicates_blocked(self):
  with self.assertRaises(AssertionError):n.candidates([self.c,self.c],self.at)
 def test_cpr_no_results(self):self.assertIsNone(n.core.metric({'spend':'1'})['cpr'])
 def test_alias_not_summed(self):self.assertIsNone(n.core.metric({'spend':'1','actions':[{'action_type':'omni_add_to_wishlist','value':'2'}]})['cpr'])
 def test_cpr_exact(self):self.assertEqual(n.core.metric({'spend':'1','actions':[{'action_type':'offsite_conversion.fb_pixel_add_to_wishlist','value':'2'}]})['cpr'],'0.5')
 def test_finance_zero_denominator(self):self.assertIsNone(n.finance.roi('1','0'))
 def test_finance_missing(self):self.assertIsNone(n.finance.roi(None,'1'))
 def test_finance_valid(self):self.assertEqual(n.finance.roi('15','10'),50)
 def test_finance_sum_empty(self):self.assertIsNone(n.finance.sum_metric([],'NET_REVENUE'))
 def test_finance_explicit_zero(self):self.assertEqual(n.finance.sum_metric([{'NET_REVENUE':'0'}],'NET_REVENUE'),0)
 def test_finance_duplicate(self):
  x={'CUSTOMER_ID':n.AID,'CAMPAIGN_ID':'1','DATE':n.DAY,'ADGROUP_ID':'2'}
  with self.assertRaises(ValueError):n.finance.scoped_evidence([x,x],n.AID,[n.DAY])
 def test_expiration_before_api(self):
  root=n.ROOT;scope=n.scope
  try:
   with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as td:
    n.ROOT=Path(td);n.save(n.ROOT/'manifest.json',{'date':n.DAY,'expires_at':'2026-11-28T00:00:00-05:00'})
    n.scope=lambda m:(_ for _ in ()).throw(AssertionError('unexpected API'))
    self.assertEqual(n.execute(SimpleNamespace(initial=True,dry_run=False),datetime.fromisoformat('2026-11-28T00:00:00-05:00'))['api_calls'],0)
  finally:n.ROOT=root;n.scope=scope
 def test_replay_before_api(self):
  root=n.ROOT;scope=n.scope
  try:
   with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as td:
    n.ROOT=Path(td);n.save(n.ROOT/'manifest.json',{'date':n.DAY,'expires_at':'2026-11-28T00:00:00-05:00'});n.save(n.ROOT/'runs/initial/complete.json',{'status':'COMPLETE_GET_VERIFIED'})
    n.scope=lambda m:(_ for _ in ()).throw(AssertionError('unexpected API'))
    self.assertEqual(n.execute(SimpleNamespace(initial=True,dry_run=False),self.at)['status'],'COMPLETE_GET_VERIFIED')
  finally:n.ROOT=root;n.scope=scope
 def test_delivery_destination(self):
  _,d=n.helpers();self.assertEqual(d.TID,n.TID);self.assertEqual(d.USER,n.USER)
 def test_splitting(self):self.assertTrue(all(len(p.encode('utf-16-le'))//2<=2000 for p in n.core.w.split_parts(['\n'.join(['test'*100]*100)])))
 def test_all_metrics_shown(self):
  snap={'rows':{'1':{'number':'1','cpr':'0.2','roi':'5','results':'5','spend':'1','status':'PAUSED','pending':None}},'observed_at':self.at.isoformat(),'sb_at':self.at.isoformat(),'campaigns':[self.c]}
  txt='\n'.join(n.text(snap));self.assertIn('0,20',txt);self.assertIn('5,00%',txt);self.assertIn('Paus.',txt)
 def test_no_threshold(self):self.assertNotIn('threshold',p.read_text())
 def test_wrapper_forwarding(self):self.assertIn('"$@"',p.with_suffix('.sh').read_text())
 def test_decimal_serialization(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as td:
   q=Path(td)/'model.json';n.save(q,{'value':n.Decimal('1.2')});self.assertEqual(n.load(q)['value'],'1.2')
class CollectorTests(unittest.TestCase):
 def run_collect(self, campaigns, adsets, insights, admitted=None):
  from unittest.mock import patch
  calls=[];stamp='2026-11-27T13:06:00-05:00'
  import json
  class Runner:
   def graph_batch_get(self,token,reqs):
    out=[]
    for req in reqs:
     cid=req['path'];calls.append((cid,req['params']));obj=next((c for c in campaigns if c['id']==cid),None)
     out.append({'code':200,'body':json.dumps(obj)} if obj else {'code':404,'body':{}})
    return 200,out,{}
   def __init__(self,*a):self.meta=self;self.token=None
   def graph(self,path,params):
    calls.append((path,params));return {'id':n.AID,'name':'Yolokfx-US-SHEIN-EN-04-G004','currency':'USD','timezone_name':str(n.NY)}
   def paged(self,path,params):
    calls.append((path,params))
    if path.endswith('/campaigns'):return campaigns
    if path.endswith('/adsets'):return adsets
    if path.endswith('/insights'):return insights
    raise AssertionError('unexpected API path')
   def source(self,run,name,fn):
    v=fn();n.save(run/(name+'-observed-at.json'),{'observed_at':stamp});return v
   def publishers(self):raise RuntimeError('fixture finance unavailable')
   def sbquery(self,*a):raise RuntimeError('fixture unavailable')
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as td:
   snap=n.collect(SimpleNamespace(Runner=Runner),{'account_name':'Yolokfx-US-SHEIN-EN-04-G004','campaigns':admitted if admitted is not None else [{**c,'number':c['name'].split(' - ')[0],'membership_source':'created_today'} for c in campaigns],'edited_campaigns':[c for c in (admitted or []) if c.get('membership_source')=='edited_today'],'request_time':n.DAY+'T23:59:59-05:00','cohort_frozen':True,'dynamic_discovery':{'enabled':False}},Path(td),{})
  return snap,calls
 def campaign(self,cid='1',created='2026-11-27T13:00:00-0500'):
  return {'id':cid,'account_id':n.AID,'created_time':created,'name':cid+' - fixture','status':'ACTIVE'}
 def adset(self,cid='1'):
  return {'id':'a'+cid,'account_id':n.AID,'campaign_id':cid,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}}
 def insight(self,cid='1',spend='1'):
  return {'campaign_id':cid,'date_start':n.DAY,'date_stop':n.DAY,'spend':spend,'actions':[{'action_type':'offsite_conversion.fb_pixel_add_to_wishlist','value':'2'}]}
 def test_old_edited_not_admitted_no_activities(self):
  old=self.campaign('2','2026-11-16T13:00:00-0500');old['updated_time']='2026-11-27T13:02:00-0500'
  snap,calls=self.run_collect([self.campaign(),old],[self.adset()],[self.insight()],admitted=[{**self.campaign(),'number':'1','membership_source':'created_today'}]);self.assertEqual(set(snap['rows']),{'1'});self.assertFalse(any('activities' in p for p,_ in calls))
 def test_empty_cohort_no_empty_filter_queries(self):
  snap,calls=self.run_collect([],[],[]);self.assertFalse(snap['rows']);self.assertFalse(any(p.endswith(('/adsets','/insights')) for p,_ in calls))
 def test_numeric_failure_isolated(self):
  snap,_=self.run_collect([self.campaign(),self.campaign('2')],[self.adset(),self.adset('2')],[self.insight(spend='NaN'),self.insight('2')]);self.assertIn('1',snap['pending']);self.assertEqual(snap['rows']['2']['cpr'],'0.5')
 def test_structure_missing_isolated(self):
  snap,_=self.run_collect([self.campaign(),self.campaign('2')],[self.adset('2')],[self.insight('2')]);self.assertIn('1',snap['pending']);self.assertEqual(snap['rows']['2']['cpr'],'0.5')
 def test_pending_member_recovers(self):
  c=self.campaign();c.update(number='1',membership_source='created_today')
  snap,_=self.run_collect([self.campaign()],[self.adset()],[self.insight()],admitted=[c]);self.assertFalse(snap['pending']);self.assertEqual(len(snap['campaigns']),1)
 def test_event_lost_isolated(self):
  wrong=self.adset();wrong['promoted_object']['custom_event_type']='PURCHASE'
  snap,_=self.run_collect([self.campaign(),self.campaign('2')],[wrong,self.adset('2')],[self.insight('2')]);self.assertIn('1',snap['pending']);self.assertEqual(snap['rows']['2']['cpr'],'0.5')
 def test_date_and_labels(self):
  snap,_=self.run_collect([self.campaign()],[self.adset()],[self.insight()]);text='\n'.join(n.text(snap));self.assertIn('27/11/2026',text);self.assertIn('seleção congelada',text);self.assertNotIn('16/11/2026',text)

class FrozenTests(CollectorTests):
 def test_frozen_ids_only(self):
  c=self.campaign();c.update(number='1',membership_source='created_today')
  snap,calls=self.run_collect([c,self.campaign('2')],[self.adset()],[self.insight()],admitted=[c])
  self.assertEqual(set(snap['rows']),{'1'})
  self.assertFalse(any(p.endswith('/campaigns') for p,_ in calls))
  self.assertFalse(any(p=='2' for p,_ in calls))
  for p,v in calls:
   if p.endswith(('/adsets','/insights')):self.assertEqual(json.loads(v['filtering'])[0]['value'],['1'])
 def test_empty_frozen_no_campaign_queries(self):
  snap,calls=self.run_collect([self.campaign()],[],[],admitted=[])
  self.assertFalse(snap['rows']);self.assertFalse(any(p.endswith(('/campaigns','/adsets','/insights')) or p=='1' for p,_ in calls))
 def test_edit_union_and_paused(self):
  a=self.campaign();a.update(number='1',membership_source='created_today')
  b=self.campaign('2','2026-11-15T13:00:00-0500');b.update(number='2',membership_source='edited_today',status='PAUSED',edit_evidence=[{'event_type':'update_campaign_run_status'}])
  snap,_=self.run_collect([a,b],[self.adset(),self.adset('2')],[self.insight(),self.insight('2')],admitted=[a,b])
  self.assertEqual(set(snap['rows']),{'1','2'});txt='\n'.join(n.text(snap));self.assertIn('Alteradas hoje',txt);self.assertIn('Paus.',txt)
  for num in ['1','2']:self.assertEqual(txt.count('C'+num+' '),1)
 def test_many_rows_utf16(self):
  snap={'rows':{},'campaigns':[],'observed_at':n.DAY+'T15:00:00-05:00','sb_at':None}
  for i in range(1,400):
   cid=str(i);snap['campaigns'].append({'id':cid,'membership_source':'created_today'});snap['rows'][cid]={'id':cid,'number':cid,'status':'ACTIVE','pending':None,'spend':'1','results':'2','cpr':'0.5','roi':None}
  parts=n.text(snap);self.assertTrue(all(len(x.encode('utf-16-le'))//2<=2000 for x in parts))
  import re
  self.assertEqual(len(re.findall(r'^C\d+\s', '\n'.join(parts), re.M)),399)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
 rec={'pass':result.wasSuccessful(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'source':str(Path(__file__))}
 n.save(n.ROOT/'tests.json',rec);print(json.dumps(rec));sys.exit(not result.wasSuccessful())
