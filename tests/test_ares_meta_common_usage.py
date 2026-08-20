import importlib.util
import json
import math
from pathlib import Path
from unittest import mock

import pytest

SCRIPT = Path('/root/mgs-agent/scripts/ares-meta-common.py')


def load_module(name='ares_meta_common_usage_test'):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_business_usage_multiple_businesses_and_max_metric():
    mod = load_module()
    header = json.dumps({
        'biz-1': [
            {'type': 'ads_management', 'call_count': 79, 'total_cputime': 20, 'total_time': 30},
            {'type': 'ads_insights', 'call_count': 40, 'total_cputime': 88, 'total_time': 10, 'estimated_time_to_regain_access': 3},
        ],
        'biz-2': [
            {'type': 'ads_management', 'call_count': 10, 'total_cputime': 11, 'total_time': 12},
        ],
    })
    parsed = mod.parse_business_usage_headers({'X-Business-Use-Case-Usage': header})
    assert parsed['entry_count'] == 3
    assert parsed['max_usage_pct'] == 88.0
    assert parsed['estimated_time_to_regain_access_minutes'] == 3.0
    assert parsed['limiting_metric'] == 'total_cputime'
    assert parsed['entries'][1]['business_id'] == 'biz-1'


def test_parse_business_usage_malformed_is_safe():
    mod = load_module()
    assert mod.parse_business_usage_headers({'x-business-use-case-usage': 'not-json'})['entry_count'] == 0
    assert mod.parse_business_usage_headers({})['max_usage_pct'] == 0.0


def test_parser_computes_max_over_more_than_32_entries_and_rejects_nonfinite():
    mod = load_module()
    rows = [{'type': 'ads_management', 'call_count': 1} for _ in range(32)]
    rows.append({'type': 'ads_management', 'call_count': 99, 'estimated_time_to_regain_access': 4})
    rows.append({'type': 'ads_management', 'call_count': float('inf')})
    parsed = mod.parse_business_usage_headers({'X-Business-Use-Case-Usage': json.dumps({'biz': rows})})
    assert parsed['entry_count'] == 34
    assert len(parsed['entries']) == 32
    assert parsed['max_usage_pct'] == 99.0
    assert parsed['estimated_time_to_regain_access_minutes'] == 4.0


def test_soft_limit_wait_starts_at_80_percent():
    mod = load_module()
    usage = {'entry_count': 1, 'max_usage_pct': 80.0, 'estimated_time_to_regain_access_minutes': 0.0}
    decision = mod.business_usage_decision(usage, now_epoch=1000.0)
    assert decision['soft_limited'] is True
    assert decision['wait_seconds'] == mod.BUSINESS_USAGE_SOFT_LIMIT_WAIT_SECONDS
    assert decision['blocked_until_epoch'] == 1000.0 + mod.BUSINESS_USAGE_SOFT_LIMIT_WAIT_SECONDS


def test_estimated_regain_minutes_override_soft_limit_default():
    mod = load_module()
    usage = {'entry_count': 1, 'max_usage_pct': 99.0, 'estimated_time_to_regain_access_minutes': 4.0}
    decision = mod.business_usage_decision(usage, now_epoch=1000.0)
    assert decision['wait_seconds'] == 240
    assert decision['blocked_until_epoch'] == 1240.0


def test_rate_error_17_uses_header_estimated_minutes():
    mod = load_module()
    headers = {'X-Business-Use-Case-Usage': json.dumps({'biz': [{'type': 'ads_management', 'call_count': 100, 'estimated_time_to_regain_access': 2}]})}
    payload = {'error': {'code': 17, 'message': 'User request limit reached'}}
    assert mod.retry_wait_seconds(400, payload, headers, attempt=1) == 120


def test_rate_error_613_falls_back_to_exponential_without_header_estimate():
    mod = load_module()
    payload = {'error': {'code': 613, 'message': 'Calls to this api have exceeded rate limit'}}
    assert mod.retry_wait_seconds(400, payload, {}, attempt=1) == mod.RATE_LIMIT_INITIAL_SLEEP
    assert mod.retry_wait_seconds(400, payload, {}, attempt=3) == mod.RATE_LIMIT_INITIAL_SLEEP * 4


def test_only_5xx_uses_fixed_ten_second_retry():
    mod = load_module()
    assert mod.retry_wait_seconds(503, {'error': {'code': 2}}, {}, attempt=1) == 10
    assert mod.retry_wait_seconds(408, {'error': {'code': 2}}, {}, attempt=1) is None
    assert mod.retry_wait_seconds(400, {'error': {'code': 100}}, {}, attempt=1) is None


def test_record_usage_state_persists_block_cross_process(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, 'THROTTLE_STATE_PATH', tmp_path / 'state.json')
    headers = {'X-Business-Use-Case-Usage': json.dumps({'biz': [{'type': 'ads_management', 'call_count': 83}]})}
    state = mod.record_response_usage(headers, 200, {}, now_epoch=5000.0)
    assert state['business_usage']['max_usage_pct'] == 83.0
    assert state['blocked_until_epoch'] > 5000.0
    saved = json.loads((tmp_path / 'state.json').read_text())
    assert saved['business_usage']['max_usage_pct'] == 83.0


def test_successful_low_usage_response_does_not_clear_future_rate_block(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, 'THROTTLE_STATE_PATH', tmp_path / 'state.json')
    high = {'X-Business-Use-Case-Usage': json.dumps({'biz': [{'type': 'ads_management', 'call_count': 100, 'estimated_time_to_regain_access': 1}]})}
    mod.record_response_usage(high, 400, {'error': {'code': 17}}, now_epoch=1000.0)
    low = {'X-Business-Use-Case-Usage': json.dumps({'biz': [{'type': 'ads_management', 'call_count': 10}]})}
    state = mod.record_response_usage(low, 200, {'id': 'ok'}, now_epoch=1001.0)
    assert state['blocked_until_epoch'] == 1060.0
    assert state['block_reason'] == 'meta_rate_limit'


def test_graph_get_retries_5xx_in_ten_seconds(monkeypatch):
    mod = load_module()
    responses = iter([
        (503, {'error': {'code': 2, 'message': 'temporary'}}, {}),
        (200, {'id': 'ok'}, {}),
    ])
    monkeypatch.setattr(mod, '_graph_get_once', lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(mod, '_wait_before_request_from_state', lambda: 0)
    sleeps = []
    monkeypatch.setattr(mod.time, 'sleep', sleeps.append)
    status, body, _ = mod.graph_get('me', 'token')
    assert status == 200 and body['id'] == 'ok'
    assert sleeps == [10]


def test_graph_get_does_not_retry_validation_error(monkeypatch):
    mod = load_module()
    calls = []
    def once(*args, **kwargs):
        calls.append(1)
        return 400, {'error': {'code': 100, 'message': 'Invalid parameter'}}, {}
    monkeypatch.setattr(mod, '_graph_get_once', once)
    monkeypatch.setattr(mod, '_wait_before_request_from_state', lambda: 0)
    status, _, _ = mod.graph_get('me', 'token')
    assert status == 400
    assert len(calls) == 1


def test_graph_batch_get_builds_one_outer_request(monkeypatch, tmp_path):
    mod = load_module()
    monkeypatch.setattr(mod, 'THROTTLE_STATE_PATH', tmp_path / 'state.json')
    captured = {}
    def fake_post(path, token, params=None):
        captured['path'] = path
        captured['params'] = params
        return 200, [
            {'code': 200, 'headers': [], 'body': json.dumps({'id': '1'})},
            {'code': 200, 'headers': [], 'body': json.dumps({'data': []})},
        ], {}
    monkeypatch.setattr(mod, 'graph_post', fake_post)
    status, rows, _ = mod.graph_batch_get('token', [
        {'name': 'campaign', 'path': '1', 'params': {'fields': 'id'}},
        {'name': 'ads', 'path': '1/ads', 'params': {'fields': 'id', 'limit': 10}},
    ])
    assert status == 200
    assert captured['path'] == ''
    assert len(captured['params']['batch']) == 2
    assert [row['name'] for row in rows] == ['campaign', 'ads']
    assert rows[0]['body'] == {'id': '1'}
