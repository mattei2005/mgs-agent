"""Offline source-thread label and stable outbox delivery regressions."""
import json,unittest
from unittest.mock import patch
import test_direct_traffic_landing_followup as fixtures
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_followup_reporting import origin_notification_content

class OriginNoticeTests(unittest.TestCase):
 setUp=fixtures.FollowupTests.setUp
 tearDown=fixtures.FollowupTests.tearDown
 def configure(self):
  p=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'notification_origin_context':{'enabled':True,'authority_message_id':'1561407383786487848'}}))
  base=self.dc.get
  def get(path):
   out=base(path)
   if '/messages' not in path and path.startswith('/channels/'):out['name']='🎯Yolokfx Conta 02 Criar Camp'
   return out
  self.dc.get=get
 def notice(self):
  self.configure();key='landing-item:'+self.key+':0:1:PASSED'
  with self.q.tx():
   self.q.prepare_message(key,core.INCIDENT_THREAD,'**Acompanhamento — campanha b01fb02c221**\nAnuncio identificado.')
   self.q.event(self.key,'progress_update_authorized',{'notification_key':key,'scope_jobs':[self.key]})
  return key
 def test_real_delivery_uses_name_and_retains_base(self):
  key=self.notice();before=dict(self.q.db.execute('select * from messages where key=?',(key,)).fetchone());m=self.dc.deliver(self.q,key)
  self.assertIn('🎯Yolokfx Conta 02 Criar Camp',m['content']);self.assertIn('<#'+self.payload['source_thread_id']+'>',m['content'])
  after=dict(self.q.db.execute('select * from messages where key=?',(key,)).fetchone());self.assertEqual(before['content'],after['content']);self.assertEqual(before['nonce'],after['nonce']);self.assertEqual(after['state'],'VERIFIED')
 def test_ambiguous_post_keeps_exact_rendered_content(self):
  key=self.notice();self.dc.lose_post=True
  with self.assertRaises(ValueError):self.dc.deliver(self.q,key)
  posts=self.dc.posts;m=self.dc.deliver(self.q,key);self.assertEqual(self.dc.posts,posts);self.assertIn('Thread de origem',m['content'])
 def test_manager_thread_message_unchanged(self):
  self.configure()
  with self.q.tx():self.q.prepare_message('manager-standard',self.payload['source_thread_id'],'Mensagem padrao.')
  m=self.dc.deliver(self.q,'manager-standard');self.assertEqual(m['content'],'Mensagem padrao.')
 def test_old_ambiguous_without_rendering_not_modified(self):
  key=self.notice()
  with self.q.tx():self.q.db.execute("update messages set state='INTENT' where key=?",(key,))
  row=dict(self.q.db.execute('select * from messages where key=?',(key,)).fetchone());self.assertEqual(origin_notification_content(self.q,row,self.dc),row['content'])
 def test_wrong_parent_rejected_without_post(self):
  key=self.notice();self.dc.channel_parents[self.payload['source_thread_id']]='150000000000000099'
  with self.assertRaises(ValueError):self.dc.deliver(self.q,key)
  self.assertEqual(self.dc.posts,0)
 def test_completion_event_resolves_origin_and_dedupes(self):
  self.configure();key='landing-request-complete:1561407383786487848'
  with self.q.tx():
   self.q.prepare_message(key,core.INCIDENT_THREAD,'Rodada concluida.')
   self.q.event(None,'completion_notice_authorized',{'notification_key':key,'job_keys':[self.key,self.key]})
  m=self.dc.deliver(self.q,key);self.assertEqual(m['content'].count('Thread de origem'),1)
 def test_verified_rendering_not_changed_on_rename(self):
  key=self.notice();m=self.dc.deliver(self.q,key);self.dc._landing_origin_names={}
  self.dc.get=lambda p: (_ for _ in ()).throw(AssertionError('must not refetch existing rendering'))
  row=dict(self.q.db.execute('select * from messages where key=?',(key,)).fetchone());self.assertEqual(origin_notification_content(self.q,row,self.dc),m['content'])

if __name__=='__main__':unittest.main()
