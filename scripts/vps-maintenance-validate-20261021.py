#!/usr/bin/env python3
"""Pure VPS verifier and post-boot receipt; never reboots or restarts gateways."""
import argparse,datetime,importlib.util,json,os,pathlib,re,stat,subprocess,tempfile,time,urllib.request
BASE=pathlib.Path('/root/mgs-agent')
ROOT=pathlib.Path('/root/.hermes/secure-backups/vps-maintenance/20261021-1562331354568589393')
IDENT='zeus-vps-hermes-1562331354568589393'
THREAD='1562331354568589393'
AUTH='1562451046654283847'
UNIT='mgs-vps-maintenance-1562331354568589393.service'
SCRIPT=BASE/'scripts/vps-maintenance-validate-20261021.py'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(args,timeout=120,check=True,input=None):
 p=subprocess.run(args,text=True,capture_output=True,timeout=timeout,input=input)
 if check and p.returncode:raise RuntimeError(str(args[:2])+' rc='+str(p.returncode)+': '+p.stderr[-300:])
 return p
def atomic(path,obj):
 path=pathlib.Path(path);fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
 with os.fdopen(fd,'w') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(name,0o600);os.replace(name,path)
 assert json.loads(path.read_text())==obj
def audit(event,**data):
 row={'ts':now(),'event':event,'agent':'zeus','authority':AUTH,'thread_id':THREAD,'id':IDENT,**data}
 with (BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
def service(unit):
 return dict(l.split('=',1) for l in run(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','UnitFileState']).stdout.splitlines() if '=' in l)
def checkpoint(state,next_step):
 run(['python3',str(BASE/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id',IDENT,'--agent','zeus','--thread-id',THREAD,'--objective','VPS primeiro, Hermes main depois; rollback e validacao integral','--state',state,'--next-step',next_step,'--source',str(ROOT/'post-boot-result.json')])
def inventory_update(path,status,result):
 for _ in range(5):
  path=pathlib.Path(path);before=path.read_bytes();data=json.loads(before)
  rows=[x for x in data['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==IDENT];assert len(rows)==1
  rows[0].update(status=status,vps_phase=status,critical_authorization=AUTH,validator=str(SCRIPT),validator_unit=UNIT,validator_unit_retention='disabled_retained_no_deletion_authorized',post_boot_result=str(ROOT/'post-boot-result.json'),checks=result.get('checks',{}),updated_at=now(),hermes_phase='pending_after_vps' if result.get('overall') else 'blocked_until_vps_recovery',next_gate='Hermes full-surface port and validation' if result.get('overall') else result.get('first_failure','unknown'))
  for item in data.get('system_packages',[]):
   if isinstance(item,dict) and item.get('id')=='vps-runtime-package-baseline':item['maintenance_20261021']={'authority':AUTH,'kernel':result.get('kernel'),'status':status,'result':str(ROOT/'post-boot-result.json')}
  if path.read_bytes()!=before:continue
  atomic(path,data);return
 raise RuntimeError('Concurrent inventory changes did not converge; no overwrite')
def collect(after=False):
 pre=json.loads((ROOT/'reboot-prestate.json').read_text());checks={};details={}
 boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip();kernel=run(['uname','-r']).stdout.strip()
 checks['boot_changed' if after else 'boot_unchanged']=(boot!=pre['boot_id']) if after else boot==pre['boot_id']
 checks['kernel_expected']=kernel==pre['kernel_expected'];checks['reboot_marker_absent']=not pathlib.Path('/var/run/reboot-required').exists()
 for name,version in pre['package_versions'].items():checks['package_'+name]=run(['dpkg-query','-W','-f=${Version}',name]).stdout==version
 checks['dpkg_clean']=not run(['dpkg','--audit']).stdout.strip();checks['holds_zero']=not run(['apt-mark','showhold']).stdout.strip()
 for action in ['upgrade','full-upgrade']:
  text=run(['apt-get','-s',action]).stdout
  rows=[l for l in text.splitlines() if re.match(r'^(Inst |Remv |Conf |\d+ upgraded)',l)]
  checks['apt_'+action+'_zero']=not any(l.startswith(('Inst ','Remv ')) for l in rows);details['apt_'+action]=rows
 checks['launcher_unchanged']=str(pathlib.Path('/root/.local/bin/hermes').resolve())==pre['launcher']
 checks['runtime_head_unchanged']=run(['git','-C',pre['runtime_repo'],'rev-parse','HEAD']).stdout.strip()==pre['runtime_head']
 for profile,items in pre['profile_hashes'].items():
  for name,h in items.items():checks['profile_'+profile+'_'+name]=run(['sha256sum',str(pathlib.Path('/root/.hermes/profiles')/profile/name)]).stdout.split()[0]==h
 for unit,old in pre['services'].items():
  state=service(unit);checks['service_'+unit]=state['ActiveState']=='active' and int(state['MainPID'])>0
  if unit=='ssh.service' and not checks['service_'+unit]:
   sock=dict(l.split('=',1) for l in run(['systemctl','show','ssh.socket','-p','ActiveState','-p','SubState','-p','Listen']).stdout.splitlines() if '=' in l)
   listener=run(['ss','-ltnp','sport = :22']).stdout
   config=run(['/usr/sbin/sshd','-t'],check=False)
   checks['service_'+unit]=sock.get('ActiveState')=='active' and sock.get('SubState')=='listening' and ':22' in sock.get('Listen','') and 'LISTEN' in listener and config.returncode==0
   details['ssh_socket_activation']={'socket':sock,'port22_listening':'LISTEN' in listener,'config_valid':config.returncode==0,'service_pid_zero_expected_until_connection':True}
  if unit.endswith('-gateway.service'):
   agent=unit.removesuffix('-gateway.service');args=(pathlib.Path('/proc')/state['MainPID']/'cmdline').read_bytes().split(b'\0')
   checks['runtime_argv_'+agent]=[s.decode() for s in args[:6]]==[pre['interpreter'],'/root/.local/bin/hermes','-p',agent,'gateway','run']
   checks['gateway_pid_'+agent]=(state['MainPID']!=old['MainPID']) if after else state['MainPID']==old['MainPID']
 for name,version in pre['tools'].items():checks['tool_'+name]=run([name,'--version']).stdout.strip()==version
 nr=run(['needrestart','-b','-r','l']).stdout;fields={}
 for line in nr.splitlines():
  if ': ' in line:
   k,v=line.split(': ',1);fields.setdefault(k,[]).append(v)
 checks['needrestart_kernel_current']=fields.get('NEEDRESTART-KCUR')==fields.get('NEEDRESTART-KEXP')==[pre['kernel_expected']]
 details['needrestart']=fields
 failed=run(['systemctl','--failed','--no-legend','--plain','--no-pager']).stdout.strip().splitlines();details['failed_units']=failed
 if after:
  checks['needrestart_services_zero']=not fields.get('NEEDRESTART-SVC');checks['failed_units_zero']=not failed
 else:
  # The approved reboot renews stale services. The already-disclosed external
  # LVFS outage is not reclassified as healthy; post-boot acceptance stays strict.
  checks['failed_units_no_new_scope']=all(l.startswith('fwupd-refresh.service ') for l in failed)
 temp=pathlib.Path('/tmp').stat();checks['tmp_safe']=temp.st_uid==temp.st_gid==0 and temp.st_mode&0o7777==0o1777
 checks['rollback_hashes']=run(['sha256sum','-c',str(ROOT/'SHA256SUMS')],timeout=300,check=False).returncode==0
 if after:
  parsed=[]
  for line in run(['journalctl','-b','-p','0..3','--no-pager','-o','json']).stdout.splitlines():
   try:d=json.loads(line);parsed.append({'unit':d.get('_SYSTEMD_UNIT'),'message':d.get('MESSAGE','')[:400]})
   except json.JSONDecodeError:pass
  checks['boot_priority_errors_zero']=not parsed;details['boot_priority_errors']=parsed
 return {'at':now(),'overall':all(checks.values()),'checks':checks,'first_failure':next((k for k,v in checks.items() if not v),''),'kernel':kernel,'boot_id':boot,'details':details,'authority':AUTH,'hermes_unchanged':checks['launcher_unchanged'] and checks['runtime_head_unchanged']}
def token():
 s=importlib.util.spec_from_file_location('mgs_discord_post',BASE/'scripts/discord-bot-post.py');assert s is not None and s.loader is not None
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.load_env(m.DEFAULT_ENV)
 return os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']
def verify_message(channel,mid,expected=None):
 q=urllib.request.Request('https://discord.com/api/v10/channels/'+channel+'/messages/'+mid,headers={'Authorization':'Bot '+token(),'User-Agent':'MGS-Zeus/1.0'})
 with urllib.request.urlopen(q,timeout=25) as f:d=json.load(f)
 assert d['id']==mid and d['channel_id']==channel and d['author']['id']=='1496296175014252634'
 if expected is not None:assert d.get('content','')==expected
 if channel=='1498132022634483894':assert not d.get('content') and len(d.get('embeds',[]))==1 and not d.get('mentions')
 return {'channel_id':channel,'message_id':mid,'readback':True}
def sync_git():
 paths=['scripts/vps-maintenance-validate-20261021.py','data/infra-inventory.json','data/agent-checkpoints.json']
 end=time.monotonic()+720
 while time.monotonic()<end:
  if not run(['git','-C',str(BASE),'status','--porcelain','--',*paths]).stdout.strip():break
  time.sleep(5)
 else:raise RuntimeError('Canonical auto-versioning owned paths still pending')
 end=time.monotonic()+90
 while time.monotonic()<end:
  run(['git','-C',str(BASE),'fetch','--quiet','origin','main'])
  h=run(['git','-C',str(BASE),'rev-parse','HEAD']).stdout.strip();u=run(['git','-C',str(BASE),'rev-parse','origin/main']).stdout.strip()
  if h==u:
   remote=json.loads(run(['git','-C',str(BASE),'show','origin/main:data/infra-inventory.json']).stdout)
   row=next(x for x in remote['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==IDENT)
   assert row.get('post_boot_result')==str(ROOT/'post-boot-result.json')
   return {'head':h,'origin_main':u,'remote_receipt':True}
  time.sleep(3)
 raise RuntimeError('Remote Git convergence pending')
def report(result):
 text=run(['bash',str(BASE/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','vps/systemd/data','--path',str(SCRIPT)+'; /etc/systemd/system/'+UNIT+'; data/infra-inventory.json; data/agent-checkpoints.json','--reason','Lote exato de nove pacotes e reboot autorizados; Hermes preservado. Unit retida desabilitada, sem exclusao.','--evidence',str(ROOT/'post-boot-result.json')+'; overall='+str(result['overall'])+'; gate='+result['first_failure']+'; phased preservados; validacao completa no recibo.']).stdout
 m=re.search(r'message_id=(\d+)',text);assert m
 return verify_message('1498132022634483894',m.group(1))
def post_boot():
 result=None
 try:
  pre=json.loads((ROOT/'reboot-prestate.json').read_text());ready={}
  for agent in ['ares','atena','zeus']:
   text=run(['python3',str(BASE/'scripts/check-gateway-ready.py'),'--service',agent+'-gateway.service','--log',str(pathlib.Path('/root/.hermes/profiles')/agent/'logs/agent.log'),'--offset',str(pre['log_offsets'][agent]),'--timeout','300'],timeout=340).stdout;ready[agent]=json.loads(text)
  run(['apt-get','update','-qq'],timeout=180)
  result=collect(True);result['details']['gateway_readiness']=ready
  # One bounded recovery probe after the new boot; never firmware installation.
  fw=run(['fwupdmgr','refresh'],timeout=180,check=False)
  atomic(ROOT/'fwupd-post-boot.json',{'at':now(),'returncode':fw.returncode,'stdout':fw.stdout[-1800:],'stderr':fw.stderr[-1800:]})
  result=collect(True);result['checks']['fresh_discord_3_profiles']=all(v.get('ready') for v in ready.values());result['details']['gateway_readiness']=ready
  result['checks']['firmware_metadata_refreshed']=fw.returncode in (0,2,101)
  result['overall']=all(result['checks'].values());result['first_failure']=next((k for k,v in result['checks'].items() if not v),'')
 except Exception as exc:result={'at':now(),'overall':False,'checks':{},'first_failure':type(exc).__name__+': '+str(exc)[:400],'authority':AUTH}
 atomic(ROOT/'post-boot-result.json',result);audit('vps_post_boot_runtime_readback',overall=result['overall'],result=str(ROOT/'post-boot-result.json'))
 # Never unlink or daemon-reload an activating validator. Leave it disabled.
 run(['systemctl','disable',UNIT]);result['validator_disabled']=run(['systemctl','is-enabled',UNIT],check=False).stdout.strip()=='disabled'
 if not result['validator_disabled']:result['overall']=False;result['first_failure']='Validator could execute again'
 status='vps_completed_validated_ready_hermes' if result['overall'] else 'blocked_post_boot'
 inventory_update(BASE/'data/infra-inventory.json',status,result)
 checkpoint(status,'VPS validada; entregar aviso solicitado e continuar Hermes main autorizado, com port e gates proprios.' if result['overall'] else 'Investigar e recuperar sem repetir instalacao: '+result['first_failure'])
 try:result['git']=sync_git();result['governance_complete']=True
 except Exception as exc:result['overall']=False;result['first_failure']='governance_git: '+str(exc);result['governance_complete']=False
 atomic(ROOT/'post-boot-result.json',result)
 try:result['report_infra']=report(result)
 except Exception as exc:result['overall']=False;result['transport_error']=str(exc)
 atomic(ROOT/'post-boot-result.json',result);audit('vps_post_boot_external_validation_finished',overall=result['overall'],first_failure=result['first_failure'])
 # Same-session native continuation consumes this receipt and owns the final
 # operational answer, recovery and Hermes phase: no duplicate thread post.
 return 0
def self_test():
 root=pathlib.Path(tempfile.mkdtemp(prefix='vps-20261021-verifier-',dir=os.environ['TMPDIR']));p=root/'inventory.json'
 seed={'runtime_artifacts':[{'id':IDENT,'keep':'unchanged'},{'protected':True}],'system_packages':[]};atomic(p,seed)
 inventory_update(p,'fixture_pass',{'overall':True,'checks':{'fixture':True},'kernel':'test'})
 d=json.loads(p.read_text());assert d['runtime_artifacts'][1]==seed['runtime_artifacts'][1] and d['runtime_artifacts'][0]['keep']=='unchanged';assert d['runtime_artifacts'][0]['status']=='fixture_pass'
 print('SELF_TEST_PASS atomic JSON, exact record update, unrelated record preservation; '+str(root));return 0
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--post-boot',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
 if a.self_test:raise SystemExit(self_test())
 if a.post_boot:raise SystemExit(post_boot())
 r=collect(False);atomic(ROOT/'reboot-preflight.json',r);print(json.dumps({'overall':r['overall'],'checks':len(r['checks']),'first_failure':r['first_failure']}));raise SystemExit(0 if r['overall'] else 1)
