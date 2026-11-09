import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import mgs_flat_consolidation as c

class ResumeCasTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.expected={'id':'source','name':'x.mp4','mimeType':'video/mp4','size':'3','md5Checksum':'md5','sha256Checksum':'sha','createdTime':'t','properties':{},'version':'2','parents':['old'],'trashed':False,'owners':[{'emailAddress':c.b.ACCOUNT}],'permissions':[]}
        self.current={**copy.deepcopy(self.expected),'version':'4'}
        self.record={'metadata_before':self.expected,'destination_parent':'new','permissions_before':[]}
        self.sa=Mock();self.sa.meta.side_effect=lambda fid:copy.deepcopy(self.current)
        self.sa.hashes.return_value={'size':'3','md5':'md5','sha256':'sha'}
        self.journal=c.transport.Journal(self.home/'journal.json')
        self.patches=[patch.object(c.f,'permissions',return_value=[]),patch.object(c.f,'same_access',return_value=True)]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def refresh(self):
        return c.expected_for_move(self.sa,self.journal,self.home,'generation','source',self.record)
    def test_refresh_preserves_frozen_record_and_cas_exact(self):
        frozen=copy.deepcopy(self.record)
        new=self.refresh();self.assertEqual(new['version'],'4');self.assertEqual(self.record,frozen)
        proof=c.b.read_json(self.home/'cas-source-4.json');self.assertEqual(proof['record_sha256'],c.sha(frozen));self.assertTrue(proof['full_streams_verified'])
        self.refresh();self.assertEqual(c.b.read_json(self.home/'cas-source-4.json'),proof)
    def test_no_refresh_for_equal_version(self):
        self.current['version']='2';self.assertEqual(self.refresh(),self.expected);self.sa.hashes.assert_not_called();self.assertFalse(list(self.home.glob('cas-*')))
    def test_refresh_rejects_byte_drift(self):
        self.sa.hashes.return_value['sha256']='changed'
        with self.assertRaises(c.b.ArchiveError):self.refresh()
        self.assertFalse(list(self.home.glob('cas-*')))
    def test_refresh_rejects_content_drift(self):
        self.current['name']='changed.mp4'
        with self.assertRaises(c.b.ArchiveError):self.refresh()
    def test_refresh_rejects_acl_drift(self):
        with patch.object(c.f,'same_access',return_value=False):
            with self.assertRaises(c.b.ArchiveError):self.refresh()
    def test_refresh_rejects_parent_drift(self):
        self.current['parents']=['unrelated']
        with self.assertRaises(c.b.ArchiveError):self.refresh()
    def test_refresh_rejects_version_regression(self):
        self.current['version']='1'
        with self.assertRaises(c.b.ArchiveError):self.refresh()
    def test_refresh_rejects_unstable_metadata(self):
        self.sa.meta.side_effect=[copy.deepcopy(self.current),{**copy.deepcopy(self.current),'version':'5'}]
        with self.assertRaises(c.b.ArchiveError):self.refresh()
        self.assertFalse(list(self.home.glob('cas-*')))
    def test_move_still_rejects_version_without_refresh(self):
        with patch.object(c.f,'rpc_once') as rpc:
            with self.assertRaises(c.b.ArchiveError):c.move_once(Mock(),self.sa,self.journal,'source','old','new',self.expected)
            rpc.assert_not_called()
    def test_prior_unlanded_intent_is_not_blindly_replayed(self):
        self.current['version']='2';binding={'source_parent':'old','destination_parent':'new','metadata_before':self.expected,'authority':c.AUTHORITY};self.journal.intent('consolidate:source',binding)
        with patch.object(c.f,'rpc_once') as rpc:
            with self.assertRaises(c.b.ArchiveError):c.move_once(Mock(),self.sa,self.journal,'source','old','new',self.expected)
            rpc.assert_not_called()
    def test_real_journal_landed_without_receipt_no_remote_write(self):
        binding={'source_parent':'old','destination_parent':'new','metadata_before':self.expected,'authority':c.AUTHORITY};self.journal.intent('consolidate:source',binding);started=self.journal.data['intents']['consolidate:source']['started_at'];self.current['parents']=['new']
        with patch.object(c.f,'rpc_once') as rpc:
            c.move_once(Mock(),self.sa,self.journal,'source','old','new',self.expected);rpc.assert_not_called()
        landed=c.transport.Journal(self.home/'journal.json');self.assertEqual(landed.known_id('consolidate:source'),'source');self.assertEqual(landed.data['intents']['consolidate:source']['started_at'],started)
    def test_landed_binding_drift_is_rejected(self):
        binding={'source_parent':'old','destination_parent':'new','metadata_before':self.expected,'authority':'wrong'};self.journal.intent('consolidate:source',binding);self.current['parents']=['new']
        with patch.object(c.f,'rpc_once') as rpc:
            with self.assertRaises(c.b.ArchiveError):c.move_once(Mock(),self.sa,self.journal,'source','old','new',self.expected)
            rpc.assert_not_called()
    def test_refreshed_intent_requires_its_exact_proof(self):
        fresh=self.refresh();binding={'source_parent':'old','destination_parent':'new','metadata_before':fresh,'authority':c.AUTHORITY};self.journal.intent('consolidate:source',binding);self.assertEqual(self.refresh(),fresh)
        proof=self.home/'cas-source-4.json';proof.unlink()
        with self.assertRaises(c.b.ArchiveError):self.refresh()
    def test_unjournalled_new_parent_still_rejected(self):
        self.current['parents']=['new'];expected=self.refresh()
        with patch.object(c.f,'rpc_once') as rpc:
            with self.assertRaises(c.b.ArchiveError):c.move_once(Mock(),self.sa,self.journal,'source','old','new',expected)
            rpc.assert_not_called()

if __name__=='__main__':unittest.main()
