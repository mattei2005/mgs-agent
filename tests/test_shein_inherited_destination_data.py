"""OFFLINE: selected source URL is a Meta field, never a website capability."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_single_clone as driver, shein_general as general
from ares_campaign_v3 import shein_reference as ref, shein_grouped_media as media, shein_request_queue as queue


def fixture(mode='clone_prestaged'):
    r, s, a, assets = case(5, mode=mode)
    p = a['shein_profile']; old = p['destination_base']
    p['destination_base'] = 'https://destination.example/quiz/us/sh2-g006/'
    for ad in s['ads']:
        value = ad['creative']['object_story_spec']['video_data']['call_to_action']['value']
        value['link'] = value['link'].replace(old, p['destination_base'])
    s['campaign']['status'] = 'ACTIVE'
    s['adset']['status'] = 'ACTIVE'
    s['ads'][0]['status'] = 'ACTIVE'
    r.pop('_resolved_assets', None)
    return r, s, a, assets


class ReadTransport:
    def __init__(self, profile, source):
        self.p, self.s, self.calls = profile, source, []

    def graph_batch_get(self, token, requests):
        self.calls.extend(copy.deepcopy(requests))
        p, s = self.p, self.s
        bodies = {
            'account': dict(id='act_' + p['account_id'], name=p['account_name'], currency='USD',
                            timezone_name=p['timezone'], account_status=1, disable_reason=0, user_tasks=['ADVERTISE']),
            'identity': dict(id=driver.SYSTEM_USER_ID, client_business_id=driver.BUSINESS_ID),
            'campaigns': {'data': [s['campaign']]}, 'campaign': s['campaign'],
            'adsets': {'data': [s['adset']]}, 'ads': {'data': s['ads']},
            'video-source': dict(id='video-source', title='fixture', length=3, status='ready'),
            'page': dict(id=p['page_id'], access_token='OFFLINE_PAGE'),
            'assignment': {'data': [dict(id=driver.SYSTEM_USER_ID, tasks=['ADVERTISE'])]},
            'pixels': {'data': [dict(id=p['pixel_id'])]},
        }
        return 200, [dict(name=q['name'], code=200, body=copy.deepcopy(bodies[q['name']])) for q in requests], {}


class InheritedTests(unittest.TestCase):
    def test_selected_same_account_field_avoids_domain_gate_without_mutation(self):
        for mode in ('pure_clone', 'clone_prestaged'):
            r, s, a, _ = fixture(mode); p = a['shein_profile']; before = copy.deepcopy((r, s, p))
            with patch('subprocess.run', side_effect=AssertionError('no website checker')):
                driver.validate_request_destinations(r, p)
                driver.validate_inherited_source(r, p, s)
            self.assertEqual((r, s, p), before)

    def test_profile_only_or_implicit_template_is_still_domain_scoped(self):
        for r in ({}, {'mode': 'from_zero_prestaged', 'source_number': 110}, {'mode': 'site_admin', 'source_number': 110}):
            with patch('subprocess.run', return_value=SimpleNamespace(returncode=3)) as check:
                with self.assertRaises(driver.RouteBlocked):
                    driver.validate_request_destinations(r, {'destination_base': 'https://site.example/'})
                self.assertEqual(check.call_count, 1)
                self.assertIn('mgs-domain-scope.py', check.call_args.args[0][1])

    def test_invalid_reference_or_missing_authority_never_admitted(self):
        for field, value in [('authorized_by', 'UNAUTHORIZED'), ('source_channel_id', 'OTHER'), ('account', 'OTHER')]:
            r, s, a, _ = fixture(); r[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                driver.validate_request_destinations(r, a['shein_profile'])
        for number in (None, 0, -1, '1x', True):
            self.assertFalse(driver.inherited_destination_request({'source_number': number}))

    def test_live_channel_denial_stops_before_any_graph_read(self):
        r, s, a, _ = fixture(); p = a['shein_profile']
        p['channel_authorization_policy'] = dict(enabled=True, approved_by=ref.RODOLFO, channel_ids=[p['channel_id']])
        common = Mock()
        with patch('ares_campaign_v3.shein_channel_authority.verify', return_value={'verified': False}):
            with self.assertRaisesRegex(ValueError, 'authorization'):
                driver.preflight_inherited_destination(r, p, {}, common, 'OFFLINE')
        common.graph_batch_get.assert_not_called()

    def test_malformed_credentials_and_invalid_hosts_are_sanitized(self):
        for url in ('javascript:alert(1)', 'https:///missing', 'https://user:secret@destination.example/x',
                    'https://destination.example:bad/x', 'https://destination.example:0/',
                    'https://bad%2Fhost/x', 'https://-bad.example/x', 'https://a..example/x',
                    'https://destination.example\\@other.example/', 'https://destination.example/\x7f',
                    'https://destination.example/\npath'):
            r, s, a, _ = fixture(); s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value']['link'] = url
            with self.subTest(url=url), self.assertRaises(ValueError) as error:
                driver.validate_inherited_source(r, a['shein_profile'], s)
            self.assertNotIn(url, str(error.exception))

    def test_source_account_number_event_parent_and_tracking_fail_closed(self):
        for delta in ('account', 'number', 'event', 'parent', 'tracking', 'host', 'empty'):
            r, s, a, _ = fixture()
            if delta == 'account': s['campaign']['account_id'] = 'OTHER'
            if delta == 'number': s['campaign']['name'] = '999 - Other'
            if delta == 'event': s['adset']['promoted_object']['custom_event_type'] = 'PURCHASE'
            if delta == 'parent': s['ads'][0]['adset_id'] = 'OTHER'
            if delta == 'tracking': s['ads'][0]['creative']['url_tags'] = 'utm_campaign=WRONG'
            if delta == 'host': a['shein_profile']['destination_base'] = 'https://other.example/x/'
            if delta == 'empty': s['ads'] = []
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                driver.validate_inherited_source(r, a['shein_profile'], s)

    def test_source_preflight_only_never_loads_assets_or_seals_manifest(self):
        r, s, a, _ = fixture(); p = a['shein_profile']; common = ReadTransport(p, s); before = copy.deepcopy(s)
        cfg = {'accounts': {p['account_id']: a}}
        with patch.object(driver, 'seal_creation_pair', side_effect=AssertionError('no sealing')), \
             patch('ares_campaign_v3.shein_media_handoff.load_ready_assets', side_effect=AssertionError('no assets')):
            prepared = driver.preflight_inherited_destination(r, p, cfg, common, 'OFFLINE')
        self.assertEqual(prepared['source']['campaign']['id'], s['campaign']['id'])
        self.assertEqual(prepared['compiler_config']['shein_profile']['destination_base'], p['destination_base'])
        self.assertEqual([prepared[k] for k in ('campaign_writes', 'media_uploads', 'inventory_reservations')], [0, 0, 0])
        self.assertEqual(before, s)
        self.assertIsNone(driver.CURRENT_PROFILE.get())

    def test_wrong_live_source_account_rejected_before_video_or_assets(self):
        r, s, a, _ = fixture(); p = a['shein_profile']; s['campaign']['account_id'] = 'OTHER'
        common = ReadTransport(p, s)
        with self.assertRaisesRegex(ValueError, 'campaign/account'):
            driver.preflight_inherited_destination(r, p, {'accounts': {p['account_id']: a}}, common, 'OFFLINE')
        self.assertFalse(any(q['name'] == 'video-source' for q in common.calls))

    def test_new_tracking_per_number_and_original_location_with_source_immutable(self):
        for mode in ('pure_clone', 'clone_prestaged'):
            r, s, a, assets = fixture(mode); before = copy.deepcopy(s); r['quantity'] = 2
            if mode != 'pure_clone':
                r['_resolved_assets'] = assets[:2]
            shells = general.build(r, s, 114, a)['campaigns']
            for number, shell in zip((114, 115), shells):
                creative = shell['ads'][0]['creative_payload']
                effective = json.dumps(creative)
                self.assertIn(f"{a['shein_profile']['tracking_prefix']}c{number:03d}", effective)
                if mode == 'clone_prestaged':
                    link = creative['object_story_spec']['video_data']['call_to_action']['value']['link']
                    self.assertTrue(link.startswith(a['shein_profile']['destination_base'] + '?'))
                    self.assertIn(f'c{number:03d}g01', link)
                self.assertEqual(shell['source_campaign_id'], s['campaign']['id'])
            self.assertEqual(s, before)

    def test_eight_groups_fifteen_ads_preserve_literals_and_new_target_tokens(self):
        r, s, a, pool = fixture(); before = copy.deepcopy(s)
        counts = [3, 2, 2, 2, 3, 1, 1, 1]; groups = []; assets = []
        for i, count in enumerate(counts):
            filenames = []
            for j in range(count):
                item = copy.deepcopy(pool[0]); item.update(asset_id=f'asset-{i}-{j}', checksum=f'{i*5+j+1:064x}',
                    vertical_video_id=f'video-{i}-{j}', canonical_filename=f'SHEIN_US_EN_VID_PRODUCT_{i}_PV_{j+1:03d}.mp4')
                assets.append(item); filenames.append(item['canonical_filename'])
            groups.append(dict(files=filenames, product_label=f'PRODUCT {i}', primary_text=f'EXACT {i}', description='⭐⭐⭐⭐⭐'))
        r.update(quantity=8, campaign_groups=groups, _resolved_assets=assets, budget_usd='35', bid_strategy='COCAP', bid_usd='0.90')
        out = general.build(r, s, 114, a)['campaigns']
        self.assertEqual([len(c['ads']) for c in out], counts)
        self.assertEqual(sum(len(c['ads']) for c in out), 15)
        self.assertEqual(sum(int(c['campaign_updates']['daily_budget']) for c in out), 28000)
        for number, shell, group in zip(range(114, 122), out, groups):
            self.assertEqual(shell['adset_updates']['bid_amount'], '90')
            self.assertEqual(shell['campaign_updates']['bid_strategy'], 'COST_CAP')
            for ad in shell['ads']:
                creative = ad['creative_payload']; vd = creative['object_story_spec']['video_data']
                self.assertEqual(vd['message'], group['primary_text']); self.assertEqual(vd['link_description'], '⭐⭐⭐⭐⭐')
                self.assertTrue(vd['call_to_action']['value']['link'].startswith(a['shein_profile']['destination_base'] + '?'))
                for key, value in [('utm_campaign', f'b01fb06c{number:03d}'), ('utm_adgroup', f'b01fb06c{number:03d}g01')]:
                    self.assertIn(key + '=' + value, vd['call_to_action']['value']['link'])
                    self.assertIn(key + '=' + value, creative['url_tags'])
        self.assertEqual(s, before)

    def test_media_preparation_stops_before_drive_when_source_preflight_fails(self):
        r, s, a, assets = fixture(); p = a['shein_profile']
        r.update(quantity=1, campaign_groups=[dict(files=[assets[0]['canonical_filename']], product_label='EXACT', primary_text='EXACT')])
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw); cfg = base / 'data/ares/meta-ads/engine-v3/config.json'; cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({'accounts': {p['account_id']: {**a, 'token_item': 'OFFLINE'}}}))
            op = base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json'; op.parent.mkdir(parents=True)
            op.write_text(json.dumps({'channel_authorization_policy': {}}))
            common = Mock(); common.get_token_from_1password.return_value = ('OFFLINE', 'field')
            with patch.object(driver, 'lookup_account', return_value={'account_id': p['account_id']}), \
                 patch.object(driver, '_load_common', return_value=common), \
                 patch.object(driver, 'preflight_inherited_destination', side_effect=ValueError('source rejected')) as preflight, \
                 patch('ares_campaign_v3.shein_media_handoff._ops') as ops:
                with self.assertRaisesRegex(ValueError, 'source rejected'):
                    media._prepare_locked(r, base=base)
                preflight.assert_called_once(); ops.assert_not_called(); common.graph_get.assert_not_called()

    def test_queue_reservation_transfer_stops_if_live_source_rejected(self):
        from test_shein_request_queue import RequestQueueTests
        harness = RequestQueueTests(); harness.setUp()
        try:
            harness.state('shein-1111', 'COMPLETE_FUTURE_ACTIVE'); before = harness.inv.read_bytes()
            r = {**harness.req, 'source_number': 110, 'mode': 'clone_prestaged'}
            root = harness.root; cfg = root / 'engine-v3/config.json'; cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({'accounts': {'123': {'token_item': 'OFFLINE'}}}))
            op = root / 'operations'; op.mkdir()
            (op / 'SHEIN-US-DIRECT.json').write_text(json.dumps({'channel_authorization_policy': {}}))
            (op / 'SHEIN-US-DIRECT-profiles.json').write_text(json.dumps({'profiles': {'123': {}}}))
            common = Mock(); common.get_token_from_1password.return_value = ('OFFLINE', 'field')
            with patch.object(driver, '_load_common', return_value=common), \
                 patch.object(driver, 'preflight_inherited_destination', side_effect=ValueError('source rejected')) as preflight:
                with self.assertRaisesRegex(ValueError, 'source rejected'):
                    queue.claim_terminal(r, '123', harness.base)
                preflight.assert_called_once()
            self.assertEqual(before, harness.inv.read_bytes())
        finally:
            harness.tearDown()


if __name__ == '__main__':
    unittest.main()
