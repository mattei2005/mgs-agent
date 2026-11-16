"""Own candidate metadata grant is scoped by account/profile/issuer and remains read-only."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
CANDIDATE=Path('/root/mgs-agent/scripts/mgs-ares-asset-scope.py')
class CandidateMetadataTests(unittest.TestCase):
 def setUp(self):
  s=importlib.util.spec_from_file_location('candidate_metadata_guard',CANDIDATE);self.g=importlib.util.module_from_spec(s);s.loader.exec_module(self.g)
  self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.profile=self.root/'profile.json';self.selection=self.root/'selection.json'
  self.grant={'status':'active','account_id':'1481815942722118','authorized_by_discord_id':'344196393512075265','authority_message_id':'1571975883286257726','expected_app_id':'1299247318762949','expected_profile_name':'Ana Cunha','expected_token_type':'USER','allowed_reads':['me:id,name','debug_token:self_only']}
  self.profile.write_text(json.dumps({'status':'active','approved_app_id':'1299247318762949','technical_identity_validation_by_account':{'1481815942722118':self.grant}}));self.selection.write_text(json.dumps({'target_app_id':'1299247318762949','read_only_test_authority_message_id':'1571975883286257726','agent_actions_on_hold':False}))
  for key,value in [('CREDENTIAL_ADVERTISER_PROFILE_POLICY',self.profile),('CREDENTIAL_APP_SELECTION_POLICY',self.selection)]:
   p=patch.object(self.g,key,value,create=True);p.start();self.addCleanup(p.stop)
 def observe(self,app='1299247318762949',kind='USER'):
  self.g.observe_credential_metadata('debug_token',{'input_token':'synthetic-own'},{'data':{'is_valid':True,'app_id':app,'user_id':'12345678','type':kind}},'1481815942722118','synthetic-own')
 def test_exact_new_issuer_and_user_accepted(self):self.observe()
 def test_previous_issuer_denied(self):
  with self.assertRaises(self.g.ScopeError):self.observe('953171080682697')
 def test_other_token_and_extra_fields_and_post_denied(self):
  cases=[('debug_token',{'input_token':'someone-else'},'GET'),('debug_token',{'input_token':'synthetic-own','ids':'123'},'GET'),('me',{'fields':'id,name'},'POST'),('me/adaccounts',{},'GET')]
  for path,params,method in cases:
   with self.subTest(path=path,method=method),self.assertRaises(self.g.ScopeError):self.g.enforce_credential_metadata(path,params,method,'1481815942722118','synthetic-own')
 def test_owner_hold_denies_before_transport(self):
  d=json.loads(self.selection.read_text());d['agent_actions_on_hold']=True;self.selection.write_text(json.dumps(d))
  with self.assertRaises(self.g.ScopeError):self.g.enforce_credential_metadata('me',{'fields':'id,name'},'GET','1481815942722118','synthetic-own')
 def test_wrong_profile_and_system_user_denied(self):
  with self.assertRaises(self.g.ScopeError):self.g.observe_credential_metadata('me',{'fields':'id,name'},{'id':'12345678','name':'Another Profile'},'1481815942722118','synthetic-own')
  with self.assertRaises(self.g.ScopeError):self.observe(kind='SYSTEM_USER')
 def test_metadata_not_promoted_to_assets(self):
  with patch.object(self.g,'_objects') as objects:
   self.g.observe_credential_metadata('me',{'fields':'id,name'},{'id':'12345678','name':'Ana Cunha'},'1481815942722118','synthetic-own');objects.assert_not_called()
if __name__=='__main__':unittest.main()
