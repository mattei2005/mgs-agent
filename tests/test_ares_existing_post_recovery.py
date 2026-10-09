"""Offline regressions for existing-post recovery; never contacts Meta."""
from urllib.parse import parse_qs, urlsplit

import pytest

from test_ares_campaign_engine_v3 import (
    CampaignEngine, BatchResult, FakeBatchTransport, ExecutionFailed,
    config, manifest, existing_post_campaign,
)


def recovery_case(tmp_path, *, known=False, duplicate=False, repeated=False, mismatch=False,
                  wrong_account=False, wrong_tags=False, never_end=False):
    campaign = existing_post_campaign()
    campaign['ads'] = campaign['ads'][:2]
    request = manifest([campaign], request_id='existing-post-pagination-regression')
    creatives = [
        {'id': f'known-{i}', 'account_id': '100',
         'name': ad['creative_payload']['name'] + ' 2026-10-06-generated-suffix',
         'object_story_id': ad['creative_payload']['object_story_id'],
         'effective_object_story_id': ad['creative_payload']['object_story_id'],
         'url_tags': ad['creative_payload']['url_tags']}
        for i, ad in enumerate(campaign['ads'], 1)
    ]

    class RecoveryTransport(FakeBatchTransport):
        def __init__(self):
            super().__init__('100')
            self.operations = []
            self.pages = 0

        def execute(self, operations, stage):
            self.operations.extend(operations)
            if stage.startswith('existing_post_recovery_inventory'):
                self.calls.append({'stage': stage, 'operations': len(operations)})
                results = []
                for op in operations:
                    if op.name.startswith('existing_post_recovery_ads_'):
                        body = {'data': []}
                    elif op.name.startswith('existing_post_recovery_creative_id_'):
                        cid = op.relative_url.split('?', 1)[0]
                        body = dict(next(c for c in creatives if c['id'] == cid))
                        if mismatch:
                            body['object_story_id'] = 'different-post'
                        if wrong_account:
                            body['account_id'] = 'different-account'
                        if wrong_tags:
                            body['url_tags'] = 'utm_campaign=wrong'
                    elif op.name.startswith('existing_post_recovery_candidate_'):
                        cid = op.relative_url.split('?', 1)[0]
                        if cid == 'duplicate-id':
                            body = {**creatives[0], 'id': cid}
                        else:
                            body = dict(next(c for c in creatives if c['id'] == cid))
                    elif '/adcreatives?' in op.relative_url:
                        query = parse_qs(urlsplit(op.relative_url).query)
                        assert query['fields'] == ['id,name']
                        assert query['limit'] == ['5000']
                        assert not known, 'known IDs must avoid account-wide creative inventory'
                        after = parse_qs(urlsplit(op.relative_url).query).get('after')
                        self.pages += 1
                        if not after:
                            body = {'data': [{'id': 'unrelated', 'name': 'unrelated'}],
                                    'paging': {'next': 'https://graph.invalid/never-follow',
                                               'cursors': {'after': 'cursor & encoded'}}}
                        elif never_end:
                            body = {'data': [], 'paging': {
                                'next': 'https://graph.invalid/never-follow',
                                'cursors': {'after': f'cursor-{self.pages}'}}}
                        elif repeated:
                            body = {'data': [], 'paging': {
                                'next': 'https://graph.invalid/never-follow',
                                'cursors': {'after': 'cursor & encoded'}}}
                        else:
                            rows = list(creatives)
                            if duplicate:
                                rows.append({**creatives[0], 'id': 'duplicate-id'})
                            body = {'data': [{k: row[k] for k in ('id', 'name')} for row in rows]}
                    else:
                        raise AssertionError(op.relative_url)
                    results.append(BatchResult(op.name, 200, body))
                return results
            return super().execute(operations, stage)

    transport = RecoveryTransport()
    engine = CampaignEngine(config(tmp_path, enabled=True, write_enabled=True),
                            transport_factory=lambda account: transport)
    bundle = engine.planner.build(request).lanes['100'][0]
    record = {'campaign_ids': ['existing-campaign'], 'adset_ids': ['existing-adset'],
              'stage': 'shells_normalized', 'timings': {}}
    if known:
        record['existing_post_creative_ids'] = {'1.1': 'known-1', '1.2': 'known-2'}
    return engine, bundle, record, transport


def test_existing_post_recovery_paginates_and_accepts_meta_name_suffix(tmp_path):
    engine, bundle, record, transport = recovery_case(tmp_path)
    assert engine._recover_existing_post_bundle(bundle, transport, record) == ['existing-campaign']
    assert transport.pages == 2
    assert record['creative_ids'] == ['known-1', 'known-2']
    assert len([op for op in transport.operations if op.kind == 'existing_post_ad_copy']) == 2
    assert not any(op.kind in {'creative_create', 'campaign_copy', 'adset_copy'}
                   for op in transport.operations)
    assert all(op.body['status_option'] == 'PAUSED'
               for op in transport.operations if op.kind == 'existing_post_ad_copy')


def test_existing_post_recovery_prefers_verified_persisted_ids(tmp_path):
    engine, bundle, record, transport = recovery_case(tmp_path, known=True)
    engine._recover_existing_post_bundle(bundle, transport, record)
    assert transport.pages == 0
    assert record['creative_ids'] == ['known-1', 'known-2']
    assert not any(op.kind == 'creative_create' for op in transport.operations)


def test_existing_post_recovery_rejects_persisted_post_mismatch_before_writes(tmp_path):
    engine, bundle, record, transport = recovery_case(tmp_path, known=True, mismatch=True)
    with pytest.raises(ExecutionFailed, match='persisted creative identity mismatch'):
        engine._recover_existing_post_bundle(bundle, transport, record)
    assert all(op.method == 'GET' for op in transport.operations)


def test_existing_post_recovery_rejects_repeated_cursor_before_writes(tmp_path):
    engine, bundle, record, transport = recovery_case(tmp_path, repeated=True)
    with pytest.raises(ExecutionFailed, match='invalid creative inventory pagination'):
        engine._recover_existing_post_bundle(bundle, transport, record)
    assert all(op.method == 'GET' for op in transport.operations)


def test_existing_post_recovery_rejects_duplicate_semantic_creatives(tmp_path):
    engine, bundle, record, transport = recovery_case(tmp_path, duplicate=True)
    with pytest.raises(ExecutionFailed, match='duplicate creatives'):
        engine._recover_existing_post_bundle(bundle, transport, record)
    assert all(op.method == 'GET' for op in transport.operations)


@pytest.mark.parametrize('option', ['wrong_account', 'wrong_tags'])
def test_existing_post_recovery_rejects_wrong_account_or_tracking(tmp_path, option):
    engine, bundle, record, transport = recovery_case(tmp_path, known=True, **{option: True})
    with pytest.raises(ExecutionFailed, match='persisted creative identity mismatch'):
        engine._recover_existing_post_bundle(bundle, transport, record)
    assert all(op.method == 'GET' for op in transport.operations)


def test_existing_post_recovery_bounds_inventory_pages(tmp_path):
    engine, bundle, record, transport = recovery_case(tmp_path, never_end=True)
    with pytest.raises(ExecutionFailed, match='invalid creative inventory pagination'):
        engine._recover_existing_post_bundle(bundle, transport, record)
    assert transport.pages == 100
    assert all(op.method == 'GET' for op in transport.operations)


def test_existing_post_recovery_preserves_partial_success_ids():
    record = {}
    CampaignEngine._remember_existing_post_creatives(record, {'successful_children': [
        {'name': 'existing_post_creative_1_1', 'ids': {'id': 'known-1'}},
        {'name': 'existing_post_recovery_creative_1_2', 'ids': {'id': 'known-2'}},
        {'name': 'ad_copy_1_1', 'ids': {'copied_ad_id': 'ignore'}},
    ]})
    assert record['existing_post_creative_ids'] == {'1.1': 'known-1', '1.2': 'known-2'}
    record['error'] = {'message': 'later recovery read failed'}
    CampaignEngine._remember_existing_post_creatives(record, {'successful_children': []})
    assert record['existing_post_creative_ids'] == {'1.1': 'known-1', '1.2': 'known-2'}
