"""Offline exact-control binding and reversible dual-parent reader transition."""
import sys,unittest,copy
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
class ControlScope(unittest.TestCase):
 def setUp(self):
  self.binding={'production_enabled':True,'parent_ids':['NEW'],'folder_map':{'OLD':'NEW'},'migration_pending':False}
  self.meta={'parents':['NEW'],'driveId':None,'trashed':False,'owners':[{'emailAddress':b.ACCOUNT}],'permissions':[]}
 def check(self,meta,parent='NEW'):
  with patch.object(b,'read_json',return_value=self.binding):return b.control_object_scope(meta,parent)
 def test_exact_my_drive_control(self):self.assertTrue(self.check(self.meta))
 def test_wrong_owner_public_parent_and_disabled_rejected(self):
  for key,value in [('owners',[{'emailAddress':'foreign@example.invalid'}]),('permissions',[{'type':'anyone'}]),('parents',['FOREIGN']),('driveId',b.SOURCE_DRIVE)]:
   m=copy.deepcopy(self.meta);m[key]=value
   with self.subTest(key=key):self.assertFalse(self.check(m))
  self.binding['production_enabled']=False;self.assertFalse(self.check(self.meta))
 def test_only_frozen_parent_alias_during_migration(self):
  self.assertFalse(self.check(self.meta,'OLD'));self.binding['migration_pending']=True;self.assertTrue(self.check(self.meta,'OLD'));self.assertFalse(self.check(self.meta,'OTHER'))
 def test_source_control_compatibility_without_migration(self):
  self.assertTrue(self.check({'parents':['OLD'],'driveId':b.SOURCE_DRIVE,'trashed':False},'OLD'))
 def test_queue_lookup_follows_same_key_to_frozen_destination(self):
  d=b.Drive.__new__(b.Drive);d.listing=Mock(side_effect=[[],[{'id':'SAME_ID'}]]);self.binding['migration_pending']=True
  with patch.object(b,'read_json',return_value=self.binding):self.assertEqual(d.one('OLD','request:offline')['id'],'SAME_ID')
  self.assertEqual([x.args[0] for x in d.listing.call_args_list],['OLD','NEW'])
 def test_duplicates_across_transition_block(self):
  d=b.Drive.__new__(b.Drive);d.listing=Mock(side_effect=[[{'id':'ONE'}],[{'id':'TWO'}]]);self.binding['migration_pending']=True
  with patch.object(b,'read_json',return_value=self.binding),self.assertRaises(b.ArchiveError):d.one('OLD','request:offline')
if __name__=='__main__':unittest.main()
