import unittest,tempfile,json,copy
from pathlib import Path
from unittest.mock import patch,Mock
import ares_autonomous_intake as i
import ares_archive_storage as storage
import ares_flat_intake as flat

class FlatExistingArchiveDuplicateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);p=self.root/'data/ares/creative-ops/inventory/assets.jsonl';p.parent.mkdir(parents=True)
  self.row={'asset_id':'existing','asset_drive_id':'old-logical-clean','source_drive_id':'old-source','duplicate_source_drive_ids':['new-source'],'canonical_filename':'clean.png','operation':'SHEIN_US_ES','format':'IMG','metadata_clean':True,'asset_path':'MGS-AGENTS/CRIATIVOS/SHEIN_US_ES/IMG/NICOLAS - Usados/clean.png','original_checksum':'1'*64,'clean_checksum':'2'*64,'source_manager':'Nicolas','ares_eligible':False};p.write_text(json.dumps(self.row)+'\n')
  self.batch={'operation':'SHEIN_US_ES','manager_name':'Nicolas','sources':[{'source_id':'new-source','name':'reupload.png','md5':'a'*32,'size':'12'}]}
  self.drive=Mock();self.drive.token='offline-unit-fixture';self.drive.meta.return_value={'id':'new-source','name':'reupload.png','parents':['current-legacy'],'driveId':i.bridge.SOURCE_DRIVE,'trashed':False};self.drive.relative_parent.return_value=['SHEIN_US_ES','IMG','99_LEGACY'];self.drive.hashes.side_effect=lambda fid:{'size':'12','md5':('a' if fid=='new-source' else 'b')*32,'sha256':('1' if fid=='new-source' else '2')*64}
  self.resolved={'logical_source_id':'old-logical-clean','provider_id':'native-provider-id','provider_metadata':{'id':'native-provider-id','name':'clean.png','parents':['archive-parent'],'size':'12','md5Checksum':'b'*32,'trashed':False}}
 def check(self,resolved):
  with patch.object(i.bridge,'BASE',self.root),patch.object(flat,'policy',return_value={'phase':'active'}),patch.object(storage,'resolve_media',return_value=resolved):return i.verify_completed(self.drive,self.batch,{'existing':[i.protected_fingerprint(self.row)]})
 def test_existing_provider_verified_without_restaging_or_reassignment(self):
  proof=self.check(self.resolved)[0];self.assertEqual(proof['clean_source_id'],'old-logical-clean');self.assertEqual(proof['clean_provider_id'],'native-provider-id');self.assertTrue(proof['existing_archive_duplicate']);self.drive.meta.assert_called_once_with('new-source');self.drive.hashes.assert_any_call('native-provider-id');self.assertEqual(json.loads((self.root/'data/ares/creative-ops/inventory/assets.jsonl').read_text()),self.row)
 def test_provider_identity_substitution_rejected(self):
  with self.assertRaises(i.IntakeError):self.check({**self.resolved,'provider_id':'wrong'})
 def test_existing_protected_reservation_not_overwritten(self):
  self.row['source_manager']='Another';baseline={**self.row,'source_manager':'Nicolas'}
  with self.assertRaises(i.IntakeError):i.verify_reservation(self.row,{'existing':[i.protected_fingerprint(baseline)]},self.batch)
if __name__=='__main__':unittest.main()
