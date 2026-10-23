import sys,unittest,copy,contextlib,tempfile,json
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
import ares_archive_locations as loc
import mgs_archive_layout_cutover as layout
import mgs_private_stock_transport as stock
class LayoutClosure(unittest.TestCase):
 def binding(self,**kw):
  return {'schema':'mgs.archive.stock.layout.v1','approval_message_id':loc.APPROVAL,'source_drive_id':b.SOURCE_DRIVE,'staging_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'upload_root_id':loc.UPLOAD,'owner':b.ACCOUNT,'stock_root_id':'stock-root-1234','active':True,'same_ids_verified':True,'consumer_canary_verified':True,'acceptance_proof':'proof',**kw}
 def test_descendants_excludes_upload_entire_tree(self):
  rows=[{'id':'a','parents':['root'],'mimeType':b.FOLDER},{'id':'b','parents':['a']},{'id':'upload','parents':['root'],'mimeType':b.FOLDER},{'id':'pending','parents':['upload']}]
  self.assertEqual(set(layout.descendants(rows,'root',['upload'])),{'a','b'})
 def test_descendants_does_not_follow_shortcut(self):
  rows=[{'id':'alias','parents':['root'],'mimeType':'application/vnd.google-apps.shortcut'},{'id':'external','parents':['alias']}]
  self.assertEqual(set(layout.descendants(rows,'root')),{'alias'})
 def test_content_hash_cas(self):
  old={'id':'x','name':'a','version':'1','size':'4','md5Checksum':'old','parents':['p'],'trashed':False}
  with self.assertRaises(b.ArchiveError):layout.unchanged(old,{**old,'md5Checksum':'new'})
 def test_id_cas(self):
  old={'id':'x','version':'1','parents':['p'],'trashed':False}
  with self.assertRaises(b.ArchiveError):layout.unchanged(old,{**old,'id':'y'})
 def test_move_same_id_content_unchanged(self):
  old={'id':'x','version':'1','parents':['old'],'trashed':False}
  self.assertTrue(layout.unchanged(old,{**old,'version':'2','parents':['new']},parent=['new']))
 def test_shortcut_target_preserved(self):
  old={'id':'x','version':'1','parents':['p'],'trashed':False,'shortcutDetails':{'targetId':'a'}}
  with self.assertRaises(b.ArchiveError):layout.unchanged(old,{**old,'shortcutDetails':{'targetId':'b'}})
 def test_canary_not_success_without_real_proof(self):
  v=self.binding(phase='consumer_canary',consumer_canary_verified=False)
  with self.assertRaises(b.ArchiveError):loc.validate(v)
 def test_internal_canary_is_process_scoped(self):
  v=self.binding(phase='consumer_canary',consumer_canary_verified=False)
  with patch.object(b,'read_json',return_value={'control_cutover_in_progress':True}):
   with loc.internal_canary():self.assertIs(loc.validate(v),v)
  with self.assertRaises(b.ArchiveError):loc.validate(v)
 def test_internal_canary_requires_barrier(self):
  with patch.object(b,'read_json',return_value={}):
   with self.assertRaises(b.ArchiveError):
    with loc.internal_canary():pass
 def test_active_requires_same_ids(self):
  with self.assertRaises(b.ArchiveError):loc.validate(self.binding(same_ids_verified=False))
 def test_wrong_owner_or_public_fails(self):
  with patch.object(loc,'active',return_value=self.binding()):
   self.assertFalse(loc.stock_metadata_allowed({'trashed':False,'owners':[{'emailAddress':'other'}]}))
   self.assertFalse(loc.stock_metadata_allowed({'trashed':False,'owners':[{'emailAddress':b.ACCOUNT}],'permissions':[{'type':'anyone'}]}))
 def test_old_drive_not_accepted_as_stock_after_cutover(self):
  with patch.object(loc,'active',return_value=self.binding()):self.assertFalse(loc.stock_metadata_allowed({'trashed':False,'driveId':b.SOURCE_DRIVE}))
 def test_unresolved_move_never_replayed(self):
  journal=Mock();journal.data={'intents':{'move:x':{'binding':{'old_parent':'p','new_parent':'q','new_name':None}}}}
  with patch.object(layout,'native',return_value={'id':'x','parents':['p'],'trashed':False}),patch.object(layout.urllib.request,'urlopen') as rpc:
   with self.assertRaises(b.ArchiveError):layout.move_once(Mock(),Mock(),journal,'x','p','q')
   rpc.assert_not_called()
 def test_landed_move_adopted_same_id(self):
  journal=Mock();journal.data={'intents':{'move:x':{'binding':{'old_parent':'p','new_parent':'q','new_name':None}}}}
  with patch.object(layout,'native',return_value={'id':'x','parents':['q'],'trashed':False}),patch.object(layout.urllib.request,'urlopen') as rpc:
   self.assertEqual(layout.move_once(Mock(),Mock(),journal,'x','p','q')['id'],'x');rpc.assert_not_called()
 def test_relocation_membership_fail_closed(self):
  with patch.object(loc,'active',return_value=self.binding()),patch.object(b,'read_json',return_value={}):
   with self.assertRaises(b.ArchiveError):layout.verify_relocated(Mock(),{}, {'sourceId':'unknown'})
 def test_stock_lane_inactive_no_credentials(self):
  with patch.object(loc,'active',return_value=None),patch.object(stock.t,'OwnerDrive') as owner:
   self.assertEqual(stock.tick()['status'],'inactive');owner.assert_not_called()
 def test_wrong_stock_batch_rejected(self):
  with self.assertRaises(b.ArchiveError):stock.tick(5)
if __name__=='__main__':unittest.main()
