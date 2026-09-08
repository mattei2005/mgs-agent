"""Create approved four users with passwords generated/stored in1Password, never printed."""
import pathlib,sys,json,urllib.request,urllib.error,http.cookiejar
R=pathlib.Path(__file__).resolve().parents[1];S=R/'private/manager-access-1546858367635685396';sys.path.insert(0,str(R/'deploy'));from runcloud_ops import op,secret,VAULT
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();BASE='https://dash.mgsdigitalcorp.com';assert json.loads((S/'published.json').read_text())['pass'];assert json.loads((S/'schema-mgs_finance.json').read_text())['pass']
jar=http.cookiejar.CookieJar();http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));csrf=None

def call(path,body=None):
 headers={'Origin':BASE,'Content-Type':'application/json'}
 if csrf:headers['X-CSRF-Token']=csrf
 req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method='GET' if body is None else 'POST')
 try:
  with http.open(req,timeout=90) as f:return json.load(f)
 except urllib.error.HTTPError as e:raise RuntimeError('HTTP '+str(e.code)+' '+path) from None
call('/api/auth/login',{'username':'rodolfo','password':secret('MGS Finance - rodolfo - dash.mgsdigitalcorp.com','password')});csrf=call('/api/auth/me')['csrf'];users=call('/api/finance/users');existing={x['username']:x for x in users};preserve={k:v for k,v in existing.items() if k in ['rodolfo','nicolas']};items=op(['item','list','--vault',VAULT,'--format','json']);out=[]
try:
 for username,name in [('joe','Joe'),('isliago','Isliago'),('kelly','Kelly'),('icaro','Ícaro')]:
  title='MGS Finance - '+username+' - dash.mgsdigitalcorp.com';match=[i for i in items if i['title']==title];assert len(match)<=1
  if not match:
   item=op(['item','create','--category','login','--vault',VAULT,'--title',title,'--url',BASE+'/login','--generate-password=letters,digits,symbols,32','username='+username,'--tags','MGS,Financeiro','--format','json']);item_id=item['id'];items.append({'title':title,'id':item_id})
  else:item_id=match[0]['id']
  item=op(['item','get',item_id,'--vault',VAULT,'--format','json']);fields={f.get('id'):f.get('value') for f in item['fields']};assert fields.get('username')==username and len(fields.get('password',''))>=14
  (S/(username+'-1password.json')).write_text(json.dumps({'pass':True,'item_id':item_id,'title':title,'username':username,'readback':True,'password_stored':True},ensure_ascii=False,indent=2))
  user=next((u for u in call('/api/finance/users') if u['username']==username),None)
  if user is None:
   call('/api/finance/users',{'username':username,'display_name':name,'email':'','phone':'','discord_id':'','role':'manager','manager_key':username});user=next(u for u in call('/api/finance/users') if u['username']==username);assert not user['enabled']
  assert user['role']=='manager' and user['manager_key']==username and user['display_name']==name
  if not user['enabled']:call('/api/finance/users/'+username+'/credential',{'password':fields['password'],'revision':user['revision']})
  user=next(u for u in call('/api/finance/users') if u['username']==username);assert user['enabled'] and user['role']=='manager' and user['manager_key']==username
  out.append({'pass':True,'username':username,'display_name':name,'manager_key':username,'enabled':True,'revision':user['revision'],'onepassword_item':item_id,'onepassword_title':title});(S/'users-created.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out[-1],ensure_ascii=False))
 final=call('/api/finance/users');assert {u['username']:u for u in final if u['username'] in preserve}==preserve;assert len(out)==4 and len(set(x['username'] for x in out))==4
finally:call('/api/auth/logout',{})
