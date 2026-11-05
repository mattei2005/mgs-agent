"""Read-only comparator regressions: static image with AFS text variants.
Synthetic offline fixtures only; never transport, token, or manifest mutation.
"""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3.creative_media import matches
from ares_campaign_v3.image_sourcing import sourcing

class StaticTextFeedTests(unittest.TestCase):
    def fixture(self):
        feed = {'bodies': [{'text': 'Body A'}, {'text': 'Body B'}],
                'titles': [{'text': 'Title A'}, {'text': 'Title B'}],
                'descriptions': [{'text': 'Description'}],
                'optimization_type': 'DEGREES_OF_FREEDOM'}
        return {'object_story_spec': {'page_id': '123', 'instagram_user_id': '456',
                    'link_data': {'image_hash': 'image-approved',
                        'link': 'https://example.invalid/?utm_campaign=c025',
                        'call_to_action': {'type': 'LEARN_MORE', 'value': {'link': 'https://example.invalid/?utm_campaign=c025'}}}},
                'asset_feed_spec': feed,
                'media_sourcing_spec': {'images': [{'hash': 'image-approved', 'source': 'multi_media', 'opt_in_status': 'opt_in'}],
                    **{k: copy.deepcopy(v) for k, v in feed.items() if k != 'optimization_type'}},
                'url_tags': '', 'contextual_multi_ads': {'enroll_status': 'OPT_OUT'}}

    def test_exact_preserved_static_text_feed_matches_without_mutation(self):
        expected = self.fixture(); actual = copy.deepcopy(expected); before = copy.deepcopy(expected)
        self.assertTrue(matches(actual, expected))
        self.assertEqual(expected, before); self.assertEqual(actual, before)

    def test_missing_changed_extra_media_and_identity_fail_closed(self):
        expected = self.fixture()
        for field in ['missing_spec', 'extra_image', 'hash', 'sourcing_hash', 'source', 'opt',
                      'sourcing_body', 'feed_body', 'page', 'instagram', 'link', 'cta',
                      'tags', 'multi_ads', 'feed_extra', 'spec_extra', 'video', 'post']:
            with self.subTest(field=field):
                actual = copy.deepcopy(expected)
                if field == 'missing_spec': actual.pop('media_sourcing_spec')
                elif field == 'extra_image': actual['media_sourcing_spec']['images'].append({'hash': 'extra'})
                elif field == 'hash': actual['object_story_spec']['link_data']['image_hash'] = 'wrong'
                elif field == 'sourcing_hash': actual['media_sourcing_spec']['images'][0]['hash'] = 'wrong'
                elif field in {'source', 'opt'}: actual['media_sourcing_spec']['images'][0]['source' if field == 'source' else 'opt_in_status'] = 'wrong'
                elif field == 'sourcing_body': actual['media_sourcing_spec']['bodies'][0]['text'] = 'wrong'
                elif field == 'feed_body': actual['asset_feed_spec']['bodies'][0]['text'] = 'wrong'
                elif field == 'page': actual['object_story_spec']['page_id'] = 'wrong'
                elif field == 'instagram': actual['object_story_spec']['instagram_user_id'] = 'wrong'
                elif field == 'link': actual['object_story_spec']['link_data']['link'] = 'https://example.invalid/wrong'
                elif field == 'cta': actual['object_story_spec']['link_data']['call_to_action']['type'] = 'APPLY_NOW'
                elif field == 'tags': actual['url_tags'] = 'utm_campaign=wrong'
                elif field == 'multi_ads': actual['contextual_multi_ads']['enroll_status'] = 'OPT_IN'
                elif field == 'feed_extra': actual['asset_feed_spec']['images'] = [{'hash': 'extra'}]
                elif field == 'spec_extra': actual['media_sourcing_spec']['related_media'] = []
                elif field == 'video': actual['object_story_spec']['video_data'] = {'video_id': 'extra'}
                elif field == 'post': actual['object_story_id'] = '123_789'
                self.assertFalse(matches(actual, expected))

    def test_unapproved_expected_shapes_cannot_pass_by_equality(self):
        for field in ['feed_media', 'unknown_feed', 'spec_media', 'hash_mismatch', 'text_mismatch', 'post', 'video']:
            with self.subTest(field=field):
                expected = self.fixture()
                if field == 'feed_media': expected['asset_feed_spec']['images'] = [{'hash': 'extra'}]
                elif field == 'unknown_feed': expected['asset_feed_spec']['unknown'] = True
                elif field == 'spec_media': expected['media_sourcing_spec']['videos'] = []
                elif field == 'hash_mismatch': expected['media_sourcing_spec']['images'][0]['hash'] = 'wrong'
                elif field == 'text_mismatch': expected['media_sourcing_spec']['bodies'][0]['text'] = 'wrong'
                elif field == 'post': expected['object_story_id'] = '123_789'
                elif field == 'video': expected['object_story_spec']['video_data'] = {'video_id': 'extra'}
                try: result = matches(copy.deepcopy(expected), expected)
                except (ValueError, KeyError): result = False
                self.assertFalse(result)

    def test_new_media_sourcing_recipe_stays_strict(self):
        with self.assertRaises(ValueError): sourcing(self.fixture())

if __name__ == '__main__':
    unittest.main()
