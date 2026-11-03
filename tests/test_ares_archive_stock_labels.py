"""Synthetic fixtures only; never writes live bindings or invokes Google."""
import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ares_archive_stock_labels as labels
import ares_archive_namespace as namespace

class LabelsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.scope = patch.object(labels, 'HOME', self.home); self.scope.start()
        self.entry = dict(zip(labels.FIELDS, [labels.SOURCE, labels.PROVIDER, labels.STOCK, labels.JOB, 'synthetic-lineage', 'b'*32, 'a'*64, '10']))
        self.rec = {'identity': labels.identity(self.entry), 'stock_name': '03 - BABY TEES', 'provider_name': 'SHEIN_US_EN_IMG_FREE_BABY_TEES_NV_003.jpg', 'catalogue_name': 'SHEIN_US_EN_IMG_FREE_BABY_TEES_NV_003.jpg', 'provider_parents': ['synthetic-provider-parent']}
        self.proof = {'schema': 'mgs.archive.stock.label.proof.v1', 'authority_message_id': labels.AUTHORITY, 'native_verified': True, 'record': self.rec, 'provider_hashes': {k:self.entry[k] for k in ('size','md5','sha256')}, 'ack_verified': True}
        self.physical = {'id':labels.PROVIDER, 'name':self.rec['provider_name'], 'parents':self.rec['provider_parents']}
        self.stock = {'id':labels.STOCK, 'name':self.rec['stock_name'], 'shortcutDetails':{'targetId':labels.PROVIDER}, 'properties':{'mgsArchiveLogicalSource':labels.SOURCE}}
        self.save()
    def tearDown(self):
        self.scope.stop(); self.tmp.cleanup()
    def save(self):
        labels.b.atomic_json(self.home/'native-proof.json', self.proof)
        labels.b.atomic_json(self.home/'binding.json', {'schema':'mgs.archive.stock.label.binding.v1','authority_message_id':labels.AUTHORITY,'phase':'active','proof_sha256':hashlib.sha256(labels.b.canonical(self.proof)).hexdigest()})
    def test_exact_approved_label(self):
        self.assertTrue(labels.names_match(self.entry,self.physical,self.stock))
        self.assertEqual(labels.catalogue_name(self.entry,self.stock),self.rec['provider_name'])
    def test_different_entry_remains_original_rule(self):
        with patch.object(namespace,'binding',return_value=None):
            self.assertFalse(namespace.names_match({'sourceId':'synthetic-other'}, {'name':'old'},{'name':'new'}))
    def test_any_identity_drift_fails_closed(self):
        for k in labels.FIELDS:
            with self.subTest(k=k):
                with self.assertRaises(labels.b.ArchiveError):labels.record({**self.entry,k:'unexpected'}) if k!='sourceId' else labels.record({**self.entry,'archiveId':'unexpected'})
    def test_label_and_target_drift_rejected(self):
        for changed in [{'name':'other'},{'id':'other'},{'shortcutDetails':{'targetId':'other'}},{'properties':{'mgsArchiveLogicalSource':'other'}}]:
            with self.subTest(changed=changed): self.assertFalse(labels.names_match(self.entry,self.physical,{**self.stock,**changed}))
    def test_provider_name_parent_and_id_drift_rejected(self):
        for changed in [{'name':'other'},{'id':'other'},{'parents':['other']}]:
            with self.subTest(changed=changed): self.assertFalse(labels.names_match(self.entry,{**self.physical,**changed},self.stock))
    def test_tampered_proof_rejected(self):
        proof=copy.deepcopy(self.proof);proof['record']['stock_name']='other'
        labels.b.atomic_json(self.home/'native-proof.json',proof)
        with self.assertRaises(labels.b.ArchiveError):labels.record(self.entry)
    def test_wrong_authority_rejected(self):
        self.proof['authority_message_id']='unapproved';self.save()
        with self.assertRaises(labels.b.ArchiveError):labels.record(self.entry)
    def test_bytes_or_ack_not_verified_rejected(self):
        self.proof['ack_verified']=False;self.save()
        with self.assertRaises(labels.b.ArchiveError):labels.record(self.entry)
    def test_native_mapping_preserves_business_filename(self):
        self.assertEqual(labels.native_stock_label(labels.SOURCE,labels.STOCK,self.rec['catalogue_name']),self.rec['stock_name'])
        self.assertIsNone(labels.native_stock_label('other',labels.STOCK,self.rec['catalogue_name']))
    def test_namespace_hooks_preserve_canonical_filename(self):
        with patch.object(namespace,'binding',return_value=None):
            self.assertTrue(namespace.names_match(self.entry,self.physical,self.stock))
            self.assertEqual(namespace.catalogue_name(self.entry,self.stock),self.rec['catalogue_name'])
            self.assertEqual(namespace.native_stock_label(labels.SOURCE,labels.STOCK,self.rec['catalogue_name']),self.rec['stock_name'])

if __name__=='__main__':unittest.main()
