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
 def test_old_hour_and_other_hours_are_silent(self):
  for hour in [7,8,10]:self.assertEqual(self.invoke(['--scheduled'],hour=hour),(0,0,0))
  self.assertFalse(self.state.exists())
 def test_scheduled_success_without_actionable_change_sends(self):
  self.assertFalse(render_report(self.report)['actionable'])
  self.assertEqual(self.invoke(['--scheduled']),(1,1,0))
  self.assertTrue(json.loads(self.state.read_text())['last_notice']['readback'])
 def test_previous_day_same_signature_does_not_suppress(self):
  self.state.write_text(json.dumps({'last_scheduled_day':'2026-09-08','last_status':'ok','last_notice_signature':render_report(self.report)['signature']}))
  self.assertEqual(self.invoke(['--scheduled']),(1,1,0))
 def test_successful_same_day_does_not_duplicate(self):
  self.invoke(['--scheduled']);self.assertEqual(self.invoke(['--scheduled']),(0,0,0))
 def test_manual_is_silent_unless_requested(self):self.assertEqual(self.invoke([]),(0,1,0))
 def test_manual_notify(self):self.assertEqual(self.invoke(['--notify']),(1,1,0))
 def test_dry_run_is_silent(self):self.assertEqual(self.invoke(['--scheduled','--dry-run','--notify']),(0,1,0));self.assertFalse(self.state.exists())
 def test_partial_retains_attention(self):
  r=copy.deepcopy(self.report);r['api_query_errors']=1
  self.assertTrue(render_report(r)['attention']);self.assertEqual(self.invoke(['--scheduled'],r),(1,1,0));self.assertEqual(json.loads(self.state.read_text())['last_status'],'partial')
 def test_delivery_failure_not_recorded_as_success(self):
  self.assertEqual(self.invoke(['--scheduled'],notice_error=True),(2,1,1))
  s=json.loads(self.state.read_text());self.assertEqual(s['last_status'],'failed');self.assertNotIn('last_notice',s)
 def test_compact_success_retains_unavailable_not_zero(self):
  r=copy.deepcopy(self.report);r['api_unavailable']=[{'spend_status':'unavailable_status'}]
  n=render_report(r);self.assertLess(len(n['body']),700);self.assertIn('08/09/2026',n['body']);self.assertIn('16 sites',n['body']);self.assertIn('não foram tratadas como zero',n['body']);self.assertFalse(n['attention'])
 def test_no_changes_is_not_claimed_as_updated_sites(self):
  r=copy.deepcopy(self.report);r['changed_sites']=0;self.assertIn('nenhuma alteração necessária',render_report(r)['body'])
 def test_success_transport_is_unmentioned(self):
  with patch.object(sync,'verify_notice',return_value={'readback':True}),patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='message_id=123456789')) as send:
   sync.notice(self.report);payload=json.loads(send.call_args.kwargs['input']);self.assertEqual(payload['content'],'');self.assertEqual(payload['allowed_mentions']['parse'],[]);self.assertTrue(payload['enforce_nonce']);self.assertIn(sync.THREAD,send.call_args.args[0])
 def test_failure_transport_preserves_alert(self):
  with patch.object(sync,'verify_notice',return_value={'readback':True}),patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='message_id=123456789')) as send:
   sync.notice({'pass':False,'step':'source_collection','error':'FixtureError'});payload=json.loads(send.call_args.kwargs['input']);self.assertEqual(payload['content'],'<@344196393512075265>');self.assertIn('não foi concluída',payload['embeds'][0]['description'])

if __name__=='__main__':unittest.main()
