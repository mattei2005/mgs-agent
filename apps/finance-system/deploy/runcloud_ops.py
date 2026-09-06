"""Bounded deployment helpers. Credentials remain in 1Password/memory."""
import os,json,subprocess,urllib.request,urllib.error,pathlib,datetime
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system')
STATE=ROOT/'private/deployment-1545928620462313645'
STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
VAULT=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
def op(args,payload=None):
 r=subprocess.run(['op']+args,input=None if payload is None else json.dumps(payload),capture_output=True,text=True,timeout=60)
 if r.returncode:raise RuntimeError('1Password operation failed: '+args[0])
 return json.loads(r.stdout)
def secret(item,field):
 o=op(['item','get',item,'--vault',VAULT,'--format','json'])
 return next(f['value'] for f in o['fields'] if f.get('label')==field or f.get('id')==field)
def api(base,token,method,path,payload=None):
 q=urllib.request.Request(base+path,data=None if payload is None else json.dumps(payload).encode(),method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/json','Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(q,timeout=60) as f:return json.load(f)
 except urllib.error.HTTPError as e:
  body=e.read().decode(errors='replace')
  try:d=json.loads(body);msg=d.get('errors',d.get('message',''))
  except Exception:msg='unparsed response'
  raise RuntimeError(f'API {method} {path} HTTP {e.code}; validation={str(msg)[:1200]}') from None

def rc(method,path,payload=None):return api('https://manage.runcloud.io/api/v3',secret('RunCloud API - MGS','runcloud_api_key_token'),method,path,payload)
def cf(method,path,payload=None):return api('https://api.cloudflare.com/client/v4',secret('Cloudflare MGS Admin Token - mattei20052','token'),method,path,payload)
def unwrap(d):return d.get('data',d)
def list_rc(path):
 items=[];page=1
 while True:
  d=rc('GET',path+('&' if '?' in path else '?')+f'perPage=40&page={page}');items.extend(d['data']);m=d.get('meta',{});pages=int(m.get('lastPage') or m.get('pagination',{}).get('total_pages') or 1)
  if page>=pages:break
  page+=1
 return items

def ssh(command,input_data=None,timeout=180):
 pw=secret('Runcloud Server 01 - 162.55.28.178- zeus Acesso','password');r,w=os.pipe();os.write(w,(pw+'\n').encode());os.close(w)
 try:
  p=subprocess.run(['sshpass','-d',str(r),'ssh','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','ConnectTimeout=20','zeus@162.55.28.178',command],pass_fds=(r,),input=input_data,capture_output=True,timeout=timeout)
 finally:os.close(r)
 if p.returncode:raise RuntimeError('SSH command failed exit='+str(p.returncode)+' '+p.stderr.decode(errors='replace')[-1500:]+p.stdout.decode(errors='replace')[-1500:])
 return p.stdout.decode(errors='replace')
def save(name,data):
 p=STATE/(name+'.json');p.write_text(json.dumps(data,ensure_ascii=False,indent=2));p.chmod(0o600)
def load(name):return json.loads((STATE/(name+'.json')).read_text())
def audit(event,**fields):
 with pathlib.Path('/root/mgs-agent/logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'agent':'zeus','event':event,'authorization':'1545928620462313645',**fields})+'\n')
