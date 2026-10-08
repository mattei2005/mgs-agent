"""Offline tests for source setup and tracking-location preservation."""
import copy
import unittest
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_general as compiler
from ares_campaign_v3.creative_media import creative_body,matches
from ares_campaign_v3.schema import Manifest

class SourceSetupTests(unittest.TestCase):
    def source_case(self):
        r,s,a,_=case(1);a['pure_clone_setup_policy']='PRESERVE_SOURCE_DEFINITION'
        c=s['ads'][0]['creative'];c['instagram_user_id']='ig-source'
        c['object_story_spec']['video_data'].update(image_url='https://example.test/thumbnail',image_hash='hash-source',link_description='description')
        c['media_sourcing_spec']={'titles':[{'text':'CLICK'}]}
        return r,s,a

    def test_create_ad_stays_create_ad_with_full_url_and_blank_tracking(self):
        r,s,a=self.source_case();before=copy.deepcopy(s);p=compiler.build(r,s,114,a);cp=p['campaigns'][0]['ads'][0]['creative_payload']
        self.assertEqual(p['campaigns'][0]['creative_materialization_route'],'source_definition_two_phase')
        self.assertNotIn('object_story_id',cp);self.assertEqual(cp['url_tags'],'')
        self.assertEqual(cp['object_story_spec']['instagram_user_id'],'ig-source')
        vd=cp['object_story_spec']['video_data'];self.assertNotIn('image_url',vd);self.assertEqual(vd['image_hash'],'hash-source')
        self.assertIn('utm_campaign=b01fb02c114',vd['call_to_action']['value']['link']);self.assertNotIn('c110',vd['call_to_action']['value']['link'])
        self.assertEqual(s,before);Manifest.from_dict(p)
        body=creative_body(cp);self.assertIn('object_story_spec',body);self.assertNotIn('object_story_id',body)
        actual=copy.deepcopy(cp);actual['instagram_user_id']='ig-source';self.assertTrue(matches(actual,cp))
        actual['object_story_spec']['video_data']['call_to_action']['value']['link']=s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value']['link'];self.assertFalse(matches(actual,cp))

    def test_source_tracking_field_remains_same_location_when_present(self):
        r,s,a=self.source_case();c=s['ads'][0]['creative'];link=c['object_story_spec']['video_data']['call_to_action']['value']['link'];c['url_tags']=link.split('?')[1];c['object_story_spec']['video_data']['call_to_action']['value']['link']=link.split('?')[0]
        p=compiler.build(r,s,114,a);cp=p['campaigns'][0]['ads'][0]['creative_payload']
        self.assertEqual(cp['object_story_spec']['video_data']['call_to_action']['value']['link'],link.split('?')[0]);self.assertIn('c114',cp['url_tags'])

if __name__=='__main__':unittest.main()
