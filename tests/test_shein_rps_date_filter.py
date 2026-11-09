"""Regression for local display date versus initial UTC query at 23:31 ET."""
import asyncio
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock

SPEC = importlib.util.spec_from_file_location(
    'shein_rps_ui_date', Path('/root/.hermes/profiles/ares/scripts/shein-daily-rps-ui.py'))
assert SPEC is not None and SPEC.loader is not None
ui = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ui)
HEADERS = ['DATE', 'DOMAIN', 'ACCOUNT_ID', 'CAMPAIGN_ID', 'CAMPAIGN NAME', 'RPS']


class DateFilterTests(unittest.TestCase):
    def page(self, value):
        page = MagicMock()
        node = MagicMock()
        node.first = node
        node.filter.return_value = node
        node.click = AsyncMock()
        node.input_value = AsyncMock(return_value=value)
        page.locator.return_value = node
        page.get_by_role.return_value = node
        page.wait_for_timeout = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        return page, node

    def test_matching_display_still_applies_today_and_update(self):
        page, node = self.page('08/11/2026 - 08/11/2026')
        result = asyncio.run(ui.apply_report_date(page, '2026-11-08', 'Today'))
        self.assertEqual(result, '08/11/2026 - 08/11/2026')
        page.get_by_role.assert_called_once_with('button', name='Today', exact=True)
        self.assertEqual(node.click.await_count, 3)
        page.wait_for_load_state.assert_awaited_once()

    def test_yesterday_keeps_explicit_preset(self):
        page, _ = self.page('08/11/2026 - 08/11/2026')
        asyncio.run(ui.apply_report_date(page, '2026-11-08', 'Yesterday'))
        page.get_by_role.assert_called_once_with('button', name='Yesterday', exact=False)

    def test_wrong_control_date_fails_closed(self):
        page, _ = self.page('09/11/2026 - 09/11/2026')
        with self.assertRaisesRegex(AssertionError, 'did not converge'):
            asyncio.run(ui.apply_report_date(page, '2026-11-08', 'Today'))

    def test_wrong_date_outside_scope_cannot_be_silently_ignored(self):
        raw = [['09/11/2026', 'other', 'other', 'c', 'name', '$1']]
        with self.assertRaisesRegex(AssertionError, 'another report date'):
            ui.matching_rows(raw, HEADERS, {'123'}, {'mavroa'}, '2026-11-08', set())

    def test_correct_date_scope_and_account_prefix(self):
        raw = [['08/11/2026', 'mavroa', 'act_123', 'c', 'name', '$1'],
               ['08/11/2026', 'other', '456', 'd', 'name', '$2']]
        seen = set()
        rows = ui.matching_rows(raw, HEADERS, {'123'}, {'mavroa'}, '2026-11-08', seen)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['RPS'], '$1')
        self.assertEqual(seen, {('123', 'c', '2026-11-08')})

    def test_duplicates_across_pages_fail_closed(self):
        raw = [['08/11/2026', 'mavroa', '123', 'c', 'name', '$1']]
        seen = set()
        ui.matching_rows(raw, HEADERS, {'123'}, {'mavroa'}, '2026-11-08', seen)
        with self.assertRaises(AssertionError):
            ui.matching_rows(raw, HEADERS, {'123'}, {'mavroa'}, '2026-11-08', seen)


if __name__ == '__main__':
    unittest.main()
