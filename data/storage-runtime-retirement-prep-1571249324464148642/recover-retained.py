"""Recovery proof uses retained inputs only; no code in old runtimes is executed."""
import pathlib,subprocess,json,gzip,tarfile,hashlib,stat,os
OUT=pathlib.Path(__file__).parent
ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0',PYTHONDONTWRITEBYTECODE='1')
def sha(path):return subprocess.check_output(['sha256sum','--',str(path)],text=True).split()[0]
def verify_archive(proof):
 assert sha(proof['archive'])==proof['sha256']
 expected={r['member']:r for r in json.load(gzip.open(proof['member_manifest'],'rt'))};seen=set();digests={}
 with tarfile.open(proof['archive'],'r|gz')as tf:
  for m in tf:
   assert m.name in expected and m.name not in seen;seen.add(m.name);r=expected[m.name]
   assert m.mode==stat.S_IMODE(r['mode'])and m.uid==r['uid']and m.gid==r['gid']
   if m.issym():assert m.linkname==r['link_target']
   elif m.islnk():assert digests[m.linkname]==r['sha256'];digests[m.name]=r['sha256']
   elif m.isfile():
    f=tf.extractfile(m);assert f is not None;h=hashlib.sha256();size=0
    while chunk:=f.read(1024*1024):h.update(chunk);size+=len(chunk)
    assert size==r['size']and h.hexdigest()==r['sha256'];digests[m.name]=h.hexdigest()
   else:assert m.isdir()
 assert seen==set(expected)
 return len(digests)
def verify_recovery():
 env=json.load(open(OUT/'environment-audit.json'));python_files=verify_archive(env['python_overrides']);node_files=verify_archive(env['node_preservation'])
 code=json.load(open(OUT/'code-recovery-spec.json'));assert sha(code['archive'])==code['sha256'];repo=code['retained_repository'];scratch=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/runtime-lot-recovery-1571249324464148642');scratch.mkdir(mode=0o700,exist_ok=True)
 wanted={root['label']+'/working-tree.patch'for root in code['roots']}|{root['label']+'/overlay/'+r['path']for root in code['roots']for r in root['expected_files']if r['path']not in root['modified_paths']};data={}
 with tarfile.open(code['archive'],'r:gz')as tf:
  for m in tf:
   if m.name in wanted:
    f=tf.extractfile(m);assert f is not None;data[m.name]=f.read()
 checked=0
 for root in code['roots']:
  p=subprocess.run(['git','-C',repo,'archive','--format=tar',root['base']],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=ENV);assert p.returncode==0
  dest=scratch/root['label'];dest.mkdir(exist_ok=True)
  for rel in root['modified_paths']:
   p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','-C',repo,'show',root['base']+':'+rel],env=ENV));record=next(r for r in root['expected_files']if r['path']==rel);os.chmod(p,record['mode'])
  patch=scratch/(root['label']+'.patch');patch.write_bytes(data[root['label']+'/working-tree.patch'])
  subprocess.run(['git','-C',str(dest),'apply','--check',str(patch)],env=ENV,check=True,capture_output=True);subprocess.run(['git','-C',str(dest),'apply',str(patch)],env=ENV,check=True,capture_output=True)
  for r in root['expected_files']:
   p=dest/r['path']
   if r['path']not in root['modified_paths']:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data[root['label']+'/overlay/'+r['path']]);os.chmod(p,r['mode'])
   assert sha(p)==r['sha256'];checked+=1
 gitproof=json.load(open(OUT/'git-recovery-and-registration.json'))
 for row in gitproof['git_object_coverage']:
  if row['missing_object_pack']:assert sha(row['missing_object_pack']['path'])==row['missing_object_pack']['sha256']
 return {'source_and_state_files_replayed':checked,'python_override_payloads_verified':python_files,'node_payloads_verified':node_files,'reads_original_runtime_paths':False,'old_python_environment_rebuilt':False,'live_profile_or_SQLite_opened':False}
if __name__=='__main__':print(json.dumps(verify_recovery()))
