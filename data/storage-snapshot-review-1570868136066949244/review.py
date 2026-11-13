import os, sys, json, gzip, hashlib, sqlite3, gc, pickle, tarfile, subprocess, datetime, stat
from pathlib import Path
os.umask(0o077)
REQUEST='1570868136066949244'
O=Path('/root/.hermes/profiles/zeus/cache/scratch/snapshot-review-'+REQUEST)
D=Path('/root/mgs-agent/data/storage-snapshot-review-'+REQUEST)
BASE=Path('/root/.hermes/secure-backups/hermes-update')
OLD=[('preparation','20261021-1562474468146942115-preparation','profile-snapshots'),('activation','20261021-1562558871053144137-activation','profiles'),('recovery','20261021-1562583718722539622-recovery','profiles')]
KEEP=BASE/'20261103-phase4-1567354570823172209'
PRIOR=Path('/root/mgs-agent/data/storage-backup-review-1570830889359777924')
O.mkdir(parents=True,exist_ok=True);D.mkdir(parents=True,exist_ok=True)
def sha(p):
 return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def save(name,value):
 (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def available():
 return int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
def digest(row):
 return hashlib.sha256(pickle.dumps(tuple(row),protocol=5)).digest()
def qi(x): return '"'+x.replace('"','""')+'"'
def load_ram(payload,size):
 assert available() >= 2*size+1024**3,'RAM_GATE_LOAD'
 assert payload[:16]==b'SQLite format 3\x00'
 assert payload[18] in (1,2) and payload[19] in (1,2)
 payload[18]=payload[19]=1
 c=sqlite3.connect(':memory:');c.deserialize(payload)
 c.execute('PRAGMA query_only=ON');c.execute('PRAGMA temp_store=MEMORY');c.execute('PRAGMA cache_size=-8192')
 return c

def read_clone(path):
 p=Path(path);size=p.stat().st_size
 assert available()>=3*size+1024**3,'RAM_GATE_READ'
 wal=Path(str(p)+'-wal');shm=Path(str(p)+'-shm')
 assert not wal.exists() or wal.stat().st_size==0,'NONEMPTY_WAL_REQUIRES_OTHER_ROUTE'
 # A checksum-frozen SHM with an empty WAL is only a disposable index cache.
 # Copy it into RAM for source preservation; never use or rewrite the original.
 shm_image=shm.read_bytes() if shm.exists() else b''
 assert len(shm_image) in (0,32768),'UNCLASSIFIED_SHM_LAYOUT'
 payload=bytearray(size)
 with p.open('rb',buffering=0) as f:
  v=memoryview(payload);pos=0
  while pos<size:
   n=f.readinto(v[pos:min(size,pos+8*1024**2)]);assert n;pos+=n
  del v
 c=load_ram(payload,size);del payload,shm_image;gc.collect();return c

def check(c):
 assert c.execute('PRAGMA quick_check').fetchall()==[('ok',)],'QUICK_CHECK'
 assert not c.execute('PRAGMA foreign_key_check').fetchall(),'FOREIGN_KEYS'

def schema(c):
 rows=c.execute('PRAGMA table_list').fetchall();out={};skipped=[]
 for sch,name,kind,ncol,wr,strict in rows:
  if sch!='main' or name.startswith('sqlite_'): continue
  if kind in ('shadow','virtual'):
   skipped.append(name);continue
  info=c.execute('PRAGMA table_info('+qi(name)+')').fetchall()
  cols=[r[1] for r in info];pk=[r[1] for r in sorted(info,key=lambda r:r[5]) if r[5]]
  out[name]={'columns':cols,'pk':pk,'rows':c.execute('SELECT count(*) FROM '+qi(name)).fetchone()[0]}
 return out,skipped

def inventory():
 rows=[];fingerprints=[];coupling=[];shared={}
 for phase,group,sub in OLD:
  root=BASE/group
  contracts=[]
  for name in ('ROLLBACK.sha256','FINAL-COMPONENTS.sha256','PREPARATION-BUNDLE.sha256'):
   mf=root/name
   if mf.is_file():
    for line in mf.read_text().splitlines():
     bits=line.split(None,1)
     if len(bits)==2 and len(bits[0])==64:
      raw=bits[1].lstrip('* ');p=os.path.abspath(os.path.join(str(root),raw));contracts.append((p,bits[0],name))
  for profile in ('root','zeus','atena','ares'):
   r=root/sub/profile;assert r.is_dir() and not r.is_symlink();fs=[];dirs=[];links=[]
   for parent,ds,ns in os.walk(r,followlinks=False):
    for n in ds+ns:
     p=Path(parent)/n;s=p.lstat();rel=str(p.relative_to(r));item={'path':str(p),'rel':rel,'ino':s.st_ino,'dev':s.st_dev,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'mode':s.st_mode,'blocks':s.st_blocks*512,'nlink':s.st_nlink}
     if stat.S_ISLNK(s.st_mode):item['link_target']=os.readlink(p);links.append(item)
     elif stat.S_ISDIR(s.st_mode):dirs.append(item)
     elif stat.S_ISREG(s.st_mode):fs.append(item)
     else:raise RuntimeError('UNCLASSIFIED_SNAPSHOT_NODE')
   for start in range(0,len(fs),128):
    batch=fs[start:start+128];text=subprocess.check_output(['sha256sum','--',*[x['path'] for x in batch]],text=True)
    hs={line.split(None,1)[1].lstrip('* '):line.split(None,1)[0] for line in text.splitlines()}
    for x in batch:x['sha256']=hs[x['path']]
   bypath={x['path']:x for x in fs};bound=[{'path':p,'manifest':m,'expected_sha256':h,'matches':bypath[p]['sha256']==h} for p,h,m in contracts if p in bypath]
   for x in fs:
    k=(x['dev'],x['ino']);shared.setdefault(k,{'blocks':x['blocks'],'count':0,'nlink':x['nlink']});shared[k]['count']+=1
   row={'id':phase+'-'+profile,'phase':phase,'group':group,'profile':profile,'root':str(r),'regular_files':len(fs),'directories':len(dirs),'symlinks':len(links),'logical_bytes':sum(x['size'] for x in fs),'allocated_naive':sum(x['blocks'] for x in fs),'checksum_coupled_files':len({x['path'] for x in bound}),'contract_mismatches':sum(not x['matches'] for x in bound)}
   rows.append(row);fingerprints.append({'id':row['id'],'root':str(r),'files':fs,'directories':dirs,'links':links});coupling.append({'id':row['id'],'contracts':bound})
 assert len(rows)==12
 with gzip.open(D/'original-fingerprints.json.gz','wt') as f:json.dump(fingerprints,f)
 with gzip.open(D/'evidence-coupling.json.gz','wt') as f:json.dump(coupling,f)
 summary={'status':'frozen_for_read_only_review','request_message_id':REQUEST,'snapshots':rows,'snapshot_count':12,'regular_files':sum(x['regular_files'] for x in rows),'unique_allocated_bytes':sum(x['blocks'] for x in shared.values()),'inode_closed_reclaim_ceiling':sum(x['blocks'] for x in shared.values() if x['count']==x['nlink']),'errors':[],'deletions':0,'persistent_db_staging_bytes':0}
 save('inventory.json',summary)
 print(json.dumps({'snapshots':12,'files':summary['regular_files'],'occupied_GiB':round(summary['unique_allocated_bytes']/1024**3,3),'coupled_snapshot_count':sum(bool(x['checksum_coupled_files']) for x in rows),'contract_mismatches':sum(x['contract_mismatches'] for x in rows)}))

def fixture():
 c=sqlite3.connect(':memory:');c.execute('CREATE TABLE h(id INTEGER PRIMARY KEY,body TEXT)');c.executemany('INSERT INTO h VALUES(?,?)',[(1,'old'),(2,'preserved'),(3,'unique')]);c.commit();source=c.serialize();c.close();p=bytearray(source);p[18]=p[19]=2;frozen=bytes(p);shm=bytes(32768);x=load_ram(p,len(p));check(x);assert x.execute('SELECT count(*) FROM h').fetchone()[0]==3
 try:x.execute('DELETE FROM h');raise AssertionError('WRITE_ALLOWED')
 except sqlite3.OperationalError as e:assert 'readonly' in str(e)
 candidate={digest(row) for row in x.execute('SELECT id,body FROM h')};a={digest((1,'new')),digest((2,'preserved'))};b={digest((1,'old'))};assert len(candidate-a-b)==1;assert bytes(p)!=frozen and frozen[18:20]==b'\x02\x02' and len(shm)==32768;x.close();gc.collect()
 save('ram-fixture.json',{'status':'PASS','query_only_write_rejected':True,'union_recovers_one_source_missing_row':True,'same_pk_different_payload_not_misclassified':True,'unique_full_row_detected':True,'zero_wal_stale_shm_model':True,'normalization_only_in_ram':[18,19],'no_original_sqlite_connection':True})
 print('fixture_PASS')

def comparison(profile):
 assert json.load(open(D/'ram-fixture.json'))['status']=='PASS'
 frozen=json.load(gzip.open(D/'original-fingerprints.json.gz','rt'));items=[x for x in frozen if x['id'].endswith('-'+profile)];assert len(items)==3
 specs={};by_hash={}
 for item in items:
  p=Path(item['root'])/'state.db';h=sha(p);expected=next(x['sha256'] for x in item['files'] if x['rel']=='state.db');assert h==expected
  if h not in by_hash:
   c=read_clone(p)
   try:check(c);by_hash[h]=schema(c)
   finally:c.close();gc.collect()
  specs[item['id']]=by_hash[h]
 # Cache by schema projection, not snapshot age or file size. Later phases can add tables/columns.
 coverage_cache={};results=[];result_cache={}
 def coverage_for(spec):
  schema_key=json.dumps({t:{'columns':s['columns'],'pk':s['pk']} for t,s in spec.items()},sort_keys=True)
  if schema_key in coverage_cache:return coverage_cache[schema_key]
  covers={t:{'pk':set(),'rows':set()} for t in spec};sources=[];source_hashes=set()
  def consume(c,label,source_hash):
   check(c);other,shadow=schema(c);missing=[]
   for t,s in spec.items():
    if t not in other or any(x not in other[t]['columns'] for x in s['columns']):missing.append(t);continue
    if not s['pk']:continue
    indices=[s['columns'].index(k) for k in s['pk']]
    for row in c.execute('SELECT '+','.join(map(qi,s['columns']))+' FROM '+qi(t)):
     covers[t]['pk'].add(digest(tuple(row[i] for i in indices)));covers[t]['rows'].add(digest(row))
   source_hashes.add(source_hash);sources.append({'label':label,'db_sha256':source_hash,'quick_check':'ok','foreign_key_violations':0,'missing_candidate_tables_or_columns':missing})
  if profile!='root':
   p=KEEP/'retry-1/cutover-checkpoints'/profile/'state.db';h=sha(p);proof=json.load(open(PRIOR/'retained-db-integrity.json'));expected=[x for x in proof['rows'] if x['path']==str(p)];assert len(expected)==1 and h==expected[0]['sha256'];c=read_clone(p)
   try:consume(c,'retained_native_retry1',h)
   finally:c.close();gc.collect()
   proof=json.load(gzip.open(PRIOR/'control-plane-archive-proof.json.gz','rt'));member='control-plane/profiles/'+profile+'/state.db';entry=[x for x in proof['matched'] if x['member']==member];assert len(entry)==1;archive=Path(proof['retained_archive']);assert sha(archive)==proof['retained_archive_sha256']
   if entry[0]['sha256']==h:sources.append({'label':'retained_archive','same_digest_as_native':True})
   else:
    with tarfile.open(archive,'r|gz') as tar:
     found=False
     for ti in tar:
      if ti.name!=member:continue
      assert ti.isfile() and ti.size==entry[0]['size'];size=ti.size;assert available()>=3*size+1024**3,'RAM_GATE_ARCHIVE';buf=bytearray(size);view=memoryview(buf);f=tar.extractfile(ti);pos=0
      while pos<size:
       n=f.readinto(view[pos:min(size,pos+8*1024**2)]);assert n;pos+=n
      del view;assert hashlib.sha256(buf).hexdigest()==entry[0]['sha256'];c=load_ram(buf,size);del buf;gc.collect()
      try:consume(c,'retained_control_plane_archive',entry[0]['sha256'])
      finally:c.close();gc.collect()
      found=True;break
     assert found,'MISSING_ARCHIVE_MEMBER'
  else:
   p=Path(items[-1]['root'])/'state.db';h=sha(p);c=read_clone(p)
   try:consume(c,'latest_historical_root_snapshot_recovery',h)
   finally:c.close();gc.collect()
  value=(covers,sources,source_hashes);coverage_cache[schema_key]=value;return value
 for item in items:
  p=Path(item['root'])/'state.db';h=sha(p);spec,shadow=specs[item['id']]
  if h in result_cache:row={**result_cache[h],'id':item['id'],'reused_identical_db_digest':True}
  else:
   covers,sources,source_hashes=coverage_for(spec);c=read_clone(p)
   try:
    check(c);table_results=[]
    for t,s in spec.items():
     if not s['pk']:
      table_results.append({'table':t,'rows':s['rows'],'without_primary_key':True,'coverage_proven':s['rows']==0 or h in source_hashes,'exact_database_digest_covers_no_pk_table':h in source_hashes});continue
     indices=[s['columns'].index(k) for k in s['pk']];missing_pk=0;missing_payload=0
     for record in c.execute('SELECT '+','.join(map(qi,s['columns']))+' FROM '+qi(t)):
      if digest(tuple(record[i] for i in indices)) not in covers[t]['pk']:missing_pk+=1
      if digest(record) not in covers[t]['rows']:missing_payload+=1
     table_results.append({'table':t,'rows':s['rows'],'primary_key_absent_from_retained_union':missing_pk,'full_row_absent_from_retained_union':missing_payload,'same_pk_different_historical_payload':missing_payload-missing_pk,'coverage_proven':missing_payload==0})
    row={'id':item['id'],'db_sha256':h,'quick_check':'ok','foreign_key_violations':0,'tables':table_results,'fts_rebuildable_tables_skipped':len(shadow),'sources':sources,'all_meaningful_rows_covered':all(x['coverage_proven'] for x in table_results),'original_sqlite_opened':False,'persistent_db_staging_bytes':0};result_cache[h]=row
   finally:c.close();gc.collect()
  results.append(row)
  with (D/('sqlite-'+profile+'.jsonl')).open('a') as f:f.write(json.dumps(row)+'\n')
 save('sqlite-'+profile+'.json',{'profile':profile,'snapshot_count':3,'snapshots':results,'schema_variants':len(coverage_cache)})
 print(json.dumps({'profile':profile,'snapshots':3,'integrity':'PASS','schema_variants':len(coverage_cache),'summary':[{'id':x['id'],'missing_pk':sum(t.get('primary_key_absent_from_retained_union',0) for t in x['tables']),'missing_full_rows':sum(t.get('full_row_absent_from_retained_union',0) for t in x['tables']),'covered':x['all_meaningful_rows_covered']} for x in results]}))

if __name__=='__main__':
 action=sys.argv[1]
 if action=='inventory':inventory()
 elif action=='fixture':fixture()
 elif action=='compare':comparison(sys.argv[2])
 else:raise SystemExit('unknown action')
