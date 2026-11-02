"""Flat upload registration and consumer gates; all tests are offline."""
import copy,unittest
from unittest.mock import patch
import ares_flat_intake as f

class FlatIntakeTests(unittest.TestCase):
 def setUp(self):
  self.ctx={'request_id':'a'*32,'operation':'SHEIN_US_ES','manager_code':'g006','manager_name':'Nicolas','destination_mode':'exclusive','requested_by_discord_id':'344196393512075265','request_message_id':'123456789012345678','request_channel_id':'1562078493498540042'}
  self.native={'id':'source_12345678','parents':[f.UPLOAD],'mimeType':'image/png','trashed':False,'name':'example.png','size':'42','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'createdTime':'2026-11-02T14:00:00Z','version':'2','driveId':f.b.SOURCE_DRIVE}
 def test_valid_context(self):self.assertTrue(f.validate_context(self.ctx))
 def test_reject_wrong_manager_pair(self):
  with self.assertRaises(f.FlatIntakeError):f.validate_context({**self.ctx,'manager_name':'Joe'})
 def test_reject_unknown_operation(self):
  with self.assertRaises(f.FlatIntakeError):f.validate_context({**self.ctx,'operation':'UNREGISTERED'})
 def test_reject_campaign_destination(self):
  with self.assertRaises(f.FlatIntakeError):f.validate_context({**self.ctx,'destination_mode':'campaign'})
 def test_descriptor_explicit_request(self):
  x=f.descriptor(self.native,self.ctx);self.assertEqual(x['flat_request_id'],'a'*32);self.assertEqual(x['source_parent_id'],f.UPLOAD);self.assertEqual(x['manager_name'],'Nicolas')
 def test_root_name_cannot_set_manager(self):
  m={**self.native,'name':'JOE_OTHER_OPERATION.png'};self.assertEqual(f.descriptor(m,self.ctx)['manager_name'],'Nicolas')
 def test_wrong_native_parent(self):
  with self.assertRaises(f.FlatIntakeError):f.descriptor({**self.native,'parents':['another']},self.ctx)
 def test_nonmedia_rejected(self):
  with self.assertRaises(f.FlatIntakeError):f.descriptor({**self.native,'mimeType':'application/zip'},self.ctx)
 def test_batch_does_not_mix_requests(self):
  x=f.descriptor(self.native,self.ctx);y={**x,'source_id':'source_other123','flat_request_id':'b'*32};r=f.make_batch([x,y],set(),4);self.assertEqual(len(r['sources']),1);self.assertEqual(r['scope_type'],'flat_request')
 def test_batch_source_set_stable(self):
  x=f.descriptor(self.native,self.ctx);self.assertEqual(f.make_batch([x],set(),4),f.make_batch([x],set(),4))
 def test_reupload_excluded(self):
  x=f.descriptor(self.native,self.ctx);self.assertIsNone(f.make_batch([x],{x['source_id']},4))
 def test_scope_digest_tamper(self):
  x=f.descriptor(self.native,self.ctx);r=f.make_batch([x],set(),4);r['manager_name']='Joe'
  with self.assertRaises(f.FlatIntakeError):f.validate_batch_identity(r)
if __name__=='__main__':unittest.main()
