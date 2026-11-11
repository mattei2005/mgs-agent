"""Offline maintenance: exact reviewed existing static variants, no transport."""
import copy
import unittest
from ares_campaign_v3 import reviewed_copy_omissions as review
from ares_campaign_v3.creative_media import matches
from ares_campaign_v3.shein_continuation import content_digest

class PreservedStaticSourcingTests(unittest.TestCase):
    def fixture(self):
        expected = {
            'object_story_spec': {'page_id': '123', 'instagram_user_id': '456',
                'link_data': {'image_hash': 'primary', 'link': 'https://example.invalid/?utm_campaign=c030'}},
            'asset_feed_spec': {'optimization_type': 'DEGREES_OF_FREEDOM',
                'titles': [{'text': 'Title'}], 'bodies': [{'text': 'Body'}]},
            'media_sourcing_spec': {'images': [
                {'hash': 'padded', 'source': 'padding', 'opt_in_status': 'opt_out', 'variant_types': ['SQUARE']},
                {'hash': 'expanded', 'source': 'uncrop', 'opt_in_status': 'opt_out', 'variant_types': ['VERTICAL']},
                {'hash': 'primary', 'source': 'multi_media', 'opt_in_status': 'opt_in'}],
                'titles': [{'text': 'Title'}], 'bodies': [{'text': 'Body'}]},
            'url_tags': '', 'contextual_multi_ads': {'enroll_status': 'OPT_OUT'}}
        actual = copy.deepcopy(expected); actual['id'] = '789'
        receipt = {'binding': {'slots': [{'creative_id': '789',
            'effective_payload_digest': content_digest(expected)}]}}
        return expected, actual, {'verified': True, 'receipt': receipt, 'digest': content_digest(receipt)}

    def test_exact_variants_pass_only_inside_bound_verified_context(self):
        e, a, proof = self.fixture()
        self.assertFalse(matches(a, e))
        before = copy.deepcopy((e, a)); marker = review.CURRENT.set(proof)
        try: self.assertTrue(matches(a, e))
        finally: review.CURRENT.reset(marker)
        self.assertEqual((e, a), before)
        self.assertFalse(matches(a, e))

    def test_material_changes_cannot_be_accepted_by_feature_review(self):
        e, a, proof = self.fixture(); marker = review.CURRENT.set(proof)
        try:
            for mutation in ['hash', 'crop', 'flag', 'source', 'extra', 'text', 'feed', 'destination', 'page', 'instagram', 'tags', 'post', 'missing']:
                bad = copy.deepcopy(a)
                if mutation == 'hash': bad['media_sourcing_spec']['images'][0]['hash'] = 'wrong'
                if mutation == 'crop': bad['media_sourcing_spec']['images'][0]['variant_types'] = ['HORIZONTAL']
                if mutation == 'flag': bad['media_sourcing_spec']['images'][1]['opt_in_status'] = 'opt_in'
                if mutation == 'source': bad['media_sourcing_spec']['images'][0]['source'] = 'unknown'
                if mutation == 'extra': bad['media_sourcing_spec']['videos'] = []
                if mutation == 'text': bad['media_sourcing_spec']['titles'][0]['text'] = 'wrong'
                if mutation == 'feed': bad['asset_feed_spec']['bodies'][0]['text'] = 'wrong'
                if mutation == 'destination': bad['object_story_spec']['link_data']['link'] = 'https://example.invalid/?utm_campaign=wrong'
                if mutation == 'page': bad['object_story_spec']['page_id'] = 'wrong'
                if mutation == 'instagram': bad['object_story_spec']['instagram_user_id'] = 'wrong'
                if mutation == 'tags': bad['url_tags'] = 'wrong'
                if mutation == 'post': bad['object_story_id'] = 'fixed'
                if mutation == 'missing': bad.pop('media_sourcing_spec')
                with self.subTest(mutation=mutation): self.assertFalse(matches(bad, e))
        finally: review.CURRENT.reset(marker)

    def test_slot_payload_or_proof_changes_fail_closed(self):
        for mutation in ['creative', 'payload', 'proof', 'digest']:
            e, a, proof = self.fixture()
            if mutation == 'creative': a['id'] = 'foreign'
            if mutation == 'payload': e['url_tags'] = a['url_tags'] = 'changed'
            if mutation == 'proof': proof['verified'] = False
            if mutation == 'digest': proof['digest'] = 'wrong'
            marker = review.CURRENT.set(proof)
            try:
                with self.subTest(mutation=mutation): self.assertFalse(matches(a, e))
            finally: review.CURRENT.reset(marker)

if __name__ == '__main__': unittest.main()
