"""Zeus-only live BM reader. Credentials never leave this host or reach the browser.
Rodolfo 1546618148571058266 + explicit live 'sim' for systemd auxiliary service.
"""
import pathlib,sys,os,json,importlib.util,time,datetime,re,fcntl,argparse,subprocess
ROOT=pathlib.Path(__file__).resolve().parent;STATE=ROOT/'private/meta-lookup-worker-state.json';sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import secret
_SSH_SECRET=None;_SSH_AT=0
def ssh(command,input_data=None,timeout=180):
 global _SSH_SECRET,_SSH_AT
 if not _SSH_SECRET or time.monotonic()-_SSH_AT>86400:
  _SSH_SECRET=secret('Runcloud Server 01 - 162.55.28.178- zeus Acesso','password');_SSH_AT=time.monotonic()
 r,w=os.pipe();os.write(w,(_SSH_SECRET+'\n').encode());os.close(w)
 try:
  p=subprocess.run(['sshpass','-d',str(r),'ssh','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','ConnectTimeout=20','zeus@162.55.28.178',command],pass_fds=(r,),input=input_data,capture_output=True,timeout=timeout)
 finally:os.close(r)
 if p.returncode:raise RuntimeError('SSH queue transport exit='+str(p.returncode))
 return p.stdout.decode()
os.environ['ARES_META_TOKEN_CACHE_PATH']='/root/.cache/mgs/finance-bm-inventory-meta-token.json'
spec=importlib.util.spec_from_file_location('meta','/root/mgs-agent/scripts/ares-meta-common.py');meta=importlib.util.module_from_spec(spec);spec.loader.exec_module(meta)
BM='155263197283282';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';STAGE='/var/tmp/mgs-finance-origin-1546618148571058266'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def inventory():
 cfg=json.loads(pathlib.Path('/root/mgs-agent/data/ares/meta-ads/accounts/1034081997659047.json').read_text())['accounts'][0];token,_=meta.get_token_from_1password(os.environ.get('FINANCE_META_ITEM') or 'APP NOVO 02/09 Token Meta API - Contas de Anuncio Meta - Roosevelt Mattei')
 status,business,_=meta.graph_get(BM,token,{'fields':'id,name'})
 if status!=200 or business.get('id')!=BM or business.get('name')!='Digital Trust':raise RuntimeError('BM identity/access unavailable')
 out={};pages=0
 for edge in ['owned_ad_accounts','client_ad_accounts']:
  params={'fields':'id,account_id,name,currency,timezone_name','limit':100};seen=set()
  while True:
   status,d,_=meta.graph_get(BM+'/'+edge,token,params)
   if status!=200:raise RuntimeError('BM inventory HTTP '+str(status)+' code '+str(d.get('error',{}).get('code')))
   pages+=1
   for a in d.get('data',[]):
    if not re.fullmatch(r'\d{5,30}',a.get('account_id','')) or a.get('id')!='act_'+a['account_id']:raise RuntimeError('Meta identity mismatch')
    result={'account_id':a['account_id'],'name':a['name'],'currency':a['currency'],'timezone':a.get('timezone_name'),'business_id':BM}
    if a['account_id'] in out and out[a['account_id']]!=result:raise RuntimeError('Conflicting BM account metadata')
    out[a['account_id']]=result
   if not d.get('paging',{}).get('next'):break
   cursor=d.get('paging',{}).get('cursors',{}).get('after')
   if not cursor or cursor in seen or pages>100:raise RuntimeError('Incomplete BM pagination')
   seen.add(cursor);params['after']=cursor
 return out,pages

def tick(target):
 rows=json.loads(ssh('sudo -n -u mgsfinance python3 '+target+'/deploy/meta-lookup-queue.py wait',timeout=65))
 if not rows:return {'ok':True,'pending':0,'checked_at':now()}
 active=[r for r in rows if time.time()-datetime.datetime.fromisoformat(r['requested_at']).timestamp()<120]
 accounts,pages=inventory() if active else ({},0);out=[]
 for r in rows:
  row={**r,'verified_at':now()}
  if r not in active:row.update(status='error',error='Consulta expirada. Informe o ID novamente.')
  elif r['account_id'] not in accounts:row.update(status='error',error='ID não localizado nas contas da BM Digital Trust. Nenhum cadastro foi feito.')
  elif not accounts[r['account_id']].get('timezone'):row.update(status='error',error='A BM não retornou o fuso horário. Cadastro bloqueado para não inventar dados.')
  else:row.update(accounts[r['account_id']],status='ready')
  out.append(row)
 rb=json.loads(ssh('sudo -n -u mgsfinance python3 '+target+'/deploy/meta-lookup-queue.py complete',json.dumps(out).encode(),timeout=45));assert rb['readback'] and set(rb['completed'])=={r['request_id'] for r in rows}
 return {'ok':True,'completed':len(rows),'bm_accounts':len(accounts),'pages':pages,'checked_at':now(),'meta_writes':0}
def write_state(out):
 p=STATE.with_suffix('.pending');p.write_text(json.dumps(out));p.chmod(0o600);os.replace(p,STATE)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');parser.add_argument('--stage',action='store_true');parser.add_argument('--probe');a=parser.parse_args()
 if a.probe:
  assert re.fullmatch(r'\d{5,30}',a.probe);data,pages=inventory();print(json.dumps({'account':data.get(a.probe),'accounts':len(data),'pages':pages,'meta_writes':0},ensure_ascii=False));raise SystemExit(0)
 with (ROOT/'private/meta-lookup-worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);streak=0
  while True:
   try:
    out=tick(STAGE if a.stage else TARGET);streak=0;write_state(out)
    if a.once:print(json.dumps(out));break
   except Exception as e:
    streak+=1;write_state({'ok':False,'consecutive_failures':streak,'diagnostic':type(e).__name__,'checked_at':now()});print('Meta lookup failed: '+type(e).__name__+' streak='+str(streak),flush=True)
    if a.once:raise SystemExit(1)
    if streak in [3,5]:subprocess.run(['/root/mgs-agent/scripts/send-report-infra-embed.sh','--action','alerta','--type','finance-meta-lookup','--path',str(STATE),'--reason','Consulta BM da dash requer investigação; falhas consecutivas '+str(streak),'--evidence','Sem escrita na Meta/credenciais. Consulte estado seguro e journal. '+('Serviço bloqueado após 5 falhas.' if streak==5 else 'Retry seguro em andamento.')],capture_output=True,timeout=50)
    if streak>=5:raise SystemExit(0)
    time.sleep(min(60,streak*10))
