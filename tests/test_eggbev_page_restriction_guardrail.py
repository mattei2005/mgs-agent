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


restriction = load_module(
    'eggbev_page_restriction_guardrail_test',
    BASE / 'scripts/ares-eggbev-page-restriction-guardrail.py',
)
lead = load_module(
    'eggbev_page_lead_guardrail_layout_test',
    BASE / 'scripts/ares-eggbev-page-lead-guardrail.py',
)


class EggbevPageRestrictionGuardrailTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 8, 31, 18, 0, tzinfo=NY)
        self.row = {
            'bot_user': 'disparoseggbev@gmail.com',
            'last_seen': '2026-08-31T17:59:00-04:00',
            'page_name': 'Tina Walter',
            'restricted_until': '2026-09-20',
        }
        self.transition = {
            '_meta': {},
            'active': {
                'bot-page:disparoseggbev@gmail.com|5024': {
                    'bot_user': 'disparoseggbev@gmail.com',
                    'page_id': '5024',
                    'page_name': 'Tina Walter',
                    'fb_page_id': '123456789',
                    'restricted_until': '2026-09-20',
                    'sites': 'eggbev',
                    'utm_campaign': 'pg_5024',
                }
            },
        }
        self.dtr = {'alerted_restricted_pages': {'user_page|disparoseggbev@gmail.com|5024': self.row}}

    def test_collects_only_new_dtr_confirmed_eggbev_event(self):
        events = restriction.collect_confirmed_events(self.dtr, self.transition, {'initialized_at_et': 'x'}, self.now)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['utm_campaign'], 'pg_5024')
        self.assertEqual(events[0]['fb_page_id'], '123456789')
        self.assertEqual(events[0]['source'], 'DTR #2022 + Smart Bidding readback')

    def test_cursor_deduplicates_same_event(self):
        eid = restriction.event_id('user_page|disparoseggbev@gmail.com|5024', self.row)
        state = {
            'initialized_at_et': '2026-08-31T17:00:00-04:00',
            'cursor_last_seen_at': '2026-08-31T17:59:00-04:00',
            'cursor_event_ids': [eid],
        }
        self.assertEqual(restriction.collect_confirmed_events(self.dtr, self.transition, state, self.now), [])

    def test_sb_only_or_expired_event_never_becomes_action_event(self):
        no_dtr = {'alerted_restricted_pages': {}}
        self.assertEqual(restriction.collect_confirmed_events(no_dtr, self.transition, {}, self.now), [])
        expired = dict(self.transition)
        expired['active'] = {k: {**v, 'restricted_until': '2026-08-30'} for k, v in self.transition['active'].items()}
        self.assertEqual(restriction.collect_confirmed_events(self.dtr, expired, {}, self.now), [])

    def test_exact_meta_match_requires_utm_and_page(self):
        campaign = {'id': 'c1', 'name': 'Eggbev (pg_5024)', 'status': 'ACTIVE', 'effective_status': 'ACTIVE'}
        ad = {
            'campaign': {'id': 'c1'},
            'creative': {
                'url_tags': 'utm_campaign=pg_5024',
                'object_story_spec': {'page_id': '123456789'},
            },
        }
        event = {'utm_campaign': 'pg_5024', 'fb_page_id': '123456789'}
        matched = restriction.exact_meta_matches(event, [campaign], [ad], lead)
        self.assertEqual(len(matched['exact']), 1)
        event['fb_page_id'] = 'other'
        matched = restriction.exact_meta_matches(event, [campaign], [ad], lead)
        self.assertEqual(matched['exact'], [])
        self.assertEqual(len(matched['partial']), 1)

    def test_short_alert_layouts_are_four_or_five_lines(self):
        event = {
            'page_name': 'Tina Walter',
            'utm_campaign': 'pg_5024',
            'restricted_until': '2026-09-20',
        }
        action = [{'ok': True, 'campaign_id': 'c1'}]
        alert = restriction.build_action_alert(event, action, self.now)
        self.assertLessEqual(len(alert.splitlines()), 4)
        self.assertIn('PÁGINA RESTRITA', alert)
        self.assertIn('pausadas: **1**', alert)
        self.assertNotIn('```', alert)
        test_alert = restriction.build_test_alert(self.now)
        self.assertEqual(len(test_alert.splitlines()), 4)
        self.assertIn('ação Meta: **nenhuma**', test_alert)

    def test_lead_alert_is_short_and_direct(self):
        group = {'page_name': 'Tina Walter', 'utm_campaign': 'pg_5024', 'leads': 5001}
        actions = [{'ok': True, 'campaign_id': 'c1'}]
        alert = lead.build_alert(group, actions, {}, self.now, 5000)
        self.assertEqual(len(alert.splitlines()), 4)
        self.assertIn('LIMITE DE LEADS', alert)
        self.assertIn('pausadas: **1**', alert)
        issue = lead.build_issue_alert([{'issue': 'stale'}], self.now, 'Eggbev-US-CC-EN-01-G006')
        self.assertLessEqual(len(issue.splitlines()), 5)
        self.assertNotIn('```', issue)


if __name__ == '__main__':
    unittest.main()
