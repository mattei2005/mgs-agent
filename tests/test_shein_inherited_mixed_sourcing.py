"""Pure-clone inherited variants: exact source-bound QA, never new-media waiver."""
import copy
import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3.creative_media import matches
from ares_campaign_v3 import shein_qa

class InheritedMixedSourcingTests(unittest.TestCase):
    def fixture(self):
        source = {
            'id': '123456', 'instagram_user_id': '200',
            'object_story_spec': {'page_id': '100', 'instagram_user_id': '200',
                'link_data': {'image_hash': 'primary', 'name': 'Title', 'message': 'Body',
                    'link': 'https://example.invalid/?utm_campaign=c34',
                    'call_to_action': {'type': 'LEARN_MORE', 'value': {'link': 'https://example.invalid/?utm_campaign=c34'}}}},
            'asset_feed_spec': {'optimization_type': 'DEGREES_OF_FREEDOM',
                'titles': [{'text': 'Title'}], 'bodies': [{'text': 'Body'}]},
            'media_sourcing_spec': {'titles': [{'text': 'Title'}], 'bodies': [{'text': 'Body'}],
                'images': [
                    {'hash': 'pad', 'source': 'padding', 'opt_in_status': 'opt_in',
                     'url': 'https://example.invalid/pad.jpg', 'variant_types': ['SQUARE']},
                    {'hash': 'uncrop', 'source': 'uncrop', 'opt_in_status': 'opt_out',
                     'url': 'https://example.invalid/uncrop.jpg', 'variant_types': ['VERTICAL']},
                    {'hash': 'recomp', 'source': 'recomposition', 'opt_in_status': 'opt_in',
                     'url': 'https://example.invalid/recomp.jpg', 'variant_types': ['FULLSCREEN_VERTICAL']},
                    {'hash': 'primary', 'source': 'multi_media', 'opt_in_status': 'opt_in'}]},
            'contextual_multi_ads': {'enroll_status': 'OPT_OUT'}, 'url_tags': ''}
        expected = copy.deepcopy(source); expected.pop('id')
        expected['object_story_spec']['link_data']['link'] = 'https://example.invalid/?utm_campaign=c36'
        expected['object_story_spec']['link_data']['call_to_action']['value']['link'] = 'https://example.invalid/?utm_campaign=c36'
        actual = copy.deepcopy(expected); actual['id'] = '654321'; actual.pop('url_tags')
        return source, expected, actual

    def bound_matches(self, actual, expected, source):
        # Pre-fix reproduction must fail on semantic rejection, not a new-API TypeError.
        if 'source_creative' not in inspect.signature(matches).parameters:
            return matches(actual, expected)
        return matches(actual, expected, source_creative=source)

    def test_exact_inherited_variants_are_recognized_only_with_source(self):
        source, expected, actual = self.fixture()
        before = copy.deepcopy((source, expected, actual))
        self.assertFalse(matches(actual, expected))
        self.assertTrue(self.bound_matches(actual, expected, source))
        self.assertEqual((source, expected, actual), before)

    def test_actual_drift_in_any_material_dimension_is_rejected(self):
        for kind in ['hash', 'variant_hash', 'variant_source', 'enrollment', 'variant_type',
                     'variant_url', 'missing_variant', 'extra_variant', 'order', 'copy',
                     'feed', 'sourcing_text', 'page', 'instagram', 'link', 'cta', 'tags',
                     'contextual', 'fixed_post', 'extra_video', 'extra_related']:
            with self.subTest(kind=kind):
                source, expected, actual = self.fixture()
                rows = actual['media_sourcing_spec']['images']; ld = actual['object_story_spec']['link_data']
                if kind == 'hash': ld['image_hash'] = 'wrong'
                if kind == 'variant_hash': rows[0]['hash'] = 'wrong'
                if kind == 'variant_source': rows[0]['source'] = 'gen_ai'
                if kind == 'enrollment': rows[0]['opt_in_status'] = 'opt_out'
                if kind == 'variant_type': rows[0]['variant_types'] = ['VERTICAL']
                if kind == 'variant_url': rows[0]['url'] = 'https://example.invalid/other.jpg'
                if kind == 'missing_variant': rows.pop(0)
                if kind == 'extra_variant': rows.append(copy.deepcopy(rows[0]))
                if kind == 'order': rows.reverse()
                if kind == 'copy': ld['message'] = 'Changed'
                if kind == 'feed': actual['asset_feed_spec']['titles'][0]['text'] = 'Changed'
                if kind == 'sourcing_text': actual['media_sourcing_spec']['titles'][0]['text'] = 'Changed'
                if kind == 'page': actual['object_story_spec']['page_id'] = '999'
                if kind == 'instagram': actual['instagram_user_id'] = '999'
                if kind == 'link': ld['link'] = 'https://example.invalid/?utm_campaign=wrong'
                if kind == 'cta': ld['call_to_action']['type'] = 'SHOP_NOW'
                if kind == 'tags': actual['url_tags'] = 'utm_campaign=wrong'
                if kind == 'contextual': actual['contextual_multi_ads']['enroll_status'] = 'OPT_IN'
                if kind == 'fixed_post': actual['object_story_id'] = '100_200'
                if kind == 'extra_video': actual['media_sourcing_spec']['videos'] = []
                if kind == 'extra_related': actual['media_sourcing_spec']['related_media'] = {}
                self.assertFalse(self.bound_matches(actual, expected, source))

    def test_expected_cannot_invent_variants_or_switch_primary_from_source(self):
        for kind in ['hash', 'sourcing', 'page', 'instagram', 'source_identity', 'source_post', 'unknown_source', 'video', 'feed_media']:
            with self.subTest(kind=kind):
                source, expected, actual = self.fixture()
                if kind == 'hash': expected['object_story_spec']['link_data']['image_hash'] = 'wrong'
                if kind == 'sourcing': expected['media_sourcing_spec']['images'][0]['hash'] = 'wrong'
                if kind == 'page': expected['object_story_spec']['page_id'] = '999'
                if kind == 'instagram': expected['object_story_spec']['instagram_user_id'] = '999'
                if kind == 'source_identity': source.pop('id')
                if kind == 'source_post': source['object_story_id'] = '100_200'
                if kind == 'unknown_source':
                    source['media_sourcing_spec']['images'][0]['source'] = 'unknown'
                    expected['media_sourcing_spec']['images'][0]['source'] = 'unknown'
                if kind == 'video': expected['media_sourcing_spec']['videos'] = []
                if kind == 'feed_media': expected['asset_feed_spec']['images'] = [{'hash': 'extra'}]
                actual = copy.deepcopy(expected); actual['id'] = '654321'
                self.assertFalse(self.bound_matches(actual, expected, source))

    def test_semantic_readback_binds_source_lineage_and_rejects_mixed_variant_drift(self):
        from ares_campaign_v3.shein_single_clone import verify_readback
        source, expected, actual = self.fixture()
        when = '2030-11-24T00:00:00-05:00'
        spec = {'mode': 'pure_clone', 'creative_materialization_route': 'source_definition_two_phase',
            'account_id': '500', 'name': 'C036', 'status': 'PAUSED', 'start_time': when,
            'idempotency_key': 'unit-36', 'adset_name': 'SET', 'campaign_updates': {'daily_budget': '10000'},
            'ads': [{'name': 'AD', 'source_ad_id': '300', 'creative_payload': expected}]}
        payload = {'request_id': 'unit-inherited', 'campaigns': [spec]}
        src = {'adset': {'targeting': {}}, 'ads': [{'id': '300', 'creative': source}]}
        live = {'campaign': {'id': '600', 'account_id': '500', 'name': 'C036', 'status': 'PAUSED',
                    'effective_status': 'PAUSED', 'start_time': when, 'daily_budget': '10000'},
            'adsets': {'data': [{'id': '700', 'name': 'SET', 'status': 'PAUSED', 'start_time': when, 'targeting': {}}]},
            'ads': {'data': [{'id': '400', 'name': 'AD', 'status': 'PAUSED', 'adset_id': '700', 'source_ad_id': '300', 'creative': actual}]}}
        self.assertEqual(verify_readback(payload, src, live), [])
        bad = copy.deepcopy(live); bad['ads']['data'][0]['creative']['media_sourcing_spec']['images'][0]['hash'] = 'wrong'
        with self.assertRaises(ValueError): verify_readback(payload, src, bad)
        bad_source = copy.deepcopy(src); bad_source['ads'].append(copy.deepcopy(src['ads'][0]))
        with self.assertRaises(ValueError): verify_readback(payload, bad_source, live)

    def test_activation_rechecks_the_complete_inherited_sourcing(self):
        from types import SimpleNamespace as NS
        from ares_campaign_v3.activation import validate_live
        source, expected, actual = self.fixture()
        when = '2030-11-24T00:00:00-05:00'
        spec = NS(mode='pure_clone', creative_materialization_route='source_definition_two_phase',
            start_time=when, account_id='500', name='C036', bid_override=False, reference=None,
            ads=[NS(name='AD', media=None, creative_payload=expected)])
        tree = {'campaign': {'id': '600', 'account_id': '500', 'name': 'C036', 'status': 'PAUSED',
                    'start_time': when, 'daily_budget': '10000', 'bid_strategy': 'COST_CAP'},
            'adsets': {'data': [{'id': '700', 'name': 'SET', 'status': 'PAUSED', 'start_time': when}]},
            'ads': {'data': [{'id': '400', 'name': 'AD', 'status': 'PAUSED', 'adset_id': '700', 'source_ad_id': '300', 'creative': actual}]}}
        validate_live(tree, copy.deepcopy(tree), spec)
        bad = copy.deepcopy(tree); bad['ads']['data'][0]['creative']['media_sourcing_spec']['images'][0]['hash'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'inherited source variants drift'):
            validate_live(bad, tree, spec)

    def test_media_qa_uses_source_binding_only_for_pure_definition_clone(self):
        source, expected, actual = self.fixture()
        slot = {'name': 'AD 1', 'source_ad_id': '300', 'creative_payload': expected}
        desired = {'mode': 'pure_clone', 'creative_materialization_route': 'source_definition_two_phase', 'ads': [slot]}
        live = {'ads': {'data': [{'id': '400', 'name': 'AD 1', 'source_ad_id': '300', 'creative': actual}]}}
        src = {'ads': [{'id': '300', 'creative': source}]}
        class Common:
            def graph_batch_get(self, token, requests):
                return 200, [{'name': '400', 'code': 200, 'body': {'data': [{'body': '<iframe src="https://example.invalid/preview"></iframe>'}]}}], {}
        with patch.object(shein_qa, 'render_previews', return_value=[{'images': [{'width': 100, 'height': 100}]}]):
            proof = shein_qa.verify_media(Common(), 'fake-offline', live, desired, src, {'enabled': True, 'chrome_path': '/not-used'})
        self.assertTrue(proof['verified']); self.assertEqual(proof['ad_ids'], ['400'])
        for change in [{'mode': 'clone_prestaged'}, {'creative_materialization_route': 'existing_post_two_phase'}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                shein_qa.verify_media(Common(), 'fake-offline', live, {**desired, **change}, src, {'enabled': True})

if __name__ == '__main__':
    unittest.main()
