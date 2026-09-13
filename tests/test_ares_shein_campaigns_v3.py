from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path('/root/mgs-agent')
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.quota import LaneQuotaStore
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.shein import (
    SHEIN_ACCOUNT_ID,
    SheinManifestError,
    build_clone_prestaged_manifest,
    build_from_zero_manifest,
    build_pure_clone_manifest,
    next_campaign_numbers,
)


def future_start() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=1)).astimezone(
        timezone(timedelta(hours=-4))
    ).replace(hour=0, minute=10, second=0, microsecond=0).isoformat()


def source_campaign(number: int, *, budget: str = '3000') -> dict:
    return {
        'id': f'campaign-{number}',
        'name': f'{number} - PRODUTOS SHEIN - US-EN (b01fb03c{number:03d}) event_add_to_wishlist',
        'daily_budget': budget,
        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
        'objective': 'OUTCOME_SALES',
        'buying_type': 'AUCTION',
    }


def source_adset(number: int) -> dict:
    return {
        'id': f'adset-{number}',
        'name': f'01 - ADGROUP - VIDEOS (b01fb03c{number:03d}g01)',
        'billing_event': 'IMPRESSIONS',
        'optimization_goal': 'OFFSITE_CONVERSIONS',
        'targeting': {
            'age_min': 18,
            'age_max': 65,
            'geo_locations': {
                'countries': ['US'],
                'location_types': ['frequently_in', 'home', 'recent'],
            },
            'targeting_automation': {'advantage_audience': 1},
        },
        'attribution_spec': [
            {'event_type': 'CLICK_THROUGH', 'window_days': 7},
            {'event_type': 'VIEW_THROUGH', 'window_days': 1},
        ],
        'promoted_object': {
            'pixel_id': '1049581090103163',
            'custom_event_type': 'ADD_TO_WISHLIST',
            'smart_pse_enabled': False,
        },
        'regional_regulated_categories': ['VOLUNTARY_VERIFICATION'],
        'regional_regulation_identities': {
            'universal_beneficiary': '1773412024030451',
            'universal_payer': '1773412024030451',
        },
        'is_dynamic_creative': False,
    }


def source_ad(slot: int, *, campaign_number: int = 34, upstream: str | None = None) -> dict:
    return {
        'id': f'ad-{campaign_number}-{slot}',
        'name': f'VIDEO - {slot:02d}',
        'source_ad_id': upstream or f'upstream-{campaign_number}-{slot}',
        'creative': {
            'id': f'creative-{campaign_number}-{slot}',
            'effective_object_story_id': f'410983488769165_post-{campaign_number}-{slot}',
            'object_story_spec': {
                'page_id': '410983488769165',
                'instagram_user_id': '17841469509077092',
                'video_data': {
                    'video_id': f'source-video-{campaign_number}-{slot}',
                    'title': 'CLICK HERE ✅',
                    'message': '😱 SHEIN PRODUCTS FREE\n✔️ NO EXTRA COSTS OR FEES.',
                    'call_to_action': {
                        'type': 'GET_OFFER_VIEW',
                        'value': {
                            'link': (
                                'https://yolokfx.com/quiz/us/sh2-g005/'
                                f'?utm_source=facebook&utm_medium=g005-s'
                                f'&utm_campaign=b01fb03c{campaign_number:03d}'
                                f'&utm_adgroup=b01fb03c{campaign_number:03d}g01'
                            )
                        },
                    },
                    'image_url': 'https://example.test/old-thumbnail.jpg',
                    'image_hash': 'old-image-hash',
                },
            },
            'degrees_of_freedom_spec': {
                'creative_features_spec': {
                    'advantage_plus_creative': {'enroll_status': 'OPT_OUT'},
                    'standard_enhancements': {'enroll_status': 'OPT_IN'},
                }
            },
            'media_sourcing_spec': {
                'videos': [
                    {
                        'video_id': f'source-video-{campaign_number}-{slot}',
                        'original_video_id': f'source-video-{campaign_number}-{slot}',
                        'source': 'multi_media',
                        'opt_in_status': 'opt_in',
                        'thumbnail_source': 'generated_default',
                        'thumbnail_url': 'https://example.test/old-thumbnail.jpg',
                    }
                ]
            },
        },
    }


def media(slot: int, *, product: str) -> dict:
    return {
        'asset_id': f'asset-{product}-{slot}',
        'checksum': f'checksum-{product}-{slot}',
        'canonical_filename': f'SHEIN_US_EN_VID_FREE_{product}_PV_{slot:03d}.mp4',
        'vertical_video_id': f'new-video-{product}-{slot}',
        'square_video_id': f'new-square-{product}-{slot}',
        'ready': True,
        'upload_edge': 'ad_account_advideos',
        'association_verified': True,
        'thumbnail_url': f'https://example.test/{product}-{slot}.jpg',
    }


class SheinManifestTests(unittest.TestCase):
    def test_next_numbers_are_allocated_from_live_maximum(self):
        rows = [source_campaign(34), source_campaign(40), {'id': 'x', 'name': 'not numbered'}]
        self.assertEqual(next_campaign_numbers(rows, 3), [41, 42, 43])
        with self.assertRaises(SheinManifestError):
            next_campaign_numbers([], 1)

    def test_pure_clone_uses_source_post_and_target_url_tags(self):
        manifest = build_pure_clone_manifest(
            request_id='req-pure',
            number=39,
            start_time=future_start(),
            source_campaign=source_campaign(34),
            source_adset=source_adset(34),
            source_ads=[source_ad(1), source_ad(2)],
        )
        parsed = Manifest.from_dict(manifest)
        campaign = parsed.campaigns[0]
        self.assertEqual(campaign.mode, 'pure_clone')
        self.assertEqual(campaign.source_campaign_id, 'campaign-34')
        self.assertEqual(campaign.campaign_updates['daily_budget'], '3000')
        for source, ad in zip([source_ad(1), source_ad(2)], campaign.ads):
            payload = ad.creative_payload
            self.assertEqual(ad.source_ad_id, source['id'])
            self.assertEqual(
                payload['object_story_id'],
                source['creative']['effective_object_story_id'],
            )
            self.assertNotIn('object_story_spec', payload)
            self.assertIn('utm_campaign=b01fb03c039', payload['url_tags'])
            self.assertIn('utm_adgroup=b01fb03c039g01', payload['url_tags'])
            self.assertNotIn('b01fb03c034', json.dumps(payload))
            self.assertNotIn('standard_enhancements', json.dumps(payload))

    def test_clone_new_media_normalizes_graph_v26_payload(self):
        assets = [media(i, product='MAKEUP_BAG') for i in range(1, 4)]
        sources = [
            source_ad(1, campaign_number=20, upstream='ad-19-1'),
            source_ad(2, campaign_number=20, upstream='ad-19-2'),
        ]
        manifest = build_clone_prestaged_manifest(
            request_id='req-clone',
            number=40,
            start_time=future_start(),
            source_campaign=source_campaign(20, budget='2500'),
            source_adset=source_adset(20),
            source_ads=sources,
            assets=assets,
            budget_minor=5000,
            product_label='MALETA DE MAQUIAGEM',
        )
        campaign = Manifest.from_dict(manifest).campaigns[0]
        self.assertEqual(campaign.mode, 'clone_prestaged')
        self.assertEqual(len(campaign.ads), 3)
        self.assertEqual(len({ad.source_ad_id for ad in campaign.ads}), 3)
        self.assertEqual(
            [ad.source_ad_id for ad in campaign.ads],
            ['ad-20-1', 'ad-20-2', 'ad-19-1'],
        )
        for asset, ad in zip(assets, campaign.ads):
            payload = ad.creative_payload
            video = payload['object_story_spec']['video_data']
            self.assertEqual(video['video_id'], asset['vertical_video_id'])
            self.assertEqual(video['image_url'], asset['thumbnail_url'])
            self.assertNotIn('image_hash', video)
            sourcing = payload['media_sourcing_spec']['videos']
            self.assertEqual(len(sourcing), 1)
            self.assertEqual(sourcing[0]['video_id'], video['video_id'])
            self.assertEqual(sourcing[0]['original_video_id'], video['video_id'])
            self.assertEqual(sourcing[0]['source'], 'multi_media')
            self.assertEqual(sourcing[0]['opt_in_status'], 'opt_in')
            self.assertNotIn('standard_enhancements', json.dumps(payload))
            self.assertIn('b01fb03c040', json.dumps(payload))

    def test_from_zero_forbids_source_ids_and_builds_three_direct_ads(self):
        assets = [media(i, product='PORTABLE_BLENDER') for i in range(1, 4)]
        manifest = build_from_zero_manifest(
            request_id='req-zero',
            number=38,
            start_time=future_start(),
            reference_campaign=source_campaign(34),
            reference_adset=source_adset(34),
            copy_source_ad=source_ad(1),
            assets=assets,
            budget_minor=5000,
            product_label='LIQUIDIFICADOR',
        )
        campaign = Manifest.from_dict(manifest).campaigns[0]
        self.assertEqual(campaign.mode, 'from_zero_prestaged')
        self.assertIsNone(campaign.source_campaign_id)
        self.assertIsNone(campaign.source_adset_id)
        self.assertEqual(campaign.campaign_create['daily_budget'], '5000')
        self.assertEqual(len(campaign.ads), 3)
        self.assertTrue(all(ad.source_ad_id is None for ad in campaign.ads))
        self.assertTrue(all('media_sourcing_spec' not in ad.creative_payload for ad in campaign.ads))


class QuotaTierPersistenceTests(unittest.TestCase):
    def test_empty_write_headers_do_not_erase_known_standard_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LaneQuotaStore(tmp, soft_score=100, hard_score=120, window_seconds=300)
            lane = ('mgs-app', SHEIN_ACCOUNT_ID)
            standard = json.dumps({
                SHEIN_ACCOUNT_ID: [
                    {
                        'type': 'ads_insights',
                        'call_count': 1,
                        'ads_api_access_tier': 'standard_access',
                    }
                ]
            })
            first = store.observe_headers(
                lane,
                {'X-Business-Use-Case-Usage': standard},
                now=1000,
            )
            self.assertEqual(first['ads_api_access_tier'], 'standard_access')
            second = store.observe_headers(lane, {}, now=1001)
            self.assertEqual(second['ads_api_access_tier'], 'standard_access')
            reservation = store.reserve(lane, 500, request_id='fast-recovery', now=1002)
            self.assertEqual(reservation['hard_score'], 9000)
            self.assertEqual(reservation['ads_api_access_tier'], 'standard_access')


class SheinRunnerTests(unittest.TestCase):
    def test_offline_smoke_builds_all_three_modes_without_network_or_writes(self):
        script = ROOT / 'scripts/ares-shein-campaigns.py'
        spec = importlib.util.spec_from_file_location('ares_shein_campaigns_test', script)
        if spec is None or spec.loader is None:
            self.fail('SHEIN runner module could not be loaded')
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'smoke.json'
            result = runner.offline_smoke(output)
            self.assertEqual(result['status'], 'OFFLINE_SMOKE_OK')
            self.assertEqual(result['engine_version'], 3)
            self.assertEqual(result['campaigns'], 3)
            self.assertEqual(result['ads'], 8)
            self.assertEqual(result['network_calls'], 0)
            self.assertEqual(result['writes'], 0)
            self.assertEqual(
                result['modes'],
                ['from_zero_prestaged', 'pure_clone', 'clone_prestaged'],
            )
            payload = json.loads(output.read_text())
            self.assertEqual(len(payload['manifests']), 3)
            self.assertTrue(all(item['prevalidated'] is True for item in payload['manifests']))


if __name__ == '__main__':
    unittest.main()
