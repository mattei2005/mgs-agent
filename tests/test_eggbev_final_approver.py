"""Final campaign approval follows the existing exact account delegation."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
CANDIDATE=Path('/root/mgs-agent/scripts/ares_campaign_v3/eggbev_same_account_replacement.py')
class FinalApproverTests(unittest.TestCase):
 def setUp(self):
  spec=importlib.util.spec_from_file_location('ares_campaign_v3.final_approver_candidate',CANDIDATE);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
  self.temp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.q={'account_id':'1481815942722118','source_thread_id':'1565032671669919827'}
  self.authority={'status':'active','account_id':self.q['account_id'],'source_thread_id':self.q['source_thread_id'],'authorized_by_discord_id':self.m.CEO,'authorized_manager_discord_id':'1055570806945620030','scope':['campaign creation, clone and duplication requests','per-request campaign activation including explicit immediate start']}
  self.save_authority()
  p=self.root/'data/authorized-users.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'agents':{'ares':{'authorized_user_discord_ids':['1055570806945620030',self.m.CEO]}}}))
  self.ctx=patch.object(self.m,'ROOT',self.root);self.ctx.start();self.addCleanup(self.ctx.stop)
 def save_authority(self):
  p=self.root/'data/ares/meta-ads/operations/Eggbev-US-CC-EN-03-BOT.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'authority':self.authority}))
 def test_get429_retries_only_idempotent_reads(self):
  from types import SimpleNamespace
  calls=[];replies=iter([(429,{'retry_after':0.2}),(200,{'id':'message'})])
  def request(method,path):calls.append((method,path));return next(replies)
  with patch.object(self.m.time,'sleep') as sleep:
   result=self.m.discord_get(SimpleNamespace(discord_request=request),'/channels/1565032671669919827/messages/123')
  self.assertEqual(result,(200,{'id':'message'}));self.assertEqual([x[0] for x in calls],['GET','GET']);sleep.assert_called_once_with(0.2)
 def test_get404_not_retried(self):
  from types import SimpleNamespace
  from unittest.mock import Mock
  request=Mock(return_value=(404,None))
  self.assertEqual(self.m.discord_get(SimpleNamespace(discord_request=request),'/channels/1565032671669919827/messages/123'),(404,None));request.assert_called_once()
 def test_get429_old_sdk_missing_body_has_bounded_backoff(self):
  from types import SimpleNamespace
  from unittest.mock import Mock
  request=Mock(side_effect=[(429,None),(200,{'id':'message'})])
  with patch.object(self.m.time,'sleep') as sleep:
   self.m.discord_get(SimpleNamespace(discord_request=request),'/channels/1565032671669919827/messages/123')
  sleep.assert_called_once_with(2.0)
 def test_existing_manager_may_approve_and_unknown_cannot(self):
  self.assertTrue(self.m.authorized_final_approver(self.q,'1055570806945620030'))
  self.assertTrue(self.m.authorized_final_approver(self.q,self.m.CEO))
  self.assertFalse(self.m.authorized_final_approver(self.q,'999999999999999999'))
 def test_revoked_delegation_denies_manager(self):
  self.authority['status']='revoked';self.save_authority();self.assertFalse(self.m.authorized_final_approver(self.q,'1055570806945620030'))
 def test_wrong_account_or_thread_denies_manager(self):
  for field,value in [('account_id','1034081997659047'),('source_thread_id','1541578556037927053')]:
   q={**self.q,field:value};self.assertFalse(self.m.authorized_final_approver(q,'1055570806945620030'))
if __name__=='__main__':unittest.main()
