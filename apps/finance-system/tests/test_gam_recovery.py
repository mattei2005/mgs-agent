"""Synthetic fault injection; no mailbox, database or production writes."""
import pathlib,sys,unittest,subprocess
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from gam_recovery import guarded_import, retry_read, RecoveryBlocked, failure_fields

class RecoveryTests(unittest.TestCase):
 def run_case(self,script):
  calls=[]; events=[]
  def remote(phase,plan):
   calls.append(phase);expected,value=script.pop(0);self.assertEqual(phase,expected)
   if isinstance(value,Exception):raise value
   return value
  result=guarded_import(remote,{},events.append,lambda _:None)
  self.assertFalse(script);return result,calls,events
 def test_normal(self):
  out,calls,events=self.run_case([('apply',{'pass':True}),('verify',{'pass':True})]);self.assertEqual(calls,['apply','verify']);self.assertFalse(events)
 def test_commit_then_transport_loss_only_reads(self):
  out,calls,events=self.run_case([('apply',TimeoutError()),('inspect',{'pass':True,'disposition':'applied','verify':{'pass':True,'audit_id':99}})])
  self.assertEqual(calls.count('apply'),1);self.assertTrue(out['recovered']);self.assertEqual(out['verify']['audit_id'],99);self.assertTrue(events)
 def test_proven_not_applied_can_retry_once(self):
  out,calls,events=self.run_case([('apply',TimeoutError()),('inspect',{'pass':True,'disposition':'not_applied'}),('apply',{'pass':True}),('verify',{'pass':True})]);self.assertEqual(calls.count('apply'),2);self.assertTrue(out['recovered'])
 def test_verification_loss_does_not_reapply(self):
  out,calls,events=self.run_case([('apply',{'pass':True}),('verify',TimeoutError()),('inspect',{'pass':True,'disposition':'applied','verify':{'pass':True}})]);self.assertEqual(calls.count('apply'),1)
 def test_unknown_or_conflicting_write_never_retries(self):
  for disposition in ['unknown','partial','conflict']:
   calls=[]
   def remote(phase,plan):
    calls.append(phase)
    if phase=='apply':raise TimeoutError()
    return {'pass':False,'disposition':disposition}
   with self.assertRaises(RecoveryBlocked):guarded_import(remote,{},lambda _:None,lambda _:None)
   self.assertEqual(calls,['apply','inspect'])
 def test_auth_failure_no_repair_or_write_retry(self):
  calls=[]
  def remote(phase,plan):
   calls.append(phase)
   if phase=='apply':raise RuntimeError('permission denied')
   return {'pass':True,'disposition':'not_applied'}
  with self.assertRaises(RecoveryBlocked):guarded_import(remote,{},lambda _:None,lambda _:None)
  self.assertEqual(calls,['apply','inspect'])
 def test_retry_is_bounded_and_inspected_again(self):
  calls=[]
  def remote(phase,plan):
   calls.append(phase)
   if phase=='apply':raise TimeoutError()
   return {'pass':True,'disposition':'not_applied'}
  with self.assertRaises(RecoveryBlocked):guarded_import(remote,{},lambda _:None,lambda _:None)
  self.assertEqual(calls,['apply','inspect','apply','inspect'])
 def test_first_failure_requires_intervention(self):
  self.assertTrue(failure_fields(1)['intervention_required']);self.assertFalse(failure_fields(1)['blocked_after_five']);self.assertTrue(failure_fields(5)['blocked_after_five'])
 def test_read_retry_and_no_auth_retry(self):
  calls=[];events=[]
  def read():
   calls.append(1)
   if len(calls)==1:raise TimeoutError()
   return 42
  self.assertEqual(retry_read(read,'intake',events.append,lambda _:None),42);self.assertEqual(len(calls),2)
  calls=[]
  def denied():calls.append(1);raise RuntimeError('1Password mailbox lookup failed')
  with self.assertRaises(RuntimeError):retry_read(denied,'intake',events.append,lambda _:None)
  self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main()
