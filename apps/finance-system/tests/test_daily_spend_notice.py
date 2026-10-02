"""Notification-only regression tests; isolated files, no APIs/Discord/DB writes."""
import base64
import contextlib
import copy
import datetime
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import finance_media_spend_sync as sync
from spend_report import render_report

class DailyNoticeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=pathlib.Path(self.tmp.name);(self.root/'private').mkdir()
  self.state=self.root/'state.json'
  self.source={'schema':'api-first-1','since':'2026-09-01','until':'2026-09-08'}
  self.report={'pass':True,'readback':True,'period':'2026-09','since':'2026-09-01','until':'2026-09-08','changed_sites':16,'source_errors':0,'discovery_errors':[],'api_query_errors':0,'exceptions':[],'missing_accounts':[],'auto_registration':{'created':[],'bound':[]},'backup':{'verified':True,'path':'/fixture/backup','sha256':hashlib.sha256(b'fixture backup').hexdigest()}}
 def invoke(self,flags,report=None,notice_error=False,hour=9):
  r=copy.deepcopy(report or self.report)
  class Clock(datetime.datetime):
   @classmethod
   def now(cls,tz=None):return cls(2026,9,9,hour,3,26,tzinfo=sync.TZ)
  def remote(command,*args,**kwargs):
   if 'base64' in command:return base64.b64encode(b'fixture backup').decode()
   return json.dumps(r)
  with contextlib.ExitStack() as stack:
   for attr,value in [('ROOT',self.root),('STATE',self.state),('LOCK',self.root/'private/sync.lock')]:stack.enter_context(patch.object(sync,attr,value))
   stack.enter_context(patch.object(sync.datetime,'datetime',Clock))
   stack.enter_context(patch.object(sys,'argv',['sync']+flags))
   stack.enter_context(patch.dict(sys.modules,{'mgs_google_workspace_auth':SimpleNamespace(load_env=lambda:None)}))
   collect=stack.enter_context(patch.object(sync,'collect_api_first',return_value=self.source))
   stack.enter_context(patch.object(sync,'ssh',side_effect=remote))
   notice=stack.enter_context(patch.object(sync,'notice',return_value={'message_id':'fixture','channel_id':sync.THREAD,'readback':True},side_effect=RuntimeError('fixture transport failure') if notice_error else None))
   stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
   exit_code=0
   try:sync.main()
   except SystemExit as exc:exit_code=exc.code
   return notice.call_count,collect.call_count,exit_code
 def test_unassigned_mapping_never_marks_day_complete(self):
  r=copy.deepcopy(self.report);r['exceptions']=[{'reason':'ambiguous_mapping','id':'12345','name':'Test account'}];r['unassigned']={'USD':'1.25'}
  self.invoke(['--scheduled'],r)
  state=json.loads(self.state.read_text());self.assertEqual(state['last_status'],'partial');self.assertEqual(state['failure_streak'],0)
 def test_monthly_preflight_is_mandatory_and_fail_closed(self):
  with patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'pass':True,'readback':True,'blocked':[]}))) as p:
   sync.ensure_monthly_configuration('2026-11');self.assertIn('--ensure-period',p.call_args.args[0])
  with patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')):
   with self.assertRaises(RuntimeError):sync.ensure_monthly_configuration('2026-11')
 def test_old_hour_and_other_hours_are_silent(self):
  for hour in [7,8,10]:self.assertEqual(self.invoke(['--scheduled'],hour=hour),(0,0,0))
  self.assertFalse(self.state.exists())
 def test_scheduled_success_without_confirmation_question_is_silent(self):
  self.assertFalse(render_report(self.report)['actionable'])
  self.assertEqual(self.invoke(['--scheduled']),(0,1,0))
  self.assertNotIn('last_notice',json.loads(self.state.read_text()))
 def test_pipeline_date_runs_immediately_at_eight_and_counts_as_daily_execution(self):
  self.assertEqual(self.invoke(['--pipeline-date','2026-09-08'],hour=8),(0,1,0))
  state=json.loads(self.state.read_text())
  self.assertEqual(state['last_until'],'2026-09-08')
  self.assertEqual(state['last_scheduled_day'],'2026-09-09')
 def test_nine_am_fallback_is_noop_after_successful_pipeline_step(self):
  self.invoke(['--pipeline-date','2026-09-08'],hour=8)
  self.assertEqual(self.invoke(['--scheduled'],hour=9),(0,0,0))
 def test_previous_day_same_signature_does_not_force_routine_notice(self):
  self.state.write_text(json.dumps({'last_scheduled_day':'2026-09-08','last_status':'ok','last_notice_signature':render_report(self.report)['signature']}))
  self.assertEqual(self.invoke(['--scheduled']),(0,1,0))
 def test_successful_same_day_does_not_duplicate(self):
  self.invoke(['--scheduled']);self.assertEqual(self.invoke(['--scheduled']),(0,0,0))
 def test_manual_is_silent_unless_requested(self):self.assertEqual(self.invoke([]),(0,1,0))
 def test_manual_notify(self):self.assertEqual(self.invoke(['--notify']),(1,1,0))
 def test_dry_run_is_silent(self):self.assertEqual(self.invoke(['--scheduled','--dry-run','--notify']),(0,1,0));self.assertFalse(self.state.exists())
 def test_partial_retains_attention(self):
  r=copy.deepcopy(self.report);r['api_query_errors']=1
  self.assertTrue(render_report(r)['attention']);self.assertEqual(self.invoke(['--scheduled'],r),(1,1,0));self.assertEqual(json.loads(self.state.read_text())['last_status'],'partial')
 def test_delivery_failure_not_recorded_as_success(self):
  r=copy.deepcopy(self.report);r['api_query_errors']=1
  self.assertEqual(self.invoke(['--scheduled'],r,notice_error=True),(2,1,1))
  s=json.loads(self.state.read_text());self.assertEqual(s['last_status'],'failed');self.assertNotIn('last_notice',s)
 def test_compact_success_retains_unavailable_not_zero(self):
  r=copy.deepcopy(self.report);r['api_unavailable']=[{'spend_status':'unavailable_status'}]
  n=render_report(r);self.assertLess(len(n['body']),700);self.assertIn('08/09/2026',n['body']);self.assertIn('16 sites',n['body']);self.assertIn('não foram tratadas como zero',n['body']);self.assertFalse(n['attention'])
 def test_no_changes_is_not_claimed_as_updated_sites(self):
  r=copy.deepcopy(self.report);r['changed_sites']=0;self.assertIn('nenhuma alteração necessária',render_report(r)['body'])
 def test_success_transport_is_unmentioned(self):
  with patch.object(sync,'verify_notice',return_value={'readback':True}),patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='message_id=123456789')) as send:
   sync.notice(self.report);payload=json.loads(send.call_args.kwargs['input']);self.assertIn('Gastos',payload['content']);self.assertEqual(payload['embeds'],[]);self.assertNotIn('<@',payload['content']);self.assertEqual(payload['allowed_mentions']['parse'],[]);self.assertTrue(payload['enforce_nonce']);self.assertIn(sync.THREAD,send.call_args.args[0])
 def test_failure_transport_preserves_alert(self):
  with patch.object(sync,'verify_notice',return_value={'readback':True}),patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='message_id=123456789')) as send:
   sync.notice({'pass':False,'step':'source_collection','error':'FixtureError'});payload=json.loads(send.call_args.kwargs['input']);self.assertTrue(payload['content'].startswith('<@344196393512075265>'));self.assertIn('não foi concluída',payload['content']);self.assertEqual(payload['embeds'],[])

class CombinedCompletionTests(unittest.TestCase):
 def setUp(self):
  import finance_gam_revenue_sync as gam
  self.gam=gam;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  self.result={'pass':True,'date':'2026-09-26','cutoff':'2026-09-26','status':'applied','blockers':[],'verify':{'pass':True},'source_bundle_sha256':'fixture-bundle'}
  self.spend={'pass':True,'readback':True,'period':'2026-09','until':'2026-09-26','exceptions':[],'source_errors':0}
  self.state={'last_status':'ok','last_applied_date':'2026-09-26','last_result':str(self.root/'result.json'),'last_plan':str(self.root/'plan.json')}
  self.ss={'last_status':'ok','last_until':'2026-09-26','last_report_path':str(self.root/'spend.json')}
  self.contract={'thread_id':sync.THREAD}
 def invoke(self,fail=False,twice=False):
  for name,obj in [('result.json',self.result),('spend.json',self.spend),('plan.json',{}),('ss.json',self.ss)]: (self.root/name).write_text(json.dumps(obj))
  with patch.object(self.gam,'STATE',self.root/'state.json'),patch.object(self.gam,'MEDIA_SPEND_STATE',self.root/'ss.json'),patch.object(self.gam,'remote_phase',return_value={'pass':True,'cutoff':'2026-09-26'}) as remote,patch.object(self.gam,'notice',return_value={'readback':True,'message_id':'fixture'},side_effect=RuntimeError('transport') if fail else None) as notice:
   with contextlib.redirect_stdout(io.StringIO()):
    self.gam.deliver_completion(self.contract,self.state)
    if twice:self.gam.deliver_completion(self.contract,self.state)
   return notice,remote
 def test_combined_success_exact_date_once(self):
  notice,remote=self.invoke(twice=True);self.assertEqual(notice.call_count,1);self.assertEqual(remote.call_count,1)
  self.assertIn('26/09/2026',notice.call_args.args[2]);self.assertIn('gastos',notice.call_args.args[2]);self.assertIn('receitas',notice.call_args.args[2]);self.assertFalse(notice.call_args.kwargs['attention']);self.assertEqual(self.state['last_completion_date'],'2026-09-26')
 def test_partial_revenue_never_claims_completion(self):
  self.result['blockers']=[{'type':'unknown_domain'}];self.assertEqual(self.invoke()[0].call_count,0)
 def test_partial_spend_never_claims_completion(self):
  self.ss['last_status']='partial';self.assertEqual(self.invoke()[0].call_count,0)
 def test_spend_exceptions_block_all_filled_claim(self):
  self.spend['exceptions']=[{'id':'a','name':'Conta','reason':'missing_mapping'}];self.assertEqual(self.invoke()[0].call_count,0)
 def test_spend_without_readback_never_claims_completion(self):
  self.spend['readback']=False;self.assertEqual(self.invoke()[0].call_count,0)
 def test_delivery_failure_retains_financial_success_and_retries(self):
  self.invoke(fail=True);self.assertEqual(self.state['last_status'],'ok');self.assertTrue(self.state['completion_notice_pending']);self.assertNotIn('last_completion_signature',self.state)
  self.assertEqual(self.invoke()[0].call_count,1);self.assertFalse(self.state['completion_notice_pending'])
 def test_same_day_skip_retries_notice_without_any_import(self):
  self.invoke(fail=True)
  class Clock(datetime.datetime):
   @classmethod
   def now(cls,tz=None):return cls(2026,9,27,8,18,tzinfo=self.gam.TZ)
  (self.root/'contract.json').write_text(json.dumps({**self.contract,'poll_minutes':[3,8,18,28]}))
  with patch.object(self.gam,'CONTRACT',self.root/'contract.json'),patch.object(self.gam,'STATE',self.root/'state.json'),patch.object(self.gam,'RUNS',self.root/'runs'),patch.object(self.gam,'LOCK',self.root/'lock'),patch.object(self.gam.dt,'datetime',Clock),patch.object(sys,'argv',['sync','--scheduled-intake']),patch.object(self.gam,'deliver_completion') as delivery,patch.object(self.gam,'fetch_candidates') as collect,patch.object(self.gam,'guarded_import') as apply:
   self.assertEqual(self.gam.main(),0);delivery.assert_called_once();collect.assert_not_called();apply.assert_not_called()

if __name__=='__main__':unittest.main()
