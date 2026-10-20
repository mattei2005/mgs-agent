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
    def test_optional_headline_is_literal_and_preserves_native_cta(self):
        r,s,a,_=self.fixture();before=copy.deepcopy(s)
        r['campaign_groups'][0]['headline']='LO QUIERO GRATIS 👉'
        r['campaign_groups'][1]['headline']='  EXACT TWO 👉  '
        out=general.build(r,s,114,a)['campaigns']
        for c,g in zip(out,r['campaign_groups']):
            for ad in c['ads']:
                cr=ad['creative_payload'];vd=cr['object_story_spec']['video_data']
                self.assertEqual(vd['title'],g['headline'])
                self.assertEqual(cr['media_sourcing_spec']['titles'],[{'text':g['headline']}])
                self.assertEqual(vd['call_to_action']['type'],s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['type'])
        self.assertEqual(s,before)
        r.pop('_resolved_assets');driver.validate_request(r)

    def test_invalid_optional_headline_rejected(self):
        for value in ['', '  ', None, 123, {'text':'NO'}]:
            r,s,a,_=self.fixture();r['campaign_groups'][0]['headline']=value
            with self.assertRaises(ValueError):general.build(r,s,114,a)

    def test_omitted_headline_keeps_live_reference(self):
        r,s,a,_=self.fixture()
        out=general.build(r,s,114,a)['campaigns']
        expected=s['ads'][0]['creative']['object_story_spec']['video_data']['title']
        self.assertTrue(all(ad['creative_payload']['object_story_spec']['video_data']['title']==expected for c in out for ad in c['ads']))

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

    def test_twelve_heterogeneous_groups_match_exact_counts_and_caps(self):
        r,s,a,base=case(5,mode='clone_prestaged');counts=[3,2,2,1,2,5,2,2,3,2,2,3]
        assets=[];groups=[]
        for i,n in enumerate(counts):
            group=[]
            for j in range(n):
                x=copy.deepcopy(base[0]);x.update(asset_id=f'asset-{i}-{j}',checksum=f'{i*5+j+1:064x}',vertical_video_id=f'video-{i}-{j}',canonical_filename=f'SHEIN_US_EN_VID_PRODUCT_{i}_PV_{j+1:03d}.mp4');assets.append(x);group.append(x['canonical_filename'])
            groups.append({'files':group,'product_label':f'PRODUCT {i}','primary_text':f'EXACT {i}'})
        r.update(quantity=12,campaign_groups=groups,_resolved_assets=assets,bid_strategy='COCAP',bid_usd='0.90',budget_usd='45')
        out=general.build(r,s,101,a)['campaigns']
        self.assertEqual([len(c['ads']) for c in out],counts)
        self.assertEqual(sum(len(c['ads']) for c in out),29)
        self.assertEqual(sum(int(c['campaign_updates']['daily_budget']) for c in out),54000)
        self.assertTrue(all(c['adset_updates']['bid_amount']=='90' and c['campaign_updates']['bid_strategy']=='COST_CAP' for c in out))
        self.assertEqual(len({c['idempotency_key'] for c in out}),12)

    def test_persisted_rendered_proof_requires_exact_unchanged_ids(self):
        from ares_campaign_v3.shein_qa import proof_covers
        proof={'verified':True,'ad_ids':['ad'],'creative_ids':['creative']}
        live={'ads':{'data':[{'id':'ad','creative':{'id':'creative'}}]}}
        self.assertTrue(proof_covers(proof,live))
        self.assertFalse(proof_covers(proof,{'ads':{'data':[]}}))
        changed=copy.deepcopy(live);changed['ads']['data'][0]['creative']['id']='changed'
        self.assertFalse(proof_covers(proof,changed))
        changed=copy.deepcopy(live);changed['ads']['data'][0]['id']='changed'
        self.assertFalse(proof_covers(proof,changed))
        self.assertFalse(proof_covers({**proof,'verified':False},live))

if __name__=='__main__':unittest.main()
