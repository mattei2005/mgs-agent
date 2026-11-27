"""Offline regression: exact nested OPT_IN review, with all strict gates kept."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ares_campaign_v3 import reviewed_copy_omissions as r
from ares_campaign_v3.creative_copy_policy import effective, verify_creative
from ares_campaign_v3.shein_continuation import content_digest
from test_reviewed_copy_omissions import ReviewedCopyOmissionsTests

NESTED = {'enroll_status': 'OPT_IN', 'customizations': {
    'text_extraction': {'enroll_status': 'OPT_IN'}}}
KEYS = ['enhance_cta', 'inline_comment', 'text_optimizations', 'text_translation']


class ReviewedCopyCustomizationsTests(unittest.TestCase):
    def fixture(self):
        helper = ReviewedCopyOmissionsTests()
        receipt, state, checkpoint, messages = helper.fixture()
        receipt, state = copy.deepcopy(receipt), copy.deepcopy(state)
        for campaign in state['manifest']['campaigns']:
            for ad in campaign['ads']:
                features = ad['creative_payload']['degrees_of_freedom_spec']['creative_features_spec']
                for key in KEYS:
                    features[key] = copy.deepcopy(NESTED if key in {'enhance_cta', 'text_optimizations'}
                                                   else {'enroll_status': 'OPT_IN'})
        receipt['accepted_omissions'] = list(KEYS)
        receipt['binding'] = r.binding(state, checkpoint)
        grant = {'account_id': checkpoint['account_id'], 'approval_id': receipt['approval_id'],
                 'approved_by': receipt['approved_by'], 'receipt_digest': content_digest(receipt)}
        # Sandbox only. No production grant, transport, or Meta write in tests.
        directory = Path(tempfile.mkdtemp(prefix='review-customizations-', dir=os.environ.get('TMPDIR')))
        index = directory / 'policy.json'
        index.write_text(json.dumps({'requests': {state['request']['request_id']: grant}}))
        with patch.object(r, 'POLICY_INDEX', index):
            proof = r.validate(receipt, state, checkpoint, get_message=helper.get(messages))
        return receipt, state, proof

    def payload(self, receipt, state):
        slot = receipt['binding']['slots'][0]
        campaign = next(c for c in state['manifest']['campaigns'] if c['idempotency_key'] == slot['key'])
        expected = effective(next(a['creative_payload'] for a in campaign['ads']
                                  if a['source_ad_id'] == slot['source_ad_id']))
        actual = copy.deepcopy(expected)
        actual['id'] = slot['creative_id']
        for key in KEYS:
            del actual['degrees_of_freedom_spec']['creative_features_spec'][key]
        return expected, actual

    def test_known_shapes_only_and_no_mutation(self):
        for key in KEYS:
            self.assertTrue(r._reviewable_opt_in(key, {'enroll_status': 'OPT_IN'}))
        for key in ['enhance_cta', 'text_optimizations']:
            value = copy.deepcopy(NESTED)
            self.assertTrue(r._reviewable_opt_in(key, value))
            self.assertEqual(value, NESTED)
        self.assertFalse(r._reviewable_opt_in('inline_comment', NESTED))
        self.assertFalse(r._reviewable_opt_in('unapproved_feature', NESTED))
        invalid = [None, {}, 'OPT_IN', {'enroll_status': 'OPT_OUT'},
                   {'enroll_status': 'OPT_IN', 'customizations': {}},
                   {'enroll_status': 'OPT_IN', 'customizations': {'text_extraction': {'enroll_status': 'OPT_OUT'}}},
                   {'enroll_status': 'OPT_IN', 'customizations': {'unknown': {'enroll_status': 'OPT_IN'}}},
                   {**NESTED, 'extra': True}]
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(r._reviewable_opt_in('enhance_cta', value))

    def test_validate_and_verify_keep_sealed_payloads_unchanged(self):
        receipt, state, proof = self.fixture()
        expected, actual = self.payload(receipt, state)
        original_state, original_expected = copy.deepcopy(state), copy.deepcopy(expected)
        with self.assertRaises(ValueError):
            verify_creative(actual, expected)
        marker = r.CURRENT.set(proof)
        try:
            verify_creative(actual, expected)
            self.assertEqual(state, original_state)
            self.assertEqual(expected, original_expected)
        finally:
            r.CURRENT.reset(marker)

    def test_review_does_not_accept_other_drift(self):
        receipt, state, proof = self.fixture()
        expected, actual = self.payload(receipt, state)
        marker = r.CURRENT.set(proof)
        try:
            for kind in ['explicit_out', 'subset', 'new_in', 'creative', 'payload']:
                bad, wanted = copy.deepcopy(actual), copy.deepcopy(expected)
                features = bad['degrees_of_freedom_spec']['creative_features_spec']
                if kind == 'explicit_out':
                    features['enhance_cta'] = {'enroll_status': 'OPT_OUT'}
                elif kind == 'subset':
                    features['enhance_cta'] = copy.deepcopy(NESTED)
                elif kind == 'new_in':
                    features['unapproved_feature'] = {'enroll_status': 'OPT_IN'}
                elif kind == 'creative':
                    bad['id'] = 'foreign'
                else:
                    wanted['url_tags'] = 'changed'
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    verify_creative(bad, wanted)
        finally:
            r.CURRENT.reset(marker)


if __name__ == '__main__':
    unittest.main()
