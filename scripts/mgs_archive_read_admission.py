"""Read-only I/O admission; all native mutations keep the canonical writer lock."""
import contextlib,fcntl,time
from pathlib import Path
import ares_archive_bridge as b
@contextlib.contextmanager
def binary_read_slot():
 b.DATA.mkdir(parents=True,exist_ok=True);held=None
 try:
  while held is None:
   for i in range(4):
    f=(b.DATA/('.binary-read-'+str(i)+'.lock')).open('a+')
    try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);held=f;break
    except BlockingIOError:f.close()
   if held is None:time.sleep(0.05)
  yield
 finally:
  if held:fcntl.flock(held,fcntl.LOCK_UN);held.close()

def readonly_map(read, values, *, parallel=True):
 """Ordered GET-only work, at most four in flight; caller owns write lease.

 Never pass mutations here. Drain running reads on failure and do not submit
 another wave after any failed result. No shared cache or skipped verification.
 """
 from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
 values=list(values)
 if not parallel or len(values)<2:return [read(value) for value in values]
 results=[None]*len(values);cursor=0
 with ThreadPoolExecutor(max_workers=min(4,len(values)),thread_name_prefix='mgs-sa-read') as pool:
  pending={}
  while cursor<len(values) and len(pending)<4:
   pending[pool.submit(read,values[cursor])]=cursor;cursor+=1
  try:
   while pending:
    done,_=wait(pending,return_when=FIRST_COMPLETED)
    # Inspect the entire completed wave before submitting anything new.
    for future in done:results[pending.pop(future)]=future.result()
    while cursor<len(values) and len(pending)<4:
     pending[pool.submit(read,values[cursor])]=cursor;cursor+=1
  except BaseException:
   for future in pending:future.cancel()
   raise
 return results

def bounded_hashes(original):
 def run(fid):
  with binary_read_slot():return original(fid)
 return run

def backup_read_hashes(original,writer_lease):
 """A backup-only claim remains held; temporarily release ONLY the global
 mutation lease during full binary GET. Reacquire before returning/raising.
 The verifier still rechecks native metadata and ACKs under the writer lease.
 """
 def run(fid):
  if writer_lease is None:
   with binary_read_slot():return original(fid)
  fcntl.flock(writer_lease,fcntl.LOCK_UN)
  try:
   with binary_read_slot():return original(fid)
  finally:fcntl.flock(writer_lease,fcntl.LOCK_EX)
 return run
