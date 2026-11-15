"""Offline GET transport regression. Never accesses credentials/network/Engine."""
import copy
import importlib
import io
import json
import socket
import sys
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_channel_authority as auth
from ares_campaign_v3 import target_start_revision as rev


def headers(values=None):
    out = Message()
    for k, v in (values or {}).items(): out[k] = str(v)
    return out


def response(body=None, rates=None):
    out = io.BytesIO(json.dumps(body if body is not None else {'fresh': True}).encode())
    out.headers = headers(rates)
    return out


def limited(rates=None, body=None):
    return urllib.error.HTTPError('https://discord.com', 429, 'limited', headers(rates),
        io.BytesIO(json.dumps(body if body is not None else {'retry_after': 1, 'global': False}).encode()))


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0; self.sleeps = []
        def sleep(delay): self.sleeps.append(delay); self.now += delay
        self.clock = SimpleNamespace(monotonic=lambda: self.now, time=lambda: 1000 + self.now, sleep=sleep)
        self.patches = [patch.object(auth, 'time', self.clock), patch.object(auth, '_READ_DEADLINES', {}),
                        patch.object(socket.socket, 'connect', side_effect=AssertionError('offline external network forbidden'))]
        for p in self.patches: p.start(); self.addCleanup(p.stop)
        self.calls = []
    def get(self, path='/channels/111/messages/222'):
        with patch.object(Path, 'read_text', return_value='DISCORD_BOT_TOKEN=synthetic-offline-only'):
            return auth._get(path)
    def run_rows(self, rows, path='/channels/111/messages/222'):
        with patch.object(auth.urllib.request, 'urlopen', side_effect=rows) as net:
            result = self.get(path)
        self.calls.extend(net.call_args_list)
        return result
    def test_plain_success_preserves_shape(self):
        for value in [[], {'id':'1'}, None, 3]:
            self.assertEqual(self.run_rows([response(value)]), {'fresh':True} if value is None else value)
    def test_conflicting_retry_delays_use_safe_maximum(self):
        self.run_rows([limited({'Retry-After':'5','X-RateLimit-Reset-After':'4.797'}, {'retry_after':0.797,'global':False}), response()])
        self.assertAlmostEqual(self.sleeps[0], 5.05)
    def test_body_longer_wins(self):
        self.run_rows([limited({'Retry-After':'1'}, {'retry_after':7}), response()]);self.assertAlmostEqual(self.sleeps[0],7.05)
    def test_reset_absolute_longer_wins(self):
        self.run_rows([limited({'Retry-After':'1','X-RateLimit-Reset':'1109'}), response()]);self.assertAlmostEqual(self.sleeps[0],9.05)
    def test_case_insensitive_headers(self):
        self.run_rows([limited({'rEtRy-AfTeR':'3'}), response()]);self.assertAlmostEqual(self.sleeps[0],3.05)
    def test_http_date_retry(self):
        self.run_rows([limited({'Retry-After':'Thu, 01 Jan 1970 00:18:25 GMT'}, {'retry_after':1}),response()]);self.assertAlmostEqual(self.sleeps[0],5.05)
    def test_header_only_429(self):
        self.run_rows([limited({'Retry-After':'2'}, {}),response()]);self.assertAlmostEqual(self.sleeps[0],2.05)
    def test_body_only_429(self):
        self.run_rows([limited({}, {'retry_after':2.5}),response()]);self.assertAlmostEqual(self.sleeps[0],2.55)
    def test_zero_delay_has_margin(self):
        self.run_rows([limited({}, {'retry_after':0}),response()]);self.assertAlmostEqual(self.sleeps[0],.05)
    def test_retry_attempt_bound(self):
        with patch.object(auth.urllib.request,'urlopen',side_effect=[limited() for _ in range(4)]) as net:
            with self.assertRaisesRegex(ValueError,'retry bound'):self.get()
        self.assertEqual(net.call_count,4);self.assertEqual(len(self.sleeps),3)
    def test_wait_bound_not_truncated(self):
        with patch.object(auth.urllib.request,'urlopen',side_effect=[limited({'Retry-After':60}),response()]) as net:
            with self.assertRaisesRegex(ValueError,'wait bound'):self.get()
        self.assertEqual(net.call_count,1);self.assertEqual(self.sleeps,[])
    def test_cumulative_wait_bound(self):
        with patch.object(auth.urllib.request,'urlopen',side_effect=[limited({'Retry-After':11}) for _ in range(4)]) as net:
            with self.assertRaisesRegex(ValueError,'wait bound'):self.get()
        self.assertEqual(net.call_count,3);self.assertLessEqual(sum(self.sleeps),30)
    def test_elapsed_bound(self):
        def slow(*args,**kw):self.now+=91;raise limited()
        with patch.object(auth.urllib.request,'urlopen',side_effect=slow) as net:
            with self.assertRaisesRegex(ValueError,'bound'):self.get()
        self.assertEqual(net.call_count,1)
    def test_non429_not_retried(self):
        for status in [400,401,403,404,500,503]:
            with self.subTest(status=status), patch.object(auth.urllib.request,'urlopen',side_effect=urllib.error.HTTPError('x',status,'denied',headers(),io.BytesIO(b'{}'))) as net:
                with self.assertRaisesRegex(ValueError,'HTTP='+str(status)):self.get()
                self.assertEqual(net.call_count,1)
    def test_transport_not_retried_or_leaked(self):
        for error in [TimeoutError('secret'),urllib.error.URLError('secret'),OSError('secret')]:
            with patch.object(auth.urllib.request,'urlopen',side_effect=error) as net:
                with self.assertRaisesRegex(ValueError,'^Discord permission proof transport unavailable$'):self.get()
                self.assertEqual(net.call_count,1)
    def test_malformed_200_fails(self):
        with patch.object(auth.urllib.request,'urlopen',return_value=io.BytesIO(b'not JSON')):
            with self.assertRaises(ValueError):self.get()
    def test_malformed_429_json(self):
        error=urllib.error.HTTPError('https://discord.com',429,'limited',headers({'Retry-After':1}),io.BytesIO(b'not JSON'))
        with patch.object(auth.urllib.request,'urlopen',side_effect=error) as net:
            with self.assertRaisesRegex(ValueError,'malformed rate'):self.get()
        self.assertEqual(net.call_count,1)
    def test_missing_delay_fails(self):
        with patch.object(auth.urllib.request,'urlopen',side_effect=limited({},{})):
            with self.assertRaisesRegex(ValueError,'malformed rate'):self.get()
    def test_invalid_delays_failclosed(self):
        for v in [-1, True, 'NaN','Infinity','bad',{},None]:
            with self.subTest(v=v),patch.object(auth.urllib.request,'urlopen',side_effect=limited({'Retry-After':5},{'retry_after':v})):
                with self.assertRaisesRegex(ValueError,'malformed rate'):self.get()
    def test_invalid_headers_failclosed_even_with_valid_body(self):
        for key in ['Retry-After','X-RateLimit-Reset-After','X-RateLimit-Reset']:
            for v in ['NaN','Infinity','-1','bad']:
                with self.subTest(key=key,v=v),patch.object(auth.urllib.request,'urlopen',side_effect=limited({key:v})):
                    with self.assertRaisesRegex(ValueError,'malformed rate'):self.get()
    def test_invalid_body_shapes(self):
        for v in [[],True,'bad',{'retry_after':1,'global':'false'}]:
            with self.subTest(v=v),patch.object(auth.urllib.request,'urlopen',side_effect=limited({'Retry-After':1},v)):
                with self.assertRaisesRegex(ValueError,'malformed rate'):self.get()
    def test_pacing_distinct_message_ids_no_content_cache(self):
        self.assertEqual(self.run_rows([response({'v':1},{'X-RateLimit-Remaining':0,'X-RateLimit-Reset-After':4})]),{'v':1})
        self.assertEqual(self.run_rows([response({'v':2})],'/channels/111/messages/333'),{'v':2})
        self.assertEqual(len(self.calls),2);self.assertAlmostEqual(self.sleeps[0],4.05)
    def test_pacing_separate_major(self):
        self.run_rows([response({}, {'X-RateLimit-Remaining':0,'X-RateLimit-Reset-After':4})])
        self.run_rows([response()],'/channels/999/messages/333');self.assertEqual(self.sleeps,[])
    def test_exhausted_success_missing_reset_fails(self):
        with patch.object(auth.urllib.request,'urlopen',return_value=response({}, {'X-RateLimit-Remaining':0})):
            with self.assertRaises(ValueError):self.get()
    def test_remaining_positive_no_sleep(self):
        self.run_rows([response({}, {'X-RateLimit-Remaining':1,'X-RateLimit-Reset-After':5})]);self.run_rows([response()]);self.assertEqual(self.sleeps,[])
    def test_global_body_paces_other_major(self):
        with patch.object(auth,'_READ_MAX_WAIT',1):
            with patch.object(auth.urllib.request,'urlopen',side_effect=limited({'Retry-After':3},{'retry_after':1,'global':True})):
                with self.assertRaises(ValueError):self.get()
        self.run_rows([response()],'/guilds/999/roles');self.assertAlmostEqual(self.sleeps[0],3.05)
    def test_global_header_paces_other_major(self):
        with patch.object(auth,'_READ_MAX_ATTEMPTS',1),patch.object(auth.urllib.request,'urlopen',side_effect=limited({'Retry-After':3,'X-RateLimit-Global':'true'})):
            with self.assertRaises(ValueError):self.get()
        self.run_rows([response()],'/guilds/999/roles');self.assertAlmostEqual(self.sleeps[0],3.05)
    def test_no_credential_fallback(self):
        with patch.object(Path,'read_text',return_value='OTHER_TOKEN=not-used'),patch.object(auth.urllib.request,'urlopen') as net:
            with self.assertRaisesRegex(ValueError,'identity unavailable'):auth._get('/channels/111')
        net.assert_not_called()
    def test_get_identity_and_timeout_preserved(self):
        self.run_rows([response()]);args,kw=self.calls[-1];self.assertEqual(args[0].get_method(),'GET');self.assertEqual(kw['timeout'],15)
        self.assertEqual(args[0].get_header('Authorization'),'Bot synthetic-offline-only')
    def test_shein_consumers_import_same_get(self):
        for name in ['shein_elapsed_continuation','shein_manual_observation','shein_continuation','shein_manual_takeover','reviewed_ad_schedule','shein_request_queue','reviewed_copy_omissions','shein_prewrite_amendment']:
            self.assertIsNotNone(importlib.import_module('ares_campaign_v3.'+name))
    def test_triple_fresh_authority_without_injected_get(self):
        from test_target_start_revision import RevisionTests
        fixture=RevisionTests('test_live_human_and_credential_helper');fixture.setUp();self.addCleanup(fixture.doCleanups)
        calls=[];successes=[]
        def live(request,**kwargs):
            path=request.full_url.split('/api/v10',1)[1];calls.append(path)
            # Reproduce the third-wave live 429, retain every equality/re-read.
            if len(calls)==9:raise limited({'Retry-After':5,'X-RateLimit-Reset-After':4.797},{'retry_after':.797,'global':False})
            successes.append(path);return response(fixture.get(path))
        original_read=Path.read_text
        def scoped_read(path,*a,**kw):
            return 'DISCORD_BOT_TOKEN=synthetic-offline-only' if str(path).endswith('/ares/.env') else original_read(path,*a,**kw)
        with patch.object(auth.urllib.request,'urlopen',side_effect=live),patch.object(Path,'read_text',scoped_read):
            for _ in range(3):rev.live_authority({'grant':fixture.grant},meta=fixture.meta(),token='synthetic')
        self.assertEqual(len(successes),12);self.assertEqual(len(calls),13)
        for m in fixture.messages:self.assertEqual(sum(p.endswith('/messages/'+m['id']) for p in successes),3)
        self.assertAlmostEqual(self.sleeps[0],5.05)
    def test_third_fresh_authority_edit_is_rejected(self):
        from test_target_start_revision import RevisionTests
        fixture=RevisionTests('test_live_human_and_credential_helper');fixture.setUp();self.addCleanup(fixture.doCleanups)
        reads=[]
        def live(request,**kwargs):
            path=request.full_url.split('/api/v10',1)[1];reads.append(path);body=fixture.get(path)
            if len(reads)>=9 and 'author' in body:body['content']='revoked'
            return response(body)
        with patch.object(auth.urllib.request,'urlopen',side_effect=live),patch.object(Path,'read_text',return_value='DISCORD_BOT_TOKEN=synthetic-offline-only'):
            for _ in range(2):rev.live_authority({'grant':fixture.grant},meta=fixture.meta(),token='synthetic')
            with self.assertRaisesRegex(ValueError,'changed or unavailable'):rev.live_authority({'grant':fixture.grant},meta=fixture.meta(),token='synthetic')
        self.assertGreater(len(reads),8)

if __name__=='__main__':unittest.main()
