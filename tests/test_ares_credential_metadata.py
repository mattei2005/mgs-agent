import importlib.util,json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/root/mgs-agent')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
scope=load('scope_own_identity',ROOT/'scripts/mgs-ares-asset-scope.py')
common=load('common_own_identity',ROOT/'scripts/ares-meta-common.py')
class CredentialMetadataTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.tmp.cleanup)
  self.policy=Path(self.tmp.name)/'policy.json'
  self.grant={'status':'active','account_id':'1034081997659047','technical_identity_validation':{'status':'active','account_id':'1034081997659047','authorized_by_discord_id':'344196393512075265','authority_message_id':'1567911802774360195','allowed_reads':['me:id,name','debug_token:self_only']}}
  self.policy.write_text(json.dumps(self.grant));self.p=patch.object(scope,'CREDENTIAL_IDENTITY_POLICY',self.policy);self.p.start();self.addCleanup(self.p.stop)
 def enforce(self,path='me',params=None,method='GET',account='1034081997659047',token='synthetic-own-token'):
  return scope.enforce_credential_metadata(path,params if params is not None else {'fields':'id,name'},method,account,token)
 def test_approved_own_identity(self):self.enforce()
 def test_self_debug(self):self.enforce('debug_token',{'input_token':'synthetic-own-token'})
 def test_foreign_token_denied(self):
  with self.assertRaises(scope.ScopeError):self.enforce('debug_token',{'input_token':'synthetic-other-token'})
 def test_other_account_denied(self):
  with self.assertRaises(scope.ScopeError):self.enforce(account='1481815942722118')
 def test_missing_grant_denied(self):
  self.policy.write_text('{}')
  with self.assertRaises(scope.ScopeError):self.enforce()
 def test_discovery_and_write_denied(self):
  for path,params,method in [('me/adaccounts',{},'GET'),('me',{'fields':'id,name,adaccounts'},'GET'),('me',{'fields':'id,name'},'POST'),('debug_token',{'input_token':'synthetic-own-token','ids':'123456'},'GET')]:
   with self.subTest(path=path,method=method),self.assertRaises(scope.ScopeError):self.enforce(path,params,method)
 def test_identity_not_enrolled_as_asset(self):
  with patch.object(scope,'_objects') as objects:
   scope.observe_credential_metadata('me',{'fields':'id,name'},{'id':'1234567','name':'Example'},'1034081997659047','synthetic-own-token');objects.assert_not_called()
 def test_wrong_app_or_invalid_token_denied(self):
  for payload in [{'is_valid':True,'app_id':'1234567','user_id':'1234567'},{'is_valid':False,'app_id':scope.APP_ID,'user_id':'1234567'}]:
   with self.subTest(payload=payload),self.assertRaises(scope.ScopeError):scope.observe_credential_metadata('debug_token',{'input_token':'synthetic-own-token'},{'data':payload},'1034081997659047','synthetic-own-token')
 def test_unknown_account_denied_before_http(self):
  with patch.object(common.urllib.request,'urlopen') as http:
   with self.assertRaises(ValueError):common.graph_get_credential_metadata('999999999999999999','synthetic-own-token')
   http.assert_not_called()
 def test_generic_me_still_denied_without_grant_context(self):
  with patch.object(scope,'is_ares_context',return_value=True):
   with self.assertRaises(scope.ScopeError):scope.enforce_meta_path('me',{'fields':'id,name'})
if __name__=='__main__':unittest.main()
