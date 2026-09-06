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

    def test_current_rem_acum_header_is_shared_by_both_monitors(self):
        headers = ['Rem Acum', 'User', 'Segurador', 'NO APP', 'USUARIO']
        self.assertEqual(self.generic.resolve_removed_header(headers), 'Rem Acum')
        self.assertEqual(self.b013.resolve_removed_header(headers), 'Rem Acum')

    def test_revenue_sheet_accepts_current_and_legacy_removed_headers(self):
        trailing = ['User', 'RECEITA 7 DIAS', 'Segurador']
        self.assertTrue(self.helper.headers_are_expected(['Rem Acum', *trailing, 'PG']))
        self.assertTrue(self.helper.headers_are_expected(['Removidos acumulado', *trailing]))
        self.assertFalse(self.helper.headers_are_expected(['zzzaa', *trailing]))
        self.assertFalse(self.helper.headers_are_expected(['Rem Acum', 'Segurador', 'RECEITA 7 DIAS', 'User']))

    def test_removed_header_aliases_and_column_guard_are_fail_closed(self):
        for module in (self.generic, self.b013):
            for marker in ('Removidos acumulado', 'zzzaa'):
                with self.subTest(module=module, marker=marker):
                    self.assertEqual(module.resolve_removed_header([marker, 'User']), marker)
            with self.assertRaisesRegex(RuntimeError, 'ambiguous/missing'):
                module.resolve_removed_header(['User', 'Segurador'])
            with self.assertRaisesRegex(RuntimeError, 'moved away'):
                module.resolve_removed_header(['User', 'Rem Acum'])

    def test_helper_separates_today_from_three_closed_dates(self):
        rows, payload = self.fixture()
        result = self.helper.aggregate_invest_3d(rows, payload)
        self.assertEqual(result['status'], 'INVEST_3D_OK')
        self.assertEqual(result['days'], 3)
        self.assertEqual(result['period_start'], '2026-09-01')
        self.assertEqual(result['period_end'], '2026-09-03')
        self.assertEqual(result['current_date'], '2026-09-04')
        self.assertFalse(result['includes_current_day'])
        self.assertTrue(result['current_day_partial'])
        self.assertEqual(result['by_profile']['profile 000'], '3.00')
        self.assertEqual(result['by_profile_today']['profile 000'], '1.00')
        self.assertEqual(result['total'], '600.00')
        self.assertEqual(result['today_total'], '200.00')
        self.assertEqual(result['source_rows'], 600)
        self.assertEqual(result['source_rows_today'], 200)

    def test_helper_fails_closed_when_one_of_three_dates_is_missing(self):
        rows, payload = self.fixture()
        rows = [row for row in rows if row['DATE'] != '2026-09-03']
        with self.assertRaisesRegex(RuntimeError, 'dates missing'):
            self.helper.aggregate_invest_3d(rows, payload)

    def test_helper_fails_closed_when_current_date_is_missing(self):
        rows, payload = self.fixture()
        rows = [row for row in rows if row['DATE'] != '2026-09-04']
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
            'by_profile_today': {
                'jose da silva': '45.60',
                'alpha': '1.00',
                'beta': '2.00',
            },
        }
        module.format_invest_3d.__globals__['INVEST_3D_DATA'] = payload
        self.assertEqual(module.format_invest_3d('José da Silva'), 'R$ 1.234,50')
        self.assertEqual(module.format_invest_3d('Alpha / Beta'), 'R$ 30,00')
        self.assertEqual(module.format_invest_3d('Sem Match'), 'n/d')
        self.assertEqual(module.format_invest_today('José da Silva'), 'R$ 45,60')
        self.assertEqual(module.format_invest_today('Alpha / Beta'), 'R$ 3,00')
        self.assertEqual(module.format_invest_today('Sem Match'), 'n/d')

    def test_generic_formatter_and_table(self):
        self.exercise_formatter(self.generic)
        self.generic.sheet_user = lambda name, app_key=None: {
            'profile_id': 'profile-1',
            'bot_email': 'bot@example.com',
            'pages': '4',
            'app_key': app_key,
        }
        rendered = self.generic.fmt_roles([{'id': '1', 'name': 'José da Silva'}], app_key='B001-5')
        self.assertIn('INVEST HOJE', rendered)
        self.assertIn('INVEST 3D', rendered)
        self.assertIn('R$ 45,60', rendered)
        self.assertIn('R$ 1.234,50', rendered)
        self.assertNotIn('7 DIAS', rendered)

    def test_profile_replacement_preserves_old_investment_under_current_profile(self):
        note = 'Perfil Antigo: Fernanda Peixoto - 61577752899332'
        for module in (self.generic, self.b013):
            with self.subTest(module=module):
                self.assertEqual(module.parse_old_profile_references(note), [{
                    'name': 'Fernanda Peixoto',
                    'profile_id': '61577752899332',
                }])

        generic_globals = self.generic.load_sheet_users.__globals__
        saved = {
            key: generic_globals.get(key)
            for key in (
                'SHEET_ROWS', 'SHEET_USERS', 'SHEET_APP_BY_NAME', 'SHEET_APP_BY_PROFILE_ID',
                'SHEET_OLD_PROFILE_NAMES_BY_APP', 'SHEET_OLD_PROFILE_IDS_BY_APP',
                'SHEET_INVEST_PROFILE_NAMES_BY_APP', 'load_sheet_rows', 'INVEST_3D_DATA',
            )
        }
        try:
            generic_globals['SHEET_ROWS'] = None
            generic_globals['SHEET_USERS'] = None
            generic_globals['SHEET_APP_BY_NAME'] = None
            generic_globals['SHEET_APP_BY_PROFILE_ID'] = None
            generic_globals['SHEET_OLD_PROFILE_NAMES_BY_APP'] = None
            generic_globals['SHEET_OLD_PROFILE_IDS_BY_APP'] = None
            generic_globals['SHEET_INVEST_PROFILE_NAMES_BY_APP'] = None
            generic_globals['load_sheet_rows'] = lambda: [{
                'User': 'disparosopenzedes@gmail.com',
                'Segurador': 'Paula Oliveira',
                'USUARIO': 'PaulaOliveira1234565',
                'NO APP': 'B007-3',
                'PG': '12',
                'OBS': note,
            }]
            self.generic.load_sheet_users()
            self.assertEqual(
                generic_globals['SHEET_OLD_PROFILE_NAMES_BY_APP']['B007-3'],
                {'fernanda peixoto'},
            )
            self.assertEqual(
                generic_globals['SHEET_OLD_PROFILE_IDS_BY_APP']['B007-3'],
                {'61577752899332'},
            )
            self.assertEqual(
                generic_globals['SHEET_INVEST_PROFILE_NAMES_BY_APP'][('B007-3', 'paula oliveira')],
                ['Paula Oliveira', 'Fernanda Peixoto'],
            )
            generic_globals['INVEST_3D_DATA'] = {
                'status': 'INVEST_3D_OK',
                'days': 3,
                'by_profile_today': {'fernanda peixoto': '342.93'},
                'by_profile': {'fernanda peixoto': '3472.98'},
            }
            rendered = self.generic.fmt_roles(
                [{'id': '122137905093210709', 'name': 'Paula Oliveira'}],
                app_key='B007-3',
            )
            self.assertIn('disparosopenzedes', rendered)
            self.assertIn('Paula Oliveira', rendered)
            self.assertIn('12', rendered)
            self.assertIn('R$ 342,93', rendered)
            self.assertIn('R$ 3.472,98', rendered)
            self.assertNotIn('n/d', rendered)
        finally:
            generic_globals.update(saved)

        b013_globals = self.b013.format_invest_today.__globals__
        previous_payload = b013_globals.get('INVEST_3D_DATA')
        try:
            b013_globals['INVEST_3D_DATA'] = {
                'status': 'INVEST_3D_OK',
                'days': 3,
                'by_profile_today': {'fernanda peixoto': '342.93'},
                'by_profile': {'fernanda peixoto': '3472.98'},
            }
            row = {
                'linked': True,
                'user': 'disparosopenzedes@gmail.com',
                'segurador': 'Paula Oliveira',
                'profile_id': 'PaulaOliveira1234565',
                'pages': '12',
                'invest_profile_names': ['Paula Oliveira', 'Fernanda Peixoto'],
            }
            rendered = self.b013.fmt_status_rows([row])
            self.assertIn('R$ 342,93', rendered)
            self.assertIn('R$ 3.472,98', rendered)
            self.assertNotIn('n/d', rendered)
            self.assertIn("quote_sheet_range(title, 'A:P')", B013.read_text(encoding='utf-8'))
        finally:
            b013_globals['INVEST_3D_DATA'] = previous_payload

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
            self.assertIn('INVEST HOJE', rendered)
            self.assertIn('INVEST 3D', rendered)
            self.assertIn('R$ 45,60', rendered)
            self.assertIn('R$ 1.234,50', rendered)
            self.assertNotIn('7 DIAS', rendered)


if __name__ == '__main__':
    unittest.main()
