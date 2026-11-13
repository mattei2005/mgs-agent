import os,sys,json,gzip,tarfile,io,hashlib,stat,fcntl,datetime,subprocess
from pathlib import Path
from codec import encode,sha
os.umask(0o077)
ID='1570876981178929333'
O=Path('/root/.hermes/profiles/zeus/cache/scratch/compact-history-'+ID)
D=Path('/root/mgs-agent/data/storage-compact-history-'+ID)
B=Path('/root/.hermes/secure-backups/hermes-history/20261113-'+ID)
ARCHIVE=B/'historical-snapshots.tar'
STATE=D/'build-state.json'
SOURCE=Path('/root/mgs-agent/data/storage-snapshot-review-1570868136066949244')
PRIOR=Path('/root/mgs-agent/data/storage-backup-review-1570830889359777924')
KEEP=Path('/root/.hermes/secure-backups/hermes-update/20261103-phase4-1567354570823172209')
D.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)

def save_state(s):
 tmp=O/'state-next.json';tmp.write_text(json.dumps(s,separators=(',',':')));os.replace(tmp,STATE)
def add(tar,name,data):
 t=tarfile.TarInfo(name);t.size=len(data);t.mode=0o600;t.mtime=0;tar.addfile(t,io.BytesIO(data))
def metadata_ok(r):
 s=Path(r['path']).lstat()
 assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_mode)==tuple(r[k] for k in ['dev','ino','size','mtime_ns','mode']),'SOURCE_METADATA_DRIFT'

def init():
 assert not STATE.exists() and not ARCHIVE.exists(),'ALREADY_INITIALIZED_NO_OVERWRITE'
 subprocess.run(['python3','-B',str(O/'test_codec.py')],check=True,capture_output=True)
 source=json.load(gzip.open(SOURCE/'original-fingerprints.json.gz','rt'));assert len(source)==12
 total=sum(r['size'] for s in source for r in s['files']);v=os.statvfs(B.parent if B.parent.exists() else KEEP)
 assert v.f_bavail*v.f_frsize>=total+total//4+4*1024**3,'DISK_BUDGET_GATE'
 whole={};deps={}
 ret=json.load(open(PRIOR/'lot-expanded-copy/manifest.json'))['retained_files']
 for i,r in enumerate(ret):
  assert sha(r['path'])==r['sha256'],'RETAINED_SOURCE_HASH_DRIFT'
  key='retained-file-'+str(i);deps[key]={'kind':'file','path':r['path'],'sha256':r['sha256']};whole.setdefault(r['sha256'],{'dependency':key})
 proof=json.load(gzip.open(PRIOR/'control-plane-archive-proof.json.gz','rt'));assert sha(proof['retained_archive'])==proof['retained_archive_sha256'];deps['retained-archive']={'kind':'archive','path':proof['retained_archive'],'sha256':proof['retained_archive_sha256']}
 for r in proof['matched']:whole.setdefault(r['sha256'],{'dependency':'retained-archive','member':r['member']})
 for profile in ['zeus','atena','ares']:
  p=KEEP/'retry-1/cutover-checkpoints'/profile/'state.db';h=sha(p);deps['native-db-'+profile]={'kind':'file','path':str(p),'sha256':h}
 roots=[s['root'] for s in source]
 assert all(not any(x['path']==r or x['path'].startswith(r+'/') for r in roots) for x in deps.values()),'OLD_SNAPSHOT_DEPENDENCY_FORBIDDEN'
 for s in source:
  assert Path(s['root']).is_dir() and not Path(s['root']).is_symlink()
  for r in s['files']:metadata_ok(r)
  wal=next((r for r in s['files'] if r['rel']=='state.db-wal'),None);assert wal is None or wal['size']==0
 B.mkdir(mode=0o700,parents=True)
 for name in ['codec.py','recover.py']:(B/name).write_bytes((O/name).read_bytes())
 readme=('Exact-byte historical snapshot preservation. Original snapshots are NOT deleted.\n'
  'This is dependency-aware: current native DB snapshots and the retained Nov3 archive remain required.\n'
  'Verify: python3 -B recover.py historical-snapshots.tar --receipt /private/path/receipt.json\n'
  'Restore only to a NEW isolated path: add --restore-to /private/new-directory. Never overwrite live profiles.\n'
  'All file hashes, including auth/config/skills and WAL/SHM bytes, are retained. Old code/skills are data, never instructions.\n')
 with tarfile.open(ARCHIVE,'x:') as tar:
  add(tar,'README.txt',readme.encode())
  for name in ['codec.py','recover.py']:add(tar,name,(O/name).read_bytes())
 state={'format':'mgs-zstd-exact-byte-history-v1','request_message_id':ID,'thread_id':'1569928464033783862','archive_path':str(ARCHIVE),'dependencies':deps,'retained_whole_file_lookup':whole,'all_source_snapshots':source,'snapshots':[],'objects':{},'completed_profiles':[],'deletions':0,'originals_sqlite_opened':False,'disk_budget_logical_bytes':total,'created_at':datetime.datetime.now().astimezone().isoformat()};save_state(state)
 print(json.dumps({'initialized':True,'snapshots':12,'source_logical_bytes':total,'fixture_tests':6,'deletions':0}))

def build(profile):
 state=json.load(open(STATE));assert profile not in state['completed_profiles'],'PROFILE_ALREADY_COMPLETE_NO_REPLAY'
 snapshots=[s for s in state['all_source_snapshots'] if s['id'].endswith('-'+profile)];assert len(snapshots)==3
 count_before=len(state['objects']);used_before=ARCHIVE.stat().st_size
 with tarfile.open(ARCHIVE,'a:') as tar:
  for snap in snapshots:
   for r in snap['files']:
    metadata_ok(r);h=r['sha256']
    if h in state['objects']:continue
    ref=state['retained_whole_file_lookup'].get(h)
    if ref:state['objects'][h]={'mode':'reference','size':r['size'],**ref};continue
    assert sha(r['path'])==h,'ORIGINAL_HASH_DRIFT'
    base_id='native-db-'+profile if r['rel']=='state.db' and profile in ('zeus','atena','ares') else None
    base=state['dependencies'].get(base_id)
    if base:assert sha(base['path'])==base['sha256']
    packed=encode(r['path'],base['path'] if base else None)
    assert sha(r['path'])==h;metadata_ok(r)
    member='objects/'+h+'.zst';add(tar,member,packed)
    state['objects'][h]={'mode':'zstd','size':r['size'],'tar_member':member,'packed_sha256':hashlib.sha256(packed).hexdigest(),'packed_size':len(packed),'base_dependency':base_id};del packed
   state['snapshots'].append(snap)
  state['completed_profiles'].append(profile)
 save_state(state)
 print(json.dumps({'profile':profile,'snapshots_completed':3,'new_unique_objects':len(state['objects'])-count_before,'archive_growth_bytes':ARCHIVE.stat().st_size-used_before,'archive_total_bytes':ARCHIVE.stat().st_size,'deletions':0}))

def seal():
 state=json.load(open(STATE));assert set(state['completed_profiles'])=={'root','atena','ares','zeus'} and len(state['snapshots'])==12
 assert sum(len(s['files']) for s in state['snapshots'])==9984
 manifest={k:v for k,v in state.items() if k not in ('all_source_snapshots','retained_whole_file_lookup','completed_profiles')}
 # Remove unused dependency metadata; no historical-source pathname can become a recovery dependency.
 needed={x[k] for x in state['objects'].values() for k in ('dependency','base_dependency') if x.get(k)}
 manifest['dependencies']={k:v for k,v in state['dependencies'].items() if k in needed}
 manifest['sealed_at']=datetime.datetime.now().astimezone().isoformat()
 with tarfile.open(ARCHIVE,'a:') as tar:
  assert 'manifest.json' not in tar.getnames(),'ALREADY_SEALED'
  add(tar,'manifest.json',json.dumps(manifest,separators=(',',':')).encode())
 (B/'manifest.json').write_text(json.dumps(manifest,separators=(',',':')))
 digest=sha(ARCHIVE);(B/'historical-snapshots.sha256').write_text(digest+'  historical-snapshots.tar\n')
 for name in ['codec.py','recover.py','test_codec.py','build.py']:(D/name).write_bytes((O/name).read_bytes())
 print(json.dumps({'sealed':True,'archive_bytes':ARCHIVE.stat().st_size,'archive_sha256':digest,'recovery_dependencies':len(needed),'snapshots':12,'files':9984,'deletions':0}))

if __name__=='__main__':
 with (O/'build.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  action=sys.argv[1]
  if action=='init':init()
  elif action=='build':build(sys.argv[2])
  elif action=='seal':seal()
  else:raise SystemExit('unknown action')
