"""Archive read/move adapter call-site checks with offline test doubles only."""
import unittest,importlib.util,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class ConsumerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  s=importlib.util.spec_from_file_location('shein_archive_wiring',ROOT/'scripts/ares-shein-campaigns.py');assert s and s.loader;cls.ops=importlib.util.module_from_spec(s);sys.modules[s.name]=cls.ops;s.loader.exec_module(cls.ops)
 def test_shein_media_read_uses_explicit_domain_projection(self):
  import ares_archive_storage as storage
  projected={'id':'logicalOffline001','record_kind':'mgs.logical.media.v1','provider_id':'archiveOffline001'}
  with patch.object(storage,'resolve_media',return_value=projected) as resolve,patch.object(self.ops.urllib.request,'urlopen',side_effect=AssertionError('OFFLINE_NETWORK_FORBIDDEN')):
   self.assertEqual(self.ops.drive_file_readback('offline-test-token','logicalOffline001'),projected);resolve.assert_called_once()
 def test_shein_move_targets_stock_alias_not_archive_payload(self):
  import ares_archive_storage as storage
  record={'id':'logicalOffline001','record_kind':'mgs.logical.media.v1','parents':['readyOffline001']}
  moved={**record,'parents':['testingOffline001']}
  with patch.object(self.ops,'drive_file_readback',return_value=record),patch.object(storage,'move_stock',return_value=moved) as move,patch.object(self.ops.urllib.request,'urlopen',side_effect=AssertionError('OFFLINE_NETWORK_FORBIDDEN')):
   self.assertEqual(self.ops.move_asset_to_testing('offline-test-token',{'asset_drive_id':record['id']},ready_id='readyOffline001',testing_id='testingOffline001'),moved);move.assert_called_once()
if __name__=='__main__':unittest.main()
