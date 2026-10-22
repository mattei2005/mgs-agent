"""Offline history consumer fixtures, never fabricated Google proof."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_storage as s
class HistoricalConsumerTests(unittest.TestCase):
 def setUp(self):
  self.entry={'mapping_kind':'historical_verified','sourceId':'OFFLINE_SOURCE01','archiveId':'OFFLINE_ARCHIVE01','archiveParentId':'OFFLINE_PARENT01','owner':s.b.ACCOUNT,'verified':True,'size':'5','md5':'a'*32,'sha256':'b'*64,'role':'historical','lineageId':None,'jobId':'OFFLINE_JOB01','relativeParent':['SHEIN_US_EN','VID','01_READY']}
  self.physical={'id':self.entry['archiveId'],'name':'canonical.mp4','mimeType':'video/mp4','size':'5','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'parents':['OFFLINE_PARENT01'],'owners':[{'emailAddress':s.b.ACCOUNT}],'trashed':False,'capabilities':{'canDownload':True}}
  self.stock={'id':self.entry['sourceId'],'name':'operator label','mimeType':'video/mp4','size':'5','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'parents':['OFFLINE_STOCK01'],'driveId':s.b.SOURCE_DRIVE,'trashed':False,'capabilities':{'canMoveItemWithinDrive':True}}
 def test_real_source_metadata_and_archive_metadata_stay_separate(self):
  r=s.historical_media_record(self.entry,self.physical,self.stock)
  self.assertEqual(r['id'],self.entry['sourceId']);self.assertEqual(r['provider_id'],self.entry['archiveId']);self.assertEqual(r['provider_metadata'],self.physical);self.assertEqual(r['stock_metadata'],self.stock);self.assertEqual(r['name'],'operator label');self.assertIsNone(r['lineage_id']);self.assertEqual(r['stock_representation'],'retained_source')
 def test_changed_bytes_wrong_owner_or_missing_stock_is_rejected(self):
  for bad in [{**self.physical,'md5Checksum':'c'*32},{**self.physical,'owners':[{'emailAddress':'outside@example.invalid'}]}]:
   with self.assertRaises(s.StorageError):s.historical_media_record(self.entry,bad,self.stock)
  with self.assertRaises(s.StorageError):s.historical_media_record(self.entry,self.physical,{**self.stock,'trashed':True})
 def test_download_uses_verified_archive_and_preserves_logical_id(self):
  with patch.object(s,'resolve_media',return_value={'provider_id':self.entry['archiveId']}):self.assertEqual(s.download_id(self.entry['sourceId']),self.entry['archiveId'])
 def test_historical_feature_is_fail_closed_without_flag(self):
  with patch.object(s.b,'read_json',return_value={}):self.assertFalse(s.historical_enabled())
if __name__=='__main__':unittest.main()
