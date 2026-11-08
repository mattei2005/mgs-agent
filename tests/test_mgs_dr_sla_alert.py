import importlib.util, json, os, tempfile, threading, unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('dr','/root/mgs-agent/scripts/mgs-dr-sla-alert.py')
assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.p=Path(tempfile.mkdtemp(prefix='dr-alert-fixture-',dir=os.environ['TMPDIR']))/'state.json';self.sent=[]
 def sender(self,body,state,path):self.sent.append(body);return str(len(self.sent)),body
 def test_healthy_silent(self):
  self.assertFalse(m.tick(True,[],{},self.p,self.sender));self.assertEqual(self.sent,[])
 def test_first_failure_and_deduplication(self):
  self.assertTrue(m.tick(False,['test failed'],{},self.p,self.sender));self.assertFalse(m.tick(False,['test failed'],{},self.p,self.sender));self.assertEqual(len(self.sent),1)
 def test_recovery_once_silent_mentions(self):
  m.tick(False,['test failed'],{},self.p,self.sender);m.tick(True,[],{},self.p,self.sender);m.tick(True,[],{},self.p,self.sender)
  self.assertEqual(len(self.sent),2);self.assertEqual(self.sent[-1]['content'],'');self.assertEqual(self.sent[-1]['allowed_mentions']['parse'],[])
 def test_changed_failure(self):
  m.tick(False,['a'],{},self.p,self.sender);m.tick(False,['b'],{},self.p,self.sender);self.assertEqual(len(self.sent),2)
 def test_failed_delivery_preserves_active(self):
  m.tick(False,['a'],{},self.p,self.sender)
  def fail(*a):raise RuntimeError('mock transport')
  with self.assertRaises(RuntimeError):m.tick(True,[],{},self.p,fail)
  self.assertTrue(json.loads(self.p.read_text())['active']);m.tick(True,[],{},self.p,self.sender);self.assertFalse(json.loads(self.p.read_text())['active'])
 def test_real_http_mock_and_pending_readback_retry(self):
  calls=[];store={};fail_get=[True]
  class H(BaseHTTPRequestHandler):
   def log_message(self,format,*a):pass
   def do_POST(self):
    calls.append(('POST',self.path,self.headers.get('Authorization')));body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));store['body']=dict(body,id='42',channel_id=m.CHANNEL,mentions=[]);self.send_response(200);self.end_headers();self.wfile.write(json.dumps(store['body']).encode())
   def do_GET(self):
    calls.append(('GET',self.path,self.headers.get('Authorization')))
    if fail_get[0]:self.send_response(503);self.end_headers();return
    self.send_response(200);self.end_headers();self.wfile.write(json.dumps(store['body']).encode())
  server=HTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch.dict(os.environ,{'MGS_DR_DISCORD_API_BASE':f'http://127.0.0.1:{server.server_port}','MGS_DISCORD_BOT_TOKEN_OVERRIDE':'mock-only-not-a-secret'}):
    with self.assertRaises(Exception):m.tick(False,['a'],{},self.p,m.deliver)
    self.assertIn('pending_delivery',json.loads(self.p.read_text()));fail_get[0]=False
    self.assertFalse(m.tick(False,['a'],{},self.p,m.deliver));self.assertEqual(len([x for x in calls if x[0]=='POST']),1);self.assertTrue(all(x[2]=='Bot mock-only-not-a-secret' for x in calls));self.assertTrue(all(m.CHANNEL in x[1] for x in calls));self.assertNotIn('pending_delivery',json.loads(self.p.read_text()))
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
