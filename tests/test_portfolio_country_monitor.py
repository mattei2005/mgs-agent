"""Offline acceptance fixtures. Never posts to Discord or Cloudflare."""
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error

SPEC = importlib.util.spec_from_file_location('portfolio', '/root/mgs-agent/scripts/monitor-portfolio-country.py')
assert SPEC is not None and SPEC.loader is not None
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
C = m.read_config(m.STORE)


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch')
        self.store = Path(self.tmp.name)
        self.c = copy.deepcopy(C)
        self.s = m.state_read(self.store)
        self.s['activation_verified'] = True
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def sample(self, token, site, a, b):
        self.calls.append((site['domain'], a, b))
        return m.base.normalize([{'count': 90, 'dimensions': {'clientCountryName': 'BR'}, 'avg': {'sampleInterval': 2}},
                                 {'count': 10, 'dimensions': {'clientCountryName': 'US'}, 'avg': {'sampleInterval': 1}}], a, b)

    def delivered(self, s, key, p, store):
        s['outbox'][key] = {'payload': p, 'verified': True, 'message_id': str(len(s['outbox'])+1)}
        m.save(store/'state.json', s)

    def message(self, p):
        return {'id': '123', 'channel_id': m.THREAD, 'content': '', 'mentions': [], 'mention_roles': [],
                'mention_everyone': False, 'timestamp': m.iso(dt.datetime.now(m.UTC)),
                'author': {'id': '1496296175014252634', 'bot': True}, 'embeds': p['embeds']}

    def test_thirty_complete_nonoverlapping_days(self):
        items = m.intervals(self.c)
        self.assertEqual(len(items), 30)
        self.assertEqual(items[0][1], self.c['start'])
        self.assertEqual(items[-1][2], self.c['end'])
        for i, (day, a, b) in enumerate(items):
            self.assertEqual((m.parse(b)-m.parse(a)).total_seconds(), 86400)
            if i: self.assertEqual(items[i-1][2], a)

    def test_no_provider_before_due(self):
        with patch.object(m, 'credential') as t, patch.object(m, 'deliver') as d:
            m.run(self.c, self.s, self.store, m.parse(self.c['start'])+dt.timedelta(hours=26))
            t.assert_not_called(); d.assert_not_called()

    def test_activation_required_is_safe(self):
        self.s.pop('activation_verified')
        with patch.object(m, 'credential') as t:
            self.assertEqual(m.run(self.c, self.s, self.store, m.parse(self.c['end']))['status'], 'activation_required')
            t.assert_not_called()

    def test_daily_once_and_exact_scope(self):
        now = m.parse(m.intervals(self.c)[0][2])+dt.timedelta(hours=3)
        with patch.object(m, 'credential', return_value='fixture') as t, patch.object(m, 'query', side_effect=self.sample), patch.object(m, 'deliver', side_effect=self.delivered):
            m.run(self.c, self.s, self.store, now); m.run(self.c, self.s, self.store, now)
        self.assertEqual(len(self.calls), 38); self.assertEqual(t.call_count, 1)
        self.assertEqual(len(self.s['outbox']), 5); self.assertEqual(self.s['delivered_days'], ['1'])
        self.assertEqual({a for _, a, _ in self.calls}, {self.c['start']})

    def test_full_duration_and_noop_after_close(self):
        with patch.object(m, 'credential', return_value='fixture') as t, patch.object(m, 'query', side_effect=self.sample) as q, patch.object(m, 'deliver', side_effect=self.delivered):
            m.run(self.c, self.s, self.store, m.parse(self.c['end'])+dt.timedelta(hours=3), deadline=float('inf'))
            self.assertEqual(self.s['status'], 'completed'); self.assertEqual(len(self.calls), 38*30)
            self.assertEqual(len(self.s['delivered_days']), 30); self.assertEqual(len(self.s['outbox']), 155)
            q.reset_mock(); t.reset_mock()
            result = m.run(self.c, self.s, self.store, m.parse(self.c['end'])+dt.timedelta(days=2))
            self.assertEqual(result['external_requests'], 0); q.assert_not_called(); t.assert_not_called()
        final = m.aggregate_days(self.c, self.store)
        self.assertTrue(all(x['total'] == 3000 for x in final.values()))

    def test_interrupted_collection_resumes_missing(self):
        sites = self.c['sites']; now = m.parse(m.intervals(self.c)[0][2])+dt.timedelta(hours=3)
        def partial(token, site, a, b):
            if site['domain'] == sites[2]['domain']: raise m.Error('fixture_timeout')
            return self.sample(token, site, a, b)
        with patch.object(m, 'credential', return_value='fixture'), patch.object(m, 'query', side_effect=partial), patch.object(m, 'deliver') as d:
            with self.assertRaises(m.Error): m.run(self.c, self.s, self.store, now)
            d.assert_not_called()
        self.assertEqual(len(json.loads((self.store/'day-01.json').read_text())['sites']), 2)
        self.calls = []
        with patch.object(m, 'credential', return_value='fixture'), patch.object(m, 'query', side_effect=self.sample), patch.object(m, 'deliver', side_effect=self.delivered):
            m.run(self.c, self.s, self.store, now)
        self.assertEqual(len(self.calls), 36)
        self.assertNotIn(sites[0]['domain'], [x[0] for x in self.calls])

    def test_budget_yield_preserves_progress(self):
        a, b = self.c['start'], m.intervals(self.c)[0][2]
        with patch.object(m, 'credential', return_value='fixture'), patch.object(m, 'query') as q:
            packet, complete = m.collect(self.c, self.store, 'partial.json', a, b, time.monotonic()-1)
            self.assertFalse(complete); q.assert_not_called()

    def test_sampling_not_multiplied(self):
        data = self.sample(None, self.c['sites'][0], 'a', 'b')
        self.assertEqual(data['total'], 100); self.assertEqual(data['max_sample_interval'], 2)

    def test_filter_literal(self):
        site = self.c['sites'][8]; q = m.query_text(site, self.c['start'], self.c['end'])
        self.assertIn('requestSource:"eyeball"', q)
        self.assertIn('clientRequestHTTPHost_in:'+json.dumps(site['hosts']), q)
        self.assertIn('clientCountryName', q); self.assertNotIn('countryMap', q)

    def test_render_all_sites_limits_mentions_and_percentages(self):
        data = {site['domain']: self.sample(None, site, 'a', 'b') for site in self.c['sites']}
        packets = m.payloads(self.c, 'daily', 'test', data, 'period')
        self.assertEqual(len(packets), 5)
        self.assertEqual(sum(len(p['embeds'][0]['fields']) for _, p in packets), 38)
        for _, p in packets:
            m.validate_payload(p)
            self.assertIn('90.0%', p['embeds'][0]['fields'][0]['value'])

    def test_unknown_categories_preserved_and_top10_aggregated(self):
        site = self.c['sites'][0]
        data = {'countries': {'XX': 1, 'T1': 1, **{f'{i:02}': 1 for i in range(12)}}, 'total': 14}
        field = m.country_field(site, data)
        self.assertIn('Outros (4 países/categorias)', field['value'])
        self.assertEqual(len(data['countries']), 14)

    def test_preflight_no_publication(self):
        with patch.object(m, 'credential', return_value='fixture'), patch.object(m, 'query', side_effect=self.sample), patch.object(m, 'deliver') as d:
            r = m.run(self.c, self.s, self.store, m.parse(self.c['start']), 'preflight')
            self.assertEqual(r['sites'], 38); d.assert_not_called()
        self.assertEqual(self.s['delivered_days'], [])

    def test_blocked_no_external_calls(self):
        self.s['status'] = 'blocked'
        with patch.object(m, 'credential') as t, patch.object(m.base, 'discord_get') as d:
            self.assertEqual(m.run(self.c, self.s, self.store, m.parse(self.c['end']))['external_requests'], 0)
            t.assert_not_called(); d.assert_not_called()

    def test_exact_readback_rejects_other_thread(self):
        data = {site['domain']: self.sample(None, site, 'a', 'b') for site in self.c['sites']}
        p = m.payloads(self.c, 'daily', 'test', data, 'period')[0][1]
        msg = self.message(p); msg['channel_id'] = 'wrong'
        with self.assertRaises(m.Error): m.base.verify_message(msg, p)

    def test_ambiguous_delivery_reconciles_without_post(self):
        data = {site['domain']: self.sample(None, site, 'a', 'b') for site in self.c['sites']}
        key, p = m.payloads(self.c, 'daily', 'test', data, 'period')[0]; msg = self.message(p)
        self.s['outbox'][key] = {'payload': p, 'prepared_at': m.iso(dt.datetime.now(m.UTC))}
        with patch.object(m.base, 'discord_get', side_effect=[[msg], msg]), patch.object(m.subprocess, 'run') as post:
            m.deliver(self.s, key, p, self.store); post.assert_not_called()
        self.assertTrue(self.s['outbox'][key]['verified'])

    def test_existing_receipt_get_only(self):
        data = {site['domain']: self.sample(None, site, 'a', 'b') for site in self.c['sites']}
        key, p = m.payloads(self.c, 'daily', 'test', data, 'period')[0]; msg = self.message(p)
        self.s['outbox'][key] = {'payload': p, 'message_id': '123'}
        with patch.object(m.base, 'discord_get', return_value=msg) as get, patch.object(m.subprocess, 'run') as post:
            m.deliver(self.s, key, p, self.store); post.assert_not_called()
            get.assert_called_once_with('channels/'+m.THREAD+'/messages/123')

    def test_five_failures_stop_provider_and_alert_once(self):
        self.c['start'] = m.iso(dt.datetime.now(m.UTC)-dt.timedelta(days=2))
        self.c['end'] = m.iso(m.parse(self.c['start'])+dt.timedelta(days=30))
        with patch.object(m, 'STORE', self.store), patch.object(m, 'read_config', return_value=self.c), patch.object(sys, 'argv', ['monitor']), patch.object(m, 'query', side_effect=m.Error('fixture_timeout')) as q, patch.object(m, 'credential', return_value='fixture'), patch.object(m, 'notice', side_effect=lambda s, st, k, title, detail, color: self.delivered(s, k, {'title': title}, st)):
            m.save(self.store/'state.json', self.s)
            for _ in range(5): m.main()
            n = q.call_count; m.main(); self.assertEqual(q.call_count, n)
            self.assertEqual(m.state_read(self.store)['status'], 'blocked')

    def test_graphql_authz_is_not_zero(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.read.return_value = json.dumps({'data': None, 'errors': [{'extensions': {'code': 'authz'}}]}).encode()
        response.__enter__.return_value = response
        with patch.object(m.urllib.request, 'urlopen', return_value=response):
            with self.assertRaises(m.Error) as error:
                m.query('fixture', self.c['sites'][0], self.c['start'], m.intervals(self.c)[0][2])
        self.assertTrue(error.exception.permanent)

    def test_invalid_dataset_is_blocker_not_zero(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.read.return_value = json.dumps({'data': {'viewer': {'zones': [{'settings': {'httpRequestsAdaptiveGroups': {'enabled': False, 'maxDuration': 86400, 'notOlderThan': 9999999}}, 'httpRequestsAdaptiveGroups': []}]}}}).encode()
        response.__enter__.return_value = response
        with patch.object(m.urllib.request, 'urlopen', return_value=response):
            with self.assertRaises(m.Error) as error:
                m.query('fixture', self.c['sites'][0], self.c['start'], m.intervals(self.c)[0][2])
        self.assertTrue(error.exception.permanent)

    def test_retry_after_is_respected_without_sleeping_long(self):
        from email.message import Message
        headers = Message(); headers['Retry-After'] = '120'
        e = urllib.error.HTTPError('https://api.cloudflare.com', 429, 'rate limited', headers, None)
        with patch.object(m.urllib.request, 'urlopen', side_effect=e) as call, patch.object(m.time, 'sleep') as sleep:
            with self.assertRaises(m.Error) as error:
                m.query('fixture', self.c['sites'][0], self.c['start'], m.intervals(self.c)[0][2])
        self.assertIn(';retry_at=', str(error.exception)); self.assertEqual(call.call_count, 1); sleep.assert_not_called()

    def test_recovery_not_claimed_while_collection_pending(self):
        self.s['failure_streak'] = 1; self.s['incident_id'] = 'fixture'
        m.save(self.store/'state.json', self.s)
        with patch.object(m, 'STORE', self.store), patch.object(m, 'read_config', return_value=self.c), patch.object(sys, 'argv', ['monitor']), patch.object(m, 'run', return_value={'status': 'collection_pending'}), patch.object(m, 'notice') as notice:
            self.assertEqual(m.main(), 0); notice.assert_not_called()
        self.assertEqual(m.state_read(self.store)['failure_streak'], 1)


if __name__ == '__main__':
    unittest.main()
