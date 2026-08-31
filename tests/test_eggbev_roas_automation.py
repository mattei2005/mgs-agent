#!/usr/bin/env python3
import datetime as dt
import importlib.util
import json
import unittest
from unittest import mock
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
cycle = load('eggbev_cycle_test', BASE / 'scripts/ares-eggbev-roas-cycle.py')
ET = ZoneInfo('America/New_York')


def active_ad(ad_id='a1', campaign_id='c1', effective='ACTIVE', configured='ACTIVE', adset_status='ACTIVE', campaign_start=None):
    return {
        'id': ad_id, 'name': f'Ad {ad_id}', 'status': configured,
        'effective_status': effective, 'configured_status': configured,
        'campaign': {'id': campaign_id, 'name': f'Campaign {campaign_id}', 'status': 'ACTIVE', 'configured_status': 'ACTIVE', 'effective_status': 'ACTIVE', 'start_time': campaign_start},
        'adset': {'id': 's1', 'name': 'AdG1', 'status': adset_status, 'configured_status': adset_status, 'effective_status': adset_status},
    }


def metric(spend=0.0, roas=None):
    return {'status': 'ok', 'spend': spend, 'purchase_roas': roas}


class PhaseTests(unittest.TestCase):
    def at(self, hour, minute=0):
        return dt.datetime(2026, 8, 29, hour, minute, tzinfo=ET)

    def test_midnight_is_phase3_recycling(self):
        self.assertEqual(common.phase_for_time(self.at(0)), 'PHASE_3')

    def test_phase_1_times(self):
        for hour in (5, 6, 8, 10, 12):
            self.assertEqual(common.phase_for_time(self.at(hour)), 'PHASE_1')

    def test_phase_2_times(self):
        for hour in (13, 14, 16, 18, 20, 22, 23):
            self.assertEqual(common.phase_for_time(self.at(hour)), 'PHASE_2')

    def test_non_cycle_time(self):
        self.assertEqual(common.phase_for_time(self.at(7)), 'NO_CYCLE')

    def test_scheduled_tick_maps_bounded_delay_to_logical_hour(self):
        actual = self.at(5, 11)
        self.assertEqual(cycle.scheduled_cycle_at(actual), self.at(5, 0))

    def test_scheduled_tick_rejects_excessive_delay(self):
        with self.assertRaises(RuntimeError):
            cycle.scheduled_cycle_at(self.at(5, 16))

    def test_daily_rollover_preserves_only_ad_pause_provenance(self):
        previous = common.default_state(dt.date(2026, 8, 28), 0.55)
        previous['paused_ads']['a1'] = {'reason': 'roas_cycle', 'campaign_id': 'c1'}
        previous['paused_campaigns'] = {'c1': {'reason': 'legacy_roas_zero_active_ads'}}
        rolled = common.rollover_state(previous, dt.date(2026, 8, 29), 0.40)
        self.assertEqual(rolled['date_et'], '2026-08-29')
        self.assertEqual(rolled['threshold'], 0.40)
        self.assertIn('a1', rolled['paused_ads'])
        self.assertNotIn('paused_campaigns', rolled)
        self.assertEqual(rolled['provenance_rolled_from_date_et'], '2026-08-28')


class DecisionTests(unittest.TestCase):
    def decide(self, active=None, tracked=None, insights=None, state=None, phase='PHASE_1', cycle_at=None):
        return common.decide_cycle(active or [], tracked or [], insights or {}, state or common.default_state(dt.date(2026, 8, 29)), phase, 0.40, cycle_at)

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

    def test_night_cycle_excludes_campaign_scheduled_for_next_midnight(self):
        result = self.decide(
            [active_ad(campaign_start='2026-08-30T00:00:00-04:00')],
            insights={}, phase='PHASE_2', cycle_at=dt.datetime(2026, 8, 29, 20, 0, tzinfo=ET),
        )
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')
        self.assertEqual(result['decisions'][0]['reason'], 'night_excluded_campaign_scheduled_for_next_day')

    def test_night_cycle_still_cuts_nd_from_campaign_that_ran_that_day(self):
        result = self.decide(
            [active_ad(campaign_start='2026-08-29T00:00:00-04:00')],
            insights={}, phase='PHASE_2', cycle_at=dt.datetime(2026, 8, 29, 22, 0, tzinfo=ET),
        )
        self.assertEqual(result['decisions'][0]['action'], 'PAUSE_AD')

    def test_phase1_at_05_and_06_cuts_when_spend_gate_and_roas_fail(self):
        for hour in (5, 6):
            self.assertEqual(common.phase_for_time(dt.datetime(2026, 8, 29, hour, 0, tzinfo=ET)), 'PHASE_1')
            result = self.decide([active_ad()], insights={'a1': metric(2.01, .39)}, phase='PHASE_1')
            self.assertEqual(result['decisions'][0]['action'], 'PAUSE_AD')

    def test_exact_threshold_never_changes_state(self):
        result = self.decide([active_ad()], insights={'a1': metric(10.0, 0.40)}, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_above_threshold_active_ad_is_kept(self):
        result = self.decide([active_ad()], insights={'a1': metric(10.0, 0.41)}, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'KEEP')

    def test_ares_paused_ad_reactivates_above_threshold(self):
        state = common.default_state(dt.date(2026, 8, 29))
        state['paused_ads']['a1'] = {'reason': 'roas_cycle', 'campaign_id': 'c1'}
        tracked = [active_ad(effective='PAUSED', configured='PAUSED')]
        result = self.decide(tracked=tracked, insights={'a1': metric(5.0, 0.41)}, state=state, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'REACTIVATE_AD')
        self.assertFalse(result['campaign_actions'])
        self.assertEqual(result['counts']['reactivate_campaigns'], 0)

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

    def test_last_active_ad_cut_never_pauses_campaign_or_adset(self):
        result = self.decide([active_ad()], insights={'a1': metric(3.0, 0.10)}, phase='PHASE_2')
        self.assertEqual(result['decisions'][0]['action'], 'PAUSE_AD')
        self.assertFalse(result['campaign_actions'])
        self.assertEqual(result['counts']['pause_campaigns'], 0)

    def test_campaign_stays_active_when_another_ad_survives(self):
        ads = [active_ad('a1'), active_ad('a2')]
        result = self.decide(ads, insights={'a1': metric(3.0, 0.10), 'a2': metric(3.0, 0.80)}, phase='PHASE_2')
        self.assertFalse(result['campaign_actions'])

    def test_no_cycle_never_plans_actions(self):
        result = self.decide([active_ad()], insights={'a1': metric(100.0, None)}, phase='NO_CYCLE')
        self.assertEqual(result['counts']['pause_ads'], 0)


class ExecutePlanTests(unittest.TestCase):
    def test_execute_plan_ignores_campaign_actions_and_writes_only_ads(self):
        plan = {
            'decisions': [
                {'ad_id': 'a1', 'ad_name': 'AD 01', 'campaign_id': 'c1', 'adset_status': 'ACTIVE', 'action': 'REACTIVATE_AD'},
                {'ad_id': 'a2', 'ad_name': 'AD 02', 'campaign_id': 'c1', 'adset_status': 'ACTIVE', 'action': 'PAUSE_AD'},
            ],
            'campaign_actions': [
                {'campaign_id': 'c1', 'action': 'REACTIVATE_CAMPAIGN'},
                {'campaign_id': 'c1', 'action': 'PAUSE_CAMPAIGN'},
            ],
        }
        state = {'paused_ads': {'a1': {'reason': 'roas_cycle'}}}
        run = {'writes': [], 'audit_path': '/tmp/ignored.json', 'started_at_et': '2026-08-30T20:00:00-04:00', 'phase': 'PHASE_2', 'threshold': .4}

        def write_result(_meta, _token, object_id, status):
            return {'object_id': object_id, 'ok': True, 'stage': 'confirmed', 'after': {'status': status}}

        with mock.patch.object(cycle.common, 'reconcile_status_write', side_effect=write_result) as write, mock.patch.object(cycle.common, 'atomic_json'):
            cycle.execute_plan(object(), 'token', plan, state, run)
        self.assertEqual([(call.args[2], call.args[3]) for call in write.call_args_list], [('a1', 'ACTIVE'), ('a2', 'PAUSED')])
        self.assertTrue(all(item['kind'] == 'ad' for item in run['writes']))
        self.assertNotIn('a1', state['paused_ads'])
        self.assertIn('a2', state['paused_ads'])


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

    def test_manual_adset_intervention_requires_full_set_review(self):
        state = common.default_state(dt.date(2026, 8, 29))
        state['paused_ads']['a1'] = {
            'reason': 'roas_cycle',
            'adset_id': 's1',
            'adset_updated_time': '2026-08-29T10:00:00+0000',
        }
        review = common.detect_manual_interventions(
            state,
            [{'id': 'a1', 'adset': {'id': 's1', 'updated_time': '2026-08-29T11:00:00+0000'}}],
            [],
        )
        self.assertEqual(review[0]['kind'], 'adset')
        self.assertEqual(review[0]['action'], 'ASK_NICOLAS_FOR_ORIENTATION')

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

    def test_estimated_delay_total_minutes_is_valid_without_fill_timestamp(self):
        result = common.evaluate_economic_freshness({'totalMinutes': 0, 'currentFillTime': None})
        self.assertTrue(result['ready'])
        self.assertEqual(result['evidence_mode'], 'totalMinutes')

    def test_estimated_delay_over_two_hours_still_blocks(self):
        result = common.evaluate_economic_freshness({'totalMinutes': 121, 'currentFillTime': None})
        self.assertFalse(result['ready'])
        self.assertEqual(result['reason'], 'delay_minutes_out_of_range')


class Phase3RecyclingTests(unittest.TestCase):
    def fixture(self, roas=.38, spend=10, leads=5000, campaign_status='PAUSED', adset_status='PAUSED', ad_status='PAUSED', campaign_id='c1', ad_id='a1', adset_id='s1'):
        ad = {
            'id': ad_id, 'name': 'AD 01 - Winner', 'status': ad_status,
            'configured_status': ad_status, 'effective_status': ad_status,
            'campaign': {
                'id': campaign_id, 'name': '162 - Page One - ENG - US - (pg_12345) C001',
                'status': campaign_status, 'configured_status': campaign_status,
                'effective_status': campaign_status, 'start_time': '2026-08-29T00:00:00-04:00',
            },
            'adset': {'id': adset_id, 'name': 'AdG1', 'status': adset_status, 'configured_status': adset_status, 'effective_status': adset_status},
            'creative': {'url_tags': 'utm_campaign=pg_12345', 'object_story_spec': {'page_id': 'page1'}},
        }
        meta = {
            'phase3_ads': [ad],
            'phase3_adsets': [ad['adset']],
            'phase3_campaigns': [{
                'id': campaign_id, 'name': ad['campaign']['name'], 'status': campaign_status,
                'configured_status': campaign_status, 'effective_status': campaign_status,
                'daily_budget': '5000', 'start_time': '2026-08-29T00:00:00-04:00',
            }],
            'insights_by_ad': {ad_id: metric(spend, roas)},
            'insights': [{'ad_id': ad_id, 'campaign_id': campaign_id, 'spend': str(spend)}],
            'native_rules': {'conflict': {'enabled': False}},
            'phase3_object_errors': [],
        }
        sb = {
            'page_rows': [{'UTM_CAMPAIGN': 'pg_12345'}],
            'page_index': {'pg_12345': [{'UTM_CAMPAIGN': 'pg_12345', 'FB_PAGE_ID': 'page1', 'PAGE_NAME': 'Page One', 'LEADS': leads}]},
            'economic_ready': True,
            'economic_freshness': {'ready': True, 'age_minutes': 30, 'current_fill_time': '2026-08-30T23:30:00-04:00'},
        }
        return meta, sb

    def plan(self, **kwargs):
        meta, sb = self.fixture(**kwargs)
        state = common.default_state(dt.date(2026, 8, 30))
        return common.plan_phase3_recycling(meta, sb, state, '2026-08-29', .38, chooser=lambda values: 4500)

    def test_roas_0_38_is_inclusive_and_reactivates_manual_pauses(self):
        plan = self.plan(roas=.38)
        self.assertEqual(plan['decisions'][0]['action'], 'REACTIVATE_AD')
        self.assertEqual(plan['campaign_actions'][0]['action'], 'ACTIVATE_CAMPAIGN')
        self.assertEqual(plan['adset_actions'][0]['action'], 'ACTIVATE_ADSET')
        self.assertEqual(plan['budget_assignments_minor'], {'c1': 4500})

    def test_roas_below_0_38_is_not_recycled(self):
        plan = self.plan(roas=.3799)
        self.assertEqual(plan['decisions'], [])
        self.assertEqual(plan['campaign_actions'], [])

    def test_exactly_5000_leads_is_allowed_but_over_5000_is_excluded(self):
        allowed = self.plan(leads=5000)
        blocked = self.plan(leads=5000.01)
        self.assertEqual(len(allowed['campaign_actions']), 1)
        self.assertEqual(blocked['campaign_actions'], [])
        self.assertEqual(blocked['excluded_campaigns'][0]['reason'], 'page_leads_strictly_over_5000')

    def test_zero_spend_never_enters_previous_day_recycling(self):
        plan = self.plan(spend=0, roas=9)
        self.assertEqual(plan['decisions'], [])

    def test_random_budget_assignment_is_only_45_or_65_and_reused_on_retry(self):
        state = common.default_state(dt.date(2026, 8, 30))
        choices = iter((4500, 6500))
        first = common.materialize_phase3_budget_assignment(state, '2026-08-29', ['c1', 'c2'], chooser=lambda values: next(choices))
        second = common.materialize_phase3_budget_assignment(state, '2026-08-29', ['c1', 'c2'], chooser=lambda values: self.fail('retry must reuse persisted choice'))
        self.assertEqual(first, {'c1': 4500, 'c2': 6500})
        self.assertEqual(second, first)
        self.assertTrue(set(first.values()) <= {4500, 6500})

    def test_phase3_source_gate_uses_estimated_delay_and_allows_manual_pause_override(self):
        meta, sb = self.fixture()
        meta['manual_review'] = [{'kind': 'ad', 'object_id': 'a1'}]
        gate = common.source_gate(meta, sb, 'PHASE_3')
        self.assertTrue(gate['write_ready'])
        self.assertEqual(gate['freshness_evidence'], 'Smart Bidding /estimated/delay')

    def test_execute_phase3_orders_budget_campaign_adset_then_ad(self):
        plan = self.plan()
        state = common.default_state(dt.date(2026, 8, 30))
        state['paused_ads']['a1'] = {'reason': 'roas_cycle'}
        run = {'writes': [], 'audit_path': '/tmp/phase3-test.json'}
        order = []

        def budget(*args):
            order.append(('budget', args[2]))
            return {'object_id': args[2], 'ok': True, 'stage': 'confirmed', 'after': {'daily_budget': args[3]}}

        def status(*args):
            order.append(('status', args[2]))
            return {'object_id': args[2], 'ok': True, 'stage': 'confirmed', 'after': {'status': args[3]}}

        with mock.patch.object(cycle.common, 'reconcile_campaign_budget_write', side_effect=budget), mock.patch.object(cycle.common, 'reconcile_status_write', side_effect=status), mock.patch.object(cycle.common, 'atomic_json'):
            ok = cycle.execute_phase3_plan(object(), 'token', plan, state, run)
        self.assertTrue(ok)
        self.assertEqual(order, [('budget', 'c1'), ('status', 'c1'), ('status', 's1'), ('status', 'a1')])
        self.assertNotIn('a1', state['paused_ads'])

    def test_phase3_report_is_explicit_and_keeps_frozen_quality_table(self):
        campaign = {
            'campaign_id': 'c1', 'name': '162 - Page One - ENG - US - (pg_12345) C001',
            'utm_campaign': 'pg_12345', 'status': 'ACTIVE', 'budget_usd': 45,
            'spend': 10, 'cost_per_messaging_started': 2, 'purchase_roas': .38,
            'ads_roas': '01·0,38♻️', 'roi_real': 1, 'roi_estimated': 2,
            'sb_page_name': 'Page One', 'sb_leads': 5000, 'rps': 5, 'cpm': 20, 'ctr': 2,
            'pause_ads': 0, 'reactivate_ads': 1, 'action_label': 'REATIVAR',
        }
        run = {
            'started_at_et': '2026-08-30T00:00:00-04:00', 'phase': 'PHASE_3', 'threshold': .38,
            'mode': 'controlled_write', 'meta_status': 'ok', 'smart_bidding_status': 'ok',
            'source_gate': {'write_ready': True, 'reasons': []},
            'plan': {'source_date': '2026-08-29', 'counts': {'ads_considered': 1, 'reactivate_ads': 1, 'reactivate_adsets': 1, 'reactivate_campaigns': 1, 'budget_updates': 1, 'excluded_campaigns': 0}, 'decisions': [{'action': 'REACTIVATE_AD'}], 'budget_scale_candidates': []},
            'reporting': {'campaigns': [campaign], 'campaign_count': 1}, 'writes': [],
        }
        rendered = cycle.render_report(run)
        self.assertIn('Fase 3 — Reativação/Reciclagem', rendered)
        self.assertIn('Purchase ROAS ≥ 0,38', rendered)
        self.assertIn('budget aleatório US$45/US$65', rendered)
        self.assertIn('Ação da Fase 3', rendered)
        for label in cycle.CANONICAL_DESKTOP_HEADERS:
            self.assertIn(label, rendered)
        self.assertIn('01·0,38♻️', rendered)


class ScalingTests(unittest.TestCase):
    def campaign(self, cid='c1', budget='1000', status='ACTIVE'):
        return {'id': cid, 'name': cid, 'daily_budget': budget, 'status': status, 'configured_status': status, 'effective_status': status}

    def decision(self, cid='c1', spend=10.0, roas=0.41):
        return {**common.normalize_ad(active_ad(campaign_id=cid)), 'spend': spend, 'purchase_roas': roas, 'purchase_value': spend * roas}

    def test_all_active_campaigns_above_0_50_receive_10_percent_recommendation(self):
        result = common.plan_campaign_budget_scales(
            [self.campaign('c1', '1000'), self.campaign('c2', '2000')],
            [self.decision('c1', 10, .51), self.decision('c2', 10, .80)], .50, 10,
        )
        self.assertEqual([row['target_daily_budget_minor'] for row in result], [1100, 2200])
        self.assertTrue(all(row['write_enabled'] is False for row in result))

    def test_0_40_through_0_50_keeps_current_budget(self):
        result = common.plan_campaign_budget_scales(
            [self.campaign('c1'), self.campaign('c2')],
            [self.decision('c1', 10, .50), self.decision('c2', 10, .41)], .50, 10,
        )
        self.assertEqual(result, [])

    def test_zero_spend_does_not_scale(self):
        self.assertEqual(common.plan_campaign_budget_scales([self.campaign()], [self.decision(spend=0, roas=9)], .50, 10), [])


class ReportingTests(unittest.TestCase):
    def test_roas_cycle_reporting_has_requested_metrics_and_cut_emoji(self):
        meta_bundle = {
            'campaigns': [{
                'id': 'c1', 'name': '123 - Full Campaign - ENG - US - (pg_12345)',
                'status': 'ACTIVE', 'effective_status': 'ACTIVE', 'configured_status': 'ACTIVE',
                'daily_budget': '4500',
            }],
            'ads': [{
                'id': 'a1', 'campaign': {'id': 'c1', 'name': '123 - Full Campaign - ENG - US - (pg_12345)'},
                'creative': {'url_tags': 'utm_campaign=pg_12345', 'object_story_spec': {'page_id': 'page1'}},
            }],
            'insights': [{
                'ad_id': 'a1', 'campaign_id': 'c1', 'campaign_name': '123 - Full Campaign - ENG - US - (pg_12345)',
                'spend': '12', 'impressions': '1000', 'inline_link_clicks': '3', 'ctr': '2',
                'actions': [{'action_type': 'onsite_conversion.messaging_conversation_started_7d', 'value': '4'}],
                'action_values': [{'action_type': 'purchase', 'value': '6'}],
            }],
        }
        sb_bundle = {
            'ready': True,
            'target_report_rows': [{
                'UTM_CAMPAIGN': 'pg_12345', 'INVESTIMENT': 11, 'REVENUE': 10,
                'LEADS': 20, 'SUBSCRIBED': 5, 'DRIP_REVENUE': 6, 'BD_REVENUE': 4,
                'SESSIONS': 20, 'ACQUISITION_CLICKS': 5, 'AVG_PRICE': 6.2,
            }],
            'page_index': {'pg_12345': [{'UTM_CAMPAIGN': 'pg_12345', 'FB_PAGE_ID': 'page1', 'PAGE_NAME': 'Page One'}]},
            'freshness': {'ready': True, 'latest_at_et': '2026-08-29T20:00:00-04:00'},
            'economic_ready': True,
            'economic_performance_rows': [{
                'CAMPAIGN_ID': 'c1', 'UTM_ADGROUP': 'pg_12345', 'INVESTIMENT': 10,
                'NET_REVENUE': 15, 'REVENUE_ESTIMATED': 0, 'SESSIONS': 30,
                'GAM_IMPRESSIONS': 50,
            }],
            'economic_estimated': {'grouped': [{
                'utm_adgroup': 'pg_12345', 'estimatedRevenue': 20, 'confidence': .95,
            }]},
            'economic_freshness': {'ready': True, 'age_minutes': 45},
        }
        plan = {
            'decisions': [{
                'campaign_id': 'c1', 'campaign_name': '123 - Full Campaign - ENG - US - (pg_12345)',
                'ad_id': 'a1', 'ad_name': 'Ad a1', 'action': 'PAUSE_AD', 'reason': 'roas_below_or_nd',
            }],
            'budget_scale_candidates': [],
        }
        report = cycle.build_campaign_reporting(meta_bundle, sb_bundle, plan)
        row = report['campaigns'][0]
        self.assertEqual(row['action_emoji'], '🛑')
        self.assertEqual(row['action_label'], 'CORTAR')
        self.assertEqual(row['sb_leads'], 20)
        self.assertEqual(row['cost_per_messaging_started'], 3)
        self.assertEqual(row['purchase_roas'], 0.5)
        self.assertEqual(row['cpm'], 12)
        self.assertEqual(row['ctr'], 2)
        self.assertEqual(row['cpc_link'], 4)
        self.assertEqual(row['messaging_results'], 4)
        self.assertEqual(row['cost_per_message'], 3)
        self.assertEqual(row['sb_page_id'], 'page1')
        self.assertEqual(row['sb_page_name'], 'Page One')
        self.assertEqual(row['sb_cost_subscriber'], 2.2)
        self.assertEqual(row['sb_profit'], -1)
        self.assertAlmostEqual(row['sb_roi_percent'], -100 / 11)
        self.assertAlmostEqual(row['sb_drip_roi_percent'], -500 / 11)
        self.assertEqual(row['sb_broadcast_revenue'], 4)
        self.assertEqual(row['rps'], 500)
        self.assertEqual(row['roi_real'], 50)
        self.assertEqual(row['roi_estimated'], 100)
        self.assertEqual(row['block_cpm'], 300)
        self.assertEqual(row['economic_join_status'], 'matched')

    def test_economic_estimate_fails_closed_when_utm_maps_to_multiple_campaigns(self):
        bundle = {
            'economic_ready': True,
            'economic_performance_rows': [
                {'CAMPAIGN_ID': 'c1', 'UTM_ADGROUP': 'pg_1', 'INVESTIMENT': 10, 'NET_REVENUE': 15, 'SESSIONS': 30, 'GAM_IMPRESSIONS': 50},
                {'CAMPAIGN_ID': 'c2', 'UTM_ADGROUP': 'pg_1', 'INVESTIMENT': 20, 'NET_REVENUE': 15, 'SESSIONS': 30, 'GAM_IMPRESSIONS': 50},
            ],
            'economic_estimated': {'grouped': [{'utm_adgroup': 'pg_1', 'estimatedRevenue': 99}]},
            'economic_freshness': {'ready': True, 'age_minutes': 20},
        }
        result = cycle.aggregate_economic_reporting(bundle)
        first = result['by_campaign_utm'][('c1', 'pg_1')]
        self.assertEqual(first['roi_real'], 50)
        self.assertIsNone(first['roi_estimated'])
        self.assertEqual(first['estimated_join_status'], 'ambiguous_utm')

    def test_economic_reporting_stays_unavailable_when_freshness_gate_is_closed(self):
        result = cycle.aggregate_economic_reporting({
            'economic_ready': False,
            'economic_reason': 'economic_freshness_unverifiable_or_stale',
            'economic_performance_rows': [{'CAMPAIGN_ID': 'c1', 'UTM_ADGROUP': 'pg_1'}],
        })
        self.assertFalse(result['ready'])
        self.assertEqual(result['by_campaign_utm'], {})

    def test_reporting_keeps_insight_only_paused_campaign_visible_without_write_decision(self):
        meta_bundle = {
            'campaign_readbacks': [{
                'id': 'c1', 'name': '123 - Page - ENG - US - (pg_12345)',
                'status': 'PAUSED', 'effective_status': 'PAUSED', 'daily_budget': '4500',
            }],
            'ad_readbacks': [{
                'id': 'a1', 'campaign': {'id': 'c1'},
                'creative': {'url_tags': 'utm_campaign=pg_12345', 'object_story_spec': {'page_id': 'page1'}},
            }],
            'insights': [{
                'ad_id': 'a1', 'campaign_id': 'c1', 'campaign_name': '123 - Page - ENG - US - (pg_12345)',
                'spend': '5', 'impressions': '500', 'inline_link_clicks': '10', 'ctr': '2',
            }],
        }
        report = cycle.build_campaign_reporting(
            meta_bundle,
            {'ready': False, 'reason': 'smart_bidding_freshness_unverifiable', 'target_report_rows': []},
            {'decisions': [], 'budget_scale_candidates': []},
        )
        self.assertEqual(report['campaign_count'], 1)
        row = report['campaigns'][0]
        self.assertEqual(row['status'], 'PAUSED')
        self.assertEqual(row['action_label'], 'OBSERVAR')
        self.assertEqual(row['cpc_link'], .5)

    def test_roas_cycle_renderer_matches_cpv13_intraday_desktop_table(self):
        campaign = {
            'campaign_id': 'c1', 'name': '123 - Full Campaign - ENG - US - (pg_12345)',
            'action_emoji': '🛑', 'action_label': 'CORTAR', 'action_detail': '1 anúncio(s)',
            'pause_ads': 1, 'reactivate_ads': 0,
            'ads_roas': '03·0,92✅ 02·0,76✅ 01·0,30🛑',
            'utm_campaign': 'pg_12345', 'status': 'ACTIVE', 'budget_usd': 45,
            'spend': 12, 'messaging_started': 4, 'cost_per_messaging_started': 3,
            'messaging_results': 6, 'cost_per_message': 2, 'cpc_link': .4,
            'ctr': 2, 'purchase_roas': .3, 'cpm': 12, 'sb_leads': 20,
            'sb_page_id': '123456789012345', 'sb_page_name': 'Page One',
            'sb_cost_subscriber': 1.5, 'sb_revenue': 40, 'sb_profit': 28,
            'sb_roi_percent': 233.3, 'sb_drip_roi_percent': 50,
            'sb_broadcast_revenue': 18,
            'roi_real': 12.3, 'roi_estimated': -5.5, 'block_cpm': None, 'rps': 500,
            'join_status': 'matched',
        }
        run = {
            'started_at_et': '2026-08-29T20:00:00-04:00', 'phase': 'PHASE_2',
            'threshold': .4, 'mode': 'controlled_write', 'meta_status': 'ok', 'smart_bidding_status': 'ok',
            'source_gate': {'write_ready': True, 'reasons': []},
            'plan': {
                'counts': {'ads_considered': 1, 'pause_ads': 1, 'reactivate_ads': 0, 'budget_scale_candidates': 0},
                'decisions': [{'ad_name': 'Ad a1', 'action': 'PAUSE_AD', 'spend': 12, 'purchase_roas': .5, 'reason': 'roas_below_or_nd'}],
                'budget_scale_candidates': [],
            },
            'reporting': {'campaigns': [campaign], 'campaign_count': 1, 'source_join_matched': 1, 'leads_total': 20},
            'writes': [],
        }
        rendered = cycle.render_report(run)
        self.assertIn('## 🛑 Corte & ROAS •', rendered)
        self.assertIn('🎯 `1 camp`', rendered)
        self.assertIn('**Legenda:** Ads ↓ = maior→menor ROAS', rendered)
        self.assertIn('🛑n/♻️n = quantidade de anúncios', rendered)
        self.assertIn('R/E (atual/estimado): 🟢 ≥0% | 🟡 <0% e >-15% | 🔴 ≤-15% | ⚪ N/D', rendered)
        self.assertNotIn('Custo por conversa` =', rendered)
        self.assertIn('**📊 Tabela consolidada — visão desktop**', rendered)
        self.assertEqual(rendered.count('```text'), 1)
        self.assertEqual(rendered.count('```'), 2)
        for label in ('R/E', 'Camp', 'Página', 'Status', 'Budget', 'Spend', 'Custo', 'ROAS', 'Ads ↓', 'ROI real', 'ROI est.', 'Leads', 'RPS', 'CPM', 'CTR', 'Ação'):
            self.assertIn(label, rendered)
        for abbreviation in ('Bloco', 'Métrica 1', 'Valor 1', 'Camp/Pg', 'C/msg', 'C/Sub', 'Page ID'):
            self.assertNotIn(abbreviation, rendered)
        self.assertIn('123/pg_12345', rendered)
        self.assertNotIn('123456789012345', rendered)
        self.assertIn('Page One', rendered)
        self.assertIn('0,30', rendered)
        self.assertIn('03·0,92✅ 02·0,76✅ 01·0,30🛑', rendered)
        self.assertIn('+12,3%', rendered)
        self.assertIn('-5,5%', rendered)
        self.assertIn('🟢🟡', rendered)
        self.assertIn('🛑1', rendered)
        self.assertNotIn('🛑 CORTAR', rendered)
        self.assertNotIn('CORTES E ♻️ REATIVAÇÕES POR ANÚNCIO', rendered)
        self.assertNotIn('roas_below_or_nd', rendered)
        self.assertNotIn('Ad a1', rendered)
        self.assertIn('$3,00', rendered)
        self.assertIn('2,00%', rendered)
        self.assertNotIn('$3.00', rendered)
        self.assertNotIn(' │ ', rendered)
        self.assertNotIn(' ║ ', rendered)
        self.assertNotIn('**📌 Decisão e identidade**', rendered)
        self.assertNotIn('**📣 Meta Ads**', rendered)
        self.assertNotIn('**💰 Smart Bidding**', rendered)

    def test_roas_cycle_table_compacts_ad_action_counts(self):
        row = {
            'action_label': 'CORTAR', 'pause_ads': 3, 'reactivate_ads': 1,
            'roi_real': None, 'roi_estimated': None,
        }
        self.assertEqual(cycle._intraday_action_visual(row), '🛑3 ♻️1')
        self.assertEqual(cycle._intraday_action_visual({'action_label': 'MANTER'}), '✅')
        self.assertEqual(cycle._intraday_action_visual({'action_label': 'OBSERVAR'}), '👁️')
        self.assertEqual(cycle._intraday_action_visual({'action_label': 'ESCALA +10%'}), '🚀')

    def test_ads_roas_visual_is_abbreviated_sorted_descending_and_action_aware(self):
        decisions = [
            {'ad_name': 'AD 01 - full creative name', 'purchase_roas': .35, 'action': 'PAUSE_AD', 'configured_status': 'ACTIVE', 'effective_status': 'ACTIVE'},
            {'ad_name': 'AD 03 - full creative name', 'purchase_roas': .92, 'action': 'KEEP', 'configured_status': 'ACTIVE', 'effective_status': 'ACTIVE'},
            {'ad_name': 'AD 02 - full creative name', 'purchase_roas': .56, 'action': 'REACTIVATE_AD', 'configured_status': 'PAUSED', 'effective_status': 'PAUSED'},
            {'ad_name': 'AD 04 - full creative name', 'purchase_roas': None, 'action': 'KEEP', 'configured_status': 'PAUSED', 'effective_status': 'PAUSED'},
        ]
        visual = cycle._ads_roas_visual(decisions)
        self.assertEqual(visual, '03·0,92✅ 02·0,56♻️ 01·0,35🛑 04·N/D⏸')
        self.assertNotIn('full creative name', visual)

    def test_roas_cycle_roi_signal_uses_current_and_future_color_bands(self):
        self.assertEqual(cycle._roi_signal(None), '⚪')
        self.assertEqual(cycle._roi_signal(0), '🟢')
        self.assertEqual(cycle._roi_signal(8.36), '🟢')
        self.assertEqual(cycle._roi_signal(-0.01), '🟡')
        self.assertEqual(cycle._roi_signal(-1), '🟡')
        self.assertEqual(cycle._roi_signal(-7.31), '🟡')
        self.assertEqual(cycle._roi_signal(-14.99), '🟡')
        self.assertEqual(cycle._roi_signal(-15), '🔴')
        self.assertEqual(cycle._roi_signal(-16.52), '🔴')
        self.assertEqual(cycle._roi_signal(-19.99), '🔴')
        self.assertEqual(cycle._roi_signal(-20), '🔴')
        self.assertEqual(cycle._roi_signal(-24.75), '🔴')

    def test_roas_cycle_campaign_key_distinguishes_c_and_dup_variants(self):
        names = [
            '162 - Amy Shook - ENG - US - (pg_5024) C001',
            '162 - Amy Shook - ENG - US - (pg_5024) C001 DUP01',
            '162 - Amy Shook - ENG - US - (pg_5024) C001 DUP02',
            '162 - Amy Shook - ENG - US - (pg_5024) C001 DUP03',
            '162 - Amy Shook - ENG - US - (pg_5024) C001 DUP04',
        ]
        keys = [cycle._campaign_key({'name': name, 'utm_campaign': 'pg_5024'}, index) for index, name in enumerate(names, 1)]
        self.assertEqual(keys, [
            '162·C001/pg_5024',
            '162·C001·D01/pg_5024',
            '162·C001·D02/pg_5024',
            '162·C001·D03/pg_5024',
            '162·C001·D04/pg_5024',
        ])
        self.assertEqual(len(keys), len(set(keys)))

    def test_roas_cycle_fifty_five_variants_are_sorted_and_paginated_ten_per_page(self):
        campaigns = []
        for duplicate in range(55, 0, -1):
            campaigns.append({
                'name': f'162 - Amy Shook - ENG - US - (pg_5024) C001 DUP{duplicate:02d}',
                'utm_campaign': 'pg_5024', 'sb_page_name': 'Amy Shook', 'status': 'ACTIVE',
                'action_label': 'MANTER', 'roi_real': 1, 'roi_estimated': -10,
            })
        rows = cycle._dashboard_desktop_rows(campaigns, .4)
        keys = [row[1] for row in rows]
        self.assertEqual(keys[0], '162·C001·D01/pg_5024')
        self.assertEqual(keys[-1], '162·C001·D55/pg_5024')
        self.assertEqual(len(keys), 55)
        self.assertEqual(len(set(keys)), 55)
        headers = list(cycle.CANONICAL_DESKTOP_HEADERS)
        pages = cycle._compact_table_pages(headers, rows, max_chars=1750, max_rows=10)
        self.assertEqual(len(pages), 6)
        self.assertTrue(all(page.count('\n') <= 13 for page in pages))
        self.assertTrue(all(page.count('```') == 2 for page in pages))

    def test_roas_cycle_desktop_table_aligns_without_wrapping_or_cut_labels(self):
        base = {
            'status': 'ACTIVE', 'name': '123 - Campaign - ENG - US - (pg_12345)',
            'utm_campaign': 'pg_12345', 'sb_page_name': 'Page One',
            'action_label': 'MANTER', 'cost_per_messaging_started': 3,
            'cost_per_message': 2, 'messaging_results': 6, 'budget_usd': 45,
            'spend': 12, 'cpm': 12, 'ctr': 2, 'cpc_link': .4,
            'sb_cost_subscriber': 1.5, 'sb_revenue': 40, 'sb_profit': 28,
            'sb_roi_percent': 233.3, 'sb_leads': 20,
            'sb_drip_roi_percent': 50, 'sb_broadcast_revenue': 18,
            'roi_real': 12.3, 'roi_estimated': -5.5,
        }
        campaigns = [dict(base, purchase_roas=roas) for roas in (.3, .4, .5, None)]
        headers = list(cycle.CANONICAL_DESKTOP_HEADERS)
        pages = cycle._compact_table_pages(headers, cycle._dashboard_desktop_rows(campaigns, .4), max_chars=1750)
        self.assertGreaterEqual(len(pages), 1)
        for table in pages:
            body = table.splitlines()[1:-1]
            expected_width = cycle._display_width(body[0])
            self.assertTrue(all(cycle._display_width(line) == expected_width for line in body))
            self.assertLessEqual(expected_width, 160)
            self.assertNotIn('│', table)
            self.assertNotIn('║', table)
            self.assertEqual(table.count('```'), 2)
        joined = '\n'.join(pages)
        self.assertIn('Custo', joined)
        self.assertNotIn('Métrica 1', joined)
        self.assertIn('ROI est.', joined)

    def test_roas_cycle_first_full_spaced_model_is_the_only_canonical_table(self):
        expected = (
            'R/E', 'Camp', 'Página', 'Status', 'Budget', 'Spend', 'Custo', 'ROAS',
            'Ads ↓', 'ROI real', 'ROI est.', 'Leads', 'RPS', 'CPM', 'CTR', 'Ação',
        )
        self.assertEqual(cycle.CANONICAL_DESKTOP_HEADERS, expected)
        campaign = {
            'name': '162 - Amy Shook - ENG - US - (pg_5024) C001 DUP01',
            'utm_campaign': 'pg_5024', 'sb_page_name': 'Amy Shook', 'status': 'ACTIVE',
            'budget_usd': 45, 'spend': 86.25, 'cost_per_messaging_started': 1.17,
            'purchase_roas': .58,
            'ads_roas': '03·0,92✅ 02·0,56✅ 01·0,35🛑 04·N/D⏸',
            'roi_real': -9.52, 'roi_estimated': -16.52, 'sb_leads': 119,
            'rps': .92, 'cpm': 40.82, 'ctr': 2.34,
            'action_label': 'CORTAR', 'pause_ads': 1, 'reactivate_ads': 0,
        }
        rows = cycle._dashboard_desktop_rows([campaign], .4)
        self.assertEqual(len(rows[0]), len(expected))
        table = cycle._aligned_table(list(expected), rows)
        header, divider, data = table.splitlines()[1:4]
        self.assertRegex(header, r'^R/E {2,}Camp')
        self.assertEqual(set(divider), {'─', ' '})
        self.assertIn('162·C001·D01/pg_5024', data)
        self.assertIn('03·0,92✅', data)
        self.assertIn('119', data)
        self.assertIn('$0,92', data)
        self.assertIn('2,34%', data)
        self.assertNotIn('|', table)
        self.assertNotIn('│', table)
        with self.assertRaisesRegex(ValueError, 'preserve every canonical column'):
            cycle._aligned_table(list(expected), [rows[0][:-1]])

    def test_roas_cycle_multipart_posts_repeat_title_and_keep_fences_balanced(self):
        report = '\n'.join([
            '## 🛑 CORTE & ROAS',
            *['```text\n' + ('row ' + str(index) + ' ' + 'x' * 180) + '\n```' for index in range(20)],
        ])
        stored = {}
        def fake_request(method, path, body=None):
            if method == 'POST':
                self.assertIsInstance(body, dict)
                message_id = str(len(stored) + 1)
                stored[message_id] = body['content']  # type: ignore[index]
                return 200, {'id': message_id}
            message_id = path.rsplit('/', 1)[-1]
            return 200, {'id': message_id, 'content': stored[message_id]}
        with mock.patch.object(common, 'discord_request', side_effect=fake_request):
            result = common.post_to_thread('thread', report, '⚔️ Corte & ROAS')
        self.assertTrue(result['ok'])
        self.assertGreater(result['posted_count'], 1)
        for content in stored.values():
            self.assertLess(len(content), 2000)
            self.assertEqual(content.count('```') % 2, 0)
            self.assertTrue(content.startswith('**⚔️ Corte & ROAS • Parte '))

    def test_roas_cycle_discord_readback_accepts_trimmed_trailing_newline(self):
        stored = {}

        def fake_request(method, path, body=None):
            if method == 'POST':
                self.assertIsInstance(body, dict)
                assert isinstance(body, dict)
                message_id = str(len(stored) + 1)
                stored[message_id] = body['content']
                return 200, {'id': message_id}
            message_id = path.rsplit('/', 1)[-1]
            return 200, {'id': message_id, 'content': stored[message_id].rstrip()}

        with mock.patch.object(common, 'discord_request', side_effect=fake_request):
            result = common.post_to_thread('thread', 'relatório\n', None)

        self.assertTrue(result['ok'])
        self.assertEqual(result['posted_count'], 1)

    def test_roas_cycle_high_volume_keeps_each_campaign_once_in_desktop_table(self):
        campaigns = []
        decisions = []
        for index in range(1, 26):
            name = f'{index:03d} - Full Campaign Name {index} - ENG - US - (pg_{index:05d})'
            campaigns.append({
                'campaign_id': f'c{index}', 'name': name, 'action_emoji': '✅',
                'action_label': 'MANTER', 'action_detail': '1 anúncio(s)',
                'utm_campaign': f'pg_{index:05d}', 'status': 'ACTIVE', 'budget_usd': 45,
                'spend': 1, 'messaging_started': 1, 'cost_per_messaging_started': 1,
                'ctr': 2, 'purchase_roas': .5, 'cpm': 10, 'sb_leads': index,
                'roi_real': None, 'roi_estimated': None, 'block_cpm': None, 'rps': 500,
                'join_status': 'matched',
            })
            decisions.append({'action': 'KEEP'})
        run = {
            'started_at_et': '2026-08-29T20:00:00-04:00', 'phase': 'PHASE_2',
            'threshold': .4, 'mode': 'dry_run', 'meta_status': 'ok', 'smart_bidding_status': 'ok',
            'source_gate': {'write_ready': True, 'reasons': []},
            'plan': {
                'counts': {'ads_considered': 25, 'pause_ads': 0, 'reactivate_ads': 0, 'budget_scale_candidates': 0},
                'decisions': decisions, 'budget_scale_candidates': [],
            },
            'reporting': {'campaigns': campaigns, 'campaign_count': 25, 'source_join_matched': 25, 'leads_total': 325},
            'writes': [],
        }
        rendered = cycle.render_report(run)
        for index, row in enumerate(campaigns, start=1):
            self.assertEqual(rendered.count(f'{index:03d}/{row["utm_campaign"]}'), 1)
        self.assertIn('**📊 Tabela consolidada — visão desktop • 1/', rendered)
        self.assertNotIn('**📌 Decisão e identidade', rendered)
        self.assertNotIn('**📣 Meta Ads', rendered)
        self.assertNotIn('**💰 Smart Bidding', rendered)
        self.assertNotIn('│', rendered)
        self.assertNotIn('║', rendered)
        chunks = common.split_messages(rendered, limit=1750)
        self.assertTrue(all(len(chunk) <= 1750 for chunk in chunks))
        self.assertTrue(all(chunk.count('```') % 2 == 0 for chunk in chunks))

    def test_auto_0800_returns_previous_and_current(self):
        at = dt.datetime(2026, 8, 29, 8, 0, tzinfo=ET)
        dates = daily.report_dates('auto', at)
        self.assertEqual([row[0] for row in dates], ['2026-08-28', '2026-08-29'])
        self.assertEqual([row[1] for row in dates], ['Fechamento D-1', 'Sinal atual 08:00'])

    def test_auto_other_time_returns_current_only(self):
        at = dt.datetime(2026, 8, 29, 6, 0, tzinfo=ET)
        self.assertEqual(daily.report_dates('auto', at), [('2026-08-29', 'Parcial atual')])

    def test_daily_source_filters_exact_date_and_accepts_verified_delay(self):
        bundle = {
            'ready': False,
            'reason': 'smart_bidding_freshness_unverifiable',
            'economic_freshness': {
                'ready': True, 'age_minutes': 12, 'current_fill_time': '2026-08-30T08:00:00-04:00',
                'evidence': 'Smart Bidding /estimated/delay',
            },
            'target_report_rows': [
                {'DATE': '2026-08-29', 'UTM_CAMPAIGN': 'pg_1', 'REVENUE': 100},
                {'DATE': '2026-08-30', 'UTM_CAMPAIGN': 'pg_2', 'REVENUE': 200},
            ],
        }
        prepared = daily.prepare_daily_sb_bundle(bundle, '2026-08-30')
        self.assertTrue(prepared['daily_reporting_ready'])
        self.assertEqual([row['UTM_CAMPAIGN'] for row in prepared['target_report_rows']], ['pg_2'])
        self.assertEqual(prepared['freshness']['timestamp_field'], 'estimated.delay.currentFillTime')

    def test_smart_bidding_aggregation_does_not_invent_roi(self):
        bundle = {'ready': True, 'target_report_rows': [{'UTM_CAMPAIGN': 'pg_12345', 'INVESTIMENT': 10, 'REVENUE': 20, 'LEADS': 5, 'SESSIONS': 40, 'ACQUISITION_CLICKS': 10, 'AVG_PRICE': 6.2}], 'available_account_names': ['Eggbev-US-CC-EN-01']}
        result = daily.aggregate_sb(bundle)
        self.assertEqual(result['investment'], 10)
        self.assertEqual(result['revenue'], 20)
        self.assertIsNone(result['roi_real'])
        self.assertEqual(result['rps_gross'], 500)
        self.assertEqual(result['epc_gross'], 2)

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

    def test_cost_per_started_message_uses_exact_meta_action(self):
        bundle = {'insights': [{
            'campaign_id': 'c1', 'campaign_name': 'C', 'spend': '12', 'impressions': '1000', 'ctr': '2',
            'actions': [
                {'action_type': 'onsite_conversion.messaging_first_reply', 'value': '6'},
                {'action_type': 'onsite_conversion.messaging_conversation_started_7d', 'value': '4'},
            ],
        }]}
        result = daily.aggregate_meta(bundle)
        self.assertEqual(result['messaging_started'], 4)
        self.assertEqual(result['cost_per_messaging_started'], 3)
        self.assertEqual(result['campaigns'][0]['messaging_started'], 4)
        self.assertEqual(result['campaigns'][0]['cost_per_messaging_started'], 3)

    def test_unified_join_uses_exact_utm_and_page_id(self):
        meta_bundle = {
            'insights': [{
                'ad_id': 'a1', 'campaign_id': 'c1', 'campaign_name': 'Campaign pg_12345',
                'spend': '12', 'impressions': '1000', 'ctr': '2',
                'actions': [{'action_type': 'onsite_conversion.messaging_conversation_started_7d', 'value': '4'}],
            }],
            'campaign_readbacks': [{'id': 'c1', 'name': 'Campaign pg_12345', 'status': 'ACTIVE', 'effective_status': 'ACTIVE', 'daily_budget': '4500'}],
            'ad_readbacks': [{
                'id': 'a1', 'campaign': {'id': 'c1'},
                'creative': {'url_tags': 'utm_campaign=pg_12345', 'object_story_spec': {'page_id': 'page1'}},
            }],
        }
        sb_bundle = {
            'ready': True,
            'target_report_rows': [{
                'UTM_CAMPAIGN': 'pg_12345', 'INVESTIMENT': 11, 'REVENUE': 10,
                'LEADS': 20, 'SESSIONS': 20, 'ACQUISITION_CLICKS': 5, 'AVG_PRICE': 6.2,
            }],
            'page_index': {'pg_12345': [{'UTM_CAMPAIGN': 'pg_12345', 'FB_PAGE_ID': 'page1', 'PAGE_NAME': 'Page One'}]},
        }
        meta = daily.aggregate_meta(meta_bundle)
        sb = daily.aggregate_sb(sb_bundle)
        row = daily.merge_campaign_sources(meta, sb)['campaigns'][0]
        self.assertEqual(row['join_status'], 'matched')
        self.assertEqual(row['cost_per_messaging_started'], 3)
        self.assertEqual(row['sb_investment'], 11)
        self.assertEqual(row['sb_revenue'], 10)
        self.assertEqual(row['sb_leads'], 20)
        self.assertEqual(row['pricing_avg'], 6.2)
        self.assertEqual(row['pricing_rps'], 500)
        self.assertEqual(row['pricing_epc'], 2)

    def test_unified_join_page_mismatch_is_fail_closed(self):
        meta = {'campaigns': [{'utm_campaign': 'pg_12345', 'meta_page_id': 'page1'}]}
        sb = {
            'ready': True,
            'by_utm': {'pg_12345': {
                'sb_page_id': 'page2', 'investment': 11, 'revenue': 10, 'leads': 20,
                'avg_price': 6.2, 'rps_gross': 500, 'epc_gross': 2,
            }},
        }
        row = daily.merge_campaign_sources(meta, sb)['campaigns'][0]
        self.assertEqual(row['join_status'], 'meta_sb_page_id_mismatch')
        self.assertIsNone(row['sb_revenue'])
        self.assertIsNone(row['pricing_rps'])

    def test_unified_join_stale_source_is_fail_closed(self):
        meta = {'campaigns': [{'utm_campaign': 'pg_12345', 'meta_page_id': 'page1'}]}
        sb = {
            'ready': False, 'reason': 'smart_bidding_freshness_unverifiable',
            'by_utm': {'pg_12345': {'sb_page_id': 'page1'}},
        }
        row = daily.merge_campaign_sources(meta, sb)['campaigns'][0]
        self.assertEqual(row['join_status'], 'smart_bidding_freshness_unverifiable')
        self.assertIsNone(row['pricing_epc'])

    def test_active_campaign_without_insight_remains_visible(self):
        bundle = {
            'insights': [],
            'campaigns': [{
                'id': 'c1', 'name': '125 - Full Name - ENG - US - (pg_99999)',
                'status': 'ACTIVE', 'effective_status': 'ACTIVE',
                'daily_budget': '4500', 'start_time': '2026-08-30T00:00:00-0400',
            }],
        }
        result = daily.aggregate_meta(bundle)
        self.assertEqual(result['campaigns_in_scope'], 1)
        self.assertEqual(result['active_without_insight'], 1)
        row = result['campaigns'][0]
        self.assertFalse(row['has_insight'])
        self.assertIsNone(row['spend'])
        self.assertEqual(row['budget_usd'], 45.0)
        self.assertEqual(row['status'], 'ACTIVE')

    def test_d1_scope_keeps_only_campaigns_that_ran_in_d1(self):
        meta = {
            'campaigns': [
                {'campaign_id': 'ran', 'has_insight': True, 'join_status': 'matched'},
                {'campaign_id': 'future-active', 'has_insight': False, 'join_status': 'sb_utm_not_found'},
            ],
            'active_without_insight': 1,
            'source_join_matched': 1,
        }
        scoped = daily.apply_period_campaign_scope(meta, 'Fechamento D-1')
        self.assertEqual([row['campaign_id'] for row in scoped['campaigns']], ['ran'])
        self.assertEqual(scoped['active_without_d1_insight_excluded'], 1)
        self.assertEqual(scoped['campaigns_in_scope'], 1)
        self.assertEqual(scoped['source_join_matched'], 1)
        current = daily.apply_period_campaign_scope(meta, 'Parcial atual')
        self.assertEqual(len(current['campaigns']), 2)

    def test_campaign_row_has_all_approved_metrics(self):
        bundle = {
            'insights': [{
                'campaign_id': 'c1', 'campaign_name': 'Long campaign name',
                'spend': '10', 'impressions': '1000', 'ctr': '2',
                'actions': [{'action_type': 'onsite_conversion.messaging_first_reply', 'value': '5'}],
                'action_values': [{'action_type': 'purchase', 'value': '4'}],
            }],
            'campaign_readbacks': [{
                'id': 'c1', 'name': 'Long campaign name', 'status': 'PAUSED',
                'effective_status': 'PAUSED', 'daily_budget': '7000',
                'start_time': '2026-08-03T13:16:33-0400',
            }],
        }
        row = daily.aggregate_meta(bundle)['campaigns'][0]
        self.assertEqual(row['status'], 'PAUSED')
        self.assertEqual(row['budget_usd'], 70.0)
        self.assertAlmostEqual(row['purchase_roas'], 0.4)
        self.assertAlmostEqual(row['cost_per_message'], 2.0)
        self.assertAlmostEqual(row['cpm'], 10.0)
        self.assertAlmostEqual(row['ctr'], 2.0)
        self.assertIn('estado atual PAUSED', row['note'])

    def test_render_has_all_25_compact_campaign_keys_without_silent_limit(self):
        names = [f'{index:03d} - Full Campaign Name {index} - ENG - US - (pg_{index:05d})' for index in range(1, 26)]
        campaigns = [{
            'name': name, 'status': 'ACTIVE', 'start_time': '2026-08-30T00:00:00-0400',
            'budget_usd': 45.0, 'spend': 1.0, 'purchase_roas': 0.5,
            'messaging_results': 1.0, 'cost_per_message': 1.0, 'cpm': 10.0,
            'ctr': 2.0, 'has_insight': True, 'note': 'Entrega no período',
        } for name in names]
        period = {
            'label': 'Parcial atual', 'date': '2026-08-29',
            'meta': {'campaigns': campaigns, 'campaigns_in_scope': 25},
            'smart_bidding': daily.aggregate_sb({'ready': False, 'reason': 'target_missing', 'target_report_rows': [], 'freshness': {'ready': False, 'max_age_hours': 2.0}}),
        }
        rendered = '\n'.join(daily.render_period(period))
        self.assertIn('Visão unificada · Página → fonte de clone', rendered)
        self.assertIn('**N/D** · 25 campanhas', rendered)
        self.assertIn('Tabela da página • 1/3', rendered)
        self.assertIn('Tabela da página • 3/3', rendered)
        for name in names:
            self.assertIn(daily.source_alias(name, None), rendered)

    def test_smart_bidding_freshness_is_explicit_and_nd_is_not_percent(self):
        period = {
            'label': 'Parcial atual', 'date': '2026-08-29',
            'meta': {'campaigns': [], 'ctr': None},
            'smart_bidding': daily.aggregate_sb({
                'ready': False, 'reason': 'smart_bidding_freshness_unverifiable',
                'target_report_rows': [{}],
                'freshness': {'ready': False, 'reason': 'smart_bidding_freshness_unverifiable', 'max_age_hours': 2.0, 'timestamp_field': None},
            }),
        }
        rendered = '\n'.join(daily.render_period(period))
        self.assertIn('⏱ SB', rendered)
        self.assertIn('campo N/D', rendered)
        self.assertIn('máx. 2h', rendered)
        self.assertNotIn('N/D%', rendered)

    def test_compact_renderer_exposes_meta_sb_and_pricing_columns(self):
        campaign = {
            'name': 'Campaign pg_12345', 'status': 'ACTIVE', 'utm_campaign': 'pg_12345',
            'join_status': 'matched', 'spend': 12.0, 'messaging_started': 4.0,
            'cost_per_messaging_started': 3.0, 'purchase_roas': 0.5, 'cpm': 10.0,
            'sb_investment': 11.0, 'sb_revenue': 10.0, 'sb_leads': 20.0,
            'pricing_avg': 6.2, 'pricing_rps': 500.0, 'pricing_epc': 2.0,
        }
        period = {
            'label': 'Parcial atual', 'date': '2026-08-29',
            'meta': {'campaigns': [campaign], 'source_join_matched': 1},
            'smart_bidding': daily.aggregate_sb({'ready': True, 'target_report_rows': []}),
        }
        rendered = '\n'.join(daily.render_period(period))
        self.assertIn('Visão unificada · Página → fonte de clone', rendered)
        self.assertIn('BC agora', rendered)
        self.assertIn('$/Msg', rendered)
        self.assertIn('CPM', rendered)
        self.assertIn('RPS', rendered)
        self.assertIn('1/1 campanhas', rendered)

    def test_daily_groups_pages_z_to_a_and_uses_current_dashboard_broadcast(self):
        campaigns = [
            {'name': '001 C001', 'campaign_id': '1', 'utm_campaign': 'pg_1', 'sb_page_name': 'Amy Shook', 'status': 'ACTIVE', 'spend': 1, 'has_insight': True},
            {'name': '002 C001', 'campaign_id': '2', 'utm_campaign': 'pg_2', 'sb_page_name': 'Tina Walter', 'status': 'ACTIVE', 'spend': 2, 'has_insight': True},
            {'name': '003 C001', 'campaign_id': '3', 'utm_campaign': 'pg_3', 'sb_page_name': 'Celia Draper', 'status': 'ACTIVE', 'spend': 3, 'has_insight': True},
            {'name': '004 C001', 'campaign_id': '4', 'utm_campaign': 'pg_9', 'sb_page_name': None, 'status': 'PAUSED', 'spend': 0, 'has_insight': True},
        ]
        current = {
            'ready': True, 'date': '2026-08-31', 'broadcast_revenue': 9.0,
            'freshness': {'latest_at_et': '2026-08-31T04:42:00Z', 'age_minutes': 66},
            'by_utm': {
                'pg_1': {'broadcast_revenue': 1.0},
                'pg_2': {'broadcast_revenue': 5.0},
                'pg_3': {'broadcast_revenue': 3.0},
            },
        }
        pages = daily.build_page_summary(campaigns, current)
        self.assertEqual([row['page_name'] for row in pages], ['Tina Walter', 'Celia Draper', 'Amy Shook', ''])
        rendered = '\n'.join(daily.render_grouped_page_tables(pages, campaigns))
        self.assertLess(rendered.index('Tina Walter'), rendered.index('Celia Draper'))
        self.assertLess(rendered.index('Celia Draper'), rendered.index('Amy Shook'))
        self.assertLess(rendered.index('Amy Shook'), rendered.index('pg_9'))
        self.assertIn('BC agora $5,00', rendered)

    def test_revenue_anomaly_uses_equivalent_median_and_30_40_bands(self):
        state = daily.default_anomaly_state()
        for date, revenue in [('2026-08-26', 90), ('2026-08-27', 100), ('2026-08-28', 110)]:
            state = daily.upsert_anomaly_snapshot(state, {
                'eligible': True, 'date': date, 'kind': 'same_clock', 'cutoff': '08:00',
                'pages': [{'page_id': 'page1', 'utm_campaign': 'pg_1', 'page_name': 'Page One', 'revenue': revenue}],
            }, date + 'T08:00:00-04:00')
        policy = {
            'baseline_days': 7, 'minimum_comparable_samples': 3,
            'warning_drop_percent': 30, 'critical_drop_percent': 40,
        }
        critical = daily.analyze_revenue_snapshot({
            'eligible': True, 'date': '2026-08-29', 'kind': 'same_clock', 'cutoff': '08:00',
            'pages': [{'page_id': 'page1', 'utm_campaign': 'pg_1', 'page_name': 'Page One', 'revenue': 60}],
        }, state, policy)
        self.assertEqual(critical['status'], 'alert')
        self.assertEqual(critical['alerts'][0]['severity'], 'critical')
        self.assertAlmostEqual(critical['alerts'][0]['baseline_median_revenue'], 100)
        self.assertAlmostEqual(critical['alerts'][0]['drop_percent'], 40)
        warning = daily.analyze_revenue_snapshot({
            'eligible': True, 'date': '2026-08-29', 'kind': 'same_clock', 'cutoff': '08:00',
            'pages': [{'page_id': 'page1', 'utm_campaign': 'pg_1', 'page_name': 'Page One', 'revenue': 70}],
        }, state, policy)
        self.assertEqual(warning['alerts'][0]['severity'], 'warning')

    def test_revenue_anomaly_fails_visible_when_source_or_baseline_is_missing(self):
        source_missing = daily.analyze_revenue_snapshot(
            {'eligible': False, 'reason': 'smart_bidding_freshness_unverifiable'},
            daily.default_anomaly_state(), {},
        )
        self.assertEqual(source_missing['status'], 'source_unavailable')
        self.assertIn('sem leitura confiável', daily.anomaly_bullets(source_missing)[0])
        baseline = daily.analyze_revenue_snapshot({
            'eligible': True, 'date': '2026-08-29', 'kind': 'same_clock', 'cutoff': '08:00',
            'pages': [{'page_id': 'page1', 'utm_campaign': 'pg_1', 'revenue': 80}],
        }, daily.default_anomaly_state(), {'minimum_comparable_samples': 3})
        self.assertEqual(baseline['status'], 'baseline_forming')
        self.assertIn('Baseline de receita em formação', daily.anomaly_bullets(baseline)[0])

        not_comparable = daily.analyze_revenue_snapshot(
            {'eligible': False, 'reason': 'period_not_anomaly_comparable'},
            daily.default_anomaly_state(), {},
        )
        self.assertEqual(not_comparable['status'], 'not_comparable_window')
        self.assertIn('não aplicado nesta parcial', daily.anomaly_bullets(not_comparable)[0])

    def test_operational_alerts_flag_duplicate_names_and_name_utm_mismatch(self):
        period = {'meta': {'campaigns': [
            {'name': '165 - Tina - (pg_5071) C003', 'utm_campaign': 'pg_5071', 'sb_page_name': 'Tina'},
            {'name': '165 - Tina - (pg_5071) C003', 'utm_campaign': 'pg_5071', 'sb_page_name': 'Tina'},
            {'name': '165 - Tina - (pg_5071) C003 DUP03', 'utm_campaign': 'pg_5024', 'sb_page_name': 'Amy'},
        ]}}
        bullets = daily.operational_alert_bullets(period)
        self.assertTrue(any('Nome duplicado' in bullet for bullet in bullets))
        self.assertTrue(any('Naming/UTM divergente' in bullet and 'pg_5024' in bullet for bullet in bullets))

    def test_discord_split_keeps_fences_balanced_without_omitting_compact_keys(self):
        names = [f'{index:03d} - Full Campaign Name {index} - ENG - US - (pg_{index:05d})' for index in range(1, 26)]
        campaigns = [{
            'name': name, 'status': 'ACTIVE', 'start_time': '2026-08-30T00:00:00-0400',
            'budget_usd': 45.0, 'spend': 1.0, 'purchase_roas': 0.5,
            'messaging_results': 1.0, 'cost_per_message': 1.0, 'cpm': 10.0,
            'ctr': 2.0, 'has_insight': True, 'note': 'Entrega no período',
        } for name in names]
        period = {
            'label': 'Parcial atual', 'date': '2026-08-29',
            'meta': {'campaigns': campaigns, 'campaigns_in_scope': 25},
            'smart_bidding': daily.aggregate_sb({'ready': False, 'reason': 'target_missing', 'target_report_rows': [], 'freshness': {'ready': False, 'max_age_hours': 2.0}}),
        }
        report = '\n'.join(daily.render_period(period))
        chunks = common.split_messages(report, limit=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 500 for chunk in chunks))
        self.assertTrue(all(chunk.count('```') % 2 == 0 for chunk in chunks))
        joined = '\n'.join(chunks)
        for name in names:
            self.assertIn(daily.source_alias(name, None), joined)

    def test_source_alias_is_stable_and_tracking_conflicts_are_visible(self):
        name = '165 - Tina Walter - ENG - US - (pg_5071) C003 DUP01'
        self.assertEqual(daily.source_alias(name, 'campaign-1'), daily.source_alias(name, 'campaign-1'))
        annotated = daily.annotate_campaign_display_identities({'campaigns': [{
            'campaign_id': 'campaign-1', 'name': name, 'utm_campaign': 'pg_5024',
            'sb_page_name': 'Amy Shook', 'join_status': 'matched',
        }]})
        row = annotated['campaigns'][0]
        self.assertTrue(row['source_alias'].startswith('SRC-165-C003-D01-'))
        self.assertEqual(row['identity_signal'], '⚠️')
        self.assertIn('name_utm_mismatch', row['identity_reasons'])
        self.assertIn('name_page_mismatch', row['identity_reasons'])


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operation = json.loads((BASE / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json').read_text())

    def test_meta_account_is_exact(self):
        self.assertEqual(self.operation['smart_bidding_reconciliation']['target_meta_account_id'], 'act_1034081997659047')

    def test_roas_status_writes_and_cron_are_enabled_but_budget_write_is_not(self):
        runtime = self.operation['roas_cycle_policy']['runtime']
        self.assertTrue(runtime['write_enabled'])
        self.assertTrue(runtime['post_enabled'])
        self.assertTrue(runtime['cron_enabled'])
        self.assertFalse(runtime['budget_write_enabled'])
        self.assertTrue(runtime['phase3_budget_write_enabled'])
        self.assertTrue(runtime['phase3_parent_status_write_enabled'])

    def test_phase3_contract_matches_nicolas_exact_recycling_policy(self):
        roas = self.operation['roas_cycle_policy']
        phase3 = roas['phase_3_recycling']
        self.assertEqual(roas['formation_window']['to_exclusive'], '05:00')
        self.assertEqual(roas['phase_1']['times'], ['05:00', '06:00', '08:00', '10:00', '12:00'])
        self.assertEqual(roas['phase_2']['night_no_roas_scope']['times'], ['20:00', '22:00', '23:00'])
        self.assertEqual(phase3['time'], '00:00')
        self.assertTrue(phase3['ordered_inside_existing_midnight_job'])
        self.assertEqual(phase3['activation_roas_minimum'], .38)
        self.assertEqual(phase3['activation_roas_operator'], '>=')
        self.assertTrue(phase3['manual_pause_override_authorized'])
        self.assertEqual(phase3['page_leads_exclusion']['operator'], '>')
        self.assertEqual(phase3['page_leads_exclusion']['threshold'], 5000)
        self.assertEqual(phase3['campaign_budget']['choices_usd'], [45, 65])
        self.assertTrue(phase3['campaign_budget']['write_enabled'])
        self.assertEqual(phase3['normal_cut_resume_at'], '05:00')
        self.assertTrue(phase3['reporting']['title_must_identify_phase3'])

    def test_daily_build_does_not_enable_post_or_cron(self):
        runtime = self.operation['daily_reporting_policy']['runtime']
        self.assertFalse(runtime['post_enabled'])
        self.assertFalse(runtime['cron_enabled'])

    def test_daily_page_grouped_contract_uses_exact_keys_and_formulas(self):
        renderer = self.operation['daily_reporting_policy']['renderer_contract']
        self.assertIn('page_grouped_desktop_v6', renderer['status'])
        self.assertIn('descending Z-to-A', renderer['layout'])
        self.assertIn('sequence·Cnnn·Dnn', renderer['per_campaign_fields'][0])
        self.assertIn('current dashboard Broadcast revenue from /report/messenger BD_REVENUE', renderer['per_page_smart_bidding_fields'])
        self.assertIn('spend-weighted Meta Purchase ROAS', renderer['per_page_meta_fields'])
        self.assertIn('UTM_CAMPAIGN', renderer['source_join']['primary'])
        self.assertIn('FB_PAGE_ID', renderer['source_join']['identity_confirmation'])
        self.assertIn('messaging_conversation_started_7d', renderer['metric_formulas']['cost_per_messaging_started'])
        self.assertIn('fallback', renderer['metric_formulas']['gross_rps_fallback_only'])
        self.assertIn('fallback', renderer['metric_formulas']['gross_epc_fallback_only'])
        direct = renderer['smart_bidding_direct_sources']
        self.assertEqual(direct['accepted_routes'], ['vertical', 'Messenger Pages', 'domain'])
        self.assertIn('prefer the direct Smart Bidding metric value', direct['direct_field_policy'])
        self.assertIn('currency', direct['required_readback'])

    def test_daily_reporting_change_does_not_enable_any_write(self):
        policy = self.operation['daily_reporting_policy']
        self.assertEqual(policy['mode'], 'read_only')
        self.assertFalse(policy['runtime']['post_enabled'])
        self.assertFalse(policy['runtime']['cron_enabled'])
        self.assertIn('never cuts', policy['action_policy'])

    def test_roas_reporting_v22_locks_full_spaced_table_with_leads_rps_and_ctr(self):
        reporting_policy = self.operation['roas_cycle_policy']['reporting']
        self.assertIn('v22_full_spaced_locked_active', reporting_policy['status'])
        self.assertIn('one short direct legend below the table; no long explanatory block', reporting_policy['layout'])
        self.assertIn('Camp uses a compact unique sequence+C+DUP+UTM key such as 162·C001·D01/pg_5024', reporting_policy['layout'])
        large_table = reporting_policy['campaign_identity_and_large_table_correction']
        self.assertEqual(large_table['validation']['high_volume_fixture_campaigns'], 55)
        self.assertEqual(large_table['validation']['unique_compact_keys'], 55)
        self.assertEqual(large_table['validation']['expected_table_parts'], 6)
        self.assertIn('maximum ten campaign rows', large_table['pagination'])
        self.assertTrue(reporting_policy['unicode_spacing_correction']['validation']['unicode_alignment_regression'])
        desktop = reporting_policy['cpv13_intraday_print_correction']
        self.assertEqual(desktop['manager_approval']['approved_by'], 'Nicolas Holanda')
        self.assertEqual(desktop['manager_approval']['change_control'], 'locked_after_v22_no_further_table_changes')
        self.assertIn('until the manager explicitly requests the next change', desktop['manager_approval']['decision'])
        self.assertTrue(desktop['validation']['single_table'])
        self.assertTrue(desktop['validation']['one_row_per_campaign'])
        self.assertGreaterEqual(desktop['validation']['single_campaign_display_width'], 122)
        self.assertTrue(desktop['validation']['aligned_rows'])
        self.assertFalse(desktop['validation']['generic_metric_value_headers'])
        self.assertFalse(desktop['validation']['vertical_bar_separators'])
        self.assertEqual(desktop['columns'], ['R/E', 'Camp', 'Página', 'Status', 'Budget', 'Spend', 'Custo', 'ROAS', 'Ads ↓', 'ROI real', 'ROI est.', 'Leads', 'RPS', 'CPM', 'CTR', 'Ação'])
        ad_only = reporting_policy['ad_only_and_compact_ad_roas_correction']
        self.assertIn('ad status only', ad_only['decision'])
        self.assertIn('highest-to-lowest ROAS', ad_only['table_format'])
        self.assertFalse(ad_only['full_ad_name_visible'])
        self.assertFalse(ad_only['technical_ad_id_visible'])
        self.assertEqual(self.operation['cut_level']['roas_zero_active_ads_exception'], 'none')
        self.assertEqual(self.operation['cut_level']['roas_campaign_action'], 'none')
        self.assertFalse(self.operation['roas_cycle_policy']['zero_active_ads_after_cycle']['pause_campaign'])
        self.assertFalse(self.operation['roas_cycle_policy']['zero_active_ads_after_cycle']['pause_adset'])
        self.assertIn('one campaign per row with direct semantic headings instead of generic metric/value headings', reporting_policy['layout'])
        fields = reporting_policy['per_campaign_metrics']
        for expected in (
            'Ligada with visual yes/no signal', 'Campanha compact sequence plus C/DUP variant plus UTM',
            'Entrega', 'Ação from the Ares cycle decision', 'Página name',
            'Cost per messaging conversation started',
            'Meta Purchase ROAS with directional below/equal/above/unavailable threshold marker',
            'Abbreviated ad slots with Purchase ROAS and ad action/status, sorted descending by ROAS',
            'Cost per result', 'Results', 'Budget USD', 'Amount spent USD',
            'Meta CPM', 'Meta CTR link click-through rate', 'Meta CPC link click',
            'Smart Bidding Cost Subscriber', 'Smart Bidding Revenue', 'Smart Bidding Profit',
            'Smart Bidding ROI percent', 'Smart Bidding LEADS',
            'Smart Bidding DRIP ROI percent', 'Smart Bidding Broadcast Revenue',
            'ROI atual report-only percentage', 'ROI estimado report-only percentage',
        ):
            self.assertIn(expected, fields)
        self.assertNotIn('Smart Bidding Page ID', fields)
        self.assertLess(fields.index('Campanha compact sequence plus C/DUP variant plus UTM'), fields.index('Página name'))
        self.assertLess(fields.index('Página name'), fields.index('Entrega'))
        self.assertIn('Page ID is hidden', reporting_policy['display_exclusions'][0])
        self.assertIn('$1,86', reporting_policy['display_currency_format'])
        self.assertEqual(reporting_policy['roas_visual_policy']['below_threshold'], 'down arrow; not negative')
        self.assertEqual(reporting_policy['roas_visual_policy']['equal_threshold'], 'target marker')
        self.assertEqual(reporting_policy['roas_visual_policy']['above_threshold'], 'up arrow; not positive ROI')
        self.assertIn('only ROI below 0 percent is labeled negative', reporting_policy['semantic_distinction'])
        self.assertIn('greater than or equal to 0', reporting_policy['roi_visual_policy']['positive_or_zero'])
        self.assertIn('above -15', reporting_policy['roi_visual_policy']['negative_warning'])
        self.assertIn('less than or equal to -15', reporting_policy['roi_visual_policy']['negative_critical'])
        source_correction = reporting_policy['roi_pair_source_and_color_correction']
        self.assertEqual(source_correction['display_order'], 'R/E always shows current ROI first and estimated future ROI second')
        self.assertIn('/estimated/revenue/utm_adgroup', source_correction['source_confirmation'])
        self.assertEqual(source_correction['color_bands']['yellow'], 'ROI < 0% and > -15%')
        roi_v20 = reporting_policy['roi_color_bands_v20']
        self.assertIn('fractional negatives such as -0.1% in yellow', roi_v20['deterministic_continuous_interpretation'])
        ctr_v21 = reporting_policy['ctr_and_compact_insight_v21']
        self.assertEqual(ctr_v21['column_position'], 'after CPM and before Ação')
        self.assertIn('future insights cannot add, remove, reorder or compress table columns', ctr_v21['future_insight_rule'])
        full_v22 = reporting_policy['canonical_full_spaced_table_v22']
        self.assertEqual(full_v22['columns'], list(cycle.CANONICAL_DESKTOP_HEADERS))
        self.assertIn('Leads', full_v22['mandatory_columns'])
        self.assertIn('RPS', full_v22['mandatory_columns'])
        self.assertIn('reduced explanatory subset', full_v22['rejected_reference'])
        self.assertIn('shortened table subsets are forbidden', full_v22['manual_examples'])
        self.assertIn('no future table modification', full_v22['layout_lock'])
        self.assertIn('same future-estimate backend', reporting_policy['source_routes']['economics_estimated'])
        formulas = reporting_policy['report_only_formulas']
        for key in ('cpc_link_usd', 'cost_subscriber_usd', 'profit_usd', 'smart_bidding_roi_percent', 'drip_roi_percent'):
            self.assertIn(key, formulas)
        self.assertIn('Meta Purchase ROAS decides only ad-level cuts/reactivations', reporting_policy['decision_separation'])
        self.assertIn('performance_per_campaigns', reporting_policy['source_routes']['economics_actual'])
        self.assertIn('pagination uses actual rendered character count', reporting_policy['pagination'])
        self.assertIn('never splits a campaign row', reporting_policy['pagination'])
        self.assertIn('keeps every code fence balanced', reporting_policy['pagination'])
        self.assertFalse(self.operation['roas_cycle_policy']['runtime']['budget_write_enabled'])

    def test_native_rule_disable_is_future_only(self):
        transition = self.operation['roas_cycle_policy']['native_rule_transition']
        self.assertTrue(transition['disable_authorized_at_future_activation'])
        self.assertFalse(transition['execute_now'])

    def test_clone_page_switch_schema_ready_but_copied_adset_write_blocked(self):
        cloning = self.operation['campaign_cloning_policy']
        mode = cloning['allowed_modes']['clone_page_switch']
        self.assertIn('selected and confirmed', mode['daily_budget'])
        self.assertEqual(mode['start_time'], 'next_day_00:00_America/New_York')
        self.assertIn('ACTIVE', mode['delivery_state'])
        self.assertEqual(mode['media_and_copy'], 'preserve source media and copy')
        page_policy = mode['target_page_selection']
        self.assertIn('pause the intake', page_policy['default'])
        self.assertIn('forbidden', page_policy['automatic_selection'])
        self.assertIn('no manifest sealing, no Meta write', page_policy['missing_page_behavior'])
        self.assertIn('audit compatibility', mode['engine_support'])
        self.assertIn('fail-closed at Engine v3 account prevalidation', mode['engine_support'])
        live = mode['live_runtime_evidence_20260831']
        self.assertIn('1885090', live['copied_adset_page_switch'])
        self.assertIn('zero ads', live['partial_shell'])
        self.assertIn('Nicolas explicitly authorized', live['manager_approved_recovery_completed'])
        self.assertIn('2238280', live['additional_live_failures'])
        self.assertIn('fail before any Meta write', live['prevention'])
        self.assertIn('direct GETs', live['readback_recovery'])
        self.assertTrue(cloning['engine_readback']['eggbev_account_registered'])
        self.assertIn('manager-selected budget materialized explicitly', cloning['execution_gates'])
        self.assertIn('Nicolas exact budget instruction or approved operation policy satisfied', cloning['execution_gates'])

    def test_normal_creation_is_active_future_and_canary_remains_paused(self):
        policy = self.operation['campaign_structure']['delivery_state_policy']
        self.assertIn('ACTIVE', policy['normal_production_after_final_summary_approval'])
        self.assertIn('future start_time', policy['normal_production_after_final_summary_approval'])
        self.assertIn('PAUSED', policy['technical_canary'])

    def test_scaling_is_10_percent_every_cycle_strictly_above_0_50_but_write_disabled(self):
        policy = self.operation['campaign_scaling_policy']
        self.assertEqual(policy['roas_threshold'], 0.50)
        self.assertEqual(policy['operator'], '>')
        self.assertEqual(policy['increase_percent'], 10)
        self.assertIn('every approved ROAS action cycle', policy['frequency'])
        self.assertFalse(policy['budget_write_enabled'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
