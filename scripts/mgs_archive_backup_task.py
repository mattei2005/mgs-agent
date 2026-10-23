"""One existing cron supervises a silent finite backup child; no new schedule.
The parent remains SA-only. The child is the previously approved private lane.
"""
import os,sys,json,fcntl,subprocess
from pathlib import Path
import ares_archive_bridge as b
import mgs_backup_automation as a
HOME=b.DATA/'owner-connector/backup-lane'

def start_ticks(pid):
 try:
  text=Path('/proc/'+str(pid)+'/stat').read_text();fields=text.rpartition(')')[2].split()
  return None if fields[0]=='Z' else fields[19]
 except (FileNotFoundError,ProcessLookupError,IndexError):return None

def supervise():
 HOME.mkdir(parents=True,exist_ok=True)
 with (HOME/'supervisor.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);state=b.read_json(HOME/'background-task.json',{});now=b.now_iso()
  if state.get('pid') and state.get('start_ticks') and start_ticks(state['pid'])==state['start_ticks']:
   return {'status':'ok','in_progress':True,'blocked':[],'schema':'mgs.private.backup.supervision.v1','sa_cycle':{'status':'private_backup_in_progress','blocked':[],'archive_trash_enabled':False}}
  prior=None;recovery_attempts=state.get('recovery_attempts',0)
  if state.get('result_path'):
   try:prior=json.loads(Path(state['result_path']).read_text())
   except (ValueError,FileNotFoundError):
    recovery_attempts+=1
    if recovery_attempts>2:return {'status':'blocked','blocked':[{'component':'private_backup_child','reason':'PRIVATE_BACKUP_CHILD_REPEATED_NO_RESULT'}],'sa_cycle':{'status':'private_backup_child_failed','blocked':[]}}
    # No blind native move replay: the same private lane reconciles its
    # persisted intent/ID/receipt before any mutation. Preserve the failed log.
    b.atomic_json(HOME/('failed-task-'+state.get('run_id','unknown')+'.json'),{**state,'detected_at':now,'reason':'child_lost_without_result','retry_strategy':'same bound journal, native reconciliation before move'})
   if prior and (prior.get('schema')!='mgs.private.backup.heartbeat.v1' or prior.get('status')!='ok' or prior.get('blocked')):return {'status':'blocked','blocked':prior.get('blocked') or [{'component':'private_backup_child','reason':'PRIVATE_BACKUP_CHILD_RESULT_INVALID'}],'sa_cycle':{'status':'private_backup_child_failed','blocked':[]}}
  # An explicitly supervised foreground drain/canary can own the same lane.
  with (HOME/'backup-lane.lock').open('a+') as lane:
   try:fcntl.flock(lane,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:return {'status':'ok','in_progress':True,'blocked':[],'sa_cycle':{'status':'private_backup_foreground_in_progress','blocked':[]}}
  sa_cycle=a.cycle(apply=True) if not recovery_attempts else {'status':'private_backup_recovering_same_journal','blocked':[],'archive_trash_enabled':False}
  if sa_cycle.get('blocked'):return {'status':'blocked','blocked':sa_cycle['blocked'],'sa_cycle':sa_cycle}
  import uuid
  run=uuid.uuid4().hex;out=HOME/('task-'+run+'.json');err=HOME/('task-'+run+'.stderr')
  unit='mgs-backup-archive-task-'+run
  command=['systemd-run','--quiet','--collect','--unit='+unit,'--property=Type=exec','--property=WorkingDirectory='+str(b.BASE),'--property=StandardOutput=append:'+str(out),'--property=StandardError=append:'+str(err),sys.executable,str(b.BASE/'scripts/mgs_private_backup_transport.py'),'tick','--apply']
  launched=subprocess.run(command,capture_output=True,text=True,timeout=30)
  if launched.returncode:raise b.ArchiveError('PRIVATE_BACKUP_TRANSIENT_TASK_START_FAILED')
  check=subprocess.run(['systemctl','show',unit+'.service','--value','-p','MainPID'],capture_output=True,text=True,timeout=15)
  if check.returncode or not check.stdout.strip().isdigit():raise b.ArchiveError('PRIVATE_BACKUP_TRANSIENT_PID_UNKNOWN')
  pid=int(check.stdout.strip());ticks=start_ticks(pid)
  state={'schema':'mgs.private.backup.task.v1','started_at':now,'pid':pid,'start_ticks':ticks,'unit':unit+'.service','result_path':str(out),'stderr_path':str(err),'run_id':run,'previous_completed_task':state.get('run_id'),'recovery_attempts':recovery_attempts};b.atomic_json(HOME/'background-task.json',state)
  return {'schema':'mgs.private.backup.supervision.v1','status':'ok','in_progress':True,'blocked':[],'sa_cycle':sa_cycle,'previous_verified_moves':prior.get('moved',[]) if prior else []}
