import sys,copy,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
import ares_archive_locations as l
class LocationTests(unittest.TestCase):
 def value(self):
  return {'schema':'mgs.archive.stock.layout.v1','approval_message_id':l.APPROVAL,'source_drive_id':b.SOURCE_DRIVE,'staging_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'upload_root_id':l.UPLOAD,'owner':b.ACCOUNT,'stock_root_id':'OFFLINE_STOCK_ROOT','active':False}
 def test_inactive_preserves_old_contract(self):
  with patch.object(l,'binding',return_value=self.value()):
   self.assertEqual(l.stock_root(),b.SOURCE_ROOT);self.assertEqual(l.upload_parent(),b.SOURCE_ROOT)
 def test_active_requires_verified_acceptance(self):
  v=self.value();v['active']=True
  with self.assertRaisesRegex(b.ArchiveError,'ACCEPTANCE_REQUIRED'):l.validate(v)
 def test_approved_active_contract(self):
  v={**self.value(),'active':True,'same_ids_verified':True,'consumer_canary_verified':True,'acceptance_proof':'OFFLINE_PROOF'}
  with patch.object(l,'binding',return_value=l.validate(v)):
   self.assertEqual(l.stock_root(),'OFFLINE_STOCK_ROOT');self.assertEqual(l.upload_parent(),b.SOURCE_DRIVE)
 def test_unknown_or_changed_pins_fail_closed(self):
  for k,val in [('owner','wrong@example.invalid'),('source_drive_id','OFFLINE_WRONG'),('staging_root_id','OFFLINE_WRONG'),('approval_message_id','wrong'),('active','true'),('stock_root_id',b.SOURCE_ROOT)]:
   with self.subTest(k=k),self.assertRaises(b.ArchiveError):l.validate({**self.value(),k:val})
 def test_stock_gate_rejects_public_wrong_owner_shared_and_trashed(self):
  active={**self.value(),'active':True,'same_ids_verified':True,'consumer_canary_verified':True,'acceptance_proof':'OFFLINE_PROOF'}
  meta={'trashed':False,'owners':[{'emailAddress':b.ACCOUNT}],'permissions':[{'type':'user'}]}
  with patch.object(l,'active',return_value=active):
   self.assertTrue(l.stock_metadata_allowed(meta))
   for changed in [{'owners':[{'emailAddress':'wrong@example.invalid'}]},{'driveId':b.SOURCE_DRIVE},{'trashed':True},{'permissions':[{'type':'anyone'}]},{'permissions':[{'type':'domain'}]}]:
    with self.subTest(changed=changed):self.assertFalse(l.stock_metadata_allowed({**meta,**changed}))
 def test_absent_binding_is_not_activation(self):
  with patch.object(b,'read_json',return_value=None):self.assertIsNone(l.active())
 def test_scope_helper_requires_native_ancestry(self):
  class D:
   def meta(self,fid):return {'id':fid,'mimeType':b.FOLDER,'trashed':False,'driveId':b.SOURCE_DRIVE}
   def relative_parent(self,parent,root):raise b.ArchiveError('ANCESTRY')
  with patch.object(l,'active',return_value=None),self.assertRaisesRegex(b.ArchiveError,'ANCESTRY'):l.stock_parent(D(),'OFFLINE_PARENT')
if __name__=='__main__':unittest.main()
