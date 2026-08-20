import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-create-clone-sequence.py')


def load_module():
    spec = importlib.util.spec_from_file_location('creditoparaveiculo_sequence_test', SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_source():
    return {
        'advertiser': 'Garagem Brasil',
        'beneficiary': 'Digital Trust',
        'payor': 'Digital Trust',
        'campaign': {
            'objective': 'OUTCOME_SALES',
            'buying_type': 'AUCTION',
            'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
            'special_ad_categories': ['FINANCIAL_PRODUCTS_SERVICES'],
            'special_ad_category_country': ['BR'],
        },
        'adset': {
            'billing_event': 'IMPRESSIONS',
            'optimization_goal': 'OFFSITE_CONVERSIONS',
            'targeting': {
                'age_min': 18,
                'age_max': 65,
                'age_range': [18, 65],
                'geo_locations': {'countries': ['BR']},
                'brand_safety_content_filter_levels': ['FACEBOOK_RELAXED'],
            },
            'promoted_object': {'pixel_id': '1', 'custom_event_type': 'SUBSCRIBE', 'smart_pse_enabled': False},
            'attribution_spec': [{'event_type': 'CLICK_THROUGH', 'window_days': 7}],
        },
    }


def test_test1_payload_is_paused_brazil_regulation_and_dsa():
    mod = load_module()
    payload = mod.direct_adset_payload(fake_source(), 'campaign-id', 70)
    assert payload['status'] == 'PAUSED'
    assert payload['regional_regulated_categories'] == ['BRAZIL_REGULATION']
    assert payload['dsa_beneficiary'] == 'Digital Trust'
    assert payload['dsa_payor'] == 'Digital Trust'
    assert 'age_range' not in payload['targeting']
    assert 'brand_safety_content_filter_levels' not in payload['targeting']
    assert 'smart_pse_enabled' not in payload['promoted_object']


def test_test3_runs_only_when_both_test1_and_test2_fail():
    mod = load_module()
    assert mod.should_run_test3({'status': 'rejected_by_meta'}, {'status': 'copy_rejected_by_meta'}) is True
    assert mod.should_run_test3({'status': 'created_and_readable'}, {'status': 'copy_rejected_by_meta'}) is False
    assert mod.should_run_test3({'status': 'rejected_by_meta'}, {'status': 'copy_compliant_updated_readable'}) is False


def test_copy_paths_explicitly_disable_deep_copy():
    source = SCRIPT.read_text()
    assert source.count("'deep_copy': 'false'") >= 2


def test_minimal_readback_contract():
    mod = load_module()
    readback = {
        'campaign': {'configured_status': 'PAUSED', 'daily_budget': '3000'},
        'adsets': {'data': [{'configured_status': 'PAUSED', 'regional_regulated_categories': ['BRAZIL_REGULATION', 'VOLUNTARY_VERIFICATION']}]},
        'ads': {'data': []},
    }
    assert all(mod.validate_minimal_hierarchy(readback).values())


def test_batch_readback_waits_using_child_estimate(monkeypatch):
    mod = load_module()
    header = json.dumps({'biz': [{'type': 'ads_management', 'call_count': 100, 'estimated_time_to_regain_access': 2}]})
    calls = []
    class Common:
        def graph_batch_get(self, token, requests):
            calls.append(1)
            if len(calls) == 1:
                return 200, [{'name': 'campaign', 'code': 400, 'body': {'error': {'code': 17, 'message': 'limited'}}, 'headers': {'X-Business-Use-Case-Usage': header}}], {}
            return 200, [{'name': 'campaign', 'code': 200, 'body': {'id': '1'}, 'headers': {}}], {}
        def retry_wait_seconds(self, status, payload, headers, attempt=1):
            return 120 if status == 400 else None
        def safe_meta_error(self, payload):
            return payload.get('error') or payload
    sleeps = []
    monkeypatch.setattr(mod.time, 'sleep', sleeps.append)
    result, meta = mod.batch_requests(Common(), 'token', [{'name': 'campaign', 'path': '1', 'params': {}}], 'readback', ['1'])
    assert result['campaign'] == {'id': '1'}
    assert meta == {'attempts': 2, 'wait_seconds': 120}
    assert sleeps == [120]


def test_outer_deferred_is_not_slept_or_retried_again(monkeypatch):
    mod = load_module()
    calls = []
    class Common:
        def graph_batch_get(self, token, requests):
            calls.append(1)
            return 429, {'error': {'type': 'AresRateLimitDeferred', 'code': 'ARES_RATE_LIMIT_DEFERRED', 'retry_after_seconds': 120}}, {}
        def safe_meta_error(self, payload):
            return payload['error']
    sleeps = []
    monkeypatch.setattr(mod.time, 'sleep', sleeps.append)
    with pytest.raises(mod.ReadbackDeferred) as captured:
        mod.batch_requests(Common(), 'token', [{'name': 'campaign', 'path': '1', 'params': {}}], 'readback', ['1'])
    assert captured.value.retry_after_seconds == 120
    assert calls == [1]
    assert sleeps == []


def test_async_nonterminal_never_reads_hierarchy_or_cleans(monkeypatch, tmp_path):
    mod = load_module()
    audit = {'tests': [], 'cleanups': [], 'active_campaign_ids': [], 'audit_path': str(tmp_path / 'audit.json')}
    monkeypatch.setattr(mod, 'create_campaign_shell', lambda *args, **kwargs: 'campaign-72')
    monkeypatch.setattr(mod, 'save_audit', lambda *args, **kwargs: None)
    monkeypatch.setattr(mod, 'post', lambda *args, **kwargs: ({'async_sessions': [{'id': 'session-1'}]}, {}))
    monkeypatch.setattr(mod, 'batch_requests', lambda *args, **kwargs: ({'session_1': {'status': 'RUNNING'}}, {'attempts': 1, 'wait_seconds': 0}))
    monkeypatch.setattr(mod.time, 'sleep', lambda _: None)
    monkeypatch.setattr(mod, 'hierarchy_readback', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('must not read before terminal')))
    monkeypatch.setattr(mod, 'cleanup_campaign', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('must not cleanup before terminal')))
    with pytest.raises(mod.ReadbackDeferred) as captured:
        mod.run_test3(object(), 'token', fake_source(), audit)
    assert captured.value.stage == 'test3_async_poll'
    assert audit['active_campaign_ids'] == ['campaign-72']


def test_async_missing_session_id_defers_without_cleanup(monkeypatch, tmp_path):
    mod = load_module()
    audit = {'tests': [], 'cleanups': [], 'active_campaign_ids': [], 'audit_path': str(tmp_path / 'audit.json')}
    monkeypatch.setattr(mod, 'create_campaign_shell', lambda *args, **kwargs: 'campaign-72')
    monkeypatch.setattr(mod, 'save_audit', lambda *args, **kwargs: None)
    monkeypatch.setattr(mod, 'post', lambda *args, **kwargs: ({'accepted': True}, {}))
    monkeypatch.setattr(mod.time, 'sleep', lambda _: None)
    monkeypatch.setattr(mod, 'hierarchy_readback', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('must not read without async terminal')))
    monkeypatch.setattr(mod, 'cleanup_campaign', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('must not cleanup without async terminal')))
    with pytest.raises(mod.ReadbackDeferred) as captured:
        mod.run_test3(object(), 'token', fake_source(), audit)
    assert captured.value.stage == 'test3_async_session_missing'


def test_deferred_exception_separates_target_and_async_ids():
    mod = load_module()
    exc = mod.ReadbackDeferred('test3_async_poll', 300, ['campaign-72'], ['session-1'])
    assert exc.deferred_target_ids == ['campaign-72']
    assert exc.async_session_ids == ['session-1']


def test_resume_preflight_without_artifact_restarts_sequence_not_hierarchy(monkeypatch, tmp_path):
    mod = load_module()
    state = tmp_path / 'state.json'
    audit = tmp_path / 'audit.json'
    audit.write_text(json.dumps({'active_campaign_ids': [], 'tests': [], 'cleanups': []}))
    state.write_text(json.dumps({'status': 'deferred_readback', 'audit_path': str(audit), 'active_campaign_ids': [], 'deferred_target_ids': ['source-campaign', 'source-adset'], 'deferred_stage': 'source_preflight', 'async_session_ids': []}))
    monkeypatch.setattr(mod, 'STATE_PATH', state)
    monkeypatch.setattr(mod, 'execute_sequence', lambda: 7)
    monkeypatch.setattr(mod, 'hierarchy_readback', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('source ids must not be treated as campaign artifacts')))
    assert mod.resume_deferred() == 7


def test_resume_missing_async_session_preserves_paused_artifact(monkeypatch, tmp_path, capsys):
    mod = load_module()
    state = tmp_path / 'state.json'
    audit_path = tmp_path / 'audit.json'
    audit_path.write_text(json.dumps({'active_campaign_ids': ['campaign-72'], 'tests': [], 'cleanups': []}))
    state.write_text(json.dumps({'status': 'deferred_readback', 'audit_path': str(audit_path), 'active_campaign_ids': ['campaign-72'], 'deferred_target_ids': ['campaign-72'], 'deferred_stage': 'test3_async_session_missing', 'async_session_ids': []}))
    monkeypatch.setattr(mod, 'STATE_PATH', state)
    monkeypatch.setattr(mod, 'load_common', lambda: (_ for _ in ()).throw(AssertionError('must not call Meta without pollable session id')))
    assert mod.resume_deferred() == 2
    saved = json.loads(state.read_text())
    assert saved['status'] == 'async_session_untrackable_no_cleanup'
    assert saved['active_campaign_ids'] == ['campaign-72']


def test_dry_run_has_zero_meta_calls(monkeypatch, capsys):
    mod = load_module()
    monkeypatch.setattr(mod, 'execute_sequence', lambda: (_ for _ in ()).throw(AssertionError('must not execute')))
    import sys
    monkeypatch.setattr(sys, 'argv', ['runner'])
    assert mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['status'] == 'DRY_RUN_OFFLINE'
    assert payload['meta_calls'] == 0


def test_known_error_keeps_full_meta_json():
    mod = load_module()
    class Common:
        def graph_post(self, path, token, params):
            return 400, {'error': {
                'message': 'Invalid parameter',
                'code': 100,
                'error_subcode': 3858634,
                'error_user_title': 'Advertiser is missing',
                'error_user_msg': 'Provide a verified advertiser',
                'error_data': {'blame_field_specs': [['compliance_section']]},
            }}, {}
        def safe_meta_error(self, payload):
            return payload['error']
    with pytest.raises(mod.KnownMetaError) as captured:
        mod.post(Common(), 'token', 'path', {}, 'test_stage')
    assert captured.value.error['error_user_title'] == 'Advertiser is missing'
    assert captured.value.error['error_user_msg'] == 'Provide a verified advertiser'
    assert captured.value.error['error_data']['blame_field_specs'] == [['compliance_section']]
