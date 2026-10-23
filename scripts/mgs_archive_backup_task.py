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
  prior=None
  if state.get('result_path'):
   try:prior=json.loads(Path(state['result_path']).read_text())
   except (ValueError,FileNotFoundError):return {'status':'blocked','blocked':[{'component':'private_backup_child','reason':'PRIVATE_BACKUP_CHILD_DIED_WITHOUT_RESULT'}],'sa_cycle':{'status':'private_backup_child_failed','blocked':[]}}
   if prior.get('schema')!='mgs.private.backup.heartbeat.v1' or prior.get('status')!='ok' or prior.get('blocked'):return {'status':'blocked','blocked':prior.get('blocked') or [{'component':'private_backup_child','reason':'PRIVATE_BACKUP_CHILD_RESULT_INVALID'}],'sa_cycle':{'status':'private_backup_child_failed','blocked':[]}}
  # An explicitly supervised foreground drain/canary can own the same lane.
  with (HOME/'backup-lane.lock').open('a+') as lane:
   try:fcntl.flock(lane,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:return {'status':'ok','in_progress':True,'blocked':[],'sa_cycle':{'status':'private_backup_foreground_in_progress','blocked':[]}}
  sa_cycle=a.cycle(apply=True)
  if sa_cycle.get('blocked'):return {'status':'blocked','blocked':sa_cycle['blocked'],'sa_cycle':sa_cycle}
  import uuid
  run=uuid.uuid4().hex;out=HOME/('task-'+run+'.json');err=HOME/('task-'+run+'.stderr')
  with out.open('wb') as output,err.open('wb') as errors:
   process=subprocess.Popen([sys.executable,str(b.BASE/'scripts/mgs_private_backup_transport.py'),'tick','--apply'],stdin=subprocess.DEVNULL,stdout=output,stderr=errors,start_new_session=True,cwd=str(b.BASE))
  state={'schema':'mgs.private.backup.task.v1','started_at':now,'pid':process.pid,'start_ticks':start_ticks(process.pid),'result_path':str(out),'stderr_path':str(err),'run_id':run,'previous_completed_task':state.get('run_id')};b.atomic_json(HOME/'background-task.json',state)
  return {'schema':'mgs.private.backup.supervision.v1','status':'ok','in_progress':True,'blocked':[],'sa_cycle':sa_cycle,'previous_verified_moves':prior.get('moved',[]) if prior else []}
