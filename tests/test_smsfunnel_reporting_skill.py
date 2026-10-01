import importlib.util
from decimal import Decimal
from pathlib import Path

SCRIPT = Path('/root/.hermes/profiles/ares/skills/growth/sms-funnel-reporting/scripts/report.py')
spec = importlib.util.spec_from_file_location('smsfunnel_reporting', SCRIPT)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_month_bounds_include_next_month_boundary():
    assert module.month_bounds('2026-08') == ('2026-08-01', '2026-08-31', '2026-09-01')
    assert module.month_bounds('2026-12') == ('2026-12-01', '2026-12-31', '2027-01-01')


def test_manager_normalization_ignores_suffix_and_uses_whole_token():
    assert module.manager_from_text('AUTOMACAO G001 DISPARO 1') == 'G001'
    assert module.manager_from_text('url utm_medium=g001-s') == 'G001'
    assert module.manager_from_text('url utm_medium=g006-d') == 'G006'
    assert module.manager_from_text('G0010') is None
    assert module.manager_from_text('sem gestor') is None


def test_medium_shapes_distinguish_plain_suffix_and_missing():
    assert module.medium_shape('g002') == 'plain'
    assert module.medium_shape('g002-s') == 'suffix_s'
    assert module.medium_shape('g002-d') == 'other_suffix'
    assert module.medium_shape('') == 'missing'


def test_brl_uses_decimal_money():
    assert module.brl(4166, Decimal('0.08')) == '333.28'
    assert module.brl(255632, Decimal('0.08')) == '20450.56'
