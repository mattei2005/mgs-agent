"""Offline fixtures: never Google production proof."""
import importlib,sys,unittest,urllib.parse
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
a=importlib.import_module('mgs_archive_owner_auth')
class OwnerAuthTests(unittest.TestCase):
 def setUp(self):
  self.cfg={'approval_message_id':'1562888530265374731','owner_email':'mgsdigitalcorp@gmail.com','owner_permission_id':'03783617840924670288','archive_root_id':'1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J','redirect_uri':'https://host.example:8443/callback','public_origin':'https://host.example:8443'}
  self.item={'client_id':'123-fixture.apps.googleusercontent.com','client_secret':'OFFLINE_FIXTURE','approval_message_id':self.cfg['approval_message_id'],'refresh_token':''}
  self.v=Mock();self.v.fields.return_value=self.item;self.v.save_refresh.return_value=7
  self.g=Mock();self.g.exchange.return_value={'access_token':'OFFLINE_ACCESS','refresh_token':'OFFLINE_REFRESH','scope':a.DRIVE_SCOPE};self.g.refresh.return_value={'access_token':'OFFLINE_REFRESHED','scope':a.DRIVE_SCOPE}
  self.g.identity.return_value={'emailAddress':self.cfg['owner_email'],'permissionId':self.cfg['owner_permission_id']}
  self.g.root.return_value={'id':self.cfg['archive_root_id'],'mimeType':'application/vnd.google-apps.folder','trashed':False,'owners':[self.g.identity.return_value],'capabilities':{'canAddChildren':True}}
  self.clock=[100.0];self.auth=a.OwnerAuthorization(self.cfg,self.v,self.g,lambda:self.clock[0]);self.csrf=self.auth.issue_csrf()
 def start(self):
  url=self.auth.begin(self.csrf,self.csrf,self.cfg['public_origin']);q=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query);return q['state'][0],q
 def test_begin_requires_exact_origin(self):
  with self.assertRaisesRegex(a.AuthError,'ORIGIN'):self.auth.begin(self.csrf,self.csrf,'https://evil.example')
 def test_begin_requires_csrf_pair(self):
  with self.assertRaisesRegex(a.AuthError,'CSRF'):self.auth.begin('wrong',self.csrf,self.cfg['public_origin'])
 def test_begin_does_not_put_client_secret_in_link(self):
  state,q=self.start();self.assertEqual(q['scope'],[a.DRIVE_SCOPE]);self.assertEqual(q['access_type'],['offline']);self.assertEqual(q['prompt'],['consent']);self.assertEqual(q['code_challenge_method'],['S256']);self.assertNotIn('client_secret',q)
 def test_empty_client_stops_before_google(self):
  self.item['client_secret']=''
  with self.assertRaisesRegex(a.AuthError,'CLIENT_CONFIGURATION'):self.start()
  self.g.exchange.assert_not_called()
 def test_wrong_approval_rejects_credential_item(self):
  self.item['approval_message_id']='other'
  with self.assertRaisesRegex(a.AuthError,'APPROVAL'):self.start()
 def test_bad_state_never_exchanges(self):
  self.start()
  with self.assertRaisesRegex(a.AuthError,'STATE'):self.auth.complete('wrong','code')
  self.g.exchange.assert_not_called()
 def test_expired_state_stops(self):
  state,q=self.start();self.clock[0]+=601
  with self.assertRaisesRegex(a.AuthError,'STATE'):self.auth.complete(state,'code')
 def test_valid_callback_verifies_refresh_owner_root_and_saves_only_vault(self):
  state,q=self.start();proof=self.auth.complete(state,'OFFLINE_CODE');self.assertEqual(proof['owner_email'],self.cfg['owner_email']);self.assertEqual(proof['item_version'],7);self.assertFalse(proof['production_enabled']);self.v.save_refresh.assert_called_once_with('OFFLINE_REFRESH');self.assertNotIn('OFFLINE_REFRESH',str(proof));self.g.refresh.assert_called_once()
 def test_callback_cannot_replay(self):
  state,q=self.start();self.auth.complete(state,'OFFLINE_CODE')
  with self.assertRaisesRegex(a.AuthError,'STATE'):self.auth.complete(state,'OFFLINE_CODE')
  self.g.exchange.assert_called_once()
 def test_wrong_owner_never_stores_refresh(self):
  state,q=self.start();self.g.identity.return_value['emailAddress']='wrong@example.com'
  with self.assertRaisesRegex(a.AuthError,'OWNER'):self.auth.complete(state,'OFFLINE_CODE')
  self.v.save_refresh.assert_not_called()
 def test_wrong_native_id_never_stores_refresh(self):
  state,q=self.start();self.g.identity.return_value['permissionId']='changed'
  with self.assertRaisesRegex(a.AuthError,'OWNER'):self.auth.complete(state,'OFFLINE_CODE')
  self.v.save_refresh.assert_not_called()
 def test_wrong_archive_owner_never_stores_refresh(self):
  state,q=self.start();self.g.root.return_value['owners']=[{'emailAddress':'wrong','permissionId':'wrong'}]
  with self.assertRaisesRegex(a.AuthError,'ROOT'):self.auth.complete(state,'OFFLINE_CODE')
  self.v.save_refresh.assert_not_called()
 def test_no_refresh_is_not_success(self):
  state,q=self.start();self.g.exchange.return_value.pop('refresh_token')
  with self.assertRaisesRegex(a.AuthError,'REFRESH'):self.auth.complete(state,'OFFLINE_CODE')
  self.v.save_refresh.assert_not_called()
 def test_unexpected_scopes_do_not_expand_authority(self):
  state,q=self.start();self.g.exchange.return_value['scope']=a.DRIVE_SCOPE+' https://mail.google.com/'
  with self.assertRaisesRegex(a.AuthError,'SCOPE'):self.auth.complete(state,'OFFLINE_CODE')
  self.v.save_refresh.assert_not_called()
 def test_failed_exchange_consumes_state_and_does_not_save(self):
  state,q=self.start();self.g.exchange.side_effect=a.AuthError('GOOGLE_TOKEN_HTTP_400')
  with self.assertRaises(a.AuthError):self.auth.complete(state,'OFFLINE_CODE')
  with self.assertRaisesRegex(a.AuthError,'STATE'):self.auth.complete(state,'OFFLINE_CODE')
  self.v.save_refresh.assert_not_called()
class PrivateHttpTests(unittest.TestCase):
 def setUp(self):
  import threading,os,tempfile
  from unittest.mock import patch
  self.tmp=tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR','/root/.hermes/profiles/zeus/cache/scratch'));self.override=patch.object(a,'PROOF',Path(self.tmp.name)/'proof.json');self.override.start()
  self.cfg={'public_origin':'https://private.example:8443','port':0};self.auth=Mock();self.auth.issue_csrf.return_value='OFFLINE_CSRF';self.auth.begin.return_value='https://accounts.google.com/o/oauth2/v2/auth?client_id=fixture'
  self.server=a.ThreadingHTTPServer(('127.0.0.1',0),a.handler(self.cfg,self.auth));self.cfg['port']=self.server.server_port;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.override.stop();self.tmp.cleanup()
 def request(self,method,path,body=None,headers=None):
  import http.client
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5);c.request(method,path,body=body,headers=headers or {});r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read().decode());c.close();return result
 def test_live_status_endpoint_has_no_secrets_or_production_claim(self):
  status,headers,body=self.request('GET','/status');self.assertEqual(status,200);self.assertFalse(__import__('json').loads(body)['production_enabled']);self.assertNotIn('client_secret',body)
 def test_landing_page_is_private_setup_not_fake_oauth_link(self):
  self.cfg['redirect_uri']='https://private.example:8443/callback';status,headers,body=self.request('GET','/');self.assertEqual(status,200);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('Secure',headers['Set-Cookie']);self.assertIn('no-store',headers['Cache-Control']);self.assertIn('mgs-core-prod',body);self.assertNotIn('OFFLINE_REFRESH',body)
 def test_wrong_host_is_rejected(self):self.assertEqual(self.request('GET','/status',headers={'Host':'evil.example'})[0],400)
 def test_unknown_route_has_no_config_dump(self):self.assertEqual(self.request('GET','/config')[0],404)
 def test_callback_without_transaction_is_rejected(self):self.assertEqual(self.request('GET','/callback?code=x')[0],400);self.auth.complete.assert_not_called()
 def test_valid_start_issues_only_google_redirect(self):
  status,headers,body=self.request('POST','/start','csrf=OFFLINE_CSRF',{'Origin':self.cfg['public_origin'],'Cookie':'mgs_auth_csrf=OFFLINE_CSRF','Content-Type':'application/x-www-form-urlencoded'});self.assertEqual(status,303);self.assertTrue(headers['Location'].startswith('https://accounts.google.com/'));self.auth.begin.assert_called_once()
 def test_oversized_request_is_rejected_before_auth(self):
  self.assertEqual(self.request('POST','/start','x'*2049)[0],400);self.auth.begin.assert_not_called()
 def test_callback_failure_never_saves_public_success_proof(self):
  self.auth.complete.side_effect=a.AuthError('STATE_INVALID_OR_EXPIRED');self.assertEqual(self.request('GET','/callback?state=wrong&code=fixture')[0],400);self.assertFalse(a.PROOF.exists())
 def test_callback_success_saves_only_public_proof_and_keeps_production_off(self):
  self.auth.complete.return_value={'owner_email':'mgsdigitalcorp@gmail.com','production_enabled':False};status,headers,body=self.request('GET','/callback?state=fixture&code=fixture');self.assertEqual(status,200);self.assertTrue(a.PROOF.exists());self.assertNotIn('access_token',a.PROOF.read_text())
if __name__=='__main__':unittest.main()

