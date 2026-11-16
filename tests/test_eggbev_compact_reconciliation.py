"""Narrow complete target reconciliation and exact persisted source reads."""
import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock,patch
import test_eggbev_cross_account_clone as fixtures
from ares_campaign_v3 import eggbev_cross_account as c

class ReconciliationTests(unittest.TestCase):
 def setUp(self):
  self.base=fixtures.CrossTests('test_01_new_mode_shape_and_five_by_three_order');self.base.setUp();self.addCleanup(self.base.doCleanups)
  self.home=self.base.root;self.q=self.base.q;self.assets=self.base.assets;self.common=Mock();self.rows=[{'id':'123456','name':'other','creative':None}];self.common.fetch_all_meta.return_value=self.rows
 def evidence(self,**changes):
  e={'account_id':c.TARGET,'request_id':self.q['request_id'],'fields':c.MEDIA_RECONCILIATION_FIELDS,'complete':True,'after':None,'data':copy.deepcopy(self.rows),'data_sha256':c.digest(self.rows),'selected_identity_sha256':c.digest([{k:a.get(k) for k in ['asset_id','canonical_filename','clean_checksum','clean_md5','manager_media_folder_id']} for a in self.assets]),'completed_at':datetime.now(timezone.utc).isoformat()};e.update(changes);(self.home/'target-media-use-reconciliation.json').write_text(json.dumps(e));return e
 def call(self):return c.target_media_reconciliation(self.q,self.home,self.assets,self.common,Mock(),'fake')
 def test_fresh_complete_proof_reused_without_network(self):
  self.evidence();self.assertEqual(self.call(),self.rows);self.common.fetch_all_meta.assert_not_called()
 def test_tampered_rows_fail_closed(self):
  self.evidence(data=[{'id':'9999'}])
  with self.assertRaises(ValueError):self.call()
  self.common.fetch_all_meta.assert_not_called()
 def test_wrong_scope_fails_closed(self):
  self.evidence(account_id=c.SOURCE)
  with self.assertRaises(ValueError):self.call()
 def test_changed_selected_identity_fails_closed(self):
  self.evidence(selected_identity_sha256='0'*64)
  with self.assertRaises(ValueError):self.call()
 def test_stale_proof_refreshed_with_narrow_projection(self):
  self.evidence(completed_at=(datetime.now(timezone.utc)-timedelta(minutes=11)).isoformat());self.call();args=self.common.fetch_all_meta.call_args.args;self.assertEqual(args[3]['fields'],c.MEDIA_RECONCILIATION_FIELDS);self.assertEqual(args[3]['limit'],100)
 def test_incomplete_proof_cannot_be_reused(self):
  self.evidence(complete=False,after='opaque');self.call();self.common.fetch_all_meta.assert_called_once()
 def test_duplicate_ids_rejected(self):
  self.evidence(data=self.rows*2,data_sha256=c.digest(self.rows*2))
  with self.assertRaises(ValueError):self.call()
 def test_persisted_source_uses_exact_GET_not_inventory(self):
  b=self.base;q=copy.deepcopy(self.q);q['source_campaign_id']=b.source['campaign']['id'];meta=Mock();meta.graph_get.return_value=(200,copy.deepcopy(b.source['campaign']),{})
  def fetch(meta,token,path,params):
   if path==q['source_campaign_id']+'/adsets':return [copy.deepcopy(b.source['adset'])]
   if path==q['source_campaign_id']+'/ads':return copy.deepcopy(b.source['ads'])
   raise AssertionError('source inventory read must not repeat')
  self.common.fetch_all_meta.side_effect=fetch
  with patch.object(b.m,'source_seed_proof',return_value=None):out=c.source_read(q,b.m,self.common,meta,'fake',b.cfg)
  self.assertEqual(out['campaign']['id'],q['source_campaign_id']);self.assertEqual(self.common.fetch_all_meta.call_count,2)

if __name__=='__main__':unittest.main()
