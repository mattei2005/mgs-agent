from __future__ import annotations

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest

SCRIPT = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py')


def load():
    spec = importlib.util.spec_from_file_location('cpv_daily_estimated_tests', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('current,investment,matched,expected', [
    (True, 10, True, 50),
    (True, 10, False, None),
    (True, 0, True, None),
    (False, 10, True, None),
])
def test_daily_estimate_period_and_missing_data(monkeypatch, tmp_path, current, investment, matched, expected):
    module = load()
    op = tmp_path / 'operation.json'
    op.write_text(json.dumps({'management_scope': {'autonomous_action_scope': {'allowed_campaigns': {}}}}))
    monkeypatch.setattr(module, 'OP_PATH', op)
    target = '2026-10-06' if current else '2026-10-05'
    campaign = {'id': '123', 'name': '07 - 05-10 - Garagem - (b01fb13c07)',
                'configured_status': 'ACTIVE', 'daily_budget': '2500',
                'bid_strategy': 'LOWEST_COST_WITHOUT_CAP', 'start_time': '2026-10-05T00:30:00-0300'}
    monkeypatch.setattr(module, 'fetch_meta', lambda day: {
        'campaigns': [campaign], 'adsets': [], 'insights': [
            {'campaign_id': '123', 'spend': str(investment), 'actions': [], 'purchase_roas': []}
        ]})
    calls = []

    def fake_sb(day, include_estimated, *, include_sms):
        calls.append((day, include_estimated, include_sms))
        return {'rows': [{'CAMPAIGN_ID': '123', 'UTM_ADGROUP': 'b01fb13c07g01',
                          'INVESTIMENT': investment, 'NET_REVENUE': 8,
                          'CDP_IMPRESSIONS': 90, 'GAM_CODE_SERVED_COUNT': 100}],
                'estimated': {'grouped': [{'utm_adgroup': 'b01fb13c07g01', 'estimatedRevenue': 15,
                                          'confidence': 0.9}] if matched else []}}

    monkeypatch.setattr(module, 'fetch_sb', fake_sb)
    monkeypatch.setattr(module, 'hydrate_missing_report_campaigns', lambda campaigns, adsets, ids: (campaigns, adsets, {}))
    text, audit = module.build_daily(target, datetime(2026, 10, 6, 14, 0, tzinfo=module.SP))
    assert calls == [(target, current, False)]
    assert 'ROI est.' in text
    assert audit['campaigns'][0]['estimated_roi'] == expected
    assert audit['campaigns'][0]['health_pct'] == 90
    if investment > 0:
        assert audit['campaigns'][0]['sb_roi'] == pytest.approx(-20)
    chunks = module.split_message(text)
    assert all(len(chunk) <= 2000 for chunk in chunks)
    assert 'estimativa histórica' in text


def test_canonical_column_order_matches_renderer():
    module = load()
    presentation = json.loads(module.OP_PATH.read_text())['reporting_presentation']
    cols = presentation['daily_columns']
    assert cols[cols.index('ROI SB') + 1] == 'ROI est.'
    assert presentation['daily_estimated_roi']['decision_use'].startswith('presentation only')
