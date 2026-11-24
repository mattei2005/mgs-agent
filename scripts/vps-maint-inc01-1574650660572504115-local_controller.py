"""External Inc01 reboot consumer, exclusive native admission, no Discord output."""
import contextlib,datetime,fcntl,importlib.util,json,os,pathlib,re,subprocess,time
P=pathlib.Path;R=P('/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc01/reboot-1574650660572504115');APP=P('/root/mgs-agent/apps/finance-system');REMOTE='/root/mgs-maintenance/1574252891898908684-inc01/reboot-1574650660572504115';AUTH='1574650660572504115';UID='mgs-inc01-reboot-1574650660572504115-dispatch'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(name,d):
 p=R/name;t=p.with_name(p.name+'.new-'+str(os.getpid()))
 with t.open('x') as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(t,0o600);os.replace(t,p)
def sh(args,timeout=120):return subprocess.run(args,capture_output=True,text=True,timeout=timeout)
def gatepids():
 r=sh(['systemctl','show','zeus-gateway','atena-gateway','ares-gateway','-p','Id','-p','MainPID','-p','ActiveState']);assert r.returncode==0
 rows=[dict(x.split('=',1) for x in block.splitlines() if '=' in x) for block in r.stdout.strip().split('\n\n')];assert len(rows)==3 and all(x['ActiveState']=='active' and int(x['MainPID'])>0 for x in rows)
 return {x['Id']:x['MainPID'] for x in rows}
@contextlib.contextmanager
def admission():
 handles=[];deadline=time.monotonic()+180
 try:
  for name in ['release-admission.lock','gam-revenue-sync.lock','media-spend-sync.lock','quote-sync.lock','history-refresh.lock']:
   p=APP/'private'/name;assert p.is_file();f=p.open('r+');handles.append(f)
   while True:
    try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);break
    except BlockingIOError:
     atomic('controller-progress.json',{'at':now(),'status':'waiting_native_finance_admission','lock':name,'pid':os.getpid()})
     if time.monotonic()>deadline:raise RuntimeError('native financial job still busy; no reboot dispatched')
     time.sleep(.2)
  state=json.loads((APP/'private/release-current.json').read_text());assert state['state']=='committed','noncommitted release; never recover/write finance as part of reboot'
  yield state['release_id']
 finally:
  for f in reversed(handles):f.close()

def main():
 guard=(R/'controller.lock').open('a');fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if (R/'controller-final.json').exists():
  old=json.loads((R/'controller-final.json').read_text())
  if old.get('overall'):return 0
 if (R/'controller-start.json').exists():raise RuntimeError('existing controller receipt: reconcile process and remote attempt, never duplicate')
 source_boot=P('/proc/sys/kernel/random/boot_id').read_text().strip();gateways=gatepids();atomic('controller-start.json',{'at':now(),'pid':os.getpid(),'authorization_message_id':AUTH,'source_boot_id':source_boot})
 spec=importlib.util.spec_from_file_location('inc01_secret_reader','/root/.hermes/profiles/zeus/reports/vps-audit-1574249078584377544/run.py');cred=importlib.util.module_from_spec(spec);spec.loader.exec_module(cred);f=cred.item('vgor2cjdz5lvrkfulf26qmkoya');user=f.get('username','zeus');password=f['password'];port=str(f.get('port','22') or '22')
 def remote(code,timeout=120):
  rfd,wfd=os.pipe();os.write(wfd,(password+'\n').encode());os.close(wfd)
  try:return subprocess.run(['sshpass','-d',str(rfd),'ssh','-p',port,'-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','ConnectTimeout=12',user+'@162.55.28.178',('' if user=='root' else 'sudo -n ')+'python3 -I -'],pass_fds=(rfd,),input=code,capture_output=True,text=True,timeout=timeout)
  finally:os.close(rfd)
 result={'at':now(),'overall':False,'status':'controller_starting','authorization_message_id':AUTH}
 try:
  with admission() as release_id:
   receipt={'at':now(),'authorization_message_id':AUTH,'local_exclusive_admission_verified':True,'local_legacy_locks_verified':True,'finance_release_id':release_id,'controller_pid':os.getpid(),'source_boot_id':source_boot}
   atomic('local-admission-receipt.json',receipt)
   code="""import pathlib,json,subprocess,time,os
R=pathlib.Path(@@REMOTE@@);assert os.uname().nodename=='MatteiInc01'
assert not (R/'reboot-attempt.json').exists() and not (R/'dispatch-readback.json').exists(),'existing reboot dispatch; reconcile'
(R/'admission-receipt.json').write_text(json.dumps(@@RECEIPT@@,indent=2)+'\\n')
r=subprocess.run(['systemd-run','--unit',@@UID@@,'--on-active=10s','--timer-property=AccuracySec=1s','--property=Type=simple','--property=RuntimeMaxSec=300','--property=StandardOutput=append:'+str(R/'dispatch.log'),'--property=StandardError=append:'+str(R/'dispatch.log'),'/usr/bin/python3','-I',str(R/'reboot_dispatcher.py')],capture_output=True,text=True,timeout=30);assert r.returncode==0
for i in range(10):
 r=subprocess.run(['systemctl','show',@@UID@@+'.timer','-p','ActiveState','-p','SubState','-p','Triggers'],capture_output=True,text=True,check=True);timer=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
 r=subprocess.run(['systemctl','show',@@UID@@+'.service','-p','Type','-p','ActiveState','-p','MainPID','-p','ExecStart'],capture_output=True,text=True,check=True);service=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
 if timer['ActiveState']=='active' and timer['SubState']=='waiting' and timer['Triggers']==@@UID@@+'.service' and str(R/'reboot_dispatcher.py') in service['ExecStart']:break
 time.sleep(.2)
else:raise RuntimeError('timer readback not confirmed; inspect exact existing unit')
d={'timer':timer,'service':service,'authorization_message_id':@@AUTH@@};(R/'dispatch-readback.json').write_text(json.dumps(d,indent=2)+'\\n');print(json.dumps(d))
""".replace('@@REMOTE@@',repr(REMOTE)).replace('@@RECEIPT@@',repr(receipt)).replace('@@UID@@',repr(UID)).replace('@@AUTH@@',repr(AUTH))
   r=remote(code,100);atomic('timer-dispatch-transport.json',{'at':now(),'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr[-2000:]});assert r.returncode==0,'dispatch transport failed; reconcile before another action'
   atomic('controller-progress.json',{'at':now(),'status':'single_remote_reboot_queued_waiting_new_boot','local_admission_held':True,'timer_readback':json.loads(r.stdout)})
   time.sleep(35);deadline=time.monotonic()+1200;transport_failures=0
   while True:
    code="""import pathlib,json,subprocess,os
R=pathlib.Path(@@REMOTE@@);d={'at':@@NOW@@,'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'kernel':os.uname().release}
for name in ['dispatch-blocked.json','reboot-attempt.json','postboot-result.json','validator-exit.json','readiness-progress.json']:
 p=R/name
 if p.exists():d[name]=json.loads(p.read_text())
r=subprocess.run(['systemctl','show','mgs-inc01-reboot-1574650660572504115-validate.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','UnitFileState'],capture_output=True,text=True);d['validator_unit']=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
print(json.dumps(d))
""".replace('@@REMOTE@@',repr(REMOTE)).replace('@@NOW@@',repr(now()))
    try:r=remote(code,50)
    except subprocess.TimeoutExpired:r=None
    if r is None or r.returncode:
     transport_failures+=1;atomic('controller-progress.json',{'at':now(),'status':'expected_boot_transport_wait','consecutive_transport_failures':transport_failures,'local_admission_held':True})
     if transport_failures>=5:raise RuntimeError('five SSH readiness failures after single dispatch; reconcile provider/host, never issue another reboot')
    else:
     transport_failures=0;d=json.loads(r.stdout);atomic('remote-last-observation.json',d)
     if 'dispatch-blocked.json' in d:raise RuntimeError('remote dispatcher withheld reboot: '+d['dispatch-blocked.json']['diagnosis'])
     if 'postboot-result.json' in d and d['validator_unit'].get('MainPID')=='0':
      post=d['postboot-result.json'];assert d['boot_id']!=json.loads((R/'remote-prestate.json').read_text())['boot_id'],'boot did not change'
      if not post['overall']:raise RuntimeError('postboot validation blocked: '+','.join(k for k,v in post.get('checks',{}).items() if not v)+' '+post.get('diagnosis',''))
      assert d['kernel']=='5.15.0-204-generic' and d['validator_unit']['ActiveState']=='inactive' and d['validator_unit']['UnitFileState']=='disabled' and d['validator-exit.json']['disable_rc']==0
      result.update({'overall':True,'status':'runtime_validated_foreground_governance_pending','remote':d,'runtime_checks_passed':post['checks_passed'],'runtime_checks_total':post['checks_total']});break
    if time.monotonic()>deadline:raise RuntimeError('new-boot validation deadline; inspect exact validator/host without repeating reboot')
    time.sleep(15)
   external={}
   for label,url,expected in [('eggbev','https://eggbev.com/','200'),('finance_login','https://dash.mgsdigitalcorp.com/login','200'),('finance_unauth_api','https://dash.mgsdigitalcorp.com/api/scenarios','401')]:
    p=sh(['curl','-sS','-L','--max-time','30','-o','/dev/null','-w','%{http_code}',url],40);external[label]={'rc':p.returncode,'status':p.stdout.strip()};assert p.returncode==0 and p.stdout.strip()==expected
   result['external_canaries']=external
  result['native_admission_released']=True;result['source_host_boot_unchanged']=P('/proc/sys/kernel/random/boot_id').read_text().strip()==source_boot;result['source_gateway_pids_unchanged']=gatepids()==gateways;assert result['source_host_boot_unchanged'] and result['source_gateway_pids_unchanged']
 except BaseException as e:result.update({'overall':False,'status':'controller_blocked_reconcile_without_reboot_replay','diagnosis':type(e).__name__+': '+str(e)[:900]})
 finally:
  result['finished_at']=now();atomic('controller-final.json',result)
 print(json.dumps({'overall':result['overall'],'status':result['status'],'diagnosis':result.get('diagnosis'),'checks':result.get('runtime_checks_passed'),'receipt':str(R/'controller-final.json')}),flush=True)
 return 0 if result['overall'] else 1
if __name__=='__main__':raise SystemExit(main())
