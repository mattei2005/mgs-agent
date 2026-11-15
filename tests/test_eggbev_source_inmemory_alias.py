"""Offline live-shape regression: classify -> normalizer -> native comparator.

Real preserved JSONs supply source values; the fetcher supplies explicitly
synthetic test bytes. No request preparation, Engine, network or production write.
"""
import copy
import importlib.util
import json
import os
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))
from ares_campaign_v3 import native_thumbnail_equivalence as native

SPEC = importlib.util.spec_from_file_location('inmemory_alias_runner', os.environ.get('MGS_ALIAS_RUNNER', str(ROOT / 'scripts/ares-eggbev-target-clone.py')))
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
HOME = ROOT / 'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937'
TECH = ROOT / 'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23187-1570285402068091011'
BODY = b'\xff\xd8\xffoffline-alias-regression-only'
CONTEXT = dict(request_id='offline-source-alias-regression', approved_digest='a' * 64,
               account_id=runner.ACCOUNT, source_campaign_id='120251175890330629')


class InMemorySourceTests(unittest.TestCase):
    def setUp(self):
        for name in ('socket', 'create_connection'):
            guard = patch.object(socket, name, side_effect=AssertionError('offline: network forbidden'))
            guard.start(); self.addCleanup(guard.stop)
        for name in ('CampaignEngine', 'runtime', 'save'):
            guard = patch.object(runner, name, side_effect=AssertionError('offline: effects forbidden'))
            guard.start(); self.addCleanup(guard.stop)
        self.original = json.loads((HOME / 'source-live.json').read_text())
        self.raw = json.loads((HOME / 'source-current-before-resume-20261115T043056494871Z.json').read_text())
        self.technical = json.loads((TECH / 'source-live.json').read_text())
        self.fetch = Mock(return_value=BODY)

    def classify(self, source=None):
        s = self.raw if source is None else source
        return runner.classify_source(s['campaign'], [s['adset']], s['all_ads'],
                                      len(s['ads']), s['source_selection']['proof'])

    def compare(self, current, original=None):
        original = self.original if original is None else original
        context = dict(CONTEXT, source_campaign_id=original['campaign']['id'])
        return native.compare(original, current, context=context,
                              normalize=runner.source_comparison, fetcher=self.fetch)

    def test_ordinary_lists_independent(self):
        s = self.classify()
        self.assertIsNot(s['ads'], s['all_ads'])
        self.assertIsNot(s['technical_seed_ads'], s['ads'])
        self.assertIsNot(s['technical_seed_ads'], s['all_ads'])

    def test_ordinary_objects_and_nested_values_independent(self):
        s = self.classify(); before = copy.deepcopy(self.raw)
        self.assertIsNot(s['ads'][0], s['all_ads'][0])
        self.assertIsNot(s['ads'][0]['creative'], s['all_ads'][0]['creative'])
        s['ads'][0]['creative']['object_story_spec']['video_data']['message'] = 'offline edit'
        self.assertEqual(s['all_ads'], before['all_ads'])
        self.assertEqual(self.raw, before)

    def test_ordinary_exact_raw_values_and_literal_order_preserved(self):
        before = copy.deepcopy(self.raw); s = self.classify()
        self.assertEqual(s, self.raw)
        order = ['120251177068760629', '120251177043210629', '120251176981530629']
        self.assertEqual([a['id'] for a in s['ads']], order)
        normalized = runner.source_comparison(s)
        self.assertEqual([a['id'] for a in normalized['ads']], order)
        self.assertEqual(normalized['all_ads'], sorted(normalized['all_ads'], key=lambda a: a['id']))
        self.assertEqual(s, before); self.assertEqual(self.raw, before)

    def test_ordinary_normalization_matches_independent_original_json(self):
        s = self.classify(self.original)
        self.assertEqual(runner.source_comparison(s), runner.source_comparison(self.original))
        self.assertEqual(runner.source_comparison(s), runner.source_comparison(json.loads(json.dumps(s))))
        self.compare(s); self.fetch.assert_not_called()

    def test_actual_live_classify_native_rotation_strict_bytes_and_raw_intact(self):
        before = copy.deepcopy((self.original, self.raw)); s = self.classify()
        a, b = runner.source_comparison(self.original), runner.source_comparison(s)
        paths = native._diff(a, b)
        self.assertEqual(len(paths), 2)
        self.assertEqual({p[0] for p in paths}, {'ads', 'all_ads'})
        self.assertTrue(all(tuple(p[2:]) == ('creative', 'object_story_spec', 'video_data', 'image_url') for p in paths))
        receipt = self.compare(s)
        self.assertEqual(len(receipt['entries']), 2); self.assertEqual(self.fetch.call_count, 2)
        self.assertTrue(all(e['original_bytes_sha256'] == e['current_bytes_sha256'] for e in receipt['entries']))
        self.assertTrue(native.verify_receipt(receipt, expected_sha256=native.digest(receipt),
                       original=self.original, current=s, context=CONTEXT, normalize=runner.source_comparison))
        self.assertEqual((self.original, self.raw), before); self.assertEqual(s, self.raw)

    def test_actual_live_bytes_difference_rejected(self):
        self.fetch.side_effect = [BODY, BODY[:-1] + b'!']
        with self.assertRaisesRegex(ValueError, 'bytes differ'): self.compare(self.classify())

    def test_actual_reorder_not_normalized(self):
        raw = copy.deepcopy(self.raw); raw['all_ads'].reverse(); s = self.classify(raw)
        self.assertEqual([a['id'] for a in s['ads']], [a['id'] for a in raw['all_ads']])
        with self.assertRaises(ValueError): self.compare(s)
        self.fetch.assert_not_called()

    def test_actual_id_drift_rejected(self):
        raw = copy.deepcopy(self.raw); raw['all_ads'][0]['id'] = '999999'
        with self.assertRaises(ValueError): self.compare(self.classify(raw))
        self.fetch.assert_not_called()

    def test_actual_status_drift_rejected(self):
        raw = copy.deepcopy(self.raw); ad = raw['all_ads'][0]
        ad['status'] = 'ACTIVE' if ad['status'] == 'PAUSED' else 'PAUSED'
        with self.assertRaises(ValueError): self.compare(self.classify(raw))
        self.fetch.assert_not_called()

    def test_actual_commercial_deltas_rejected_before_download(self):
        paths = [(['campaign', 'status'], 'PAUSED'), (['adset', 'targeting', 'age_min'], 80),
                 (['all_ads', 0, 'creative', 'url_tags'], 'offline-changed'),
                 (['all_ads', 0, 'creative', 'object_story_spec', 'video_data', 'message'], 'changed'),
                 (['all_ads', 0, 'creative', 'object_story_spec', 'video_data', 'video_id'], '99999'),
                 (['all_ads', 0, 'creative', 'object_story_spec', 'video_data', 'call_to_action', 'type'], 'LEARN_MORE')]
        for path, value in paths:
            with self.subTest(path=path):
                raw = copy.deepcopy(self.raw); node = raw
                for key in path[:-1]: node = node[key]
                node[path[-1]] = value
                with self.assertRaises(ValueError): self.compare(self.classify(raw))
                self.fetch.assert_not_called()

    def test_technical_lists_objects_and_proof_independent(self):
        s = self.classify(self.technical)
        for a, b in [('ads', 'all_ads'), ('ads', 'technical_seed_ads'), ('all_ads', 'technical_seed_ads')]:
            self.assertIsNot(s[a], s[b])
            for left in s[a]:
                for right in s[b]:
                    if left['id'] == right['id']:
                        self.assertIsNot(left, right); self.assertIsNot(left['creative'], right['creative'])
        self.assertIsNot(s['source_selection']['proof'], self.technical['source_selection']['proof'])
        before = copy.deepcopy(s['all_ads'])
        s['technical_seed_ads'][0]['creative']['offline_only'] = True
        self.assertEqual(s['all_ads'], before)

    def test_technical_exact_order_values_and_pure_normalization(self):
        before = copy.deepcopy(self.technical); s = self.classify(self.technical)
        self.assertEqual(s, before)
        norm = runner.source_comparison(s)
        self.assertEqual([a['id'] for a in norm['ads']], [a['id'] for a in before['ads']])
        self.assertEqual(norm, runner.source_comparison(json.loads(json.dumps(s))))
        self.compare(s, original=self.technical); self.fetch.assert_not_called()
        self.assertEqual(s, before); self.assertEqual(self.technical, before)

    def test_technical_reordered_proof_slots_fail_comparison(self):
        raw = copy.deepcopy(self.technical); raw['source_selection']['proof']['pairs'].reverse()
        with self.assertRaises(ValueError): self.compare(self.classify(raw), original=self.technical)
        self.fetch.assert_not_called()

    def test_technical_seed_status_and_lineage_fail_classification(self):
        seed_id = self.technical['source_selection']['proof']['pairs'][0][1]
        for key, value in [('status', 'ACTIVE'), ('source_ad_id', '99999'), ('id', '99999')]:
            with self.subTest(field=key):
                raw = copy.deepcopy(self.technical)
                next(a for a in raw['all_ads'] if a['id'] == seed_id)[key] = value
                with self.assertRaises(ValueError): self.classify(raw)
        self.fetch.assert_not_called()

    def test_technical_seed_copy_drift_fail_comparison(self):
        raw = copy.deepcopy(self.technical); seed_id = raw['source_selection']['proof']['pairs'][0][1]
        next(a for a in raw['all_ads'] if a['id'] == seed_id)['name'] += ' unauthorized'
        with self.assertRaises(ValueError): self.compare(self.classify(raw), original=self.technical)
        self.fetch.assert_not_called()

    def test_technical_seed_edge_mutation_cannot_hide_via_alias(self):
        current = self.classify(self.technical)
        current['technical_seed_ads'][0]['status'] = 'ACTIVE'
        with self.assertRaises(ValueError): self.compare(current, original=self.technical)
        self.fetch.assert_not_called()


if __name__ == '__main__': unittest.main()
