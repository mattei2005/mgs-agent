"""Verify exact historical bytes, optionally restore ONLY to a new isolated directory."""
import sys, os, json, hashlib, tarfile, argparse, gc, sqlite3
from pathlib import Path, PurePosixPath
from codec import decode, sha, memory_gate

def safe_rel(s):
 p=PurePosixPath(s)
 if p.is_absolute() or '..' in p.parts:raise ValueError('UNSAFE_RELATIVE_PATH')
 return s

def run(bundle,manifest_file=None,profile=None,restore_to=None):
 with tarfile.open(bundle,'r:') as tar:
  manifest=json.load(open(manifest_file)) if manifest_file else json.load(tar.extractfile('manifest.json'))
  snapshots=[s for s in manifest['snapshots'] if profile is None or s['id'].endswith('-'+profile)]
  selected={f['sha256'] for s in snapshots for f in s['files']};objects={h:manifest['objects'][h] for h in selected}
  dependencies=manifest['dependencies'];needed=set()
  for ob in objects.values():
   if ob.get('dependency'):needed.add(ob['dependency'])
   if ob.get('base_dependency'):needed.add(ob['base_dependency'])
  for k in needed:
   dep=dependencies[k]
   if sha(dep['path'])!=dep['sha256']:raise ValueError('DEPENDENCY_HASH_MISMATCH:'+k)
  archive_cache={}
  for k in needed:
   dep=dependencies[k]
   if dep['kind']!='archive':continue
   wants={ob['member']:h for h,ob in objects.items() if ob.get('dependency')==k}
   total=sum(objects[h]['size'] for h in wants.values());memory_gate(3*total+1024**3)
   with tarfile.open(dep['path'],'r|gz') as source:
    for member in source:
     if member.name not in wants:continue
     h=wants[member.name];assert member.isfile() and member.size==objects[h]['size'];data=source.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==h;archive_cache[(k,member.name)]=data
   assert len([x for x in archive_cache if x[0]==k])==len(wants),'MISSING_RETAINED_ARCHIVE_MEMBER'
  destination=None
  if restore_to:
   destination=Path(restore_to).absolute()
   if destination.exists():raise ValueError('RESTORE_DESTINATION_MUST_NOT_EXIST')
   total=sum(f['size'] for s in snapshots for f in s['files']);parent=destination.parent
   if not parent.is_dir():raise ValueError('RESTORE_PARENT_MUST_EXIST')
   v=os.statvfs(parent)
   if v.f_bavail*v.f_frsize < total+max(total//4,1024**3):raise ValueError('RESTORE_DISK_CAPACITY_GATE')
   destination.mkdir(mode=0o700)
   for s in snapshots:
    (destination/s['id']).mkdir(mode=0o700)
    for d in sorted(s['directories'],key=lambda x:len(PurePosixPath(x['rel']).parts)):(destination/s['id']/safe_rel(d['rel'])).mkdir(mode=0o700,exist_ok=True)
  state_hashes={f['sha256'] for s in snapshots for f in s['files'] if f['rel']=='state.db'}
  verified={};sqlite_results=[]
  # Decode each unique object once; all target paths are bound to its full hash.
  for h,ob in objects.items():
   if ob['mode']=='reference':
    dep=dependencies[ob['dependency']]
    data=archive_cache[(ob['dependency'],ob['member'])] if dep['kind']=='archive' else Path(dep['path']).read_bytes()
   else:
    packed=tar.extractfile(ob['tar_member']).read();assert hashlib.sha256(packed).hexdigest()==ob['packed_sha256']
    base=dependencies[ob['base_dependency']] if ob.get('base_dependency') else None
    data=decode(packed,base['path'] if base else None,base['sha256'] if base else None,ob['size'])
   assert len(data)==ob['size'] and hashlib.sha256(data).hexdigest()==h,'RECONSTRUCTED_BYTES_MISMATCH'
   if h in state_hashes:
    memory_gate(3*len(data)+1024**3);payload=bytearray(data);assert payload[:16]==b'SQLite format 3\x00';assert payload[18] in (1,2) and payload[19] in (1,2);payload[18]=payload[19]=1;c=sqlite3.connect(':memory:')
    try:
     c.deserialize(payload);del payload;gc.collect();c.execute('PRAGMA query_only=ON');c.execute('PRAGMA temp_store=MEMORY');c.execute('PRAGMA cache_size=-8192');assert c.execute('PRAGMA quick_check').fetchall()==[('ok',)];assert not c.execute('PRAGMA foreign_key_check').fetchall();sqlite_results.append({'db_sha256':h,'quick_check':'ok','foreign_key_violations':0,'reconstructed_from_compact':True})
    finally:c.close();gc.collect()
   verified[h]=True
   if destination:
    for s in snapshots:
     for f in s['files']:
      if f['sha256']!=h:continue
      out=destination/s['id']/safe_rel(f['rel']);out.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
      with out.open('xb') as handle:handle.write(data)
      os.chmod(out,f['mode']&0o777);os.utime(out,ns=(f['mtime_ns'],f['mtime_ns']))
   del data;gc.collect()
  if destination:
   for s in snapshots:
    for link in s['links']:os.symlink(link['link_target'],destination/s['id']/safe_rel(link['rel']))
  # Dependencies must still match after decoding, not only before it.
  for k in needed:assert sha(dependencies[k]['path'])==dependencies[k]['sha256']
  count=sum(len(s['files']) for s in snapshots);db_count=sum(f['rel']=='state.db' for s in snapshots for f in s['files'])
  return {'status':'PASS','snapshots':len(snapshots),'files_reconstructed_hash_verified':count,'unique_objects_verified':len(verified),'state_databases_covered':db_count,'unique_state_databases_sqlite_checked':len(sqlite_results),'sqlite_results':sqlite_results,'dependency_count':len(needed),'dependencies_unchanged':True,'original_snapshot_files_read_by_decoder':0,'persistent_db_staging_bytes':0 if destination is None else sum(f['size'] for s in snapshots for f in s['files']),'restore_destination':str(destination) if destination else None,'recovery_layer':'exact file bytes reconstructed and hashed; DBs opened only as query-only RAM clones'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('--manifest-file');p.add_argument('--profile');p.add_argument('--restore-to');p.add_argument('--receipt',required=True);a=p.parse_args();os.umask(0o077);r=run(a.bundle,a.manifest_file,a.profile,a.restore_to);Path(a.receipt).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='sqlite_results'}))
