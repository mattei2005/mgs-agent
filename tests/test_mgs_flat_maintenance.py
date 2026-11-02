import unittest
from unittest.mock import patch,Mock
import mgs_flat_maintenance as m
import ares_archive_retirement as retirement

class MaintenanceTests(unittest.TestCase):
 def setUp(self):
  self.file={'id':'source_123456','size':'12','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'properties':{}}
  self.entry={'verified':True,'stockTransferredToArchive':True,'size':'12','md5':'a'*32,'sha256':'b'*64}
 def test_uncompleted_not_eligible(self):self.assertFalse(m.eligible_file(self.file,{self.file['id']:self.entry},{}))
 def test_complete_verified_pair_eligible(self):self.assertTrue(m.eligible_file(self.file,{self.file['id']:self.entry},{self.file['id']:'b'*64}))
 def test_ack_stock_missing_rejected(self):self.assertFalse(m.eligible_file(self.file,{self.file['id']:{**self.entry,'stockTransferredToArchive':False}},{self.file['id']:'b'*64}))
 def test_sha_changed_rejected(self):self.assertFalse(m.eligible_file(self.file,{self.file['id']:self.entry},{self.file['id']:'c'*64}))
 def test_completed_reupload_same_id_preserved(self):self.assertTrue(m.eligible_file(self.file,{}, {self.file['id']:'b'*64}))
 def test_unregistered_unreleased_not_eligible(self):self.assertFalse(m.eligible_file(self.file,{},{}))
 def test_flat_cycle_never_deletes(self):
  with patch('ares_flat_intake.policy',return_value={'same_id_source_preservation':True}):
   d=Mock();r=retirement.run_cycle(d,{'delete_source':True},{},True);self.assertEqual(r['files_retired'],0);self.assertEqual(r['delete_writes'],0);d.assert_not_called()
 def test_direct_delete_entrypoint_closed(self):
  with patch('ares_flat_intake.policy',return_value={'same_id_source_preservation':True}):
   d=Mock()
   with self.assertRaises(retirement.RetirementError):retirement.retire_asset(d,{}, {}, {'sourceId':'source_123456'},'unused')
   self.assertEqual(d.method_calls,[])
if __name__=='__main__':unittest.main()
