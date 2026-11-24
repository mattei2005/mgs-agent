"""Inc01-only reboot primitive, confined to a detached remote systemd timer."""
import fcntl,importlib.util,json,os,pathlib,re,time
P=pathlib.Path;R=P('/root/mgs-maintenance/1574252891898908684-inc01/reboot-1574650660572504115');UNIT='mgs-inc01-reboot-1574650660572504115-validate.service'
s=importlib.util.spec_from_file_location('inc01_dispatch_probe',R/'boot_probe.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
def atomic(name,d):
 p=R/name;t=p.with_name(p.name+'.new-'+str(os.getpid()))
 with t.open('x') as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(t,0o600);os.replace(t,p)
def main():
 assert os.uname().nodename=='MatteiInc01'
 lock=(R/'dispatch.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not (R/'reboot-attempt.json').exists(),'existing attempt; never replay'
 try:
  pre=json.loads((R/'prestate.json').read_text());assert pre['authorization_message_id']=='1574650660572504115'
  receipt=json.loads((R/'admission-receipt.json').read_text());assert receipt['authorization_message_id']=='1574650660572504115' and receipt['local_exclusive_admission_verified'] and receipt['local_legacy_locks_verified']
  rid=receipt['finance_release_id'];assert re.fullmatch(r'[A-Za-z0-9_-]+',rid)
  ctl=P('/home/mgsfinance/releases/pg-auth-1545934831664242748/private/release-control');remote_lock=(ctl/'files.lock').open('a');fcntl.flock(remote_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  fence=json.loads((ctl/(rid+'.json')).read_text());assert fence['phase']=='committed','finance release not safely committed'
  c.run(['sha256sum','-c',str(R/'dispatch.sha256')]);c.run(['sha256sum','-c',str(R/'postgresql-before-reboot.sha256')])
  assert P('/proc/sys/kernel/random/boot_id').read_text().strip()==pre['boot_id']
  current=c.observe(None,refresh=True);assert current['assessment']['overall'],'pure pre-dispatch checks failed'
  for key in ['executables','configuration_hashes','mariadb_catalog','postgresql_version','finance_socket','optional_state']:assert current[key]==pre[key],'protected baseline drift: '+key
  u=c.unit(UNIT);assert u['ActiveState']=='inactive' and u['MainPID']=='0' and u['UnitFileState']=='enabled'
  # Do not interrupt an already active PostgreSQL application transaction.
  until=time.monotonic()+120
  while True:
   value=c.pg("BEGIN READ ONLY; SELECT count(*) FROM pg_stat_activity WHERE pid<>pg_backend_pid() AND backend_type='client backend' AND state='active' AND xact_start IS NOT NULL; ROLLBACK;")
   if value.splitlines()==['BEGIN','0','ROLLBACK']:break
   if time.monotonic()>until:raise RuntimeError('active application transaction did not drain; reboot withheld')
   time.sleep(2)
  attempt={'at':c.now(),'status':'issuing_one_approved_reboot','authorization_message_id':'1574650660572504115','disclosed_gate_message_id':'1574649750643281962','boot_id_before':pre['boot_id'],'expected_kernel':pre['expected_kernel'],'finance_release_id':rid,'local_admission_and_remote_fence_verified':True};atomic('reboot-attempt.json',attempt)
  p=c.run(['systemctl','reboot'],60,False);attempt.update({'command_rc':p.returncode,'returned_at':c.now()});atomic('reboot-attempt.json',attempt)
  assert p.returncode==0,'systemd refused reboot; do not force or replay'
 except BaseException as error:
  atomic('dispatch-blocked.json',{'at':c.now(),'diagnosis':type(error).__name__+': '+str(error)[:700],'attempt_exists':(R/'reboot-attempt.json').exists()})
  c.run(['systemctl','disable',UNIT],30,False)
  return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
