import importlib.util,json,os,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path('/root/mgs-agent')
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);assert s is not None and s.loader is not None
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
scope=module('asset_scope',BASE/'scripts/mgs-ares-asset-scope.py')
domains=module('domain_scope',BASE/'scripts/mgs-domain-scope.py')
common=module('meta_common_scope_test',BASE/'scripts/ares-meta-common.py')
class AresScopeTests(unittest.TestCase):
 def fixture(self):return {'ad_accounts':[{'account_id':'111111'}]}
 def test_exact_account_and_act_alias(self):
  for x in ['111111','act_111111']:self.assertTrue(scope.allowed_account(x,self.fixture()))
 def test_unknown_or_malformed_account(self):
  for x in ['222222','111111x',' 111111','https://example.invalid/111111']:self.assertFalse(scope.allowed_account(x,self.fixture()))
 def test_ares_blocks_before_http_get(self):
  with patch.dict(os.environ,{'HERMES_PROFILE':'ares'}),patch.object(common.urllib.request,'urlopen') as http:
   with self.assertRaises(ValueError):common._graph_get_once('act_999999999999999999/campaigns','synthetic-not-a-secret')
   http.assert_not_called()
 def test_ares_blocks_before_http_post(self):
  with patch.dict(os.environ,{'HERMES_PROFILE':'ares'}),patch.object(common.urllib.request,'urlopen') as http:
   with self.assertRaises(ValueError):common._graph_post_once('act_999999999999999999/campaigns','synthetic-not-a-secret',{})
   http.assert_not_called()
 def test_positive_account_passes_library_gate(self):
  live=scope.load_scope();aid=live['ad_accounts'][0]['account_id']
  with patch.dict(os.environ,{'HERMES_PROFILE':'ares'}):common._enforce_operational_account_scope('act_'+aid+'/campaigns')
 def test_zeus_audit_is_not_restricted(self):
  with patch.dict(os.environ,{'HERMES_PROFILE':'zeus','HERMES_HOME':'/root/.hermes/profiles/zeus'}),patch.object(scope,'is_ares_context',return_value=False):scope.enforce_meta_path('act_222222/campaigns')
 def test_nested_batch_is_checked(self):
  with patch.object(scope,'is_ares_context',return_value=True),patch.object(scope,'load_scope',return_value=self.fixture()):
   with self.assertRaises(scope.ScopeError):scope.enforce_meta_path('',{'batch':json.dumps([{'method':'GET','relative_url':'act_222222/campaigns'}])})
 def test_app_metadata_exception_is_preserved(self):
  with patch.object(scope,'is_ares_context',return_value=True),patch.object(scope,'load_scope') as loader:
   scope.enforce_meta_path('1299247318762949',{'fields':'id,name'});loader.assert_not_called()
 def test_ares_domain_scope_matches_approved_catalog(self):
  d=domains.load_registry(BASE/'data/mgs-domain-scope.json');a=scope.load_scope()
  self.assertEqual(domains.domains_for_agent(d,'ares'),a['domains']);self.assertEqual(len(a['domains']),52)
 def test_atena_unchanged(self):
  d=domains.load_registry(BASE/'data/mgs-domain-scope.json');self.assertEqual(domains.domains_for_agent(d,'atena'),d['domains']);self.assertEqual(len(d['domains']),58)
 def test_synthetic_agent_domain_override(self):
  d={'domains':['global.test'],'agent_scopes':{'ares':{'domains':['sb-only.test']}},'policy':{'allow_www_alias':True}}
  self.assertIsNone(domains.allowed_domain('global.test',d,'ares'));self.assertEqual(domains.allowed_domain('www.sb-only.test',d,'ares'),'sb-only.test');self.assertIsNone(domains.allowed_domain('child.sb-only.test',d,'ares'));self.assertEqual(domains.allowed_domain('global.test',d,'atena'),'global.test')
 def test_denial_never_echoes_target(self):
  x='999999999999999999';r=subprocess.run(['python3',str(BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',x,'--json'],capture_output=True,text=True)
  self.assertEqual(r.returncode,3);self.assertNotIn(x,r.stdout);self.assertFalse(json.loads(r.stdout)['allowed'])
if __name__=='__main__':unittest.main()
