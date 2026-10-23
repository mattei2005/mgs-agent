"""Offline bounded slot contract; never mint owner/SA credentials in tests."""
import sys,copy,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_private_control_store as c
class SlotScope(unittest.TestCase):
 def setUp(self):
  self.binding={'schema':'mgs.private.control.binding.v1','approval_message_id':'1562972150455992431','root_id':'OFFLINE_ROOT','parent_ids':['OFFLINE_ROOT','OFFLINE_CHILD']}
  self.j={'schema':'mgs.private.control.slot.request.v1','parent_id':'OFFLINE_CHILD','key':'request:offline','kind':'vps_request','mime':'application/json','name':'offline.json','size':24,'sha256':'a'*64}
 def test_exact_json_slot_accepted(self):self.assertTrue(c.validate_request(self.j,self.binding))
 def test_foreign_media_parent_kind_and_digest_rejected(self):
  for k,v in [('parent_id','FOREIGN'),('kind','delete'),('mime','video/mp4'),('sha256','invalid'),('size',c.MAX_BYTES+1),('name','../../escape'),('key',"x' and 'x")]:
   j=copy.deepcopy(self.j);j[k]=v
   with self.subTest(k=k),self.assertRaises(c.b.ArchiveError):c.validate_request(j,self.binding)
 def test_unapproved_binding_rejected(self):
  self.binding['approval_message_id']='different'
  with self.assertRaises(c.b.ArchiveError):c.validate_request(self.j,self.binding)
 def test_stock_snapshot_is_json_only_and_parent_bounded(self):
  j={**self.j,'kind':'stock_layout_snapshot'};self.assertTrue(c.validate_request(j,self.binding))
  with self.assertRaises(c.b.ArchiveError):c.validate_request({**j,'parent_id':'FOREIGN'},self.binding)
  with self.assertRaises(c.b.ArchiveError):c.validate_request({**j,'mime':'video/mp4'},self.binding)
if __name__=='__main__':unittest.main()
