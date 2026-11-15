"""Exact source CTA normalization and pre-write ordering; offline only."""
import ast
import copy
import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))
RUNNER = Path(os.environ.get('MGS_TARGET_CLONE_TEST_RUNNER', str(ROOT / 'scripts/ares-eggbev-target-clone.py')))
spec = importlib.util.spec_from_file_location('eggbev_source_cta_runner', RUNNER)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def afs(cta='APPLY_NOW'):
    return {'asset_feed_spec': {'call_to_action_types': [cta]}, 'url_tags': 'utm_source=fb&utm_campaign=pg_23187&x=1'}


def native(cta='APPLY_NOW', branch='video_data'):
    return {'object_story_spec': {branch: {'call_to_action': {'type': cta, 'value': {'app_destination': 'MESSENGER', 'link': 'https://m.me/123'}}}}, 'url_tags': 'utm_campaign=pg_23187'}


def batch():
    return {'ads': [{'id': str(i), 'creative': c} for i, c in enumerate([native(), afs(), afs()], 1)]}


class ExactSourceCTATests(unittest.TestCase):
    def setUp(self):
        self.net = patch.object(socket, 'socket', side_effect=AssertionError('network forbidden'))
        self.net.start()
        self.addCleanup(self.net.stop)

    def test_afs_exact(self):
        self.assertEqual(runner.source_cta(afs()), 'APPLY_NOW')

    def test_native_video_exact(self):
        self.assertEqual(runner.source_cta(native()), 'APPLY_NOW')

    def test_native_link_exact(self):
        self.assertEqual(runner.source_cta(native('LEARN_MORE', 'link_data')), 'LEARN_MORE')

    def test_no_default_cta(self):
        self.assertEqual(runner.source_cta(afs('LEARN_MORE')), 'LEARN_MORE')

    def test_matching_afs_native_evidence(self):
        c = native(); c['asset_feed_spec'] = afs()['asset_feed_spec']
        self.assertEqual(runner.source_cta(c), 'APPLY_NOW')

    def test_matching_afs_action_evidence(self):
        c = afs(); c['asset_feed_spec']['call_to_actions'] = [native()['object_story_spec']['video_data']['call_to_action']]
        self.assertEqual(runner.source_cta(c), 'APPLY_NOW')

    def test_afs_native_conflict(self):
        c = native('LEARN_MORE'); c['asset_feed_spec'] = afs()['asset_feed_spec']
        with self.assertRaisesRegex(ValueError, 'conflict'): runner.source_cta(c)

    def test_afs_actions_conflict(self):
        c = afs(); c['asset_feed_spec']['call_to_actions'] = [{'type': 'LEARN_MORE'}]
        with self.assertRaisesRegex(ValueError, 'conflict'): runner.source_cta(c)

    def test_absence_and_malformed_shapes_fail_closed(self):
        for c in [None, {}, {'asset_feed_spec': None}, {'object_story_spec': []}, {'object_story_spec': {'video_data': None}}, {'object_story_spec': {'video_data': {'call_to_action': None}}}]:
            with self.subTest(creative=c), self.assertRaises(ValueError): runner.source_cta(c)

    def test_afs_empty_ambiguous_and_malformed_fail_closed(self):
        for value in [None, [], ['APPLY_NOW', 'LEARN_MORE'], ['APPLY_NOW', 'APPLY_NOW'], 'APPLY_NOW', [None], [''], ['apply_now'], [' APPLY_NOW']]:
            c = afs(); c['asset_feed_spec']['call_to_action_types'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): runner.source_cta(c)

    def test_native_missing_malformed_type_fail_closed(self):
        for value in [None, '', False, [], 'apply_now', 'APPLY_NOW ']:
            c = native(value)
            with self.subTest(value=value), self.assertRaises(ValueError): runner.source_cta(c)

    def test_invalid_afs_does_not_fallback_to_valid_native(self):
        c = native(); c['asset_feed_spec'] = {'call_to_action_types': []}
        with self.assertRaises(ValueError): runner.source_cta(c)

    def test_invalid_native_does_not_fallback_to_valid_afs(self):
        c = afs(); c['object_story_spec'] = {'video_data': {'call_to_action': {}}}
        with self.assertRaises(ValueError): runner.source_cta(c)

    def test_multiple_native_branches_ambiguous_even_if_equal(self):
        for value in ['APPLY_NOW', 'LEARN_MORE']:
            c = native(); c['object_story_spec'].update(native(value, 'link_data')['object_story_spec'])
            with self.subTest(value=value), self.assertRaises(ValueError): runner.source_cta(c)

    def test_explicit_destination_conflict_is_not_converted(self):
        for value in ['WHATSAPP', 'INSTAGRAM_DIRECT', None, 'messenger']:
            c = native(); c['object_story_spec']['video_data']['call_to_action']['value']['app_destination'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'destination'): runner.source_cta(c)

    def test_unsupported_native_shape_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unsupported'): runner.source_cta(native(branch='template_data'))

    def test_malformed_afs_actions_rejected(self):
        for value in [None, [], [{'type': 'APPLY_NOW'}, {'type': 'APPLY_NOW'}], [None]]:
            c = afs(); c['asset_feed_spec']['call_to_actions'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): runner.source_cta(c)

    def test_native_value_malformed_rejected(self):
        c = native(); c['object_story_spec']['video_data']['call_to_action']['value'] = None
        with self.assertRaises(ValueError): runner.source_cta(c)

    def test_source_and_snapshot_preserved(self):
        source = batch(); old = copy.deepcopy(source)
        result = runner.source_rematerialization(source)
        self.assertEqual([c for c, _ in result], ['APPLY_NOW'] * 3)
        result[0][1]['url_tags'] = 'modified-return-only'
        self.assertEqual(source, old)

    def test_late_bad_slot_rejected_before_registry_or_payload(self):
        for index in range(3):
            source = batch(); source['ads'][index]['creative'] = {}
            registry = Mock()
            with self.subTest(index=index), patch.object(runner, '_creative_payload') as payload:
                with self.assertRaisesRegex(ValueError, 'CTA'): runner.build({}, source, {}, [{}, {}, {}], registry, {})
                registry.require_ready.assert_not_called(); payload.assert_not_called()

    def test_late_tracking_and_policy_failure_rejected(self):
        for change in ['missing', 'ambiguous', 'policy']:
            source = batch(); c = source['ads'][-1]['creative']
            if change == 'missing': c['url_tags'] = ''
            elif change == 'ambiguous': c['url_tags'] = 'utm_campaign=pg_1&utm_campaign=pg_2'
            else: c['degrees_of_freedom_spec'] = {'creative_features_spec': {'image_background_gen': {'enroll_status': 'UNKNOWN'}}}
            with self.subTest(change=change), self.assertRaises(ValueError): runner.source_rematerialization(source)

    def test_preflight_ast_precedes_all_side_effects(self):
        tree = ast.parse(RUNNER.read_text()); f = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare')
        calls = [(n.lineno, ast.unparse(n.func)) for n in ast.walk(f) if isinstance(n, ast.Call)]
        check = next(line for line, name in calls if name == 'source_rematerialization')
        for line, name in calls:
            if name in {'resolve_page', 'save', 'naming.reserve', 'creation.reserve_inventory', 'OnDemandMediaPipeline', 'MediaRegistry'}:
                self.assertLess(check, line, name)

    def test_synthetic_preflight_rejects_before_any_writer(self):
        # Fully mocked temporary input only; never run a live prepare/execute.
        cfg = {'state_root': 'synthetic', 'accounts': {runner.ACCOUNT: {'supported_modes': [runner.MODE]}}}
        for change in ['cta', 'tracking', 'policy']:
            source = batch(); c = source['ads'][-1]['creative']
            if change == 'cta': c.pop('asset_feed_spec')
            elif change == 'tracking': c['url_tags'] = ''
            else: c['degrees_of_freedom_spec'] = {'creative_features_spec': {'image_background_gen': {'enroll_status': 'UNKNOWN'}}}
            with self.subTest(change=change), tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch') as tmp, ExitStack() as stack:
                stack.enter_context(patch.object(runner, 'request_load', return_value={'request_id': 'synthetic-only'}))
                stack.enter_context(patch.object(runner, 'load', return_value=cfg))
                stack.enter_context(patch.object(runner, 'reader_block_reason', return_value=None))
                stack.enter_context(patch.object(runner, 'runtime', return_value=(None, None, None, 'synthetic-only')))
                stack.enter_context(patch.object(runner, 'source_read', return_value=source))
                writers = [stack.enter_context(patch.object(runner, name, side_effect=AssertionError('writer forbidden'))) for name in ['resolve_page', 'save', 'MediaRegistry', 'OnDemandMediaPipeline']]
                reserve = stack.enter_context(patch.object(runner.naming, 'reserve', side_effect=AssertionError('reserve forbidden')))
                with self.assertRaises(ValueError): runner.prepare(Path(tmp)/'synthetic.json', True)
                for writer in writers + [reserve]: writer.assert_not_called()


if __name__ == '__main__': unittest.main()
