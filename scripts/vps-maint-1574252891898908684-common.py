#!/usr/bin/env python3
"""Shared pure checks and durable receipts for the approved Hostinger reboot."""
import datetime,fcntl,hashlib,importlib.util,json,os,pathlib,re,sqlite3,subprocess,time,urllib.request
P=pathlib.Path
ROOT=P('/root/mgs-agent')
B=P('/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-hostinger/reboot-preparation')
AUTH='1574551205768732753';THREAD='1574249078584377544';REQUEST='1574252891898908684';ID='VPS-MAINT-'+REQUEST
VALIDATOR='mgs-vps-maint-1574252891898908684-validate.service'
CLOSURE='mgs-vps-maint-1574252891898908684-close.service'
SCOPE='/root/.hermes/profiles/zeus/sessions';KEY='agent:main:discord:thread:'+THREAD+':'+THREAD
HANDOFF='Reinicialização da Hostinger agendada. O procedimento externo só inicia após o encerramento desta resposta e valida o novo kernel e a reconexão de Zeus, Atena e Ares.\n\nA conclusão será publicada nesta thread. Os outros servidores e o dashboard não serão alterados nesta etapa.'
ENV={**os.environ,'LC_ALL':'C','NEEDRESTART_MODE':'l','DEBIAN_FRONTEND':'noninteractive'}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(args,timeout=120,check=True):
 r=subprocess.run([str(a) for a in args],capture_output=True,text=True,timeout=timeout,env=ENV)
 if check and r.returncode:raise RuntimeError(str(args[0])+' rc='+str(r.returncode))
 return r

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def atomic(path,value):
 path=P(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.new-'+str(os.getpid()))
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def load(path):return json.loads(P(path).read_text())
def audit(action,**extra):
 with open(ROOT/'logs/events-audit.jsonl','a') as f:
  fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':now(),'agent':'zeus','action':action,'request_id':REQUEST,'thread_id':THREAD,'authorization_message_id':AUTH,**extra},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def unit(name):return dict(l.split('=',1) for l in run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','SubState','-p','UnitFileState','-p','LoadState','-p','ExecStart']).stdout.splitlines() if '=' in l)
def source_turn(entries):
 rows=[r for r in entries if r['scope']==SCOPE and r['key']==KEY]
 if len(rows)!=1:raise RuntimeError('missing or ambiguous canonical source routing row')
 return rows[0]
def routing(profile='zeus'):
 path=P('/root/.hermes/profiles')/profile/'state.db'
 with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True,timeout=20) as c:
  return [{'scope':s,'key':k,'entry':json.loads(e)} for s,k,e in c.execute('SELECT scope,session_key,entry_json FROM gateway_routing')]
def all_active_turns():
 active=[]
 for profile in ['zeus','atena','ares']:
  for row in routing(profile):
   if row['entry'].get('active_turn_token'):active.append({'profile':profile,'scope':row['scope'],'key':row['key'],'started_at':row['entry'].get('active_turn_started_at')})
 return active

def discord_get(channel,suffix):
 spec=importlib.util.spec_from_file_location('mgs_discord_poster',ROOT/'scripts/discord-bot-post.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.load_env(m.DEFAULT_ENV)
 token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']
 req=urllib.request.Request('https://discord.com/api/v10/channels/'+str(channel)+'/messages'+suffix,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def post_once(name,text):
 path=B/(name+'-transport.json')
 if path.exists():
  receipt=load(path)
  if receipt.get('message_id'):
   msg=discord_get(THREAD,'/'+receipt['message_id']);assert msg['content']==text;return receipt
  raise RuntimeError('ambiguous prior '+name+' send; do not duplicate')
 payload={'content':text,'allowed_mentions':{'parse':[],'users':[],'roles':[],'replied_user':False}}
 atomic(path,{'state':'posting','at':now(),'text':text})
 r=run([ROOT/'scripts/discord-bot-post.py','--channel-id',THREAD],check=False) if False else subprocess.run([str(ROOT/'scripts/discord-bot-post.py'),'--channel-id',THREAD],input=json.dumps(payload),capture_output=True,text=True,timeout=60,env=ENV)
 atomic(B/(name+'-stdout.json'),{'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 match=re.search(r'message_id=(\d+)',r.stdout)
 if not match:raise RuntimeError(name+' send result ambiguous; inspect preserved stdout')
 receipt={'state':'posted_pending_readback','message_id':match[1],'at':now()};atomic(path,receipt)
 msg=discord_get(THREAD,'/'+match[1]);assert msg['id']==match[1] and msg['channel_id']==THREAD and msg['author']['id']=='1496296175014252634' and msg['content']==text and not msg.get('mentions')
 receipt['state']='sent_verified';atomic(path,receipt);return receipt

def report_once(reason,evidence):
 path=B/'closure-report-transport.json'
 if path.exists():
  receipt=load(path)
  if not receipt.get('message_id'):raise RuntimeError('ambiguous report send; preserve and reconcile')
 else:
  atomic(path,{'state':'posting','at':now()})
  r=run([ROOT/'scripts/send-report-infra-embed.sh','--action','modificada','--type','VPS/reboot/systemd/data','--path','Hostinger srv1767265; '+VALIDATOR+'; '+CLOSURE+'; data/infra-inventory.json; data/agent-checkpoints.json','--reason',reason,'--evidence',evidence],timeout=120,check=False)
  atomic(B/'closure-report-stdout.json',{'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr});match=re.search(r'message_id=(\d+)',r.stdout)
  if not match:raise RuntimeError('report send ambiguous; inspect stdout before any retry')
  receipt={'at':now(),'message_id':match[1],'state':'posted_pending_readback'};atomic(path,receipt)
 msg=discord_get('1498132022634483894','/'+receipt['message_id']);assert msg['content']=='' and len(msg.get('embeds',[]))==1 and not msg.get('mentions')
 fields={r['name']:r['value'] for r in msg['embeds'][0]['fields']};assert fields['Motivo']==reason[:1000] and fields['Evidência']==evidence[:1000]
 receipt['state']='sent_verified';atomic(path,receipt);return receipt

def mutate_inventory(path,callback):
 path=P(path)
 for attempt in range(5):
  raw=path.read_bytes();d=json.loads(raw);callback(d)
  if path.read_bytes()!=raw:time.sleep(.2);continue
  tmp=path.with_name(path.name+'.owned-'+str(os.getpid()))
  # The production temporary is outside the auto-versioned repository.
  if path==ROOT/'data/infra-inventory.json':tmp=P('/root/.hermes/profiles/zeus/cache/scratch')/('reboot-inventory-'+str(os.getpid())+'.json')
  atomic(tmp,d)
  if path.read_bytes()!=raw:time.sleep(.2);continue
  os.replace(tmp,path);return
 raise RuntimeError('shared inventory changed concurrently')
def inventory_phase(phase,result_path,extra=None):
 def change(d):
  matches=[r for section in d.values() if isinstance(section,list) for r in section if isinstance(r,dict) and r.get('id')==ID];assert len(matches)==1;r=matches[0]
  r.update({'status':phase,'updated_at':now(),'reboot_authorization_message_id':AUTH,'reboot_validation':str(result_path),'reboot_artifacts':{'validator_unit':VALIDATOR,'closure_unit':CLOSURE,'root':str(B),'retention':'disabled_definitions_retained_no_file_deletion'},'reboot_executed':phase not in ['hostinger_reboot_prepared','hostinger_reboot_scheduled']})
  if extra:r.update(extra)
  for item in r.get('ledger',[]):
   if item['target']=='Hostinger reboot':item.update({'state':phase,'source':str(result_path)})
 mutate_inventory(ROOT/'data/infra-inventory.json',change)
def checkpoint(state,next_step):
 run(['/usr/bin/python3',ROOT/'scripts/mgs-knowledge-control.py','checkpoint-upsert','--id',ID,'--agent','zeus','--thread-id',THREAD,'--objective','Manutenção cinco hosts + Node/dashboard e reboots coordenados; preservar fases independentes e gates críticos','--state',state,'--next-step',next_step,'--source',str(B/'postboot-result.json')])

def git_ready(deadline,paths=None):
 paths=paths or ['data/infra-inventory.json','data/agent-checkpoints.json']
 # Persist the original convergence allowance before polling, then each observation.
 if not (B/'closure-git-deadline.json').exists():atomic(B/'closure-git-deadline.json',{'deadline_epoch':deadline,'paths':paths,'at':now()})
 while True:
  run(['git','-C',ROOT,'fetch','origin'],timeout=90)
  h=run(['git','-C',ROOT,'rev-parse','HEAD']).stdout.strip();remote=run(['git','-C',ROOT,'rev-parse','origin/main']).stdout.strip();dirty=run(['git','-C',ROOT,'status','--porcelain','--']+paths).stdout.strip()
  result={'at':now(),'head':h,'origin_main':remote,'scoped_dirty':dirty,'watcher_active':unit('mgs-autocommit.service')['ActiveState']=='active'};atomic(B/'closure-git-observation.json',result)
  if h==remote and not dirty and result['watcher_active']:return result
  if time.time()>=deadline:raise RuntimeError('canonical Git closure did not converge within existing batch deadline')
  time.sleep(10)
