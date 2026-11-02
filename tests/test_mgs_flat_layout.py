import unittest
import mgs_flat_layout as f

class FlatGateTests(unittest.TestCase):
 def test_role_equivalence(self):
  self.assertEqual(f.access_role('fileOrganizer'),'writer');self.assertEqual(f.access_role('organizer'),'writer');self.assertEqual(f.access_role('reader'),'reader')
 def test_unknown_role_closed(self):
  with self.assertRaises(f.FlatError):f.access_role('unknown')
 def test_no_new_principal(self):
  before=[{'id':'a','type':'user','emailAddress':'a@example.invalid','role':'writer'}]
  self.assertEqual(f.allowed_grant(before,'a'),{'type':'user','emailAddress':'a@example.invalid','role':'writer'})
  with self.assertRaises(f.FlatError):f.allowed_grant(before,'b')
 def test_public_principal_rejected(self):
  with self.assertRaises(f.FlatError):f.allowed_grant([{'id':'a','type':'anyone','role':'reader'}],'a')
 def test_actual_reader_not_writer(self):
  self.assertFalse(f.same_access([{'id':'a','type':'user','emailAddress':'a@x','role':'writer'}],[{'id':'a','type':'user','emailAddress':'a@x','role':'reader'}]))
 def test_owner_role_normalized(self):
  self.assertTrue(f.same_access([{'id':'a','type':'user','emailAddress':'a@x','role':'organizer'}],[{'id':'a','type':'user','emailAddress':'a@x','role':'owner'}]))
 def test_extra_principal_not_equal(self):
  a=[{'id':'a','type':'user','emailAddress':'a@x','role':'writer'}];self.assertFalse(f.same_access(a,a+[{'id':'b','type':'user','emailAddress':'b@x','role':'writer'}]))
 def test_authority_required(self):
  with self.assertRaises(f.FlatError):f.validate_authority({})
 def test_authority_valid(self):
  self.assertTrue(f.validate_authority({'redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','author_id':'344196393512075265','thread_id':'1562078493498540042'}))
class FlatMoveBoundaryTests(unittest.TestCase):
 def setUp(self):
  from unittest.mock import patch
  self.patcher=patch.object(f,'authority',return_value={});self.patcher.start();self.addCleanup(self.patcher.stop)
  self.plan={'schema':'mgs.flat.layout.move.plan.v1','access_confirmation':'1566825959645253764','objects':{'source123':{'id':'source123','source_parent':'old','destination_parent':f.CONTROL}},'allowed_destination_ids':[f.CONTROL]};self.plan['plan_sha256']=f.sha(self.plan)
 def test_exact_manifest(self):self.assertEqual(f.validate_move(self.plan,'source123')['source_parent'],'old')
 def test_unknown_id_closed(self):
  with self.assertRaises(f.FlatError):f.validate_move(self.plan,'unknown123')
 def test_digest_drift_closed(self):
  self.plan['allowed_destination_ids'].append('foreign')
  with self.assertRaises(f.FlatError):f.validate_move(self.plan,'source123')
 def test_protected_root_closed(self):
  self.plan['objects'][f.UPLOAD]={'id':f.UPLOAD,'source_parent':'old','destination_parent':f.CONTROL};self.plan['plan_sha256']=f.sha({k:v for k,v in self.plan.items() if k!='plan_sha256'})
  with self.assertRaises(f.FlatError):f.validate_move(self.plan,f.UPLOAD)
 def test_delete_method_closed(self):
  with self.assertRaises(f.FlatError):f.rpc_once(None,'DELETE','files/source123',{},None)

if __name__=='__main__':unittest.main()
