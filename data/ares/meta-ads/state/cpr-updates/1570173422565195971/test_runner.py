import importlib.util,sys,unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timedelta
from types import SimpleNamespace as NS
s=importlib.util.spec_from_file_location('new_cpr','/root/.hermes/profiles/ares/scripts/shein-g004-escalatepower-cpr-updates-20261111.py')
assert s is not None and s.loader is not None
n=importlib.util.module_from_spec(s);sys.modules[s.name]=n;s.loader.exec_module(n);b=n.b
M=b.load(b.ROOT/'manifest.json');AT=b.CUTOFF

def campaign(cid='a',created=None,aid=None):return {'id':cid,'name':'005 - Product','number':'005','account_id':aid or b.AID,'created_time':created or AT.isoformat(),'status':'ACTIVE'}

def fixture(missing=False,bad=None):
 class Runner:
  def __init__(self,*a):self.token='fixture';self.meta=self
  def graph(self,path,params):
   assert path=='act_'+b.AID
   return {'id':'act_'+b.AID,'name':M['account_name'],'currency':'USD','timezone_name':M['timezone']}
  def source(self,run,name,fn):
   value=fn();b.save(run/(name+'-observed-at.json'),{'observed_at':AT.isoformat()});return value
  def graph_batch_get(self,token,reqs):
   assert {r['path'] for r in reqs}=={'a','b'}
   return 200,[{'code':200,'body':campaign(r['path'])} for r in reqs],{}
  def paged(self,path,params):
   ids=json.loads(params['filtering'])[0]['value']
   assert path in ['act_'+b.AID+'/adsets','act_'+b.AID+'/insights']
   if path.endswith('/adsets'):
    assert ids==['a','b']
    return [{'id':'s'+cid,'campaign_id':cid,'account_id':b.AID,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}} for cid in ids if not(missing and cid=='b')]
   assert ids==(['a'] if missing else ['a','b'])
   rows=[{'campaign_id':cid,'date_start':b.DAY,'date_stop':b.DAY,'spend':'2','actions':[{'action_type':b.w.ACTION,'value':'2'}]} for cid in ids]
   if bad=='decimal':rows[-1]['spend']='bad'
   if bad=='cpr':rows[-1]['cost_per_action_type']=[{'action_type':b.w.ACTION,'value':'7'}]
   return rows
 return NS(Runner=Runner)

class Tests(unittest.TestCase):
 def test_at_cut(self):self.assertIn('a',b.candidates([campaign()],AT))
 def test_after_cut(self):self.assertEqual(b.candidates([campaign(created=(AT+timedelta(seconds=1)).isoformat())],AT+timedelta(hours=1)),{})
 def test_previous_day(self):self.assertEqual(b.candidates([campaign(created='2026-11-10T23:59:59-05:00')],AT),{})
 def test_next_day(self):self.assertEqual(b.candidates([campaign(created='2026-11-12T00:00:00-05:00')],AT),{})
 def test_other_account(self):
  with self.assertRaises(AssertionError):b.candidates([campaign(aid='123')],AT)
 def test_duplicate(self):
  with self.assertRaises(AssertionError):b.candidates([campaign(),campaign()],AT)
 def test_missing(self):self.assertIsNone(b.metric({'spend':'2'})['cpr'])
 def test_zero(self):self.assertIsNone(b.metric({'spend':'2','actions':[{'action_type':b.w.ACTION,'value':'0'}]})['cpr'])
 def test_alias(self):self.assertIsNone(b.metric({'spend':'2','actions':[{'action_type':'omni_add_to_wishlist','value':'1'}]})['cpr'])
 def test_decimal(self):self.assertEqual(b.metric({'spend':'3','actions':[{'action_type':b.w.ACTION,'value':'2'}]})['cpr'],'1.5')
 def test_low_visible(self):self.assertIn('US$ 0,10/resultado',''.join(n.text({'observed_at':AT.isoformat(),'rows':{'a':{'number':'005','status':'ACTIVE','pending':None,'spend':'1','results':'10','cpr':'0.1'}}})))
 def test_destination(self):
  _,delivery=b.helpers();self.assertEqual(delivery.TID,M['thread_id']);self.assertEqual(delivery.USER,M['requester_discord_id'])
 def test_split(self):self.assertTrue(all(len(p.encode('utf-16-le'))//2<=2000 for p in b.w.split_parts(['linha 🎁'*50]*100)))
 def test_expired(self):self.assertFalse(b.applicable(M,datetime.fromisoformat(M['expires_at'])))
 def test_replay_expiry(self):
  oldroot,oldscope=b.ROOT,b.scope
  try:
   with tempfile.TemporaryDirectory() as temp:
    b.ROOT=Path(temp);b.save(b.ROOT/'manifest.json',M)
    def fail(*a):raise AssertionError('forbidden API')
    b.scope=fail;b.save(b.ROOT/'runs/initial/complete.json',{'marker':'persisted'})
    self.assertEqual(b.execute(NS(initial=True,dry_run=False),AT)['marker'],'persisted')
    self.assertEqual(b.execute(NS(initial=True,dry_run=False),datetime.fromisoformat(M['expires_at']))['api_calls'],0)
  finally:b.ROOT,b.scope=oldroot,oldscope
 def test_empty(self):
  class Runner:
   def __init__(self,*a):pass
   def graph(self,*a):return {'id':'act_'+b.AID,'name':M['account_name'],'currency':'USD','timezone_name':M['timezone']}
   def source(self,run,name,fn):
    val=fn();b.save(run/(name+'-observed-at.json'),{'observed_at':AT.isoformat()});return val
   def paged(self,*a):raise AssertionError('empty API forbidden')
  with tempfile.TemporaryDirectory() as temp:self.assertEqual(n.collect(NS(Runner=Runner),dict(M,campaigns=[]),Path(temp),{})['rows'],{})
 def run_collect(self,**args):
  with tempfile.TemporaryDirectory() as temp:return n.collect(fixture(**args),dict(M,campaigns=[campaign('a'),campaign('b')]),Path(temp),{})
 def test_frozen_exact_paths(self):self.assertEqual(set(self.run_collect()['rows']),{'a','b'})
 def test_pending_recovers(self):
  self.assertIsNotNone(self.run_collect(missing=True)['rows']['b']['pending']);self.assertIsNone(self.run_collect()['rows']['b']['pending'])
 def test_decimal_isolated(self):
  rows=self.run_collect(bad='decimal')['rows'];self.assertEqual(rows['a']['cpr'],'1');self.assertIsNotNone(rows['b']['pending'])
 def test_cpr_isolated(self):
  rows=self.run_collect(bad='cpr')['rows'];self.assertEqual(rows['a']['cpr'],'1');self.assertIsNotNone(rows['b']['pending'])
 def test_timezone(self):self.assertEqual(AT.astimezone(b.NY).strftime('%H:%M'),'15:28');self.assertEqual(M['timezone'],'America/New_York')
if __name__=='__main__':unittest.main()
