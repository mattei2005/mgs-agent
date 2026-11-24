"""One new-boot-only validator; no reboot, database write or Discord send."""
import datetime,importlib.util,json,os,pathlib,time
P=pathlib.Path;R=P('/root/mgs-maintenance/1574252891898908684-inc01/reboot-1574650660572504115');UNIT='mgs-inc01-reboot-1574650660572504115-validate.service'
s=importlib.util.spec_from_file_location('inc01_boot_probe',R/'boot_probe.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
def atomic(name,d):
 p=R/name;t=p.with_name(p.name+'.new-'+str(os.getpid()))
 with t.open('x') as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(t,0o600);os.replace(t,p)
def main():
 pre=json.loads((R/'prestate.json').read_text());result={'at':c.now(),'authorization_message_id':'1574650660572504115','overall':False,'status':'waiting_new_boot_readiness'}
 try:
  assert not (R/'postboot-result.json').exists(),'existing durable result; do not replay'
  assert P('/proc/sys/kernel/random/boot_id').read_text().strip()!=pre['boot_id'],'validator must not run before reboot'
  deadline=time.monotonic()+600
  while True:
   states={n:c.unit(n) for n in c.SERVICES};active=all(x['ActiveState']=='active' and int(x['MainPID'])>0 for x in states.values())
   mariadb=c.run(['mariadb-admin','ping'],15,False).returncode==0
   pg=P('/run/mgs-postgresql18/.s.PGSQL.5432').exists()
   http=c.run(['curl','-sS','--max-time','10','-o','/dev/null','-w','%{http_code}','https://dash.mgsdigitalcorp.com/login'],15,False)
   ready=active and mariadb and pg and http.returncode==0 and http.stdout.strip()=='200'
   atomic('readiness-progress.json',{'at':c.now(),'active_services':active,'mariadb_ping':mariadb,'postgresql_socket':pg,'finance_login_http':http.stdout.strip(),'services':states})
   if ready:break
   if time.monotonic()>deadline:raise RuntimeError('essential service/database/public readiness deadline')
   time.sleep(5)
  observed=c.observe(pre,refresh=True);atomic('postboot-observation.json',observed)
  result.update(observed['assessment']);result.update({'status':'runtime_validated_pending_foreground_closure' if result['overall'] else 'postboot_gate_failed','boot_id':observed['boot_id'],'kernel':observed['kernel'],'journal_error_count':len(observed.get('journal_errors') or []),'http':observed['http']})
 except BaseException as e:result.update({'overall':False,'status':'validator_exception','diagnosis':type(e).__name__+': '+str(e)[:700]})
 finally:
  result['finished_at']=c.now();atomic('postboot-result.json',result)
  d=c.run(['systemctl','disable',UNIT],30,False);atomic('validator-exit.json',{'at':c.now(),'disable_rc':d.returncode,'definition':'retained_no_deletion','runtime_overall':result['overall']})
 return 0
if __name__=='__main__':raise SystemExit(main())
