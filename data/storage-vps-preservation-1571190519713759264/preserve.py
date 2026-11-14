import os,stat,json,gzip,pathlib,subprocess,hashlib,tarfile,datetime,shutil
os.umask(0o077)
ROOT=pathlib.Path('/root/.hermes/secure-backups/vps-maintenance')
OLD=pathlib.Path('/root/mgs-agent/data/storage-vps-legacy-review-1571144515673260184')
SECURE=pathlib.Path('/root/.hermes/secure-backups/maintenance-history/20261114-1571190519713759264')
OUT=pathlib.Path('/root/mgs-agent/data/storage-vps-preservation-1571190519713759264')
SECURE.mkdir(mode=0o700,parents=True,exist_ok=True);OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
assert not (SECURE/'maintenance-history.tar.xz').exists(),'Existing archive: reconcile before retry'
old=json.load(gzip.open(OLD/'metadata-and-hashes.json.gz','rt'))

def digest(p):return subprocess.run(['sha256sum',str(p)],capture_output=True,text=True,check=True).stdout.split()[0]
def hash_rows(rows):
 paths=[str(ROOT/r['relative_path']) for r in rows if stat.S_ISREG(r['mode'])]
 b=subprocess.run(['xargs','-0','sha256sum','--zero'],input=b'\0'.join(os.fsencode(p) for p in paths)+b'\0',capture_output=True,check=True).stdout
 return {os.fsdecode(z[66:]):z[:64].decode() for z in b.split(b'\0') if z}
def verify_old():
 hashes=hash_rows(old)
 for r in old:
  p=ROOT/r['relative_path'];s=os.lstat(p)
  assert (s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_dev,s.st_ino,s.st_nlink,s.st_blocks*512)==tuple(r[k] for k in ['mode','size','mtime_ns','ctime_ns','dev','ino','nlink','allocated']), 'Source metadata drift'
  if stat.S_ISREG(s.st_mode):assert hashes[str(p)]==r['sha256'],'Source payload drift'
  if stat.S_ISLNK(s.st_mode):assert os.readlink(p)==r['link_target'],'Source link drift'
verify_old()
manifest=[]
for r in old:
 p=ROOT/r['relative_path'];s=os.lstat(p);row=dict(r,uid=s.st_uid,gid=s.st_gid)
 row['xattrs']={k:os.getxattr(p,k,follow_symlinks=False).hex() for k in os.listxattr(p,follow_symlinks=False)}
 manifest.append(row)
(SECURE/'source-manifest.json').write_text(json.dumps({'root':str(ROOT),'files':manifest},ensure_ascii=False,indent=2)+'\n')
archive=SECURE/'maintenance-history.tar.xz'
# GNU pax metadata, ACLs, all xattrs; no dereference, no overwrite, no source mutation.
cmd=['tar','--create','--file',str(archive),'--use-compress-program=xz -T2 -6','--format=pax','--acls','--xattrs','--xattrs-include=*','--numeric-owner','--sparse','--directory',str(ROOT.parent),ROOT.name]
p=subprocess.run(cmd,capture_output=True,text=True)
(OUT/'archive-create.json').write_text(json.dumps({'command':cmd,'returncode':p.returncode,'stderr':p.stderr},indent=2)+'\n')
assert p.returncode==0,'Archive creation failed; retain partial, do not retry blindly'
os.chmod(archive,0o600)
sha=digest(archive)
(SECURE/'SHA256SUMS').write_text(sha+'  maintenance-history.tar.xz\n'+digest(SECURE/'source-manifest.json')+'  source-manifest.json\n')
for command in [['xz','-t',str(archive)],['tar','-tJf',str(archive)],['sha256sum','-c','SHA256SUMS']]:
 p=subprocess.run(command,cwd=SECURE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 assert p.returncode==0,'Archive integrity gate failed'
# Independent Python reader recovers all regular bytes to bounded hash streams.
expected={ROOT.name+('' if r['relative_path']=='.' else '/'+r['relative_path']):r for r in manifest}
seen={};payloads={};links={};gnu_members=[];dirs=0;regular=0
with tarfile.open(archive,'r|xz') as tf:
 for m in tf:
  name=m.name.rstrip('/');assert name in expected and name not in seen,'Unexpected or repeated archive pathname';r=expected[name];seen[name]=True
  assert m.mode==stat.S_IMODE(r['mode']) and m.uid==r['uid'] and m.gid==r['gid'],'Archive ownership/mode mismatch'
  rawmtime=m.pax_headers.get('mtime',str(m.mtime));from decimal import Decimal
  assert abs(int(Decimal(rawmtime)*1000000000)-r['mtime_ns'])<=1,'Archive timestamp mismatch'
  if stat.S_ISDIR(r['mode']):assert m.isdir();dirs+=1
  elif stat.S_ISLNK(r['mode']):assert m.issym() and m.linkname==r['link_target'];links[name]=m.linkname
  elif stat.S_ISREG(r['mode']):
   regular+=1
   if m.islnk():
    assert m.linkname in payloads,'Hardlink source not available in recovered stream';h,n=payloads[m.linkname]
   else:
    assert m.isfile();gnu_members.append(name);f=tf.extractfile(m);hh=hashlib.sha256();n=0
    while b:=f.read(1024*1024):hh.update(b);n+=len(b)
    h=hh.hexdigest()
   assert h==r['sha256'] and n==r['size'],'Recovered member bytes mismatch';payloads[name]=(h,n)
  else:raise AssertionError('Unsupported source type')
assert set(seen)==set(expected),'Incomplete recovered pathname coverage'
verify_old()
# Independent GNU extraction hashes the full concatenated payload stream as a second implementation.
# Original payloads are fed in archive regular-member order to the same digest algorithm.
expected_hash=hashlib.sha256()
for name in gnu_members:
 r=expected[name]
 with open(ROOT/r['relative_path'],'rb') as f:
  while b:=f.read(1024*1024):expected_hash.update(b)
proc=subprocess.Popen(['tar','-xOJf',str(archive)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
actual_hash=hashlib.sha256()
while b:=proc.stdout.read(1024*1024):actual_hash.update(b)
err=proc.stderr.read();rc=proc.wait()
assert rc==0 and actual_hash.hexdigest()==expected_hash.hexdigest(),'Independent GNU payload recovery mismatch'
result={'status':'preservation_created_all_payloads_verified_materialized_fixture_pending','authority_message_id':'1571190519713759264','thread_id':'1569928464033783862','source_root':str(ROOT),'secure_set':str(SECURE),'archive_path':str(archive),'archive_sha256':sha,'archive_bytes':archive.stat().st_size,'archive_allocated_bytes':archive.stat().st_blocks*512,'original_allocated_bytes':sum({(r['dev'],r['ino']):r['allocated'] for r in manifest}.values()),'regular_files_recovered':regular,'directories_covered':dirs,'symlinks_covered':len(links),'source_originals_unchanged':True,'self_contained':True,'external_base_dependencies':0,'stream_recovery_python_all_files':True,'stream_recovery_gnu_concat':True,'full_real_layout_materialized':False,'deletions':0,'retention_changed':False,'services_restarted':False,'source_manifest_sha256':digest(SECURE/'source-manifest.json'),'created_at':datetime.datetime.now().astimezone().isoformat()}
(OUT/'preservation-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
