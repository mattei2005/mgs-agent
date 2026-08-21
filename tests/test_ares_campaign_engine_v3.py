from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path('/root/mgs-agent')
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.adapters import build_cpv_manifest
from ares_campaign_v3.engine import CampaignEngine, EngineDisabled
from ares_campaign_v3.media_registry import MediaRegistry, MediaNotReady
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


def test_media_registry_roundtrip_and_fail_closed(tmp_path):
    registry = MediaRegistry(tmp_path / 'media.json')
    registry.register(account_id='100', asset_id='asset-1', checksum='sum-1', vertical_video_id='v1', square_video_id='s1', ready=True)
    assert registry.require_ready('100', 'asset-1', 'sum-1')['vertical_video_id'] == 'v1'
    with pytest.raises(MediaNotReady):
        registry.require_ready('100', 'missing', 'sum-x')


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
    )
    built = Manifest.from_dict(payload)
    assert len(built.campaigns) == 2
    assert all(c.mode == 'clone_prestaged' for c in built.campaigns)
    assert all(c.status == 'PAUSED' for c in built.campaigns)
    assert [len(c.ads) for c in built.campaigns] == [3, 3]
    assert all(c.start_time.endswith('-03:00') for c in built.campaigns)
    assert 'b01fb13c14' in json.dumps(built.campaigns[0].ads[0].creative_payload)
    assert 'b01fb13c15' in json.dumps(built.campaigns[1].ads[0].creative_payload)
    assert 'b01fb13c08' not in json.dumps(payload)
    assert 'source_ad_id' not in built.campaigns[0].ads[0].creative_payload
    assert 'creative_payload' not in built.campaigns[0].ads[0].creative_payload


def test_engine_refuses_execute_while_disabled(tmp_path):
    engine = CampaignEngine(config(tmp_path), transport_factory=lambda account: FakeBatchTransport(account))
    with pytest.raises(EngineDisabled):
        engine.execute(manifest([pure_campaign(1)]))


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


def test_forty_campaigns_three_accounts_produce_seven_global_waves():
    rows = [pure_campaign(i, str(100 + (i % 3))) for i in range(40)]
    plan = Planner(bundle_size=2, max_ads_per_batch=10).build(manifest(rows, request_id='forty'))
    assert plan.global_wave_count == 7
    assert max(plan.campaigns_per_global_wave) <= 6
    assert sum(plan.campaigns_per_global_wave) == 40
