#!/usr/bin/env python3
"""Offline regression for UIA Accounts transient-frame and owned-filter gates."""
import ast,json,re,unittest
from pathlib import Path
from types import SimpleNamespace
class Tests(unittest.TestCase):
 def env(self,frames):
  src=Path(__file__).with_name('read_pc1_accounts_uia.py').read_text();tree=ast.parse(src);fns=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['cap','search','setquery']];calls=[];queue=list(frames)
  def call(x):
   calls.append(x)
   if x['action']=='capture':return queue.pop(0)
   return {'ok':True}
  env={'json':json,'re':re,'Path':Path,'time':SimpleNamespace(sleep=lambda _:None),'bind':{'pid':1,'window_id':2},'T':{'x':{'name':'Approved'},'y':{'name':'Other approved account'}},'a':SimpleNamespace(account_ids=['x']),'call':call}
  exec(compile(ast.Module(body=fns,type_ignores=[]),'worker_functions','exec'),env);return env,calls
 def frame(self,*items):return {'elements':[{'label':'Accounts','role':'Heading'},{'label':'Rodolfo','role':'Button'},*items]}
 def edit(self,index):return {'label':'Search','role':'Edit','index':index}
 def test_transient_frame_waits_without_input(self):
  e,c=self.env([{'elements':[]},self.frame(self.edit(3))]);e['cap']();self.assertEqual(len(c),2);self.assertTrue(all(x['action']=='capture'for x in c))
 def test_wrong_surface_is_bounded(self):
  e,c=self.env([{'elements':[]}for _ in range(4)])
  with self.assertRaisesRegex(AssertionError,'wrong_surface'):e['cap']()
  self.assertEqual(len(c),4)
 def test_gate_stops_immediately(self):
  e,c=self.env([self.frame({'label':'Windows Security','role':'Text'})])
  with self.assertRaisesRegex(AssertionError,'native_or_provider_gate'):e['cap']()
  self.assertEqual(len(c),1)
 def test_known_chip_clear_uses_fresh_search(self):
  e,c=self.env([self.frame({'label':'Clear Name contains Approved','role':'Button','index':4}),self.frame(self.edit(17))]);e['setquery']('Approved');self.assertEqual([x for x in c if x['action']!='capture'],[{'action':'click','element':4},{'action':'set_value','element':17,'value':'Approved'}])
 def test_unknown_chip_never_clicked(self):
  e,c=self.env([self.frame({'label':'Clear Name contains Unknown','role':'Button','index':4})])
  with self.assertRaisesRegex(AssertionError,'unknown_filter_do_not_clear'):e['setquery']('Approved')
  self.assertTrue(all(x['action']=='capture'for x in c))
 def test_other_batch_chip_never_clicked(self):
  e,c=self.env([self.frame({'label':'Clear Name contains Other approved account','role':'Button','index':4})])
  with self.assertRaisesRegex(AssertionError,'unknown_filter_do_not_clear'):e['setquery']('Approved')
  self.assertTrue(all(x['action']=='capture'for x in c))
 def test_multiple_chips_never_clicked(self):
  e,c=self.env([self.frame(*[{'label':'Clear Name contains Approved','role':'Button','index':i}for i in [4,5]])])
  with self.assertRaisesRegex(AssertionError,'unknown_filter_do_not_clear'):e['setquery']('Approved')
  self.assertTrue(all(x['action']=='capture'for x in c))
if __name__=='__main__':unittest.main()
