"""Metadata-only version reconciliation; no external writes in tests."""
import copy,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from unittest.mock import Mock,patch
import ares_flat_intake as f

class VersionProofTests(unittest.TestCase):
 def setUp(self):
  self.old={'id':'source_12345678','name':'file.mp4','mimeType':'video/mp4','parents':[f.UPLOAD],'driveId':f.b.SOURCE_DRIVE,'size':'42','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'createdTime':'2026-11-13T18:55:00Z','trashed':False,'version':'9'}
  self.native={**self.old,'version':'11','capabilities':{'canEdit':True,'canDownload':True},'permissions':[{'type':'user','role':'organizer','emailAddress':'internal@example.test'}]}
  self.batch={'flat_request_id':'a'*32,'batch_id':'b'*32}
  self.source={'version':'11'}
  self.d=Mock();self.d.meta.side_effect=lambda fid:copy.deepcopy(self.native)
  self.d.hashes.return_value={'size':'42','md5':'a'*32,'sha256':'b'*64}
 def verify(self):return f.verify_version_advance(self.d,self.batch,self.source,self.old,self.native)
 def test_metadata_only_advance_proof_no_snapshot_rewrite(self):
  before=copy.deepcopy(self.old)
  with patch.object(f.b,'read_json',return_value=None),patch.object(f.b,'atomic_json') as save:
   self.assertTrue(self.verify());proof=save.call_args.args[1]
   self.assertEqual(proof['registered_version'],'9');self.assertEqual(proof['accepted_version'],'11');self.assertEqual(proof['remote_writes'],0)
   self.assertEqual(self.old,before);self.d.hashes.assert_called_once();self.d.meta.assert_called_once()
 def test_stale_batch_rejected(self):
  self.source['version']='10'
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_backward_version_rejected(self):
  self.old['version']='12'
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_invalid_version_rejected(self):
  self.old['version']='9x'
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_identity_content_and_ancestry_changes_rejected(self):
  for key,value in [('id','another_id'),('name','changed.mp4'),('mimeType','image/png'),('parents',['another_parent']),('driveId','another_drive'),('size','43'),('md5Checksum','c'*32),('sha256Checksum','c'*64),('createdTime','changed'),('trashed',True)]:
   with self.subTest(key=key):
    old=self.native;self.native={**old,key:value}
    with self.assertRaises(f.FlatIntakeError):self.verify()
    self.native=old
 def test_reference_property_change_rejected(self):
  self.native['properties']={'reference_only':'true'}
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_public_access_rejected(self):
  self.native['permissions']=[{'type':'anyone','role':'reader'}]
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_missing_capability_rejected(self):
  self.native['capabilities']['canDownload']=False
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_missing_registered_sha_rejected(self):
  self.old.pop('sha256Checksum');self.native.pop('sha256Checksum')
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_full_stream_mismatch_rejected(self):
  self.d.hashes.return_value['sha256']='c'*64
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_metadata_or_acl_drift_during_read_rejected(self):
  self.d.meta.side_effect=lambda fid:{**self.native,'permissions':[]}
  with self.assertRaises(f.FlatIntakeError):self.verify()
 def test_proof_collision_rejected(self):
  with patch.object(f.b,'read_json',return_value={'wrong':'proof'}),patch.object(f.b,'atomic_json') as save:
   with self.assertRaises(f.FlatIntakeError):self.verify()
   save.assert_not_called()
 def test_proof_replay_does_not_rewrite(self):
  with patch.object(f.b,'read_json',return_value=None),patch.object(f.b,'atomic_json') as save:
   self.verify();proof=save.call_args.args[1]
  with patch.object(f.b,'read_json',return_value=proof),patch.object(f.b,'atomic_json') as save:
   self.assertTrue(self.verify());save.assert_not_called()

 def integration(self,native=None,registered=None,source_version=None,human='same'):
  native=copy.deepcopy(native or self.native);old=copy.deepcopy(registered or self.old)
  c={'request_id':'a'*32,'operation':'SHEIN_US_EN','manager_code':'g005','manager_name':'Kelly','destination_mode':'common','requested_by_discord_id':'1291113428982693940','request_message_id':'1570875079363919935','request_channel_id':'1516887105543077949','native_human_source':{'body_sha256':'same'},'sources':[old]}
  s=f.descriptor(native,c)
  if source_version:s['version']=source_version
  batch=f.make_batch([s],set(),4)
  self.d.meta.side_effect=lambda fid:copy.deepcopy(native)
  with patch.object(f,'registered_operations',return_value={'SHEIN_US_EN'}),patch.object(f,'human_source',return_value={'body_sha256':human}),patch.object(f.b,'read_json',side_effect=lambda p,*a: {'requests':{c['request_id']:c}} if p==f.REQUESTS else None),patch.object(f.b,'atomic_json') as save:
   result=f.validate_new_batch(self.d,batch)
   return result,save.call_count
 def test_claim_integration_accepts_full_byte_proof(self):
  self.assertEqual(self.integration(),(True,1))
 def test_claim_integration_same_version_has_no_supplement(self):
  self.assertEqual(self.integration(registered={**self.old,'version':'11'}),(True,0));self.d.hashes.assert_not_called()
 def test_claim_integration_stale_batch_rejected(self):
  with self.assertRaises(f.FlatIntakeError):self.integration(source_version='10')
 def test_claim_integration_changed_registered_content_rejected(self):
  with self.assertRaises(f.FlatIntakeError):self.integration(registered={**self.old,'md5Checksum':'c'*32})
 def test_claim_integration_changed_human_request_rejected(self):
  with self.assertRaises(f.FlatIntakeError):self.integration(human='changed')

if __name__=='__main__':unittest.main()
