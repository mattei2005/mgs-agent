"""Exact approved source-folder labels; never relax bytes, IDs or membership.

Called only after mgs_flat_source_compat verified the immutable source snapshot.
"""
import hashlib
import ares_archive_bridge as b
AUTHORITY='1567427715030716417'
HOME=b.DATA/('source-ancestry-name-'+AUTHORITY)
PROOF_SHA256='f8ad6a2ef6d8914579d5c6969b8454126b8f25f921d487211fd54ffafc82ab96'
def sha(value):return hashlib.sha256(b.canonical(value)).hexdigest()
def require(ok,reason):
 if not ok:raise b.ArchiveError(reason)
def load():
 binding=b.read_json(HOME/'binding.json',{})
 if not binding:return None,None
 require(binding.get('schema')=='mgs.archive.source.ancestry.name.binding.v1' and binding.get('authority_message_id')==AUTHORITY and binding.get('phase')=='active' and binding.get('proof_sha256')==PROOF_SHA256,'SOURCE_NAMES_BINDING')
 proof=b.read_json(HOME/'native-proof.json',{})
 require(sha(proof)==PROOF_SHA256 and proof.get('schema')=='mgs.archive.source.ancestry.name.proof.v1' and proof.get('authority_message_id')==AUTHORITY and proof.get('native_verified') is True and proof.get('author_discord_id')=='344196393512075265','SOURCE_NAMES_LOCAL_PROOF')
 return proof,binding

def verify(d,meta,asset,job,snapshot):
 proof,binding=load()
 if proof is None:return False
 if binding is None:raise b.ArchiveError('SOURCE_NAMES_BINDING_MISSING')
 rec=proof.get('records',{}).get(asset.get('sourceId'))
 if rec is None:return False
 require(job is not None and meta.get('id')==asset.get('sourceId')==rec.get('source_id') and meta.get('parents')==[rec.get('source_parent')],'SOURCE_NAMES_SOURCE_IDENTITY')
 require(job.get('jobId')==rec.get('job_id') and sha(job)==rec.get('job_sha256') and sha(asset)==rec.get('asset_sha256'),'SOURCE_NAMES_FROZEN_JOB')
 require(rec.get('root_id')==snapshot.get('processing_destination_id') and rec.get('expected_path')==asset.get('relativeParent') and rec.get('full_source_archive_streams_verified') is True and rec.get('hashes')=={k:asset[k] for k in ('size','md5','sha256')},'SOURCE_NAMES_EXACT_PATH_AND_BYTES')
 native=d.meta(binding['proof_file_id']);b.require_publisher(native,b.CANONICAL_SA,'SOURCE_NAMES_NATIVE_PUBLISHER')
 require(b.control_object_scope(native,binding['control_folder_id']) and native.get('properties',{}).get('mgsArchiveType')=='lineage_map' and d.raw(binding['proof_file_id'])==b.canonical(proof),'SOURCE_NAMES_NATIVE_PROOF')
 chain=rec.get('chain',[]);require(len(chain)==len(asset['relativeParent'])==3,'SOURCE_NAMES_CHAIN_BOUND')
 parent=meta['parents'][0];names=[];seen=set()
 for expected in chain:
  require(parent==expected.get('id') and parent not in seen,'SOURCE_NAMES_CHAIN_ID');seen.add(parent);current=d.meta(parent)
  require(all(current.get(k)==expected.get(k) for k in ('id','name','parents')) and current.get('mimeType')==b.FOLDER and current.get('trashed') is False and not current.get('driveId') and len(current.get('parents',[]))==1 and any(o.get('emailAddress')==b.ACCOUNT for o in current.get('owners',[])) and not any(p.get('type') in ('anyone','domain') for p in current.get('permissions',[])),'SOURCE_NAMES_NATIVE_CHAIN')
  names.append(current['name']);parent=current['parents'][0]
 require(parent==rec['root_id'] and list(reversed(names))==rec['current_path'],'SOURCE_NAMES_ROOT_OR_LABELS')
 return True
