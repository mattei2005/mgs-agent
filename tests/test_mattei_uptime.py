import copy,importlib.util,json,pathlib,tempfile,unittest
spec=importlib.util.spec_from_file_location('uptime','/root/mgs-agent/scripts/monitor-mattei-uptime.py');assert spec and spec.loader
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MockDiscord:
    channel='1575283341404672001'
    def __init__(self):self.messages={};self.posts=0;self.fail_get=False
    def post(self,p):
        self.posts+=1;v=copy.deepcopy(p);v.update(id=str(self.posts),channel_id=self.channel,mentions=[]);self.messages[v['id']]=v;return v
    def get(self,ident):
        if self.fail_get:raise RuntimeError('mock_get_unavailable')
        return self.messages[ident]
    def recent(self):return list(self.messages.values())
class Tests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(m.classify(0,200,'x'*100,1),'ok')
        self.assertEqual(m.classify(0,200,'x'*100,9),'slow')
        self.assertEqual(m.classify(0,503,'x'*100,1),'http_error')
        self.assertEqual(m.classify(0,403,'cf-chl- x',1),'challenge')
        self.assertEqual(m.classify(0,403,'x'*100,1),'access_restricted')
        self.assertEqual(m.classify(60,0,'',0),'tls_error')
        self.assertEqual(m.classify(6,0,'',0),'dns_error')
        self.assertEqual(m.classify(28,0,'',20),'timeout')
        self.assertEqual(m.classify(0,200,'error establishing a database connection',1),'application_error')
        self.assertEqual(m.classify(0,200,' ',1),'empty_response')
    def test_retry_recovers_without_origin_or_false_alert(self):
        calls=[]
        def probe(*a,**kw):calls.append((a,kw));return {'status':'timeout' if len(calls)==1 else 'ok'}
        r=m.website('eggbev.com',['1.2.3.4'],8,probe=probe,sleep=lambda _:None)
        self.assertEqual(r['status'],'ok');self.assertEqual(len(calls),2)
    def test_confirm_and_origin(self):
        calls=[]
        def probe(*a,**kw):calls.append(kw);return {'status':'http_error','http':503,'seconds':1}
        r=m.website('eggbev.com',['1.2.3.4'],8,probe=probe,sleep=lambda _:None)
        self.assertTrue(r['confirmed']);self.assertEqual(calls[-1],{'origin':'1.2.3.4'})
    def test_dedupe_and_recovery(self):
        s={'announced':{'site:eggbev.com':'timeout'}}
        self.assertEqual(m.events_for(s,{'site:eggbev.com':{'status':'timeout'}}),[])
        self.assertEqual(m.events_for(s,{'site:eggbev.com':{'status':'probe_error'}}),[])
        self.assertEqual(len(m.events_for(s,{'site:eggbev.com':{'status':'ok'}})),1)
    def test_outbox_readback_retry_no_repost(self):
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch') as temp:
            path=pathlib.Path(temp)/'state.json';s={};d=MockDiscord();m.enqueue(s,{'embeds':[{'title':'fixture','description':'isolated mock only','color':1}]},'panel')
            d.fail_get=True
            with self.assertRaises(RuntimeError):m.deliver(s,path,d)
            self.assertEqual(d.posts,1);self.assertEqual(s['outbox'][0]['message_id'],'1')
            d.fail_get=False;m.deliver(s,path,d);self.assertEqual(d.posts,1);self.assertEqual(s['panel_id'],'1');self.assertEqual(s['outbox'],[])
    def test_ambiguous_post_reconciled(self):
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch') as temp:
            path=pathlib.Path(temp)/'state.json';s={};d=MockDiscord();m.enqueue(s,{'embeds':[{'title':'fixture','description':'mock only','color':1}]},'panel');d.post(s['outbox'][0]['payload']);s['outbox'][0]['phase']='sending';m.deliver(s,path,d);self.assertEqual(d.posts,1)
    def test_ambiguous_no_blind_retry(self):
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch') as temp:
            path=pathlib.Path(temp)/'state.json';s={};d=MockDiscord();m.enqueue(s,{'embeds':[{'title':'fixture'}]},'panel');s['outbox'][0]['phase']='sending'
            with self.assertRaises(RuntimeError):m.deliver(s,path,d)
            self.assertEqual(d.posts,0)
    def test_real_panel_limits_and_all_sites(self):
        cfg=json.loads(m.CONFIG.read_text());dry=json.loads(pathlib.Path('/root/mgs-agent/reports/mattei-uptime-1575283341404672001/dry-run.json').read_text());p=m.panel(cfg,dry['observations'],'fixture')
        self.assertEqual(sum(len(s['domains']) for s in cfg['servers']),55)
        self.assertTrue(all(len(e['description'])<4096 for e in p['embeds']));self.assertLess(sum(len(e['description'])+len(e['title']) for e in p['embeds']),5800)
        for s,e in zip(cfg['servers'],p['embeds']):
            for domain in s['domains']:self.assertIn(domain,e['description'])
    def test_no_remote_mutations_and_no_credential_lookups(self):
        text=pathlib.Path('/root/mgs-agent/scripts/monitor-mattei-uptime.py').read_text();self.assertNotIn('sshpass',text);self.assertNotIn('systemctl restart',text);self.assertNotIn('item get',text)
if __name__=='__main__':unittest.main()
