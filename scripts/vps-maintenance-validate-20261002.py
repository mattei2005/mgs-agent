#!/usr/bin/env python3
"""Validate an authorized VPS maintenance after boot; no reboot primitive here."""
import argparse,datetime,json,os,pathlib,re,subprocess,tempfile,time,urllib.request,importlib.util
BASE=pathlib.Path('/root/mgs-agent')
CHECKPOINT='ZEUS-VPS-1555704911805808712'
UNIT='mgs-vps-maintenance-1555704911805808712.service'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(args,timeout=120,input=None):
 p=subprocess.run(args,input=input,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(str(args[:3])+' rc='+str(p.returncode)+' '+p.stderr[-250:])
 return p.stdout.strip()
def atomic(path,obj):
 path=pathlib.Path(path);fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
 with os.fdopen(fd,'w') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(name,path.stat().st_mode&0o777 if path.exists() else 0o600);os.replace(name,path)
 assert json.loads(path.read_text())==obj
def audit(event,pre,**kw):
 with (BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'ts':now(),'agent':'zeus','event':event,'authority':pre['authority'],'thread_id':pre['thread_id'],**kw})+'\n');f.flush();os.fsync(f.fileno())
def checkpoint(state,next_step,source):
 return run(['python3',str(BASE/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id',CHECKPOINT,'--agent','zeus','--thread-id','1555704911805808712','--objective','Atualizar somente VPS: pacotes APT/npm, backup, reboot validado; Hermes inalterado','--state',state,'--next-step',next_step,'--source',source])
def inventory(b,pre,status,result=None):
 path=BASE/'data/infra-inventory.json';before=path.read_bytes();d=json.loads(before);items=d.setdefault('runtime_artifacts',[])
 item: dict | None=next((x for x in items if x.get('id')==CHECKPOINT),None)
 if item is None:item={'id':CHECKPOINT,'agent':'zeus','type':'vps_package_maintenance'};items.append(item)
 item.update(status=status,authority=pre['authority'],source_thread_id=pre['thread_id'],backup=str(b),result=str(b/'post-boot-result.json'),validator=str(BASE/'scripts/vps-maintenance-validate-20261002.py'),unit=UNIT,unit_retention='retained_disabled_after_validation; no deletion authorized',updated_at=now())
 if result:item['validation']={k:result.get(k) for k in ['overall','first_failure','checks','kernel','boot_id']}
 for x in d.get('system_packages',[]):
  if x.get('id')=='vps-runtime-package-baseline':
   known={p['name']:p for p in x.get('packages',[])}
   for e in pre['transaction']:
    p=known.get(e['name'])
    if p is None:p={'name':e['name']};x.setdefault('packages',[]).append(p)
    p.update(version=e['after'],status='installed',previous_version=e['before'])
   for name,version in [('npm','12.2.0'),('corepack',pre['corepack']),('nodejs',pre['node'])]:
    p=next((p for p in x.get('packages',[]) if p.get('name')==name),None)
    if p is None:p={'name':name};x.setdefault('packages',[]).append(p)
    p.update(version=version,status='installed')
   x['packages_count']=len(x['packages']);x['latest_maintenance']={'authority':pre['authority'],'status':status,'backup':str(b),'result':str(b/'post-boot-result.json')};x['updated_at']=now()
  if x.get('id')=='monarx-security-agent':
   for p in x.get('packages',[]):
    if p['name']=='monarx-agent':p.update(previous_version='4.3.76-master',version='4.3.78-master')
   x['updated_at']=now()
 assert path.read_bytes()==before, 'concurrent inventory change; retry from readback'
 atomic(path,d)
def collect(b,after=False):
 pre=json.loads((b/'pre-state.json').read_text());checks={};details={}
 checks['boot_changed']=not after or pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=pre['boot_id']
 kernel=run(['uname','-r']);checks['kernel_expected']=kernel==(pre['expected_kernel'] if after else pre['kernel'])
 checks['packages_exact']=all(run(['dpkg-query','-W','-f=${Version}',e['name']])==e['after'] for e in pre['transaction'])
 checks['npm_exact']=run(['npm','--version'])=='12.2.0' and json.loads(pathlib.Path('/usr/lib/node_modules/npm/package.json').read_text())['version']=='12.2.0'
 checks['node_corepack_unchanged']=run(['node','--version'])==pre['node'] and run(['corepack','--version'])==pre['corepack']
 checks['dpkg_clean']=run(['dpkg','--audit'])=='';checks['holds_zero']=run(['apt-mark','showhold'])==''
 for action in ['upgrade','dist-upgrade']:
  sim=run(['apt-get','-s',action],240);checks['apt_'+action+'_no_transaction']=not re.search(r'^(Inst|Remv) ',sim,re.M)
 details['apt_remaining']=run(['apt','list','--upgradable']);checks['apt_only_phased_sosreport']=all(line.startswith(('Listing','sosreport/')) for line in details['apt_remaining'].splitlines() if line.strip())
 checks['failed_units_zero']=run(['systemctl','--failed','--no-legend','--plain'])==''
 s=pathlib.Path('/tmp').stat();checks['tmp_safe']=s.st_uid==0 and s.st_gid==0 and (s.st_mode&0o7777)==0o1777
 checks['runtime_head_unchanged']=run(['git','-C',pre['runtime']['repo'],'rev-parse','HEAD'])==pre['runtime']['head']
 checks['launcher_unchanged']=str(pathlib.Path('/root/.local/bin/hermes').resolve())==pre['runtime']['launcher'] and pathlib.Path('/root/.local/bin/hermes').read_text().splitlines()[0]=='#!'+pre['runtime']['interpreter']
 checks['profile_config_soul_unchanged']=all(run(['sha256sum',str(pathlib.Path('/root/.hermes/profiles')/n/f)]).split()[0]==pre['profiles'][n][f] for n in pre['profiles'] for f in ['config.yaml','SOUL.md'])
 for u in pre['services']:
  props=dict(x.split('=',1) for x in run(['systemctl','show',u,'-p','ActiveState','-p','MainPID']).splitlines())
  checks['service_'+u]=props['ActiveState']=='active' and int(props['MainPID'])>0
  if u.endswith('gateway.service'):
   pid=props['MainPID'];argv=pathlib.Path('/proc/'+pid+'/cmdline').read_bytes().split(b'\0');checks['runtime_pid_'+u]=argv[0].decode()==pre['runtime']['interpreter']
 checks['rollback_hashes']=subprocess.run(['sha256sum','-c',str(b/'rollback.sha256')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
 if after:
  checks['reboot_marker_absent']=not pathlib.Path('/var/run/reboot-required').exists()
  nr=run(['needrestart','-b','-r','l']);details['needrestart']=nr
  fields=dict(re.findall(r'^(NEEDRESTART-K\w+): (.*)$',nr,re.M));checks['needrestart_kernel_current']=fields.get('NEEDRESTART-KCUR')==fields.get('NEEDRESTART-KEXP')==pre['expected_kernel'];checks['needrestart_services_zero']='NEEDRESTART-SVC:' not in nr
  errors=run(['journalctl','-b','-p','0..3','--no-pager','-o','cat']);details['boot_errors']=errors;checks['boot_priority_errors_zero']=errors.strip() in ['', '-- No entries --']
 result={'validated_at':now(),'overall':all(checks.values()),'checks':checks,'first_failure':next((k for k,v in checks.items() if not v),''),'kernel':kernel,'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'details':details}
 return result
def transport(payload,channel):
 text=run(['python3',str(BASE/'scripts/discord-bot-post.py'),'--channel-id',channel],input=json.dumps(payload,ensure_ascii=False));match=re.search(r'message_id=(\d+)',text)
 if not match:raise RuntimeError('transport lacks message id')
 return verify_message(channel,match[1],payload)
def verify_message(channel,mid,payload=None):
 spec=importlib.util.spec_from_file_location('mgs_discord_post',BASE/'scripts/discord-bot-post.py')
 assert spec is not None and spec.loader is not None
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.load_env(m.DEFAULT_ENV)
 token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN')
 assert token, 'bot credential unavailable'
 req=urllib.request.Request('https://discord.com/api/v10/channels/'+channel+'/messages/'+mid,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
 with urllib.request.urlopen(req,timeout=20) as f:d=json.load(f)
 assert d['id']==mid and d['channel_id']==channel
 if payload:assert d.get('content','')==payload.get('content','')
 if channel=='1498132022634483894':assert d.get('content','')=='' and len(d.get('embeds',[]))==1 and not d.get('mentions')
 return {'channel_id':channel,'message_id':mid,'readback':True}
def report(reason,evidence):
 t=run(['bash',str(BASE/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','vps/packages/systemd/data','--path','srv1767265; '+str(BASE/'scripts/vps-maintenance-validate-20261002.py'),'--reason',reason,'--evidence',evidence]);mid=re.search(r'message_id=(\d+)',t)
 if not mid:raise RuntimeError('REPORT lacks message id')
 return verify_message('1498132022634483894',mid[1])
def post_boot(b):
 pre=json.loads((b/'pre-state.json').read_text());ready={}
 try:
  offsets=json.loads((b/'reboot-log-offsets.json').read_text())
  for name in ['ares','atena','zeus']:
   run(['python3',str(BASE/'scripts/check-gateway-ready.py'),'--service',name+'-gateway.service','--log','/root/.hermes/profiles/'+name+'/logs/agent.log','--offset',str(offsets[name]),'--timeout','300'],340);ready[name]=True
  run(['apt-get','update','-qq'],240);result=collect(b,True);result['checks']['fresh_discord_3_profiles']=all(ready.values());result['overall']=all(result['checks'].values());result['first_failure']=next((k for k,v in result['checks'].items() if not v),'')
 except Exception as e:result={'validated_at':now(),'overall':False,'first_failure':str(e),'checks':{},'discord_ready':ready}
 atomic(b/'post-boot-result.json',result);audit('vps_post_boot_validated' if result['overall'] else 'vps_post_boot_blocked',pre,result=str(b/'post-boot-result.json'),overall=result['overall'])
 run(['systemctl','disable',UNIT])
 result['validator_disabled']=subprocess.run(['systemctl','is-enabled',UNIT],capture_output=True,text=True).stdout.strip()=='disabled'
 if not result['validator_disabled']:result['overall']=False;result['first_failure']='validator_future_execution_not_disabled'
 status='completed_validated' if result['overall'] else 'blocked_post_boot';inventory(b,pre,status,result);checkpoint('completed' if result['overall'] else 'blocked', 'Nenhum; VPS validada, Hermes inalterado' if result['overall'] else 'Investigar '+result['first_failure'],str(b/'post-boot-result.json'))
 # Canonical watcher commits the narrowly owned paths; no manual commit.
 paths=['scripts/vps-maintenance-validate-20261002.py','data/infra-inventory.json','data/agent-checkpoints.json']
 deadline=time.monotonic()+660
 while time.monotonic()<deadline:
  if not run(['git','-C',str(BASE),'status','--porcelain','--',*paths]):break
  time.sleep(5)
 else:result['overall']=False;result['first_failure']='canonical_git_paths_pending'
 try:
  # A clean index can precede the async post-commit push; wait for remote convergence.
  sync_deadline=time.monotonic()+90
  while True:
   run(['git','-C',str(BASE),'fetch','--quiet','origin','main'],120)
   if run(['git','-C',str(BASE),'rev-parse','HEAD'])==run(['git','-C',str(BASE),'rev-parse','origin/main']):
    result['git_remote_synced']=True
    break
   if time.monotonic()>=sync_deadline:raise RuntimeError('async push did not converge within 90s')
   time.sleep(3)
 except Exception as exc:
  result['overall']=False;result['first_failure']='canonical_git_sync_pending'
  result['git_sync_diagnostic']=type(exc).__name__+': '+str(exc)
 if not result['overall']:
  inventory(b,pre,'blocked_post_boot_governance',result)
  checkpoint('blocked','Investigar '+result['first_failure'],str(b/'post-boot-result.json'))
 atomic(b/'post-boot-result.json',result)
 try:
  result['report']=report('VPS atualizada e boot validado; Hermes preservado' if result['overall'] else 'Manutenção VPS bloqueada após reboot',str(b/'post-boot-result.json')+'; gate='+str(result.get('first_failure','')))
  if result['overall']:
   content='**Sim, VPS concluída.**\n\n• Kernel `6.8.0-146-generic` ativo após reboot.\n• 16 pacotes atualizados e seis componentes do kernel instalados, sem remoções.\n• npm `12.2.0`; Node e Corepack preservados.\n• Zeus, Atena e Ares ativos, com novas conexões Discord validadas.\n• Sem falhas de serviços, reinícios pendentes ou erros críticos no novo boot.\n• Hermes permaneceu no mesmo código e configuração.\n\n**Rollback:** backup validado preservado; kernel anterior mantido. Não excluí backups.\n**Residual:** sosreport segue aguardando a liberação gradual do Ubuntu. O validador fica registrado e desabilitado, sem executar novamente.\n\nDois ajustes de leitura de saída foram necessários na preparação; recuperados e validados antes do reboot. REPORT-INFRA enviado e conferido.'
  else:content='<@344196393512075265> **A manutenção ainda não está concluída.**\nGate bloqueado: `'+str(result['first_failure'])+'`.\nOs pacotes foram instalados; a validação pós-boot encontrou esse bloqueio. Evidência preservada em `'+str(b/'post-boot-result.json')+'`. Não declarei recuperação integral nem executei alterações adicionais fora do escopo.'
  result['thread']=transport({'content':content,'allowed_mentions':{'parse':[],'users':['344196393512075265'] if not result['overall'] else []}},pre['thread_id'])
 except Exception as e:result['transport_error']=str(type(e).__name__)+': '+str(e)
 atomic(b/'post-boot-result.json',result)
 return 0 if result['overall'] and result.get('thread') and result.get('report') else 1
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--backup',type=pathlib.Path,required=True);p.add_argument('--post-boot',action='store_true');p.add_argument('--register',action='store_true');a=p.parse_args()
 if a.post_boot:
  try:code=post_boot(a.backup)
  except Exception as exc:
   pre=json.loads((a.backup/'pre-state.json').read_text())
   result={'overall':False,'first_failure':type(exc).__name__+': '+str(exc),'validated_at':now()}
   atomic(a.backup/'post-boot-failure.json',result)
   audit('vps_post_boot_validator_exception',pre,failure=result['first_failure'])
   try:checkpoint('blocked','Investigar '+result['first_failure'],str(a.backup/'post-boot-failure.json'))
   except Exception as checkpoint_error:result['checkpoint_error']=type(checkpoint_error).__name__+': '+str(checkpoint_error)
   result['thread']=transport({'content':'<@344196393512075265> **VPS ainda não concluída.** O validador pós-boot parou em `'+result['first_failure']+'`. Pacotes instalados; recuperação integral não declarada. Evidência: `'+str(a.backup/'post-boot-failure.json')+'`.','allowed_mentions':{'parse':[],'users':['344196393512075265']}},pre['thread_id'])
   atomic(a.backup/'post-boot-failure.json',result);code=1
  raise SystemExit(code)
 pre=json.loads((a.backup/'pre-state.json').read_text())
 if a.register:inventory(a.backup,pre,'packages_validated_reboot_pending')
 else:
  result=collect(a.backup);atomic(a.backup/'reboot-preflight.json',result);print(json.dumps({'overall':result['overall'],'first_failure':result['first_failure'],'checks':len(result['checks'])}));raise SystemExit(0 if result['overall'] else 1)
