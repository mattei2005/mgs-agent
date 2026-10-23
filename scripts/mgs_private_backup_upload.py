#!/usr/bin/env python3
"""Private owner reserves empty encrypted-backup slots; uploader stays SA.
Separate canary/production binding. No public API, delete or credential fallback.
"""
import sys,json,re,hashlib,fcntl,urllib.request,urllib.parse,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
HOME=b.DATA/'owner-connector/backup-direct-upload'
BINDING=HOME/'binding.json'
APPROVAL='1562972150455992431'

def contract(canary=False):
 v=b.read_json(BINDING,{})
 if not v:return None
 if v.get('schema')!='mgs.backup.direct.upload.binding.v1' or v.get('approval_message_id')!=APPROVAL:raise b.ArchiveError('BACKUP_DIRECT_BINDING_INVALID_NO_FALLBACK')
 if canary and v.get('canary_enabled') is True:return v
 if not canary and v.get('production_enabled') is True:return v
 return None

def validate_slot(j,p,c):
 if j.get('schema')!='mgs.backup.direct.slot.v1' or c.get('approval_message_id')!=APPROVAL or c.get('archive_root_id')!=p['archiveRootId'] or c.get('owner')!=b.ACCOUNT or j.get('tier') not in p['tiers'] or j.get('parent_id')!=p['tiers'][j['tier']]['archiveId']:raise b.ArchiveError('BACKUP_DIRECT_SLOT_SCOPE')
 if j.get('mode')!=('quick' if j['tier']=='hourly' else 'full') or not re.fullmatch('mgs-dr-'+j['tier']+'-[0-9]{8}T[0-9]{6}Z\\.zip\\.gpg',j.get('name','')) or not re.fullmatch('[a-f0-9]{64}',j.get('sha256','')) or not re.fullmatch('[a-f0-9]{32}',j.get('md5','')) or type(j.get('size')) is not int or j['size']<=0:raise b.ArchiveError('BACKUP_DIRECT_SLOT_BYTES')
 return True

def destination(drive,tier,canary=False):
 c=contract(canary)
 if not c:return None
 import mgs_backup_automation as a
 p=b.read_json(a.PLAN);parent=p['tiers'][tier]['archiveId'];fields='id,name,mimeType,parents,driveId,trashed,owners(emailAddress,permissionId),capabilities(canAddChildren)'
 def meta(fid):return drive.request('https://www.googleapis.com/drive/v3/files/'+fid+'?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':fields}))
 root=meta(p['archiveRootId']);folder=meta(parent)
 for m in [root,folder]:
  if m.get('driveId') or m.get('mimeType')!=b.FOLDER or m.get('trashed') is not False or m.get('capabilities',{}).get('canAddChildren') is not True or not any(z.get('emailAddress')==b.ACCOUNT and z.get('permissionId')==p['ownerPermissionId'] for z in m.get('owners',[])):raise b.ArchiveError('BACKUP_DIRECT_NATIVE_ROOT')
 if folder.get('parents')!=[p['archiveRootId']] or root.get('parents')!=[p['corporateRootId']]:raise b.ArchiveError('BACKUP_DIRECT_NATIVE_ANCESTRY')
 return {'root':root,'parent_id':parent,'binding':c,'plan':p}

def reserve_slot(parent,path,tier,mode,sha256,md5,canary=False):
 c=contract(canary)
 if not c:raise b.ArchiveError('BACKUP_DIRECT_NOT_ENABLED')
 j={'schema':'mgs.backup.direct.slot.v1','parent_id':parent,'name':path.name,'size':path.stat().st_size,'tier':tier,'mode':mode,'sha256':sha256,'md5':md5,'canary':canary}
 proc=subprocess.run([sys.executable,str(Path(__file__)),'reserve','--apply'],input=json.dumps(j),capture_output=True,text=True,timeout=90)
 if proc.returncode:raise b.ArchiveError('BACKUP_DIRECT_PRIVATE_SLOT_FAILED')
 r=json.loads(proc.stdout)
 if r.get('schema')!='mgs.backup.direct.slot.response.v1' or r.get('request_sha256')!=hashlib.sha256(b.canonical(j)).hexdigest():raise b.ArchiveError('BACKUP_DIRECT_SLOT_RESPONSE')
 return r['file_id']

def publish_ack(result):
 import mgs_private_control_store as store
 import mgs_backup_automation as a
 p=b.read_json(a.PLAN);binding=b.read_json(store.CONFIG);sa=b.Drive(True);fid=result['remote_file_id'];meta=sa.meta(fid);b.require_publisher(meta,b.CANONICAL_SA)
 if result.get('status')!='PASS' or result.get('storage_backend')!='private_owner_slot_sa_upload' or meta.get('driveId') or meta.get('parents')!=[p['tiers'][result['tier']]['archiveId']] or meta.get('md5Checksum')!=result['encrypted_md5'] or meta.get('sha256Checksum')!=result['encrypted_sha256'] or str(meta.get('size'))!=str(result['remote_size_bytes']) or not any(z.get('emailAddress')==b.ACCOUNT for z in meta.get('owners',[])):raise b.ArchiveError('BACKUP_DIRECT_ACK_NATIVE_BINDING')
 body={'schema':'mgs.backup.direct.archive.ack.v1','status':'verified','file_id':fid,'parent_id':meta['parents'][0],'archive_root_id':p['archiveRootId'],'size':str(result['remote_size_bytes']),'md5':result['encrypted_md5'],'sha256':result['encrypted_sha256'],'tier':result['tier'],'canonical_sa_upload':True,'independent_sa_stream_verified':True,'archive_trash_enabled':False};data=b.canonical(body);ack=store.publish_sa(sa,binding['root_id'],'direct-backup-ack-'+fid+'.json',data,'application/json','direct-backup-ack:'+fid,'backup_direct_ack');return {'file_id':ack,'sha256':hashlib.sha256(data).hexdigest()}

def owner_reserve(j):
 import mgs_backup_automation as a
 import mgs_archive_owner_transport as t
 c=contract(j.get('canary') is True);p=b.read_json(a.PLAN)
 if not c:raise b.ArchiveError('BACKUP_DIRECT_OWNER_NOT_ENABLED')
 validate_slot(j,p,c);o=t.OwnerDrive();parent=o.meta(j['parent_id'])
 if parent.get('parents')!=[p['archiveRootId']] or parent.get('driveId') or parent.get('mimeType')!=b.FOLDER or not any(z.get('emailAddress')==b.ACCOUNT and z.get('permissionId')==p['ownerPermissionId'] for z in parent.get('owners',[])):raise b.ArchiveError('BACKUP_DIRECT_OWNER_PARENT')
 HOME.mkdir(parents=True,exist_ok=True)
 with (HOME/'slots.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);journal=t.Journal(HOME/'slots-journal.json');key='direct-backup:'+hashlib.sha256(b.canonical(j)).hexdigest();found=o.one(j['parent_id'],key);fid=journal.known_id(key)
  if found:
   if fid and found['id']!=fid:raise b.ArchiveError('BACKUP_DIRECT_SLOT_ID_CONFLICT')
   fid=found['id']
  if not fid:
   journal.allow_create(key);journal.intent(key,j);metadata={'name':j['name'],'mimeType':'application/pgp-encrypted','parents':[j['parent_id']],'properties':{'mgsArchiveKey':key,'mgsArchiveType':'encrypted_backup_slot','expectedSha256':j['sha256'],'expectedMd5':j['md5'],'expectedSize':str(j['size'])}};request=urllib.request.Request(o.base+'files?fields=id',data=b.canonical(metadata),headers={'Authorization':'Bearer '+o.token,'Content-Type':'application/json'},method='POST')
   try:
    with urllib.request.urlopen(request,timeout=60) as response:fid=json.load(response)['id']
   except Exception:
    found=o.one(j['parent_id'],key)
    if not found:raise b.ArchiveError('BACKUP_DIRECT_SLOT_UNKNOWN_NO_REPLAY') from None
    fid=found['id']
   journal.landed(key,fid)
  m=o.meta(fid)
  if m.get('parents')!=[j['parent_id']] or m.get('driveId') or m.get('mimeType')!='application/pgp-encrypted' or m.get('properties',{}).get('expectedSha256')!=j['sha256'] or not any(z.get('emailAddress')==b.ACCOUNT for z in m.get('owners',[])):raise b.ArchiveError('BACKUP_DIRECT_SLOT_NATIVE_READBACK')
  return {'schema':'mgs.backup.direct.slot.response.v1','file_id':fid,'request_sha256':hashlib.sha256(b.canonical(j)).hexdigest()}

if __name__=='__main__':
 if sys.argv[1:]!=['reserve','--apply']:raise SystemExit('DIRECT_PRIVATE_SLOT_APPLY_REQUIRED')
 try:print(json.dumps(owner_reserve(json.load(sys.stdin))))
 except b.ArchiveError as e:print(json.dumps({'status':'blocked','reason':str(e)[:160]}));raise SystemExit(2)
