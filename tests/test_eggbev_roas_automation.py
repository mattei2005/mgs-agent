#!/usr/bin/env python3
import datetime as dt
import importlib.util
import json
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load('eggbev_roas_common_test', BASE / 'scripts/ares-eggbev-roas-common.py')
daily = load('eggbev_daily_test', BASE / 'scripts/ares-eggbev-daily-report.py')
ET = ZoneInfo('America/New_York')


def active_ad(ad_id='a1', campaign_id='c1', effective='ACTIVE', configured='ACTIVE', adset_status='ACTIVE'):
    return {
        'id': ad_id, 'name': f'Ad {ad_id}', 'status': configured,
        'effective_status': effective, 'configured_status': configured,
        'campaign': {'id': campaign_id, 'name': f'Campaign {campaign_id}', 'status': 'ACTIVE', 'effective_status': 'ACTIVE'},
        'adset': {'id': 's1', 'name': 'AdG1', 'status': adset_status, 'effective_status': adset_status},
    }


def metric(spend=0.0, roas=None):
    return {'status': 'ok', 'spend': spend, 'purchase_roas': roas}


class PhaseTests(unittest.TestCase):
    def at(self, hour, minute=0):
        return dt.datetime(2026, 8, 29, hour, minute, tzinfo=ET)

    def test_midnight_is_reset(self):
        self.assertEqual(common.phase_for_time(self.at(0)), 'RESET')

    def test_phase_1_times(self):
        for hour in (6, 8, 10, 12):
            self.assertEqual(common.phase_for_time(self.at(hour)), 'PHASE_1')

    def test_phase_2_times(self):
        for hour in (13, 14, 16, 18, 20, 22, 23):
            self.assertEqual(common.phase_for_time(self.at(hour)), 'PHASE_2')

    def test_non_cycle_time(self):
        self.assertEqual(common.phase_for_time(self.at(7)), 'NO_CYCLE')

    def test_daily_rollover_resets_threshold_but_preserves_pause_provenance(self):
        previous = common.default_state(dt.date(2026, 8, 28), 0.55)
        previous['paused_ads']['a1'] = {'reason': 'roas_cycle', 'campaign_id': 'c1'}
        previous['paused_campaigns']['c1'] = {'reason': 'roas_zero_active_ads'}
        rolled = common.rollover_state(previous, dt.date(2026, 8, 29), 0.40)
        self.assertEqual(rolled['date_et'], '2026-08-29')
        self.assertEqual(rolled['threshold'], 0.40)
        self.assertIn('a1', rolled['paused_ads'])
        self.assertIn('c1', rolled['paused_campaigns'])
        self.assertEqual(rolled['provenance_rolled_from_date_et'], '2026-08-28')


class DecisionTests(unittest.TestCase):
    def decide(self, active=None, tracked=None, insights=None, state=None, phase='PHASE_1'):
        return common.decide_cycle(active or [], tracked or [], insights or {}, state or common.default_state(dt.date(2026, 8, 29)), phase, 0.40)

    def test_phase1_pauses_below_threshold_after_spend_gate(self):
        result = self.decide([active_ad()], insights={'a1': metric(2.01, 0.39)})
        self.assertEqual(result['decisions'][0]['action'], 'PAUSE_AD')

    def test_phase1_does_not_pause_at_two_dollars(self):
        result = self.decide([active_ad()], insights={'a1': metric(2.00, 0.10)})
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_phase1_null_roas_is_cut_eligible_after_spend_gate(self):
        result = self.decide([active_ad()], insights={'a1': metric(2.50, None)})
        self.assertEqual(result['decisions'][0]['action'], 'PAUSE_AD')

    def test_phase1_null_roas_with_low_spend_is_not_cut(self):
        result = self.decide([active_ad()], insights={'a1': metric(1.99, None)})
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_phase2_null_roas_is_cut_without_spend_gate(self):
        result = self.decide([active_ad()], insights={'a1': metric(0.0, None)}, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'PAUSE_AD')

    def test_phase2_missing_insight_row_is_cut_as_approved_nd(self):
        result = common.decide_cycle([active_ad()], [], {}, common.default_state(dt.date(2026, 8, 29)), 'PHASE_2', 0.40)
        self.assertEqual(result['decisions'][0]['action'], 'PAUSE_AD')
        self.assertEqual(result['decisions'][0]['reason'], 'roas_below_or_nd')

    def test_exact_threshold_never_changes_state(self):
        result = self.decide([active_ad()], insights={'a1': metric(10.0, 0.40)}, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_above_threshold_active_ad_is_kept(self):
        result = self.decide([active_ad()], insights={'a1': metric(10.0, 0.41)}, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_ares_paused_ad_reactivates_above_threshold(self):
        state = common.default_state(dt.date(2026, 8, 29))
        state['paused_ads']['a1'] = {'reason': 'roas_cycle', 'campaign_id': 'c1'}
        state['paused_campaigns']['c1'] = {'reason': 'roas_zero_active_ads'}
        tracked = [active_ad(effective='PAUSED', configured='PAUSED')]
        result = self.decide(tracked=tracked, insights={'a1': metric(5.0, 0.41)}, state=state, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'REACTIVATE_AD')
        self.assertEqual(result['campaign_actions'][0]['action'], 'REACTIVATE_CAMPAIGN')

    def test_paused_ad_equal_threshold_does_not_reactivate(self):
        state = common.default_state(dt.date(2026, 8, 29))
        state['paused_ads']['a1'] = {'reason': 'roas_cycle'}
        result = self.decide(tracked=[active_ad(effective='PAUSED', configured='PAUSED')], insights={'a1': metric(5.0, 0.40)}, state=state, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_manual_paused_ad_is_not_reactivated(self):
        result = self.decide(tracked=[active_ad(effective='PAUSED', configured='PAUSED')], insights={'a1': metric(5.0, 9.0)}, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_inactive_adset_blocks_reactivation(self):
        state = common.default_state(dt.date(2026, 8, 29))
        state['paused_ads']['a1'] = {'reason': 'roas_cycle'}
        tracked = [active_ad(effective='ADSET_PAUSED', configured='PAUSED', adset_status='PAUSED')]
        result = self.decide(tracked=tracked, insights={'a1': metric(5.0, 9.0)}, state=state, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['reason'], 'tracked_adset_not_configured_active')

    def test_last_active_ad_cut_pauses_campaign(self):
        result = self.decide([active_ad()], insights={'a1': metric(3.0, 0.10)}, phase='PHASE_2')
        self.assertEqual(result['campaign_actions'][0]['action'], 'PAUSE_CAMPAIGN')

    def test_campaign_stays_active_when_another_ad_survives(self):
        ads = [active_ad('a1'), active_ad('a2')]
        result = self.decide(ads, insights={'a1': metric(3.0, 0.10), 'a2': metric(3.0, 0.80)}, phase='PHASE_2')
        self.assertFalse(result['campaign_actions'])

    def test_no_cycle_never_plans_actions(self):
        result = self.decide([active_ad()], insights={'a1': metric(100.0, None)}, phase='NO_CYCLE')
        self.assertEqual(result['counts']['pause_ads'], 0)


class SourceGateTests(unittest.TestCase):
    def meta(self, conflict=False):
        return {'native_rules': {'conflict': {'enabled': conflict}}}

    def test_ready_requires_both_sources_and_no_rule_conflict(self):
        gate = common.source_gate(self.meta(False), {'ready': True}, 'PHASE_1')
        self.assertTrue(gate['write_ready'])

    def test_native_rule_blocks_write(self):
        gate = common.source_gate(self.meta(True), {'ready': True}, 'PHASE_1')
        self.assertIn('native_rule_ADS_ZERO_RESULTS_enabled', gate['reasons'])

    def test_missing_smart_bidding_blocks_write(self):
        gate = common.source_gate(self.meta(False), {'ready': False, 'reason': 'target_missing'}, 'PHASE_1')
        self.assertIn('target_missing', gate['reasons'])

    def test_reset_is_not_action_cycle(self):
        gate = common.source_gate(self.meta(False), {'ready': True}, 'RESET')
        self.assertIn('not_an_action_cycle', gate['reasons'])

    def test_manual_intervention_requires_review_instead_of_discarding_provenance(self):
        state = common.default_state(dt.date(2026, 8, 29))
        state['paused_ads']['a1'] = {'reason': 'roas_cycle', 'meta_updated_time': '2026-08-29T10:00:00+0000'}
        review = common.detect_manual_interventions(
            state,
            [{'id': 'a1', 'updated_time': '2026-08-29T11:00:00+0000'}],
            [],
        )
        self.assertEqual(review[0]['action'], 'ASK_NICOLAS_FOR_ORIENTATION')
        gate = common.source_gate({'native_rules': {'conflict': {'enabled': False}}, 'manual_review': review}, {'ready': True}, 'PHASE_2')
        self.assertIn('manual_intervention_review_required', gate['reasons'])
        self.assertIn('a1', state['paused_ads'])

    def test_freshness_accepts_source_timestamp_within_two_hours(self):
        observed = dt.datetime(2026, 8, 29, 14, 0, tzinfo=ET)
        result = common.evaluate_sb_freshness([{'UPDATED_AT': '2026-08-29T13:00:00-04:00'}], observed, 2.0)
        self.assertTrue(result['ready'])

    def test_freshness_rejects_source_timestamp_older_than_two_hours(self):
        observed = dt.datetime(2026, 8, 29, 14, 0, tzinfo=ET)
        result = common.evaluate_sb_freshness([{'UPDATED_AT': '2026-08-29T11:59:00-04:00'}], observed, 2.0)
        self.assertFalse(result['ready'])
        self.assertEqual(result['reason'], 'smart_bidding_data_stale_over_2h')

    def test_freshness_without_timestamp_is_fail_closed(self):
        result = common.evaluate_sb_freshness([{'DATE': '2026-08-29'}], dt.datetime(2026, 8, 29, 14, 0, tzinfo=ET), 2.0)
        self.assertFalse(result['ready'])
        self.assertEqual(result['reason'], 'smart_bidding_freshness_unverifiable')


class ScalingTests(unittest.TestCase):
    def campaign(self, cid='c1', budget='1000', status='ACTIVE'):
        return {'id': cid, 'name': cid, 'daily_budget': budget, 'status': status, 'configured_status': status, 'effective_status': status}

    def decision(self, cid='c1', spend=10.0, roas=0.41):
        return {**common.normalize_ad(active_ad(campaign_id=cid)), 'spend': spend, 'purchase_roas': roas, 'purchase_value': spend * roas}

    def test_all_active_campaigns_above_threshold_receive_30_percent_recommendation(self):
        result = common.plan_campaign_budget_scales(
            [self.campaign('c1', '1000'), self.campaign('c2', '2000')],
            [self.decision('c1', 10, .41), self.decision('c2', 10, .80)], .40, 30,
        )
        self.assertEqual([row['target_daily_budget_minor'] for row in result], [1300, 2600])
        self.assertTrue(all(row['write_enabled'] is False for row in result))

    def test_equal_or_below_threshold_does_not_scale(self):
        result = common.plan_campaign_budget_scales(
            [self.campaign('c1'), self.campaign('c2')],
            [self.decision('c1', 10, .40), self.decision('c2', 10, .39)], .40, 30,
        )
        self.assertEqual(result, [])

    def test_zero_spend_does_not_scale(self):
        self.assertEqual(common.plan_campaign_budget_scales([self.campaign()], [self.decision(spend=0, roas=9)], .40, 30), [])


class ReportingTests(unittest.TestCase):
    def test_auto_0600_returns_previous_and_current(self):
        at = dt.datetime(2026, 8, 29, 6, 0, tzinfo=ET)
        dates = daily.report_dates('auto', at)
        self.assertEqual([row[0] for row in dates], ['2026-08-28', '2026-08-29'])

    def test_auto_other_time_returns_current_only(self):
        at = dt.datetime(2026, 8, 29, 8, 0, tzinfo=ET)
        self.assertEqual(daily.report_dates('auto', at), [('2026-08-29', 'Parcial atual')])

    def test_smart_bidding_aggregation_does_not_invent_roi(self):
        bundle = {'ready': True, 'target_report_rows': [{'INVESTIMENT': 10, 'REVENUE': 20, 'LEADS': 5}], 'available_account_names': ['Eggbev-US-CC-EN-01']}
        result = daily.aggregate_sb(bundle)
        self.assertEqual(result['investment'], 10)
        self.assertEqual(result['revenue'], 20)
        self.assertIsNone(result['roi_real'])
        self.assertIsNone(result['rps'])

    def test_unreconciled_smart_bidding_metrics_are_nd_not_zero(self):
        result = daily.aggregate_sb({'ready': False, 'reason': 'target_missing', 'target_report_rows': []})
        self.assertIsNone(result['investment'])
        self.assertIsNone(result['revenue'])
        self.assertIsNone(result['leads'])

    def test_meta_aggregation_uses_purchase_value_over_spend(self):
        bundle = {'insights': [{'campaign_id': 'c1', 'campaign_name': 'C', 'spend': '10', 'impressions': '1000', 'ctr': '2', 'actions': [{'action_type': 'onsite_conversion.messaging_first_reply', 'value': '5'}], 'action_values': [{'action_type': 'purchase', 'value': '4'}]}]}
        result = daily.aggregate_meta(bundle)
        self.assertAlmostEqual(result['purchase_roas'], 0.4)
        self.assertAlmostEqual(result['cost_per_message'], 2.0)


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operation = json.loads((BASE / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json').read_text())

    def test_meta_account_is_exact(self):
        self.assertEqual(self.operation['smart_bidding_reconciliation']['target_meta_account_id'], 'act_1034081997659047')

    def test_runner_build_does_not_enable_writes_or_crons(self):
        runtime = self.operation['roas_cycle_policy']['runtime']
        self.assertFalse(runtime['write_enabled'])
        self.assertFalse(runtime['cron_enabled'])

    def test_daily_build_does_not_enable_post_or_cron(self):
        runtime = self.operation['daily_reporting_policy']['runtime']
        self.assertFalse(runtime['post_enabled'])
        self.assertFalse(runtime['cron_enabled'])

    def test_native_rule_disable_is_future_only(self):
        transition = self.operation['roas_cycle_policy']['native_rule_transition']
        self.assertTrue(transition['disable_authorized_at_future_activation'])
        self.assertFalse(transition['execute_now'])

    def test_clone_page_switch_contract_is_scoped_and_not_engine_ready(self):
        cloning = self.operation['campaign_cloning_policy']
        mode = cloning['allowed_modes']['clone_page_switch']
        self.assertEqual(mode['daily_budget_usd'], 45)
        self.assertEqual(mode['start_time'], 'next_day_00:00_America/New_York')
        self.assertIn('ACTIVE', mode['delivery_state'])
        self.assertEqual(mode['media_and_copy'], 'preserve source media and copy')
        self.assertEqual(mode['engine_support'], 'contract_approved_pending_v3_manifest_and_executor_extension')
        self.assertFalse(cloning['engine_readback']['eggbev_account_registered'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
