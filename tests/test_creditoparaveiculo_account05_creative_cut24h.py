from __future__ import annotations

import importlib.util
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RUNNER = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-creative-cut24h.py')
WRAPPER = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-creative-cut24h.sh')
OPERATION = Path('/root/mgs-agent/data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR-05-CREATIVE-CUT-24H.json')


def load():
    spec = importlib.util.spec_from_file_location('cpv05_cut_runner_test', RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strategy():
    return {
        'stage_a_concentration': {
            'dominant_spend_share_gte_pct': 80.0,
            'each_other_ad_spend_share_lte_pct': 10.0,
        },
        'stage_b_concentration': {
            'dominant_spend_share_gte_pct': 90.0,
            'other_ad_spend_share_lte_pct': 10.0,
        },
    }


def test_stage_a_exact_80_10_10_pauses_only_dominant_ad():
    m = load()
    result = m.evaluate_decision('THREE_ADS_ACTIVE', -12.5, {'a': 80, 'b': 10, 'c': 10}, ['a', 'b', 'c'], strategy())
    assert result['action'] == 'PAUSE_AD'
    assert result['dominant_ad_id'] == 'a'


def test_stage_a_without_concentration_requires_manual_review():
    m = load()
    result = m.evaluate_decision('THREE_ADS_ACTIVE', -12.5, {'a': 79, 'b': 11, 'c': 10}, ['a', 'b', 'c'], strategy())
    assert result['action'] == 'MANUAL_REVIEW'


def test_stage_b_exact_90_10_pauses_dominant_ad():
    m = load()
    result = m.evaluate_decision('TWO_ADS_ACTIVE', -1, {'b': 90, 'c': 10}, ['b', 'c'], strategy())
    assert result['action'] == 'PAUSE_AD'
    assert result['dominant_ad_id'] == 'b'


def test_stage_c_negative_pauses_campaign_and_positive_recovers():
    m = load()
    negative = m.evaluate_decision('ONE_AD_ACTIVE', -0.01, {'c': 7}, ['c'], strategy())
    positive = m.evaluate_decision('ONE_AD_ACTIVE', 0.01, {'c': 7}, ['c'], strategy())
    assert negative['action'] == 'PAUSE_CAMPAIGN'
    assert positive['action'] == 'KEEP_POSITIVE'


def test_window_metrics_subtracts_baseline_and_fails_closed_on_divergence():
    m = load()
    record = {
        'active_ad_ids': ['a', 'b'],
        'baseline_meta_spend_by_ad': {'a': 20, 'b': 10},
        'baseline_sb_investment_usd': 30,
        'baseline_sb_net_revenue_usd': 20,
    }
    cumulative = {
        'meta_by_ad': {'a': 38, 'b': 12},
        'sb_by_campaign': {'c1': {'investment': 50, 'net_revenue': 30, 'matched_rows': 2}},
    }
    result = m.window_metrics('c1', record, cumulative, 5, 1)
    assert result['spend_by_active_ad'] == {'a': 18, 'b': 2}
    assert result['meta_spend_usd'] == 20
    assert result['sb_investment_usd'] == 20
    assert result['sb_net_revenue_usd'] == 10
    assert result['roi_pct'] == -50
    assert result['reconciled'] is True
    cumulative['sb_by_campaign']['c1']['investment'] = 40
    assert m.window_metrics('c1', record, cumulative, 5, 1)['reconciled'] is False


def test_verified_ad_pause_opens_new_24h_window_and_baselines(tmp_path):
    m = load()
    setattr(m, 'STATE_PATH', tmp_path / 'state.json')
    now = datetime(2026, 9, 1, 0, 30, tzinfo=ZoneInfo('America/Sao_Paulo'))
    record = {
        'active_ad_ids': ['a', 'b', 'c'], 'paused_ad_ids': [], 'current_stage': 'THREE_ADS_ACTIVE',
    }
    state = {'campaigns': {'c1': record}}
    pending = {
        'target_type': 'ad', 'target_id': 'a', 'action_key': 'k',
        'window_metrics': {'roi_pct': -20},
        'cumulative_snapshot': {
            'meta_by_ad': {'a': 80, 'b': 10, 'c': 10},
            'sb_by_campaign': {'c1': {'investment': 100, 'net_revenue': 80}},
        },
    }
    m.finalize_pause(state, 'c1', record, pending, {'configured_status': 'PAUSED'}, now)
    saved = json.loads(m.STATE_PATH.read_text())
    assert saved['campaigns']['c1']['current_stage'] == 'TWO_ADS_ACTIVE'
    assert saved['campaigns']['c1']['active_ad_ids'] == ['b', 'c']
    assert saved['campaigns']['c1']['paused_ad_ids'] == ['a']
    assert saved['campaigns']['c1']['baseline_sb_investment_usd'] == 100
    assert saved['campaigns']['c1']['next_checkpoint_at_sp'].startswith('2026-09-02T00:30:00')


def test_runner_scope_has_no_delete_budget_or_adset_write():
    source = RUNNER.read_text()
    assert "graph_post_once(target_id, token, {'status': 'PAUSED'})" in source
    assert "'DELETED'" not in source
    assert "'daily_budget'" not in source.split('graph_post_once(target_id', 1)[1]
    assert 'adset' not in source.split('graph_post_once(target_id', 1)[1].lower()
    wrapper = WRAPPER.read_text()
    assert '--watch --quiet' in wrapper
    assert 'ares-cpv-meta-lane-2039876850230678.lock' in wrapper


def test_contract_exposes_bounded_automation_scope_when_enabled():
    op = json.loads(OPERATION.read_text())
    cfg = op['management_scope']['autonomous_action_scope']['creative_cut_writes']
    if isinstance(cfg, dict):
        assert cfg['allowed_actions'] == ['pause_dominant_ad_stage_a', 'pause_dominant_ad_stage_b', 'pause_campaign_terminal_stage_c']
        assert cfg['never_actions'] == ['delete_campaign', 'change_budget', 'pause_adset', 'reactivate_paused_ad']
