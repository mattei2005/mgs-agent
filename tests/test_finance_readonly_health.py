import copy,importlib.util,json,pathlib,threading,unittest,urllib.request
from http.server import BaseHTTPRequestHandler,HTTPServer
P=pathlib.Path('/root/mgs-agent/scripts/finance-readonly-health.py');spec=importlib.util.spec_from_file_location('finance_health',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
BAD={'ok':False,'expected':85,'checked':85,'passed':84,'failures':[{'period':'2026-10','manager':'nicolas','code':'manager_reconciliation'}]};GOOD={'ok':True,'expected':85,'checked':85,'passed':85,'failures':[]}
class Tests(unittest.TestCase):
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
