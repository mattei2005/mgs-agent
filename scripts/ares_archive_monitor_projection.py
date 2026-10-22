"""Keep quota waits stable without hiding real new failures or claiming recovery."""
import copy
READ='API call to drive.files.list failed with error: Internal Error'
CREATE='API call to drive.files.create failed with error: The operation was successful, but there was an error preparing the response.'
def stable_incident(snapshot,retryable_job_ids=()):
 out=copy.deepcopy(snapshot)
 if out.get('owner_worker_status')!='runtime_budget_paused' and out.get('owner_bulk_runtime_paused') is not True:return out
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

def native_runtime_context(snapshot,heartbeat,expected_sha,now=None):
 from datetime import datetime,timezone,timedelta
 out=copy.deepcopy(snapshot);now=now or datetime.now(timezone.utc)
 bulk=(heartbeat.get('runtimeBudget') or {}).get('bulk') or {}
 trusted=(heartbeat.get('workerSha256')==expected_sha==snapshot.get('owner_worker_sha256') and heartbeat.get('executionMode') in ('manual_probe_only','scheduled_bulk') and heartbeat.get('status') in ('ok','runtime_budget_paused') and not heartbeat.get('blocked') and heartbeat.get('canaryAcknowledged') is True)
 paused=trusted and bulk.get('paused') is True
 out['owner_bulk_runtime_paused']=bool(paused);out['runtime_wait_expected']=False
 if paused:
  try:
   due=datetime.fromisoformat(bulk['earliestRetryAt'].replace('Z','+00:00'))
   observed=datetime.fromisoformat(heartbeat['executedAt'].replace('Z','+00:00'))
   if due.tzinfo is None or observed.tzinfo is None or not 0<=(due-observed).total_seconds()<=86400:raise ValueError('invalid wait estimate')
   out['runtime_wait_expected']=now<due+timedelta(minutes=20)
  except (KeyError,TypeError,ValueError):pass
 return out

def notification_class(snapshot):
 if snapshot.get('status')=='blocked' and snapshot.get('blocked')==[] and not snapshot.get('reason') and snapshot.get('queue_enabled') is True and snapshot.get('owner_repin_pending') is False and snapshot.get('owner_bulk_runtime_paused') is True and snapshot.get('runtime_wait_expected') is True:return 'known_runtime_wait'
 return 'actionable_or_unproven'
