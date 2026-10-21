"""Offline regression: technical dependencies never authorize discovery/writes."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('scope_dependencies','/root/mgs-agent/scripts/mgs-ares-asset-scope.py')
assert spec is not None and spec.loader is not None
scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)
class ScopeDependencies(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch')
  self.addCleanup(self.tmp.cleanup)
  self.data={'ad_accounts':[{'account_id':'111111'},{'account_id':'999999'}],'operational_business_id':'155263197283282'}
  self.ps=[patch.object(scope,'is_ares_context',return_value=True),patch.object(scope,'load_scope',return_value=self.data),patch.object(scope,'PROVENANCE',Path(self.tmp.name)/'provenance.json')]
  for p in self.ps:p.start();self.addCleanup(p.stop)
 def observe(self):
  scope.observe_meta_response('act_111111/ads',{}, {'data':[{'id':'333333','account_id':'111111','creative':{'id':'444444','object_story_spec':{'page_id':'555555','video_data':{'video_id':'666666'}},'asset_feed_spec':{'videos':[{'video_id':'777777'}]}}}]})
 def test_referenced_media_and_page_read_only(self):
  self.observe()
  for p,params in [('666666',{'fields':'id,title,length,status'}),('777777',{'fields':'id,picture'}),('555555',{'fields':'id,name,access_token'}),('555555/assigned_users',{'business':'155263197283282','fields':'id,name,tasks','limit':100})]:scope.enforce_meta_path(p,params)
  for p,params,m in [('555555/assigned_users',{'business':'222222','fields':'id,tasks'},'GET'),('555555/assigned_users',{'business':'155263197283282','fields':'id,tasks'},'POST'),('555555',{'name':'x'},'POST'),('666666',{'fields':'id'},'POST'),('555555/owned_ad_accounts',{},'GET'),('777777',{'fields':'id,adaccounts'},'GET'),('888888',{'fields':'id'},'GET')]:
   with self.subTest(p=p,m=m),self.assertRaises(scope.ScopeError):scope.enforce_meta_path(p,params,m)
 def test_dependency_read_never_promotes_users_or_page(self):
  self.observe();scope.observe_meta_response('555555/assigned_users',{'business':'155263197283282','fields':'id,tasks'}, {'data':[{'id':'888888','tasks':['ADVERTISE']}]})
  self.assertNotIn('888888',scope._objects(self.data));self.assertIsNone(scope._account_for_node('555555',self.data))
 def test_copy_receipts_prove_only_actual_ids(self):
  self.observe();scope.observe_meta_response('333333/copies',{}, {'copied_campaign_id':'888888'},'POST')
  scope.enforce_meta_path('888888',{'name':'approved'},'POST')
  with self.assertRaises(scope.ScopeError):scope.enforce_meta_path('222222',{'account_id':'111111'},'POST')
 def test_shared_page_does_not_grant_other_accounts(self):
  self.observe();scope.observe_meta_response('act_999999/ads',{}, {'data':[{'id':'888888','creative':{'id':'222222','object_story_spec':{'page_id':'555555'}}}]})
  self.assertEqual(scope._objects(self.data)['555555']['account_ids'],['111111','999999'])
  with self.assertRaises(scope.ScopeError):scope.enforce_meta_path('act_123456/campaigns')
 def test_unknown_response_cannot_seed_provenance(self):
  with self.assertRaises(scope.ScopeError):scope.observe_meta_response('act_123456/ads',{}, {'data':[{'id':'333333'}]})
  self.assertFalse(scope.PROVENANCE.exists())
 def test_transport_blocks_before_http_and_binds_lane(self):
  import sys
  sys.path.insert(0,'/root/mgs-agent/scripts')
  from ares_campaign_v3 import transport
  with patch.object(transport,'_operational_scope_guard',return_value=scope),patch.object(transport.urllib.request,'urlopen') as http:
   for lane,path in [('111111','act_123456/campaigns'),('111111','act_999999/campaigns'),('123456','act_111111/campaigns')]:
    with self.subTest(lane=lane,path=path),self.assertRaises(scope.ScopeError):transport.GraphBatchTransport(lane,'v26.0','synthetic').execute([transport.BatchOperation('read','GET',path)],'test')
   http.assert_not_called()
 def test_transport_copy_receipt_is_persisted_before_next_stage(self):
  import sys
  sys.path.insert(0,'/root/mgs-agent/scripts')
  from ares_campaign_v3 import transport
  self.observe()
  from unittest.mock import MagicMock
  response=MagicMock();response.__enter__.return_value=response;response.headers={};response.read.return_value=json.dumps([{'code':200,'body':json.dumps({'copied_ad_id':'888888'})}]).encode()
  with patch.object(transport,'_operational_scope_guard',return_value=scope),patch.object(transport.urllib.request,'urlopen',return_value=response):
   transport.GraphBatchTransport('111111','v26.0','synthetic').execute([transport.BatchOperation('copy','POST','333333/copies',{'adset_id':'333333'})],'copy')
  self.assertEqual(scope._account_for_node('888888',self.data),'111111')
 def test_transport_observation_failure_preserves_successful_ids(self):
  import sys
  sys.path.insert(0,'/root/mgs-agent/scripts')
  from ares_campaign_v3 import transport
  from unittest.mock import MagicMock
  response=MagicMock();response.__enter__.return_value=response;response.headers={};response.read.return_value=json.dumps([{'code':200,'body':json.dumps({'id':'888888'})}]).encode()
  with patch.object(transport,'_operational_scope_guard',return_value=scope),patch.object(scope,'observe_meta_response',side_effect=scope.ScopeError('test')),patch.object(transport.urllib.request,'urlopen',return_value=response):
   with self.assertRaises(transport.BatchTransportError) as got:transport.GraphBatchTransport('111111','v26.0','synthetic').execute([transport.BatchOperation('create','POST','act_111111/adcreatives')],'create')
  self.assertEqual(got.exception.detail['successful_children'][0]['ids']['id'],'888888')
if __name__=='__main__':unittest.main()
