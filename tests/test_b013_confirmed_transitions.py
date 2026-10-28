"""Regression: transport recovery is not an app membership addition/removal."""
import asyncio
import copy
import os
from pathlib import Path
from typing import Any
import unittest

SCRIPT = Path(os.environ.get('B013_TEST_SCRIPT', '/root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh'))


def load_namespace():
    text = SCRIPT.read_text()
    body = text.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    ns: dict[str, Any] = {'__name__': 'b013_transition_regression'}
    exec(compile(body, str(SCRIPT), 'exec'), ns)
    return ns


class FakeBrowser:
    async def close(self):
        pass


class FakePlaywright:
    def __init__(self):
        self.chromium = self

    async def launch(self, **kwargs):
        return FakeBrowser()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class ConfirmedTransitionsTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_namespace()
        self.messages = []
        self.persisted = None
        self.ns.update(
            load_config=lambda: {'app_name': 'B013-7', 'app_id': 'test-app', 'config_item_title': 'test', 'alert_channel_id': '1522830283240505385', 'profile_name': 'Profile', 'backup_profile_name': 'Backup'},
            sheet_rows=lambda _: [{'user': 'bot@example.com', 'segurador': 'Profile'}],
            map_dtr_items=lambda _: {'bot@example.com': 'test-item'},
            async_playwright=FakePlaywright,
            sync_sheet_x=lambda *_: {'enabled': True, 'updated': False},
            post_discord=lambda *args, **kwargs: self.messages.append(args),
            post_code_blocks=lambda *args, **kwargs: None,
            fmt_status_rows=lambda *_: 'isolated fixture',
            automatic_movement_sections=lambda *_: ['isolated fixture'],
            save_state=lambda state: setattr(self, 'persisted', copy.deepcopy(state)),
            DRY_RUN=False,
            FORCE_LIVE_ALERT=False,
        )

    def row(self, verdict='linked', status=None):
        return {'user': 'bot@example.com', 'segurador': 'Profile', 'verdict': verdict,
                'linked': verdict == 'linked',
                'link_status': status or ('linked' if verdict == 'linked' else 'not_linked_or_invalid'),
                'checked_at': '2026-10-28T12:00:00-04:00', 'debug_is_valid': verdict == 'linked'}

    def cycle(self, previous, current):
        state = {'initialized': True, 'accounts': {}, 'alerts': {}}
        if previous is not None:
            state['accounts']['bot@example.com|profile'] = copy.deepcopy(previous)
        self.ns['load_state'] = lambda: copy.deepcopy(state)
        async def inspect(*_):
            return [copy.deepcopy(current)]
        self.ns['inspect_item'] = inspect
        before = len(self.messages)
        asyncio.run(self.ns['main']())
        assert self.persisted is not None
        return self.persisted['accounts']['bot@example.com|profile'], len(self.messages) - before

    def test_linked_unknown_linked_does_not_emit_added(self):
        uncertain, sent = self.cycle(self.row(), self.row('unknown', 'item_check_failed'))
        self.assertEqual(sent, 0)
        recovered, sent = self.cycle(uncertain, self.row())
        self.assertEqual(sent, 0, 'Transport recovery is not a new app member')

    def test_unlinked_unknown_unlinked_does_not_emit_removed(self):
        uncertain, _ = self.cycle(self.row('unlinked_confirmed'), self.row('unknown', 'item_check_failed'))
        _, sent = self.cycle(uncertain, self.row('unlinked_confirmed'))
        self.assertEqual(sent, 0, 'Previously confirmed absence is not a new removal')

    def test_unknown_keeps_last_confirmed_verdict_without_stale_live_data(self):
        uncertain, _ = self.cycle(self.row(), self.row('unknown', 'item_check_failed'))
        self.assertEqual(uncertain.get('last_confirmed_verdict'), 'linked')
        self.assertEqual(uncertain['verdict'], 'unknown')
        self.assertFalse(uncertain['debug_is_valid'])

    def test_real_removal_and_reconnection_still_alert(self):
        removed, sent = self.cycle(self.row(), self.row('unlinked_confirmed'))
        self.assertEqual(sent, 1)
        uncertain, sent = self.cycle(removed, self.row('unknown', 'item_check_failed'))
        self.assertEqual(sent, 0)
        _, sent = self.cycle(uncertain, self.row())
        self.assertEqual(sent, 1)

    def test_new_sheet_assignment_still_alerts_even_when_unknown(self):
        for current in [self.row(), self.row('unknown', 'item_check_failed')]:
            with self.subTest(verdict=current['verdict']):
                _, sent = self.cycle(None, current)
                self.assertEqual(sent, 1)

    def test_legacy_unknown_recovery_is_silent_without_confirmed_removal(self):
        _, sent = self.cycle(self.row('unknown', 'item_check_failed'), self.row())
        self.assertEqual(sent, 0)

    def test_same_confirmed_unlinked_verdict_different_diagnostic_is_silent(self):
        _, sent = self.cycle(self.row('unlinked_confirmed'), self.row('unlinked_confirmed', 'token_app_mismatch'))
        self.assertEqual(sent, 0)

    def test_target_reassignment_retires_baseline_and_new_assignment_alerts(self):
        accounts = {'bot@example.com|profile': self.row()}
        self.ns['retire_out_of_scope_accounts'](accounts, set())
        self.assertEqual(accounts, {})
        _, sent = self.cycle(None, self.row())
        self.assertEqual(sent, 1)


if __name__ == '__main__':
    unittest.main()
