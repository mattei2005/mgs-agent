#!/usr/bin/env python3
import datetime as dt
import importlib.util
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
NY = ZoneInfo('America/New_York')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guardrail = load_module(
    'eggbev_zero_pixel_guardrail_test',
    BASE / 'scripts/ares-eggbev-zero-pixel-guardrail.py',
)


class EggbevZeroPixelGuardrailTests(unittest.TestCase):
    def setUp(self):
        self.policy = {
            'spend_threshold_usd': 2.0,
            'after_hour_et': 3,
            'pixel_event': {
                'pixel_id': '935354115143283',
                'custom_event_type': 'OTHER',
                'custom_event_str': 'eggbev-pv-u',
                'insights_action_type': 'offsite_conversion.fb_pixel_custom',
            },
        }
        self.campaign = {
            'id': 'c1',
            'name': '162 - Amy Shook - ENG - US - (pg_5024) C001',
            'status': 'ACTIVE',
            'configured_status': 'ACTIVE',
            'effective_status': 'ACTIVE',
        }
        self.adset = {
            'id': 's1',
            'campaign_id': 'c1',
            'status': 'ACTIVE',
            'configured_status': 'ACTIVE',
            'effective_status': 'ACTIVE',
            'optimization_goal': 'OFFSITE_CONVERSIONS',
            'promoted_object': {
                'pixel_id': '935354115143283',
                'custom_event_type': 'OTHER',
                'custom_event_str': 'eggbev-pv-u',
            },
        }

    def insight(self, spend, results=None):
        actions = [] if results is None else [{
            'action_type': 'offsite_conversion.fb_pixel_custom',
            'value': str(results),
        }]
        return {
            'campaign_id': 'c1',
            'campaign_name': self.campaign['name'],
            'spend': str(spend),
            'actions': actions,
        }

    def plan(self, spend, results=0, adsets=None):
        return guardrail.plan_guardrail(
            [self.campaign],
            [self.adset] if adsets is None else adsets,
            [self.insight(spend, results)],
            self.policy,
        )

    def test_internal_gate_starts_at_03_et(self):
        self.assertFalse(guardrail.after_daily_gate(dt.datetime(2026, 9, 1, 2, 59, tzinfo=NY), 3))
        self.assertTrue(guardrail.after_daily_gate(dt.datetime(2026, 9, 1, 3, 0, tzinfo=NY), 3))

    def test_spend_strictly_over_two_and_zero_pixel_result_is_candidate(self):
        plan = self.plan(2.01, 0)
        self.assertEqual(plan['counts']['candidates'], 1)
        self.assertEqual(plan['candidates'][0]['reason'], 'spend_strictly_over_threshold_after_03_and_zero_pixel_results')

    def test_exactly_two_dollars_is_not_candidate(self):
        self.assertEqual(self.plan(2.00, 0)['candidates'], [])

    def test_any_pixel_result_keeps_campaign_active(self):
        self.assertEqual(self.plan(100, 1)['candidates'], [])

    def test_missing_action_is_zero_result(self):
        self.assertEqual(self.plan(2.01, None)['counts']['candidates'], 1)

    def test_wrong_pixel_event_mapping_blocks_write_and_creates_issue(self):
        wrong = {**self.adset, 'promoted_object': {**self.adset['promoted_object'], 'custom_event_str': 'other-event'}}
        plan = self.plan(2.01, 0, [wrong])
        self.assertEqual(plan['candidates'], [])
        self.assertEqual(plan['issues'][0]['issue'], 'pixel_promoted_object_mismatch')

    def test_unrelated_custom_actions_do_not_count_as_target_result(self):
        row = self.insight(2.01, 0)
        row['actions'] = [{'action_type': 'offsite_conversion.fb_pixel_purchase', 'value': '99'}]
        plan = guardrail.plan_guardrail([self.campaign], [self.adset], [row], self.policy)
        self.assertEqual(plan['counts']['candidates'], 1)

    def test_action_alert_is_four_lines_and_explicit(self):
        candidate = self.plan(2.01, 0)['candidates'][0]
        message = guardrail.build_action_alert([candidate], [{'ok': True}], dt.datetime(2026, 9, 1, 3, 3, tzinfo=NY))
        self.assertEqual(len(message.splitlines()), 4)
        self.assertIn('spend > US$2', message)
        self.assertIn('Eggbev PV U = 0', message)
        self.assertIn('Pausadas/readback: **1/1**', message)

    def test_runtime_rate_limit_alert_is_sanitized_and_four_lines(self):
        code, message = guardrail.build_runtime_error_alert(
            dt.datetime(2026, 9, 1, 3, 8, tzinfo=NY),
            'Eggbev-US-CC-EN-01-G006',
            'Meta batch child insights failed: HTTP 400; {"code": 17, "fbtrace_id": "secret-trace"}',
        )
        self.assertEqual(code, 'meta_read_rate_limited')
        self.assertEqual(len(message.splitlines()), 4)
        self.assertNotIn('secret-trace', message)
        self.assertIn('novos writes: **bloqueados**', message)

    def test_live_snapshot_normal_path_uses_two_batch_children(self):
        class FakeMeta:
            requests = []

            @staticmethod
            def safe_meta_error(body):
                return body

            @classmethod
            def graph_batch_get(cls, token, requests):
                cls.requests = requests
                responses = []
                for request in requests:
                    body = {'id': 'account', 'account_status': 1, 'currency': 'USD', 'timezone_name': 'America/New_York'} if request['name'] == 'account' else {'data': []}
                    responses.append({'name': request['name'], 'code': 200, 'body': body})
                return 200, responses, {}

        snapshot = guardrail.fetch_live_snapshot(FakeMeta, 'token-not-printed', 'act_1', self.policy)
        self.assertEqual(len(FakeMeta.requests), 2)
        self.assertEqual(set(snapshot), {'account', 'account_preflight_performed', 'campaigns', 'adsets', 'insights', 'metric_risk_campaign_ids'})
        self.assertFalse(snapshot['account_preflight_performed'])

    def test_live_snapshot_reads_account_and_target_adsets_only_after_metric_risk(self):
        campaign = self.campaign
        adset = self.adset

        class FakeMeta:
            calls = []

            @staticmethod
            def safe_meta_error(body):
                return body

            @classmethod
            def graph_batch_get(cls, token, requests):
                cls.calls.append(requests)
                rows = []
                for request in requests:
                    name = request['name']
                    if name == 'campaigns':
                        body = {'data': [campaign]}
                    elif name == 'insights':
                        body = {'data': [{'campaign_id': 'c1', 'spend': '2.01', 'actions': []}]}
                    elif name == 'account':
                        body = {'id': 'account', 'account_status': 1, 'currency': 'USD', 'timezone_name': 'America/New_York'}
                    else:
                        body = {'data': [adset]}
                    rows.append({'name': name, 'code': 200, 'body': body})
                return 200, rows, {}

        snapshot = guardrail.fetch_live_snapshot(FakeMeta, 'token-not-printed', 'act_1', self.policy)
        self.assertEqual(len(FakeMeta.calls), 2)
        self.assertEqual([request['name'] for request in FakeMeta.calls[0]], ['campaigns', 'insights'])
        self.assertEqual([request['name'] for request in FakeMeta.calls[1]], ['account', 'adsets:c1'])
        self.assertTrue(snapshot['account_preflight_performed'])
        self.assertEqual(snapshot['metric_risk_campaign_ids'], ['c1'])
        self.assertEqual(len(snapshot['adsets']), 1)

    def test_live_snapshot_fails_closed_when_batch_page_is_incomplete(self):
        class FakeMeta:
            @staticmethod
            def graph_batch_get(token, requests):
                responses = []
                for request in requests:
                    body: dict = {'id': 'account'} if request['name'] == 'account' else {'data': [], 'paging': {}}
                    if request['name'] == 'campaigns':
                        body['paging'] = {'next': 'redacted'}
                    responses.append({'name': request['name'], 'code': 200, 'body': body})
                return 200, responses, {}

        with self.assertRaises(guardrail.ZeroPixelGuardrailError):
            guardrail.fetch_live_snapshot(FakeMeta, 'token-not-printed', 'act_1', self.policy)


if __name__ == '__main__':
    unittest.main()
