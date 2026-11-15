"""Offline strict pairwise byte proof and transport regression. No live URLs."""
import copy
import importlib.util
import json
import socket
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))
from ares_campaign_v3 import native_thumbnail_equivalence as proof
spec = importlib.util.spec_from_file_location('thumbnail_runner', ROOT / 'scripts/ares-eggbev-target-clone.py')
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
OLD = 'https://www.facebook.com/ads/image/?d=old_1'
NEW = 'https://www.facebook.com/ads/image/?d=new_2'
CONTEXT = dict(request_id='offline-thumbnail-test', approved_digest='a' * 64, account_id='123', source_campaign_id='456')
JPEG = b'\xff\xd8\xff' + b'offline image fixture'


def snapshot(url):
    ad = dict(id='10', adset_id='20', status='ACTIVE', creative=dict(id='30', url_tags='utm_campaign=pg_23189',
              object_story_spec=dict(page_id='40', video_data=dict(video_id='50', image_url=url,
              message='literal copy', call_to_action=dict(type='APPLY_NOW', value=dict(app_destination='MESSENGER'))))))
    return dict(campaign=dict(id='456', account_id='123', status='ACTIVE', daily_budget='3500'),
                adset=dict(id='20', targeting=dict(age_min=18)), ads=[ad], all_ads=[copy.deepcopy(ad)], technical_seed_ads=[])


class ThumbnailTests(unittest.TestCase):
    def setUp(self):
        self.net = patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')); self.net.start(); self.addCleanup(self.net.stop)
        self.a, self.b = snapshot(OLD), snapshot(NEW)
        self.fetch = Mock(return_value=JPEG)

    def compare(self, **kw):
        return proof.compare(kw.get('a', self.a), kw.get('b', self.b), context=kw.get('context', CONTEXT), normalize=runner.source_comparison, fetcher=self.fetch)

    def verify(self, receipt, **kw):
        return proof.verify_receipt(receipt, expected_sha256=kw.get('pin', proof.digest(receipt)), original=kw.get('a', self.a), current=kw.get('b', self.b), context=kw.get('context', CONTEXT), normalize=runner.source_comparison)

    def test_positive_two_edges_deduplicated_bytes_and_no_mutation(self):
        before = copy.deepcopy((self.a, self.b)); receipt = self.compare()
        self.assertEqual(len(receipt['entries']), 2); self.assertEqual(self.fetch.call_count, 2)
        self.assertEqual((self.a, self.b), before); self.assertTrue(self.verify(receipt))
        self.assertNotIn(OLD, json.dumps(receipt)); self.assertNotIn(NEW, json.dumps(receipt))

    def test_replay_offline_bound_to_exact_snapshots(self):
        receipt = json.loads(json.dumps(self.compare())); self.fetch.reset_mock()
        self.assertTrue(self.verify(receipt)); self.fetch.assert_not_called()

    def test_production_never_reuses_receipt_as_fetch_cache(self):
        self.compare(); self.compare(); self.assertEqual(self.fetch.call_count, 4)

    def test_tamper_pinned_receipt(self):
        receipt = self.compare(); pin = proof.digest(receipt); receipt['entries'][0]['original_bytes'] += 1
        with self.assertRaises(ValueError): self.verify(receipt, pin=pin)

    def test_rehashed_size_hash_and_url_tamper(self):
        original = self.compare()
        changes = [('original_bytes', 1), ('original_bytes_sha256', 'f' * 64), ('original_url_sha256', 'b' * 64), ('ad_id', '99'), ('slot', 1)]
        for k, v in changes:
            with self.subTest(k=k):
                receipt = copy.deepcopy(original); receipt['entries'][0][k] = v
                with self.assertRaises(ValueError): self.verify(receipt)

    def test_replay_other_request_seal_account_source(self):
        receipt = self.compare()
        for key, value in [('request_id', 'different-request'), ('approved_digest', 'b' * 64), ('account_id', '999'), ('source_campaign_id', '999')]:
            with self.subTest(key=key), self.assertRaises(ValueError): self.verify(receipt, context=dict(CONTEXT, **{key: value}))

    def test_replay_other_url_snapshot(self):
        receipt = self.compare(); b = snapshot(NEW + 'a')
        with self.assertRaises(ValueError): self.verify(receipt, b=b)

    def test_bytes_diverge_even_same_size(self):
        self.fetch.side_effect = [JPEG, JPEG[:-1] + b'!']
        with self.assertRaises(ValueError): self.compare()

    def test_missing_empty_oversize_and_failed_fetch(self):
        for value in [None, b'', b'x' * (proof.MAX_BYTES + 1)]:
            with self.subTest(size=None if value is None else len(value)):
                self.fetch.return_value = value
                with self.assertRaises(ValueError): self.compare()
        self.fetch.side_effect = ValueError('403')
        with self.assertRaises(ValueError): self.compare()

    def test_no_native_delta_requires_no_fetch(self):
        self.compare(b=self.a); self.fetch.assert_not_called()

    def test_all_other_delta_rejected_before_fetch(self):
        paths = [(['campaign', 'daily_budget'], '4500'), (['campaign', 'status'], 'PAUSED'), (['adset', 'targeting', 'age_min'], 21),
                 (['ads', 0, 'creative', 'id'], '31'), (['ads', 0, 'id'], '11'), (['ads', 0, 'adset_id'], '21'),
                 (['ads', 0, 'creative', 'url_tags'], 'changed'), (['ads', 0, 'creative', 'object_story_spec', 'page_id'], '41'),
                 (['ads', 0, 'creative', 'object_story_spec', 'video_data', 'video_id'], '51'),
                 (['ads', 0, 'creative', 'object_story_spec', 'video_data', 'message'], 'changed'),
                 (['ads', 0, 'creative', 'object_story_spec', 'video_data', 'call_to_action', 'type'], 'LEARN_MORE')]
        for path, value in paths:
            with self.subTest(path=path):
                b = copy.deepcopy(self.b); node = b
                for key in path[:-1]: node = node[key]
                node[path[-1]] = value
                with self.assertRaises(ValueError): self.compare(b=b)
                self.fetch.assert_not_called()

    def test_feature_delta_not_hidden(self):
        self.b['ads'][0]['creative']['degrees_of_freedom_spec'] = {'creative_features_spec': {'image_background_gen': {'enroll_status': 'OPT_IN'}}}
        with self.assertRaises(ValueError): self.compare()
        self.fetch.assert_not_called()

    def test_ads_slot_order_not_sorted(self):
        other = copy.deepcopy(self.a['ads'][0]); other['id'] = '11'
        self.a['ads'].append(other); self.b['ads'].insert(0, copy.deepcopy(other))
        with self.assertRaises(ValueError): self.compare()
        self.fetch.assert_not_called()

    def test_duplicate_id_rejected(self):
        self.a['ads'].append(copy.deepcopy(self.a['ads'][0])); self.b['ads'].append(copy.deepcopy(self.b['ads'][0]))
        with self.assertRaises(ValueError): self.compare()

    def test_missing_identity_not_accepted(self):
        for edge in ('ads', 'all_ads'):
            self.a[edge][0]['creative'].pop('id'); self.b[edge][0]['creative'].pop('id')
        with self.assertRaises(ValueError): self.compare()

    def test_arbitrary_host_path_credentials_query_and_fragment_fail_closed(self):
        bad = ['http://www.facebook.com/ads/image/?d=x', 'https://facebook.com/ads/image/?d=x',
               'https://www.facebook.com.evil.test/ads/image/?d=x', 'https://127.0.0.1/ads/image/?d=x',
               'https://user:pass@www.facebook.com/ads/image/?d=x', 'https://www.facebook.com:443/ads/image/?d=x',
               'https://www.facebook.com/ads/IMAGE/?d=x', NEW + '#x', NEW + '&d=x', NEW + '&x=y',
               'https://www.facebook.com/ads/image/?d=', NEW + '%20', NEW + '\n']
        for url in bad:
            with self.subTest(shape=url):
                with self.assertRaises(ValueError): self.compare(b=snapshot(url))
                self.fetch.assert_not_called()

    def test_afs_existing_restrictions_remain(self):
        for s in (self.a, self.b):
            s['ads'][0]['creative']['asset_feed_spec'] = {'videos': [{'video_id': '60', 'thumbnail_url': 'https://scontent-lga3-2.xx.fbcdn.net/x.jpg?oh=old&stp=size'}]}
        self.b['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url'] = 'https://scontent-lga3-1.xx.fbcdn.net/x.jpg?oh=new&stp=size'
        self.compare(); self.fetch.reset_mock()
        self.b['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url'] += '2'
        with self.assertRaises(ValueError): self.compare()
        self.fetch.assert_not_called()

    def test_native_link_branch_not_accepted(self):
        for s in (self.a, self.b):
            story = s['ads'][0]['creative']['object_story_spec']; story['link_data'] = story.pop('video_data')
        with self.assertRaises(ValueError): self.compare()


class TransportTests(unittest.TestCase):
    def response(self, status=200, headers=None, body=JPEG):
        response = Mock(status=status); headers = {'Content-Type': 'image/jpeg', 'Content-Length': str(len(body)), **(headers or {})}
        response.getheader.side_effect = lambda key, default=None: headers.get(key, default)
        response.read.return_value = body
        return response

    def fetch(self, response):
        with patch.object(proof, '_PinnedHTTPS') as factory:
            conn = factory.return_value; conn.getresponse.return_value = response
            result = proof.fetch_native(OLD)
            self.assertEqual(conn.request.call_args.args[0], 'GET'); conn.close.assert_called_once()
            headers = conn.request.call_args.kwargs['headers']; self.assertNotIn('Authorization', headers); self.assertNotIn('Cookie', headers)
            return result

    def test_safe_get_bounded_and_no_credentials(self):
        self.assertEqual(self.fetch(self.response()), JPEG)

    def test_403_redirect_html_encoding_missing_truncated_large_rejected(self):
        cases = [self.response(status=403), self.response(status=302, headers={'Location': 'http://127.0.0.1/'}),
                 self.response(headers={'Location': OLD}), self.response(headers={'Content-Type': 'text/html'}),
                 self.response(headers={'Content-Encoding': 'gzip'}), self.response(body=b'html'), self.response(body=b''),
                 self.response(headers={'Content-Length': '999'}), self.response(headers={'Content-Length': str(proof.MAX_BYTES + 1)})]
        for response in cases:
            with self.subTest(response=response), self.assertRaises(ValueError): self.fetch(response)

    def test_one_exact_cdn_redirect_allowed_no_second_hop(self):
        url = 'https://scontent-iad3-1.xx.fbcdn.net/v/t45.1600-4/123_456_789_n.jpg?oh=abc&oe=123'
        first = self.response(status=302, headers={'Location': url})
        with patch.object(proof, '_PinnedHTTPS') as factory:
            a, b = Mock(), Mock(); factory.side_effect = [a, b]
            a.getresponse.return_value = first; b.getresponse.return_value = self.response()
            self.assertEqual(proof.fetch_native(OLD), JPEG)
            self.assertEqual(factory.call_args.args[0], 'scontent-iad3-1.xx.fbcdn.net')
            self.assertEqual(b.request.call_args.args[1], '/v/t45.1600-4/123_456_789_n.jpg?oh=abc&oe=123')
        with patch.object(proof, '_PinnedHTTPS') as factory:
            factory.return_value.getresponse.return_value = first
            with self.assertRaises(ValueError): proof.fetch_native(OLD)
            self.assertEqual(factory.call_count, 2)

    def test_unsafe_cdn_redirects_rejected(self):
        base = 'https://scontent-iad3-1.xx.fbcdn.net/v/t45.1600-4/123_456_789_n.jpg?oh=abc&oe=123'
        for url in [base.replace('https:', 'http:'), base.replace('.net/', '.net.evil.test/'), base.replace('/v/', '/..%2fv/'),
                    base + '#x', base + '&url=https://example.test', base + '&oe=1', base.replace('scontent-', 'u:p@scontent-'),
                    base.replace('.net/', '.net:443/'), 'https://www.facebook.com/unsupportedbrowser']:
            with self.subTest(shape=url), self.assertRaises(ValueError): proof._cdn_redirect(url)

    def test_private_or_mixed_dns_rejected_before_connect(self):
        for addresses in [['127.0.0.1'], ['169.254.169.254'], ['::1'], ['224.0.0.1'], ['157.240.1.1', '10.0.0.1']]:
            rows = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in addresses]
            with patch.object(socket, 'getaddrinfo', return_value=rows), patch.object(socket, 'create_connection') as create:
                with self.assertRaises(ValueError): proof._PinnedHTTPS('www.facebook.com', timeout=1).connect()
                create.assert_not_called()

    def test_public_dns_pinned_and_tls_hostname_preserved(self):
        rows = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('157.240.1.1', 443))]
        with patch.object(socket, 'getaddrinfo', return_value=rows), patch.object(socket, 'create_connection') as create:
            conn = proof._PinnedHTTPS('www.facebook.com', timeout=1); conn._context = Mock(); conn.connect()
            create.assert_called_once_with(('157.240.1.1', 443), 1)
            conn._context.wrap_socket.assert_called_once_with(create.return_value, server_hostname='www.facebook.com')


class InstalledRunnerTests(unittest.TestCase):
    def test_integrated_gate_writes_receipt_without_engine_or_final_approval(self):
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as temp, ExitStack() as stack:
            home = Path(temp); a, b = snapshot(OLD), snapshot(NEW)
            runner.save(home / 'source-live.json', a); runner.save(home / 'manifest.json', {'prevalidation': {'content_digest': 'a' * 64}})
            q = dict(request_id=CONTEXT['request_id'], source_campaign_id_candidate='456', commercial_ok_message_id='earlier', target_page_token='pg_23189')
            runner.save(home/'request.json',q);config=home/'config.json'
            runner.save(config,{'state_root':str(home/'state'),'audit_root':str(home/'audit'),'accounts':{runner.ACCOUNT:{}}})
            stack.enter_context(patch.object(runner,'CONFIG',config))
            # Match runner's exact account without touching production input.
            for s in (a, b): s['campaign']['account_id'] = runner.ACCOUNT
            runner.save(home / 'source-live.json', a)
            stack.enter_context(patch.object(runner, 'request_load', return_value=q)); stack.enter_context(patch.object(runner, 'reader_block_reason', return_value=None))
            stack.enter_context(patch.object(runner, 'verify_prevalidation', return_value=True)); stack.enter_context(patch.object(runner, 'runtime', return_value=(None, None, None, None)))
            stack.enter_context(patch.object(runner, 'source_read', return_value=b)); fetch = stack.enter_context(patch.object(proof, 'fetch_native', return_value=JPEG))
            page = stack.enter_context(patch.object(runner, 'resolve_page', side_effect=RuntimeError('stop after comparison')))
            engine = stack.enter_context(patch.object(runner, 'CampaignEngine', side_effect=AssertionError('engine forbidden')))
            with self.assertRaisesRegex(RuntimeError, 'stop after comparison'): runner.execute(home / 'request.json', True, 'a' * 64, 'later')
            self.assertEqual(len(list(home.glob('source-thumbnail-proof-*.json'))), 1); self.assertEqual(fetch.call_count, 2)
            self.assertEqual(runner.load(home / 'source-live.json'), a); self.assertEqual(runner.load(home / 'source-current-before-execute.json'), b)
            self.assertFalse((home / 'final-approval.json').exists()); engine.assert_not_called(); page.assert_called_once()


if __name__ == '__main__': unittest.main()
