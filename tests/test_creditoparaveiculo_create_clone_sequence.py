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
    assert payload['dsa_beneficiary'] == 'Garagem Brasil'
    assert payload['dsa_payor'] == 'Garagem Brasil'
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
