"""Offline regression for the account-scoped SHEIN single-clone adapter."""
import copy
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_single_clone as route

ACCOUNT = '7840111366055613'
PAGE = '1187478564456307'


def fixture():
    request = {'request_id': 'unit-single-01', 'account': 'Yolokfx-US-SHEIN-EN-01-G002',
               'source_number': 110, 'budget_usd': '30', 'start_time': '2030-10-08T00:00:00-04:00',
               'status': 'PAUSED', 'authorized_by': '344196393512075265',
               'source_thread_id': '1557274000680288307'}
    source = {'campaign': {'id': '11001', 'account_id': ACCOUNT,
                          'name': '110 - TURBO BLOWER [LP NORMAL] 07/10 - US-EN (b01fb01c110) event_add_to_wishlist',
                          'daily_budget': '4000', 'bid_strategy': 'LOWEST_COST_WITHOUT_CAP', 'objective': 'OUTCOME_SALES'},
              'adset': {'id': '11002', 'name': '01 - ADGROUP - VIDEOS (b01fb01c110g01)',
                        'optimization_goal': 'OFFSITE_CONVERSIONS', 'billing_event': 'IMPRESSIONS',
                        'is_dynamic_creative': False, 'attribution_spec': [{'event_type': 'CLICK_THROUGH', 'window_days': 7}],
                        'promoted_object': {'pixel_id': '1049581090103163', 'custom_event_type': 'ADD_TO_WISHLIST'},
                        'targeting': {'age_min': 18, 'age_max': 65, 'age_range': [18, 65],
                                      'user_age_unknown': True, 'geo_locations': {'countries': ['US']},
                                      'targeting_automation': {'advantage_audience': 1, 'individual_setting': {'age': 1, 'gender': 1}}}},
              'ads': [{'id': '11003', 'name': 'AD - 1', 'adset_id': '11002', 'status': 'ACTIVE',
                       'creative': {'id': '11004', 'effective_object_story_id': PAGE + '_123',
                                    'object_story_spec': {'page_id': PAGE, 'video_data': {'video_id': '11005',
                                        'message': 'FREE TURBO BLOWER', 'call_to_action': {'type': 'GET_OFFER_VIEW', 'value': {
                                            'link': 'https://yolokfx.com/quiz/us/sh2-g002/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b01fb01c110&utm_adgroup=b01fb01c110g01'}}}}}}]}
    cfg = {'alias': request['account'], 'app_key': 'mgs-meta-app-1299247318762949', 'operation': 'SHEIN-US-DIRECT',
           'timezone': 'America/New_York', 'supported_modes': ['pure_clone'], 'token_user_id': '122095869861482193'}
    return request, source, cfg


def live_fixture(manifest, source):
    c = manifest['campaigns'][0]
    adset = copy.deepcopy(source['adset'])
    adset.update(id='target-set', name=c['adset_name'], status='PAUSED', start_time=c['start_time'])
    return {'campaign': {'id': 'target-campaign', 'account_id': ACCOUNT, 'name': c['name'], 'status': 'PAUSED',
                         'effective_status': 'PAUSED', 'start_time': c['start_time'], **c['campaign_updates']},
            'adsets': {'data': [adset]},
            'ads': {'data': [{'id': 'target-ad', 'adset_id': 'target-set', 'name': c['ads'][0]['name'], 'status': 'PAUSED',
                              'source_ad_id': c['ads'][0]['source_ad_id'], 'creative': {
                                  'object_story_id': c['ads'][0]['creative_payload']['object_story_id'],
                                  'effective_object_story_id': c['ads'][0]['creative_payload']['object_story_id'],
                                  'url_tags': c['ads'][0]['creative_payload']['url_tags']}}]}}


class SingleCloneTests(unittest.TestCase):
    def test_discord_clock_uses_real_message_snowflake_not_runner_start(self):
        r, _, _ = fixture()
        from datetime import datetime, timezone
        expected = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
        r['source_message_id'] = str((int(expected.timestamp() * 1000) - 1420070400000) << 22)
        timestamp, basis = route.request_clock(r)
        self.assertEqual(timestamp, expected)
        self.assertEqual(basis, 'Discord message creation to readback')

    def test_clock_distinguishes_receipt_and_missing_metadata(self):
        r, _, _ = fixture()
        self.assertEqual(route.request_clock(r), (None, 'runner start to readback; message timestamp unavailable'))
        r['request_received_at'] = '2026-10-08T00:00:00+00:00'
        self.assertEqual(route.request_clock(r)[1], 'gateway request receipt to readback')
        r['source_message_id'] = 'invalid-id'
        with self.assertRaises(ValueError): route.validate_request(r)

    def test_budget_exact_cents(self):
        self.assertEqual(route.budget_minor('30'), 3000)
        self.assertEqual(route.budget_minor('30.01'), 3001)
        for value in ['30.001', '-1', '0', 'nan', 'inf']:
            with self.assertRaises(ValueError): route.budget_minor(value)

    def test_one_mode_correct_account_names_and_tracking(self):
        r, s, cfg = fixture()
        p = route.build_manifest(r, s, 114, cfg)
        c = p['campaigns'][0]
        self.assertEqual(c['account_id'], ACCOUNT)
        self.assertEqual(c['name'], '114 - TURBO BLOWER [LP NORMAL] - US-EN (b01fb01c114) 08/10 event_add_to_wishlist COPY C110')
        self.assertNotIn('adset_updates', c)
        self.assertNotIn('media', c['ads'][0])
        self.assertEqual(c['status'], 'PAUSED')
        self.assertEqual(c['campaign_updates']['daily_budget'], '3000')
        self.assertIn('utm_medium=g002-s', c['ads'][0]['creative_payload']['url_tags'])
        self.assertIn('utm_campaign=b01fb01c114', c['ads'][0]['creative_payload']['url_tags'])
        self.assertNotIn('c110', c['ads'][0]['creative_payload']['url_tags'])
        self.assertEqual(c['ads'][0]['source_ad_id'], s['ads'][0]['id'])
        self.assertEqual(c['ads'][0]['creative_payload']['object_story_id'], PAGE + '_123')

    def test_source_date_after_token(self):
        r, s, cfg = fixture()
        s['campaign']['name'] = '110 - HAIRBRUSH audio new [LP NORMAL] - US-EN (b01fb01c110) 22/09 event_add_to_wishlist'
        name = route.build_manifest(r, s, 114, cfg)['campaigns'][0]['name']
        self.assertIn('(b01fb01c114) 08/10', name)
        self.assertNotIn('22/09', name)

    def test_copied_source_replaces_previous_lineage_marker(self):
        r, s, cfg = fixture()
        s['campaign']['name'] += ' COPY C108'
        name = route.build_manifest(r, s, 114, cfg)['campaigns'][0]['name']
        self.assertTrue(name.endswith('COPY C110'))
        self.assertEqual(name.count('COPY C'), 1)

    def test_request_scope_and_authority_fail_closed(self):
        for key, value in [('account', 'other-account'), ('status', 'ACTIVE'), ('authorized_by', 'other-user'),
                           ('request_id', '../escape'), ('start_time', '2030-10-08T00:00:00')]:
            r, s, cfg = fixture(); r[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): route.build_manifest(r, s, 114, cfg)

    def test_wrong_event_account_tracking_and_destination_rejected(self):
        for change in ['event', 'account', 'url', 'tracking', 'post']:
            r, s, cfg = fixture()
            if change == 'event': s['adset']['promoted_object']['custom_event_type'] = 'PURCHASE'
            if change == 'account': s['campaign']['account_id'] = 'wrong'
            if change == 'url': s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value']['link'] = 'https://example.test/'
            if change == 'tracking': s['campaign']['name'] = s['campaign']['name'].replace('b01fb01c110', 'b01fb03c110')
            if change == 'post': s['ads'][0]['creative']['effective_object_story_id'] = 'another-page_123'
            with self.subTest(change=change), self.assertRaises(ValueError): route.build_manifest(r, s, 114, cfg)

    def test_readback_exact(self):
        r, s, cfg = fixture(); p = route.build_manifest(r, s, 114, cfg)
        self.assertEqual(route.verify_readback(p, s, live_fixture(p, s)), [])

    def test_known_optional_flag_difference_is_reported_not_written(self):
        r, s, cfg = fixture(); p = route.build_manifest(r, s, 114, cfg); live = live_fixture(p, s)
        live['adsets']['data'][0]['targeting']['targeting_automation'].pop('individual_setting')
        self.assertEqual(len(route.verify_readback(p, s, live)), 1)
        self.assertTrue(live['adsets']['data'][0]['targeting']['user_age_unknown'])

    def test_other_readback_drift_fails(self):
        for change in ['budget', 'status', 'schedule', 'audience', 'post', 'lineage', 'tags', 'count', 'issues']:
            r, s, cfg = fixture(); p = route.build_manifest(r, s, 114, cfg); live = live_fixture(p, s)
            if change == 'budget': live['campaign']['daily_budget'] = '4500'
            if change == 'status': live['campaign']['status'] = 'ACTIVE'
            if change == 'schedule': live['adsets']['data'][0]['start_time'] = '2030-10-08T00:10:00-04:00'
            if change == 'audience': live['adsets']['data'][0]['targeting']['age_min'] = 25
            if change == 'post': live['ads']['data'][0]['creative']['effective_object_story_id'] = PAGE + '_456'
            if change == 'lineage': live['ads']['data'][0]['source_ad_id'] = 'wrong'
            if change == 'tags': live['ads']['data'][0]['creative']['url_tags'] = 'utm_campaign=old'
            if change == 'count': live['ads']['data'].append(copy.deepcopy(live['ads']['data'][0]))
            if change == 'issues': live['ads']['data'][0]['issues_info'] = [{'error': 'test'}]
            with self.subTest(change=change), self.assertRaises(ValueError): route.verify_readback(p, s, live)

    def test_social_uses_page_identity_once_and_never_corporate_post_query(self):
        common = Mock()
        common.graph_get.return_value = (200, {'id': PAGE, 'name': 'Page', 'access_token': 'OFFLINE_PAGE_TOKEN'}, {})
        common.graph_batch_get.return_value = (200, [{'name': 'post-1', 'code': 200, 'body': {
            'id': PAGE + '_123', 'reactions': {'summary': {'total_count': 2}}, 'comments': {'summary': {'total_count': 0}}}}], {})
        out = route.read_social(common, 'OFFLINE_CORPORATE_TOKEN', PAGE, [PAGE + '_123', PAGE + '_123'])
        self.assertEqual(common.graph_get.call_count, 1)
        self.assertEqual(common.graph_batch_get.call_args.args[0], 'OFFLINE_PAGE_TOKEN')
        self.assertIsNone(out[0]['shares'])
        self.assertNotIn('OFFLINE_PAGE_TOKEN', json.dumps(out))

    def test_social_reuses_memory_token_and_rejects_mixed_pages(self):
        common = Mock(); common.graph_batch_get.return_value = (200, [{'name': 'post-1', 'code': 200, 'body': {'id': PAGE + '_123'}}], {})
        route.read_social(common, 'CORPORATE', PAGE, [PAGE + '_123'], page_token='PAGE_TOKEN')
        common.graph_get.assert_not_called()
        with self.assertRaises(ValueError): route.read_social(common, 'CORPORATE', PAGE, ['other_123'])


class CoreIntegrationTests(unittest.TestCase):
    def test_new_manifest_executes_via_real_engine_with_offline_transport_and_replays(self):
        from ares_campaign_v3.engine import CampaignEngine
        from ares_campaign_v3.transport import FakeBatchTransport
        r, source, account = fixture()
        account.update(ad_serving_route='lineage_required_for_new_media', marketing_api_access_tier='standard_access',
                       pure_clone_tracking_required=True, campaign_policy={'by_mode': {'pure_clone': {
                           'pure_clone_allowed_update_keys': ['daily_budget', 'bid_strategy'],
                           'creative_materialization_route': 'existing_post_two_phase'}}})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {'enabled': True, 'write_enabled': True, 'require_account_registration': True,
                      'accounts': {ACCOUNT: account}, 'state_root': str(root / 'state'), 'audit_root': str(root / 'audit')}
            payload = route.build_manifest(r, source, 114, account)
            payload = route.prevalidate_payload(payload, route.MediaRegistry(root / 'registry.json'))
            engine = CampaignEngine(config, transport_factory=lambda account_id: FakeBatchTransport(account_id))
            first = engine.execute(route.Manifest.from_dict(payload))
            second = engine.execute(route.Manifest.from_dict(payload))
            self.assertEqual(first['status'], 'COMPLETE_PAUSED')
            self.assertEqual(len(first['campaign_ids']), 1)
            self.assertEqual(second['campaign_ids'], first['campaign_ids'])
            self.assertTrue(second['idempotent_replay'])


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.request, self.source, self.account = fixture()
        self.account['single_clone_runtime'] = {'enabled': True}
        self.account['token_item'] = 'OFFLINE_FAKE_CREDENTIAL_REFERENCE'
        self.account['ad_serving_route'] = 'lineage_required_for_new_media'
        self.account['campaign_policy'] = {'by_mode': {'pure_clone': {
            'pure_clone_allowed_update_keys': ['daily_budget', 'bid_strategy'],
            'creative_materialization_route': 'existing_post_two_phase'}}}
        self.config = {'enabled': True, 'write_enabled': True, 'accounts': {ACCOUNT: self.account},
                       'state_root': str(self.root / 'engine-state'), 'audit_root': str(self.root / 'engine-audit')}
        def put(name, value):
            target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value))
        put('data/authorized-users.json', {'agents': {'ares': {'authorized_user_discord_ids': [route.RODOLFO_ID]}}})
        put('data/ares/meta-ads/engine-v3/config.json', self.config)
        put('data/ares/meta-ads/operations/SHEIN-US-DIRECT.json', {'operation_id': 'SHEIN-US-DIRECT'})
        put('data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json', {
            'operation_id': 'SHEIN-US-DIRECT', 'snapshot_at_utc': '2030-01-01T00:00:00+00:00', 'account_count': 1,
            'accounts': [{'account_id': ACCOUNT, 'name': self.request['account'], 'manager_code': 'G002',
                          'channel_id': '1548149300826079333'}]})
        put('data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json', {'profiles': {ACCOUNT: {
            'account_id': ACCOUNT, 'account_name': self.request['account'], 'manager_code': 'G002',
            'manager_discord_id': '321263240782807040', 'channel_id': '1548149300826079333',
            'timezone': 'America/New_York', 'destination_base': 'https://yolokfx.com/quiz/us/sh2-g002/'}}})
        self.stack.enter_context(patch.object(route, 'BASE', self.root))
        self.stack.enter_context(patch('subprocess.run', return_value=Mock(returncode=0)))
        self.common = Mock()
        self.common.get_token_from_1password.return_value = ('OFFLINE_CORPORATE_TOKEN', 'offline')
        self.common.graph_get.return_value = (200, {'data': [{'id': '113', 'name': '113 - TEST'}]}, {})
        self.stack.enter_context(patch.object(route, '_load_common', return_value=self.common))
        draft = route.build_manifest(self.request, self.source, 114, self.account)
        self.manifest = route.prevalidate_payload(draft, route.MediaRegistry(self.root / 'registry.json'))
        prepared = {'source': self.source, 'account': {}, 'prerequisites': {}, 'number': 114,
                    'page_id': PAGE, 'manifest': self.manifest}
        self.prepare = self.stack.enter_context(patch.object(route, '_prepare', return_value=(prepared, 'OFFLINE_PAGE_TOKEN')))
        self.engine = Mock()
        self.engine.dry_run.return_value = {'plan': {'offline': True}}
        self.engine.execute.return_value = {'status': 'COMPLETE_PAUSED', 'campaign_ids': ['target-campaign']}
        self.stack.enter_context(patch.object(route, 'CampaignEngine', return_value=self.engine))
        live = live_fixture(self.manifest, self.source)
        live['budgets'] = {'data': [{'id': 'source', 'status': 'ACTIVE', 'daily_budget': '4000'},
                                    {'id': 'target', 'status': 'PAUSED', 'daily_budget': '3000'}]}
        self.readback = self.stack.enter_context(patch.object(route, '_readback', return_value=live))
        self.common.graph_batch_get.return_value = (200, [{'name': 'budgets', 'code': 200, 'body': live['budgets']}], {})
        self.media_qa = self.stack.enter_context(patch('ares_campaign_v3.shein_qa.verify_media', return_value={'verified': True}))
        self.social = self.stack.enter_context(patch.object(route, 'read_social', return_value=[{'post_id': PAGE + '_123', 'reactions': 2}]))

    def state(self):
        path = self.root / 'data/ares/meta-ads/state/shein-campaigns/single-clone' / self.request['request_id'] / 'state.json'
        return json.loads(path.read_text())

    def test_dry_run_never_executes_or_reads_target(self):
        out = route.run_request(self.request)
        self.assertEqual(out['status'], 'DRY_RUN_OK')
        self.assertEqual(out['campaign_writes'], 0)
        self.engine.execute.assert_not_called(); self.readback.assert_not_called()
        self.common.graph_post.assert_not_called()

    def test_execution_delegates_to_engine_and_readbacks(self):
        out = route.run_request(self.request, confirm_execute=True)
        self.assertEqual(out['status'], 'COMPLETE_PAUSED')
        self.assertEqual(out['request_active_budget_delta_usd'], 0)
        self.assertEqual(out['account_active_daily_budget_usd'], 40)
        self.assertEqual(self.engine.execute.call_count, 1)
        self.assertTrue(self.engine.execute.call_args.args[0].raw['prevalidated'])
        self.common.graph_post.assert_not_called()
        self.assertEqual(self.state()['phase'], 'COMPLETE_PAUSED')
        self.assertNotIn('OFFLINE_CORPORATE_TOKEN', json.dumps(self.state()))
        self.assertNotIn('OFFLINE_PAGE_TOKEN', json.dumps(self.state()))

    def test_completed_replay_only_revalidates_no_new_engine_write(self):
        route.run_request(self.request, confirm_execute=True)
        route.run_request(self.request, confirm_execute=True)
        self.assertEqual(self.engine.execute.call_count, 1)
        self.assertEqual(self.readback.call_count, 2)
        self.assertEqual(self.prepare.call_count, 1)

    def test_postprocess_failure_preserves_ids_and_resume_only_readbacks(self):
        self.readback.side_effect = RuntimeError('offline provider failure')
        with self.assertRaises(RuntimeError): route.run_request(self.request, confirm_execute=True)
        self.assertEqual(self.state()['phase'], 'POSTPROCESS_PENDING')
        self.assertEqual(self.state()['engine_result']['campaign_ids'], ['target-campaign'])
        self.readback.side_effect = None
        route.run_request(self.request, confirm_execute=True)
        self.assertEqual(self.engine.execute.call_count, 1)

    def test_engine_failure_preserves_manifest_for_core_recovery(self):
        self.engine.execute.side_effect = RuntimeError('offline engine failure')
        with self.assertRaises(RuntimeError): route.run_request(self.request, confirm_execute=True)
        failed = self.state()
        self.assertEqual(failed['phase'], 'RECOVERY_PENDING')
        self.engine.execute.side_effect = None
        route.run_request(self.request, confirm_execute=True)
        self.assertEqual(self.state()['manifest'], failed['manifest'])
        self.assertEqual(self.prepare.call_count, 1)

    def test_request_id_cannot_change_parameters(self):
        route.run_request(self.request)
        changed = {**self.request, 'budget_usd': '31'}
        with self.assertRaises(ValueError): route.run_request(changed, confirm_execute=True)
        self.engine.execute.assert_not_called()

    def test_slot_collision_never_executes(self):
        self.common.graph_get.return_value = (200, {'data': [{'id': '114', 'name': '114 - EXISTING'}]}, {})
        with self.assertRaises(ValueError): route.run_request(self.request, confirm_execute=True)
        self.engine.execute.assert_not_called()

    def test_catalog_lookup_exact_and_cross_manager_rejected(self):
        out = route.lookup_account(self.request['account'], manager_code='G002', channel_id='1548149300826079333')
        self.assertEqual(out['account_id'], ACCOUNT)
        with self.assertRaises(ValueError): route.lookup_account(self.request['account'], manager_code='G001')
        with self.assertRaises(ValueError): route.lookup_account(self.request['account'], channel_id='another-channel')
        with self.assertRaises(ValueError): route.lookup_account('Yolokfx')


class BatchPipelineTests(unittest.TestCase):
    request: dict
    account: dict
    config: dict
    source: dict
    root: Path
    prepare: Mock
    engine: Mock
    readback: Mock
    def setUp(self):
        PipelineTests.setUp(self)  # type: ignore[arg-type] -- shared offline fixture only
        self.request.update(status='ACTIVE', quantity=2)
        self.account['shein_profile'] = {'account_id': ACCOUNT, 'account_name': self.request['account'], 'manager_code': 'G002',
            'manager_discord_id': '321263240782807040', 'channel_id': '1548149300826079333', 'language': 'EN',
            'timezone': 'America/New_York', 'tracking_prefix': 'b01fb01', 'utm_medium': 'g002-s',
            'destination_base': 'https://yolokfx.com/quiz/us/sh2-g002/', 'page_id': PAGE}
        self.config['shein_batch_activation'] = {'enabled': True}
        (self.root / 'data/ares/meta-ads/engine-v3/config.json').write_text(json.dumps(self.config))
        draft = route.build_manifest(self.request, self.source, 114, self.account)
        creation, target, barrier = route.seal_creation_pair(draft, self.config, route.MediaRegistry(self.root / 'registry.json'))
        self.prepare.return_value = ({'source': self.source, 'account': {}, 'prerequisites': {}, 'number': 114,
            'page_id': PAGE, 'manifest': creation, 'target_manifest': target, 'batch_barrier': barrier}, 'OFFLINE_PAGE_TOKEN')
        self.engine.execute.return_value = {'status': 'COMPLETE_PAUSED', 'campaign_ids': ['target-0', 'target-1']}
        self.live = []
        for i, shell in enumerate(creation['campaigns']):
            tree = live_fixture({'campaigns': [shell]}, self.source)
            tree['campaign']['id'] = f'target-{i}'
            tree['adsets']['data'][0]['id'] = f'target-set-{i}'
            tree['ads']['data'][0].update(id=f'target-ad-{i}', adset_id=f'target-set-{i}')
            tree['budgets'] = {'data': []}
            self.live.append(tree)
        self.readback.side_effect = lambda common, token, cid: copy.deepcopy(self.live[int(cid[-1])])
        def activated(*args):
            self.assertEqual(self.readback.call_count, 2)
            self.assertTrue(all(node['status'] == 'PAUSED' for t in args[2]['trees'] for node in [t['campaign']] + t['adsets']['data'] + t['ads']['data']))
            for tree in self.live:
                for node in [tree['campaign']] + tree['adsets']['data'] + tree['ads']['data']:
                    node.update(status='ACTIVE', configured_status='ACTIVE')
                tree['campaign']['effective_status'] = 'ACTIVE'
            return {'status': 'COMPLETE_FUTURE_ACTIVE', 'campaign_ids': ['target-0', 'target-1']}
        self.engine.activate_verified.side_effect = activated

    def test_batch_creates_paused_then_only_after_global_qa_activates(self):
        out = route.run_request(self.request, confirm_execute=True)
        self.assertEqual(out['status'], 'COMPLETE_FUTURE_ACTIVE')
        self.assertTrue(all(c.status == 'PAUSED' for c in self.engine.execute.call_args.args[0].campaigns))
        self.assertEqual(self.engine.activate_verified.call_count, 1)
        self.assertEqual(len(out['campaigns']), 2)

    def test_failed_global_qa_never_calls_activation(self):
        self.live[1]['campaign']['daily_budget'] = '4000'
        with self.assertRaises(ValueError): route.run_request(self.request, confirm_execute=True)
        self.engine.activate_verified.assert_not_called()

    def test_single_active_creation_pair_unchanged(self):
        one = {**self.request, 'quantity': 1}
        draft = route.build_manifest(one, self.source, 114, self.account)
        creation, target, barrier = route.seal_creation_pair(draft, self.config, route.MediaRegistry(self.root / 'registry.json'))
        self.assertFalse(barrier)
        self.assertEqual(creation['campaigns'][0]['status'], 'ACTIVE')


if __name__ == '__main__':
    unittest.main()
