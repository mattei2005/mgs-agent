"""Standard manager paths: offline only, no auth/network/production writes."""
import copy, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_manager_storage_standard as s

class StandardTests(unittest.TestCase):
 def setUp(self):
  self.slot={'operation':'SHEIN_US_EN','format':'VID','manager_code':'g006','manager_name':'Nicolas','exclusive_id':'exclusiveOffline001','used_id':'usedOffline001','parent_id':'vidOffline001','operation_id':'opOffline001','ready_id':'readyOffline001'}
  self.p={'schema':s.SCHEMA,'authority_message_id':s.AUTHORITY,'phase':'active','stock_root_id':'stockOffline001','slots':[self.slot]}
 def test_normalized_manager_is_registered_not_arbitrary(self):
  self.assertEqual(s.manager_code('NICOLAS'),'g006');self.assertEqual(s.manager_code('ICARO'),'g001')
  with self.assertRaises(s.StandardError):s.manager_code('random')
 def test_explicit_paths(self):
  self.assertEqual(s.slot_path(self.slot,'exclusive'),['SHEIN_US_EN','VID','NICOLAS - Exclusivos'])
  self.assertEqual(s.slot_path(self.slot,'used'),['SHEIN_US_EN','VID','NICOLAS - Usados'])
 def test_unapproved_policy_is_rejected(self):
  self.p['authority_message_id']='other'
  with self.assertRaises(s.StandardError):s.validate_policy(self.p)
 def test_duplicate_folder_binding_rejected(self):
  self.p['slots'].append(copy.deepcopy(self.slot))
  with self.assertRaises(s.StandardError):s.validate_policy(self.p)
 def test_cross_operation_does_not_select_other_pool(self):
  with patch.object(s,'policy',return_value=self.p):
   self.assertEqual(s.destination('SHEIN_US_EN','VID','Nicolas'),'exclusiveOffline001')
   with self.assertRaises(s.StandardError):s.destination('SHEIN_US_ES','VID','Nicolas')
 def test_one_selected_asset_only_moves_after_complete_assignment(self):
  with self.assertRaises(s.StandardError):s.validate_assignment({'campaign_id':'123','ad_id':'456'})
  s.validate_assignment({'campaign_id':'123','adset_id':'234','ad_id':'345','creative_id':'456'})
 def test_same_ids_on_used_transition_and_replay(self):self.roundtrip(False)
 def test_lost_patch_response_is_not_replayed(self):self.roundtrip(True)
 def roundtrip(self,lost):
  with tempfile.TemporaryDirectory() as tmp:
   row={'asset_id':'assetOffline001','asset_drive_id':'logicalOffline001','clean_checksum':'a'*64,'manager_media_folder_id':'exclusiveOffline001'}
   asset={'asset_drive_id':'logicalOffline001','ready_parent_id':'exclusiveOffline001','drive_md5':'b'*32}
   assignment={'campaign_id':'123','adset_id':'234','ad_id':'345','creative_id':'456'}
   class D:
    parent='exclusiveOffline001';calls=0
    def api(d,method,path,params,payload):
     assert method=='PATCH' and path=='files/stockAliasOffline001';d.parent=params['addParents'];d.calls+=1
     if lost and d.calls==1:raise TimeoutError('ambiguous offline response')
   d=D()
   def record(*args):return {'id':'logicalOffline001','stock_file_id':'stockAliasOffline001','parents':[d.parent],'sha256Checksum':'a'*64,'md5Checksum':'b'*32,'name':'SHEIN_US_EN_VID_OFFLINE_NV_001.mp4'}
   with patch.object(s,'policy',return_value=self.p),patch.object(s,'find_slot',return_value=(self.slot,'exclusive')),patch.object(s,'validate_folder'),patch.object(s.storage,'resolve_media',side_effect=record),patch.object(s,'HOME',Path(tmp)),patch('urllib.request.urlopen',side_effect=AssertionError('OFFLINE_NETWORK_FORBIDDEN')):
    if lost:
     with self.assertRaises(TimeoutError):s.mark_used(d,row,asset,assignment,'requestOffline001')
    one=s.mark_used(d,row,asset,assignment,'requestOffline001');two=s.mark_used(d,row,asset,assignment,'requestOffline001')
    self.assertEqual(d.calls,1);self.assertEqual(one['folder_id'],'usedOffline001');self.assertEqual(one,two)
    self.assertEqual(row['asset_drive_id'],'logicalOffline001')
 def test_unknown_manager_does_not_get_folder(self):
  with patch.object(s,'policy',return_value=self.p):
   with self.assertRaises(s.StandardError):s.destination('SHEIN_US_EN','VID','Joe')

if __name__=='__main__':unittest.main()
