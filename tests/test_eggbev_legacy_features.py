"""Target rematerialization only; no transport or production writes."""
import copy
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_eggbev_source_cta import runner, afs, batch


def creative(features=None):
    c = afs()
    c['degrees_of_freedom_spec'] = {'creative_features_spec': features if features is not None else {
        'standard_enhancements': {'enroll_status': 'OPT_IN'},
        'advantage_plus_creative': {'enroll_status': 'OPT_OUT'},
        'pac_relaxation': {'enroll_status': 'OPT_IN', 'opaque': ['preserve']},
        'future_feature': {'enroll_status': 'OPT_IN', 'unknown': {'x': 1}},
    }, 'opaque_top_level': {'keep': True}}
    c['contextual_multi_ads'] = {'enroll_status': 'OPT_OUT'}
    return c


def resolve(c):
    return runner.source_rematerialization({'ads': [{'creative': c}]})[0][1]


class LegacyFeatureTests(unittest.TestCase):
    def test_removes_only_legacy_key(self):
        c = creative(); wanted = copy.deepcopy(c)
        del wanted['degrees_of_freedom_spec']['creative_features_spec']['standard_enhancements']
        self.assertEqual(resolve(c), wanted)

    def test_original_untouched_and_no_aliasing(self):
        c = creative(); before = copy.deepcopy(c); out = resolve(c)
        out['degrees_of_freedom_spec']['creative_features_spec']['pac_relaxation']['opaque'].append('changed')
        self.assertEqual(c, before)

    def test_idempotent(self):
        c = resolve(creative()); self.assertEqual(resolve(c), c)

    def test_absent_degrees_stays_absent(self):
        self.assertEqual(resolve(afs()), afs())

    def test_empty_degrees_preserved(self):
        c = afs(); c['degrees_of_freedom_spec'] = {}; self.assertEqual(resolve(c), c)

    def test_empty_features_preserved(self):
        c = creative({}); self.assertEqual(resolve(c), c)

    def test_no_legacy_preserves_all_individuals(self):
        c = creative(); c['degrees_of_freedom_spec']['creative_features_spec'].pop('standard_enhancements')
        self.assertEqual(resolve(c), c)

    def test_legacy_only_keeps_explicit_empty_map_not_defaults(self):
        c = creative({'standard_enhancements': {'enroll_status': 'OPT_OUT'}})
        expected = copy.deepcopy(c); expected['degrees_of_freedom_spec']['creative_features_spec'] = {}
        self.assertEqual(resolve(c), expected)

    def test_malformed_degrees_rejected(self):
        for value in [None, [], '', False]:
            c = afs(); c['degrees_of_freedom_spec'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'shape malformed'): resolve(c)

    def test_malformed_features_rejected(self):
        for value in [None, [], '', False]:
            c = creative(); c['degrees_of_freedom_spec']['creative_features_spec'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'shape malformed'): resolve(c)

    def test_malformed_legacy_enrollment_rejected(self):
        for value in [None, [], 'OPT_IN', {}, {'enroll_status': 'UNKNOWN'}]:
            c = creative({'standard_enhancements': value})
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'enrollment malformed'): resolve(c)

    def test_background_policy_still_applies_only_existing_feature(self):
        for status in ['OPT_IN', 'OPT_OUT']:
            c = creative(); c['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen'] = {'enroll_status': status, 'opaque': 4}
            wanted = copy.deepcopy(c); f = wanted['degrees_of_freedom_spec']['creative_features_spec']
            f.pop('standard_enhancements'); f['image_background_gen']['enroll_status'] = 'OPT_OUT'
            self.assertEqual(resolve(c), wanted)

    def test_unknown_background_enrollment_still_rejected(self):
        c = creative(); c['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen'] = {'enroll_status': 'UNKNOWN'}
        with self.assertRaisesRegex(ValueError, 'background policy'): resolve(c)

    def test_every_slot_prevalidated_before_build_media(self):
        for index in range(3):
            source = batch(); source['ads'][index]['creative'] = creative()
            source['ads'][index]['creative']['degrees_of_freedom_spec'] = None
            registry = Mock()
            with self.subTest(index=index), patch.object(runner, '_creative_payload') as payload:
                with self.assertRaises(ValueError): runner.build({}, source, {}, [{}, {}, {}], registry, {})
                registry.require_ready.assert_not_called(); payload.assert_not_called()

    def test_all_bad_slots_stop_before_pbia_save_reservation_or_prestage(self):
        cfg = {'state_root': 'synthetic', 'accounts': {runner.ACCOUNT: {'supported_modes': [runner.MODE]}}}
        for index in range(3):
            source = batch(); source['ads'][index]['creative']['degrees_of_freedom_spec'] = None
            with self.subTest(index=index), tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch') as tmp, ExitStack() as s:
                for name, value in [('request_load', {'request_id': 'synthetic-only'}), ('load', cfg), ('reader_block_reason', None), ('runtime', (None, None, None, 'synthetic-only')), ('source_read', source)]:
                    s.enter_context(patch.object(runner, name, return_value=value))
                writers = [s.enter_context(patch.object(runner, n, side_effect=AssertionError('writer forbidden'))) for n in ['resolve_page', 'save', 'MediaRegistry', 'OnDemandMediaPipeline']]
                writers.append(s.enter_context(patch.object(runner.naming, 'reserve', side_effect=AssertionError('reserve forbidden'))))
                with self.assertRaises(ValueError): runner.prepare(Path(tmp)/'synthetic.json', True)
                for writer in writers: writer.assert_not_called()

    def test_schema_still_prohibits_legacy_anywhere(self):
        from ares_campaign_v3.schema import AdSpec, ManifestError
        for c in [creative(), {'unknown': {'standard_enhancements': {}}}]:
            with self.subTest(c=c), self.assertRaisesRegex(ManifestError, 'standard_enhancements is prohibited'):
                AdSpec.from_dict({'name': 'test', 'source_ad_id': '123', 'creative_payload': c}, require_media=False)


if __name__ == '__main__': unittest.main()
