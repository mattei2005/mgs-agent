"""Read-only compatibility for exact source IDs retained by confirmed flat cutover."""
import hashlib,json
import ares_archive_bridge as b
HOME=b.DATA/'flat-intake-1566814476626563115'
class FlatSourceError(b.ArchiveError):pass

def require(ok,why):
 if not ok:raise FlatSourceError(why)
def sha(x):return hashlib.sha256(b.canonical(x)).hexdigest()

def all_states():
 first=b.read_json(HOME/'source-relocation-state.json',{})
 extra=b.read_json(HOME/'maintenance-relocations.json',{}).get('records',[])
 return [x for x in [first]+extra if x.get('status')=='verified']

def local_state(fid=None):
 states=all_states()
 if fid is None:return states[0] if states else None
 found=[x for x in states if fid in x.get('media_ids',[])];require(len(found)<=1,'DUPLICATE_FLAT_RELOCATION_MEMBERSHIP')
 return found[0] if found else None

def retained(fid):return local_state(fid) is not None

def evidence(d,source_id):
 state=local_state(source_id);require(state is not None,'FLAT_SOURCE_NOT_ACCEPTED')
 require(state.get('redesign_confirmation')=='1566814476626563115' and state.get('access_confirmation')=='1566825959645253764','FLAT_SOURCE_AUTHORITY')
 cache=getattr(d,'_flat_source_proof_cache',{})
 if state['receipt_sha256'] in cache:return cache[state['receipt_sha256']]
 values={}
 for kind in ['snapshot','receipt']:
  fid=state[kind+'_file_id'];m=d.meta(fid);raw=d.raw(fid);b.require_publisher(m,b.CANONICAL_SA,'FLAT_SOURCE_PROOF_PUBLISHER')
  require(b.control_object_scope(m,state['control_folder_id']) and m.get('properties',{}).get('mgsArchiveType')=='stock_layout_snapshot' and hashlib.sha256(raw).hexdigest()==state[kind+'_sha256'],'FLAT_SOURCE_PROOF_NATIVE_SCOPE')
  values[kind]=json.loads(raw)
 snapshot=values['snapshot'];receipt=values['receipt']
 require(receipt.get('status')=='verified' and receipt.get('snapshot_sha256')==state['snapshot_sha256'] and receipt.get('access_confirmation')=='1566825959645253764','FLAT_SOURCE_RECEIPT_BINDING')
 result=(snapshot,receipt);cache[state['receipt_sha256']]=result;d._flat_source_proof_cache=cache;return result

PENDING_UPLOAD='1ARBvLammWUHuAclNmcriwkkgeedKryBd'
PENDING_BINDING=HOME/'pending-source-binding.json'

def verify_pending(d,meta,asset,job):
 """Accept only frozen, SA-proven pending inputs flattened without treatment.

 This is read-only reconciliation, never destructive retirement authority.
 """
 state=b.read_json(PENDING_BINDING,{})
 if state.get('status')!='verified' or asset.get('sourceId') not in state.get('source_ids',[]):return False
 require(state.get('schema')=='mgs.flat.pending.sources.binding.v1','FLAT_PENDING_BINDING')
 fid=state['proof_file_id'];native=d.meta(fid);raw=d.raw(fid)
 b.require_publisher(native,b.CANONICAL_SA,'FLAT_PENDING_PROOF_PUBLISHER')
 require(b.control_object_scope(native,state['control_folder_id']) and hashlib.sha256(raw).hexdigest()==state['proof_sha256'],'FLAT_PENDING_PROOF_SCOPE')
 proof=json.loads(raw)
 require(proof.get('schema')=='mgs.flat.pending.sources.proof.v1' and proof.get('redesign_confirmation')=='1566814476626563115' and proof.get('access_confirmation')=='1566825959645253764' and proof.get('delete_writes')==0,'FLAT_PENDING_AUTHORITY')
 require(set(proof.get('sources',{}))==set(state['source_ids']),'FLAT_PENDING_MEMBERSHIP')
 rec=proof['sources'][asset['sourceId']]
 require(job is not None and rec.get('job_id')==job.get('jobId') and rec.get('job_sha256')==sha(job) and rec.get('asset_sha256')==sha(asset) and rec.get('full_source_archive_streams_verified') is True,'FLAT_PENDING_FROZEN_JOB')
 after=rec['metadata_after']
 for native,key in [('id','sourceId'),('name','name'),('mimeType','mimeType'),('size','size'),('md5Checksum','md5'),('sha256Checksum','sha256'),('createdTime','sourceCreatedTime')]:
  require(meta.get(native)==after.get(native)==asset.get(key),'FLAT_PENDING_FROZEN_BYTES:'+native)
 require(meta.get('parents')==after.get('parents')==[PENDING_UPLOAD] and meta.get('driveId')==after.get('driveId')==b.SOURCE_DRIVE and meta.get('trashed') is False,'FLAT_PENDING_NATIVE_IDENTITY')
 require(not any(x.get('type') in ['anyone','domain'] for x in meta.get('permissions',[])),'FLAT_PENDING_PUBLIC')
 require(str(meta.get('version','')).isdigit() and str(after.get('version','')).isdigit() and int(meta['version'])>=int(after['version'])>=int(asset['version']),'FLAT_PENDING_VERSION')
 root=d.meta(PENDING_UPLOAD)
 require(root.get('id')==PENDING_UPLOAD and root.get('driveId')==b.SOURCE_DRIVE and root.get('mimeType')==b.FOLDER and root.get('trashed') is False,'FLAT_PENDING_INTAKE_ROOT')
 return True

def verify(d,meta,asset,job=None):
 if verify_pending(d,meta,asset,job):return True
 if not retained(asset.get('sourceId')):return False
 snapshot,receipt=evidence(d,asset['sourceId']);fid=asset['sourceId'];before=snapshot['objects'][fid]['metadata'];after=receipt['objects'][fid]['metadata_after']
 require(job is None or snapshot['jobs'].get(job['jobId'])==sha(job),'FLAT_SOURCE_JOB_BINDING')
 for native,key in [('id','sourceId'),('name','name'),('mimeType','mimeType'),('size','size'),('md5Checksum','md5'),('sha256Checksum','sha256'),('createdTime','sourceCreatedTime')]:
  require(str(before.get(native))==str(asset.get(key)) and meta.get(native)==before.get(native),'FLAT_SOURCE_FROZEN_BYTES:'+native)
 require(before.get('parents')==[asset['sourceParentId']] and meta.get('parents')==after.get('parents') and meta.get('trashed') is False and not meta.get('driveId') and any(x.get('emailAddress')==b.ACCOUNT for x in meta.get('owners',[])),'FLAT_SOURCE_NATIVE_IDENTITY')
 require(not any(x.get('type') in ['anyone','domain'] for x in meta.get('permissions',[])),'FLAT_SOURCE_PUBLIC')
 require(d.relative_parent(meta['parents'][0],snapshot['processing_destination_id'])==asset['relativeParent'],'FLAT_SOURCE_NATIVE_ANCESTRY')
 require(str(meta.get('version','')).isdigit() and int(meta['version'])>=int(before['version']),'FLAT_SOURCE_VERSION')
 return True
