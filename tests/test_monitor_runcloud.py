"""RunCloud fixtures: no production writes or real secrets."""
import importlib.util,json,threading,unittest,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from datetime import datetime,timezone
SPEC=importlib.util.spec_from_file_location('monitor_runcloud','/root/mgs-agent/scripts/monitor-runcloud.py');assert SPEC is not None and SPEC.loader is not None;M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
ROOT=Path('/root/.hermes/profiles/zeus/cache/scratch/runcloud-tests-'+uuid.uuid4().hex);ROOT.mkdir(mode=0o700)
class H(BaseHTTPRequestHandler):
    items=[]; posts=0; reject=False;failget=False
    def log_message(self,format,*args):pass
    def respond(self,code,data):
        self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())
    def do_POST(self):
        assert self.headers['Authorization']=='Bot fixture-only'
        p=json.loads(self.rfile.read(int(self.headers['Content-Length'])));H.posts+=1
        if H.reject:self.respond(429,{});return
        p['id']=str(100+H.posts);p['channel_id']='fixture';H.items.append(p);self.respond(200,p)
    def do_GET(self):
        if '?' in self.path:self.respond(200,H.items);return
        if H.failget:self.respond(503,{});return
        ident=self.path.split('/')[-1];self.respond(200,next(x for x in H.items if x['id']==ident))
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),H);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def setUp(self):
        H.items=[];H.posts=0;H.reject=False;H.failget=False
        self.state=M.fresh_state();self.path=ROOT/(uuid.uuid4().hex+'.json');self.d=M.Discord('fixture-only','fixture','http://127.0.0.1:'+str(self.server.server_port))
    def observation(self,sev,confirmed=False):return {'x':{'server':'Inc','severity':sev,'detail':'fixture event','confirmed':confirmed}}
    def queue(self,sev=2):
        e=M.transitions(self.state,self.observation(sev,True),100);M.enqueue(self.state,e,self.path,100)
    def test_disk_thresholds(self):
        for used,expected in [(10000,0),(80000,1),(91000,2)]:self.assertEqual(M.disk_observation({'totalDiskSpace':100000,'usedDiskSpace':used,'availableDiskSpace':100000-used})[0],expected)
    def test_transient_warning_and_unknown(self):
        self.assertEqual(M.transitions(self.state,self.observation(1),1),[]);M.transitions(self.state,{},2);self.assertEqual(M.transitions(self.state,self.observation(1),3),[]);self.assertEqual(len(M.transitions(self.state,self.observation(1),4)),1)
    def test_delivery_and_dedupe(self):
        self.queue();self.assertEqual(len(M.deliver(self.state,self.path,self.d)),1);self.assertEqual(M.transitions(self.state,self.observation(2,True),200),[]);self.assertEqual(H.posts,1);self.assertTrue(H.items[0]['enforce_nonce']);self.assertEqual(H.items[0]['allowed_mentions']['parse'],[])
    def test_failed_http_then_retry(self):
        self.queue();H.reject=True
        with self.assertRaises(M.APIError):M.deliver(self.state,self.path,self.d)
        self.assertEqual(self.state['incidents']['x']['published'],0);self.assertEqual(self.state['outbox'][0]['phase'],'queued');H.reject=False;M.deliver(self.state,self.path,self.d);self.assertEqual(len(H.items),1)
    def test_post_accepted_get_failed_no_repost(self):
        self.queue();H.failget=True
        with self.assertRaises(M.APIError):M.deliver(self.state,self.path,self.d)
        self.assertTrue(self.state['outbox'][0]['message_id']);H.failget=False;M.deliver(self.state,self.path,self.d);self.assertEqual(H.posts,1)
    def test_ambiguous_delivery_reconciles_by_marker(self):
        self.queue();o=self.state['outbox'][0];self.d.post(o['payload']);o['phase']='sending';M.deliver(self.state,self.path,self.d);self.assertEqual(H.posts,1)
    def test_recovery_only_after_public_alert(self):
        self.assertEqual(M.transitions(self.state,self.observation(0),1),[]);self.queue();M.deliver(self.state,self.path,self.d);e=M.transitions(self.state,self.observation(0),300);M.enqueue(self.state,e,self.path,300);M.deliver(self.state,self.path,self.d);self.assertEqual(H.posts,2);self.assertEqual(H.items[-1]['content'],'');self.assertEqual(self.state['incidents']['x']['published'],0)
    def test_stale_unsent_alert_cancelled(self):
        self.queue();H.reject=True
        with self.assertRaises(M.APIError):M.deliver(self.state,self.path,self.d)
        e=M.transitions(self.state,self.observation(0),200);M.enqueue(self.state,e,self.path,200,self.observation(0));self.assertEqual(self.state['outbox'],[]);self.assertEqual(len(H.items),0)
    def test_log_rotation_retains_history(self):
        import subprocess
        root=ROOT/uuid.uuid4().hex;root.mkdir(mode=0o700);log=root/'fixture.log';original='fixture log\\n'*100;log.write_text(original)
        template=Path('/root/mgs-agent/config/runcloud-logrotate.conf').read_text();config=root/'rotation.conf';config.write_text(template.replace('/root/mgs-agent/logs/monitor-runcloud.log',str(log)))
        r=subprocess.run(['/usr/sbin/logrotate','-f','--state',str(root/'rotation.status'),str(config)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(log.read_text(),'');self.assertEqual((root/'fixture.log.1').read_text(),original);self.assertIn('rotate -1',template);self.assertIn('nocompress',template)
    def test_watchdog_exact_frequency(self):
        text=Path('/root/mgs-agent/scripts/monitor-cron-stale-logs.sh').read_text();block=text[text.index('def threshold_seconds('):text.index('def parse_crons():')];namespace={};exec(compile(block,'watchdog-fixture','exec'),namespace);self.assertEqual(namespace['threshold_seconds']('13,28,43,58 * * * *','monitor-runcloud.py'),3600)
    def test_unknown_preserves_open(self):
        self.queue();M.deliver(self.state,self.path,self.d);self.assertEqual(M.transitions(self.state,{},200),[]);self.assertEqual(self.state['incidents']['x']['published'],2)
    def test_backup_historical_failure_is_not_incident(self):
        cfg={'servers':[],'webapp_servers':{},'backup_max_age_hours':36};s=M.fresh_state()
        class A:
            calls=0;failures=0
            def pages(self,p):return []
        obs,summary=M.collect(A(),cfg,s,1000,True);self.assertEqual(obs['monitor:api']['severity'],0)
        old={'runDate':'2026-10-01 00:00:00','status':'FAILED'};new={'runDate':'2026-10-08 00:00:00','status':'COMPLETED'};self.assertEqual(max([old,new],key=M.snapshot_time)['status'],'COMPLETED')
    def test_backup_filters_archived_and_private(self):
        now=datetime(2026,10,8,12,tzinfo=timezone.utc).timestamp();cfg={'servers':[{'id':'1','name':'Inc','services':['nginx']}],'webapp_servers':{'10':'1'},'backup_max_age_hours':36}
        class A:
            calls=0;failures=0
            def get(self,p):
                if p.endswith('/latest'):return {'updated_at':'1 second ago','totalDiskSpace':100000,'usedDiskSpace':10000,'availableDiskSpace':90000}
                if p.endswith('/services'):return {'nginx':{'running':True}}
                return {'online':True,'connected':True}
            def pages(self,p):
                if p=='/backups':return [{'id':1,'status':'active','items':{'webApplicationId':10}},{'id':2,'status':'archived','items':{'webApplicationId':10}},{'id':3,'status':'active','items':{'webApplicationId':11}}]
                assert p=='/backups/1/snapshots';return [{'runDate':'2026-10-08 10:00:00','status':'COMPLETED'},{'runDate':'2026-10-01 00:00:00','status':'FAILED'}]
        obs,r=M.collect(A(),cfg,M.fresh_state(),now,True);self.assertEqual(r['backups']['active'],1);self.assertEqual(obs['1:backup:1']['severity'],0);self.assertNotIn('1:backup:2',obs)
if __name__=='__main__':unittest.main(verbosity=2)
