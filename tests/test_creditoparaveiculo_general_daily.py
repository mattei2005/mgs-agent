from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

GENERAL = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-general-daily.py')
FIXED = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py')
ACCOUNT05 = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-reports.py')


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_account_daily_reports_exclude_sms_values_and_point_to_general():
    fixed = load(FIXED, 'cpv_fixed_account_sms_policy_test')
    account05 = load(ACCOUNT05, 'cpv05_account_sms_policy_test')
    fixed_source = inspect.getsource(fixed.build_daily)
    account05_source = inspect.getsource(account05.render_daily)
    assert 'fetch_sms_vendor_totals' not in fixed_source
    assert 'fetch_bcb_usd_brl_ptax' not in fixed_source
    assert 'SMS não atribuído por conta — consultar CPV Diário Geral.' in fixed_source
    assert 'SMS não atribuído por conta — consultar CPV Diário Geral.' in account05_source
    assert 'Custo SMS G006' not in fixed_source
    assert 'Receita SMS G006' not in account05_source


def test_general_daily_consolidates_accounts_and_sms_exactly_once(monkeypatch):
    module = load(GENERAL, 'cpv_general_render_test')

    class Fixed:
        @staticmethod
        def money(value):
            return f'${value:.2f}'

        @staticmethod
        def pct(value):
            return 'n/d' if value is None else f'{value:+.1f}%'

        @staticmethod
        def aligned_table(headers, rows):
            return '```text\n' + '|'.join(headers) + '\n' + '\n'.join('|'.join(map(str, row)) for row in rows) + '\n```'

        @staticmethod
        def daily_account_summary_rows(**kwargs):
            return [
                ['x', 'Spend Meta', Fixed.money(kwargs['meta_spend'])],
                ['x', 'Receita aquisição SB', Fixed.money(kwargs['acquisition_revenue'])],
                ['x', 'Custo SMS G006', Fixed.money(kwargs['sms_cost_usd'])],
                ['x', 'Receita SMS G006', Fixed.money(kwargs['sms_revenue'])],
                ['x', 'ROI SMS', Fixed.pct(kwargs['sms_roi'])],
                ['x', 'ROI total com SMS', Fixed.pct(kwargs['total_roi_with_sms'])],
                ['x', 'Lucro líquido USD', Fixed.money(kwargs['net_profit_usd'])],
            ]

    account13 = {
        'account_id': module.ACCOUNT13_ID, 'account_label': 'Conta 13', 'campaigns_considered': 2,
        'meta_spend': 100.0, 'sb_investment': 99.0, 'acquisition_net_revenue': 130.0,
        'acquisition_roi_pct': 30.0, 'meta_sb_spend_diff': 1.0,
    }
    account05 = {
        'account_id': module.ACCOUNT05_ID, 'account_label': 'Conta 05', 'campaigns_considered': 3,
        'meta_spend': 50.0, 'sb_investment': 49.0, 'acquisition_net_revenue': 60.0,
        'acquisition_roi_pct': 20.0, 'meta_sb_spend_diff': 1.0,
    }
    sms = {
        'scope': 'operation-wide', 'net_revenue_usd': 20.0, 'sent_count': 10,
        'cost_brl': 25.0, 'cost_usd': 5.0, 'roi_pct': 300.0,
        'vendor': {'status': 'ok', 'total_sms_sent': 10, 'campaigns': [
            {'experience': 'quiz', 'sms_sent': 8}, {'experience': 'chat', 'sms_sent': 2},
        ]},
        'fx': {'status': 'ok', 'rate_date': '2026-08-29', 'rate_brl_per_usd': 5.0},
    }
    monkeypatch.setattr(module, 'validate_contracts', lambda: ({}, {}))
    monkeypatch.setattr(module, 'runtimes', lambda: (Fixed(), object()))
    monkeypatch.setattr(module, 'collect_account13', lambda fixed, date: (account13, {}))
    monkeypatch.setattr(module, 'collect_account05', lambda account05_runtime, date, now: account05)
    monkeypatch.setattr(module, 'collect_sms', lambda fixed, date, sb: sms)

    now = module.datetime(2026, 8, 30, 20, 0, tzinfo=module.SP)
    text, payload = module.render('2026-08-30', now)
    assert payload['totals']['meta_spend'] == 150.0
    assert payload['totals']['acquisition_net_revenue'] == 190.0
    assert payload['totals']['sms_net_revenue'] == 20.0
    assert round(payload['totals']['total_roi_with_sms_pct'], 6) == round((205.0 - 150.0) * 100 / 150.0, 6)
    assert payload['totals']['net_profit_usd'] == 55.0
    assert text.count('SMS G006 contabilizado uma vez') == 1
    assert 'O SMS não é atribuído individualmente às contas 05 ou 13' in text


def test_account05_activity_monitor_contract_is_alert_only():
    module = load(GENERAL, 'cpv_general_contract_test')
    _, op05 = module.validate_contracts()
    monitor = op05['account_activity_monitor']
    assert monitor['enabled'] is True
    assert monitor['mode'] == 'account_wide_external_change_alert'
    assert monitor['graph_version'] == 'v26.0'
    assert monitor['schedule'] == 'every 5 minutes'
    assert monitor['destination_thread_id'] == '1542892943352799242'
    assert 'never auto-correct' in monitor['alert_policy']
