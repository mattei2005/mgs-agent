"""Offline maintenance regression: preserve approved legacy text-only sourcing.
No network, tokens, campaign writes, or manifest mutation.
"""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3.creative_media import matches

class TextSourcingRecoveryTests(unittest.TestCase):
    def fixture(self):
        return {'object_story_spec': {'page_id': '123', 'link_data': {
            'image_hash': 'approved-image-hash', 'name': 'Approved title',
            'message': 'Approved body', 'link': 'https://example.invalid/?utm_campaign=c210'}},
            'media_sourcing_spec': {'titles': [{'text': 'Approved title'}]},
            'url_tags': '', 'contextual_multi_ads': {'enroll_status': 'OPT_OUT'}}

    def test_exact_text_sourcing_and_primary_image_are_preserved(self):
        expected = self.fixture()
        self.assertTrue(matches(copy.deepcopy(expected), expected))

    def test_missing_changed_or_extra_sourcing_and_primary_image_fail_closed(self):
        expected = self.fixture()
        for kind in ['missing', 'changed', 'extra_image', 'video', 'related', 'image_hash', 'destination']:
            with self.subTest(kind=kind):
                actual = copy.deepcopy(expected)
                if kind == 'missing': actual.pop('media_sourcing_spec')
                if kind == 'changed': actual['media_sourcing_spec']['titles'][0]['text'] = 'Changed'
                if kind == 'extra_image': actual['media_sourcing_spec']['images'] = [{'hash': 'extra'}]
                if kind == 'video': actual['media_sourcing_spec']['videos'] = [{'video_id': 'extra'}]
                if kind == 'related': actual['media_sourcing_spec']['related_media'] = {}
                if kind == 'image_hash': actual['object_story_spec']['link_data']['image_hash'] = 'wrong'
                if kind == 'destination': actual['object_story_spec']['link_data']['link'] = 'https://example.invalid/?utm_campaign=wrong'
                self.assertFalse(matches(actual, expected))

    def test_unrecognized_expected_sourcing_is_not_approved_by_equality(self):
        for key in ['videos', 'related_media', 'destination_customizations']:
            with self.subTest(key=key):
                expected = self.fixture()
                expected['media_sourcing_spec'][key] = []
                self.assertFalse(matches(copy.deepcopy(expected), expected))

    def test_recovery_requests_material_sourcing_field(self):
        from ares_campaign_v3.engine import CampaignEngine
        import inspect
        source = inspect.getsource(CampaignEngine)
        lines = [line for line in source.splitlines() if 'creative_fields = ' in line]
        self.assertTrue(lines)
        self.assertTrue(all('media_sourcing_spec' in line for line in lines))

if __name__ == '__main__':
    unittest.main()
