"""Offline namespace relocation proofs; never manufacture production receipts."""
import sys,unittest,copy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_namespace as n
class NamespaceTests(unittest.TestCase):
 def setUp(self):
  self.entry={'sourceId':'sourceOffline001','archiveId':'providerOffline001','sha256':'a'*64,'md5':'b'*32,'size':'10','relativeParent':['SHEIN_US_ES','IMG','01_READY'],'stockShortcutId':'aliasOffline001'}
  self.rec={'source_id':'sourceOffline001','archive_id':'providerOffline001','sha256':'a'*64,'md5':'b'*32,'size':'10','provider_name':'Human label','provider_relative_parent':['SHEIN_US_ES','IMG','JOE - Usados'],'stock_name':'canonical.jpg','stock_id':'aliasOffline001'}
  self.binding={'schema':n.SCHEMA,'authority_message_id':n.AUTHORITY,'phase':'active','archive_root_id':n.b.ARCHIVE_ROOT,'stock_root_id':'stockOffline001','provider_root_id':'physicalOffline001','files':{'providerOffline001':self.rec},'stock_moves':{},'legacy_manager_folders':{}}
 def test_override_requires_same_frozen_identity_and_bytes(self):
  with patch.object(n,'binding',return_value=self.binding):
   self.assertEqual(n.effective_path(self.entry),self.rec['provider_relative_parent'])
   self.entry['sha256']='c'*64
   with self.assertRaises(n.NamespaceError):n.effective_path(self.entry)
 def test_unapproved_binding_rejected(self):
  self.binding['authority_message_id']='arbitrary'
  with self.assertRaises(n.NamespaceError):n.validate_binding(self.binding)
 def test_alias_name_and_provider_label_remain_separate_but_bound(self):
  with patch.object(n,'binding',return_value=self.binding):
   self.assertTrue(n.names_match(self.entry,{'id':'providerOffline001','name':'Human label'},{'id':'aliasOffline001','name':'canonical.jpg'}))
   self.assertFalse(n.names_match(self.entry,{'id':'providerOffline001','name':'Other'},{'id':'aliasOffline001','name':'canonical.jpg'}))
 def test_no_override_preserves_original_name_rule(self):
  with patch.object(n,'binding',return_value=None):
   self.assertTrue(n.names_match(self.entry,{'name':'canonical.jpg'},{'name':'canonical.jpg'}))
   self.assertFalse(n.names_match(self.entry,{'name':'Human label'},{'name':'canonical.jpg'}))
 def test_native_root_owner_parent_and_name_are_required(self):
  class D:
   def meta(d,fid):
    return {'id':fid,'name':'_ARQUIVO_FISICO' if fid=='physicalOffline001' else 'CRIATIVOS','mimeType':n.b.FOLDER,'parents':['stockOffline001'] if fid=='physicalOffline001' else [n.b.ARCHIVE_ROOT],'owners':[{'emailAddress':n.b.ACCOUNT}],'trashed':False,'permissions':[]}
  with patch.object(n,'binding',return_value=self.binding):self.assertEqual(n.provider_root(D()),'physicalOffline001')
  class Bad(D):
   def meta(d,fid):return {**super().meta(fid),'name':'Wrong'}
  with patch.object(n,'binding',return_value=self.binding):
   with self.assertRaises(n.NamespaceError):n.provider_root(Bad())
 def test_unrelated_root_never_becomes_logical_alias(self):
  with patch.object(n,'binding',return_value=self.binding):
   self.assertFalse(n.is_provider_boundary('randomOffline001',n.b.ARCHIVE_ROOT))
   self.assertFalse(n.is_provider_boundary('physicalOffline001','otherRootOffline001'))
 def test_stock_migration_bound_to_source_parent_and_exact_id(self):
  move={'source_id':'sourceOffline001','stock_id':'aliasOffline001','from_parent':'oldManagerOffline001','to_parent':'newManagerOffline001','sha256':'a'*64}
  self.binding['stock_moves']['aliasOffline001']=move
  with patch.object(n,'binding',return_value=self.binding):
   self.assertEqual(n.effective_stock_parent(self.entry,'oldManagerOffline001'),'newManagerOffline001')
   self.assertEqual(n.effective_stock_parent(self.entry,'unrelatedOffline001'),'unrelatedOffline001')
 def test_provider_view_keeps_original_logical_id_and_frozen_proof(self):
  self.rec.update(representation='provider_as_stock',stock_id='providerOffline001',provider_parent_id='usedOffline001')
  entry={**self.entry,'mapping_kind':'historical_verified','archiveParentId':'oldOffline001'}
  with patch.object(n,'binding',return_value=self.binding):
   projected=n.project_historical(entry)
   self.assertEqual(projected['sourceId'],entry['sourceId']);self.assertEqual(projected['approvedStockId'],entry['archiveId']);self.assertEqual(projected['archiveParentId'],'usedOffline001');self.assertEqual(entry['archiveParentId'],'oldOffline001')
 def test_logical_parent_strips_only_verified_physical_boundary(self):
  class D:
   def meta(d,fid):
    names={'physicalOffline001':'_ARQUIVO_FISICO','stockOffline001':'CRIATIVOS','leafOffline001':'01_READY'};parents={'physicalOffline001':'stockOffline001','stockOffline001':n.b.ARCHIVE_ROOT,'leafOffline001':'physicalOffline001'}
    return {'id':fid,'name':names[fid],'mimeType':n.b.FOLDER,'parents':[parents[fid]],'owners':[{'emailAddress':n.b.ACCOUNT}],'trashed':False,'permissions':[]}
  with patch.object(n,'binding',return_value=self.binding):
   self.assertEqual(n.b.Drive.relative_parent(D(),'leafOffline001',n.b.ARCHIVE_ROOT),['01_READY'])
 def test_owner_future_producer_uses_new_verified_root(self):
  import mgs_archive_owner_transport as transport
  class Owner:
   parents=set()
   def meta(d,fid):return {'id':fid,'name':'_ARQUIVO_FISICO' if fid=='physicalOffline001' else 'CRIATIVOS','mimeType':n.b.FOLDER,'parents':['stockOffline001'] if fid=='physicalOffline001' else [n.b.ARCHIVE_ROOT],'owners':[{'emailAddress':n.b.ACCOUNT}],'trashed':False,'permissions':[]}
  owner=Owner()
  with patch.object(n,'binding',return_value=self.binding):self.assertEqual(transport.Engine(owner,{},None,None)._ensure_path([]),'physicalOffline001')
if __name__=='__main__':unittest.main()
