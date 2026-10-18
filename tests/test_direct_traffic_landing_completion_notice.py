"""Offline completion-notice tests; no real observations or notifications."""
import json,unittest
import test_direct_traffic_landing_followup as fixtures
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3 import landing_followup_reporting as reporting

class CompletionNoticeTests(unittest.TestCase):
 setUp=fixtures.FollowupTests.setUp
 tearDown=fixtures.FollowupTests.tearDown
 arm=fixtures.FollowupTests.arm
 def config(self):
  return [{'enabled':True,'authority_message_id':'1561391162588401725','thread_id':core.INCIDENT_THREAD,'job_keys':[self.key],'total_links':1}]
 def terminal(self,state='PASSED'):
  with self.q.tx():
   self.q.db.execute('UPDATE links SET state=? WHERE job=?',(state,self.key))
   self.q.db.execute('UPDATE jobs SET state=? WHERE key=?',('WAITING_HUMAN' if state=='REVIEW_REQUIRED' else 'COMPLETE',self.key))
 def manager_verified(self):
  with self.q.tx():self.q.prepare_message(self.q.success_key(self.key),self.payload['source_thread_id'],'Aviso padrao de conclusao.')
  self.dc.deliver(self.q,self.q.success_key(self.key))
 def test_pending_does_not_notify(self):
  self.arm();posts=self.dc.posts
  self.assertEqual(reporting.completion_notices(self.q,lambda:self.dc,self.config())['state'],'NOT_DUE');self.assertEqual(posts,self.dc.posts)
 def test_waits_for_manager_delivery(self):
  self.arm();self.terminal()
  self.assertEqual(reporting.completion_notices(self.q,lambda:self.dc,self.config())['state'],'NOT_DUE')
 def test_verified_then_idempotent_and_no_tracking(self):
  self.arm();self.terminal();self.manager_verified()
  self.assertEqual(reporting.completion_notices(self.q,lambda:self.dc,self.config())['state'],'VERIFIED');posts=self.dc.posts
  self.assertEqual(reporting.completion_notices(self.q,lambda:self.dc,self.config())['state'],'NOT_DUE');self.assertEqual(posts,self.dc.posts)
  content=self.q.db.execute("SELECT content FROM messages WHERE key='landing-request-complete:1561391162588401725'").fetchone()[0]
  self.assertNotIn('utm_source',content);self.assertNotIn('tracking',content)
 def test_partial_review_not_reported_as_success(self):
  self.arm();self.terminal('REVIEW_REQUIRED')
  self.assertEqual(reporting.completion_notices(self.q,lambda:self.dc,self.config())['state'],'VERIFIED')
  text=list(self.dc.messages.values())[-1]['content'];self.assertIn('para revisão',text);self.assertIn('não foi comunicado',text)
 def test_coverage_mismatch_rejected(self):
  cfg=self.config();cfg[0]['total_links']=15
  with self.assertRaises(ValueError):reporting.completion_notices(self.q,lambda:self.dc,cfg)
 def test_wrong_destination_rejected(self):
  cfg=self.config();cfg[0]['thread_id']='150000000000000002'
  with self.assertRaises(ValueError):reporting.completion_notices(self.q,lambda:self.dc,cfg)
 def test_post_ambiguous_reconciles_without_duplicate(self):
  self.arm();self.terminal();self.manager_verified();self.dc.lose_post=True
  with self.assertRaises(ValueError):reporting.completion_notices(self.q,lambda:self.dc,self.config())
  posts=self.dc.posts;self.assertEqual(reporting.completion_notices(self.q,lambda:self.dc,self.config())['state'],'VERIFIED');self.assertEqual(posts,self.dc.posts)

if __name__=='__main__':unittest.main()
