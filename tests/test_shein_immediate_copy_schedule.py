"""Offline-only maintenance regression; no Meta requests."""
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3.shein_copy_schedule import normalized_schedule_proof


def fixture():
    shell = {'idempotency_key': 'test-c155', 'account_id': '123', 'start_intent': 'IMMEDIATE', 'start_time': '2026-10-13T10:10:08-04:00'}
    state = {'request': {'request_id': 'test', 'start_now': True}, 'manifest': {'campaigns': [shell]}, 'target_manifest': {'campaigns': [copy.deepcopy(shell)]}}
    checkpoint = {'account_id': '123', 'status': 'COMPLETE', 'bundles': [{'status': 'COMPLETE', 'campaign_ids': ['456'], 'adset_ids': ['789'], 'idempotency_keys': ['test-c155'], 'timings': {'adset_copy': {'started_at': '2026-10-13T14:10:12.855609+00:00', 'finished_at': '2026-10-13T14:10:16.972303+00:00'}}, 'readback_results': [{'name': 'readback_campaign_1', 'code': 200, 'body': {'id': '456', 'account_id': '123', 'start_time': '2026-10-13T10:10:13-0400'}}, {'name': 'readback_adsets_1', 'code': 200, 'body': {'data': [{'id': '789', 'start_time': '2026-10-13T10:10:13-0400'}]}}]}]}
    return state, checkpoint


def check(state=None, checkpoint=None, **changes):
    s, c = fixture()
    args = dict(request_id='test', account_id='123', campaign_id='456', idempotency_key='test-c155', expected='2026-10-13T10:10:08-04:00', observed='2026-10-13T10:10:13-0400')
    args.update(changes)
    return normalized_schedule_proof(state or s, checkpoint or c, **args)


def test_copy_window_normalization_is_proven():
    assert check()['verified'] is True


def test_scheduled_intent_rejected():
    s, c = fixture()
    s['request']['start_now'] = False
    assert check(s, c) is None
    s['request']['start_now'] = True
    s['manifest']['campaigns'][0].pop('start_intent')
    assert check(s, c) is None


def test_no_generic_time_tolerance():
    assert check(observed='2026-10-13T10:10:14-0400') is None
    s, c = fixture()
    for r in c['bundles'][0]['readback_results']:
        if r['name'].startswith('readback_campaign'): r['body']['start_time']='2026-10-13T10:10:30-0400'
        else: r['body']['data'][0]['start_time']='2026-10-13T10:10:30-0400'
    assert check(s, c, observed='2026-10-13T10:10:30-0400') is None


def test_identity_and_manifest_bindings_rejected():
    for change in [{'campaign_id':'999'}, {'account_id':'999'}, {'idempotency_key':'other-c155'}, {'request_id':'other'}, {'expected':'2026-10-13T10:10:07-04:00'}]:
        assert check(**change) is None


def test_campaign_and_adset_must_agree():
    s, c = fixture()
    c['bundles'][0]['readback_results'][1]['body']['data'][0]['start_time']='2026-10-13T10:10:12-0400'
    assert check(s, c) is None


def test_incomplete_copy_provenance_rejected():
    s, c = fixture()
    c['bundles'][0]['status']='IN_PROGRESS'
    assert check(s, c) is None
    s, c = fixture()
    c['bundles'][0]['timings']={}
    assert check(s, c) is None
