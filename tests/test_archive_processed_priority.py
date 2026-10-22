"""Offline priority tests: order only, never membership/content/authority changes."""
import sys,unittest,copy
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_backfill as h
class ProcessedPriority(unittest.TestCase):
 def setUp(self):
  self.assets=[{'sourceId':x,'sha256':x*64} for x in ['aux','raw','clean','clean2']]
  self.rows=[{'metadata_clean':True,'status':'01_READY','source_drive_id':'raw','asset_drive_id':'clean'},{'metadata_clean':True,'status':'02_TESTING','asset_drive_id':'clean2'}]
 def test_processed_then_raw_then_aux(self):self.assertEqual([x['sourceId'] for x in h.prioritize_pending_assets(self.assets,self.rows)],['clean','clean2','raw','aux'])
 def test_frozen_assets_are_unchanged(self):
  before=copy.deepcopy(self.assets);out=h.prioritize_pending_assets(self.assets,self.rows);self.assertEqual(self.assets,before);self.assertEqual(sorted(out,key=lambda x:x['sourceId']),sorted(before,key=lambda x:x['sourceId']))
 def test_stable_original_order_within_priority(self):self.assertEqual([x['sourceId'] for x in h.prioritize_pending_assets(list(reversed(self.assets)),self.rows)],['clean2','clean','raw','aux'])
 def test_retired_rows_do_not_gain_priority(self):
  self.rows[0]['status']='TRASHED_BY_MANAGER_REQUEST';self.assertEqual(h.prioritize_pending_assets(self.assets,self.rows)[0]['sourceId'],'clean2')
 def test_nonclean_rows_do_not_gain_priority(self):
  self.rows[0]['metadata_clean']=False;self.assertEqual(h.prioritize_pending_assets(self.assets,self.rows)[0]['sourceId'],'clean2')
 def test_catalogue_never_adds_unfrozen_assets(self):
  self.rows.append({'metadata_clean':True,'asset_drive_id':'not-in-manifest'});self.assertEqual(len(h.prioritize_pending_assets(self.assets,self.rows)),len(self.assets))
 def test_no_catalogue_preserves_source_order(self):self.assertEqual(h.prioritize_pending_assets(self.assets,[]),self.assets)
if __name__=='__main__':unittest.main()
