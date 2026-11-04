"""Exact remainder of the authorized frozen sweep; no global name bypass."""
import sys,copy,json,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
import mgs_archive_source_names as names
import test_archive_source_names as fixtures

class RemainingProofTests(unittest.TestCase):
 def test_remaining_pin_is_separate_from_original(self):
  self.assertEqual(names.PROOF_SHA256,'f8ad6a2ef6d8914579d5c6969b8454126b8f25f921d487211fd54ffafc82ab96')
  self.assertEqual(names.REMAINING_PROOF_SHA256,'4612911a903d2888689bc09e0c0e82030ca38972bcf9608913704c4e6ffdeda4')
 def test_remaining_exact_record_uses_separate_native_proof(self):
  d,m,a,j,p,c,folders=fixtures.SourceNamesTests().fixture()
  with patch.object(names,'load',side_effect=[({'records':{}},{}),(p,c)]) as load,patch.object(b,'control_object_scope',return_value=True):
   self.assertTrue(names.verify(d,m,a,j,{'processing_destination_id':'root'}))
   self.assertEqual(load.call_args.args,(names.HOME/'remaining-frozen-sources',names.REMAINING_PROOF_SHA256))
 def test_unknown_source_is_not_admitted_by_remaining_proof(self):
  d,m,a,j,p,c,folders=fixtures.SourceNamesTests().fixture();p['records'].clear()
  with patch.object(names,'load',side_effect=[({'records':{}},{}),(p,c)]),patch.object(b,'control_object_scope',return_value=True):
   self.assertFalse(names.verify(d,m,a,j,{'processing_destination_id':'root'}))
 def test_changed_remaining_native_proof_rejected(self):
  d,m,a,j,p,c,folders=fixtures.SourceNamesTests().fixture();d.raw.return_value=b'{}';d.raw.side_effect=None
  with patch.object(names,'load',side_effect=[({'records':{}},{}),(p,c)]),patch.object(b,'control_object_scope',return_value=True):
   with self.assertRaisesRegex(b.ArchiveError,'SOURCE_NAMES_NATIVE_PROOF'):names.verify(d,m,a,j,{'processing_destination_id':'root'})
 def test_remaining_load_rejects_wrong_pin_and_authority(self):
  proof={'schema':'mgs.archive.source.ancestry.name.proof.v1','authority_message_id':names.AUTHORITY,'author_discord_id':'344196393512075265','native_verified':True,'records':{}}
  digest=names.sha(proof);binding={'schema':'mgs.archive.source.ancestry.name.binding.v1','authority_message_id':names.AUTHORITY,'phase':'active','proof_sha256':digest}
  def read(path,default):return proof if path.name=='native-proof.json' else binding
  with patch.object(b,'read_json',side_effect=read):
   self.assertEqual(names.load(Path('fixture'),digest),(proof,binding))
   with self.assertRaisesRegex(b.ArchiveError,'SOURCE_NAMES_BINDING'):names.load(Path('fixture'),'0'*64)
   binding['authority_message_id']='other'
   with self.assertRaisesRegex(b.ArchiveError,'SOURCE_NAMES_BINDING'):names.load(Path('fixture'),digest)
 def test_remaining_record_still_rejects_job_identity_drift(self):
  d,m,a,j,p,c,folders=fixtures.SourceNamesTests().fixture();j['jobId']='not-frozen'
  with patch.object(names,'load',side_effect=[({'records':{}},{}),(p,c)]),patch.object(b,'control_object_scope',return_value=True):
   with self.assertRaisesRegex(b.ArchiveError,'SOURCE_NAMES_FROZEN_JOB'):names.verify(d,m,a,j,{'processing_destination_id':'root'})
if __name__=='__main__':unittest.main()
