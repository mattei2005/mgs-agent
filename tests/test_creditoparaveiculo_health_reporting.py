from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

SCRIPT = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py')


def load():
    spec = importlib.util.spec_from_file_location('cpv13_health_tests', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('cdp,gam,expected', [
    (332, 352, 94.31818181818181),
    (100, 100, 100),
    (120, 100, 80),
    (250, 100, 0),
    (0, 0, 0),
    (12, 0, 0),
    (0, 100, 0),
    ('50', '100', 50),
])
def test_health_matches_provider_formula(cdp, gam, expected):
    assert load().sb_health_pct(cdp, gam) == pytest.approx(expected)


@pytest.mark.parametrize('cdp,gam', [(None, 100), (100, None), ('bad', 10), (-1, 10), (10, -1), (float('nan'), 10), (10, float('inf'))])
def test_missing_or_invalid_is_not_fabricated_zero(cdp, gam):
    module = load()
    assert module.sb_health_pct(cdp, gam) is None
    assert module.health_label(None) == 'n/d'


def test_aggregate_counters_not_mean_percentages():
    module = load()
    rows = [
        {'CAMPAIGN_ID': '1', 'CDP_IMPRESSIONS': 100, 'GAM_CODE_SERVED_COUNT': 100},
        {'CAMPAIGN_ID': '1', 'CDP_IMPRESSIONS': 90, 'GAM_CODE_SERVED_COUNT': 900},
    ]
    result = module.aggregate_sb(rows)['1']
    assert result['health_pct'] == 19
    assert result['cdp_impressions'] == 190
    assert result['gam_code_served_count'] == 1000
    assert result['health_source_complete']


def test_partial_source_and_unmatched_campaign_are_unavailable():
    module = load()
    rows = [
        {'CAMPAIGN_ID': '1', 'CDP_IMPRESSIONS': 100, 'GAM_CODE_SERVED_COUNT': 100},
        {'CAMPAIGN_ID': '1', 'CDP_IMPRESSIONS': 10},
    ]
    assert module.aggregate_sb(rows)['1']['health_pct'] is None
    assert module.aggregate_sb([]) == {}


def test_health_in_both_reports_and_not_action_policy():
    module = load()
    for builder in [module.build_daily, module.build_intraday]:
        source = inspect.getsource(builder)
        assert '"Health"' in source
        assert '"health_pct"' in source
        assert 'sb_health_contract()' in source
    assert 'health' not in inspect.getsource(module.recommendation).lower()
    assert module.health_label(94.31818181818181) == '94,32%'
    assert module.sb_health_contract()['source_fields'] == ['CDP_IMPRESSIONS', 'GAM_CODE_SERVED_COUNT']
