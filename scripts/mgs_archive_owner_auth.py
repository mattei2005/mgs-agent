#!/usr/bin/env python3
"""Isolated owner-connector authorization. No agent OAuth fallback or media writer.
Secrets remain in memory and 1Password; production stays disabled.
"""
from __future__ import annotations
import argparse,base64,hashlib,hmac,html,json,re,secrets,subprocess,time
from datetime import datetime,timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode,urlsplit,parse_qs
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import ares_archive_bridge as b
APPROVAL='1562888530265374731'
DRIVE_SCOPE='https://www.googleapis.com/auth/drive'
VAULT_ID='ghkdcenuzsp57w37nzhxuxnkj4'
TITLE='MGS Drive 30TB - Owner Connector OAuth'
WRAPPER='/root/mgs-agent/scripts/mgs-op-with-service-account.sh'
HOME=b.DATA/'owner-connector'
CONFIG=HOME/'config.json'
PROOF=HOME/'authorization-proof.json'
ORIGIN='https://mgs-zeus-vps.tail3b0269.ts.net:8443'
class AuthError(RuntimeError):pass

def op(args,payload=None):
 try:r=subprocess.run([WRAPPER,*args],input=json.dumps(payload) if payload is not None else None,capture_output=True,text=True,timeout=45)
 except subprocess.TimeoutExpired:raise AuthError('VAULT_TIMEOUT') from None
 if r.returncode:raise AuthError('VAULT_COMMAND_FAILED')
 try:return json.loads(r.stdout)
 except ValueError:raise AuthError('VAULT_RESPONSE_INVALID') from None

class Vault:
 def __init__(self,cfg):self.cfg=cfg
 def item(self):
  v=op(['item','get',self.cfg['item_id'],'--vault',self.cfg['vault_id'],'--format','json'])
  if v.get('id')!=self.cfg['item_id'] or v.get('vault',{}).get('id')!=self.cfg['vault_id'] or v.get('title')!=TITLE:raise AuthError('VAULT_ITEM_BINDING')
  return v
 def fields(self):return {f['id']:f.get('value','') for f in self.item().get('fields',[]) if f.get('id')}
 def save_refresh(self,value):
  current=self.item();fields=current.get('fields',[]);f=next((x for x in fields if x.get('id')=='refresh_token'),None)
  if not f:raise AuthError('VAULT_REFRESH_FIELD_MISSING')
  f['value']=value;payload={k:current[k] for k in ('title','category','fields','sections','tags','urls') if k in current}
  op(['item','edit',self.cfg['item_id'],'--vault',self.cfg['vault_id'],'--format','json'],payload)
  got=self.item();v={x['id']:x.get('value','') for x in got.get('fields',[]) if x.get('id')}
  if v.get('refresh_token')!=value or v.get('approval_message_id')!=APPROVAL:raise AuthError('VAULT_REFRESH_READBACK')
  return got.get('version')

class Google:
 def request(self,url,*,data=None,access=None):
  headers={'Accept':'application/json','User-Agent':'MGS-Archive-Owner/1'}
  if access:headers['Authorization']='Bearer '+access
  if data is not None:headers['Content-Type']='application/x-www-form-urlencoded';data=urlencode(data).encode()
  try:
   with urlopen(Request(url,data=data,headers=headers),timeout=30) as response:return json.load(response)
  except HTTPError as e:raise AuthError('GOOGLE_HTTP_'+str(e.code)) from None
  except (URLError,ValueError,TimeoutError):raise AuthError('GOOGLE_NETWORK_OR_RESPONSE') from None
 def exchange(self,client,code,verifier,redirect):return self.request('https://oauth2.googleapis.com/token',data={'client_id':client['client_id'],'client_secret':client['client_secret'],'code':code,'code_verifier':verifier,'redirect_uri':redirect,'grant_type':'authorization_code'})
 def refresh(self,client,refresh):return self.request('https://oauth2.googleapis.com/token',data={'client_id':client['client_id'],'client_secret':client['client_secret'],'refresh_token':refresh,'grant_type':'refresh_token'})
 def identity(self,access):return self.request('https://www.googleapis.com/drive/v3/about?'+urlencode({'fields':'user(emailAddress,permissionId)'}),access=access).get('user',{})
 def root(self,access,root_id):return self.request('https://www.googleapis.com/drive/v3/files/'+root_id+'?'+urlencode({'supportsAllDrives':'true','fields':'id,mimeType,trashed,driveId,owners(emailAddress,permissionId),capabilities(canAddChildren)'}),access=access)

class OwnerAuthorization:
 def __init__(self,cfg,vault,google,clock=time.monotonic):self.cfg=cfg;self.vault=vault;self.google=google;self.clock=clock;self.csrf={};self.pending={}
 def issue_csrf(self):
  self.csrf={k:v for k,v in self.csrf.items() if self.clock()-v<=600};token=secrets.token_urlsafe(32);self.csrf[token]=self.clock();return token
 def client(self):
  f=self.vault.fields()
  if f.get('approval_message_id')!=APPROVAL:raise AuthError('APPROVAL_BINDING')
  if not re.fullmatch(r'[0-9]+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com',f.get('client_id','')) or not f.get('client_secret'):raise AuthError('CLIENT_CONFIGURATION_REQUIRED')
  return dict(f)
 def begin(self,cookie,form,origin):
  if origin!=self.cfg['public_origin']:raise AuthError('ORIGIN_REJECTED')
  if not cookie or not form or not hmac.compare_digest(cookie,form) or cookie not in self.csrf or self.clock()-self.csrf.pop(cookie)>600:raise AuthError('CSRF_REJECTED')
  client=self.client();state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64);self.pending={k:v for k,v in self.pending.items() if self.clock()-v['at']<=600};self.pending[state]={'at':self.clock(),'verifier':verifier,'client':client}
  challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
  return 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':client['client_id'],'redirect_uri':self.cfg['redirect_uri'],'response_type':'code','scope':DRIVE_SCOPE,'access_type':'offline','prompt':'consent','login_hint':self.cfg['owner_email'],'state':state,'code_challenge':challenge,'code_challenge_method':'S256'})
 def complete(self,state,code):
  pending=self.pending.pop(state,None)
  if not pending or self.clock()-pending['at']>600 or not code:raise AuthError('STATE_INVALID_OR_EXPIRED')
  token=self.google.exchange(pending['client'],code,pending['verifier'],self.cfg['redirect_uri']);refresh=token.get('refresh_token')
  if set(token.get('scope','').split())!={DRIVE_SCOPE}:raise AuthError('SCOPE_NOT_EXACT')
  if not refresh or not token.get('access_token'):raise AuthError('REFRESH_OR_ACCESS_TOKEN_MISSING')
  refreshed=self.google.refresh(pending['client'],refresh)
  if not refreshed.get('access_token') or (refreshed.get('scope') and set(refreshed['scope'].split())!={DRIVE_SCOPE}):raise AuthError('REFRESH_SCOPE_OR_TOKEN')
  user=self.google.identity(refreshed['access_token'])
  if user.get('emailAddress')!=self.cfg['owner_email'] or user.get('permissionId')!=self.cfg['owner_permission_id']:raise AuthError('OWNER_IDENTITY_MISMATCH')
  root=self.google.root(refreshed['access_token'],self.cfg['archive_root_id'])
  if root.get('id')!=self.cfg['archive_root_id'] or root.get('trashed') is not False or root.get('driveId') or root.get('mimeType')!='application/vnd.google-apps.folder' or root.get('capabilities',{}).get('canAddChildren') is not True or not any(o.get('emailAddress')==self.cfg['owner_email'] and o.get('permissionId')==self.cfg['owner_permission_id'] for o in root.get('owners',[])):raise AuthError('ARCHIVE_ROOT_BINDING')
  current=self.vault.fields()
  if any(current.get(k)!=pending['client'].get(k) for k in ('client_id','client_secret','approval_message_id')):raise AuthError('CREDENTIAL_ITEM_CHANGED_DURING_CONSENT')
  version=self.vault.save_refresh(refresh)
  return {'schema':'mgs.owner.connector.authorization.v1','approval_message_id':APPROVAL,'authorized_at':datetime.now(timezone.utc).isoformat(),'owner_email':user['emailAddress'],'owner_permission_id':user['permissionId'],'archive_root_id':root['id'],'granted_scope':DRIVE_SCOPE,'refresh_grant_verified':True,'item_version':version,'production_enabled':False}

def validate_config(c):
 if not isinstance(c,dict):raise AuthError('CONFIG_NOT_OBJECT')
 fixed={'approval_message_id':APPROVAL,'owner_email':b.ACCOUNT,'owner_permission_id':b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT],'archive_root_id':b.ARCHIVE_ROOT,'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'vault_id':VAULT_ID,'project_id':'mgs-core-prod','public_origin':ORIGIN,'redirect_uri':ORIGIN+'/callback','bind':'127.0.0.1','port':43171,'production_enabled':False}
 if any(c.get(k)!=v for k,v in fixed.items()) or c.get('production_enabled') is not False or not re.fullmatch(r'[a-z0-9]{26}',str(c.get('item_id',''))):raise AuthError('CONFIG_SCOPE_BINDING')
 return c

def init()->dict:
 if CONFIG.exists():
  c=validate_config(b.read_json(CONFIG))
  Vault(c).item();return c
 HOME.mkdir(mode=0o700,parents=True,exist_ok=True)
 items=op(['item','list','--vault',VAULT_ID,'--format','json']);same=[x for x in items if x.get('title')==TITLE]
 if len(same)>1:raise AuthError('VAULT_DUPLICATE_ITEM')
 if same:item=same[0]
 else:
  fields=[{'id':key,'label':label,'type':kind,'value':value} for key,label,kind,value in [('client_id','Client ID','STRING',''),('client_secret','Client Secret','CONCEALED',''),('refresh_token','Refresh Token - preenchimento automatico','CONCEALED',''),('approval_message_id','Autorizacao Rodolfo','STRING',APPROVAL),('project_id','Projeto Google Cloud','STRING','mgs-core-prod'),('owner_email','Conta autorizada','STRING',b.ACCOUNT)]]
  item=op(['item','create','--vault',VAULT_ID,'--format','json','-'],{'title':TITLE,'category':'API_CREDENTIAL','fields':fields,'tags':['mgs-archive-owner-isolated']})
 c={'schema':'mgs.owner.connector.config.v1','approval_message_id':APPROVAL,'owner_email':b.ACCOUNT,'owner_permission_id':b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT],'project_id':'mgs-core-prod','source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'vault_id':VAULT_ID,'item_id':item['id'],'public_origin':ORIGIN,'redirect_uri':ORIGIN+'/callback','bind':'127.0.0.1','port':43171,'production_enabled':False}
 fields=Vault(c).fields()
 if fields.get('approval_message_id')!=APPROVAL:raise AuthError('VAULT_ITEM_APPROVAL')
 b.atomic_json(CONFIG,validate_config(c));return c

def handler(cfg,auth):
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,format,*args):pass
  def send(self,status,text,*,location=None,cookie=None,json_body=False,referrer_policy='no-referrer',allow_google_redirect=False):
   form_action="'self' https://accounts.google.com" if allow_google_redirect else "'self'"
   self.send_response(status);self.send_header('Content-Type','application/json' if json_body else 'text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy',referrer_policy);self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action "+form_action+"; frame-ancestors 'none'")
   if location:self.send_header('Location',location)
   if cookie:self.send_header('Set-Cookie','mgs_auth_csrf='+cookie+'; Path=/; Secure; HttpOnly; SameSite=Lax')
   self.end_headers();self.wfile.write(text.encode())
  def valid_host(self):return self.headers.get('Host') in (urlsplit(cfg['public_origin']).netloc,'127.0.0.1:'+str(cfg['port']))
  def do_GET(self):
   if not self.valid_host():return self.send(400,'Host invalido')
   parsed=urlsplit(self.path)
   if parsed.path=='/status':
    return self.send(200,json.dumps({'service':'archive-owner-auth','approval_message_id':APPROVAL,'production_enabled':False,'authorization_saved':PROOF.exists()}),json_body=True)
   if parsed.path=='/callback':
    query=parse_qs(parsed.query)
    if len(query.get('state',[]))!=1 or len(query.get('code',[]))!=1:return self.send(400,'Autorizacao nao concluida. Nenhuma credencial foi registrada.')
    try:
     proof=auth.complete(query['state'][0],query['code'][0]);proof.update(report_infra_pending=True,source='private_google_callback')
     b.atomic_json(PROOF,proof)
     with (b.BASE/'logs/events-audit.jsonl').open('a') as audit:
      audit.write(json.dumps({'at':b.now_iso(),'actor':'mgs-owner-connector-auth','action':'new_owner_oauth_saved_with_native_identity_root_and_refresh_readback','approval_message_id':APPROVAL,'owner_email':proof.get('owner_email'),'item_id':cfg.get('item_id'),'item_version':proof.get('item_version'),'production_enabled':False,'report_infra_pending':True})+'\n')
    except AuthError as e:return self.send(400,'<h1>Autorizacao nao aceita</h1><p>'+html.escape(str(e))+'</p><p>Nenhum arquivo de producao foi alterado. Volte ao inicio para uma nova autorizacao.</p>')
    return self.send(200,'<h1>Conta autorizada e renovacao testada</h1><p>Credencial salva no 1Password; pasta e proprietario verificados. Nenhum arquivo foi migrado ou apagado por esta pagina. A ativacao produtiva ainda depende do canario e handoff do executor.</p>')
   if parsed.path!='/':return self.send(404,'Nao encontrado')
   csrf=auth.issue_csrf()
   page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Autorizacao privada - Arquivo 30 TB</title><style>body{font:18px system-ui;max-width:850px;margin:50px auto;padding:20px;line-height:1.5}code{overflow-wrap:anywhere;background:#eef;padding:4px}button{font-size:18px;padding:14px}li{margin:14px 0}</style><h1>Conector privado do arquivo 30 TB</h1><p>Esta e a configuracao inicial aprovada por Rodolfo. Nao e uma troca de hash no Apps Script e esta pagina nao migra ou exclui arquivos.</p><h2>1. Configuracao inicial Google</h2><p>No seu navegador normal, entre na conta administrativa do projeto <strong>mgs-core-prod</strong> e abra <a href="https://console.cloud.google.com/auth/clients?project=mgs-core-prod" target="_blank" rel="noopener">Google Auth Platform - Clientes</a>.</p><ol><li>Crie um cliente NOVO, tipo <strong>Aplicativo da Web</strong>, nome <strong>MGS Arquivo 30TB - Conector VPS</strong>. Nao reutilize cliente/token antigo.</li><li>URI de redirecionamento autorizada: <code>REDIRECT</code></li><li>Se o Google pedir configurar o aplicativo: nome MGS Arquivo 30TB, publico externo e suporte sob uma conta administradora valida. Para operacao duravel, nao deixar o app no modo de testes de sete dias; usar publicacao de uso privado conforme as regras Google. Se o Google bloquear publicacao/verificacao ou faltar acesso ao projeto, pare e informe a mensagem; nao mude billing ou IAM.</li></ol><h2>2. Guardar somente no 1Password</h2><p>No cofre <strong>MGS Conteudo</strong>, item <strong>MGS Drive 30TB - Owner Connector OAuth</strong>, preencha somente <strong>Client ID</strong> e <strong>Client Secret</strong> do cliente novo. Nao envie JSON, segredo ou codigo pelo Discord. O campo Refresh Token e preenchido automaticamente pelo servidor.</p><h2>3. Autorizar a conta dos 30 TB</h2><p>Depois de salvar o item, use o botao e escolha exclusivamente <strong>mgsdigitalcorp@gmail.com</strong>. O Google pedira acesso ao Drive; o conector valida o proprietario e a pasta e mantem producao desativada ate os testes reais. Os agentes continuam na Service Account.</p><form method="post" action="/start"><input type="hidden" name="csrf" value="CSRF"><button>Autorizar conta dos 30 TB</button></form></html>'''
   return self.send(200,page.replace('REDIRECT',html.escape(cfg['redirect_uri'])).replace('CSRF',html.escape(csrf)),cookie=csrf,referrer_policy='same-origin',allow_google_redirect=True)
  def do_POST(self):
   if not self.valid_host() or urlsplit(self.path).path!='/start':return self.send(400,'Rota invalida')
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=2048:raise AuthError('REQUEST_SIZE')
    data=parse_qs(self.rfile.read(size).decode());cookies=SimpleCookie(self.headers.get('Cookie',''));cookie=cookies.get('mgs_auth_csrf');forms=data.get('csrf',[])
    if len(forms)!=1:raise AuthError('CSRF_REJECTED')
    url=auth.begin(cookie.value if cookie else '',forms[0],self.headers.get('Origin',''))
   except (AuthError,ValueError) as e:
    code=str(e) if isinstance(e,AuthError) else 'REQUEST_INVALID'
    messages={'ORIGIN_REJECTED':'A origem desta solicitacao foi rejeitada. Volte a pagina inicial HTTPS e recarregue antes de tentar novamente.','CSRF_REJECTED':'A sessao desta pagina expirou ou nao corresponde ao formulario. Reabra a pagina inicial HTTPS.','CLIENT_CONFIGURATION_REQUIRED':'Primeiro crie o cliente novo em Google Auth Platform - Clientes, projeto mgs-core-prod, e salve Client ID e Client Secret somente no item do conector no 1Password. Depois volte a pagina inicial. Nenhum consentimento Google foi iniciado.'}
    message=messages.get(code,'Configuracao ou solicitacao nao aceita. Volte a pagina inicial para conferir a etapa pendente.')
    return self.send(400,'<h1>Configuracao pendente</h1><p>'+html.escape(code)+'</p><p>'+html.escape(message)+'</p><p>Nenhum arquivo foi alterado.</p><p><a href="/">Voltar ao inicio</a></p>')
   return self.send(303,'',location=url)
 return Handler

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['init','status','serve']);args=parser.parse_args()
 c=init()
 if args.action=='init':print(json.dumps({k:c[k] for k in ['approval_message_id','item_id','vault_id','public_origin','redirect_uri','production_enabled']}));return 0
 if args.action=='status':
  fields=Vault(c).fields();print(json.dumps({'client_id_present':bool(fields.get('client_id')),'client_secret_present':bool(fields.get('client_secret')),'refresh_token_present':bool(fields.get('refresh_token')),'production_enabled':False,'authorization_saved':PROOF.exists()}));return 0
 auth=OwnerAuthorization(c,Vault(c),Google());server=ThreadingHTTPServer((c['bind'],c['port']),handler(c,auth));server.serve_forever()
if __name__=='__main__':raise SystemExit(main())
