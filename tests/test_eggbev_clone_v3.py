from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.eggbev_clone import duplicate_names, next_midnight_et
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.planning import Planner
from ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from ares_campaign_v3.schema import Manifest, ManifestError


ACCOUNT_ID = '1034081997659047'


def future_midnight() -> str:
    return next_midnight_et(datetime.now(ZoneInfo('America/New_York'))).isoformat()


def manifest_payload(campaign: dict, request_id: str = 'eggbev-clone-test') -> dict:
    return {
        'schema_version': 3,
        'request_id': request_id,
        'operation': 'Eggbev-US-CC-EN-BOT',
        'graph_version': 'v26.0',
        'created_at': datetime.now(ZoneInfo('UTC')).isoformat(),
        'campaigns': [campaign],
    }


def media(index: int) -> dict:
    return {
        'asset_id': f'asset-{index}',
        'checksum': f'checksum-{index}',
        'vertical_video_id': f'vertical-{index}',
        'square_video_id': f'square-{index}',
        'ready': True,
        'upload_edge': 'ad_account_advideos',
        'association_verified': True,
    }


def creative_payload(index: int, page_id: str = 'target-page') -> dict:
    return {
        'name': f'Creative {index}',
        'object_story_spec': {
            'page_id': page_id,
            'link_data': {
                'message': 'Original primary text',
                'name': 'Original headline',
                'description': 'Original description',
                'call_to_action': {'type': 'LEARN_MORE'},
            },
        },
        'url_tags': 'utm_campaign=pg_12345',
    }


class EggbevCloneV3Tests(unittest.TestCase):
    def test_duplicate_names_keep_original_base_and_increment(self):
        self.assertEqual(
            duplicate_names('123 - Lauren Tucker - ENG - US', 3),
            [
                '123 - Lauren Tucker - ENG - US DUP01',
                '123 - Lauren Tucker - ENG - US DUP02',
                '123 - Lauren Tucker - ENG - US DUP03',
            ],
        )
        self.assertEqual(
            duplicate_names('123 - Lauren Tucker - ENG - US DUP02', 2),
            [
                '123 - Lauren Tucker - ENG - US DUP03',
                '123 - Lauren Tucker - ENG - US DUP04',
            ],
        )

    def test_next_midnight_et_is_next_calendar_day_and_active_future(self):
        now = datetime(2026, 8, 29, 22, 15, tzinfo=ZoneInfo('America/New_York'))
        self.assertEqual(next_midnight_et(now).isoformat(), '2026-08-30T00:00:00-04:00')

    def test_clone_prestaged_accepts_five_ads(self):
        campaign = {
            'idempotency_key': 'five-ads',
            'app_key': 'mgs-meta-app-current',
            'account_id': ACCOUNT_ID,
            'mode': 'clone_prestaged',
            'source_campaign_id': 'source-campaign',
            'source_adset_id': 'source-adset',
            'name': 'Source DUP01',
            'adset_name': 'AdG1',
            'start_time': future_midnight(),
            'status': 'ACTIVE',
            'campaign_updates': {'daily_budget': '4500'},
            'ads': [
                {
                    'name': f'Ad {index}',
                    'source_ad_id': f'source-ad-{index}',
                    'media': media(index),
                    'creative_payload': creative_payload(index),
                }
                for index in range(1, 6)
            ],
        }
        parsed = Manifest.from_dict(manifest_payload(campaign)).campaigns[0]
        self.assertEqual(len(parsed.ads), 5)

    def test_clone_page_switch_accepts_source_ads_without_new_media(self):
        campaign = {
            'idempotency_key': 'page-switch',
            'app_key': 'mgs-meta-app-current',
            'account_id': ACCOUNT_ID,
            'mode': 'clone_page_switch',
            'source_campaign_id': 'source-campaign',
            'source_adset_id': 'source-adset',
            'name': 'Source DUP01',
            'adset_name': 'AdG1',
            'start_time': future_midnight(),
            'status': 'ACTIVE',
            'campaign_updates': {'daily_budget': '4500'},
            'ads': [
                {
                    'name': f'Ad {index}',
                    'source_ad_id': f'source-ad-{index}',
                    'creative_payload': creative_payload(index, page_id='new-page'),
                }
                for index in range(1, 4)
            ],
        }
        payload = manifest_payload(campaign)
        parsed = Manifest.from_dict(payload).campaigns[0]
        self.assertEqual(parsed.mode, 'clone_page_switch')
        self.assertTrue(all(ad.media is None for ad in parsed.ads))

        registry = MediaRegistry(ROOT / 'work' / 'test-empty-media-registry.json')
        sealed = prevalidate_payload(payload, registry)
        self.assertTrue(sealed['prevalidated'])
        self.assertIn('source_ad_lineage', sealed['prevalidation']['checks'])
        self.assertNotIn('media_registry_exact', sealed['prevalidation']['checks'])

        stages = Planner(bundle_size=2, max_ads_per_batch=10).build(Manifest.from_dict(sealed)).lanes[ACCOUNT_ID][0].stages
        self.assertEqual(
            [stage.name for stage in stages],
            ['campaign_copy', 'adset_copy', 'campaign_adset_update', 'ad_copy_with_creative', 'ad_name_update', 'consolidated_readback'],
        )

    def test_pure_clone_has_exact_name_and_manager_selected_budget_update(self):
        campaign = {
            'idempotency_key': 'pure-clone',
            'app_key': 'mgs-meta-app-current',
            'account_id': ACCOUNT_ID,
            'mode': 'pure_clone',
            'source_campaign_id': 'source-campaign',
            'name': 'Original Campaign DUP01',
            'start_time': future_midnight(),
            'status': 'ACTIVE',
            'campaign_updates': {'daily_budget': '5500'},
        }
        bundle = Planner(bundle_size=2, max_ads_per_batch=10).build(Manifest.from_dict(manifest_payload(campaign))).lanes[ACCOUNT_ID][0]
        self.assertEqual([stage.name for stage in bundle.stages], ['pure_clone_copy', 'pure_clone_update', 'consolidated_readback'])
        update = bundle.stages[1].operations[0]
        self.assertEqual(update.body, {
            'name': 'Original Campaign DUP01',
            'daily_budget': '5500',
            'start_time': campaign['start_time'],
            'status': 'ACTIVE',
        })

    def test_eggbev_account_prompt_and_operation_are_installed(self):
        config = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/config.json').read_text())
        self.assertIn(ACCOUNT_ID, config['accounts'])
        self.assertEqual(config['accounts'][ACCOUNT_ID]['alias'], 'Eggbev-US-CC-EN-01-G006')
        self.assertIn('clone_page_switch', config['supported_modes'])
        self.assertTrue((ROOT / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json').exists())
        self.assertTrue((ROOT / 'data/ares/discord/thread-prompts/1543333373945053184.txt').exists())

    def test_account_policy_accepts_active_midnight_dup_with_budget(self):
        config = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/config.json').read_text())
        campaign = {
            'idempotency_key': 'policy-valid',
            'app_key': 'mgs-meta-app-current',
            'account_id': ACCOUNT_ID,
            'mode': 'pure_clone',
            'source_campaign_id': 'source-campaign',
            'name': 'Original Campaign DUP01',
            'start_time': future_midnight(),
            'status': 'ACTIVE',
            'campaign_updates': {'daily_budget': '4500'},
        }
        validate_account_policy(Manifest.from_dict(manifest_payload(campaign)), config)

    def test_account_policy_blocks_wrong_name_missing_budget_and_wrong_time(self):
        config = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/config.json').read_text())
        base = {
            'idempotency_key': 'policy-invalid',
            'app_key': 'mgs-meta-app-current',
            'account_id': ACCOUNT_ID,
            'mode': 'pure_clone',
            'source_campaign_id': 'source-campaign',
            'name': 'Original Campaign DUP01',
            'start_time': future_midnight(),
            'status': 'ACTIVE',
            'campaign_updates': {'daily_budget': '4500'},
        }

        wrong_name = json.loads(json.dumps(base))
        wrong_name['name'] = 'Original Campaign'
        with self.assertRaisesRegex(ManifestError, 'naming policy'):
            validate_account_policy(Manifest.from_dict(manifest_payload(wrong_name)), config)

        no_budget = json.loads(json.dumps(base))
        no_budget['campaign_updates'] = {}
        with self.assertRaisesRegex(ManifestError, 'daily_budget'):
            validate_account_policy(Manifest.from_dict(manifest_payload(no_budget)), config)

        wrong_time = json.loads(json.dumps(base))
        wrong_time['start_time'] = next_midnight_et(datetime.now(ZoneInfo('America/New_York'))).replace(hour=1).isoformat()
        with self.assertRaisesRegex(ManifestError, '00:00'):
            validate_account_policy(Manifest.from_dict(manifest_payload(wrong_time)), config)


if __name__ == '__main__':
    unittest.main()
