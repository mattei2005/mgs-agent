"""Offline fixtures for the three exact labels approved in1567388545205801030."""
import sys,json,copy,hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_stock_labels as labels
import ares_archive_namespace as namespace
IDS=['1lCL6jtet-epeEegi7SKoy80lNve84RyB','1Ey-kRHYngij81oFAkP_UGJYSVw56KL2U','1fHBobxGz9bMe0VOypAI-NMrydJl0EkKR']
class ThreeLabelTests(unittest.TestCase):
 def test_exact_scopes_are_registered_without_overwriting_predecessors(self):
  for sid in IDS:
   with self.subTest(sid=sid):
    value=labels.scope(sid);self.assertIsNotNone(value)
    self.assertEqual(value[1],'1567388545205801030')
  self.assertEqual(labels.scope(labels.SOURCE)[1],labels.AUTHORITY)
  self.assertEqual(labels.scope(labels.DIAMOND_SOURCE)[1],labels.DIAMOND_AUTHORITY)
  self.assertIsNone(labels.scope('unapproved-source'))
 def test_each_scope_rejects_authority_bytes_identity_label_target_and_parent_drift(self):
  with tempfile.TemporaryDirectory() as root,patch.object(labels,'JOE_HOME',Path(root)):
   for sid in IDS:
    with self.subTest(sid=sid):
     home,auth,alias,provider,jid,label,canonical=labels.scope(sid)
     entry=dict(zip(labels.FIELDS,[sid,provider,alias,jid,'fixture-lineage','c'*32,'a'*64,'20']))
     rec={'identity':labels.identity(entry),'stock_name':label,'provider_name':canonical,'catalogue_name':canonical,'provider_parents':['fixture-parent']}
     proof={'schema':'mgs.archive.stock.label.proof.v1','authority_message_id':auth,'native_verified':True,'record':rec,'provider_hashes':{k:entry[k] for k in ['size','md5','sha256']},'ack_verified':True}
     def save(authority=auth):
      labels.b.atomic_json(home/'native-proof.json',proof)
      labels.b.atomic_json(home/'binding.json',{'schema':'mgs.archive.stock.label.binding.v1','phase':'active','authority_message_id':authority,'proof_sha256':hashlib.sha256(labels.b.canonical(proof)).hexdigest()})
     physical={'id':provider,'name':canonical,'parents':['fixture-parent']};stock={'id':alias,'name':label,'shortcutDetails':{'targetId':provider},'properties':{'mgsArchiveLogicalSource':sid}}
     save();self.assertTrue(labels.names_match(entry,physical,stock));self.assertEqual(namespace.catalogue_name(entry,stock),canonical)
     self.assertEqual(namespace.native_stock_label(sid,alias,canonical),label)
     for key in labels.FIELDS[1:]:
      with self.assertRaises(labels.b.ArchiveError):labels.record({**entry,key:'drift'})
     self.assertFalse(labels.names_match(entry,physical,{**stock,'name':'unapproved rename'}))
     self.assertFalse(labels.names_match(entry,physical,{**stock,'shortcutDetails':{'targetId':'wrong'}}))
     self.assertFalse(labels.names_match(entry,{**physical,'parents':['other']},stock))
     save(labels.AUTHORITY)
     with self.assertRaises(labels.b.ArchiveError):labels.record(entry)
     save();proof['provider_hashes']['size']='21';save()
     with self.assertRaises(labels.b.ArchiveError):labels.record(entry)
     proof['provider_hashes']['size']='20';proof['ack_verified']=False;save()
     with self.assertRaises(labels.b.ArchiveError):labels.record(entry)
 def test_unregistered_label_has_no_generic_allowlist(self):
  self.assertIsNone(labels.record(source_id='outside'))
  self.assertIsNone(labels.native_stock_label('outside','outside','outside'))
if __name__=='__main__':unittest.main()
