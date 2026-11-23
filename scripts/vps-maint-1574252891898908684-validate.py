#!/usr/bin/env python3
"""One-shot, new-boot-only runtime validation. Never executes a reboot."""
import importlib.util,pathlib,os,json,re,time,datetime,stat,socket,sys
s=importlib.util.spec_from_file_location('mgs_reboot_common',pathlib.Path(__file__).with_name('vps-maint-1574252891898908684-common.py'));assert s and s.loader;c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
def marker_fresh(text,boot_epoch):
 for line in text.splitlines():
  if '[Discord] Connected as ' not in line:continue
  try:stamp=datetime.datetime.strptime(line[:23],'%Y-%m-%d %H:%M:%S,%f').timestamp()
  except ValueError:continue
  if stamp>=boot_epoch-2:return True
 return False

def readiness(pre):
 boot_epoch=time.time()-float(pathlib.Path('/proc/uptime').read_text().split()[0]);deadline=time.monotonic()+600;states={}
 while True:
  good=True;states={}
  for agent in ['zeus','atena','ares']:
   u=agent+'-gateway';d=c.unit(u);d['discord_marker']=False;d['argv_matches']=False
   if d['ActiveState']=='active' and int(d['MainPID'])>0:
    proc=pathlib.Path('/proc')/d['MainPID'];argv=(proc/'cmdline').read_bytes().split(b'\0');argv=[x.decode() for x in argv if x];d['argv_matches']=argv==pre['gateway_argv'][agent]
    log=pathlib.Path('/root/.hermes/profiles')/agent/'logs/gateway.log';old=pre['gateway_logs'][agent];st=log.stat();offset=old['size'] if st.st_ino==old['inode'] and st.st_size>=old['size'] else 0
    with log.open('rb') as f:f.seek(offset);text=f.read().decode(errors='replace')
    d['discord_marker']=marker_fresh(text,boot_epoch)
   if not (d['ActiveState']=='active' and int(d['MainPID'])>0 and d['discord_marker'] and d['argv_matches']):good=False
   states[agent]=d
  c.atomic(c.B/'gateway-readiness-progress.json',{'at':c.now(),'states':states})
  if good:return states
  if time.monotonic()>=deadline:raise RuntimeError('new-boot gateway/Discord readiness deadline; see per-agent progress')
  time.sleep(5)

def main():
 pre=c.load(c.B/'prestate.json');result={'at':c.now(),'authorization_message_id':c.AUTH,'overall':False,'checks':{},'status':'running'};checks=result['checks'];c.atomic(c.B/'postboot-result.json',result)
 try:
  new=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip();checks['new_boot']=new!=pre['boot_id'];assert checks['new_boot'],'validator must not run in original boot'
  checks['expected_kernel']=os.uname().release==pre['expected_kernel'];checks['reboot_marker_absent']=not pathlib.Path('/var/run/reboot-required').exists();result['boot_id']=new;result['kernel']=os.uname().release
  result['gateways']=readiness(pre);checks['all_gateway_runtime_and_fresh_discord']=True
  checks['launcher_unchanged']=str(pathlib.Path('/root/.local/bin/hermes').resolve())==pre['hermes_launcher'];checks['runtime_head_unchanged']=c.run(['git','-C',pre['hermes_runtime'],'rev-parse','HEAD']).stdout.strip()==pre['hermes_local_head']
  checks['profile_and_unit_configuration_preserved']=all(c.sha(path)==h for path,h in pre['configuration_hashes'].items())
  versions={k:c.run(['dpkg-query','-W','-f=${Version}',k]).stdout.strip() for k in pre['expected_packages']};checks['all_expected_package_versions']=versions==pre['expected_packages'];result['versions']=versions
  checks['dpkg_clean']=not c.run(['dpkg','--audit']).stdout.strip();checks['holds_zero']=not c.run(['apt-mark','showhold']).stdout.strip()
  for attempt in range(3):
   refresh=c.run(['apt-get','update','-qq'],timeout=180,check=False)
   if refresh.returncode==0:break
   time.sleep(5*(attempt+1))
  checks['apt_refresh_success']=refresh.returncode==0;result['apt_graph']={}
  for n,args in [('upgrade',['apt-get','-s','upgrade']),('full_upgrade',['apt-get','-s','dist-upgrade'])]:
   r=c.run(args);rows=[l for l in r.stdout.splitlines() if l.startswith(('Inst ','Remv ')) or 'upgraded,' in l];result['apt_graph'][n]=rows;checks[n+'_zero_candidates']=not any(l.startswith(('Inst ','Remv ')) for l in rows)
  snap=c.run(['snap','refresh','--list'],check=False);checks['snap_zero_candidates']=snap.returncode==0 and not snap.stdout.strip()
  need=c.run(['needrestart','-b','-r','l']);result['needrestart']=need.stdout;fields={k:v.strip() for k,v in (l.split(':',1) for l in need.stdout.splitlines() if ':' in l)};checks['needrestart_kernel_agreement']=fields.get('NEEDRESTART-KCUR')==fields.get('NEEDRESTART-KEXP')==pre['expected_kernel'] and fields.get('NEEDRESTART-KSTA')=='1'
  states={u:c.unit(u) for u in pre['units']};result['services']=states;checks['all_expected_services_active']=all(d['ActiveState']=='active' and int(d['MainPID'])>0 for d in states.values())
  tmp=pathlib.Path('/tmp').stat();checks['tmp_root1777']=tmp.st_uid==tmp.st_gid==0 and stat.S_IMODE(tmp.st_mode)==0o1777
  # Socket-activated SSH can be healthy without an initial ssh.service process.
  listen=c.run(['ss','-H','-ltn']).stdout;checks['ssh22_listener']=any(re.search(r':22\s',line) for line in listen.splitlines());conf=c.run(['/usr/sbin/sshd','-t'],check=False)
  if conf.returncode and '/run/sshd' in conf.stderr and c.unit('ssh.socket')['ActiveState']=='active':
   with socket.create_connection(('127.0.0.1',22),timeout=10) as sock:
    sock.sendall(b'SSH-2.0-MGS_ReadOnly_Validation\r\n');banner=sock.recv(256);assert banner.startswith(b'SSH-2.0-')
   conf=c.run(['/usr/sbin/sshd','-t'],check=False)
  checks['sshd_config_valid']=conf.returncode==0
  failed=c.run(['systemctl','--failed','--no-legend','--no-pager']).stdout.strip();checks['failed_units_zero']=not failed;result['failed_units']=failed
  logs=c.run(['journalctl','-b','0','-p','0..3','--no-pager','-o','json']);errors=[json.loads(l) for l in logs.stdout.splitlines() if l];c.atomic(c.B/'postboot-journal-errors.json',errors);checks['boot_priority0_3_errors_zero']=not errors
  checks['rollback_hashes']=all(c.run(['sha256sum','-c',p]).returncode==0 for p in pre['rollback_manifests'])
  result['overall']=all(checks.values());result['status']='runtime_validated_pending_closure' if result['overall'] else 'runtime_gate_failed'
 except BaseException as error:
  result.update({'overall':False,'status':'validator_exception','exception_type':type(error).__name__,'diagnosis':str(error)[:600]})
 finally:
  result['finished_at']=c.now();c.atomic(c.B/'postboot-result.json',result)
  c.audit('hostinger_postboot_runtime_validation',overall=result['overall'],status=result['status'],checks_passed=sum(checks.values()),checks_total=len(checks),receipt=str(c.B/'postboot-result.json'))
  c.inventory_phase('hostinger_runtime_validated_governance_pending' if result['overall'] else 'hostinger_reboot_validation_blocked',c.B/'postboot-result.json')
  c.checkpoint('hostinger_runtime_validated_governance_pending' if result['overall'] else 'hostinger_reboot_validation_blocked','External closure '+c.CLOSURE+' owns verification/reporting. Do not duplicate closure or repeat reboot. Read '+str(c.B/'postboot-result.json')+' after validator exits; other four hosts/dashboard remain open.')
  c.run(['systemctl','disable',c.VALIDATOR]);c.atomic(c.B/'validator-exit-receipt.json',{'at':c.now(),'runtime_overall':result['overall'],'future_execution':'disabled','unit_definition':'retained','closure_consumer':c.CLOSURE})
 return 0
if __name__=='__main__':sys.exit(main())
