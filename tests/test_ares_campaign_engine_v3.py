from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path('/root/mgs-agent')
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.adapters import build_cpv_manifest
from ares_campaign_v3.cli import main as cli_main
from ares_campaign_v3.engine import CampaignEngine, EngineDisabled, ExecutionFailed
from ares_campaign_v3.media_registry import MediaRegistry, MediaNotReady
from ares_campaign_v3.prestage import AdAccountVideoUploader, PrestageService
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.planning import Planner
from ares_campaign_v3.quota import LaneQuotaStore, QuotaBlocked
from ares_campaign_v3.schema import Manifest, ManifestError
from ares_campaign_v3.transport import BatchResult, BatchTransportError, FakeBatchTransport


def future_iso(hours: int = 4) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def pure_campaign(i: int, account: str = '100') -> dict:
    return {
        'idempotency_key': f'req-{account}-{i}',
        'app_key': 'mgs-main-app',
        'account_id': account,
        'mode': 'pure_clone',
        'source_campaign_id': f'source-{i}',
        'name': f'Campaign {i}',
        'start_time': future_iso(),
        'status': 'PAUSED',
    }


def media(i: int) -> dict:
    return {
        'asset_id': f'asset-{i}',
        'checksum': f'sha256-{i}',
        'vertical_video_id': f'v-{i}',
        'square_video_id': f's-{i}',
        'ready': True,
        'upload_edge': 'ad_account_advideos',
        'association_verified': True,
    }


def source_templates() -> list[dict]:
    return [
        {
            'source_ad_id': f'source-template-ad-{i}',
            'creative_payload': {
                'object_story_spec': {'page_id': '621037101089579'},
                'asset_feed_spec': {'videos': []},
            },
        }
        for i in range(3)
    ]


def selected_sources(count: int, *, templates: list[dict] | None = None, vehicle_type: str = 'CARRO') -> list[dict]:
    source = {
        'vehicle_type': vehicle_type,
        'source_campaign_id': f'source-{vehicle_type.lower()}-campaign',
        'source_adset_id': f'source-{vehicle_type.lower()}-adset',
        'templates': templates or source_templates(),
        'roi_evidence': {'roi_pct': 42.0, 'target_date': '2099-08-21', 'currency': 'USD'},
    }
    return [source for _ in range(count)]


def prestaged_campaign(i: int, account: str = '100') -> dict:
    return {
        'idempotency_key': f'pre-{account}-{i}',
        'app_key': 'mgs-main-app',
        'account_id': account,
        'mode': 'clone_prestaged',
        'source_campaign_id': f'source-campaign-{i}',
        'source_adset_id': f'source-adset-{i}',
        'name': f'Campaign {i}',
        'adset_name': f'Adset {i}',
        'start_time': future_iso(),
        'status': 'PAUSED',
        'campaign_updates': {'daily_budget': '3000'},
        'ads': [
            {
                'name': f'Ad {i}.{j}',
                'source_ad_id': f'source-ad-{i}-{j}',
                'media': media(i * 10 + j),
                'creative_payload': {
                    'name': f'Creative {i}.{j}',
                    'object_story_spec': {'page_id': 'page-1'},
                    'asset_feed_spec': {
                        'videos': [
                            {'video_id': f'v-{i * 10 + j}'},
                            {'video_id': f's-{i * 10 + j}'},
                        ]
                    },
                },
            }
            for j in range(3)
        ],
    }


def from_zero_campaign(i: int, account: str = '100') -> dict:
    return {
        'idempotency_key': f'zero-{account}-{i}',
        'app_key': 'mgs-main-app',
        'account_id': account,
        'mode': 'from_zero_prestaged',
        'name': f'Campaign {i}',
        'adset_name': f'Adset {i}',
        'start_time': future_iso(),
        'status': 'PAUSED',
        'campaign_create': {
            'objective': 'OUTCOME_SALES',
            'buying_type': 'AUCTION',
            'daily_budget': '2500',
            'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
            'special_ad_categories': ['FINANCIAL_PRODUCTS_SERVICES'],
            'special_ad_category_country': ['BR'],
        },
        'adset_create': {
            'billing_event': 'IMPRESSIONS',
            'optimization_goal': 'OFFSITE_CONVERSIONS',
            'promoted_object': {'pixel_id': 'pixel-1', 'custom_event_type': 'SUBSCRIBE'},
            'targeting': {'geo_locations': {'countries': ['BR']}},
            'attribution_spec': [{'event_type': 'CLICK_THROUGH', 'window_days': 7}],
            'regional_regulated_categories': ['BRAZIL_REGULATION'],
            'regional_regulation_identities': {'universal_beneficiary': 'identity-1', 'universal_payer': 'identity-1'},
            'is_dynamic_creative': True,
        },
        'ads': [
            {
                'name': f'Ad {i}.{j}',
                'media': media(i * 10 + j),
                'creative_payload': {
                    'name': f'Creative {i}.{j}',
                    'object_story_spec': {'page_id': 'page-1'},
                    'asset_feed_spec': {
                        'videos': [
                            {'video_id': f'v-{i * 10 + j}'},
                            {'video_id': f's-{i * 10 + j}'},
                        ],
                        'bodies': [{'text': 'Moto sem entrada'}],
                        'titles': [{'text': 'R$249/MÊS'}],
                        'call_to_action_types': ['LEARN_MORE'],
                    },
                },
            }
            for j in range(3)
        ],
    }


def manifest(campaigns: list[dict], request_id: str = 'order-1') -> Manifest:
    return Manifest.from_dict({
        'schema_version': 3,
        'request_id': request_id,
        'operation': 'test-operation',
        'graph_version': 'v26.0',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'campaigns': campaigns,
    })


def config(tmp_path: Path, **overrides) -> dict:
    data = {
        'engine_version': 3,
        'enabled': False,
        'write_enabled': False,
        'bundle_size': 2,
        'max_ads_per_batch': 10,
        'soft_score': 100,
        'hard_score': 120,
        'score_window_seconds': 300,
        'points_per_mode': {'pure_clone': 20, 'clone_prestaged': 45, 'from_zero_prestaged': 30},
        'state_root': str(tmp_path / 'state'),
        'audit_root': str(tmp_path / 'audit'),
    }
    data.update(overrides)
    return data


def test_manifest_rejects_duplicate_idempotency_key():
    campaigns = [pure_campaign(1), pure_campaign(2)]
    campaigns[1]['idempotency_key'] = campaigns[0]['idempotency_key']
    with pytest.raises(ManifestError, match='duplicate idempotency_key'):
        manifest(campaigns)


def test_manifest_rejects_active_campaign_without_future_start():
    row = pure_campaign(1)
    row['status'] = 'ACTIVE'
    row['start_time'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with pytest.raises(ManifestError, match='ACTIVE requires future start_time'):
        manifest([row])


def test_prestaged_manifest_requires_three_ready_media_assets():
    row = prestaged_campaign(1)
    row['ads'][1]['media']['ready'] = False
    with pytest.raises(ManifestError, match='media is not ready'):
        manifest([row])


def test_prestaged_manifest_requires_nonzero_source_ad_lineage():
    row = prestaged_campaign(1)
    row['ads'][0]['source_ad_id'] = '0'
    with pytest.raises(ManifestError, match='source_ad_id'):
        manifest([row])


def test_from_zero_manifest_requires_explicit_create_payloads_and_forbids_clone_ids():
    row = from_zero_campaign(1)
    built = manifest([row]).campaigns[0]
    assert built.mode == 'from_zero_prestaged'
    assert built.source_campaign_id is None
    assert built.source_adset_id is None
    assert all(ad.source_ad_id is None for ad in built.ads)
    assert built.campaign_create['daily_budget'] == '2500'
    assert built.adset_create['promoted_object']['custom_event_type'] == 'SUBSCRIBE'

    missing = from_zero_campaign(2)
    missing.pop('adset_create')
    with pytest.raises(ManifestError, match='adset_create'):
        manifest([missing])

    clone_leak = from_zero_campaign(3)
    clone_leak['source_campaign_id'] = 'must-not-clone'
    with pytest.raises(ManifestError, match='forbids source_campaign_id'):
        manifest([clone_leak])

    nested_clone_leak = from_zero_campaign(4)
    nested_clone_leak['campaign_create']['source_ad_id'] = 'must-not-clone'
    with pytest.raises(ManifestError, match='forbids source_ad_id'):
        manifest([nested_clone_leak])

    owned_field = from_zero_campaign(5)
    owned_field['adset_create']['campaign_id'] = 'must-be-engine-owned'
    with pytest.raises(ManifestError, match='engine-owned fields'):
        manifest([owned_field])


def test_manifest_rejects_legacy_standard_enhancements_anywhere():
    row = prestaged_campaign(1)
    row['ads'][0]['creative_payload']['degrees_of_freedom_spec'] = {
        'creative_features_spec': {'standard_enhancements': {'enroll_status': 'OPT_IN'}}
    }
    with pytest.raises(ManifestError, match='standard_enhancements'):
        manifest([row])


def test_manifest_rejects_video_customization_label_missing_from_replacement_videos():
    row = prestaged_campaign(1)
    row['ads'][0]['creative_payload']['asset_feed_spec']['asset_customization_rules'] = [
        {'video_label': {'id': 'vertical-label', 'name': 'vertical'}}
    ]
    with pytest.raises(ManifestError, match='video_label'):
        manifest([row])


def test_planner_bundles_two_campaigns_per_account_without_cross_account_mix():
    m = manifest([
        pure_campaign(1, '100'), pure_campaign(2, '100'), pure_campaign(3, '100'),
        pure_campaign(4, '200'), pure_campaign(5, '200'),
    ])
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(m)
    assert [len(b.campaigns) for b in plan.lanes['100']] == [2, 1]
    assert [len(b.campaigns) for b in plan.lanes['200']] == [2]
    assert all(len({c.account_id for c in b.campaigns}) == 1 for bundles in plan.lanes.values() for b in bundles)


def test_planner_builds_one_consolidated_readback_outer_call_for_two_campaigns():
    m = manifest([pure_campaign(1), pure_campaign(2)])
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(m)
    bundle = plan.lanes['100'][0]
    assert bundle.outer_write_calls == 2
    assert bundle.outer_readback_calls == 1
    assert bundle.intermediate_get_calls == 0
    assert len(bundle.stages[0].operations) == 2


def test_planner_caps_ad_copy_batch_at_ten_ads_and_preserves_lineage():
    m = manifest([prestaged_campaign(1), prestaged_campaign(2)])
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(m)
    bundle = plan.lanes['100'][0]
    create_stage = next(stage for stage in bundle.stages if stage.name == 'ad_copy_with_creative')
    ad_ops = [op for op in create_stage.operations if op.kind == 'ad_copy_with_creative']
    assert len(ad_ops) == 6
    assert len(ad_ops) <= 10
    assert all(op.depends_on is None for op in ad_ops)
    assert all(op.relative_url.startswith('source-ad-') and op.relative_url.endswith('/copies') for op in ad_ops)
    assert all('creative_parameters' in op.body for op in ad_ops)
    assert all(not op.relative_url.startswith('act_') for op in ad_ops)


def test_planner_from_zero_uses_direct_create_endpoints_and_never_copies():
    m = manifest([from_zero_campaign(1), from_zero_campaign(2)], request_id='zero-plan')
    bundle = Planner(bundle_size=2, max_ads_per_batch=10).build(m).lanes['100'][0]
    assert [stage.name for stage in bundle.stages] == [
        'campaign_create', 'adset_create', 'creative_create', 'ad_create',
        'campaign_finalize', 'consolidated_readback',
    ]
    operations = [op for stage in bundle.stages for op in stage.operations]
    assert not any('/copies' in op.relative_url for op in operations)
    assert all(op.relative_url == 'act_100/campaigns' for op in bundle.stages[0].operations)
    assert all(op.relative_url == 'act_100/adsets' for op in bundle.stages[1].operations)
    assert all(op.relative_url == 'act_100/adcreatives' for op in bundle.stages[2].operations)
    assert all(op.relative_url == 'act_100/ads' for op in bundle.stages[3].operations)


def test_quota_store_accepts_two_prestaged_campaigns_and_blocks_third(tmp_path):
    store = LaneQuotaStore(tmp_path, soft_score=100, hard_score=120, window_seconds=300)
    lane = ('mgs-main-app', '100')
    first = store.reserve(lane, 90, request_id='two-campaigns', now=1000)
    assert first['points'] == 90
    with pytest.raises(QuotaBlocked):
        store.reserve(lane, 45, request_id='third', now=1001)


def test_quota_is_independent_per_app_and_ad_account(tmp_path):
    store = LaneQuotaStore(tmp_path, soft_score=100, hard_score=120, window_seconds=300)
    assert store.reserve(('app', '100'), 90, request_id='a', now=1000)['points'] == 90
    assert store.reserve(('app', '200'), 90, request_id='b', now=1000)['points'] == 90
    assert store.reserve(('other-app', '100'), 90, request_id='c', now=1000)['points'] == 90


def test_quota_store_persists_live_meta_tier_and_usage_headers(tmp_path):
    store = LaneQuotaStore(tmp_path, soft_score=100, hard_score=120, window_seconds=300)
    lane = ('app', '100')
    observed = store.observe_headers(lane, {
        'x-ad-account-usage': json.dumps({'acc_id_util_pct': 23.5, 'reset_time_duration': 120, 'ads_api_access_tier': 'standard_access'}),
        'x-business-use-case-usage': json.dumps({'100': [{'type': 'ads_management', 'call_count': 12, 'total_time': 18, 'total_cputime': 5}]}),
    }, now=1000)
    assert observed['ads_api_access_tier'] == 'standard_access'
    snap = store.snapshot(lane, now=1000)
    assert snap['live_usage']['acc_id_util_pct'] == 23.5
    assert snap['live_usage']['reset_time_duration'] == 120
    assert snap['live_usage']['business_usage_present'] is True


def test_full_access_lane_releases_completed_bundle_but_development_keeps_window(tmp_path):
    full = LaneQuotaStore(tmp_path / 'full', soft_score=100, hard_score=120, window_seconds=300)
    lane = ('app', '100')
    full.observe_headers(lane, {'x-ad-account-usage': json.dumps({'acc_id_util_pct': 10, 'ads_api_access_tier': 'standard_access'})}, now=1000)
    full.reserve(lane, 90, request_id='bundle-1', now=1000)
    released = full.complete(lane, 'bundle-1', now=1001)
    assert released['released'] is True
    assert full.reserve(lane, 90, request_id='bundle-2', now=1002)['points'] == 90

    development = LaneQuotaStore(tmp_path / 'dev', soft_score=100, hard_score=120, window_seconds=300)
    development.observe_headers(lane, {'x-ad-account-usage': json.dumps({'acc_id_util_pct': 10, 'ads_api_access_tier': 'development_access'})}, now=1000)
    development.reserve(lane, 60, request_id='bundle-1', now=1000)
    kept = development.complete(lane, 'bundle-1', now=1001)
    assert kept['released'] is False
    with pytest.raises(QuotaBlocked):
        development.reserve(lane, 1, request_id='bundle-2', now=1002)


def test_media_registry_roundtrip_and_fail_closed(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    registry.register(
        account_id='100', asset_id='asset-1', checksum='sum-1',
        vertical_video_id='v1', square_video_id='s1', ready=True,
        upload_edge='ad_account_advideos', association_verified=True,
    )
    assert registry.require_ready('100', 'asset-1', 'sum-1')['vertical_video_id'] == 'v1'
    assert registry.require_ready('100', 'asset-1', 'sum-1')['association_verified'] is True
    with pytest.raises(MediaNotReady):
        registry.require_ready('100', 'missing', 'sum-x')


def test_cli_media_register_requires_explicit_readback_confirmation(tmp_path):
    with pytest.raises(SystemExit, match='confirm-readback'):
        cli_main([
            'media-register', '--registry', str(tmp_path / 'media.json'),
            '--account-id', '100', '--asset-id', 'asset', '--checksum', 'sum',
            '--vertical-video-id', 'v1', '--square-video-id', 's1', '--ready',
        ])


def test_prestage_registers_only_after_both_videos_are_ready(tmp_path):
    class Uploader:
        def __init__(self):
            self.uploads = []
        def upload(self, path, title):
            self.uploads.append((Path(path).name, title))
            return f'video-{len(self.uploads)}'
        def wait_ready(self, video_ids):
            return {video_id: {'ready': True} for video_id in video_ids}
        def verify_association(self, video_ids):
            return {video_id: {'associated': True} for video_id in video_ids}
    vertical = tmp_path / 'vertical.mp4'
    square = tmp_path / 'square.mp4'
    vertical.write_bytes(b'vertical')
    square.write_bytes(b'square')
    checksum = hashlib.sha256(vertical.read_bytes()).hexdigest()
    registry = MediaRegistry(tmp_path / 'media.json')
    uploader = Uploader()
    result = PrestageService(registry, uploader).prestage(
        account_id='100', asset_id='asset-1', checksum=checksum,
        vertical_path=vertical, square_path=square,
    )
    assert result['ready'] is True
    assert result['upload_edge'] == 'ad_account_advideos'
    assert result['association_verified'] is True
    assert len(uploader.uploads) == 2
    assert registry.require_ready('100', 'asset-1', checksum)['square_video_id'] == 'video-2'


def test_prestage_does_not_register_partial_processing(tmp_path):
    class Uploader:
        def upload(self, path, title):
            return 'vertical' if 'vertical' in str(path) else 'square'
        def wait_ready(self, video_ids):
            return {'vertical': {'ready': True}, 'square': {'ready': False}}
        def verify_association(self, video_ids):
            return {video_id: {'associated': True} for video_id in video_ids}
    vertical = tmp_path / 'vertical.mp4'
    square = tmp_path / 'square.mp4'
    vertical.write_bytes(b'v')
    square.write_bytes(b's')
    checksum = hashlib.sha256(vertical.read_bytes()).hexdigest()
    registry = MediaRegistry(tmp_path / 'media.json')
    with pytest.raises(MediaNotReady):
        PrestageService(registry, Uploader()).prestage(account_id='100', asset_id='asset', checksum=checksum, vertical_path=vertical, square_path=square)
    assert registry.summary()['total'] == 0


def test_prestage_rejects_ready_page_videos_without_ad_account_association(tmp_path):
    class Uploader:
        def upload(self, path, title):
            return 'vertical' if 'vertical' in str(path) else 'square'
        def wait_ready(self, video_ids):
            return {video_id: {'ready': True} for video_id in video_ids}
        def verify_association(self, video_ids):
            return {video_id: {'associated': False} for video_id in video_ids}
    vertical = tmp_path / 'vertical.mp4'
    square = tmp_path / 'square.mp4'
    vertical.write_bytes(b'v')
    square.write_bytes(b's')
    checksum = hashlib.sha256(vertical.read_bytes()).hexdigest()
    registry = MediaRegistry(tmp_path / 'media.json')
    with pytest.raises(MediaNotReady, match='associated with the ad account'):
        PrestageService(registry, Uploader()).prestage(
            account_id='100', asset_id='asset', checksum=checksum,
            vertical_path=vertical, square_path=square,
        )
    assert registry.summary()['total'] == 0


def test_manifest_rejects_page_video_media_even_when_ready():
    row = prestaged_campaign(1)
    row['ads'][0]['media']['upload_edge'] = 'page_videos'
    row['ads'][0]['media']['association_verified'] = False
    with pytest.raises(ManifestError, match='ad account'):
        manifest([row])


def test_ad_account_video_uploader_posts_to_advideos_with_user_token(monkeypatch):
    calls = []
    class Response:
        status_code = 200
        headers = {}
        def json(self):
            return {'id': 'video-1'}
    class Common:
        def _throttle_before_request(self):
            pass
        def record_response_usage(self, *args, **kwargs):
            pass
    def fake_post(url, data, files, timeout):
        calls.append({'url': url, 'data': data, 'files': files, 'timeout': timeout})
        return Response()
    monkeypatch.setattr('ares_campaign_v3.prestage.requests.post', fake_post)
    source = Path('/tmp/ares-v3-uploader-test.mp4')
    source.write_bytes(b'video')
    try:
        uploader = AdAccountVideoUploader(
            common=Common(), user_token='user-token', account_id='123', graph_version='v26.0'
        )
        assert uploader.upload(source, 'test-title') == 'video-1'
    finally:
        source.unlink(missing_ok=True)
    assert calls[0]['url'].endswith('/act_123/advideos')
    assert calls[0]['data']['access_token'] == 'user-token'
    assert calls[0]['data']['unpublished_content_type'] == 'ADS_POST'


def test_ad_account_video_upload_retries_one_5xx_after_empty_title_readback(monkeypatch, tmp_path):
    post_calls = []
    class Response:
        headers = {}
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self.payload = payload
        def json(self):
            return self.payload
    responses = [Response(500, {}), Response(200, {'id': 'video-after-retry'})]
    class Common:
        def _throttle_before_request(self):
            pass
        def record_response_usage(self, *args, **kwargs):
            pass
        def graph_get(self, path, token, params):
            return 200, {'data': [], 'paging': {}}, {}
    def fake_post(*args, **kwargs):
        post_calls.append((args, kwargs))
        return responses.pop(0)
    monkeypatch.setattr('ares_campaign_v3.prestage.requests.post', fake_post)
    monkeypatch.setattr('ares_campaign_v3.prestage.time.sleep', lambda _: None)
    source = tmp_path / 'video.mp4'
    source.write_bytes(b'video')
    uploader = AdAccountVideoUploader(common=Common(), user_token='user', account_id='123')
    assert uploader.upload(source, 'deterministic-title') == 'video-after-retry'
    assert len(post_calls) == 2


def test_ad_account_video_upload_accepts_ambiguous_5xx_readback_without_repost(monkeypatch, tmp_path):
    post_calls = []
    class Response:
        status_code = 500
        headers = {}
        def json(self):
            return {}
    class Common:
        def _throttle_before_request(self):
            pass
        def record_response_usage(self, *args, **kwargs):
            pass
        def graph_get(self, path, token, params):
            return 200, {'data': [{'id': 'video-created', 'title': 'deterministic-title'}], 'paging': {}}, {}
    def fake_post(*args, **kwargs):
        post_calls.append((args, kwargs))
        return Response()
    monkeypatch.setattr('ares_campaign_v3.prestage.requests.post', fake_post)
    source = tmp_path / 'video.mp4'
    source.write_bytes(b'video')
    uploader = AdAccountVideoUploader(common=Common(), user_token='user', account_id='123')
    assert uploader.upload(source, 'deterministic-title') == 'video-created'
    assert len(post_calls) == 1


def test_ad_account_video_association_readback_retries_bounded_eventual_consistency(monkeypatch):
    calls = []
    class Common:
        def graph_get(self, path, token, params):
            calls.append((path, token, params))
            data = [] if len(calls) == 1 else [{'id': 'video-1', 'title': 'ready'}]
            return 200, {'data': data, 'paging': {}}, {}
    monkeypatch.setattr('ares_campaign_v3.prestage.time.sleep', lambda _: None)
    uploader = AdAccountVideoUploader(
        common=Common(), user_token='user-token', account_id='123',
        graph_version='v26.0', attempts=3, interval_seconds=1,
    )
    result = uploader.verify_association(['video-1'])
    assert result['video-1']['associated'] is True
    assert len(calls) == 2
    assert all(call[0] == 'act_123/advideos' for call in calls)


def test_cpv_adapter_builds_two_campaigns_from_six_ready_assets(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(6):
        asset_id = f'asset-{i}'
        checksum = f'sum-{i}'
        registry.register(account_id='1046241194533786', asset_id=asset_id, checksum=checksum, vertical_video_id=f'v{i}', square_video_id=f's{i}', ready=True, upload_edge='ad_account_advideos', association_verified=True)
        assets.append({
            'asset_id': asset_id,
            'checksum': checksum,
            'canonical_filename': f'CAR_BR_BR_VID_TEST_PV_{i + 1:03d}.mp4',
        })
    templates = [
        {
            'source_ad_id': f'source-ad-{i}',
            'creative_payload': {
                'object_story_spec': {'page_id': '621037101089579'},
                'asset_feed_spec': {
                    'videos': [
                        {'video_id': f'old-v-{i}', 'adlabels': [{'id': f'v-label-{i}', 'name': f'vertical-{i}'}]},
                        {'video_id': f'old-s-{i}', 'adlabels': [{'id': f's-label-{i}', 'name': f'square-{i}'}]},
                    ],
                    'link_urls': [{'website_url': 'https://example.test/?utm_campaign=b01fb13c08&utm_adgroup=b01fb13c08g01'}],
                },
            },
        }
        for i in range(3)
    ]
    payload = build_cpv_manifest(
        registry=registry,
        asset_refs=assets,
        campaign_numbers=[14, 15],
        operational_date='2099-08-21',
        request_id='cpv-20260821',
        source_selections=selected_sources(2, templates=templates),
        status='ACTIVE',
    )
    built = Manifest.from_dict(payload)
    assert len(built.campaigns) == 2
    assert all(c.mode == 'clone_prestaged' for c in built.campaigns)
    assert all(c.status == 'ACTIVE' for c in built.campaigns)
    assert [len(c.ads) for c in built.campaigns] == [3, 3]
    assert all(c.start_time.endswith('-03:00') for c in built.campaigns)
    assert 'b01fb13c14' in json.dumps(built.campaigns[0].ads[0].creative_payload)
    assert 'b01fb13c15' in json.dumps(built.campaigns[1].ads[0].creative_payload)
    assert 'b01fb13c08' not in json.dumps(payload)
    assert 'source_ad_id' not in built.campaigns[0].ads[0].creative_payload
    assert [ad.source_ad_id for ad in built.campaigns[0].ads] == ['source-ad-0', 'source-ad-1', 'source-ad-2']
    assert 'creative_payload' not in built.campaigns[0].ads[0].creative_payload
    assert built.campaigns[0].ads[0].creative_payload['asset_feed_spec']['videos'] == [
        {'video_id': 'v0', 'adlabels': [{'id': 'v-label-0', 'name': 'vertical-0'}]},
        {'video_id': 's0', 'adlabels': [{'id': 's-label-0', 'name': 'square-0'}]},
    ]
    assert [ad.name for ad in built.campaigns[0].ads] == [
        'AD 01 - CAR_BR_BR_VID_TEST_PV_001',
        'AD 02 - CAR_BR_BR_VID_TEST_PV_002',
        'AD 03 - CAR_BR_BR_VID_TEST_PV_003',
    ]
    assert built.campaigns[0].ads[0].creative_payload['name'] == 'CPV C14 AD01 CAR_BR_BR_VID_TEST_PV_001'
    assert all('asset-' not in ad.name for campaign in built.campaigns for ad in campaign.ads)


def test_cpv_adapter_preserves_distinct_car_and_moto_roi_sources(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(6):
        asset_id = f'vehicle-asset-{i}'
        checksum = f'vehicle-sum-{i}'
        registry.register(
            account_id='1046241194533786', asset_id=asset_id, checksum=checksum,
            vertical_video_id=f'vehicle-v{i}', square_video_id=f'vehicle-s{i}', ready=True,
            upload_edge='ad_account_advideos', association_verified=True,
        )
        token = 'MOTO' if i >= 3 else 'CARRO'
        assets.append({
            'asset_id': asset_id,
            'checksum': checksum,
            'canonical_filename': f'CAR_BR_BR_VID_{token}_TEST_PV_{i + 1:03d}.mp4',
        })
    sources = selected_sources(1, vehicle_type='CARRO') + selected_sources(1, vehicle_type='MOTO')
    payload = build_cpv_manifest(
        registry=registry,
        asset_refs=assets,
        campaign_numbers=[40, 41],
        operational_date='2099-08-21',
        request_id='cpv-car-moto-sources',
        source_selections=sources,
        status='ACTIVE',
    )
    built = Manifest.from_dict(payload)
    assert built.campaigns[0].source_campaign_id == 'source-carro-campaign'
    assert built.campaigns[1].source_campaign_id == 'source-moto-campaign'
    assert ' - MOTO - ' not in built.campaigns[0].name
    assert ' - MOTO - ' in built.campaigns[1].name
    assert [row['vehicle_type'] for row in payload['source_selections']] == ['CARRO', 'MOTO']


def test_cpv_adapter_builds_from_zero_without_clone_lineage(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(3):
        asset_id = f'moto-zero-{i}'
        checksum = f'moto-zero-sum-{i}'
        registry.register(
            account_id='1046241194533786', asset_id=asset_id, checksum=checksum,
            vertical_video_id=f'moto-zero-v{i}', square_video_id=f'moto-zero-s{i}', ready=True,
            upload_edge='ad_account_advideos', association_verified=True,
        )
        assets.append({
            'asset_id': asset_id,
            'checksum': checksum,
            'canonical_filename': f'CAR_BR_BR_VID_MOTO_TEST_NV_{i + 1:03d}.mp4',
        })
    create_spec = {
        'campaign_create': {
            'objective': 'OUTCOME_SALES', 'buying_type': 'AUCTION',
            'daily_budget': '9999', 'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
            'special_ad_categories': ['FINANCIAL_PRODUCTS_SERVICES'],
            'special_ad_category_country': ['BR'],
        },
        'adset_create': {
            'billing_event': 'IMPRESSIONS', 'optimization_goal': 'OFFSITE_CONVERSIONS',
            'targeting': {'geo_locations': {'countries': ['BR']}},
            'promoted_object': {'pixel_id': 'pixel-1', 'custom_event_type': 'SUBSCRIBE'},
            'attribution_spec': [{'event_type': 'CLICK_THROUGH', 'window_days': 7}],
            'regional_regulated_categories': ['BRAZIL_REGULATION'],
            'regional_regulation_identities': {'universal_beneficiary': 'identity-1', 'universal_payer': 'identity-1'},
            'is_dynamic_creative': True,
        },
    }
    payload = build_cpv_manifest(
        registry=registry, asset_refs=assets, campaign_numbers=[31],
        operational_date='2099-08-27', request_id='cpv-c31-zero',
        source_selections=selected_sources(1, vehicle_type='MOTO'),
        mode='from_zero_prestaged', from_zero_specs=[create_spec],
        daily_budget_minor=2500,
    )
    built = Manifest.from_dict(payload)
    campaign = built.campaigns[0]
    assert payload['execution_mode'] == 'from_zero_prestaged'
    assert payload['source_selection_policy'] == 'live_compliant_same_vehicle_reference_only_no_clone'
    assert payload['source_selections'][0]['reference_only'] is True
    assert payload['source_selections'][0]['clone_edges_permitted'] is False
    assert 'source_campaign_id' not in payload['source_selections'][0]
    assert campaign.mode == 'from_zero_prestaged'
    assert campaign.source_campaign_id is None
    assert campaign.source_adset_id is None
    assert campaign.campaign_create['daily_budget'] == '2500'
    assert all(ad.source_ad_id is None for ad in campaign.ads)
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(built)
    assert not any('/copies' in op.relative_url for stage in plan.lanes['1046241194533786'][0].stages for op in stage.operations)


def test_cpv_adapter_accepts_explicit_future_start_for_authorized_canary(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(3):
        asset_id = f'canary-asset-{i}'
        checksum = f'canary-sum-{i}'
        registry.register(
            account_id='1046241194533786', asset_id=asset_id, checksum=checksum,
            vertical_video_id=f'canary-v{i}', square_video_id=f'canary-s{i}', ready=True,
            upload_edge='ad_account_advideos', association_verified=True,
        )
        assets.append({
            'asset_id': asset_id,
            'checksum': checksum,
            'canonical_filename': f'CAR_BR_BR_VID_CANARY_PV_{i + 1:03d}.mp4',
        })
    explicit = future_iso(2)
    payload = build_cpv_manifest(
        registry=registry,
        asset_refs=assets,
        campaign_numbers=[20],
        operational_date='2099-08-23',
        request_id='cpv-c20-canary',
        source_selections=selected_sources(1),
        status='ACTIVE',
        start_time=explicit,
    )
    built = Manifest.from_dict(payload)
    assert built.campaigns[0].start_time == datetime.fromisoformat(explicit).astimezone(ZoneInfo('America/Sao_Paulo')).isoformat()
    assert built.campaigns[0].name.startswith('20 - ')


def test_cpv_adapter_fails_closed_without_valid_canonical_filename(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(3):
        asset_id = f'asset-{i}'
        checksum = f'sum-{i}'
        registry.register(account_id='1046241194533786', asset_id=asset_id, checksum=checksum, vertical_video_id=f'v{i}', square_video_id=f's{i}', ready=True, upload_edge='ad_account_advideos', association_verified=True)
        assets.append({'asset_id': asset_id, 'checksum': checksum, 'canonical_filename': f'CAR_BR_BR_VID_TEST_PV_{i + 1:03d}.mp4'})
    assets[0].pop('canonical_filename')
    with pytest.raises(ValueError, match='requires canonical_filename'):
        build_cpv_manifest(
            registry=registry,
            asset_refs=assets,
            campaign_numbers=[14],
            operational_date='2099-08-21',
            request_id='cpv-invalid-missing-name',
            source_selections=selected_sources(1),
        )
    assets[0]['canonical_filename'] = 'asset_technical_id.mp4'
    with pytest.raises(ValueError, match='canonical_filename is invalid'):
        build_cpv_manifest(
            registry=registry,
            asset_refs=assets,
            campaign_numbers=[14],
            operational_date='2099-08-21',
            request_id='cpv-invalid-technical-name',
            source_selections=selected_sources(1),
        )


def test_cpv_adapter_builds_arbitrary_campaign_count_and_planner_chunks_pairs(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(15):
        asset_id = f'five-asset-{i}'
        checksum = f'five-sum-{i}'
        registry.register(account_id='1046241194533786', asset_id=asset_id, checksum=checksum, vertical_video_id=f'five-v{i}', square_video_id=f'five-s{i}', ready=True, upload_edge='ad_account_advideos', association_verified=True)
        assets.append({
            'asset_id': asset_id,
            'checksum': checksum,
            'canonical_filename': f'CAR_BR_BR_VID_FIVE_PV_{i + 1:03d}.mp4',
        })
    payload = build_cpv_manifest(
        registry=registry, asset_refs=assets, campaign_numbers=[14, 15, 16, 17, 18],
        operational_date='2099-08-21', request_id='cpv-five', source_selections=selected_sources(5), status='ACTIVE',
    )
    built = Manifest.from_dict(payload)
    assert len(built.campaigns) == 5
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(built)
    assert [len(bundle.campaigns) for bundle in plan.lanes['1046241194533786']] == [2, 2, 1]


def test_engine_refuses_execute_while_disabled(tmp_path):
    engine = CampaignEngine(config(tmp_path), transport_factory=lambda account: FakeBatchTransport(account))
    with pytest.raises(EngineDisabled):
        engine.execute(manifest([pure_campaign(1)]))


def test_prevalidation_hash_allows_exact_manifest_and_blocks_tamper(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    row = prestaged_campaign(1)
    for ad in row['ads']:
        item = ad['media']
        registry.register(
            account_id='100', asset_id=item['asset_id'], checksum=item['checksum'],
            vertical_video_id=item['vertical_video_id'], square_video_id=item['square_video_id'], ready=True,
            upload_edge='ad_account_advideos', association_verified=True,
        )
    payload = manifest([row], request_id='prevalidated').raw
    validated = prevalidate_payload(payload, registry)
    assert validated['prevalidated'] is True
    cfg = config(tmp_path, enabled=True, write_enabled=True, require_prevalidated_manifest=True)
    engine = CampaignEngine(cfg, transport_factory=lambda account: FakeBatchTransport(account))
    assert engine.execute(Manifest.from_dict(validated))['status'] == 'COMPLETE_PAUSED'

    tampered = json.loads(json.dumps(validated))
    tampered['campaigns'][0]['name'] = 'tampered after prevalidation'
    with pytest.raises(ExecutionFailed, match='prevalidation'):
        CampaignEngine(config(tmp_path / 'tampered', enabled=True, write_enabled=True, require_prevalidated_manifest=True), transport_factory=lambda account: FakeBatchTransport(account)).execute(Manifest.from_dict(tampered))


def test_cli_disabled_execute_returns_safe_json_without_trace(tmp_path, capsys):
    cfg_path = tmp_path / 'config.json'
    cfg_path.write_text(json.dumps(config(tmp_path)))
    manifest_path = tmp_path / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest([pure_campaign(1)]).raw))
    rc = cli_main([
        '--config', str(cfg_path), 'execute', '--manifest', str(manifest_path),
        '--confirm-execute', '--offline-fake',
    ])
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert rc == 2
    assert payload['status'] == 'BLOCKED'
    assert payload['error_type'] == 'EngineDisabled'
    assert 'Traceback' not in output


def test_engine_dry_run_never_calls_transport(tmp_path):
    transport = FakeBatchTransport('100')
    engine = CampaignEngine(config(tmp_path), transport_factory=lambda account: transport)
    result = engine.dry_run(manifest([pure_campaign(1), pure_campaign(2)]))
    assert result['status'] == 'DRY_RUN_OK'
    assert result['campaign_count'] == 2
    assert transport.calls == []


def test_engine_execute_uses_one_copy_batch_and_one_consolidated_readback(tmp_path):
    transport = FakeBatchTransport('100')
    cfg = config(tmp_path, enabled=True, write_enabled=True)
    engine = CampaignEngine(cfg, transport_factory=lambda account: transport)
    result = engine.execute(manifest([pure_campaign(1), pure_campaign(2)]))
    assert result['status'] == 'COMPLETE_PAUSED'
    assert len(result['campaign_ids']) == 2
    assert [call['stage'] for call in transport.calls] == ['pure_clone_copy', 'pure_clone_update', 'consolidated_readback']
    assert result['metrics']['intermediate_get_calls'] == 0
    assert result['metrics']['outer_readback_calls'] == 1


def test_active_future_prestaged_campaign_is_promoted_active_in_shell_batch(tmp_path):
    class CaptureTransport(FakeBatchTransport):
        def __init__(self, account_id):
            super().__init__(account_id)
            self.operations_by_stage = {}
        def execute(self, operations, stage):
            self.operations_by_stage[stage] = operations
            return super().execute(operations, stage)
    row = prestaged_campaign(1)
    row['status'] = 'ACTIVE'
    transport = CaptureTransport('100')
    result = CampaignEngine(config(tmp_path, enabled=True, write_enabled=True), transport_factory=lambda account: transport).execute(manifest([row], request_id='active-future'))
    updates = transport.operations_by_stage['campaign_adset_update']
    campaign_update = next(op for op in updates if op.kind == 'campaign_update')
    assert campaign_update.body['status'] == 'ACTIVE'
    adset_update = next(op for op in updates if op.kind == 'adset_update')
    assert adset_update.body['status'] == 'ACTIVE'
    assert 'start_time' not in adset_update.body
    assert result['status'] == 'COMPLETE_FUTURE_ACTIVE'


def test_prestaged_execution_uses_ad_copies_with_creative_and_no_direct_ad_create(tmp_path):
    class CaptureTransport(FakeBatchTransport):
        def __init__(self, account_id):
            super().__init__(account_id)
            self.operations_by_stage = {}
        def execute(self, operations, stage):
            self.operations_by_stage[stage] = operations
            return super().execute(operations, stage)

    transport = CaptureTransport('100')
    result = CampaignEngine(
        config(tmp_path, enabled=True, write_enabled=True),
        transport_factory=lambda account: transport,
    ).execute(manifest([prestaged_campaign(1)], request_id='lineage-copy-route'))
    assert result['status'] == 'COMPLETE_PAUSED'
    assert [call['stage'] for call in transport.calls] == [
        'campaign_copy', 'adset_copy', 'campaign_adset_update',
        'ad_copy_with_creative', 'ad_name_update', 'consolidated_readback',
    ]
    copy_ops = transport.operations_by_stage['ad_copy_with_creative']
    assert len(copy_ops) == 3
    assert all(op.relative_url.startswith('source-ad-1-') and op.relative_url.endswith('/copies') for op in copy_ops)
    assert all(op.body['status_option'] == 'PAUSED' for op in copy_ops)
    assert all('creative_parameters' in op.body for op in copy_ops)
    assert all(not op.relative_url.startswith('act_') for op in copy_ops)


def test_from_zero_execution_creates_campaign_adset_creatives_and_ads_without_copy(tmp_path):
    class CaptureTransport(FakeBatchTransport):
        def __init__(self, account_id):
            super().__init__(account_id)
            self.operations_by_stage = {}
        def execute(self, operations, stage):
            self.operations_by_stage[stage] = operations
            return super().execute(operations, stage)

    transport = CaptureTransport('100')
    result = CampaignEngine(
        config(tmp_path, enabled=True, write_enabled=True),
        transport_factory=lambda account: transport,
    ).execute(manifest([from_zero_campaign(1)], request_id='from-zero-live-shape'))
    assert result['status'] == 'COMPLETE_PAUSED'
    assert [call['stage'] for call in transport.calls] == [
        'campaign_create', 'adset_create', 'creative_create', 'ad_create',
        'campaign_finalize', 'consolidated_readback',
    ]
    assert not any(
        '/copies' in op.relative_url
        for operations in transport.operations_by_stage.values()
        for op in operations
    )
    assert all(not op.body.get('source_ad_id') for op in transport.operations_by_stage['ad_create'])


def test_from_zero_readback_failure_recovers_without_replaying_writes(tmp_path):
    class FailOnceReadback(FakeBatchTransport):
        def __init__(self, account_id):
            super().__init__(account_id)
            self.failed = False
        def execute(self, operations, stage):
            if stage == 'consolidated_readback' and not self.failed:
                self.failed = True
                raise RuntimeError('synthetic from-zero readback failure')
            return super().execute(operations, stage)

    transport = FailOnceReadback('100')
    cfg = config(tmp_path, enabled=True, write_enabled=True)
    engine = CampaignEngine(cfg, transport_factory=lambda account: transport)
    request = manifest([from_zero_campaign(1)], request_id='from-zero-recovery')
    with pytest.raises(RuntimeError, match='synthetic from-zero readback failure'):
        engine.execute(request)
    first_stages = [call['stage'] for call in transport.calls]
    assert first_stages == [
        'campaign_create', 'adset_create', 'creative_create', 'ad_create', 'campaign_finalize',
    ]
    result = engine.execute(request)
    assert result['status'] == 'COMPLETE_PAUSED'
    assert [call['stage'] for call in transport.calls] == [
        *first_stages, 'recovery_consolidated_readback',
    ]


def test_engine_executes_accounts_in_independent_lanes(tmp_path):
    transports: dict[str, FakeBatchTransport] = {}
    def factory(account: str) -> FakeBatchTransport:
        transports.setdefault(account, FakeBatchTransport(account))
        return transports[account]
    cfg = config(tmp_path, enabled=True, write_enabled=True)
    rows = [pure_campaign(i, str(100 + (i % 3))) for i in range(1, 7)]
    result = CampaignEngine(cfg, transport_factory=factory).execute(manifest(rows, request_id='multi'))
    assert result['status'] == 'COMPLETE_PAUSED'
    assert set(transports) == {'100', '101', '102'}
    assert all(any(call['stage'] == 'consolidated_readback' for call in transport.calls) for transport in transports.values())


def test_engine_writes_stage_timestamps_to_audit(tmp_path):
    transport = FakeBatchTransport('100')
    cfg = config(tmp_path, enabled=True, write_enabled=True)
    result = CampaignEngine(cfg, transport_factory=lambda account: transport).execute(manifest([pure_campaign(1)]))
    audit = json.loads(Path(result['audit_path']).read_text())
    assert audit['request_id'] == 'order-1'
    assert audit['engine_release_version'] == '3.3.0'
    assert audit['lanes']['100']['bundles'][0]['timings']['copy_submit']['started_at']
    assert audit['lanes']['100']['bundles'][0]['timings']['readback']['finished_at']


def test_five_prestaged_campaigns_defer_and_resume_without_replaying_completed_bundles(tmp_path):
    cfg = config(tmp_path, enabled=True, write_enabled=True)
    transport = FakeBatchTransport('100')
    engine = CampaignEngine(cfg, transport_factory=lambda account: transport)
    m = manifest([prestaged_campaign(i) for i in range(1, 6)], request_id='five-development')
    first = engine.execute(m)
    assert first['status'] == 'PARTIAL_DEFERRED_QUOTA'
    assert len(first['campaign_ids']) == 2
    assert first['deferred_accounts'] == ['100']
    first_calls = len(transport.calls)

    lane_files = list((Path(cfg['state_root'])).glob('lane-*.json'))
    assert len(lane_files) == 1
    lane_state = json.loads(lane_files[0].read_text())
    lane_state['events'] = []
    lane_state['reservations'] = {}
    lane_state['points'] = 0
    lane_files[0].write_text(json.dumps(lane_state))
    second = engine.execute(m)
    assert second['status'] == 'PARTIAL_DEFERRED_QUOTA'
    assert len(second['campaign_ids']) == 4
    assert len(transport.calls) > first_calls

    lane_state = json.loads(lane_files[0].read_text())
    lane_state['events'] = []
    lane_state['reservations'] = {}
    lane_state['points'] = 0
    lane_files[0].write_text(json.dumps(lane_state))
    third = engine.execute(m)
    assert third['status'] == 'COMPLETE_PAUSED'
    assert len(third['campaign_ids']) == 5
    assert len(set(third['campaign_ids'])) == 5


def test_failed_request_is_checkpointed_and_cannot_be_blindly_replayed(tmp_path):
    class FailReadback(FakeBatchTransport):
        def execute(self, operations, stage):
            if stage == 'consolidated_readback':
                raise RuntimeError('synthetic readback failure')
            return super().execute(operations, stage)
    cfg = config(tmp_path, enabled=True, write_enabled=True)
    engine = CampaignEngine(cfg, transport_factory=lambda account: FailReadback(account))
    m = manifest([pure_campaign(1)], request_id='partial')
    with pytest.raises(RuntimeError, match='synthetic readback'):
        engine.execute(m)
    audit_path = Path(cfg['audit_root']) / 'partial.json'
    audit = json.loads(audit_path.read_text())
    assert audit['status'] == 'FAILED'
    assert audit['manual_reconciliation_required'] is False
    assert audit['automatic_recovery_required'] is True
    recovered = CampaignEngine(cfg, transport_factory=lambda account: FakeBatchTransport(account)).execute(m)
    assert recovered['status'] == 'COMPLETE_PAUSED'
    recovered_audit = json.loads(audit_path.read_text())
    recovery = recovered_audit['lanes']['100']['bundles'][0]['recovery']
    assert recovery['mode'] == 'consolidated_readback_only'
    assert recovery['write_replay_blocked'] is True


def test_partial_prestaged_ad_batch_recovers_missing_only_without_blind_replay(tmp_path):
    class PartialAdCopyTransport(FakeBatchTransport):
        def __init__(self, account_id):
            super().__init__(account_id)
            self.campaign_ids = []
            self.adset_ids = []
            self.ads = []
            self.initial_copy_calls = 0
            self.recovery_copy_calls = 0

        def execute(self, operations, stage):
            if stage == 'campaign_copy':
                rows = super().execute(operations, stage)
                self.campaign_ids = [row.body['copied_campaign_id'] for row in rows]
                return rows
            if stage == 'adset_copy':
                rows = super().execute(operations, stage)
                self.adset_ids = [row.body['copied_adset_id'] for row in rows]
                return rows
            if stage == 'ad_copy_with_creative':
                self.initial_copy_calls += 1
                for index, operation in enumerate(operations):
                    if index == 1:
                        continue
                    ad_id = self._id('ad')
                    self.ads.append({
                        'id': ad_id,
                        'name': f'raw-{index}',
                        'adset_id': str(operation.body['adset_id']),
                        'source_ad_id': operation.relative_url.split('/', 1)[0],
                    })
                raise BatchTransportError(stage, {
                    'children': [{'name': operations[1].name, 'code': 500, 'error': {'code': 2, 'is_transient': True}}]
                })
            if stage == 'recovery_existing_ads_readback':
                rows = []
                for operation in operations:
                    campaign_id = operation.relative_url.split('/', 1)[0]
                    campaign_index = self.campaign_ids.index(campaign_id)
                    adset_id = self.adset_ids[campaign_index]
                    rows.append(BatchResult(operation.name, 200, {
                        'data': [row for row in self.ads if row['adset_id'] == adset_id]
                    }))
                return rows
            if stage == 'recovery_missing_ad_copies':
                self.recovery_copy_calls += 1
                rows = []
                for operation in operations:
                    ad_id = self._id('ad')
                    self.ads.append({
                        'id': ad_id,
                        'name': 'raw-recovered',
                        'adset_id': str(operation.body['adset_id']),
                        'source_ad_id': operation.relative_url.split('/', 1)[0],
                    })
                    rows.append(BatchResult(operation.name, 200, {'copied_ad_id': ad_id}))
                return rows
            if stage == 'recovery_ad_name_update':
                for operation in operations:
                    live = next(row for row in self.ads if row['id'] == operation.relative_url)
                    live['name'] = str(operation.body['name'])
                return [BatchResult(operation.name, 200, {'success': True}) for operation in operations]
            return super().execute(operations, stage)

    cfg = config(
        tmp_path,
        enabled=True,
        write_enabled=True,
        soft_score=100,
        hard_score=120,
        development_access_score_max=60,
        standard_access_score_max=9000,
        development_access_readback_cooldown_seconds=305,
        quota_retry_safety_seconds=5,
        readback_recovery_points_per_campaign=3,
        points_per_mode={'pure_clone': 30, 'clone_prestaged': 30},
    )
    transport = PartialAdCopyTransport('100')
    engine = CampaignEngine(cfg, transport_factory=lambda account: transport)
    engine.quota.observe_headers(
        ('mgs-main-app', '100'),
        {'x-business-use-case-usage': json.dumps({
            '100': [{'ads_api_access_tier': 'development_access'}],
        })},
    )
    expected = [prestaged_campaign(1), prestaged_campaign(2)]
    request = manifest(expected, request_id='partial-prestaged')

    with pytest.raises(BatchTransportError):
        engine.execute(request)
    assert len(transport.ads) == 5
    assert transport.initial_copy_calls == 1

    blocked = engine.execute(request)
    assert blocked['status'] == 'PARTIAL_DEFERRED_QUOTA'
    assert transport.recovery_copy_calls == 0

    lane_path = next(Path(cfg['state_root']).glob('lane-*.json'))
    lane_state = json.loads(lane_path.read_text())
    for event in lane_state['events']:
        event['at'] = 0
    lane_path.write_text(json.dumps(lane_state))

    recovered = engine.execute(request)
    assert recovered['status'] == 'COMPLETE_PAUSED'
    assert len(recovered['campaign_ids']) == 2
    assert len(transport.ads) == 6
    assert transport.initial_copy_calls == 1
    assert transport.recovery_copy_calls == 1
    assert 'recovery_consolidated_readback' in [call['stage'] for call in transport.calls]
    assert sorted(row['name'] for row in transport.ads) == sorted(
        ad['name'] for campaign in expected for ad in campaign['ads']
    )
    checkpoint = json.loads(next((Path(cfg['state_root']) / 'checkpoints').glob('*.json')).read_text())
    assert checkpoint['manual_reconciliation_required'] is False
    recovery = checkpoint['bundles'][0]['recovery']
    assert recovery['existing_ads'] == 5
    assert recovery['missing_ads_created'] == 1
    assert recovery['readback_deferred_after_mutation'] is False
    assert recovery['reservation_covered_readback'] is True


def test_development_bundle_defers_readback_then_resumes_without_any_write_replay(tmp_path):
    cfg = config(
        tmp_path,
        enabled=True,
        write_enabled=True,
        soft_score=60,
        hard_score=60,
        points_per_mode={'pure_clone': 30, 'clone_prestaged': 30},
        development_access_readback_cooldown_seconds=305,
        quota_retry_safety_seconds=5,
        readback_recovery_points_per_campaign=3,
    )
    transport = FakeBatchTransport('100')
    engine = CampaignEngine(cfg, transport_factory=lambda account: transport)
    request = manifest([prestaged_campaign(1), prestaged_campaign(2)], request_id='cooldown-resume')

    first = engine.execute(request)
    assert first['status'] == 'PARTIAL_DEFERRED_QUOTA'
    assert first['campaign_ids'] == []
    assert first['retry_after_seconds'] == 305
    stages_before = [row['stage'] for row in transport.calls]
    assert stages_before == [
        'campaign_copy',
        'adset_copy',
        'campaign_adset_update',
        'ad_copy_with_creative',
        'ad_name_update',
    ]
    checkpoint_path = next((Path(cfg['state_root']) / 'checkpoints').glob('*.json'))
    checkpoint = json.loads(checkpoint_path.read_text())
    assert checkpoint['bundles'][0]['status'] == 'READBACK_DEFERRED'
    assert checkpoint['bundles'][0]['stage'] == 'children_created_readback_pending'
    assert checkpoint['deferred']['write_replay_blocked'] is True

    lane_path = next(Path(cfg['state_root']).glob('lane-*.json'))
    lane_state = json.loads(lane_path.read_text())
    for event in lane_state['events']:
        event['at'] = 0
    lane_path.write_text(json.dumps(lane_state))

    second = engine.execute(request)
    assert second['status'] == 'COMPLETE_PAUSED'
    assert len(second['campaign_ids']) == 2
    assert [row['stage'] for row in transport.calls[len(stages_before):]] == ['recovery_consolidated_readback']
    checkpoint = json.loads(checkpoint_path.read_text())
    recovery = checkpoint['bundles'][0]['recovery']
    assert recovery['mode'] == 'consolidated_readback_only'
    assert recovery['mutation_calls'] == 0
    assert recovery['missing_ads_created'] == 0


def test_readback_cooldown_honors_live_meta_reset_header_with_safety_margin(tmp_path):
    cfg = config(
        tmp_path,
        enabled=True,
        write_enabled=True,
        soft_score=60,
        hard_score=60,
        points_per_mode={'pure_clone': 30, 'clone_prestaged': 30},
        development_access_readback_cooldown_seconds=305,
        quota_retry_safety_seconds=5,
    )
    engine = CampaignEngine(cfg, transport_factory=lambda account: FakeBatchTransport(account))
    engine.quota.observe_headers(
        ('mgs-main-app', '100'),
        {'x-ad-account-usage': json.dumps({
            'acc_id_util_pct': 100,
            'reset_time_duration': 420,
            'ads_api_access_tier': 'development_access',
        })},
    )
    result = engine.execute(manifest([prestaged_campaign(1), prestaged_campaign(2)], request_id='header-reset'))
    assert result['status'] == 'PARTIAL_DEFERRED_QUOTA'
    assert result['retry_after_seconds'] == 425


def test_business_usage_header_exposes_marketing_api_access_tier(tmp_path):
    quota = LaneQuotaStore(tmp_path, soft_score=100, hard_score=120, window_seconds=300)
    live = quota.observe_headers(
        ('mgs-main-app', '100'),
        {'x-business-use-case-usage': json.dumps({
            '100': [{
                'type': 'ads_management',
                'call_count': 3,
                'total_cputime': 2,
                'total_time': 2,
                'estimated_time_to_regain_access': 0,
                'ads_api_access_tier': 'development_access',
            }],
        })},
    )
    assert live['ads_api_access_tier'] == 'development_access'


def test_development_tier_caps_original_120_lane_at_60(tmp_path):
    quota = LaneQuotaStore(
        tmp_path,
        soft_score=100,
        hard_score=120,
        window_seconds=300,
        development_score_max=60,
        standard_score_max=9000,
    )
    lane = ('mgs-main-app', '100')
    quota.observe_headers(
        lane,
        {'x-business-use-case-usage': json.dumps({
            '100': [{'ads_api_access_tier': 'development_access'}],
        })},
    )
    first = quota.reserve(lane, 60, request_id='first', now=1000)
    assert first['hard_score'] == 60
    with pytest.raises(QuotaBlocked) as exc:
        quota.reserve(lane, 1, request_id='second', now=1000)
    assert exc.value.detail['hard_score'] == 60


def test_standard_access_skips_development_readback_cooldown(tmp_path):
    cfg = config(
        tmp_path,
        enabled=True,
        write_enabled=True,
        soft_score=100,
        hard_score=120,
        development_access_score_max=60,
        standard_access_score_max=9000,
        development_access_readback_cooldown_seconds=305,
        quota_retry_safety_seconds=5,
    )
    transport = FakeBatchTransport('100')
    engine = CampaignEngine(cfg, transport_factory=lambda account: transport)
    engine.quota.observe_headers(
        ('mgs-main-app', '100'),
        {'x-business-use-case-usage': json.dumps({
            '100': [{'ads_api_access_tier': 'standard_access'}],
        })},
    )
    result = engine.execute(manifest([prestaged_campaign(1), prestaged_campaign(2)], request_id='standard-fast'))
    assert result['status'] == 'COMPLETE_PAUSED'
    assert [row['stage'] for row in transport.calls][-1] == 'consolidated_readback'


@pytest.mark.parametrize(('campaign_count', 'expected_retry'), [(1, 5), (2, 305)])
def test_transient_code2_retry_uses_remaining_development_lane_capacity(tmp_path, campaign_count, expected_retry):
    class TransientAdCopy(FakeBatchTransport):
        def execute(self, operations, stage):
            if stage == 'ad_copy_with_creative':
                raise BatchTransportError(stage, {
                    'children': [{
                        'name': operation.name,
                        'code': 500,
                        'error': {'code': 2, 'is_transient': True},
                    } for operation in operations],
                })
            return super().execute(operations, stage)

    cfg = config(
        tmp_path,
        enabled=True,
        write_enabled=True,
        soft_score=100,
        hard_score=120,
        development_access_score_max=60,
        standard_access_score_max=9000,
        development_access_readback_cooldown_seconds=305,
        quota_retry_safety_seconds=5,
        points_per_mode={'pure_clone': 30, 'clone_prestaged': 30},
    )
    transport = TransientAdCopy('100')
    engine = CampaignEngine(cfg, transport_factory=lambda account: transport)
    engine.quota.observe_headers(
        ('mgs-main-app', '100'),
        {'x-business-use-case-usage': json.dumps({
            '100': [{'ads_api_access_tier': 'development_access'}],
        })},
    )
    request = manifest(
        [prestaged_campaign(index) for index in range(1, campaign_count + 1)],
        request_id=f'transient-{campaign_count}',
    )
    with pytest.raises(BatchTransportError) as exc:
        engine.execute(request)
    assert exc.value.detail['recommended_retry_after_seconds'] == expected_retry


def test_production_config_preserves_120_unknown_ceiling_but_caps_development_at_60():
    production = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/config.json').read_text())
    assert production['release_version'] == '3.3.0'
    assert production['soft_score'] == 100
    assert production['hard_score'] == 120
    assert production['development_access_score_max'] == 60
    assert production['standard_access_score_max'] == 9000
    assert production['score_window_seconds'] == 300
    assert production['development_access_readback_cooldown_seconds'] == 305
    assert production['points_per_mode']['clone_prestaged'] == 30
    assert production['readback_recovery_points_per_campaign'] == 3


def test_forty_campaigns_three_accounts_produce_seven_global_waves():
    rows = [pure_campaign(i, str(100 + (i % 3))) for i in range(40)]
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(manifest(rows, request_id='forty'))
    assert plan.global_wave_count == 7
    assert max(plan.campaigns_per_global_wave) <= 6
    assert sum(plan.campaigns_per_global_wave) == 40
