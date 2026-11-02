"""Offline exact-manifest trash gates; never construct real credentials."""
import copy
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
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

    def mutation_fixture(self):
        plan=c.load_plan();expected=copy.deepcopy(plan['targets'][0]);fid=expected['id']
        state={'intents':{fid:{'status':'prepared','plan_sha256':c.DIGEST}}}
        actual={**expected,'capabilities':{'canTrash':True}}
        return plan,expected,fid,state,actual

    def test_positive_single_patch_exact_payload(self):
        plan,expected,fid,state,actual=self.mutation_fixture()
        owner=SimpleNamespace(base='https://fixture.invalid/',token='fixture-not-credential')
        with patch.object(c,'validate_confirmation',return_value=True),patch.object(c,'native_meta',return_value=actual),patch.object(c,'children',return_value=[]),patch.object(c.b,'atomic_json'),patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'{}')) as http:
            c.trash_once(owner,fid,expected,plan,state)
            self.assertEqual(http.call_count,1)
            req=http.call_args.args[0]
            self.assertEqual(req.method,'PATCH');self.assertEqual(req.data,b'{"trashed":true}')
            self.assertIn('/files/'+fid+'?',req.full_url)
            self.assertEqual(state['intents'][fid]['status'],'submitted')

    def test_ambiguous_mutation_never_replayed(self):
        plan,expected,fid,state,actual=self.mutation_fixture()
        owner=SimpleNamespace(base='https://fixture.invalid/',token='fixture-not-credential')
        with patch.object(c,'validate_confirmation',return_value=True),patch.object(c,'native_meta',return_value=actual),patch.object(c,'children',return_value=[]),patch.object(c.b,'atomic_json'),patch.object(c.urllib.request,'urlopen',side_effect=TimeoutError) as http:
            with self.assertRaises(TimeoutError):c.trash_once(owner,fid,expected,plan,state)
            with self.assertRaises(c.CleanupError):c.trash_once(owner,fid,expected,plan,state)
            self.assertEqual(http.call_count,1)

    def test_nonempty_folder_no_patch(self):
        plan,expected,fid,state,actual=self.mutation_fixture()
        with patch.object(c,'validate_confirmation',return_value=True),patch.object(c,'native_meta',return_value=actual),patch.object(c,'children',return_value=[{'id':'unexpected'}]),patch.object(c.urllib.request,'urlopen') as http:
            with self.assertRaises(c.CleanupError):c.trash_once(None,fid,expected,plan,state)
            http.assert_not_called()

    def test_missing_native_capability_no_patch(self):
        plan,expected,fid,state,actual=self.mutation_fixture();actual['capabilities']['canTrash']=False
        with patch.object(c,'validate_confirmation',return_value=True),patch.object(c,'native_meta',return_value=actual),patch.object(c.urllib.request,'urlopen') as http:
            with self.assertRaises(c.CleanupError):c.trash_once(None,fid,expected,plan,state)
            http.assert_not_called()

    def test_disposition_does_not_admit_production(self):
        self.assertIsNone(c.retired_canary_proof(None,{'jobId':'production','kind':'lineage'},{},{}))

    def test_disposition_rejects_wrong_canary(self):
        self.assertIsNone(c.retired_canary_proof(None,{'jobId':'other','kind':'canary'},{},{}))

    def test_disposition_requires_native_ack(self):
        with self.assertRaises(c.CleanupError):
            c.retired_canary_proof(None,{'jobId':c.CANARY_JOB,'kind':'canary'},{},None)

    def test_disposed_canary_not_cached_or_reverified(self):
        import ares_archive_automation as a
        proof={'record_kind':'mgs.retired.validation.v1'}
        with patch.object(a,'verification_snapshot',return_value={'pending':False,'acked':True,'retired_validation':proof}):
            verify=Mock();state={}
            result=a.reconcile_jobs(None,{},[{'jobId':c.CANARY_JOB}],state,True,verify=verify)
            self.assertEqual(result['blocked'],[]);self.assertEqual(result['verified'],[]);self.assertEqual(result['cached'],[])
            self.assertEqual(result['retired_validation'],[proof]);self.assertEqual(state,{})
            verify.assert_not_called()

if __name__=='__main__':unittest.main()
