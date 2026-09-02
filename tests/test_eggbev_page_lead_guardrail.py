import datetime as dt
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path('/root/mgs-agent/scripts/ares-eggbev-page-lead-guardrail.py')
spec = importlib.util.spec_from_file_location('eggbev_lead_guardrail', MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def campaign(cid='c1', name='155 - Jolie - ENG - US - (pg_5083) C001 - Copy'):
    return {'id': cid, 'name': name, 'status': 'ACTIVE', 'effective_status': 'ACTIVE', 'daily_budget': '6560'}


def ad(cid='c1', page_id='123', url_tags='utm_campaign=pg_5083'):
    return {
        'id': 'a1',
        'effective_status': 'ACTIVE',
        'campaign': {'id': cid},
        'creative': {'object_story_spec': {'page_id': page_id}, 'url_tags': url_tags},
    }


def sb_row(leads=5001, utm='pg_5083', page_id='123', restricted_until=None,
           updated_at: str | None = '2026-08-29T12:00:00-04:00'):
    row = {
        'UTM_CAMPAIGN': utm,
        'FB_PAGE_ID': page_id,
        'PAGE_NAME': 'Jolie',
        'LEADS': leads,
        'LEADS_TOTAL': 9000,
        'STATUS': 'Campaign',
        'RESTRICTED_UNTIL': restricted_until,
    }
    if updated_at is not None:
        row['UPDATED_AT'] = updated_at
    return row


def evaluate(leads=5001, **kwargs):
    return mod.evaluate_campaigns(
        [campaign(**{k: v for k, v in kwargs.items() if k in {'cid', 'name'}})],
        [ad(**{k: v for k, v in kwargs.items() if k in {'cid', 'page_id', 'url_tags'}})],
        [sb_row(leads=leads, utm=kwargs.get('sb_utm', 'pg_5083'), page_id=kwargs.get('sb_page_id', '123'))],
        5000,
        dt.date(2026, 8, 29),
        run_at=dt.datetime(2026, 8, 29, 13, 0, tzinfo=mod.NY),
        freshness_max_age_hours=2,
        freshness_fields=('UPDATED_AT',),
    )


class EggbevPageLeadGuardrailTests(unittest.TestCase):
    def test_utm_normalization_and_campaign_parse(self):
        self.assertEqual(mod.normalize_utm('PG-05083'), 'pg_05083')
        self.assertEqual(mod.utm_from_campaign_name('X - (pg_5083) C001'), 'pg_5083')
        self.assertIsNone(mod.utm_from_campaign_name('X without page'))

    def test_threshold_is_strictly_greater_than_5000(self):
        self.assertFalse(mod.strict_over(5000, 5000))
        self.assertTrue(mod.strict_over(5001, 5000))
        self.assertFalse(mod.strict_over(None, 5000))

    def test_eligible_only_after_exact_utm_and_page_reconciliation(self):
        result = evaluate(leads=5001)
        self.assertEqual(len(result['eligible_groups']), 1)
        self.assertEqual(result['eligible_groups'][0]['utm_campaign'], 'pg_5083')
        self.assertEqual(len(result['eligible_groups'][0]['campaigns']), 1)
        self.assertEqual(result['issues'], [])

    def test_exactly_5000_is_safe_and_does_not_pause(self):
        result = evaluate(leads=5000)
        self.assertEqual(result['eligible_groups'], [])
        self.assertEqual(result['safe'][0]['reason'], 'leads_not_strictly_over_limit')

    def test_page_id_mismatch_fails_closed(self):
        result = evaluate(leads=6000, sb_page_id='999')
        self.assertEqual(result['eligible_groups'], [])
        self.assertEqual(result['issues'][0]['issue'], 'meta_and_smart_bidding_page_id_mismatch')

    def test_utm_mismatch_between_name_and_creative_fails_closed(self):
        result = evaluate(leads=6000, url_tags='utm_campaign=pg_9999')
        self.assertEqual(result['eligible_groups'], [])
        self.assertIn('campaign_name_and_creative_utm_mismatch', result['issues'][0]['issues'])

    def test_duplicate_smart_bidding_utm_fails_closed(self):
        result = mod.evaluate_campaigns(
            [campaign()], [ad()], [sb_row(leads=6000), sb_row(leads=6001)],
            5000, dt.date(2026, 8, 29),
        )
        self.assertEqual(result['eligible_groups'], [])
        self.assertEqual(result['issues'][0]['issue'], 'duplicate_smart_bidding_utm')

    def test_campaign_without_effectively_active_ad_is_not_actionable(self):
        result = mod.evaluate_campaigns(
            [campaign()], [], [sb_row(leads=6000)], 5000, dt.date(2026, 8, 29)
        )
        self.assertEqual(result['eligible_groups'], [])
        self.assertEqual(result['safe'][0]['reason'], 'no_effectively_active_ads')

    def test_restriction_state_uses_new_york_current_date_boundary(self):
        self.assertTrue(mod.active_restriction({'RESTRICTED_UNTIL': '2026-08-29'}, dt.date(2026, 8, 29))['active'])
        self.assertFalse(mod.active_restriction({'RESTRICTED_UNTIL': '2026-08-28'}, dt.date(2026, 8, 29))['active'])
        self.assertFalse(mod.active_restriction({'RESTRICTED_UNTIL': None}, dt.date(2026, 8, 29))['active'])

    def test_alert_reports_confirmed_readback_and_no_auto_reactivation(self):
        group = evaluate(leads=6000)['eligible_groups'][0]
        actions = [{'campaign_id': 'c1', 'campaign_name': campaign()['name'], 'ok': True}]
        message = mod.build_alert(
            group,
            actions,
            {'c1': {'spend': 12.34, 'purchase_roas': 0.42, 'messaging_results': 5, 'cpm': 10, 'ctr': 1.5}},
            dt.datetime(2026, 8, 29, 14, 30, tzinfo=mod.NY),
            5000,
        )
        self.assertIn('1/1 campanhas confirmadas como PAUSED', message)
        self.assertIn('Reativação automática: não', message)
        self.assertIn('pg_5083', message)

    def test_proximity_buckets_use_requested_4k_yellow_boundary(self):
        self.assertEqual(mod.lead_proximity(3999, 5000)['emoji'], '🟢')
        self.assertEqual(mod.lead_proximity(4000, 5000)['emoji'], '🟡')
        self.assertEqual(mod.lead_proximity(4499, 5000)['emoji'], '🟡')
        self.assertEqual(mod.lead_proximity(4500, 5000)['emoji'], '🟠')
        self.assertEqual(mod.lead_proximity(5000, 5000)['emoji'], '🟠')
        self.assertEqual(mod.lead_proximity(5001, 5000)['emoji'], '🔴')

    def test_status_report_shows_active_pages_and_non_statistical_proximity(self):
        evaluated = evaluate(leads=4000)
        message = mod.build_status_report(
            evaluated,
            dt.datetime(2026, 8, 29, 8, 0, tzinfo=mod.NY),
            5000,
            'Eggbev-US-CC-EN-01-G006',
        )
        self.assertIn('🟡', message)
        self.assertIn('4.000', message)
        self.assertIn('80%', message)
        self.assertIn('não previsão estatística', message)
        self.assertIn('pg_5083', message)

    def test_pause_uses_one_post_and_requires_get_readback(self):
        class FakeCommon:
            def __init__(self):
                self.gets = 0
                self.posts = 0

            def graph_get(self, path, token, params):
                self.gets += 1
                if self.gets == 1:
                    return 200, {'status': 'ACTIVE', 'effective_status': 'ACTIVE'}, {}
                return 200, {'status': 'PAUSED', 'effective_status': 'PAUSED'}, {}

            def graph_post_once(self, path, token, params):
                self.posts += 1
                return 200, {'success': True}, {}

        fake = FakeCommon()
        result = mod.reconcile_pause(fake, 'secret-never-printed', {'campaign_id': 'c1', 'campaign_name': 'C1'})
        self.assertTrue(result['ok'])
        self.assertEqual(result['stage'], 'paused_confirmed')
        self.assertEqual(fake.posts, 1)
        self.assertEqual(fake.gets, 2)

    def test_failed_post_is_reconciled_by_get_without_blind_retry(self):
        class FakeCommon:
            def __init__(self):
                self.gets = 0
                self.posts = 0

            def graph_get(self, path, token, params):
                self.gets += 1
                if self.gets == 1:
                    return 200, {'status': 'ACTIVE', 'effective_status': 'ACTIVE'}, {}
                return 200, {'status': 'PAUSED', 'effective_status': 'PAUSED'}, {}

            def graph_post_once(self, path, token, params):
                self.posts += 1
                return 500, {'error': {'message': 'transient'}}, {}

        fake = FakeCommon()
        result = mod.reconcile_pause(fake, 'secret-never-printed', {'campaign_id': 'c1', 'campaign_name': 'C1'})
        self.assertTrue(result['ok'])
        self.assertEqual(fake.posts, 1)
        self.assertEqual(fake.gets, 2)

    def test_missing_smart_bidding_freshness_fails_closed(self):
        result = mod.evaluate_campaigns(
            [campaign()], [ad()], [sb_row(leads=6000, updated_at=None)],
            5000, dt.date(2026, 8, 29),
            run_at=dt.datetime(2026, 8, 29, 13, 0, tzinfo=mod.NY),
            freshness_max_age_hours=2,
            freshness_fields=('UPDATED_AT',),
        )
        self.assertEqual(result['eligible_groups'], [])
        self.assertEqual(result['issues'][0]['issue'], 'smart_bidding_freshness_unverifiable')

    def test_stale_smart_bidding_row_fails_closed(self):
        result = mod.evaluate_campaigns(
            [campaign()], [ad()], [sb_row(leads=6000, updated_at='2026-08-29T09:00:00-04:00')],
            5000, dt.date(2026, 8, 29),
            run_at=dt.datetime(2026, 8, 29, 13, 0, tzinfo=mod.NY),
            freshness_max_age_hours=2,
            freshness_fields=('UPDATED_AT',),
        )
        self.assertEqual(result['eligible_groups'], [])
        self.assertEqual(result['issues'][0]['issue'], 'smart_bidding_source_stale')

    def test_scheduled_mode_only_allows_approved_times(self):
        approved = ('08:00', '20:00')
        self.assertTrue(mod.scheduled_window_allowed(dt.datetime(2026, 8, 29, 8, 0, tzinfo=mod.NY), approved))
        self.assertTrue(mod.scheduled_window_allowed(dt.datetime(2026, 8, 29, 8, 14, tzinfo=mod.NY), approved))
        self.assertTrue(mod.scheduled_window_allowed(dt.datetime(2026, 8, 29, 20, 0, tzinfo=mod.NY), approved))
        self.assertTrue(mod.scheduled_window_allowed(dt.datetime(2026, 8, 29, 8, 29, tzinfo=mod.NY), approved))
        self.assertFalse(mod.scheduled_window_allowed(dt.datetime(2026, 8, 29, 8, 30, tzinfo=mod.NY), approved))
        self.assertFalse(mod.scheduled_window_allowed(dt.datetime(2026, 8, 29, 19, 59, tzinfo=mod.NY), approved))

    def test_scheduled_dry_run_treats_only_unverifiable_freshness_as_expected_block(self):
        freshness = [{'issue': 'smart_bidding_freshness_unverifiable'}]
        mixed = freshness + [{'issue': 'page_id_mismatch'}]
        self.assertTrue(mod.expected_scheduled_freshness_block(freshness, scheduled=True, apply=False))
        self.assertFalse(mod.expected_scheduled_freshness_block(freshness, scheduled=False, apply=False))
        self.assertFalse(mod.expected_scheduled_freshness_block(freshness, scheduled=True, apply=True))
        self.assertFalse(mod.expected_scheduled_freshness_block(mixed, scheduled=True, apply=False))

    def test_auto_reactivate_is_read_from_scope(self):
        self.assertFalse(mod.policy_auto_reactivate({'scope': {'auto_reactivate': False}}))

    def test_mapping_issue_report_is_visible_and_delivery_failure_is_fatal(self):
        evaluated = mod.evaluate_campaigns(
            [campaign()], [ad()], [sb_row(leads=6000, updated_at=None)],
            5000, dt.date(2026, 8, 29),
            run_at=dt.datetime(2026, 8, 29, 13, 0, tzinfo=mod.NY),
            freshness_max_age_hours=2,
            freshness_fields=('UPDATED_AT',),
        )
        message = mod.build_issue_alert(
            evaluated['issues'],
            dt.datetime(2026, 8, 29, 13, 0, tzinfo=mod.NY),
            'Eggbev-US-CC-EN-01-G006',
        )
        self.assertIn('FRESHNESS', message)
        self.assertIn('smart_bidding_freshness_unverifiable', message)
        with self.assertRaises(mod.GuardrailError):
            mod.require_delivery({'ok': False}, 'mapping_issue_alert')


if __name__ == '__main__':
    unittest.main(verbosity=2)
