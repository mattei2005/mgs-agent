import importlib.util, sys, unittest, tempfile, json
from pathlib import Path
from datetime import datetime, timedelta
from types import SimpleNamespace
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-mavroa-cpr-updates-20261111.py')
s=importlib.util.spec_from_file_location('new_cpr',P)
assert s is not None and s.loader is not None
n=importlib.util.module_from_spec(s);sys.modules[s.name]=n;s.loader.exec_module(n);b=n.b
M=b.load(n.ROOT/'manifest.json');AT=datetime.fromisoformat('2026-11-11T14:10:00-05:00')
def c(cid='a',created='2026-11-11T14:09:00-05:00',aid=b.AID):return {'id':cid,'name':'052 - product','account_id':aid,'created_time':created,'status':'ACTIVE'}
class Tests(unittest.TestCase):
 def test_future_message_admission(self): self.assertIn('a',b.candidates([c()],AT))
 def test_created_after_cut(self): self.assertEqual(b.candidates([c(created=(AT+timedelta(seconds=1)).isoformat())],AT),{})
 def test_created_at_cut(self): self.assertIn('a',b.candidates([c(created=AT.isoformat())],AT))
 def test_previous_day(self): self.assertEqual(b.candidates([c(created='2026-11-10T23:59:59-05:00')],AT),{})
 def test_next_day(self): self.assertEqual(b.candidates([c(created='2026-11-12T00:00:00-05:00')],AT),{})
 def test_other_account(self):
  with self.assertRaises(AssertionError):b.candidates([c(aid='123')],AT)
 def test_duplicate(self):
  with self.assertRaises(AssertionError):b.candidates([c(),c()],AT)
 def test_zero_members(self): self.assertEqual(b.candidates([],AT),{})
 def test_missing_result(self):self.assertIsNone(b.metric({'spend':'3'})['cpr'])
 def test_zero_result(self):self.assertIsNone(b.metric({'spend':'3','actions':[{'action_type':b.w.ACTION,'value':'0'}]})['cpr'])
 def test_alias(self):self.assertIsNone(b.metric({'spend':'3','actions':[{'action_type':'omni_add_to_wishlist','value':'2'}]})['cpr'])
 def test_decimal(self):self.assertEqual(b.metric({'spend':'3','actions':[{'action_type':b.w.ACTION,'value':'2'}]})['cpr'],'1.5')
 def test_bad_metric(self):
  with self.assertRaises(AssertionError):b.metric({'spend':'3','actions':[{'action_type':b.w.ACTION,'value':'2'}],'cost_per_action_type':[{'action_type':b.w.ACTION,'value':'9'}]})
 def test_periodic_low_visible(self):
  parts=n.text({'observed_at':AT.isoformat(),'rows':{'a':{'number':'052','status':'ACTIVE','pending':None,'spend':'0.01','results':'10','cpr':'0.001'}}});self.assertIn('Campanha 052',''.join(parts));self.assertIn('gasto US$ 0,01',''.join(parts))
 def test_empty_message(self):self.assertIn('Nenhuma campanha criada hoje',''.join(n.text({'observed_at':AT.isoformat(),'rows':{}})))
 def test_pending_message(self):self.assertIn('estrutura pendente',''.join(n.text({'observed_at':AT.isoformat(),'rows':{'a':{'number':'052','pending':'estrutura pendente','status':'ACTIVE'}}})))
 def test_split(self):self.assertTrue(all(len(p.encode('utf-16-le'))//2<=2000 for p in b.w.split_parts(['linha 🎁'*50]*100)))
 def test_destination(self):
  d,transport=n.helpers();self.assertEqual(transport.TID,M['thread_id']);self.assertEqual(transport.USER,M['requester_discord_id'])
 def test_scope_expiry(self):self.assertFalse(b.applicable(M,datetime.fromisoformat(M['expires_at'])))
 def test_replay_and_expiry_full_entry(self):
  oldroot,oldscope=b.ROOT,b.scope
  try:
   with tempfile.TemporaryDirectory() as temp:
    b.ROOT=Path(temp);b.save(b.ROOT/'manifest.json',M)
    def forbidden(*a):raise AssertionError('unexpected API/scope')
    b.scope=forbidden
    b.save(b.ROOT/'runs/initial/complete.json',{'status':'COMPLETE_GET_VERIFIED','marker':'persisted'})
    self.assertEqual(b.execute(SimpleNamespace(initial=True,dry_run=False),AT)['marker'],'persisted')
    self.assertEqual(b.execute(SimpleNamespace(initial=True,dry_run=False),datetime.fromisoformat(M['expires_at']))['api_calls'],0)
  finally:b.ROOT,b.scope=oldroot,oldscope
 def test_collector_empty_no_financial_api(self):
  class Runner:
   def __init__(self,*args):pass
   def graph(self,path,params):return {'id':'act_'+b.AID,'name':M['account_name'],'currency':'USD','timezone_name':M['timezone']}
   def source(self,run,name,fn):
    result=fn();b.save(run/(name+'-observed-at.json'),{'observed_at':AT.isoformat()});return result
   def paged(self,path,params):
    if path.endswith('/campaigns'):return []
    raise AssertionError('empty coorte consulted financial API')
  with tempfile.TemporaryDirectory() as temp:
   snap=b.collect(SimpleNamespace(Runner=Runner),dict(M,campaigns=[]),Path(temp),{});self.assertEqual(snap['rows'],{})
 def test_collector_pending_isolated(self):
  class Runner:
   def __init__(self,*args):pass
   def graph(self,path,params):return {'id':'act_'+b.AID,'name':M['account_name'],'currency':'USD','timezone_name':M['timezone']}
   def source(self,run,name,fn):
    result=fn();b.save(run/(name+'-observed-at.json'),{'observed_at':AT.isoformat()});return result
   def paged(self,path,params):
    if path.endswith('/campaigns'):return [c('a'),c('b')]
    if path.endswith('/adsets'):return [{'id':'s','campaign_id':'a','account_id':b.AID,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}}]
    if path.endswith('/insights'):
     assert json.loads(params['filtering'])[0]['value']==['a'];return [{'campaign_id':'a','date_start':b.DAY,'date_stop':b.DAY,'spend':'2','actions':[{'action_type':b.w.ACTION,'value':'1'}]}]
    raise AssertionError(path)
  with tempfile.TemporaryDirectory() as temp:
   snap=b.collect(SimpleNamespace(Runner=Runner),dict(M,campaigns=[]),Path(temp),{});self.assertEqual(snap['rows']['a']['cpr'],'2');self.assertIsNotNone(snap['rows']['b']['pending'])
if __name__=='__main__':unittest.main(verbosity=1)
