"""Read-only compatibility for exact source IDs retained by confirmed flat cutover."""
import hashlib
import ares_archive_bridge as b
HOME=b.DATA/'flat-intake-1566814476626563115'
class FlatSourceError(b.ArchiveError):pass

def require(ok,why):
 if not ok:raise FlatSourceError(why)
def sha(x):return hashlib.sha256(b.canonical(x)).hexdigest()

def local_state():
 state=b.read_json(HOME/'source-relocation-state.json',{})
 return state if state.get('status')=='verified' else None

def retained(fid):
 state=local_state()
 return bool(state and fid in state.get('media_ids',[]))

def evidence(d):
 state=local_state();require(state is not None,'FLAT_SOURCE_NOT_ACCEPTED')
 require(state.get('redesign_confirmation')=='1566814476626563115' and state.get('access_confirmation')=='1566825959645253764','FLAT_SOURCE_AUTHORITY')
 cache=getattr(d,'_flat_source_proof_cache',None)
 if cache and cache[0]==state['receipt_sha256']:return cache[1]
 for kind in ['snapshot','receipt']:
  fid=state[kind+'_file_id'];m=d.meta(fid);raw=d.raw(fid);b.require_publisher(m,b.CANONICAL_SA,'FLAT_SOURCE_PROOF_PUBLISHER')
  require(b.control_object_scope(m,state['control_folder_id']) and m.get('properties',{}).get('mgsArchiveType')=='stock_layout_snapshot' and hashlib.sha256(raw).hexdigest()==state[kind+'_sha256'],'FLAT_SOURCE_PROOF_NATIVE_SCOPE')
  import json
  value=json.loads(raw)
  if kind=='snapshot':snapshot=value
  else:receipt=value
 require(receipt.get('status')=='verified' and receipt.get('snapshot_sha256')==state['snapshot_sha256'] and receipt.get('access_confirmation')=='1566825959645253764','FLAT_SOURCE_RECEIPT_BINDING')
 result=(snapshot,receipt);d._flat_source_proof_cache=(state['receipt_sha256'],result);return result

def verify(d,meta,asset,job=None):
 if not retained(asset.get('sourceId')):return False
 snapshot,receipt=evidence(d);fid=asset['sourceId'];before=snapshot['objects'][fid]['metadata'];after=receipt['objects'][fid]['metadata_after']
 require(job is None or snapshot['jobs'].get(job['jobId'])==sha(job),'FLAT_SOURCE_JOB_BINDING')
 for native,key in [('id','sourceId'),('name','name'),('mimeType','mimeType'),('size','size'),('md5Checksum','md5'),('sha256Checksum','sha256'),('createdTime','sourceCreatedTime')]:
  require(str(before.get(native))==str(asset.get(key)) and meta.get(native)==before.get(native),'FLAT_SOURCE_FROZEN_BYTES:'+native)
 require(before.get('parents')==[asset['sourceParentId']] and meta.get('parents')==after.get('parents') and meta.get('trashed') is False and not meta.get('driveId') and any(x.get('emailAddress')==b.ACCOUNT for x in meta.get('owners',[])),'FLAT_SOURCE_NATIVE_IDENTITY')
 require(not any(x.get('type') in ['anyone','domain'] for x in meta.get('permissions',[])),'FLAT_SOURCE_PUBLIC')
 require(d.relative_parent(meta['parents'][0],snapshot['processing_destination_id'])==asset['relativeParent'],'FLAT_SOURCE_NATIVE_ANCESTRY')
 require(str(meta.get('version','')).isdigit() and int(meta['version'])>=int(before['version']),'FLAT_SOURCE_VERSION')
 return True
