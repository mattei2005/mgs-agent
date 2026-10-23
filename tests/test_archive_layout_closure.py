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
 def test_get500_retries_without_mutation(self):
  d=b.Drive.__new__(b.Drive);d.base='https://www.googleapis.com/drive/v3/';d.token='fixture';d.api_json=Mock(side_effect=[(500,{}),(200,{'id':'same'})])
  with patch.object(b.time,'sleep') as sleep:
   self.assertEqual(d.api('GET','files/same'),{'id':'same'});self.assertEqual(d.api_json.call_count,2);sleep.assert_called_once_with(1)
 def test_mutations500_never_replayed(self):
  for method in ['POST','PATCH']:
   d=b.Drive.__new__(b.Drive);d.base='https://www.googleapis.com/drive/v3/';d.token='fixture';d.api_json=Mock(return_value=(500,{}))
   with self.assertRaises(b.ArchiveError):d.api(method,'files',payload={})
   self.assertEqual(d.api_json.call_count,1)
 def test_read500_attempts_bounded(self):
  d=b.Drive.__new__(b.Drive);d.base='https://www.googleapis.com/drive/v3/';d.token='fixture';d.api_json=Mock(return_value=(500,{}))
  with patch.object(b.time,'sleep'),self.assertRaises(b.ArchiveError):d.api('GET','files')
  self.assertEqual(d.api_json.call_count,3)
 def test_folder_ownership_propagation_no_move_replay(self):
  owned={'id':'x','owners':[{'emailAddress':b.ACCOUNT,'permissionId':b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT]}]}
  with patch.object(layout,'owned_inventory',side_effect=[{}, {'x':owned}]),patch.object(b,'atomic_json'),patch.object(layout.time,'sleep') as sleep:
   self.assertEqual(layout.propagated_inventory(Mock(),{'x'})['x'],owned);sleep.assert_called_once_with(15)
 def test_folder_ownership_wait_is_bounded(self):
  with patch.object(layout,'owned_inventory',return_value={}),patch.object(b,'atomic_json'),self.assertRaises(b.ArchiveError):layout.propagated_inventory(Mock(),{'x'},0)
 def test_unknown_operation_stock_folder_rejected(self):
  with patch.object(b,'read_json',return_value={'slots':[{'operation':'SHEIN_US_EN'}]}),self.assertRaises(b.ArchiveError):stock.destination_folder(Mock(),Mock(),Mock(),{'relativeParent':['UNKNOWN','VID','01_READY']})
 def test_acl_gate_rejects_without_explicit_confirmation(self):
  proposal={'action':'restore_same_inherited_upload_roles_after_parent_move','target_id':loc.UPLOAD}
  with patch.object(b,'read_json',side_effect=[proposal,{'approved':False}]),self.assertRaisesRegex(b.ArchiveError,'SHARING_CONFIRMATION_REQUIRED'):layout.require_upload_access_confirmation()
 def test_acl_gate_rejects_different_approver(self):
  proposal={'action':'restore_same_inherited_upload_roles_after_parent_move','target_id':loc.UPLOAD}
  approval={'approved':True,'author_id':'other','thread_id':'1562078493498540042','confirmation_message_id':'reply','proposal_sha256':layout.ba.sha(proposal)}
  with patch.object(b,'read_json',side_effect=[proposal,approval]),self.assertRaises(b.ArchiveError):layout.require_upload_access_confirmation()
 def test_acl_gate_exact_proposal_and_rodolfo_required(self):
  proposal={'action':'restore_same_inherited_upload_roles_after_parent_move','target_id':loc.UPLOAD}
  approval={'approved':True,'author_id':'344196393512075265','thread_id':'1562078493498540042','confirmation_message_id':'reply','proposal_sha256':layout.ba.sha(proposal)}
  with patch.object(b,'read_json',side_effect=[proposal,approval]):self.assertEqual(layout.require_upload_access_confirmation(),(proposal,approval))
 def test_acl_gate_cannot_make_move_without_approval(self):
  with patch.object(layout,'require_upload_access_confirmation',side_effect=b.ArchiveError('missing')),patch.object(layout,'move_once') as move:
   with self.assertRaises(b.ArchiveError):layout.move_upload_preserving_access(Mock(),Mock(),Mock(),{})
   move.assert_not_called()
 def test_acl_group_or_public_not_accepted(self):
  for kind in ['anyone','domain','group']:
   with self.assertRaises(b.ArchiveError):layout.acl_identity([{'type':kind,'id':'id','emailAddress':'x','role':'writer'}])
 def test_scoped_inventory_requires_exact_parents(self):
  d=Mock()
  with self.assertRaisesRegex(b.ArchiveError,'EXACT_PARENT_SCOPE'):layout.owned_inventory(d,[])
  d.api.assert_not_called()
 def test_explicit_expected_folder_rename_only(self):
  before={'id':'f','name':'old','mimeType':b.FOLDER,'parents':['p'],'version':'1','trashed':False}
  after={**before,'name':'retired','version':'2','parents':['q']}
  self.assertTrue(layout.unchanged(before,after,parent=['q'],expected_name='retired'))
  with self.assertRaises(b.ArchiveError):layout.unchanged(before,{**after,'properties':{'injected':'true'}},parent=['q'],expected_name='retired')
 def upload_move_fixture(self,*,deny=False,wrong_id=False):
  who={'id':'0001','emailAddress':'newnicolasholanda@gmail.com','type':'user','role':'fileOrganizer','permissionDetails':[{'inherited':True,'inheritedFrom':b.SOURCE_ROOT,'role':'fileOrganizer'}]}
  before=[who];state={'rows':before};d=Mock();owner=Mock();journal=Mock()
  def move(o,sa,j,fid,old,new):
   state['rows']=[] if new==b.SOURCE_DRIVE else before
   return {'id':loc.UPLOAD,'parents':[new]}
  def rpc(method,path,params,payload):
   self.assertEqual(method,'POST');self.assertEqual(path,'files/'+loc.UPLOAD+'/permissions');self.assertEqual(params['sendNotificationEmail'],'false');self.assertEqual(payload['role'],who['role']);self.assertEqual(payload['emailAddress'],who['emailAddress'])
   if deny:raise b.ArchiveError('FIXTURE_PERMISSION_DENIED')
   state['rows']=[{**who,'permissionDetails':[{'inherited':False,'role':'fileOrganizer'}]}]
   return {**who,'id':'other' if wrong_id else who['id']}
  d.api.side_effect=rpc
  with patch.object(layout,'require_upload_access_confirmation',return_value=({'permissions_before':before},{'confirmation_message_id':'approved-fixture'})),patch.object(b,'read_json',side_effect=lambda p,default=None:default),patch.object(b,'atomic_json'),patch.object(layout.t,'Journal',return_value=journal),patch.object(layout,'detailed_permissions',side_effect=lambda sa,fid:state['rows']),patch.object(layout,'move_once',side_effect=move) as mover:
   if deny or wrong_id:
    with self.assertRaises(b.ArchiveError):layout.move_upload_preserving_access(owner,d,journal,{'upload_permissions':before})
    self.assertEqual(state['rows'],before);self.assertEqual(mover.call_count,2)
   else:
    result=layout.move_upload_preserving_access(owner,d,journal,{'upload_permissions':before});self.assertTrue(result['same_existing_permission_ids_and_roles']);self.assertEqual(result['new_principals_added'],0);self.assertEqual(mover.call_count,1)
 def test_same_existing_upload_role_restored_after_move(self):self.upload_move_fixture()
 def test_denied_upload_restore_rolls_back_parent_and_access(self):self.upload_move_fixture(deny=True)
 def test_permission_response_identity_drift_rolls_back(self):self.upload_move_fixture(wrong_id=True)
if __name__=='__main__':unittest.main()
