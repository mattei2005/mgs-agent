import unittest,sys,copy
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_namespace as n
import ares_archive_storage as storage
import ares_manager_storage_standard as standard

class NativeUsedRetirement(unittest.TestCase):
 def setUp(self):
  self.entry={'sourceId':'sourceOffline001','archiveId':'providerOffline001','lineageId':'assetOffline001','role':'clean','sha256':'a'*64,'md5':'b'*32,'size':'10','stockShortcutId':'stockOffline001'}
  self.rec={'source_id':self.entry['sourceId'],'stock_id':'stockOffline001','from_parent':'oldReadyOffline001','to_parent':'usedOffline001','sha256':'a'*64,'state':'used','manager_code':'g006','inventory_asset_id':'assetOffline001','classification_basis':'native_historical_use_verified'}
  self.row={'asset_id':'assetOffline001','asset_drive_id':self.entry['sourceId'],'clean_checksum':'a'*64,'manager_media_folder_id':'usedOffline001','manager_storage_state':'used','manager_storage_code':'g006','legacy_consolidation_authority':n.AUTHORITY,'legacy_usage_classification':'native_historical_use_verified','canonical_filename':'canonical.jpg','used_by':'100','meta_ad_id':'300','meta_creative_id':'400'}
  self.record={'parents':['usedOffline001'],'sha256Checksum':'a'*64,'name':'canonical.jpg'}
 def runcheck(self,receipt=None):
  class D:
   def hashes(d,fid):return {k:self.entry[k] for k in ['size','md5','sha256']}
  with patch.object(n,'stock_move',return_value=self.rec),patch.object(standard,'validate_folder'),patch.object(storage,'resolve_media',return_value=self.record):
   return n.verify_migrated_delivery(D(),self.row,self.entry,{} if receipt is None else receipt)
 def test_native_verified_historical_use_has_no_invented_original_delivery(self):
  self.assertEqual(self.runcheck(),self.record)
 def test_wrong_authority_manager_identity_and_hash_are_rejected(self):
  for key,value in [('legacy_consolidation_authority','wrong'),('legacy_usage_classification','unproven'),('manager_storage_state','exclusive'),('manager_storage_code','g002'),('asset_drive_id','other'),('clean_checksum','c'*64),('asset_id','other')]:
   with self.subTest(key=key):
    old=self.row[key];self.row[key]=value
    with self.assertRaises(n.NamespaceError):self.runcheck()
    self.row[key]=old
 def test_only_used_and_exact_consolidated_destination_qualify(self):
  self.rec['state']='exclusive'
  with self.assertRaises(n.NamespaceError):self.runcheck()
 def test_unknown_or_unproven_classification_still_requires_original_receipt(self):
  self.rec['classification_basis']='unproven'
  with self.assertRaises(n.NamespaceError):self.runcheck()
 def test_nonempty_invalid_original_receipt_is_never_ignored(self):
  with self.assertRaises(n.NamespaceError):self.runcheck({'status':'intent'})
 def test_missing_native_assignment_identifiers_rejected(self):
  for key in ['used_by','meta_ad_id','meta_creative_id']:
   with self.subTest(key=key):
    old=self.row.pop(key)
    with self.assertRaises(n.NamespaceError):self.runcheck()
    self.row[key]=old
 def test_readback_and_full_bytes_stay_mandatory(self):
  self.record['sha256Checksum']='c'*64
  with self.assertRaises(n.NamespaceError):self.runcheck()
if __name__=='__main__':unittest.main()
