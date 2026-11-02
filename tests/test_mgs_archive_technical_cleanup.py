"""Offline exact-manifest trash gates; never construct real credentials."""
import copy
import unittest
from unittest.mock import patch
import mgs_archive_technical_cleanup as c

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.m={'id':'folder','name':'f','mimeType':c.b.FOLDER,'parents':['parent'],'version':'2','trashed':False,'owners':[{'emailAddress':c.b.ACCOUNT,'permissionId':c.b.PUBLISHER_PERMISSION_IDS[c.b.ACCOUNT]}],'permissions':[]}
    def test_manifest_real_digest(self):
        p=c.load_plan(); self.assertEqual(len(p['targets']),30)
    def test_manifest_reject_added_scope(self):
        p=c.load_plan();p['targets'].append(self.m)
        with self.assertRaises(c.CleanupError):c.validate_plan(p)
    def test_manifest_reject_action(self):
        p=c.load_plan();p['action']='permanent_delete'
        with self.assertRaises(c.CleanupError):c.validate_plan(p)
    def test_confirmation_reject_wrong_user(self):
        with self.assertRaises(c.CleanupError):c.validate_confirmation({'confirmation_message_id':c.CONFIRM,'question_message_id':c.QUESTION,'user_id':'wrong','plan_sha256':c.DIGEST})
    def test_confirmation_reject_wrong_digest(self):
        with self.assertRaises(c.CleanupError):c.validate_confirmation({'confirmation_message_id':c.CONFIRM,'question_message_id':c.QUESTION,'user_id':c.USER,'plan_sha256':'0'*64})
    def test_confirmation_accept(self):
        self.assertTrue(c.validate_confirmation({'confirmation_message_id':c.CONFIRM,'question_message_id':c.QUESTION,'user_id':c.USER,'plan_sha256':c.DIGEST}))
    def test_native_cas(self):self.assertTrue(c.check_metadata(self.m,self.m))
    def test_reject_parent_drift(self):
        n={**self.m,'parents':['other']}
        with self.assertRaises(c.CleanupError):c.check_metadata(n,self.m)
    def test_reject_version_drift(self):
        with self.assertRaises(c.CleanupError):c.check_metadata({**self.m,'version':'3'},self.m)
    def test_reject_owner_drift(self):
        with self.assertRaises(c.CleanupError):c.check_metadata({**self.m,'owners':[]},self.m)
    def test_post_trash_preserves_content(self):
        self.assertTrue(c.check_metadata({**self.m,'trashed':True,'version':'3'},self.m,after=True))
    def test_post_trash_requires_true(self):
        with self.assertRaises(c.CleanupError):c.check_metadata(self.m,self.m,after=True)
    def test_folder_reject_new_child(self):
        with self.assertRaises(c.CleanupError):c.check_children([{'id':'unexpected'}],{'known'})
    def test_folder_accept_frozen_children(self):self.assertTrue(c.check_children([{'id':'known'}],{'known'}))
    def test_bottom_up(self):
        parent={**self.m,'id':'p','parents':['outside']};child={**self.m,'id':'c','parents':['p']}
        self.assertEqual([x['id'] for x in c.bottom_up([parent,child])],['c','p'])
    def test_cycle_rejected(self):
        with self.assertRaises(c.CleanupError):c.bottom_up([{**self.m,'id':'a','parents':['a']}])
    def test_unknown_id_never_mutates(self):
        with patch.object(c,'native_meta') as meta,patch.object(c.urllib.request,'urlopen') as http:
            with self.assertRaises(c.CleanupError):c.trash_once(None,'arbitrary',self.m,{}, {})
            meta.assert_not_called();http.assert_not_called()
    def test_generic_owner_remains_forbidden(self):
        with self.assertRaises(c.t.TransportError):c.t.OwnerDrive.__new__(c.t.OwnerDrive).api('PATCH','files/arbitrary',payload={'trashed':True})

if __name__=='__main__':unittest.main()
