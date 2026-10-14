"""Offline regressions for explicitly requested heterogeneous SHEIN batches."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_general as general
from ares_campaign_v3 import shein_single_clone as driver

class GroupTests(unittest.TestCase):
    def fixture(self):
        r,s,a,assets=case(5,mode='clone_prestaged')
        r['quantity']=2
        r['campaign_groups']=[{'files':[assets[0]['canonical_filename']], 'product_label':'ONE','primary_text':'🔊 EXACT ONE\n✔️ NO FEES.'}, {'files':[x['canonical_filename'] for x in assets[1:]],'product_label':'TWO','primary_text':'🔊 EXACT TWO\n✔️ NO FEES.'}]
        return r,s,a,assets
    def test_groups_keep_order_count_copy_and_source(self):
        r,s,a,assets=self.fixture();before=copy.deepcopy(s)
        out=general.build(r,s,114,a)['campaigns']
        self.assertEqual([len(c['ads']) for c in out],[1,2])
        for c,g in zip(out,r['campaign_groups']):
            self.assertTrue(all(ad['creative_payload']['object_story_spec']['video_data']['message']==g['primary_text'] for ad in c['ads']))
            self.assertTrue(all(ad['creative_payload']['media_sourcing_spec']['bodies']==[{'text':g['primary_text']}] for ad in c['ads']))
        self.assertEqual(s,before)
        self.assertEqual(len({c['idempotency_key'] for c in out}),2)
    def test_group_request_is_supported(self):
        r,*_=self.fixture();r.pop('_resolved_assets');r['manager_media_folder_id']='1234567890';driver.validate_request(r)
    def test_duplicate_cross_group_asset_rejected(self):
        r,s,a,_=self.fixture();r['campaign_groups'][1]['files'][0]=r['campaign_groups'][0]['files'][0]
        with self.assertRaises(ValueError):general.build(r,s,114,a)
    def test_group_count_mismatch_rejected(self):
        r,s,a,_=self.fixture();r['quantity']=3
        with self.assertRaises(ValueError):general.build(r,s,114,a)
    def test_pure_clone_cannot_ignore_group_delta(self):
        r,s,a,_=self.fixture();r['mode']='pure_clone'
        with self.assertRaises(ValueError):general.build(r,s,114,a)
    def test_empty_copy_rejected(self):
        r,s,a,_=self.fixture();r['campaign_groups'][0]['primary_text']=''
        with self.assertRaises(ValueError):general.build(r,s,114,a)
    def test_unknown_group_key_rejected(self):
        r,s,a,_=self.fixture();r['campaign_groups'][0]['targeting']={}
        with self.assertRaises(ValueError):general.build(r,s,114,a)

if __name__=='__main__':unittest.main()
