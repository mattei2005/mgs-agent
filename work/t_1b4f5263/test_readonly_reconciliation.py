"""Offline regression, using saved native snapshots as fixtures, NOT live proof."""
import copy,hashlib,importlib.util,json,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/root/mgs-agent');STAGE=ROOT/'work/t_1b4f5263'
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(STAGE if os.environ.get('RECONCILIATION_INSTALLED')!='1' else ROOT/'scripts'))
import ares_archive_readonly_reconciliation as r
spec=importlib.util.spec_from_file_location('tested_storage',r.__file__.replace('ares_archive_readonly_reconciliation.py','ares_archive_storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
H=r.HOME
ORIGINAL_READ=r.b.read_json
PROOF=ORIGINAL_READ(H/'approved-native-proof.json')
BINDING=ORIGINAL_READ(H/'approved-readonly-binding.json')

class OfflineDrive:
    def __init__(self,pair):self.pair=pair;self.calls=[]
    def relative_parent(self,parent,root):return self.pair['accepted_provider_relative_path']
    def one(self,parent,key):return {'id':self.pair['ack_id']}
    def raw(self,fid):
        # Real archived ACK bytes saved by the earlier readonly diagnosis.
        proof=ORIGINAL_READ(H/'native-ack-proof.json')
        raise AssertionError('must inject ACK raw from native proof fixture')

class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.rec=copy.deepcopy(PROOF['records'][0]);self.e=self.rec['frozen_entry'];self.p=self.rec['provider'];self.stock=self.rec['source'];self.pair=self.rec['pair'];self.d=OfflineDrive(self.pair)
        # No Drive calls: the ACK digest API is stubbed separately below.
        self.context=patch.object(r,'hashlib',wraps=hashlib)
    def project(self):
        # Use actual native ACK bytes preserved in local diagnosis records.
        raw=ACKS[self.pair['ack_id']]
        with patch.object(self.d,'raw',return_value=raw):return r.project(self.d,self.e,self.p,self.stock)
    def resolve(self):
        def meta(d,fid):return self.p if fid==self.p['id'] else self.stock
        raw=ACKS[self.pair['ack_id']]
        with patch.object(s,'enabled',return_value=True),patch.object(s,'mapping',return_value=self.e),patch.object(s,'drive',return_value=self.d),patch.object(s,'meta',side_effect=meta),patch.object(s,'require_historical_ack',return_value=True),patch.object(self.d,'raw',return_value=raw),patch.object(s.locations,'stock_parent',return_value=self.pair['retained_source_relative_path']):
            return s.resolve_media(self.e['sourceId'])
    def test_both_exact_pairs_pass_readonly_and_preserve_mapping(self):
        for record in PROOF['records']:
            with self.subTest(source=record['pair']['logical_source_id']):
                self.rec=copy.deepcopy(record);self.e=self.rec['frozen_entry'];self.p=self.rec['provider'];self.stock=self.rec['source'];self.pair=self.rec['pair'];self.d=OfflineDrive(self.pair)
                before=copy.deepcopy(self.e);out=self.resolve()
                self.assertEqual(out['id'],self.e['sourceId']);self.assertEqual(out['provider_id'],self.e['archiveId']);self.assertEqual(out['stock_file_id'],self.e['sourceId']);self.assertEqual(out['sha256Checksum'],self.e['sha256']);self.assertEqual(out['parents'],self.stock['parents']);self.assertEqual(before,self.e)
    def test_unrelated_id_not_projected(self):
        self.e['sourceId']='offlineUnapproved'
        self.assertIs(r.project(self.d,self.e,self.p,self.stock),self.e)
    def test_bad_binding_digest(self):
        with patch.object(r,'BINDING_SHA256','0'*64),self.assertRaisesRegex(r.ReconciliationError,'BINDING_DIGEST'):self.project()
    def test_missing_binding(self):
        with patch.object(r.b,'read_json',side_effect=lambda p,*a:{} if p.name=='approved-readonly-binding.json' else ORIGINAL_READ(p,*a)),self.assertRaisesRegex(r.ReconciliationError,'BINDING_DIGEST'):self.project()
    def test_edited_authority_rejected(self):
        def read(p,*a):
            obj=ORIGINAL_READ(p,*a)
            if p.name=='approved-authority-readback.json':obj['messages'][0]['content']='other'
            return obj
        with patch.object(r.b,'read_json',side_effect=read),self.assertRaisesRegex(r.ReconciliationError,'AUTHORITY_READBACK'):self.project()
    def test_native_proof_tamper_rejected(self):
        def read(p,*a):
            obj=ORIGINAL_READ(p,*a)
            if p.name=='approved-native-proof.json':obj['records'][0]['full_bytes_and_native_ack_verified']=False
            return obj
        with patch.object(r.b,'read_json',side_effect=read),self.assertRaisesRegex(r.ReconciliationError,'NATIVE_PROOF_DIGEST'):self.project()
    def test_request_tamper_rejected(self):
        with patch.object(Path,'read_bytes',return_value=b'changed-request'),self.assertRaisesRegex(r.ReconciliationError,'REQUEST_DIGEST'):self.project()
    def test_changed_frozen_fields_rejected(self):
        for field in ['archiveId','archiveParentId','sha256','md5','size','jobId','mimeType','owner','stockShortcutId']:
            with self.subTest(field=field):
                before=self.e[field];self.e[field]='changed'
                with self.assertRaisesRegex(r.ReconciliationError,'FROZEN_IDENTITY'):self.project()
                self.e[field]=before
    def test_wrong_native_provider_parent_rejected(self):
        self.p['parents']=['wrong']
        with self.assertRaisesRegex(r.ReconciliationError,'NATIVE_IDS_PARENT'):self.project()
    def test_wrong_provider_id_rejected(self):
        self.p['id']='wrong'
        with self.assertRaisesRegex(r.ReconciliationError,'NATIVE_IDS_PARENT'):self.project()
    def test_wrong_stock_id_rejected(self):
        self.stock['id']='wrong'
        with self.assertRaisesRegex(r.ReconciliationError,'NATIVE_IDS_PARENT'):self.project()
    def test_path_drift_rejected(self):
        with patch.object(self.d,'relative_parent',return_value=['SHEIN_US_EN','VID','OTHER']),self.assertRaisesRegex(r.ReconciliationError,'PROVIDER_PATH'):self.project()
    def test_ack_id_drift_rejected(self):
        with patch.object(self.d,'one',return_value={'id':'wrong'}),self.assertRaisesRegex(r.ReconciliationError,'NATIVE_ACK_ID_DIGEST'):self.project()
    def test_ack_raw_drift_rejected(self):
        with patch.object(self.d,'raw',return_value=b'wrong'),self.assertRaisesRegex(r.ReconciliationError,'NATIVE_ACK_ID_DIGEST'):r.project(self.d,self.e,self.p,self.stock)
    def test_provider_owner_guard_not_bypassed(self):
        self.p['owners']=[{'emailAddress':'other@example.invalid'}]
        with self.assertRaisesRegex(s.StorageError,'PROVIDER_IDENTITY'):self.resolve()
    def test_provider_hash_guard_not_bypassed(self):
        self.p['md5Checksum']='0'*32
        with self.assertRaisesRegex(s.StorageError,'CONTENT_OR_PUBLIC'):self.resolve()
    def test_provider_public_guard_not_bypassed(self):
        self.p['permissions']=[{'type':'anyone'}]
        with self.assertRaisesRegex(s.StorageError,'CONTENT_OR_PUBLIC'):self.resolve()
    def test_retained_source_hash_guard_not_bypassed(self):
        self.stock['md5Checksum']='0'*32
        with self.assertRaisesRegex(s.StorageError,'RETAINED_SOURCE_CONTENT'):self.resolve()
    def test_trashed_source_guard_not_bypassed(self):
        self.stock['trashed']=True
        with self.assertRaisesRegex(s.StorageError,'STOCK_IDENTITY'):self.resolve()
    def test_native_ack_validation_still_required(self):
        with patch.object(s,'enabled',return_value=True),patch.object(s,'mapping',return_value=self.e),patch.object(s,'drive',return_value=self.d),patch.object(s,'meta',side_effect=[self.p,self.stock]),patch.object(s,'require_historical_ack',side_effect=s.StorageError('HISTORICAL_NATIVE_ACK_REQUIRED')):
            with self.assertRaisesRegex(s.StorageError,'NATIVE_ACK_REQUIRED'):s.resolve_media(self.e['sourceId'])
    def test_move_guard_unchanged_rejects_provider_drift(self):
        with self.assertRaisesRegex(s.StorageError,'PROVIDER_IDENTITY'):s.historical_media_record(self.e,self.p,self.stock)
    def test_namespace_mapping_not_expanded(self):
        self.assertIsNone(s.namespace.override(self.e));self.assertEqual(s.historical_mapping(self.e['sourceId']),self.e)

ACKS={}
if __name__=='__main__':
    # Load only real saved native ACK JSONs; their canonical representation is
    # not assumed to equal native bytes. Dedicated fixture file stores raw bytes.
    import base64
    data=json.loads((STAGE/'ack-raw-fixtures.json').read_text())
    ACKS={k:base64.b64decode(v) for k,v in data.items()}
    for rec in PROOF['records']:
        assert hashlib.sha256(ACKS[rec['pair']['ack_id']]).hexdigest()==rec['pair']['ack_sha256']
    unittest.main(verbosity=2)
