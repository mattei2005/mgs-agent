import copy,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_reupload_recovery as r
import ares_archive_storage as storage

def principal(pid,email,role='writer'):return {'id':pid,'type':'user','emailAddress':email,'role':role}
BASE=[principal('sa','mgsagent@mgs-core-prod.iam.gserviceaccount.com'),principal('g','geizianp@gmail.com')]
class ScopeTests(unittest.TestCase):
 def test_frozen_exact_approved_scope(self):
  x=r.frozen();self.assertEqual(len(x),116);self.assertEqual(len({s['asset_id'] for s in x}),73)
 def test_both_actual_approvals_digest_bound_offline(self):self.assertTrue(r.authority(False))
 def test_existing_access_unchanged_needs_no_grant(self):self.assertEqual(r.assert_acl_transition(BASE,BASE),set())
 def test_only_original_geizian_writer_can_be_restored(self):self.assertEqual(r.assert_acl_transition(BASE,BASE[:1]),{'g'})
 def test_new_principal_is_rejected(self):
  with self.assertRaises(r.RecoveryError):r.assert_acl_transition(BASE,BASE+[principal('x','outsider@example.invalid')])
 def test_missing_other_user_is_rejected(self):
  with self.assertRaises(r.RecoveryError):r.assert_acl_transition(BASE,BASE[1:])
 def test_role_change_is_rejected(self):
  with self.assertRaises(r.RecoveryError):r.assert_acl_transition(BASE,[principal('sa',BASE[0]['emailAddress'],'reader'),BASE[1]])
 def test_public_permission_rejected(self):
  with self.assertRaises(Exception):r.assert_acl_transition(BASE,BASE+[{'id':'public','type':'anyone','role':'reader'}])
 def test_inactive_binding_no_alias(self):
  with tempfile.TemporaryDirectory() as d,patch.object(r,'H',pathlib.Path(d)):
   self.assertIsNone(r.mapping('anything'));self.assertEqual(r.stock_aliases(),{})
 def test_unrelated_original_storage_mapping_unchanged(self):
  with patch.object(r,'mapping',return_value=None),patch.object(storage,'historical_enabled',return_value=False):self.assertIsNone(storage.mapping('unrelated',{'mappings':{},'verified_jobs':{}}))
 def test_binding_digest_tampering_rejected(self):
  with tempfile.TemporaryDirectory() as d,patch.object(r,'H',pathlib.Path(d)):
   p={'phase':'active','approval_message_id':r.APPROVAL,'acl_approval_message_id':r.ACL_APPROVAL,'source_manifest_sha256':r.DISP_SHA,'binding_sha256':'wrong'}
   (pathlib.Path(d)/'binding.json').write_text(json.dumps(p))
   with self.assertRaises(r.RecoveryError):r.active_binding()

class CatalogueTests(unittest.TestCase):
 def setUp(self):
  self.entry={'sourceId':'logical-old','archiveId':'provider-new','stockShortcutId':'stock-new','archiveParentId':'provider-parent','stockParentId':r.USED,'name':'SHEIN_US_EN_VID_FREE_TEST_PV_001.mp4','size':'4','md5':'a'*32,'sha256':'b'*64,'representation':'recovered_shortcut','permissions_expected':BASE,'lineageId':'asset-existing'}
  self.pm={'id':'provider-new','name':'old name preserved.mp4','mimeType':'video/mp4','parents':['provider-parent'],'trashed':False,'owners':[{'emailAddress':r.b.ACCOUNT}],'size':'4','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'capabilities':{'canDownload':True}}
  self.sm={'id':'stock-new','name':self.entry['name'],'mimeType':'application/vnd.google-apps.shortcut','parents':[r.USED],'trashed':False,'shortcutDetails':{'targetId':'provider-new'}}
  self.binding={'mappings':{'logical-old':self.entry}}
 def resolve(self):
  def meta(d,fid):return copy.deepcopy(self.pm if fid=='provider-new' else self.sm)
  with patch.object(r,'_binding_remote'),patch.object(r,'file_meta',side_effect=meta),patch.object(r,'acl',return_value=BASE):return r.resolve_entry(object(),self.entry,self.binding)
 def test_logical_id_preserved_actual_ids_separate(self):
  rec=self.resolve();self.assertEqual(rec['id'],'logical-old');self.assertEqual(rec['provider_id'],'provider-new');self.assertEqual(rec['stock_file_id'],'stock-new');self.assertEqual(rec['lineage_id'],'asset-existing')
 def test_content_drift_rejected(self):
  self.pm['sha256Checksum']='c'*64
  with self.assertRaises(r.RecoveryError):self.resolve()
 def test_provider_parent_drift_rejected(self):
  self.pm['parents']=['other-parent']
  with self.assertRaises(r.RecoveryError):self.resolve()
 def test_shortcut_target_drift_rejected(self):
  self.sm['shortcutDetails']['targetId']='other-provider'
  with self.assertRaises(r.RecoveryError):self.resolve()
 def test_stock_destination_drift_rejected(self):
  self.sm['parents']=['other-used-folder']
  with self.assertRaises(r.RecoveryError):self.resolve()
 def test_wrong_owner_rejected(self):
  self.pm['owners']=[{'emailAddress':'someone@example.invalid'}]
  with self.assertRaises(r.RecoveryError):self.resolve()
 def test_no_new_general_move_permission(self):
  rec=self.resolve()
  with self.assertRaises(storage.StorageError):storage.move_stock(rec,'other-parent',r.USED,'unused-token')
 def test_current_stock_projection_preserves_logical_identity(self):
  record=self.resolve()
  with patch.object(storage,'enabled',return_value=True),patch.object(storage.b,'read_json',return_value={'mappings':{}}),patch.object(r,'stock_aliases',return_value={'stock-new':'logical-old'}),patch.object(storage,'resolve_media',return_value=record):
   result=storage.project_stock([{'id':'stock-new','name':self.entry['name']}],'unused-token');self.assertEqual(result[0]['id'],'logical-old')
if __name__=='__main__':unittest.main()
