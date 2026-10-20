"""Offline storage facade fixtures; never fabricate production provider results."""
import unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('archive_storage',ROOT/'scripts/ares_archive_storage.py');assert spec and spec.loader
class StorageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert spec and spec.loader;cls.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.m)
 def setUp(self):
  self.entry={'sourceId':'logicalOffline001','archiveId':'archiveOffline001','archiveParentId':'archiveParentOffline','lineageId':'assetOffline001','role':'clean','sha256':'a'*64,'md5':'b'*32,'size':'200','owner':'mgsdigitalcorp@gmail.com','verified':True,'stockShortcutId':'shortcutOffline001'}
  self.physical={'id':'archiveOffline001','name':'SHEIN_US_ES_IMG_TEST_NH_001.png','mimeType':'image/png','size':'200','md5Checksum':'b'*32,'sha256Checksum':'a'*64,'owners':[{'emailAddress':'mgsdigitalcorp@gmail.com'}],'parents':['archiveParentOffline'],'trashed':False}
  self.stock={'id':'shortcutOffline001','name':self.physical['name'],'mimeType':'application/vnd.google-apps.shortcut','driveId':'0AEwt4Ye690ocUk9PVA','parents':['readyOffline001'],'trashed':False,'shortcutDetails':{'targetId':'archiveOffline001'},'properties':{'mgsArchiveLogicalSource':'logicalOffline001'}}
 def test_domain_record_preserves_logical_id_and_actual_provider_ids(self):
  v=self.m.media_record(self.entry,self.physical,self.stock);self.assertEqual(v['id'],'logicalOffline001');self.assertEqual(v['provider_id'],'archiveOffline001');self.assertEqual(v['stock_file_id'],'shortcutOffline001');self.assertEqual(v['record_kind'],'mgs.logical.media.v1');self.assertEqual(v['provider_metadata']['id'],'archiveOffline001')
 def test_unverified_entry_not_consumable(self):
  with self.assertRaises(self.m.StorageError):self.m.media_record({**self.entry,'verified':False},self.physical,self.stock)
 def test_redirected_shortcut_rejected(self):
  self.stock['shortcutDetails']['targetId']='otherOffline001'
  with self.assertRaises(self.m.StorageError):self.m.media_record(self.entry,self.physical,self.stock)
 def test_wrong_owner_rejected(self):
  self.physical['owners']=[{'emailAddress':'other@example.com'}]
  with self.assertRaises(self.m.StorageError):self.m.media_record(self.entry,self.physical,self.stock)
 def test_changed_archive_checksum_rejected(self):
  self.physical['sha256Checksum']='c'*64
  with self.assertRaises(self.m.StorageError):self.m.media_record(self.entry,self.physical,self.stock)
 def test_frozen_archive_path_is_not_stock_status_path(self):
  self.stock['parents']=['testingOffline001'];v=self.m.media_record(self.entry,self.physical,self.stock);self.assertEqual(v['parents'],['testingOffline001']);self.assertEqual(v['provider_metadata']['parents'],['archiveParentOffline'])
 def test_shared_drive_identity_must_be_actual_stock_identity(self):
  self.stock['driveId']='outside'
  with self.assertRaises(self.m.StorageError):self.m.media_record(self.entry,self.physical,self.stock)
 def test_projection_dedupes_original_and_shortcut_as_one_candidate(self):
  v=self.m.media_record(self.entry,self.physical,self.stock);original={'id':'logicalOffline001','name':v['name']};self.assertEqual(self.m.dedupe_catalog([original,v]),[v])
 def test_duplicate_distinct_aliases_are_blocked(self):
  v=self.m.media_record(self.entry,self.physical,self.stock)
  with self.assertRaises(self.m.StorageError):self.m.dedupe_catalog([v,{**v,'stock_file_id':'differentShortcut'}])
 def test_validation_only_jobs_never_supply_production_mapping(self):
  index={'verified_jobs':{'job':{'validationOnly':True,'assets':[self.entry]}}}
  with self.assertRaises(self.m.StorageError):self.m.require_registered_mapping(self.entry,index)
 def test_reverification_preserves_alias_outside_immutable_ack_assets(self):
  b=self.m.b;index={'mappings':{self.entry['sourceId']:dict(self.entry)},'verified_jobs':{}};entry={k:v for k,v in self.entry.items() if k!='stockShortcutId'};job={'kind':'lineage','jobId':'job'};result={'status':'verified','jobId':'job','deleteSource':False,'assets':[entry]}
  b.record_verified_job(index,job,result);self.assertEqual(index['mappings'][entry['sourceId']]['stockShortcutId'],'shortcutOffline001');self.assertNotIn('stockShortcutId',result['assets'][0])
 def test_new_lineage_cannot_reach_campaign_before_archive_ack_and_alias(self):
  from unittest.mock import patch
  row={'asset_id':'assetOffline001','asset_drive_id':'logicalOffline001','first_seen_at':'2026-10-20T21:00:00Z'};cfg={'queue_enabled':True,'effective_after':'2026-10-20T14:23:41Z'}
  with patch.object(self.m.b,'config_load',return_value=cfg),patch.object(self.m,'mapping',return_value=None):
   with self.assertRaises(self.m.StorageError):self.m.require_lineage_available(row)
  with patch.object(self.m.b,'config_load',return_value={**cfg,'queue_enabled':False}):self.assertTrue(self.m.require_lineage_available(row))
if __name__=='__main__':unittest.main()
