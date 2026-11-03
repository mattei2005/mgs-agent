import unittest,importlib.util,sys,tempfile,json
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
from unittest.mock import patch
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-cpr-watch-20261103.py')
s=importlib.util.spec_from_file_location('today_watch',P);a=importlib.util.module_from_spec(s);s.loader.exec_module(a);w=a.w
class Tests(unittest.TestCase):
 def c(self,cid='1',day='2026-11-03',status='ACTIVE'):
  return {'id':cid,'account_id':w.AID,'name':cid+' - product','created_time':'2026-11-02T18:00:00-05:00','start_time':day+'T00:00:00-05:00','status':status}
 def s(self,cid='1',day='2026-11-03',event='ADD_TO_WISHLIST'):
  return {'id':'s'+cid,'campaign_id':cid,'account_id':w.AID,'start_time':day+'T20:00:00-05:00','optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':event}}
 def row(self,spend='3',n='2'):
  return w.metric({'spend':spend,'actions':[{'action_type':w.ACTION,'value':n}]})
 def test_equal(self):self.assertEqual(w.decisions({'1':self.row()},{},a.THRESHOLD)[0],[])
 def test_fractional(self):self.assertEqual(w.decisions({'1':self.row('3.00001')},{},a.THRESHOLD)[0],['1']);self.assertGreater(float(a.fmt('1.500005',True).replace(',','.')),1.5)
 def test_zero(self):self.assertIsNone(self.row('5','0')['cpr'])
 def test_absent(self):self.assertIsNone(w.metric({'spend':'5'})['cpr'])
 def test_alias(self):self.assertIsNone(w.metric({'spend':'5','actions':[{'action_type':'omni_add_to_wishlist','value':'2'}]})['cpr'])
 def test_rearm(self):
  high=self.row('4');self.assertEqual(w.decisions({'1':high},{'1':True},a.THRESHOLD)[0],[])
  _,st=w.decisions({'1':self.row()},{'1':True},a.THRESHOLD);self.assertEqual(w.decisions({'1':high},st,a.THRESHOLD)[0],['1'])
 def test_preserve(self):self.assertEqual(w.decisions({'1':{'cpr':None}},{'1':True},a.THRESHOLD)[1],{'1':True})
 def test_cost_mismatch(self):
  with self.assertRaises(AssertionError):w.metric({'spend':'4','actions':[{'action_type':w.ACTION,'value':'2'}],'cost_per_action_type':[{'action_type':w.ACTION,'value':'4'}]})
 def test_previous_creation_future_start(self):self.assertEqual(len(a.discover([self.c()],[self.s()],{})[1]),1)
 def test_paused_included(self):self.assertEqual(len(a.discover([self.c(status='PAUSED')],[self.s()],{})[1]),1)
 def test_prior_and_next_day(self):
  for day in ['2026-11-02','2026-11-04']:self.assertEqual(a.discover([self.c(day=day)],[self.s(day=day)],{})[1],{})
 def test_wrong_account(self):
  c=self.c();c['account_id']='0'
  with self.assertRaises(AssertionError):a.discover([c],[self.s()],{})
 def test_idempotent(self):
  cs,v,p=a.discover([self.c()],[self.s()],{});self.assertEqual(a.discover([self.c()],[self.s()],cs)[0],cs)
 def test_unknown_start_pending(self):
  c=self.c();c.pop('start_time');c['created_time']='2026-11-03T10:00:00-05:00'
  cs,v,p=a.discover([c],[],{});self.assertEqual(set(cs),{'1'});self.assertFalse(v);self.assertEqual(len(p),1)
 def test_pending_recovers(self):
  cs,v,p=a.discover([self.c()],[],{});self.assertEqual(len(p),1);self.assertFalse(v);self.assertEqual(len(a.discover([self.c()],[self.s()],cs)[1]),1)
 def test_existing_loses_event_isolated(self):
  existing={'1':self.c()};cs,v,p=a.discover([self.c(),self.c('2')],[self.s(event='PURCHASE'),self.s('2')],existing)
  self.assertEqual(set(v),{'2'});self.assertEqual(p[0]['id'],'1')
 def test_earliest_start(self):
  self.assertEqual(a.discover([self.c()],[self.s(),self.s(day='2026-11-02')],{})[1],{})
 def test_expired_before_api(self):
  m={'date':'2026-11-02','expires_at':'2026-11-03T00:00:00-05:00'}
  with patch.object(w,'load',return_value=m),patch.object(w,'helpers',side_effect=AssertionError('API called')):
   self.assertEqual(w.execute(SimpleNamespace(initial=False,dry_run=False))['status'],'EXPIRED')
 def test_empty_no_insights(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   run=Path(tmp)/'dry-test';run.mkdir();m=w.load(w.ROOT/'manifest.json');m['campaigns']=[]
   class Runner:
    def __init__(self,*args):pass
    def source(self,p,name,fn):
     result=fn();w.save(p/(name+'-observed-at.json'),{'observed_at':'2026-11-03T11:00:00-05:00'});return result
    def graph(self,path,p):return {'id':w.AID,'name':m['account_name'],'currency':'USD','timezone_name':'America/New_York'}
    def paged(self,path,p):
     if path.endswith('/insights'):raise AssertionError('empty Insights query')
     return []
   snap=a.collect(SimpleNamespace(Runner=Runner),m,run,{})
   self.assertEqual(snap['rows'],{})
 def test_replay_before_api(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   root=Path(tmp);m=w.load(w.ROOT/'manifest.json');w.save(root/'manifest.json',m);w.save(root/'runs/initial/complete.json',{'status':'COMPLETE'})
   with patch.object(w,'ROOT',root),patch.object(w,'scope',side_effect=AssertionError('API called')):self.assertEqual(w.execute(SimpleNamespace(initial=True,dry_run=False)),{'status':'COMPLETE'})
 def test_destination_labels_and_splits(self):
  d,delivery=w.helpers();self.assertEqual(delivery.TID,w.TID)
  rows={str(i):{'number':str(i),'cpr':'1.500005','spend':'3.00001','results':'2'} for i in range(150)}
  text=a.text({'rows':rows,'observed_at':'2026-11-03T11:00:00-05:00'},list(rows));self.assertIn('03/11',text);self.assertIn('1,500',text);self.assertIn('1,50 — Yolokfx',text)
  parts=w.split_parts([text]);self.assertGreater(len(parts),1);self.assertTrue(all(len(p.encode('utf-16-le'))//2<=2000 for p in parts))
 def test_delivery_get_and_replay(self):
  d,delivery=w.helpers();store={};calls=[]
  class DC:
   def verify(self,b):assert b[0]['thread_id']==w.TID
   def call(self,method,path,payload=None):
    calls.append(method)
    if method=='POST':store['msg']={'id':'999','content':payload['content'],'channel_id':w.TID,'author':{'id':d.BOT_ID}};return store['msg']
    return store['msg']
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   run=Path(tmp);m=w.load(w.ROOT/'manifest.json')
   with patch.object(d,'Discord',DC):delivery.deliver(d,m,run,['offline test']);delivery.deliver(d,m,run,['offline test'])
  self.assertEqual(calls,['POST','GET','GET'])
if __name__=='__main__':unittest.main(verbosity=1)
