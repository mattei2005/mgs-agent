"""OFFLINE description overrides: no network or live campaign IDs."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_general_runtime import case
from test_shein_cross_account_reference import fixture
from ares_campaign_v3 import shein_general as general
from ares_campaign_v3.shein_grouped_media import validate_groups

class DescriptionTests(unittest.TestCase):
    def grouped(self):
        r,s,a,assets=case(5,mode='clone_prestaged')
        s['ads'][0]['creative']['object_story_spec']['video_data']['link_description']='✨✨✨✨✨'
        r['campaign_groups']=[{'files':[x['canonical_filename'] for x in assets], 'product_label':'FREE_PRODUCT','primary_text':'EXACT BODY','headline':'EXACT TITLE','description':'⭐⭐⭐⭐⭐'}]
        return r,s,a,assets

    def test_literal_video_description_source_and_cta_preserved(self):
        r,s,a,_=self.grouped();before=copy.deepcopy(s)
        ads=general.build(r,s,114,a)['campaigns'][0]['ads']
        self.assertTrue(ads)
        for ad in ads:
            v=ad['creative_payload']['object_story_spec']['video_data']
            self.assertEqual(v['link_description'],'⭐⭐⭐⭐⭐')
            self.assertEqual(v['title'],'EXACT TITLE')
            self.assertEqual(v['message'],'EXACT BODY')
            self.assertEqual(v['call_to_action']['type'],s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['type'])
        self.assertEqual(s,before)

    def test_omission_inherits_live_description(self):
        r,s,a,_=self.grouped();r['campaign_groups'][0].pop('description')
        ads=general.build(r,s,114,a)['campaigns'][0]['ads']
        self.assertTrue(all(x['creative_payload']['object_story_spec']['video_data']['link_description']=='✨✨✨✨✨' for x in ads))

    def test_invalid_description_rejected(self):
        for value in ('',' ',None,0,{},[]):
            with self.subTest(value=value):
                r,_,_,_=self.grouped();r['campaign_groups'][0]['description']=value
                with self.assertRaisesRegex(ValueError,'description'): validate_groups(r)

    def test_literal_spaces_preserved(self):
        r,s,a,_=self.grouped();r['campaign_groups'][0]['description']='  ⭐⭐⭐⭐⭐  '
        ads=general.build(r,s,114,a)['campaigns'][0]['ads']
        self.assertTrue(all(x['creative_payload']['object_story_spec']['video_data']['link_description']=='  ⭐⭐⭐⭐⭐  ' for x in ads))

    def test_image_description_uses_link_data(self):
        r,s,a,assets=self.grouped()
        for x in assets:
            x.update(media_type='image',image_hash='offline-hash-'+x['asset_id'],upload_edge='ad_account_adimages',canonical_filename=x['canonical_filename'].replace('_VID_','_IMG_').replace('.mp4','.png'))
            x.pop('vertical_video_id',None)
        r['campaign_groups'][0]['files']=[x['canonical_filename'] for x in assets]
        ads=general.build(r,s,114,a)['campaigns'][0]['ads']
        for ad in ads:
            story=ad['creative_payload']['object_story_spec']
            self.assertNotIn('video_data',story)
            self.assertEqual(story['link_data']['description'],'⭐⭐⭐⭐⭐')

    def test_cross_account_literal_and_source_immutable(self):
        r,s,a,assets,_=fixture(5,2);before=copy.deepcopy(s)
        r['campaign_groups']=[{'files':[x['canonical_filename'] for x in assets],'product_label':'FREE_PRODUCT','primary_text':r['primary_text'],'description':'⭐⭐⭐⭐⭐'}]
        shell=general.build(r,s,1,a)['campaigns'][0]
        self.assertEqual(s,before)
        self.assertEqual(len(shell['ads']),2)
        for ad in shell['ads']:
            cr=ad['creative_payload'];v=cr['object_story_spec']['video_data']
            self.assertEqual(v['link_description'],'⭐⭐⭐⭐⭐')
            self.assertEqual(v['call_to_action']['value']['link'],r['website_url'])
            self.assertEqual(cr['url_tags'],'')

if __name__=='__main__': unittest.main()
