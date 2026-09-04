import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

HELPER = Path('/root/mgs-agent/scripts/sync-sb-messenger-revenue-sheet.py')
GENERIC = Path('/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh')
B013 = Path('/root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh')


def load_python(path):
    spec = importlib.util.spec_from_file_location(path.stem.replace('-', '_'), path)
    if not spec or not spec.loader:
        raise RuntimeError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_embedded(path, marker, stop_marker=None):
    text = path.read_text(encoding='utf-8')
    start = text.index(marker)
    end = text.index(stop_marker, start) if stop_marker else text.rindex('\nPY\n')
    namespace = {'__name__': f'{path.stem}_test'}
    exec(compile(text[start:end], str(path), 'exec'), namespace)
    return SimpleNamespace(**namespace)


class MetaAppInvest3DTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = load_python(HELPER)
        cls.generic = load_embedded(GENERIC, 'import importlib.util\n', '\nstate = load_state()')
        cls.b013 = load_embedded(B013, 'import asyncio\n')

    def fixture(self):
        final = date(2026, 9, 4)
        rows = []
        for offset in range(7):
            day = final - timedelta(days=6 - offset)
            for profile in range(200):
                rows.append({
                    'DATE': day.isoformat(),
                    'PROFILE_NAME': f'Profile {profile:03d}',
                    'INVESTIMENT': '1.00',
                })
        payload = {
            'finalDate': '2026-09-04T23:59:59.999Z',
            'initialDate': '2026-08-29T00:00:00.000Z',
            'publishers': [f'p{i}' for i in range(45)],
            'currency': None,
        }
        return rows, payload

    def test_helper_uses_exactly_three_dates(self):
        rows, payload = self.fixture()
        result = self.helper.aggregate_invest_3d(rows, payload)
        self.assertEqual(result['status'], 'INVEST_3D_OK')
        self.assertEqual(result['days'], 3)
        self.assertEqual(result['period_start'], '2026-09-02')
        self.assertEqual(result['period_end'], '2026-09-04')
        self.assertEqual(result['by_profile']['profile 000'], '3.00')
        self.assertEqual(result['total'], '600.00')
        self.assertEqual(result['source_rows'], 600)

    def test_helper_fails_closed_when_one_of_three_dates_is_missing(self):
        rows, payload = self.fixture()
        rows = [row for row in rows if row['DATE'] != '2026-09-03']
        with self.assertRaisesRegex(RuntimeError, 'dates missing'):
            self.helper.aggregate_invest_3d(rows, payload)

    def exercise_formatter(self, module):
        payload = {
            'status': 'INVEST_3D_OK',
            'days': 3,
            'by_profile': {
                'jose da silva': '1234.50',
                'alpha': '10.00',
                'beta': '20.00',
            },
        }
        module.format_invest_3d.__globals__['INVEST_3D_DATA'] = payload
        self.assertEqual(module.format_invest_3d('José da Silva'), '$1.234,50')
        self.assertEqual(module.format_invest_3d('Alpha / Beta'), '$30,00')
        self.assertEqual(module.format_invest_3d('Sem Match'), 'n/d')

    def test_generic_formatter_and_table(self):
        self.exercise_formatter(self.generic)
        self.generic.sheet_user = lambda name, app_key=None: {
            'profile_id': 'profile-1',
            'bot_email': 'bot@example.com',
            'pages': '4',
            'app_key': app_key,
        }
        rendered = self.generic.fmt_roles([{'id': '1', 'name': 'José da Silva'}], app_key='B001-5')
        self.assertIn('INVEST 3D', rendered)
        self.assertIn('$1.234,50', rendered)
        self.assertNotIn('7 DIAS', rendered)

    def test_b013_formatter_and_tables(self):
        self.exercise_formatter(self.b013)
        row = {
            'linked': True,
            'user': 'bot@example.com',
            'segurador': 'José da Silva',
            'profile_id': 'profile-1',
            'pages': '4',
        }
        for rendered in (self.b013.fmt_status_rows([row]), self.b013.fmt_pending_rows([row])):
            self.assertIn('INVEST 3D', rendered)
            self.assertIn('$1.234,50', rendered)
            self.assertNotIn('7 DIAS', rendered)


if __name__ == '__main__':
    unittest.main()
