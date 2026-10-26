#!/usr/bin/env python3
"""Private owner creates bounded empty JSON slots; canonical SA publishes content.
No owner token is returned or used by an agent consumer. Production activation is
separate from the native control-store canary and existing source queue.
"""
from __future__ import annotations
import sys,json,hashlib,fcntl,re,subprocess,urllib.request,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
HOME=b.DATA/'owner-connector'/'control-store'
CONFIG=HOME/'binding.json'
MAX_BYTES=12000000
ALLOWED_KINDS={'vps_request','vps_backfill_request','request','receipt','ack','backfill_ack','backfill_manifest','backfill_metadata_reconciliation','backup_move_receipt','backup_receipt_slot','backup_ack','backup_direct_ack','vps_backup_move_request','backup_plan','private_backup_historical_manifest','retirement_receipt','source_retirement_receipt','source_retirement_intent','retirement_authorization','vps_heartbeat','vps_backup_heartbeat','control_store_canary','worker_source','authorization','lineage_map','stock_layout_snapshot'}

def validate_request(j,c):
 if c.get('schema')!='mgs.private.control.binding.v1' or c.get('approval_message_id')!='1562972150455992431' or j.get('schema')!='mgs.private.control.slot.request.v1' or j.get('parent_id') not in c.get('parent_ids',[]) or j.get('kind') not in ALLOWED_KINDS or j.get('mime') not in ['application/json','application/javascript']:raise b.ArchiveError('CONTROL_SLOT_SCOPE')
 if j.get('kind')=='source_retirement_intent' and j.get('mime')!='application/json':raise b.ArchiveError('CONTROL_SLOT_SCOPE')
 if not isinstance(j.get('key'),str) or not 1<=len(j['key'])<=300 or any(x in j['key'] for x in ['\x00','\r','\n',"'"]) or not re.fullmatch('[a-f0-9]{64}',j.get('sha256','')):raise b.ArchiveError('CONTROL_SLOT_KEY_OR_DIGEST')
 if type(j.get('size')) is not int or not 0<=j['size']<=MAX_BYTES or not isinstance(j.get('name'),str) or not j['name'] or len(j['name'])>300 or '/' in j['name'] or '\\' in j['name']:raise b.ArchiveError('CONTROL_SLOT_SIZE_OR_NAME')
 return True

def owner_slot(j):
 # Only the isolated CLI calls this function; never the agent-side publisher.
 import mgs_archive_owner_transport as t
 c=b.read_json(CONFIG,{});validate_request(j,c);approval=b.read_json(t.HOME/'whole-drive-scope-confirmation-1562972150455992431.json',{})
 if approval.get('all_other_content_to_30tb') is not True:raise b.ArchiveError('CONTROL_SLOT_APPROVAL')
 owner=t.OwnerDrive();root=owner.meta(c['root_id'])
 if root.get('parents')!=[b.ARCHIVE_ROOT] or root.get('driveId') or root.get('mimeType')!=b.FOLDER or root.get('trashed') is not False:raise b.ArchiveError('CONTROL_SLOT_ROOT')
 parent=owner.meta(j['parent_id']);owner.relative_parent(j['parent_id'],c['root_id'])
 if parent.get('driveId') or parent.get('mimeType')!=b.FOLDER or parent.get('capabilities',{}).get('canAddChildren') is not True or not any(x.get('emailAddress')==b.ACCOUNT and x.get('permissionId')==b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT] for x in parent.get('owners',[])) or any(x.get('type') in ['anyone','domain'] for x in parent.get('permissions',[])):raise b.ArchiveError('CONTROL_SLOT_PARENT')
 HOME.mkdir(parents=True,exist_ok=True)
 with (HOME/'slots.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);journal=t.Journal(HOME/'slots-journal.json');identity='slot:'+j['parent_id']+':'+j['key'];found=owner.one(j['parent_id'],j['key']);fid=journal.known_id(identity)
  if found:
   if fid and found['id']!=fid:raise b.ArchiveError('CONTROL_SLOT_ID_CONFLICT')
   fid=found['id']
  if not fid:
   journal.allow_create(identity);journal.intent(identity,j)
   owner.parents.add(j['parent_id'])
   metadata={'name':j['name'],'mimeType':j['mime'],'parents':[j['parent_id']],'properties':{'mgsArchiveKey':j['key'],'mgsArchiveType':'private_control_slot','expectedSha256':j['sha256'],'expectedKind':j['kind']}}
   request=urllib.request.Request(owner.base+'files?fields=id',data=b.canonical(metadata),headers={'Authorization':'Bearer '+owner.token,'Content-Type':'application/json'},method='POST')
   try:
    with urllib.request.urlopen(request,timeout=60) as response:fid=json.load(response)['id']
   except Exception:
    found=owner.one(j['parent_id'],j['key'])
    if not found:raise b.ArchiveError('CONTROL_SLOT_CREATE_AMBIGUOUS_NO_REPLAY') from None
    fid=found['id']
   journal.landed(identity,fid)
  meta=owner.meta(fid)
  if meta.get('parents')!=[j['parent_id']] or meta.get('driveId') or meta.get('mimeType')!=j['mime'] or not any(x.get('emailAddress')==b.ACCOUNT for x in meta.get('owners',[])):raise b.ArchiveError('CONTROL_SLOT_READBACK')
  return {'schema':'mgs.private.control.slot.response.v1','file_id':fid,'parent_id':j['parent_id'],'key':j['key'],'sha256':j['sha256']}

def publication_properties(kind,digest):
 props={'mgsArchiveType':kind,'sha256':digest}
 if kind in {'request','vps_request','vps_backfill_request','vps_backup_move_request'}:props['mgsArchiveState']='queued'
 return props

def publish_sa(d,parent,name,data,mime,key,kind):
 c=b.read_json(CONFIG,{});j={'schema':'mgs.private.control.slot.request.v1','parent_id':parent,'key':key,'kind':kind,'mime':mime,'name':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()};validate_request(j,c)
 old=d.one(parent,key)
 if old:
  m=d.meta(old['id'])
  if m.get('properties',{}).get('mgsArchiveType')==kind:
   b.require_publisher(m,b.CANONICAL_SA)
   if m.get('parents')!=[parent] or m.get('driveId') or d.raw(old['id'])!=data:raise b.ArchiveError('CONTROL_SA_IMMUTABLE_CONFLICT')
   return old['id']
 # stdin is non-secret bound metadata only; the private child obtains its own grant.
 proc=subprocess.run([sys.executable,str(Path(__file__)),'slot','--apply'],input=json.dumps(j),text=True,capture_output=True,timeout=90)
 if proc.returncode:raise b.ArchiveError('CONTROL_SLOT_PRIVATE_CHILD_FAILED')
 try:response=json.loads(proc.stdout)
 except ValueError:raise b.ArchiveError('CONTROL_SLOT_PRIVATE_RESPONSE') from None
 if response.get('schema')!='mgs.private.control.slot.response.v1' or any(response.get(k)!=j[v] for k,v in [('parent_id','parent_id'),('key','key'),('sha256','sha256')]):raise b.ArchiveError('CONTROL_SLOT_RESPONSE_BINDING')
 fid=response['file_id'];before=d.meta(fid)
 if before.get('parents')!=[parent] or before.get('driveId') or before.get('properties',{}).get('expectedSha256')!=j['sha256'] or before['properties'].get('expectedKind')!=kind:raise b.ArchiveError('CONTROL_SLOT_SA_PREWRITE')
 request=urllib.request.Request('https://www.googleapis.com/upload/drive/v3/files/'+fid+'?uploadType=media&supportsAllDrives=true',data=data,headers={'Authorization':'Bearer '+d.token,'Content-Type':mime},method='PATCH')
 try:
  with urllib.request.urlopen(request,timeout=90) as r:json.load(r)
 except Exception:
  if d.raw(fid)!=data:raise b.ArchiveError('CONTROL_SA_PUBLICATION_UNKNOWN') from None
 d.api('PATCH','files/'+fid,{'supportsAllDrives':'true','fields':'id'},{'properties':publication_properties(kind,j['sha256'])})
 after=d.meta(fid);b.require_publisher(after,b.CANONICAL_SA)
 if any(after.get('properties',{}).get(k)!=v for k,v in publication_properties(kind,j['sha256']).items()):raise b.ArchiveError('CONTROL_SA_PUBLICATION_PROPERTIES_READBACK')
 if after.get('parents')!=[parent] or after.get('driveId') or after.get('properties',{}).get('sha256')!=j['sha256'] or after['properties'].get('mgsArchiveType')!=kind or d.raw(fid)!=data:raise b.ArchiveError('CONTROL_SA_PUBLICATION_READBACK')
 return fid

if __name__=='__main__':
 if sys.argv[1:]!=['slot','--apply']:raise SystemExit('PRIVATE_SLOT_APPLY_REQUIRED')
 try:print(json.dumps(owner_slot(json.load(sys.stdin))))
 except b.ArchiveError as e:print(json.dumps({'status':'blocked','reason':str(e)[:160]}));raise SystemExit(2)
