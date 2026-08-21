import importlib.util
from datetime import datetime, timezone
from pathlib import Path

MODULE_PATH = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-daily-create.py')
spec = importlib.util.spec_from_file_location('cpv_daily_create', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def test_campaign_name_and_start_time():
    op = datetime(2026, 8, 20, 17, 0, tzinfo=mod.SP)
    assert mod.campaign_name(50, op) == '50 - 21-08 - Garagem Brasil - (b01fb13c50) event_Subscribe - MAXVOL'
    assert mod.scheduled_start(op).isoformat() == '2026-08-21T00:30:00-03:00'
    payload = mod.campaign_payload({'campaign': {'objective': 'OUTCOME_SALES', 'buying_type': 'AUCTION', 'special_ad_categories': ['FINANCIAL_PRODUCTS_SERVICES'], 'special_ad_category_country': ['BR']}}, 50, op)
    assert payload['status'] == 'PAUSED'
    assert payload['bid_strategy'] == 'LOWEST_COST_WITHOUT_CAP'


def test_standard_enhancements_validator_uses_exact_recursive_key():
    catalog_only = {
        'creative_features_spec': {
            'standard_enhancements_catalog': {'enroll_status': 'OPT_OUT'},
        }
    }
    exact_nested = {
        'creative_features_spec': {
            'nested': {
                'standard_enhancements': {'enroll_status': 'OPT_IN'},
            }
        }
    }
    assert mod.contains_exact_json_key(catalog_only, 'standard_enhancements') is False
    assert mod.contains_exact_json_key(exact_nested, 'standard_enhancements') is True


def test_validate_only_retry_is_bounded_for_5xx_and_propagation():
    assert mod.validate_only_retry_delay({'http': 500, 'error': {'code': 1}}, 1, 0) == 10
    assert mod.validate_only_retry_delay({'http': 503, 'error': {}}, 2, 1) == 10
    assert mod.validate_only_retry_delay({'http': 500, 'error': {}}, 3, 2) is None
    assert mod.validate_only_retry_delay({'http': 400, 'error': {'error_subcode': 2446289}}, 1, 0) == 5
    assert mod.validate_only_retry_delay({'http': 400, 'error': {'error_subcode': 3858504}}, 1, 0) is None


def test_choose_slots_requires_deleted_or_absent():
    campaigns = [
        {'id': 'a', 'name': '50 - old', 'effective_status': 'ARCHIVED'},
        {'id': 'b', 'name': '49 - live', 'effective_status': 'PAUSED'},
        {'id': 'c', 'name': '48 - old', 'effective_status': 'ARCHIVED'},
    ]
    slots, history, replacements = mod.choose_slots(campaigns, [50, 49, 48])
    assert slots == [50, 48]
    assert history['50'][0]['effective_status'] == 'ARCHIVED'
    assert replacements == {}


def test_default_sequence_requires_c12_then_c13_without_skipping():
    campaigns = [{'id': 'c13', 'name': '13 - existing', 'effective_status': 'PAUSED'}]
    try:
        mod.choose_slots(campaigns, None)
    except mod.Stop as exc:
        assert exc.stage == 'slot_selection'
        assert exc.detail['selected'] == [12]
    else:
        raise AssertionError('occupied C13 must block the contiguous C12+C13 batch')


def test_authorized_replacement_accepts_only_single_paused_old_campaign_per_slot():
    campaigns = [
        {'id': 'old12', 'name': '12 - old', 'configured_status': 'PAUSED', 'effective_status': 'PAUSED'},
        {'id': 'old13', 'name': '13 - old', 'configured_status': 'PAUSED', 'effective_status': 'PAUSED'},
    ]
    slots, history, replacements = mod.choose_slots(campaigns, None, allow_replacement=True)
    assert slots == [12, 13]
    assert replacements['12']['id'] == 'old12'
    assert replacements['13']['id'] == 'old13'


def test_copy_response_accepts_native_meta_copy_keys():
    assert mod.copy_response_id({'copied_campaign_id': 'new-campaign'}, 'copied_campaign_id', 'copied_campaigns') == 'new-campaign'
    assert mod.copy_response_id({'copied_adsets': [{'id': 'new-adset'}]}, 'copied_adset_id', 'copied_adsets') == 'new-adset'


def test_quota_plan_falls_back_to_one_campaign_on_development_access():
    common = mod.load_common()

    class FakeCommon:
        @staticmethod
        def read_throttle_state():
            return {
                'ad_account_usage': {'present': True, 'acc_id_util_pct': 2, 'ads_api_access_tier': 'development_access'},
                'business_usage': {},
            }

        ads_management_score_budget = staticmethod(common.ads_management_score_budget)

    plan = mod.build_quota_plan(FakeCommon(), 2, clone_source=True, replacement=True)
    assert plan['selected_count'] == 1
    assert plan['fallback_applied'] is True
    assert plan['options']['2']['projected_score'] == 95
    assert plan['options']['1']['projected_score'] == 50


def test_quota_plan_fails_closed_without_x_ad_account_usage():
    common = mod.load_common()

    class FakeCommon:
        @staticmethod
        def read_throttle_state():
            return {'business_usage': {'entries': [{'ads_api_access_tier': 'development_access'}]}}

        ads_management_score_budget = staticmethod(common.ads_management_score_budget)

    plan = mod.build_quota_plan(FakeCommon(), 2, clone_source=True, replacement=True)
    assert plan['selected_count'] == 0
    assert plan['options']['1']['reason'] == 'missing_x_ad_account_usage'


def test_async_deep_copy_builder_is_paused_and_uses_official_endpoint():
    op = datetime(2026, 8, 20, 17, 0, tzinfo=mod.SP)
    batch = mod.build_async_deep_copy_adbatch(12, op)
    assert len(batch) == 1
    assert batch[0]['relative_url'] == f'{mod.GRAPH_VERSION}/{mod.SOURCE_CAMPAIGN_ID}/copies'
    body = mod.urllib.parse.parse_qs(batch[0]['body'])
    assert body['deep_copy'] == ['true']
    assert body['status_option'] == ['PAUSED']
    assert 'C12 ASYNC CLONE' in body['rename_options'][0]


def test_choose_slots_and_assets_support_single_campaign_fallback():
    campaigns = [
        {'id': 'old12', 'name': '12 - old', 'configured_status': 'PAUSED', 'effective_status': 'PAUSED'},
        {'id': 'old13', 'name': '13 - old', 'configured_status': 'PAUSED', 'effective_status': 'PAUSED'},
    ]
    slots, _, replacements = mod.choose_slots(campaigns, [12, 13], allow_replacement=True, required_count=1)
    assert slots == [12]
    assert set(replacements) == {'12'}
    candidates = [
        {'asset_id': f'a{i}', 'canonical_filename': f'a{i}.mp4', 'perceptual_fingerprint': f'fp{i}'}
        for i in range(6)
    ]
    selected = mod.choose_assets(candidates, [row['canonical_filename'] for row in candidates], required_count=3)
    assert [row['asset_id'] for row in selected] == ['a0', 'a1', 'a2']


def test_writer_requires_separate_reconciliation_manifest(tmp_path, monkeypatch):
    path = tmp_path / 'reconciliation.json'
    monkeypatch.setattr(mod, 'RECONCILIATION_PATH', path)
    selected = [{'asset_id': 'a1', 'asset_drive_id': 'd1', 'clean_checksum': 'sha1'}]
    path.write_text(__import__('json').dumps({
        'schema_version': 1,
        'status': 'valid',
        'account_id': mod.ACCOUNT_ID,
        'generated_at_utc': '2026-08-21T00:00:00+00:00',
        'valid_until_utc': '2099-08-21T06:00:00+00:00',
        'source': {'mode': 'test'},
        'assets': [{'asset_id': 'a1', 'asset_drive_id': 'd1', 'clean_checksum': 'sha1', 'approved': True, 'meta_conflicts': []}],
    }))
    result = mod.load_reconciliation_manifest(selected)
    assert result['checks'][0]['approved'] is True
    selected[0]['clean_checksum'] = 'changed'
    try:
        mod.load_reconciliation_manifest(selected)
    except mod.Stop as exc:
        assert exc.stage == 'reconciliation_manifest'
    else:
        raise AssertionError('checksum drift must block campaign writer')


def test_campaign_writer_does_not_call_global_reconciliation():
    source = __import__('inspect').getsource(mod.execute)
    assert 'account_ads_snapshot(common' not in source
    assert 'video_metadata(common' not in source
    assert 'load_reconciliation_manifest(selected)' in source


def test_creative_payload_replaces_media_utm_and_standard_enhancements():
    source_ad = {
        'id': 'source-ad',
        'creative': {
            'object_story_spec': {'page_id': mod.PAGE_ID},
            'asset_feed_spec': {
                'videos': [
                    {'video_id': 'old-v', 'adlabels': [{'id': '1', 'name': 'vertical'}], 'thumbnail_url': 'x'},
                    {'video_id': 'old-s', 'adlabels': [{'id': '2', 'name': 'square'}], 'thumbnail_url': 'y'},
                ],
                'link_urls': [{'website_url': 'https://x/?utm_campaign=b01fb13c08&utm_adgroup=b01fb13c08g01'}],
            },
            'degrees_of_freedom_spec': {
                'creative_features_spec': {
                    'standard_enhancements': {'enroll_status': 'OPT_IN'},
                    'standard_enhancements_catalog': {'enroll_status': 'OPT_OUT'},
                }
            },
        },
    }
    payload = mod.creative_payload(source_ad, 50, 1, 'CAR_BR_BR_VID_SCORE_BAIXO_PV_016.mp4', 'new-v', 'new-s')
    videos = payload['asset_feed_spec']['videos']
    assert [row['video_id'] for row in videos] == ['new-v', 'new-s']
    assert all('thumbnail_url' not in row for row in videos)
    assert 'b01fb13c50' in payload['asset_feed_spec']['link_urls'][0]['website_url']
    assert 'b01fb13c08' not in payload['asset_feed_spec']['link_urls'][0]['website_url']
    features = payload['degrees_of_freedom_spec']['creative_features_spec']
    assert 'standard_enhancements' not in features
    assert 'standard_enhancements_catalog' in features


def test_pool_release_is_temporal_and_exact_fingerprint_deduped():
    latest = datetime(2026, 8, 18, 21, 24, tzinfo=timezone.utc)
    live = {'d1': {}, 'd2': {}, 'd3': {}}
    base = {
        'vertical': 'CAR', 'country': 'BR', 'language': 'BR', 'format': 'VID',
        'status': '01_READY', 'metadata_clean': True, 'used_by': None,
        'first_seen_at': '2026-08-19T01:00:00+00:00',
    }
    rows = [
        {**base, 'asset_id': 'a1', 'asset_drive_id': 'd1', 'perceptual_fingerprint': 'fp1', 'canonical_filename': 'a.mp4'},
        {**base, 'asset_id': 'a2', 'asset_drive_id': 'd2', 'perceptual_fingerprint': 'fp1', 'canonical_filename': 'b.mp4'},
        {**base, 'asset_id': 'a3', 'asset_drive_id': 'd3', 'perceptual_fingerprint': 'fp2', 'canonical_filename': 'c.mp4'},
    ]
    eligible, duplicate = mod.pool_candidates(rows, live, latest, True)
    assert [row['asset_id'] for row in eligible] == ['a1', 'a3']
    assert [row['asset_id'] for row in duplicate] == ['a2']


def test_meta_conflict_detects_original_sequence():
    selected = [{'asset_id': 'a', 'canonical_filename': 'CAR_BR_BR_VID_X_PV_001.mp4', 'original_filename': '1_196 - Story Financiamento (Brasil).mp4'}]
    conflicts = mod.selected_meta_conflicts(selected, [], [{'video_id': 'v', 'title': '196 - Story Financiamento (Brasil).mp4'}])
    assert len(conflicts) == 1
    assert conflicts[0]['source_sequence'] == '196'


def test_code17_batch_readback_is_deferred_not_regular_failure():
    class FakeCommon:
        @staticmethod
        def graph_batch_get(token, requests):
            return 200, [{'name': 'adsets', 'code': 400, 'body': {'error': {'code': 17, 'error_subcode': 2446079, 'message': 'limit'}}}], {}

        @staticmethod
        def safe_meta_error(payload):
            return payload.get('error') or {}

    try:
        mod.batch_get(FakeCommon(), 'token', [{'name': 'adsets'}], 'final_readback')
    except mod.ReadbackDeferred as exc:
        assert exc.stage == 'final_readback'
        assert exc.retry_after_seconds == 300
    else:
        raise AssertionError('code 17 must defer final readback')


def test_account_ads_snapshot_includes_current_and_archived_and_dedupes():
    original = mod.graph_get
    calls = []

    def fake_graph_get(common, token, path, params, stage):
        calls.append(params.get('effective_status'))
        if params.get('effective_status') == ['ARCHIVED']:
            return {'data': [{'id': '2', 'effective_status': 'ARCHIVED'}, {'id': '1', 'effective_status': 'ARCHIVED'}]}, {}
        return {'data': [{'id': '1', 'effective_status': 'PAUSED'}]}, {}

    mod.graph_get = fake_graph_get
    try:
        rows = mod.account_ads_snapshot(object(), 'token')
    finally:
        mod.graph_get = original
    assert [row['id'] for row in rows] == ['1', '2']
    assert calls == [None, ['ARCHIVED']]


def test_graph_get_code17_is_deferred():
    class FakeCommon:
        @staticmethod
        def graph_get(path, token, params):
            return 400, {'error': {'code': 17, 'error_subcode': 2446079, 'message': 'limit'}}, {}

        @staticmethod
        def safe_meta_error(payload):
            return payload.get('error') or {}

    try:
        mod.graph_get(FakeCommon(), 'token', 'campaign', {}, 'activation_readback')
    except mod.ReadbackDeferred as exc:
        assert exc.stage == 'activation_readback'
    else:
        raise AssertionError('code17 GET must defer')


def test_video_readiness_uses_one_batch_for_all_ready_media():
    class FakeCommon:
        calls = 0

        @classmethod
        def graph_batch_get(cls, token, requests):
            cls.calls += 1
            return 200, [
                {'name': row['name'], 'code': 200, 'body': {'id': row['name'], 'status': {'video_status': 'ready'}}}
                for row in requests
            ], {}

        @staticmethod
        def safe_meta_error(payload):
            return payload.get('error') or {}

    result = mod.wait_videos_ready_batch(FakeCommon(), 'page-token', ['v1', 'v2', 'v3'], 'video_ready')
    assert FakeCommon.calls == 1
    assert result['attempts'] == [{'attempt': 1, 'ready_count': 3, 'total': 3}]
