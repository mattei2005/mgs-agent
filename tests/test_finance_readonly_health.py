import copy,importlib.util,json,pathlib,threading,unittest,urllib.request,os,datetime
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,HTTPServer
P=pathlib.Path(os.environ.get('FINANCE_HEALTH_TEST_PATH','/root/mgs-agent/scripts/finance-readonly-health.py'));spec=importlib.util.spec_from_file_location('finance_health',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
BAD={'ok':False,'expected':85,'checked':85,'passed':84,'failures':[{'period':'2026-10','manager':'nicolas','code':'manager_reconciliation'}]};GOOD={'ok':True,'expected':85,'checked':85,'passed':85,'failures':[]}
class Tests(unittest.TestCase):
 def test_real_isolated_admission_lock_is_classified(self):
  import tempfile,sys
  sys.path.insert(0,'/root/mgs-agent/apps/finance-system')
  from finance_release_guard import lease
  with tempfile.TemporaryDirectory() as folder:
   def locked_probe():
    with lease(pathlib.Path(folder),timeout=.02,recover_pending=False):return GOOD
   with lease(pathlib.Path(folder),exclusive=True,timeout=.1,recover_pending=False):
    with patch.object(m,'collect',side_effect=locked_probe):r=m.probe()
   self.assertTrue(r['deferred']);self.assertFalse(r['ok'])
   with patch.object(m,'collect',side_effect=locked_probe):self.assertTrue(m.probe()['ok'])
 def test_known_admission_busy_is_deferred_not_healthy(self):
  with patch.object(m,'collect',side_effect=TimeoutError('finance_release_admission_busy_no_changes')):r=m.probe()
  self.assertTrue(r['deferred']);self.assertFalse(r['ok']);self.assertEqual(r['checked'],0)
 def test_unrelated_timeout_remains_first_failure(self):
  with patch.object(m,'collect',side_effect=TimeoutError('different_timeout')):r=m.probe()
  self.assertFalse(r.get('deferred',False));sent=[];m.transition({},r,lambda p:sent.append(p));self.assertEqual(len(sent),1)
 def test_defer_preserves_success_and_open_incident(self):
  old={'last_success':'2026-10-01T00:00:00+00:00','failure_streak':2,'alert_signature':'prior'};r={'ok':False,'deferred':True,'expected':0,'checked':0,'passed':0,'failures':[]}
  out=m.transition(old,r,lambda _:self.fail('contention must not claim failure or recovery'));self.assertEqual(out['last_status'],'deferred');self.assertEqual(out['last_success'],old['last_success']);self.assertEqual(out['alert_signature'],'prior');self.assertEqual(out['failure_streak'],2)
 def test_long_contention_escalates_and_success_clears(self):
  since=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=301)).isoformat();sent=[];r={'ok':False,'deferred':True,'expected':0,'checked':0,'passed':0,'failures':[]};out=m.transition({'deferred_since':since},r,lambda p:sent.append(p));self.assertEqual(out['last_status'],'failed');self.assertEqual(len(sent),1);self.assertEqual(out['result']['failures'][0]['code'],'finance_operation_wait_exceeded_5m');done=m.transition(out,GOOD,lambda p:sent.append(p));self.assertEqual(done['last_status'],'ok');self.assertNotIn('deferred_since',done);self.assertEqual(len(sent),2)

 def test_first_failure_and_dedup(self):
  sent=[];send=lambda p:sent.append(p) or {'readback':True};s=m.transition({},BAD,send);s=m.transition(s,BAD,send);self.assertEqual(len(sent),1);self.assertEqual(s['failure_streak'],2)
 def test_recovery_once(self):
  sent=[];send=lambda p:sent.append(p) or {'readback':True};s=m.transition({},BAD,send);s=m.transition(s,GOOD,send);s=m.transition(s,GOOD,send);self.assertEqual(len(sent),2);self.assertFalse(s['alert_signature']);self.assertEqual(sent[-1]['content'],'')
 def test_normal_silent(self):
  s=m.transition({},GOOD,lambda _:self.fail('normal success must be silent'));self.assertEqual(s['last_status'],'ok')
 def test_failed_delivery_preserves_old(self):
  old={'alert_signature':None};before=copy.deepcopy(old)
  with self.assertRaises(OSError):m.transition(old,BAD,lambda _:(_ for _ in ()).throw(OSError('TEST failure')))
  self.assertEqual(old,before)
 def test_readback_mismatch_rejected(self):
  def req(path,data=None):return {'id':'123'} if data else {'channel_id':'wrong','content':'','embeds':[]}
  with self.assertRaises(ValueError):m.send_notice(m.payload(BAD),req)
 def test_bounded_safe_fields(self):
  p=m.payload({**BAD,'failures':BAD['failures']*100});self.assertEqual(p['allowed_mentions']['users'],['344196393512075265']);self.assertLess(len(json.dumps(p)),4000);self.assertNotIn('token',json.dumps(p).lower())
 def test_http_mock_transport(self):
  messages=[];requests=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    requests.append((self.command,self.path,self.headers.get('Authorization')));d=json.loads(self.rfile.read(int(self.headers['Content-Length'])));messages.append({'id':'123456789012345678','channel_id':m.CHANNEL,**d});self.send_response(200);self.end_headers();self.wfile.write(json.dumps(messages[-1]).encode())
   def do_GET(self):
    requests.append((self.command,self.path,self.headers.get('Authorization')));self.send_response(200);self.end_headers();self.wfile.write(json.dumps(messages[-1]).encode())
  server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  def req(path,data=None):
   q=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,data=json.dumps(data).encode() if data else None,headers={'Authorization':'Bot TEST_NOT_A_SECRET','Content-Type':'application/json'})
   with urllib.request.urlopen(q,timeout=3) as r:return json.load(r)
  try:
   r=m.send_notice(m.payload(BAD),req);self.assertTrue(r['readback']);self.assertEqual([x[0] for x in requests],['POST','GET']);self.assertTrue(all(x[2]=='Bot TEST_NOT_A_SECRET' for x in requests));self.assertEqual(messages[0]['enforce_nonce'],True);self.assertEqual(len(messages[0]['nonce']),24)
  finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
