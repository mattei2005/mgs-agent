#!/usr/bin/env python3
"""Bounded private-owner backup move lane; same-ID, no copy/delete/ACL writes."""
from __future__ import annotations
import sys,json,re,hashlib,urllib.request,urllib.parse,urllib.error,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import mgs_backup_automation as a
import mgs_backup_archive as backup
import mgs_archive_owner_transport as t
HOME=t.HOME/'backup-lane'
APPROVAL='1562972150455992431'
TYPE='vps_backup_move_request'

def validate_job(j,p,plan_sha,historical=None):
 expected={'schema':'mgs.backup.move.request.v1','authorizationMessageId':p['authorizationMessageId'],'migrationAuthorizationMessageId':p['migrationAuthorizationMessageId'],'planSha256':plan_sha,'bindingSha256':p['bindingSha256'],'deleteSource':False,'archiveTrashEnabled':False}
 if any(j.get(k)!=v for k,v in expected.items()) or j.get('deleteSource') is not False or j.get('archiveTrashEnabled') is not False:raise b.ArchiveError('PRIVATE_BACKUP_JOB_BINDING')
 x=j.get('asset',{});tier=x.get('tier');parents=p['tiers'].get(tier)
 if not parents or x.get('sourceId')==p['pilotId'] or x.get('sourceParentId')!=parents['sourceId'] or x.get('destinationParentId')!=parents['archiveId'] or x.get('mimeType')!='application/pgp-encrypted' or x.get('mode')!=('quick' if tier=='hourly' else 'full') or not re.fullmatch('mgs-dr-'+tier+'-[0-9]{8}T[0-9]{6}Z\\.zip\\.gpg',x.get('name','')) or not re.fullmatch('[A-Za-z0-9_-]{8,}',x.get('sourceId','')):raise b.ArchiveError('PRIVATE_BACKUP_ASSET_SCOPE')
 historic=j.get('wholeDriveAuthorizationMessageId')==APPROVAL
 if historic and (not historical or historical.get('approval_message_id')!=APPROVAL or historical.get('plan_sha256')!=plan_sha or j.get('historicalManifestSha256')!=a.sha(historical) or x not in historical.get('assets',[])):raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_BINDING')
 if not re.fullmatch('[1-9][0-9]*',str(x.get('size',''))) or not re.fullmatch('[a-f0-9]{32}',x.get('md5','')) or not re.fullmatch('[a-f0-9]{64}',x.get('sha256','')) or (not historic and b.timestamp(x['sourceCreatedTime'])<b.timestamp(p['futureCreatedNotBefore'])):raise b.ArchiveError('PRIVATE_BACKUP_ASSET_BYTES_OR_TIME')
 props=x.get('managedProperties',{})
 if props.get('mgs_dr')!='true' or props.get('sha256')!=x['sha256'] or props.get('tier')!=tier or props.get('mode')!=x['mode'] or j.get('jobId')!=a.job_id(p,x):raise b.ArchiveError('PRIVATE_BACKUP_MANAGED_OR_JOB_ID')
 return True

def move_decision(meta,x,intent_exists):
 if meta.get('driveId')==b.SOURCE_DRIVE and meta.get('parents')==[x['sourceParentId']]:
  if intent_exists:raise b.ArchiveError('PRIVATE_BACKUP_AMBIGUOUS_NO_REPLAY')
  return 'move_once'
 if not meta.get('driveId') and meta.get('parents')==[x['destinationParentId']] and intent_exists:return 'reconcile_landed'
 raise b.ArchiveError('PRIVATE_BACKUP_UNEXPLAINED_LOCATION')

class Owner(t.OwnerDrive):
 def __init__(self):super().__init__();self.move_binding=None
 def api(self,method,path,params=None,payload=None):
  if method!='PATCH':return super().api(method,path,params,payload)
  params=params or {}
  x=self.move_binding
  if not x or path!='files/'+x['sourceId'] or payload!={} or params.get('addParents')!=x['destinationParentId'] or params.get('removeParents')!=x['sourceParentId']:raise b.ArchiveError('PRIVATE_BACKUP_PATCH_SCOPE')
  req=urllib.request.Request(self.base+path+'?'+urllib.parse.urlencode(params),data=b'{}',headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json','User-Agent':'MGS-Private-Backup/1'},method='PATCH')
  try:
   with urllib.request.urlopen(req,timeout=90) as response:return json.load(response)
  except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):raise b.ArchiveError('PRIVATE_BACKUP_PATCH_RESPONSE_AMBIGUOUS') from None
 def publish_slot(self,c,j,p,metadata,journal):
  fid=j['receiptFileId'];old=self.meta(fid);key='backup-receipt:'+j['jobId'];prior=json.loads(self.raw(fid))
  if old.get('driveId')!=b.SOURCE_DRIVE or old.get('parents')!=[c['receipts_folder_id']] or old.get('properties',{}).get('mgsArchiveKey')!=key:raise b.ArchiveError('PRIVATE_BACKUP_RECEIPT_SLOT_SCOPE')
  if prior.get('status')=='moved':
   b.require_publisher(old,b.ACCOUNT)
   if prior.get('requestSha256')!=a.sha(j) or prior.get('archiveId')!=j['asset']['sourceId']:raise b.ArchiveError('PRIVATE_BACKUP_OLD_RECEIPT')
   return prior
  b.require_publisher(old,b.CANONICAL_SA)
  if prior.get('schema')!='mgs.backup.move.receipt.slot.v1' or prior.get('jobId')!=j['jobId'] or prior.get('sourceId')!=j['asset']['sourceId']:raise b.ArchiveError('PRIVATE_BACKUP_INITIAL_SLOT')
  body={'schema':'mgs.backup.move.receipt.v1','status':'moved','jobId':j['jobId'],'authorizationMessageId':p['authorizationMessageId'],'planSha256':j['planSha256'],'requestSha256':a.sha(j),'sourceId':j['asset']['sourceId'],'archiveId':metadata['id'],'destinationParentId':j['asset']['destinationParentId'],'archiveMetadata':metadata,'deleteSource':False,'archiveTrashEnabled':False,'completedAt':b.now_iso(),'executor':'private-vps-backup-v1'}
  keyj='receipt:'+j['jobId'];stored=journal.data['intents'].get(keyj,{}).get('binding',{}).get('body')
  if stored:body=stored
  else:journal.intent(keyj,{'file_id':fid,'body':body})
  data=b.canonical(body);boundary='mgs-'+uuid.uuid4().hex;meta={'properties':{**old['properties'],'mgsArchiveType':'backup_move_receipt','sha256':a.sha(data)}}
  wire=(('--'+boundary+'\r\nContent-Type: application/json\r\n\r\n').encode()+b.canonical(meta)+('\r\n--'+boundary+'\r\nContent-Type: application/json\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode())
  req=urllib.request.Request('https://www.googleapis.com/upload/drive/v3/files/'+fid+'?uploadType=multipart&supportsAllDrives=true&fields=id',data=wire,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/related; boundary='+boundary},method='PATCH')
  try:
   with urllib.request.urlopen(req,timeout=90) as response:json.load(response)
  except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):pass
  actual=self.meta(fid);b.require_publisher(actual,b.ACCOUNT)
  if self.raw(fid)!=data or actual.get('properties',{}).get('sha256')!=a.sha(data) or actual['properties'].get('mgsArchiveType')!='backup_move_receipt':raise b.ArchiveError('PRIVATE_BACKUP_RECEIPT_READBACK')
  journal.landed(keyj,fid);return body

def move_one(owner,sa,c,p,s,job,journal):
 j=job['body'];historical=None
 if j.get('wholeDriveAuthorizationMessageId'):
  binding=b.read_json(HOME/'historical-manifest-binding.json',{});fid=binding.get('file_id')
  if not fid:raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_UNPUBLISHED')
  manifest_meta=owner.meta(fid);b.require_publisher(manifest_meta,b.CANONICAL_SA);raw=owner.raw(fid)
  if manifest_meta.get('driveId')!=b.SOURCE_DRIVE or manifest_meta.get('parents')!=[c['control_folder_id']] or a.sha(raw)!=binding.get('sha256'):raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_PROVENANCE')
  historical=json.loads(raw)
 validate_job(j,p,s['plan_sha256'],historical);request=sa.meta(job['request_file_id']);b.require_publisher(request,b.CANONICAL_SA)
 if request.get('parents')!=[c['requests_folder_id']] or request.get('properties',{}).get('mgsArchiveType')!=TYPE or sa.raw(request['id'])!=b.canonical(j):raise b.ArchiveError('PRIVATE_BACKUP_REQUEST_PROVENANCE')
 x=j['asset'];meta=backup.native_meta(owner,x['sourceId']);a.check_content(meta,x);key='move:'+j['jobId'];intent=journal.data['intents'].get(key)
 prior=json.loads(owner.raw(j['receiptFileId']))
 if prior.get('status')=='moved':
  b.require_publisher(owner.meta(j['receiptFileId']),b.ACCOUNT)
  if prior.get('requestSha256')!=a.sha(j):raise b.ArchiveError('PRIVATE_BACKUP_PRIOR_MOVE_MISMATCH')
 elif move_decision(meta,x,bool(intent))=='move_once':
  cp,_=a.corp.load_plan();a.corp.check_acl(a.corp.h.permissions(sa,x['sourceId']),a.corp.desired(cp,True))
  folder=backup.native_meta(owner,x['destinationParentId'])
  if folder.get('driveId') or folder.get('parents')!=[p['archiveRootId']] or folder.get('name')!=x['tier'] or folder.get('trashed') is not False or not any(z.get('permissionId')==p['ownerPermissionId'] for z in folder.get('owners',[])):raise b.ArchiveError('PRIVATE_BACKUP_DESTINATION_FOLDER')
  hashes=sa.hashes(x['sourceId'])
  if hashes!={k:x[k] for k in ['size','md5','sha256']}:raise b.ArchiveError('PRIVATE_BACKUP_SOURCE_STREAM')
  journal.intent(key,{'job_id':j['jobId'],'source_id':x['sourceId'],'old_parent':x['sourceParentId'],'new_parent':x['destinationParentId'],'request_sha256':a.sha(j)});owner.move_binding=x
  try:owner.api('PATCH','files/'+x['sourceId'],{'supportsAllDrives':'true','addParents':x['destinationParentId'],'removeParents':x['sourceParentId'],'fields':'id'},{})
  except b.ArchiveError:
   landed=backup.native_meta(owner,x['sourceId'])
   if landed.get('driveId') or landed.get('parents')!=[x['destinationParentId']]:raise b.ArchiveError('PRIVATE_BACKUP_MOVE_UNKNOWN_NO_REPLAY') from None
  journal.landed(key,x['sourceId'])
 actual=backup.native_meta(owner,x['sourceId']);a.check_content(actual,x)
 if actual.get('driveId') or actual.get('parents')!=[x['destinationParentId']] or not any(z.get('emailAddress')==b.ACCOUNT and z.get('permissionId')==p['ownerPermissionId'] for z in actual.get('owners',[])):raise b.ArchiveError('PRIVATE_BACKUP_LANDED_IDENTITY')
 sa_meta=backup.native_meta(sa,x['sourceId'])
 if sa_meta.get('appProperties')!=x['managedProperties']:raise b.ArchiveError('PRIVATE_BACKUP_SA_PRIVATE_PROPERTIES')
 owner.publish_slot(c,j,p,actual,journal)
 state=b.read_json(a.STATE,{})
 if not isinstance(state,dict) or j['jobId'] not in state.get('jobs',{}):raise b.ArchiveError('PRIVATE_BACKUP_STATE_MISSING')
 return a.reconcile(sa,c,p,s,state,state['jobs'][j['jobId']])

def activate_handoff():
 with b.queue_lock():
  handoff=b.read_json(HOME/'handoff.json',{});p,s=a.load();c=b.config_load();sa=b.Drive(True)
  if handoff.get('approval_message_id')!=APPROVAL or handoff.get('phase') not in ['draining','canary_pending'] or (b.timestamp(b.now_iso())-b.timestamp(handoff['reserved_at'])).total_seconds()<420:raise b.ArchiveError('PRIVATE_BACKUP_DRAIN_NOT_COMPLETE')
  for row in handoff['legacy_requests']:
   meta=sa.meta(row['id']);b.require_publisher(meta,b.CANONICAL_SA)
   if a.sha(sa.raw(row['id']))!=row['body_sha256']:raise b.ArchiveError('PRIVATE_BACKUP_REQUEST_CHANGED_DURING_DRAIN')
   if meta['properties'].get('mgsArchiveState')=='verified':continue
   if meta['properties'].get('mgsArchiveState') not in ['vps_reserved','queued'] or meta['properties'].get('mgsArchiveType') not in ['backup_move_request',TYPE]:raise b.ArchiveError('PRIVATE_BACKUP_RESERVATION_DRIFT')
   props={**meta['properties'],'mgsArchiveState':'queued','mgsArchiveType':TYPE};sa.api('PATCH','files/'+row['id'],{'supportsAllDrives':'true','fields':'id,properties'},{'properties':props})
   after=sa.meta(row['id']);b.require_publisher(after,b.CANONICAL_SA)
   if after['properties']['mgsArchiveType']!=TYPE or after['properties']['mgsArchiveState']!='queued':raise b.ArchiveError('PRIVATE_BACKUP_HANDOFF_READBACK')
  handoff.update(phase='canary_pending',converted_at=b.now_iso());b.atomic_json(HOME/'handoff.json',handoff);return handoff

def prepare_historical():
 with b.queue_lock():
  p,s=a.load();c=b.config_load();sa=b.Drive(True);proof=b.read_json(HOME/'canary.json',{});approval=b.read_json(t.HOME/'whole-drive-scope-confirmation-1562972150455992431.json',{})
  if approval.get('backup_lane_extension_authorized') is not True or proof.get('same_id_verified') is not True or proof.get('canonical_sa_streams_ack_verified') is not True:raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_ACCEPTANCE')
  manifest=b.read_json(HOME/'historical-manifest.json')
  if not manifest:
   assets=[]
   for tier,parents in sorted(p['tiers'].items()):
    for row in backup.children(sa,parents['sourceId'],managed=True):
     m=backup.native_meta(sa,row['id']);props=m.get('appProperties',{});sh=m.get('sha256Checksum')
     if m.get('driveId')!=b.SOURCE_DRIVE or m.get('parents')!=[parents['sourceId']] or sh!=props.get('sha256') or m.get('trashed') is not False:raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_SNAPSHOT')
     asset={'sourceId':m['id'],'sourceParentId':parents['sourceId'],'destinationParentId':parents['archiveId'],'tier':tier,'mode':'quick' if tier=='hourly' else 'full','name':m['name'],'mimeType':m['mimeType'],'size':m['size'],'version':m['version'],'md5':m['md5Checksum'],'sha256':sh,'sourceCreatedTime':m['createdTime'],'managedProperties':props};assets.append(asset)
   manifest={'schema':'mgs.private.backup.historical.manifest.v1','approval_message_id':APPROVAL,'plan_sha256':s['plan_sha256'],'source_root_id':p['sourceRootId'],'archive_root_id':p['archiveRootId'],'frozen_at':b.now_iso(),'assets':sorted(assets,key=lambda x:(x['sourceCreatedTime'],x['sourceId'])),'same_id_move_only':True,'delete_source':False,'archive_trash_enabled':False};b.atomic_json(HOME/'historical-manifest.json',manifest)
  stage=b.read_json(HOME/'historical-manifest-binding.json',{});digest=a.sha(manifest);state=b.read_json(a.STATE);fid=a.immutable(sa,c['control_folder_id'],'private-backup-historical:'+digest,'private_backup_historical_manifest',manifest,state)
  b.require_publisher(sa.meta(fid),b.CANONICAL_SA)
  if sa.raw(fid)!=b.canonical(manifest):raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_PUBLICATION')
  stage.update(file_id=fid,sha256=digest,asset_count=len(manifest['assets']));b.atomic_json(HOME/'historical-manifest-binding.json',stage);return stage

def enqueue_historical_locked(sa,c,p,s,state):
 binding=b.read_json(HOME/'historical-manifest-binding.json',{});manifest=b.read_json(HOME/'historical-manifest.json',{})
 if not binding:return None
 if a.sha(manifest)!=binding.get('sha256') or manifest.get('approval_message_id')!=APPROVAL:raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_LOCAL_BINDING')
 for x in manifest['assets']:
  jid=a.job_id(p,x)
  if jid in state['jobs']:continue
  m=backup.native_meta(sa,x['sourceId']);a.check_content(m,x)
  if m.get('driveId')!=b.SOURCE_DRIVE or m.get('parents')!=[x['sourceParentId']] or m.get('appProperties')!=x['managedProperties']:raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_SOURCE_DRIFT')
  slot={'schema':'mgs.backup.move.receipt.slot.v1','jobId':jid,'sourceId':x['sourceId'],'planSha256':s['plan_sha256'],'status':'awaiting_owner','deleteSource':False,'archiveTrashEnabled':False};slotid=a.immutable(sa,c['receipts_folder_id'],'backup-receipt:'+jid,'backup_receipt_slot',slot,state)
  j={'schema':'mgs.backup.move.request.v1','jobId':jid,'authorizationMessageId':p['authorizationMessageId'],'migrationAuthorizationMessageId':p['migrationAuthorizationMessageId'],'planSha256':s['plan_sha256'],'bindingSha256':p['bindingSha256'],'asset':x,'receiptFileId':slotid,'deleteSource':False,'archiveTrashEnabled':False,'wholeDriveAuthorizationMessageId':APPROVAL,'historicalManifestSha256':binding['sha256']};validate_job(j,p,s['plan_sha256'],manifest)
  state['jobs'][jid]={'jobId':jid,'body':j,'verified':False};b.atomic_json(a.STATE,state);fid=a.immutable(sa,c['requests_folder_id'],'backup-move:'+jid,TYPE,j,state);state['jobs'][jid]['request_file_id']=fid;b.atomic_json(a.STATE,state)
  sa.api('PATCH','files/'+fid,{'supportsAllDrives':'true','fields':'id,properties'},{'properties':{'mgsArchiveState':'queued'}})
  if sa.meta(fid)['properties'].get('mgsArchiveState')!='queued':raise b.ArchiveError('PRIVATE_BACKUP_HISTORICAL_QUEUE_READBACK')
  return jid

def tick():
 with b.queue_lock():
  p,s=a.load();c=b.config_load();handoff=b.read_json(HOME/'handoff.json',{});approval=b.read_json(t.HOME/'whole-drive-scope-confirmation-1562972150455992431.json',{})
  if approval.get('backup_lane_extension_authorized') is not True or s.get('owner_executor_mode') not in ['vps_handoff','vps'] or handoff.get('phase') not in ['canary_pending','active']:raise b.ArchiveError('PRIVATE_BACKUP_NOT_AUTHORIZED_OR_READY')
  owner=Owner();sa=b.Drive(True);state=b.read_json(a.STATE);journal=t.Journal(HOME/'journal.json');done=[];blocked=[]
  enqueue_historical_locked(sa,c,p,s,state)
  candidates=[j for j in state['jobs'].values() if not j.get('verified') and j.get('request_file_id')]
  candidates.sort(key=lambda j:j['body']['asset']['sourceCreatedTime'])
  for job in candidates:
   meta=sa.meta(job['request_file_id'])
   if meta['properties'].get('mgsArchiveType')!=TYPE:continue
   try:
    result=move_one(owner,sa,c,p,s,job,journal)
    if result not in ['verified','cached']:raise b.ArchiveError('PRIVATE_BACKUP_SA_VERIFY_PENDING')
    done.append({'job_id':job['jobId'],'same_id':job['body']['asset']['sourceId'],'status':result})
   except b.ArchiveError as e:blocked.append({'job_id':job['jobId'],'reason':str(e)[:200]})
   break  # Preserve one native move per tick.
  hb={'schema':'mgs.private.backup.heartbeat.v1','executedAt':b.now_iso(),'status':'blocked' if blocked else 'ok','blocked':blocked,'moved':done,'planSha256':s['plan_sha256'],'workerSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'archiveTrashEnabled':False,'deleteSource':False,'executor':'private-vps-backup-v1'}
  owner.write_json(c['control_folder_id'],'heartbeat:vps-backup-v1','vps_backup_heartbeat',hb,journal);b.atomic_json(HOME/'last-tick.json',hb)
  if done and not blocked and handoff['phase']=='canary_pending':
   proof={'schema':'mgs.private.backup.canary.v1','verified_at':b.now_iso(),'moves':done,'same_id_verified':True,'canonical_sa_streams_ack_verified':True,'plan_sha256':s['plan_sha256'],'worker_sha256':hb['workerSha256'],'archive_trash_enabled':False,'source_permanent_delete':False};b.atomic_json(HOME/'canary.json',proof)
   handoff.update(phase='active',activated_at=b.now_iso());b.atomic_json(HOME/'handoff.json',handoff);s.update(owner_executor_mode='vps',private_owner_sha256=hb['workerSha256']);b.atomic_json(a.STAGE,s)
  return hb

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['activate-handoff','prepare-historical','tick']);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 if not args.apply:raise SystemExit('APPLY_REQUIRED')
 result=activate_handoff() if args.action=='activate-handoff' else prepare_historical() if args.action=='prepare-historical' else tick();print(json.dumps(result));raise SystemExit(2 if result.get('status')=='blocked' else 0)
