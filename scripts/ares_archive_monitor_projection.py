"""Keep quota waits stable without hiding real new failures or claiming recovery."""
import copy
READ='API call to drive.files.list failed with error: Internal Error'
CREATE='API call to drive.files.create failed with error: The operation was successful, but there was an error preparing the response.'
def stable_incident(snapshot,retryable_job_ids=()):
 out=copy.deepcopy(snapshot)
 if out.get('owner_worker_status')!='runtime_budget_paused':return out
 # The rolling reconciliation scan may include different pending receipts.
 # Their known deferred provider errors are not separate quota incidents.
 # Preserve all unknown/auth/integrity/permission errors verbatim.
 out['blocked']=[x for x in out.get('blocked',[]) if not (x.get('job_id') in retryable_job_ids and str(x.get('reason','')).removeprefix('OWNER_BLOCKED:') in (READ,CREATE))]
 out['runtime_wait']='existing_90min_rolling_window_no_bypass'
 out['provider_retry_state']='deferred_existing_requests_not_recreated'
 # Still blocked, not healthy or recovered. Polling and safety gates stay on.
 return out

def native_retryable_jobs(d,c,snapshot):
 import json
 import ares_archive_bridge as b
 ids=set()
 for row in snapshot.get('blocked',[]):
  jid=row.get('job_id');reason=str(row.get('reason','')).removeprefix('OWNER_BLOCKED:')
  if not jid or reason not in (READ,CREATE):continue
  found=d.one(c['receipts_folder_id'],'receipt:'+jid)
  if not found:continue
  meta=d.meta(found['id']);b.require_publisher(meta,b.ACCOUNT)
  if meta.get('parents')!=[c['receipts_folder_id']] or meta.get('properties',{}).get('mgsArchiveKey')!='receipt:'+jid:raise b.ArchiveError('MONITOR_RECEIPT_SCOPE')
  body=json.loads(d.raw(found['id']))
  attempts=body.get('attempts')
  if body.get('jobId')==jid and body.get('status')=='blocked' and body.get('reason')==reason and isinstance(attempts,int) and not isinstance(attempts,bool) and 0<attempts<5 and body.get('retryAfter'):ids.add(jid)
 return ids
