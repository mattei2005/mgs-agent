from repair_helpers import *
import urllib.request,urllib.error,http.cookiejar
W=Path(__file__).parent;VAULT='ghkdcenuzsp57w37nzhxuxnkj4';BASE='https://dash.mgsdigitalcorp.com'
def password(item):
 d=op(['item','get',item,'--vault',VAULT,'--format','json']);return next(f['value'] for f in d['fields'] if f['id']=='password')
cookies=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
def call(path,payload=None,csrf=None):
 headers={'Origin':BASE,'User-Agent':'MGS-Authorized-Security-Validation/1551287899746598946'}
 if payload is not None:headers['Content-Type']='application/json'
 if csrf:headers['X-CSRF-Token']=csrf
 req=urllib.request.Request(BASE+path,data=None if payload is None else json.dumps(payload).encode(),headers=headers)
 try:
  with client.open(req,timeout=45) as r:
   body=r.read();return r.status,json.loads(body) if 'json' in r.headers.get('Content-Type','') else None
 except urllib.error.HTTPError as e:return e.code,None
r={};r['login_public']=call('/login')[0];r['unauth_health']=call('/api/health')[0]
vault=json.loads((W/'vault-map.json').read_text())
# Active users only: do not implicitly regenerate Kelly's pending enrollment during a smoke.
for u in ['geizian','icaro','isliago','joe','nicolas']:
 code,body=call('/api/auth/login',{'username':u,'password':password(vault[u])});assert code==202 and body.get('mfa_required') is True,(u,code)
 r[u]={'new_password_accepted':True,'mfa_required':True,'no_session_cookie':not bool(list(cookies))}
owner='dsm2vqy6vkvqc5soq45visy6l4';pw=password(owner)
code,body=call('/api/auth/login',{'username':'rodolfo','password':pw});assert code==202 and body.get('mfa_required') is True
p=subprocess.run(['op','item','get',owner,'--vault',VAULT,'--otp'],capture_output=True,text=True,timeout=60);assert p.returncode==0
code,body=call('/api/auth/login',{'username':'rodolfo','password':pw,'otp':p.stdout.strip(),'trust_device':False});assert code==200,code
code,body=call('/api/health');assert code==200 and body.get('production') is True;r['owner_authenticated_health']={'http':code,'production':body.get('production'),'mode':body.get('mode')}
code,me=call('/api/auth/me');assert code==200 and me['username']=='rodolfo'
r['owner_logout']=call('/api/auth/logout',{},csrf=me['csrf'])[0];assert r['owner_logout']==200
r['after_logout_health']=call('/api/health')[0];assert r['after_logout_health']==401
r['kelly']='password/cofre verified by production hash; pending MFA enrollment preserved without regeneration'
(W/'public-auth-validation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
print(sql("SELECT json_build_object('sessions_not_revoked',(SELECT count(*) FROM auth_sessions WHERE NOT revoked),'devices_not_revoked',(SELECT count(*) FROM auth_trusted_devices WHERE NOT revoked),'rotation_audits',(SELECT count(*) FROM audit_events WHERE action='SECURITY_CREDENTIAL_ROTATION' AND after_data->>'authorization'='1551287899746598946'))"))
