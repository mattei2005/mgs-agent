from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path('/root/mgs-agent')
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.adapters import build_cpv_manifest
from ares_campaign_v3.cli import main as cli_main
from ares_campaign_v3.engine import CampaignEngine, EngineDisabled, ExecutionFailed
from ares_campaign_v3.media_registry import MediaRegistry, MediaNotReady
from ares_campaign_v3.prestage import PrestageService
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.planning import Planner
from ares_campaign_v3.quota import LaneQuotaStore, QuotaBlocked
from ares_campaign_v3.schema import Manifest, ManifestError
from ares_campaign_v3.transport import FakeBatchTransport


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
    }


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
        'points_per_mode': {'pure_clone': 20, 'clone_prestaged': 45},
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


def test_manifest_rejects_legacy_standard_enhancements_anywhere():
    row = prestaged_campaign(1)
    row['ads'][0]['creative_payload']['degrees_of_freedom_spec'] = {
        'creative_features_spec': {'standard_enhancements': {'enroll_status': 'OPT_IN'}}
    }
    with pytest.raises(ManifestError, match='standard_enhancements'):
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
    assert bundle.outer_write_calls == 1
    assert bundle.outer_readback_calls == 1
    assert bundle.intermediate_get_calls == 0
    assert len(bundle.stages[0].operations) == 2


def test_planner_caps_ad_create_batch_at_ten_ads():
    m = manifest([prestaged_campaign(1), prestaged_campaign(2)])
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(m)
    bundle = plan.lanes['100'][0]
    create_stage = next(stage for stage in bundle.stages if stage.name == 'creative_ad_create')
    ad_ops = [op for op in create_stage.operations if op.kind == 'ad_create']
    assert len(ad_ops) == 6
    assert len(ad_ops) <= 10
    assert all(op.depends_on for op in ad_ops)


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
    development.reserve(lane, 90, request_id='bundle-1', now=1000)
    kept = development.complete(lane, 'bundle-1', now=1001)
    assert kept['released'] is False
    with pytest.raises(QuotaBlocked):
        development.reserve(lane, 90, request_id='bundle-2', now=1002)


def test_media_registry_roundtrip_and_fail_closed(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    registry.register(account_id='100', asset_id='asset-1', checksum='sum-1', vertical_video_id='v1', square_video_id='s1', ready=True)
    assert registry.require_ready('100', 'asset-1', 'sum-1')['vertical_video_id'] == 'v1'
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
    assert len(uploader.uploads) == 2
    assert registry.require_ready('100', 'asset-1', checksum)['square_video_id'] == 'video-2'


def test_prestage_does_not_register_partial_processing(tmp_path):
    class Uploader:
        def upload(self, path, title):
            return 'vertical' if 'vertical' in str(path) else 'square'
        def wait_ready(self, video_ids):
            return {'vertical': {'ready': True}, 'square': {'ready': False}}
    vertical = tmp_path / 'vertical.mp4'
    square = tmp_path / 'square.mp4'
    vertical.write_bytes(b'v')
    square.write_bytes(b's')
    checksum = hashlib.sha256(vertical.read_bytes()).hexdigest()
    registry = MediaRegistry(tmp_path / 'media.json')
    with pytest.raises(MediaNotReady):
        PrestageService(registry, Uploader()).prestage(account_id='100', asset_id='asset', checksum=checksum, vertical_path=vertical, square_path=square)
    assert registry.summary()['total'] == 0


def test_cpv_adapter_builds_two_campaigns_from_six_ready_assets(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(6):
        asset_id = f'asset-{i}'
        checksum = f'sum-{i}'
        registry.register(account_id='1046241194533786', asset_id=asset_id, checksum=checksum, vertical_video_id=f'v{i}', square_video_id=f's{i}', ready=True)
        assets.append({'asset_id': asset_id, 'checksum': checksum})
    templates = [
        {
            'source_ad_id': f'source-ad-{i}',
            'creative_payload': {
                'object_story_spec': {'page_id': '621037101089579'},
                'asset_feed_spec': {
                    'videos': [],
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
        operational_date='2026-08-21',
        request_id='cpv-20260821',
        creative_templates=templates,
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
    assert 'creative_payload' not in built.campaigns[0].ads[0].creative_payload


def test_cpv_adapter_builds_arbitrary_campaign_count_and_planner_chunks_pairs(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    assets = []
    for i in range(15):
        asset_id = f'five-asset-{i}'
        checksum = f'five-sum-{i}'
        registry.register(account_id='1046241194533786', asset_id=asset_id, checksum=checksum, vertical_video_id=f'five-v{i}', square_video_id=f'five-s{i}', ready=True)
        assets.append({'asset_id': asset_id, 'checksum': checksum})
    payload = build_cpv_manifest(
        registry=registry, asset_refs=assets, campaign_numbers=[14, 15, 16, 17, 18],
        operational_date='2026-08-21', request_id='cpv-five', status='ACTIVE',
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
    assert [call['stage'] for call in transport.calls] == ['pure_clone_copy', 'consolidated_readback']
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
    updates = transport.operations_by_stage['campaign_update_adset_copy']
    campaign_update = next(op for op in updates if op.kind == 'campaign_update')
    assert campaign_update.body['status'] == 'ACTIVE'
    assert result['status'] == 'COMPLETE_FUTURE_ACTIVE'


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
    assert audit['manual_reconciliation_required'] is True
    with pytest.raises(ExecutionFailed, match='reconciliation'):
        CampaignEngine(cfg, transport_factory=lambda account: FakeBatchTransport(account)).execute(m)


def test_forty_campaigns_three_accounts_produce_seven_global_waves():
    rows = [pure_campaign(i, str(100 + (i % 3))) for i in range(40)]
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(manifest(rows, request_id='forty'))
    assert plan.global_wave_count == 7
    assert max(plan.campaigns_per_global_wave) <= 6
    assert sum(plan.campaigns_per_global_wave) == 40
