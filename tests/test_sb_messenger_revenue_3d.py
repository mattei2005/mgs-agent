"""Revenue window regression; investment's native seven-day fetch stays intact."""
import importlib.util
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

spec = importlib.util.spec_from_file_location('revenue_3d', Path(__file__).resolve().parents[1] / 'scripts/sync-sb-messenger-revenue-sheet.py')
if spec is None or spec.loader is None:
    raise RuntimeError('Revenue helper unavailable')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class RevenueWindowTests(unittest.TestCase):
    def fixture(self):
        end = date(2026, 11, 14)
        rows = [{'DATE': (end - timedelta(days=offset)).isoformat(),
                 'PROFILE_NAME': f'Profile {profile:03d}',
                 'REVENUE': '1.25' if offset < 3 else '1000.00',
                 'INVESTIMENT': '2.00'}
                for offset in range(7) for profile in range(200)]
        payload = {'initialDate': '2026-11-08T05:00:00Z',
                   'finalDate': '2026-11-15T04:30:00Z',
                   'publishers': list(range(51))}
        return rows, payload

    def test_all_seven_dates_including_partial_today(self):
        rows, payload = self.fixture()
        aggregate, _, blank, summary = helper.aggregate_report(rows, payload)
        self.assertEqual(aggregate['profile 000'], Decimal('4003.75'))
        self.assertEqual(blank, Decimal('0.00'))
        self.assertEqual(summary['dashboard_total'], '800750.00')
        self.assertEqual(summary['period_start'], '2026-11-08')
        self.assertEqual(summary['period_end'], '2026-11-14')
        self.assertEqual(summary['days'], 7)
        self.assertTrue(summary['includes_current_day'])
        self.assertTrue(summary['current_day_partial'])
        self.assertEqual(summary['source_rows'], 1400)
        self.assertEqual(summary['api_rows'], 1400)

    def test_missing_date_blocks_instead_of_summing_another_date(self):
        rows, payload = self.fixture()
        rows = [row for row in rows if row['DATE'] != '2026-11-13']
        with self.assertRaisesRegex(RuntimeError, 'seven-day dates missing'):
            helper.aggregate_report(rows, payload)

    def test_old_header_is_rejected_and_new_header_is_exact(self):
        self.assertTrue(helper.headers_are_expected(['Rem Acum', 'User', 'RECEITA 7 DIAS', 'Segurador']))
        self.assertFalse(helper.headers_are_expected(['Rem Acum', 'User', 'RECEITA 3 DIAS', 'Segurador']))

    def test_future_or_old_rows_cannot_contaminate_revenue(self):
        rows, payload = self.fixture()
        rows.append({'DATE': '2026-11-15', 'PROFILE_NAME': 'Profile 000', 'REVENUE': '999999'})
        aggregate, _, _, _ = helper.aggregate_report(rows, payload)
        self.assertEqual(aggregate['profile 000'], Decimal('4003.75'))

    def test_investment_consumer_still_has_prior_three_closed_dates(self):
        rows, payload = self.fixture()
        summary = helper.aggregate_invest_3d(rows, payload)
        self.assertEqual(summary['period_start'], '2026-11-11')
        self.assertEqual(summary['period_end'], '2026-11-13')
        self.assertEqual(summary['by_profile']['profile 000'], '6.00')
        self.assertEqual(summary['by_profile_today']['profile 000'], '2.00')
        self.assertFalse(summary['includes_current_day'])


if __name__ == '__main__':
    unittest.main()
