"""Offline fixtures; no provider calls or real Discord publications."""
import contextlib
import copy
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SPEC=importlib.util.spec_from_file_location('country', '/root/mgs-agent/scripts/monitor-vagaaqui-country.py')
assert SPEC is not None and SPEC.loader is not None
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
CONFIG=json.loads((m.STORE/'config.json').read_text())

class TestCountryMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch')
        self.store=Path(self.tmp.name)
        self.c=copy.deepcopy(CONFIG)
        m.save(self.store/'config.json',self.c)
        self.s=m.state_read(self.store)
    def tearDown(self):self.tmp.cleanup()
    def sample(self,a,b):return m.normalize([{'count':90,'dimensions':{'clientCountryName':'ZA'},'avg':{'sampleInterval':1.2}},{'count':10,'dimensions':{'clientCountryName':'US'},'avg':{'sampleInterval':1}}],a,b)
    def delivered(self,s,key,p,store):
        if not s['outbox'].get(key,{}).get('verified'):
            s['outbox'][key]={'payload':p,'verified':True,'message_id':str(len(s['outbox'])+1)}
            m.save(store/'state.json',s)
    def test_scope_guard(self):
        self.c['hosts'].append('newsfolha.com');m.save(self.store/'config.json',self.c)
        with self.assertRaises(m.MonitorError):m.config_read(self.store)
    def test_month_guard(self):
        self.c['end']='2027-12-11T01:38:29Z';m.save(self.store/'config.json',self.c)
        with self.assertRaises(m.MonitorError):m.config_read(self.store)
    def test_intervals_exactly_cover_month(self):
        parts=list(m.intervals(self.c));self.assertEqual(parts[0][0],self.c['start']);self.assertEqual(parts[-1][1],self.c['end'])
        self.assertTrue(all(parts[i][1]==parts[i+1][0] for i in range(len(parts)-1)))
        self.assertEqual(sum((m.parse(b)-m.parse(a)).total_seconds() for a,b in parts),(m.parse(self.c['end'])-m.parse(self.c['start'])).total_seconds())
    def test_normalize_empty_is_zero(self):self.assertEqual(m.normalize([],'a','b')['total'],0)
    def test_normalize_duplicate_rejected(self):
        row={'count':1,'dimensions':{'clientCountryName':'ZA'},'avg':{'sampleInterval':1}}
        with self.assertRaises(m.MonitorError):m.normalize([row,row],'a','b')
    def test_limit_rejected(self):
        with self.assertRaises(m.MonitorError):m.normalize([{}]*1000,'a','b')
    def test_aggregate(self):
        d=self.sample('a','b');self.assertEqual(m.aggregate([d,d])['total'],200)
    def test_payload_contract(self):
        p=m.payload('daily','k',self.sample('a','b'),self.c,'period');self.assertEqual(p['content'],'');self.assertEqual(p['allowed_mentions'],{'parse':[]});self.assertTrue(p['enforce_nonce'])
        self.assertLess(len(json.dumps(p)),6000);self.assertTrue(all(len(f['value'])<=1024 for f in p['embeds'][0]['fields']))
    def test_graphql_exact_host_filter(self):
        self.assertIn('clientRequestHTTPHost_in:["vagaaqui.com","www.vagaaqui.com"]',m.QUERY);self.assertIn('requestSource:"eyeball"',m.QUERY);self.assertNotIn('ls.vagaaqui.com',m.QUERY)
    def test_no_query_before_slice_ready(self):
        a,b=list(m.intervals(self.c))[0]
        with patch.object(m,'cf_token') as token,patch.object(m,'discord_get') as get:
            m.run(self.c,self.s,self.store,m.parse(b)+dt.timedelta(hours=2),'scheduled');token.assert_not_called();get.assert_not_called()
    def test_daily_once_and_idempotent(self):
        a,b=list(m.intervals(self.c))[0];now=m.parse(b)+dt.timedelta(hours=4)
        with patch.object(m,'cf_token',return_value='fixture'),patch.object(m,'cf_query',side_effect=lambda token,a,b:self.sample(a,b)) as q,patch.object(m,'deliver',side_effect=self.delivered):
            m.run(self.c,self.s,self.store,now,'scheduled');m.run(self.c,self.s,self.store,now,'scheduled');self.assertEqual(q.call_count,1);self.assertEqual(len(self.s['days']),1);self.assertEqual(len(self.s['outbox']),1)
    def test_provider_failure_not_zero(self):
        a,b=list(m.intervals(self.c))[0]
        with patch.object(m,'cf_token',return_value='fixture'),patch.object(m,'cf_query',side_effect=m.MonitorError('fixture_timeout')):
            with self.assertRaises(m.MonitorError):m.run(self.c,self.s,self.store,m.parse(b)+dt.timedelta(hours=4),'scheduled')
        self.assertEqual(self.s['days'],{})
    def test_full_month_closes_and_then_no_requests(self):
        with patch.object(m,'cf_token',return_value='fixture'),patch.object(m,'cf_query',side_effect=lambda token,a,b:self.sample(a,b)) as q,patch.object(m,'deliver',side_effect=self.delivered):
            result=m.run(self.c,self.s,self.store,m.parse(self.c['end'])+dt.timedelta(hours=4),'scheduled');self.assertEqual(result['status'],'completed');self.assertIn('final',self.s['outbox']);self.assertEqual(len(self.s['days']),len(list(m.intervals(self.c))))
            n=q.call_count;result=m.run(self.c,self.s,self.store,m.parse(self.c['end'])+dt.timedelta(days=2),'scheduled');self.assertEqual(result['external_requests'],0);self.assertEqual(q.call_count,n)
    def test_blocked_no_requests(self):
        self.s['status']='blocked'
        with patch.object(m,'cf_query') as q,patch.object(m,'discord_get') as get:
            self.assertEqual(m.run(self.c,self.s,self.store,m.parse(self.c['end']),'scheduled')['status'],'blocked_noop');q.assert_not_called();get.assert_not_called()
    def message(self,p):return {'id':'1','channel_id':m.THREAD,'content':'','mentions':[],'mention_roles':[],'mention_everyone':False,'author':{'id':'1496296175014252634','bot':True},'embeds':p['embeds']}
    def test_readback_mismatch_rejected(self):
        p=m.payload('daily','k',self.sample('a','b'),self.c,'period');msg=self.message(p);msg['channel_id']='wrong'
        with self.assertRaises(m.MonitorError):m.verify_message(msg,p)
    def test_ambiguous_post_reconciled_no_repost(self):
        p=m.payload('daily','k',self.sample('a','b'),self.c,'period');msg=self.message(p)
        self.s['outbox']['k']={'payload':p}
        with patch.object(m,'discord_get',side_effect=[[msg],msg]),patch.object(m.subprocess,'run') as post:
            m.deliver(self.s,'k',p,self.store);post.assert_not_called();self.assertTrue(self.s['outbox']['k']['verified'])
    def test_saved_message_id_resumed_with_exact_get(self):
        p=m.payload('daily','k',self.sample('a','b'),self.c,'period');msg=self.message(p)
        self.s['outbox']['k']={'payload':p,'message_id':'1'}
        with patch.object(m,'discord_get',return_value=msg) as get,patch.object(m.subprocess,'run') as post:
            m.deliver(self.s,'k',p,self.store);post.assert_not_called();get.assert_called_once_with('channels/'+m.THREAD+'/messages/1')
    def test_real_poster_with_mock_http_and_get(self):
        p=m.payload('daily','mock-http',self.sample('a','b'),self.c,'period');received=[];message=self.message(p)
        class Handler(BaseHTTPRequestHandler):
            def do_POST(inner):
                body=json.loads(inner.rfile.read(int(inner.headers['Content-Length'])));received.append((dict(inner.headers),body))
                inner.send_response(200);inner.send_header('Content-Type','application/json');inner.end_headers();inner.wfile.write(json.dumps(message).encode())
            def log_message(self,format,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            env={'MGS_DISCORD_BOT_TOKEN_OVERRIDE':'fixture-only','MGS_DISCORD_API_URL_OVERRIDE':f'http://127.0.0.1:{server.server_port}/messages'}
            with patch.dict(os.environ,env),patch.object(m,'discord_get',side_effect=[[],message]):m.deliver(self.s,'mock-http',p,self.store)
            self.assertEqual(len(received),1);headers,body=received[0];self.assertEqual(headers['Authorization'],'Bot fixture-only');self.assertEqual(body['allowed_mentions'],{'parse':[]});self.assertTrue(self.s['outbox']['mock-http']['verified'])
        finally:server.shutdown();server.server_close();thread.join()
    def test_main_five_failures_stop_provider_and_preserve_pending(self):
        with patch.object(m,'STORE',self.store),patch.object(m.sys,'argv',['monitor']),patch.object(m,'run',side_effect=m.MonitorError('fixture_transient')),patch.object(m,'deliver',side_effect=self.delivered),contextlib.redirect_stdout(io.StringIO()):
            for i in range(5):self.assertEqual(m.main(),1)
        s=m.state_read(self.store);self.assertEqual(s['failure_streak'],5);self.assertEqual(s['status'],'blocked');self.assertEqual(s['days'],{});self.assertTrue(any(k.startswith('blocked:') for k in s['outbox']))
    def test_recovery_message_once_and_resets_failures(self):
        self.s.update(failure_streak=1,incident_id='fixture-incident');m.save(self.store/'state.json',self.s)
        with patch.object(m,'STORE',self.store),patch.object(m.sys,'argv',['monitor']),patch.object(m,'run',return_value={'status':'active'}),patch.object(m,'deliver',side_effect=self.delivered),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(m.main(),0);self.assertEqual(m.main(),0)
        s=m.state_read(self.store);self.assertEqual(s['failure_streak'],0);self.assertEqual(len([k for k in s['outbox'] if k.startswith('recovery:')]),1)

if __name__=='__main__':unittest.main()
