"""Synthetic renamed-image identity evidence and no-reupload regression."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image
from ares_campaign_v3 import image_prestage as ip, image_identity as identity
from ares_campaign_v3.media_registry import MediaRegistry,MediaNotReady
from ares_campaign_v3.shein_single_clone import atomic_json

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.proof=self.root/'synthetic-request';self.proof.mkdir()
        self.path=self.root/'SHEIN_US_ES_IMG_TEST_NV_001.png'
        Image.new('RGB',(200,300),'red').save(self.path);raw=self.path.read_bytes()
        self.account='123456789';self.sha=hashlib.sha256(raw).hexdigest();self.hash='a'*32
        self.a={'asset_id':'offline-image','checksum':self.sha,'canonical_filename':self.path.name,'vertical_file':str(self.path),'media_type':'image','metadata_clean':True,'drive_id':'offline-drive','drive_md5':hashlib.md5(raw).hexdigest()}
        self.preparation={'request_id':self.proof.name,'account_id':self.account,'assets':[self.a]}
        self.prep=self.proof/'media-preparation.json';atomic_json(self.prep,self.preparation)
        self.name=ip.image_title(self.a['asset_id'],self.sha,self.path.name)
        self.row={'hash':self.hash,'name':self.name+'_105','original_width':200,'original_height':300,'status':'ACTIVE'}
        self.reg=MediaRegistry(self.root/'registry.json')
        self.record=self.reg.register_image(account_id=self.account,asset_id=self.a['asset_id'],checksum=self.sha,image_hash=self.hash,ready=True,association_verified=True)
        self.intent={'account_id':self.account,'asset_id':self.a['asset_id'],'checksum':self.sha,'name':self.name,'image_hash':self.hash,'status':'READY'}
        self.receipt=self.proof/('image-upload-'+hashlib.sha256((self.account+'|'+self.a['asset_id']+'|'+self.sha).encode()).hexdigest()+'.json');atomic_json(self.receipt,self.intent)
    def check(self,**changes):
        args=dict(account_id=self.account,asset=self.a,registry_record=self.record,proof_dir=self.proof);args.update(changes)
        return identity.require_prepared_image([self.row],self.hash,**args)
    def test_name_is_auxiliary_only_after_exact_proof(self):
        for name in [self.name+'_105','a different mutable label',self.name+'_999']:
            with self.subTest(name=name):self.row['name']=name;self.assertEqual(self.check(),self.row)
    def test_unbound_suffix_is_not_whitelisted(self):
        self.receipt.write_text('{}')
        with self.assertRaises(MediaNotReady):self.check()
        with self.assertRaises(MediaNotReady):ip.require_image([self.row],self.hash,name=self.name)
    def test_registry_identity_negatives(self):
        for k,v in {'account_id':'999','asset_id':'other','checksum':'f'*64,'image_hash':'b'*32,'media_type':'video','ready':False,'association_verified':False,'upload_edge':'ad_account_advideos','source':'manual','vertical_video_id':'video'}.items():
            with self.subTest(field=k),self.assertRaises(MediaNotReady):self.check(registry_record={**self.record,k:v})
    def test_upload_receipt_negatives(self):
        for k,v in {'account_id':'999','asset_id':'other','checksum':'f'*64,'image_hash':'b'*32,'name':'other','status':'READBACK_PENDING','extra':'unknown'}.items():
            atomic_json(self.receipt,{**self.intent,k:v})
            with self.subTest(field=k),self.assertRaises(MediaNotReady):self.check()
        atomic_json(self.receipt,self.intent)
    def test_preparation_negatives(self):
        cases=[{**self.preparation,'account_id':'999'},{**self.preparation,'request_id':'other'},{**self.preparation,'assets':[self.a,self.a]}]
        for k,v in {'asset_id':'other','checksum':'f'*64,'canonical_filename':'other.png','media_type':'video','metadata_clean':False,'drive_md5':'f'*32,'vertical_file':str(self.root/'missing.png')}.items():
            cases.append({**self.preparation,'assets':[{**self.a,k:v}]})
        for c in cases:
            atomic_json(self.prep,c)
            with self.subTest(case=c),self.assertRaises(MediaNotReady):self.check()
    def test_hash_status_dimensions_duplicates_fail_even_with_proof(self):
        for k,v in {'hash':'b'*32,'status':'DELETED','original_width':201,'original_height':301}.items():
            original=dict(self.row);self.row[k]=v
            with self.subTest(field=k),self.assertRaises(MediaNotReady):self.check()
            self.row=original
        with self.assertRaises(MediaNotReady):identity.require_prepared_image([self.row,self.row],self.hash,account_id=self.account,asset=self.a,registry_record=self.record,proof_dir=self.proof)
    def test_missing_status_and_asset_identity_fail(self):
        for delta in [{'account_id':'other'},{'image_hash':'b'*32}]:
            with self.subTest(delta=delta),self.assertRaises(MediaNotReady):self.check(asset={**self.a,**delta})
        self.row.pop('status')
        with self.assertRaises(MediaNotReady):self.check()
    def test_local_and_asset_bytes_fail_closed(self):
        with self.assertRaises(MediaNotReady):self.check(asset={**self.a,'drive_md5':'bad'})
        with self.assertRaises(MediaNotReady):self.check(asset={**self.a,'asset_drive_id':'other-drive'})
        self.path.write_bytes(b'changed')
        with self.assertRaises(MediaNotReady):self.check()
    def test_prestage_registry_hit_zero_upload_zero_write(self):
        uploader=Mock();uploader.inventory.return_value=[self.row];writer=Mock(side_effect=AssertionError('no receipt/registry writes on cache hit'))
        result=ip.prestage_images([self.a],account_id=self.account,registry=self.reg,uploader=uploader,proof_dir=self.proof,atomic_json=writer)
        self.assertEqual(result['registry_hits'],1);uploader.upload.assert_not_called();writer.assert_not_called()
    def test_corrupt_registry_does_not_reupload(self):
        value=json.loads(self.reg.path.read_text());next(iter(value['records'].values()))['ready']=False;atomic_json(self.reg.path,value)
        uploader=Mock();uploader.inventory.return_value=[self.row]
        with self.assertRaises(MediaNotReady):ip.prestage_images([self.a],account_id=self.account,registry=self.reg,uploader=uploader,proof_dir=self.proof,atomic_json=Mock())
        uploader.upload.assert_not_called()
    def test_unknown_hash_after_lost_response_blocks_no_upload(self):
        # No registry/known hash: a suffix alone is never used for recovery.
        self.reg=MediaRegistry(self.root/'empty.json');self.intent.pop('image_hash');self.intent['status']='UPLOAD_INTENT';atomic_json(self.receipt,self.intent)
        uploader=Mock();uploader.inventory.return_value=[self.row]
        with self.assertRaises(MediaNotReady):ip.prestage_images([self.a],account_id=self.account,registry=self.reg,uploader=uploader,proof_dir=self.proof,atomic_json=Mock())
        uploader.upload.assert_not_called()
